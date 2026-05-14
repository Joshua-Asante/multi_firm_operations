"""Emit markdown + JSON summary for a Path B run directory; §14 disposition when OOS present.

Q-CORR-1.2 handoff §5.8: disposition verdict (RESOLVED / FALSIFIED / AMBIGUOUS) is
printed to stdout by the caller, NEVER written to report.json or report.md.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

_WFO = Path(__file__).resolve().parent
_REPO = _WFO.parents[1]

if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
if str(_WFO) not in sys.path:
    sys.path.insert(0, str(_WFO))

# §14 gate thresholds (LOCK — frozen with parent brief).
_GATE_PF_MIN = 1.50
_GATE_WR_MIN_PCT = 15.0
_GATE_DD_MAX_PCT = 8.0
_GATE_BOOT_P05_PF_MIN = 1.30
_GATE_HALF_RATIO_LO = 0.7
_GATE_HALF_RATIO_HI = 1.3
_GATE_MFE_MAE_RATIO_MIN = 2.0
_GATE_CORR_RESOLVED_MAX = 0.10
_GATE_CORR_AMBIGUOUS_MAX = 0.15

_DEFAULT_COMPARATOR_DIR = _REPO / "data" / "tv_exports" / "pepperstone"


def _read_manifest(run_dir: Path) -> dict:
    return json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))


def _resolve_comparator_path(
    sha: str,
    comparator_dir: Path,
) -> Path | None:
    """Find the file in `comparator_dir` whose SHA256SUMS line matches `sha`."""
    if not sha or len(sha) != 64:
        return None
    sums = comparator_dir / "SHA256SUMS"
    if not sums.is_file():
        return None
    for line in sums.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and parts[0].lower() == sha.lower():
            basename = parts[1].lstrip("*")
            candidate = comparator_dir / basename
            if candidate.is_file():
                return candidate
    return None


def _audit_ordering(run_dir: Path) -> tuple[bool, list[str]]:
    """Programmatic audit_path_b_ordering invocation; returns (pass, errors)."""
    from audit_path_b_ordering import audit_manifest

    manifest_path = run_dir / "run_manifest.json"
    errors = audit_manifest(manifest_path)
    return (not errors, errors)


def _half_panel_pf(daily_pnl_values: np.ndarray) -> tuple[float, float, float]:
    """H1/H2 PF directional ratio (H1 = chronological first half)."""
    from lib.regime_bootstrap import compute_pf

    n = len(daily_pnl_values)
    mid = n // 2
    pf_h1 = compute_pf(daily_pnl_values[:mid])
    pf_h2 = compute_pf(daily_pnl_values[mid:])
    if pf_h2 == 0 or not np.isfinite(pf_h2):
        ratio = float("inf") if pf_h1 > 0 else 0.0
    else:
        ratio = pf_h1 / pf_h2
    return float(pf_h1), float(pf_h2), float(ratio)


def _bootstrap_p05_pf(
    daily_pnl,
    *,
    seed: int,
    n_panels: int,
    notional: float = 200_000.0,
) -> float:
    from lib.regime_bootstrap import regime_bootstrap_daily_pnl

    res = regime_bootstrap_daily_pnl(
        daily_pnl,
        n_panels=n_panels,
        block_months=6,
        seed=seed,
        notional=notional,
    )
    return float(res.p05_pf)


def _evaluate_oos_gates(
    *,
    run_dir: Path,
    manifest: dict,
    oos_row: dict,
    comparator_path: Path | None,
    comparator_sha_in_sums: bool,
) -> dict:
    """Evaluate §14 gates 1-12 for a single OOS row. Returns dict per gate."""
    from lib.correlation import load_exit_date_daily_net, pearson_daily_series

    gates: dict = {}

    # Gates 1-3: hashes / comparator sha integrity (manifest-resident, plus SHA256SUMS check).
    grid_hash = manifest.get("grid_hash") or ""
    fold_spec_hash = manifest.get("fold_spec_hash") or ""
    comparator_sha = manifest.get("comparator_csv_sha256") or ""

    # Authoritative pins from grid_hash utility on the run-dir copies.
    from grid_hash import fold_spec_hash_from_path, grid_hash_from_path  # type: ignore

    grid_p = run_dir / "grid.json"
    fold_p = run_dir / "fold_spec.json"
    actual_grid = grid_hash_from_path(grid_p) if grid_p.is_file() else ""
    actual_fold = fold_spec_hash_from_path(fold_p) if fold_p.is_file() else ""

    gates["1_grid_hash"] = {
        "pass": bool(grid_hash) and grid_hash == actual_grid,
        "manifest": grid_hash,
        "actual": actual_grid,
    }
    gates["2_fold_spec_hash"] = {
        "pass": bool(fold_spec_hash) and fold_spec_hash == actual_fold,
        "manifest": fold_spec_hash,
        "actual": actual_fold,
    }
    gates["3_comparator_csv_sha256"] = {
        "pass": len(comparator_sha) == 64 and comparator_sha_in_sums,
        "manifest_sha": comparator_sha,
        "found_in_sha256sums": comparator_sha_in_sums,
    }

    # Gate 4: audit_path_b_ordering PASS.
    audit_pass, audit_errs = _audit_ordering(run_dir)
    gates["4_audit_ordering"] = {"pass": audit_pass, "errors": audit_errs}

    # Gate 5: assert_oos_matches_lock for the OOS row.
    from train_selection_lock import assert_oos_matches_lock  # type: ignore

    lock_path = run_dir / "train_selection_lock.json"
    g5_pass = True
    g5_err = ""
    try:
        assert_oos_matches_lock(Path(oos_row["path"]), lock_path)
    except (AssertionError, FileNotFoundError) as e:
        g5_pass = False
        g5_err = str(e)
    gates["5_oos_matches_lock"] = {"pass": g5_pass, "error": g5_err}

    # Gates 6-8, 11: from OOS metrics computed at ingest time.
    metrics = oos_row.get("metrics") or {}
    pf = float(metrics.get("pf", 0.0))
    wr = float(metrics.get("wr_pct", 0.0))
    dd = float(metrics.get("max_dd_pct", 100.0))
    mfe_mae = float(metrics.get("mfe_mae_ratio", 0.0))

    gates["6_pf_min"] = {"pass": pf >= _GATE_PF_MIN, "value": pf, "threshold": _GATE_PF_MIN}
    gates["7_wr_min_pct"] = {"pass": wr >= _GATE_WR_MIN_PCT, "value": wr, "threshold": _GATE_WR_MIN_PCT}
    gates["8_dd_max_pct"] = {"pass": dd <= _GATE_DD_MAX_PCT, "value": dd, "threshold": _GATE_DD_MAX_PCT}
    gates["11_mfe_mae_ratio_min"] = {
        "pass": mfe_mae > _GATE_MFE_MAE_RATIO_MIN,
        "value": mfe_mae,
        "threshold": _GATE_MFE_MAE_RATIO_MIN,
    }

    # Gates 9, 10, 12 need daily P&L.
    oos_csv_path = Path(oos_row["path"])
    bootstrap_seed = int(manifest.get("bootstrap_seed", 42))
    bootstrap_n_panels = int(manifest.get("bootstrap_n_panels", 1000))

    daily = load_exit_date_daily_net(oos_csv_path)
    if len(daily) >= 2:
        p05 = _bootstrap_p05_pf(
            daily,
            seed=bootstrap_seed,
            n_panels=bootstrap_n_panels,
        )
        gates["9_bootstrap_p05_pf"] = {
            "pass": p05 >= _GATE_BOOT_P05_PF_MIN,
            "value": p05,
            "threshold": _GATE_BOOT_P05_PF_MIN,
            "seed": bootstrap_seed,
            "n_panels": bootstrap_n_panels,
        }
        pf_h1, pf_h2, ratio = _half_panel_pf(daily.values.astype(float))
        gates["10_half_panel_pf_ratio"] = {
            "pass": _GATE_HALF_RATIO_LO <= ratio <= _GATE_HALF_RATIO_HI,
            "h1_pf": pf_h1,
            "h2_pf": pf_h2,
            "ratio_h1_over_h2": ratio,
            "range": [_GATE_HALF_RATIO_LO, _GATE_HALF_RATIO_HI],
        }
    else:
        gates["9_bootstrap_p05_pf"] = {"pass": False, "error": "insufficient daily series"}
        gates["10_half_panel_pf_ratio"] = {"pass": False, "error": "insufficient daily series"}

    # Gate 12: correlation with comparator.
    if comparator_path is None:
        gates["12_correlation"] = {
            "pass": False,
            "error": "comparator CSV not resolved from sha256",
        }
    else:
        comparator_daily = load_exit_date_daily_net(comparator_path)
        rho = pearson_daily_series(daily, comparator_daily)
        gates["12_correlation"] = {
            "pass": (rho == rho) and (rho <= _GATE_CORR_RESOLVED_MAX),  # rho==rho filters NaN
            "value": float(rho),
            "threshold_resolved": _GATE_CORR_RESOLVED_MAX,
            "threshold_ambiguous_max": _GATE_CORR_AMBIGUOUS_MAX,
        }

    return gates


def _disposition_from_gates(gates: dict) -> str:
    """Apply §14 RESOLVED / FALSIFIED / AMBIGUOUS classification."""
    # FALSIFIED: audit hooks 1-5 fail, or standalone gates 6-10 fail, or gate 11 fail,
    # or correlation > 0.15.
    audit_gate_keys = ["1_grid_hash", "2_fold_spec_hash", "3_comparator_csv_sha256",
                       "4_audit_ordering", "5_oos_matches_lock"]
    standalone_keys = ["6_pf_min", "7_wr_min_pct", "8_dd_max_pct",
                       "9_bootstrap_p05_pf", "10_half_panel_pf_ratio"]

    for k in audit_gate_keys:
        if not gates.get(k, {}).get("pass", False):
            return "FALSIFIED"
    for k in standalone_keys:
        if not gates.get(k, {}).get("pass", False):
            return "FALSIFIED"
    if not gates.get("11_mfe_mae_ratio_min", {}).get("pass", False):
        return "FALSIFIED"

    g12 = gates.get("12_correlation", {})
    rho = g12.get("value")
    if rho is None or (isinstance(rho, float) and rho != rho):
        return "FALSIFIED"
    if rho <= _GATE_CORR_RESOLVED_MAX:
        return "RESOLVED"
    if rho <= _GATE_CORR_AMBIGUOUS_MAX:
        return "AMBIGUOUS"
    return "FALSIFIED"


def _write_stub_report(run_dir: Path, manifest: dict) -> None:
    report = {
        "run_id": manifest.get("run_id"),
        "grid_hash": manifest.get("grid_hash"),
        "fold_spec_hash": manifest.get("fold_spec_hash"),
        "status": "stub_no_metrics",
    }
    (run_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        f"# WFO run {report['run_id']}",
        "",
        f"- grid_hash: `{report['grid_hash']}`",
        f"- fold_spec_hash: `{report['fold_spec_hash']}`",
        "",
        "_Metrics aggregation not yet executed for this stub run._",
        "",
    ]
    (run_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def _write_train_only_report(run_dir: Path, manifest: dict, train_rows: list[dict]) -> None:
    report = {
        "run_id": manifest.get("run_id"),
        "grid_hash": manifest.get("grid_hash"),
        "fold_spec_hash": manifest.get("fold_spec_hash"),
        "status": "train_only",
        "n_train_ingests": len(train_rows),
    }
    (run_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        f"# WFO run {report['run_id']} (train-only, no OOS yet)",
        "",
        f"- grid_hash: `{report['grid_hash']}`",
        f"- fold_spec_hash: `{report['fold_spec_hash']}`",
        f"- n_train_ingests: **{len(train_rows)}**",
        "",
        "## Train ingests (top 10 by PF)",
        "",
        "| config_id | n | PF | WR% | DD% |",
        "|---|---|---|---|---|",
    ]
    sorted_train = sorted(
        train_rows,
        key=lambda r: -float(r.get("metrics", {}).get("pf", 0.0)),
    )[:10]
    for r in sorted_train:
        m = r.get("metrics", {})
        lines.append(
            f"| `{r.get('config_id', '?')}` | {m.get('n_trades', '?')} | "
            f"{m.get('pf', 0.0):.3f} | {m.get('wr_pct', 0.0):.2f} | {m.get('max_dd_pct', 0.0):.2f} |"
        )
    lines.append("")
    (run_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def _write_full_report(
    run_dir: Path,
    manifest: dict,
    train_rows: list[dict],
    oos_row: dict,
    gates: dict,
) -> None:
    # §5.8: do NOT write disposition verdict to JSON or MD.
    report = {
        "run_id": manifest.get("run_id"),
        "grid_hash": manifest.get("grid_hash"),
        "fold_spec_hash": manifest.get("fold_spec_hash"),
        "status": "full_oos",
        "n_train_ingests": len(train_rows),
        "oos": {
            "config_id": oos_row.get("config_id"),
            "metrics": oos_row.get("metrics"),
        },
        "gates": gates,
    }
    (run_dir / "report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    lines = [
        f"# WFO run {report['run_id']} (OOS present)",
        "",
        f"- grid_hash: `{report['grid_hash']}`",
        f"- fold_spec_hash: `{report['fold_spec_hash']}`",
        f"- OOS config: `{report['oos']['config_id']}`",
        "",
        "## §14 gate evaluation",
        "",
        "| Gate | Pass | Detail |",
        "|---|---|---|",
    ]
    for gate_id in sorted(gates.keys()):
        g = gates[gate_id]
        ok = "OK" if g.get("pass") else "FAIL"
        detail_parts = []
        for k, v in g.items():
            if k == "pass":
                continue
            if isinstance(v, float):
                detail_parts.append(f"{k}={v:.4f}")
            else:
                detail_parts.append(f"{k}={v}")
        detail = ", ".join(detail_parts)
        lines.append(f"| `{gate_id}` | {ok} | {detail} |")
    lines.append("")
    (run_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def emit_reports(
    run_dir: str | Path,
    *,
    comparator_dir: Path | None = None,
) -> dict:
    """Emit report.md + report.json under run_dir.

    Modes (auto-detected from manifest contents):
      - stub: init-run only (no ingests)
      - train_only: train ingests, no OOS
      - full: at least one OOS ingest → applies §14 gates and returns disposition

    Returns a dict with keys: ``mode``, plus ``gates`` and ``disposition`` in full mode.
    """
    run_dir = Path(run_dir)
    manifest = _read_manifest(run_dir)
    ingests = manifest.get("ingests") or []
    train_rows = [r for r in ingests if r.get("phase") == "train"]
    oos_rows = [r for r in ingests if r.get("phase") == "oos"]

    if not train_rows and not oos_rows:
        _write_stub_report(run_dir, manifest)
        return {"mode": "stub"}

    if not oos_rows:
        _write_train_only_report(run_dir, manifest, train_rows)
        return {"mode": "train_only", "n_train": len(train_rows)}

    if len(oos_rows) > 1:
        raise ValueError(
            f"expected ≤1 OOS ingest per Q-CORR-1.2 §13 (n_folds=1); got {len(oos_rows)}"
        )
    oos_row = oos_rows[0]

    cdir = Path(comparator_dir) if comparator_dir else _DEFAULT_COMPARATOR_DIR
    comparator_sha = manifest.get("comparator_csv_sha256") or ""
    comparator_path = _resolve_comparator_path(comparator_sha, cdir)
    comparator_sha_in_sums = comparator_path is not None

    gates = _evaluate_oos_gates(
        run_dir=run_dir,
        manifest=manifest,
        oos_row=oos_row,
        comparator_path=comparator_path,
        comparator_sha_in_sums=comparator_sha_in_sums,
    )
    disposition = _disposition_from_gates(gates)
    _write_full_report(run_dir, manifest, train_rows, oos_row, gates)
    return {"mode": "full", "gates": gates, "disposition": disposition}
