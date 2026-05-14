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

_FLOOR_DD_MAX_PCT = 8.0
_FLOOR_WR_MIN_PCT = 15.0
_FLOOR_TRADES_MIN = 50
_TIE_TOL = 1e-9


def _read_manifest(run_dir: Path) -> dict:
    mp = run_dir / "run_manifest.json"
    if not mp.is_file():
        raise FileNotFoundError(f"missing manifest {mp}")
    return json.loads(mp.read_text(encoding="utf-8"))


def _write_manifest(run_dir: Path, data: dict) -> None:
    (run_dir / "run_manifest.json").write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )


def _fold_entry(manifest: dict, fold_id: str) -> dict:
    folds = manifest.setdefault("folds", [])
    for f in folds:
        if str(f.get("fold_id")) == str(fold_id):
            return f
    entry = {"fold_id": str(fold_id), "oos_csv_paths": []}
    folds.append(entry)
    return entry


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

    if parsed["phase"] == "oos":
        from train_selection_lock import read_train_selection_lock

        lock = read_train_selection_lock(run_dir / "train_selection_lock.json")
        fold = _fold_entry(manifest, str(lock.get("fold_id", "1")))
        oos_paths = fold.setdefault("oos_csv_paths", [])
        if str(csv_path) not in oos_paths:
            oos_paths.append(str(csv_path))

    _write_manifest(run_dir, manifest)
    return row


def _detect_tie_break(feasible_sorted: list[dict]) -> list[str] | None:
    """Inspect top-2 of sorted feasible list; return tier list or None for no-tie."""
    if len(feasible_sorted) < 2:
        return None
    a, b = feasible_sorted[0], feasible_sorted[1]
    ma, mb = a["metrics"], b["metrics"]
    if abs(float(ma["pf"]) - float(mb["pf"])) > _TIE_TOL:
        return None
    tiers = ["pf_tie"]
    if abs(float(ma["max_dd_pct"]) - float(mb["max_dd_pct"])) > _TIE_TOL:
        return tiers
    tiers.append("dd_tie")
    wd_a = abs(float(ma["wr_pct"]) - 20.0)
    wd_b = abs(float(mb["wr_pct"]) - 20.0)
    if abs(wd_a - wd_b) > _TIE_TOL:
        return tiers
    tiers.append("wr_distance_tie")
    tiers.append("alpha_id")
    return tiers


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
            m["n_trades"] >= _FLOOR_TRADES_MIN
            and m["wr_pct"] >= _FLOOR_WR_MIN_PCT
            and m["max_dd_pct"] <= _FLOOR_DD_MAX_PCT
        ):
            feasible.append(row)

    constraint_floors = {
        "DD_max": _FLOOR_DD_MAX_PCT,
        "WR_min": _FLOOR_WR_MIN_PCT,
        "trades_min": _FLOOR_TRADES_MIN,
    }
    grid_hash = manifest.get("grid_hash")
    fold_spec_hash = manifest.get("fold_spec_hash")
    lock_path = run_dir / "train_selection_lock.json"

    if not feasible:
        committed = write_train_selection_lock(
            lock_path,
            fold_id=fold_id,
            expected_oos_csv_basename="",
            selected_config_id="",
            selection_status="NO_CANDIDATE",
            constraint_floors=constraint_floors,
            tie_break_applied=None,
            candidate_count=0,
            grid_hash=grid_hash,
            fold_spec_hash=fold_spec_hash,
        )
        fold = _fold_entry(manifest, fold_id)
        fold["train_selection_committed_utc"] = committed
        fold["selection_status"] = "NO_CANDIDATE"
        fold["candidate_count"] = 0
        _write_manifest(run_dir, manifest)
        raise ValueError(
            "no feasible train config "
            f"(need n_trades>={_FLOOR_TRADES_MIN}, "
            f"WR>={_FLOOR_WR_MIN_PCT}%, DD<={_FLOOR_DD_MAX_PCT}% per §16); "
            f"NO_CANDIDATE lock written to {lock_path}"
        )

    def sort_key(r: dict) -> tuple:
        m = r["metrics"]
        pf = float(m["pf"])
        if not np.isfinite(pf):
            pf = 1e9
        return (-pf, m["max_dd_pct"], abs(float(m["wr_pct"]) - 20.0), r["config_id"])

    feasible.sort(key=sort_key)
    best = feasible[0]
    tie_break_applied = _detect_tie_break(feasible)
    oos_name = expected_oos_basename(best["basename"])

    committed = write_train_selection_lock(
        lock_path,
        fold_id=fold_id,
        expected_oos_csv_basename=oos_name,
        selected_config_id=best["config_id"],
        selection_status="OK",
        constraint_floors=constraint_floors,
        tie_break_applied=tie_break_applied,
        candidate_count=len(feasible),
        grid_hash=grid_hash,
        fold_spec_hash=fold_spec_hash,
        extra={"train_basename": best["basename"], "metrics": best["metrics"]},
    )

    fold = _fold_entry(manifest, fold_id)
    fold["train_selection_committed_utc"] = committed
    fold["selected_config_id"] = best["config_id"]
    fold["selected_train_basename"] = best["basename"]
    fold["expected_oos_csv_basename"] = oos_name
    fold["candidate_count"] = len(feasible)
    fold["selection_status"] = "OK"
    _write_manifest(run_dir, manifest)

    return {
        "selected": best,
        "expected_oos_csv_basename": oos_name,
        "train_selection_committed_utc": committed,
        "lock_path": str(lock_path),
        "candidate_count": len(feasible),
        "tie_break_applied": tie_break_applied,
    }
