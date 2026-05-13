"""Load-bearing WFO ``ingest`` / ``select`` operations (Q-CORR-1.2 §16)."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from analysis.oanda_stage1.tv_export_loader import pair_tv_export_dataframe

_WFO = Path(__file__).resolve().parent
if str(_WFO) not in sys.path:
    sys.path.insert(0, str(_WFO))

from silver_filename import (
    expected_oos_basename,
    load_grid,
    parse_silver_export_basename,
    validate_parsed_in_grid,
)
from trade_metrics import trade_panel_metrics
from train_selection_lock import write_train_selection_lock


def _read_manifest(run_dir: Path) -> dict:
    mp = run_dir / "run_manifest.json"
    if not mp.is_file():
        raise FileNotFoundError(f"missing manifest {mp}")
    return json.loads(mp.read_text(encoding="utf-8"))


def _write_manifest(run_dir: Path, data: dict) -> None:
    (run_dir / "run_manifest.json").write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )


def ingest_tv_csv(
    run_dir: Path,
    csv_path: Path,
    *,
    min_raw_rows: int = 100,
    min_trades: int = 10,
    max_trades: int = 5000,
    notional: float = 200_000.0,
    validate_grid: bool = True,
) -> dict:
    """Ingest one TV CSV: filename §16, schema pair, hash dedupe, metrics, manifest row."""
    run_dir = Path(run_dir).resolve()
    csv_path = Path(csv_path).resolve()
    if not csv_path.is_file():
        raise FileNotFoundError(csv_path)

    name = csv_path.name
    parsed = parse_silver_export_basename(name)
    if validate_grid:
        validate_parsed_in_grid(parsed, load_grid(run_dir))

    digest = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    manifest = _read_manifest(run_dir)
    ingests = manifest.setdefault("ingests", [])
    for prev in ingests:
        if prev.get("sha256") == digest:
            raise ValueError(f"duplicate ingest sha256 {digest[:12]}… (already recorded)")
        if prev.get("basename") == name:
            raise ValueError(f"duplicate basename {name!r} with different hash — investigate")

    if parsed["phase"] == "oos":
        lockp = run_dir / "train_selection_lock.json"
        if not lockp.is_file():
            raise ValueError("OOS ingest requires train_selection_lock.json (run select first)")
        from train_selection_lock import assert_oos_matches_lock

        assert_oos_matches_lock(csv_path, lockp)

    raw = pd.read_csv(csv_path, encoding="utf-8-sig")
    trades = pair_tv_export_dataframe(
        raw,
        expected_symbol="XAGUSD",
        min_raw_rows=min_raw_rows,
        source_label=name,
    )
    n_trades = len(trades)
    if n_trades < min_trades or n_trades > max_trades:
        raise ValueError(
            f"trade count {n_trades} outside plausibility range [{min_trades}, {max_trades}]"
        )

    metrics = trade_panel_metrics(trades, notional=notional)

    ingested_utc = datetime.now(timezone.utc).isoformat()
    config_id = name[:-4]  # stem
    row = {
        "path": str(csv_path),
        "basename": name,
        "sha256": digest,
        "ingested_utc": ingested_utc,
        "phase": parsed["phase"],
        "parsed": {k: parsed[k] for k in ("ema_slow_len", "stop_atr", "tp_atr", "session")},
        "metrics": metrics,
        "config_id": config_id,
    }
    ingests.append(row)
    _write_manifest(run_dir, manifest)
    return row


def select_train_fold(
    run_dir: Path,
    *,
    fold_id: str = "1",
) -> dict:
    """§16 selection ladder over train ingests only; writes lock + manifest fold."""
    run_dir = Path(run_dir).resolve()
    manifest = _read_manifest(run_dir)
    ingests = manifest.get("ingests") or []
    train_rows = [x for x in ingests if x.get("phase") == "train"]
    if not train_rows:
        raise ValueError("no train ingests in manifest")

    feasible: list[dict] = []
    for row in train_rows:
        m = row["metrics"]
        if (
            m["n_trades"] >= 50
            and m["wr_pct"] >= 15.0
            and m["max_dd_pct"] <= 8.0
        ):
            feasible.append(row)

    if not feasible:
        raise ValueError(
            "no feasible train config (need n_trades>=50, WR>=15%, DD<=8% per §16)"
        )

    def sort_key(r: dict) -> tuple:
        m = r["metrics"]
        pf = float(m["pf"])
        if not np.isfinite(pf):
            pf = 1e9
        return (-pf, m["max_dd_pct"], abs(float(m["wr_pct"]) - 20.0), r["config_id"])

    feasible.sort(key=sort_key)
    best = feasible[0]
    oos_name = expected_oos_basename(best["basename"])

    lock_path = run_dir / "train_selection_lock.json"
    committed = write_train_selection_lock(
        lock_path,
        fold_id=fold_id,
        expected_oos_csv_basename=oos_name,
        selected_config_id=best["config_id"],
        extra={"train_basename": best["basename"], "metrics": best["metrics"]},
    )

    folds = manifest.setdefault("folds", [])
    fold_entry = None
    for f in folds:
        if str(f.get("fold_id")) == str(fold_id):
            fold_entry = f
            break
    if fold_entry is None:
        fold_entry = {"fold_id": str(fold_id), "oos_csv_paths": []}
        folds.append(fold_entry)

    fold_entry["train_selection_committed_utc"] = committed
    fold_entry["selected_config_id"] = best["config_id"]
    fold_entry["selected_train_basename"] = best["basename"]
    fold_entry["expected_oos_csv_basename"] = oos_name
    _write_manifest(run_dir, manifest)

    return {
        "selected": best,
        "expected_oos_csv_basename": oos_name,
        "train_selection_committed_utc": committed,
        "lock_path": str(lock_path),
    }
