"""Q-CORR-1.2 §14 disposition + emit_reports modes."""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
WFO = REPO / "scripts" / "wfo"
EXAMPLES = WFO / "examples"


def _all_pass_gates(rho: float = 0.05) -> dict:
    return {
        "1_grid_hash": {"pass": True},
        "2_fold_spec_hash": {"pass": True},
        "3_comparator_csv_sha256": {"pass": True},
        "4_audit_ordering": {"pass": True},
        "5_oos_matches_lock": {"pass": True},
        "6_pf_min": {"pass": True, "value": 1.8, "threshold": 1.5},
        "7_wr_min_pct": {"pass": True, "value": 22.0, "threshold": 15.0},
        "8_dd_max_pct": {"pass": True, "value": 4.0, "threshold": 8.0},
        "9_bootstrap_p05_pf": {"pass": True, "value": 1.4, "threshold": 1.3},
        "10_half_panel_pf_ratio": {"pass": True, "ratio_h1_over_h2": 1.05},
        "11_mfe_mae_ratio_min": {"pass": True, "value": 3.0, "threshold": 2.0},
        "12_correlation": {"pass": rho <= 0.10, "value": rho, "threshold_resolved": 0.10},
    }


def test_disposition_resolved_all_pass():
    sys.path.insert(0, str(WFO))
    from report import _disposition_from_gates  # type: ignore

    gates = _all_pass_gates(rho=0.05)
    assert _disposition_from_gates(gates) == "RESOLVED"


def test_disposition_falsified_audit_gate1():
    sys.path.insert(0, str(WFO))
    from report import _disposition_from_gates  # type: ignore

    gates = _all_pass_gates()
    gates["1_grid_hash"] = {"pass": False}
    assert _disposition_from_gates(gates) == "FALSIFIED"


def test_disposition_falsified_gate6_pf():
    sys.path.insert(0, str(WFO))
    from report import _disposition_from_gates  # type: ignore

    gates = _all_pass_gates()
    gates["6_pf_min"] = {"pass": False, "value": 1.3, "threshold": 1.5}
    assert _disposition_from_gates(gates) == "FALSIFIED"


def test_disposition_falsified_correlation_over_15():
    sys.path.insert(0, str(WFO))
    from report import _disposition_from_gates  # type: ignore

    gates = _all_pass_gates()
    gates["12_correlation"] = {"pass": False, "value": 0.20, "threshold_resolved": 0.10}
    assert _disposition_from_gates(gates) == "FALSIFIED"


def test_disposition_ambiguous_correlation_in_band():
    sys.path.insert(0, str(WFO))
    from report import _disposition_from_gates  # type: ignore

    gates = _all_pass_gates()
    gates["12_correlation"] = {"pass": False, "value": 0.13, "threshold_resolved": 0.10}
    assert _disposition_from_gates(gates) == "AMBIGUOUS"


def test_disposition_falsified_mfe_mae():
    sys.path.insert(0, str(WFO))
    from report import _disposition_from_gates  # type: ignore

    gates = _all_pass_gates()
    gates["11_mfe_mae_ratio_min"] = {"pass": False, "value": 1.5, "threshold": 2.0}
    assert _disposition_from_gates(gates) == "FALSIFIED"


def test_disposition_falsified_correlation_nan():
    sys.path.insert(0, str(WFO))
    from report import _disposition_from_gates  # type: ignore

    gates = _all_pass_gates()
    gates["12_correlation"] = {"pass": False, "value": float("nan")}
    assert _disposition_from_gates(gates) == "FALSIFIED"


def _write_minimal_pnl_csv(
    path: Path,
    n_days: int,
    daily_pnl: float = 200.0,
    start: str = "2025-06-01",
    pattern: str = "constant",
) -> str:
    """Write a CSV with `Type / Date and time / Net P&L USD` only.

    pattern:
      - "constant": every day = daily_pnl (Pearson undefined; std=0)
      - "alternating": odd days = daily_pnl, even days = -daily_pnl * 0.4
      - "sin": daily_pnl * sin(i * 0.3) — varying with positive mean for PF
    """
    import math

    base = datetime.fromisoformat(start)
    lines = ["Type,Date and time,Net P&L USD"]
    for i in range(n_days):
        ts = (base + timedelta(days=i)).strftime("%Y-%m-%d %H:%M:%S")
        if pattern == "alternating":
            v = daily_pnl if (i % 2 == 0) else -daily_pnl * 0.4
        elif pattern == "sin":
            v = daily_pnl + daily_pnl * 0.5 * math.sin(i * 0.3)
        else:
            v = daily_pnl
        lines.append(f"Exit long,{ts},{v}")
    text = "\n".join(lines) + "\n"
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_emit_reports_stub_mode(tmp_path):
    sys.path.insert(0, str(WFO))
    import report  # type: ignore

    run_dir = tmp_path / "stub"
    run_dir.mkdir()
    shutil.copy(EXAMPLES / "grid.json", run_dir / "grid.json")
    shutil.copy(EXAMPLES / "fold_spec.json", run_dir / "fold_spec.json")
    manifest = {
        "run_id": "stub_run",
        "grid_hash": "x", "fold_spec_hash": "y",
        "ingests": [], "folds": [],
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    out = report.emit_reports(run_dir)
    assert out == {"mode": "stub"}
    assert (run_dir / "report.json").is_file()
    assert (run_dir / "report.md").is_file()
    report_json = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
    assert report_json["status"] == "stub_no_metrics"
    # §5.8: no disposition string in JSON
    assert "RESOLVED" not in (run_dir / "report.md").read_text(encoding="utf-8")
    assert "FALSIFIED" not in (run_dir / "report.md").read_text(encoding="utf-8")


def test_emit_reports_train_only_mode(tmp_path):
    sys.path.insert(0, str(WFO))
    import report  # type: ignore

    run_dir = tmp_path / "train_only"
    run_dir.mkdir()
    shutil.copy(EXAMPLES / "grid.json", run_dir / "grid.json")
    shutil.copy(EXAMPLES / "fold_spec.json", run_dir / "fold_spec.json")
    manifest = {
        "run_id": "train_only_run",
        "grid_hash": "x", "fold_spec_hash": "y",
        "ingests": [
            {
                "phase": "train",
                "config_id": "Silver_e395_sl140_tp33_NYExt_train",
                "metrics": {"n_trades": 60, "pf": 1.4, "wr_pct": 16.0, "max_dd_pct": 7.0, "mfe_mae_ratio": 3.0},
            },
        ],
        "folds": [],
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    out = report.emit_reports(run_dir)
    assert out["mode"] == "train_only"
    assert out["n_train"] == 1
    md = (run_dir / "report.md").read_text(encoding="utf-8")
    assert "train_only" in md.lower() or "train" in md.lower()
    # §5.8: no disposition verdict
    assert "RESOLVED" not in md and "FALSIFIED" not in md and "AMBIGUOUS" not in md


def test_emit_reports_full_mode_synthetic(tmp_path):
    """Full §14 evaluation on synthetic OOS + comparator CSVs.

    Builds enough machinery for gates 1-12 to *compute* — does not assert a
    specific disposition (synthetic series rarely produce a clean RESOLVED;
    disposition logic is unit-tested separately).
    """
    sys.path.insert(0, str(WFO))
    import report  # type: ignore
    from grid_hash import fold_spec_hash_from_path, grid_hash_from_path  # type: ignore

    run_dir = tmp_path / "full"
    run_dir.mkdir()
    shutil.copy(EXAMPLES / "grid.json", run_dir / "grid.json")
    shutil.copy(EXAMPLES / "fold_spec.json", run_dir / "fold_spec.json")

    # Synthetic comparator CSV + SHA256SUMS.
    comparator_dir = tmp_path / "tv_exports"
    comparator_dir.mkdir()
    cmp_csv = comparator_dir / "Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_synthetic.csv"
    cmp_sha = _write_minimal_pnl_csv(cmp_csv, n_days=200, daily_pnl=150.0, start="2025-06-01")
    (comparator_dir / "SHA256SUMS").write_text(
        f"{cmp_sha} *{cmp_csv.name}\n", encoding="utf-8"
    )

    # Synthetic OOS CSV (250 trading days; consistent win → bootstrap-stable).
    oos_csv = run_dir / "Silver_e395_sl140_tp33_NYExt_oos.csv"
    _write_minimal_pnl_csv(oos_csv, n_days=250, daily_pnl=200.0, start="2025-06-01")

    grid_h = grid_hash_from_path(run_dir / "grid.json")
    fold_h = fold_spec_hash_from_path(run_dir / "fold_spec.json")

    manifest = {
        "run_id": "full_run",
        "grid_hash": grid_h,
        "fold_spec_hash": fold_h,
        "comparator_csv_sha256": cmp_sha,
        "bootstrap_seed": 42,
        "bootstrap_n_panels": 50,  # small for test speed
        "ingests": [
            {
                "phase": "train",
                "config_id": "Silver_e395_sl140_tp33_NYExt_train",
                "metrics": {"n_trades": 80, "pf": 2.0, "wr_pct": 22.0, "max_dd_pct": 5.0, "mfe_mae_ratio": 3.0},
            },
            {
                "phase": "oos",
                "config_id": "Silver_e395_sl140_tp33_NYExt_oos",
                "path": str(oos_csv),
                "metrics": {"n_trades": 80, "pf": 2.0, "wr_pct": 22.0, "max_dd_pct": 4.0, "mfe_mae_ratio": 3.0},
            },
        ],
        "folds": [
            {
                "fold_id": "1",
                "train_selection_committed_utc": (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat(),
                "selected_config_id": "Silver_e395_sl140_tp33_NYExt_train",
                "expected_oos_csv_basename": "Silver_e395_sl140_tp33_NYExt_oos.csv",
                "oos_csv_paths": [str(oos_csv)],
            }
        ],
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Lock file (so gate 5 passes).
    from train_selection_lock import write_train_selection_lock  # type: ignore

    lock_path = run_dir / "train_selection_lock.json"
    # Hand-write so committed_utc is in the past (ahead of OOS CSV mtime which we set below).
    lock_payload = {
        "fold_id": "1",
        "expected_oos_csv_basename": "Silver_e395_sl140_tp33_NYExt_oos.csv",
        "train_selection_committed_utc": (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat(),
        "committed_utc": (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat(),
        "selected_config_id": "Silver_e395_sl140_tp33_NYExt_train",
        "selection_status": "OK",
        "constraint_floors": {"DD_max": 8.0, "WR_min": 15.0, "trades_min": 50},
        "tie_break_applied": None,
        "candidate_count": 1,
        "grid_hash": grid_h,
        "fold_spec_hash": fold_h,
    }
    lock_path.write_text(json.dumps(lock_payload, indent=2), encoding="utf-8")

    out = report.emit_reports(run_dir, comparator_dir=comparator_dir)
    assert out["mode"] == "full"
    # All 12 §14 gate slots present.
    gate_ids = set(out["gates"].keys())
    expected_ids = {
        "1_grid_hash", "2_fold_spec_hash", "3_comparator_csv_sha256",
        "4_audit_ordering", "5_oos_matches_lock",
        "6_pf_min", "7_wr_min_pct", "8_dd_max_pct",
        "9_bootstrap_p05_pf", "10_half_panel_pf_ratio",
        "11_mfe_mae_ratio_min", "12_correlation",
    }
    assert gate_ids == expected_ids, f"missing/extra gates: {expected_ids ^ gate_ids}"
    # Disposition is one of the three verdicts.
    assert out["disposition"] in {"RESOLVED", "FALSIFIED", "AMBIGUOUS"}
    # §5.8 hygiene: verdict not written to artifacts.
    md = (run_dir / "report.md").read_text(encoding="utf-8")
    rj = (run_dir / "report.json").read_text(encoding="utf-8")
    assert "DISPOSITION: " not in md and "DISPOSITION: " not in rj
    for verdict in ("RESOLVED", "FALSIFIED", "AMBIGUOUS"):
        assert verdict not in md, f"{verdict} leaked into report.md"
        assert verdict not in rj, f"{verdict} leaked into report.json"

    # Gate 1/2/3 should pass (hashes match, comparator sha in SHA256SUMS).
    assert out["gates"]["1_grid_hash"]["pass"] is True
    assert out["gates"]["2_fold_spec_hash"]["pass"] is True
    assert out["gates"]["3_comparator_csv_sha256"]["pass"] is True


def test_emit_reports_full_mode_falsifies_on_correlation(tmp_path):
    """Identical-comparator setup → ρ=1.0 → gate 12 fails → FALSIFIED."""
    sys.path.insert(0, str(WFO))
    import report  # type: ignore
    from grid_hash import fold_spec_hash_from_path, grid_hash_from_path  # type: ignore

    run_dir = tmp_path / "rho_high"
    run_dir.mkdir()
    shutil.copy(EXAMPLES / "grid.json", run_dir / "grid.json")
    shutil.copy(EXAMPLES / "fold_spec.json", run_dir / "fold_spec.json")

    comparator_dir = tmp_path / "tv_exports"
    comparator_dir.mkdir()
    cmp_csv = comparator_dir / "Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_rho1.csv"
    # Comparator and OOS share an identical *varying* pattern → ρ=1.0.
    cmp_sha = _write_minimal_pnl_csv(
        cmp_csv, n_days=200, daily_pnl=200.0, start="2025-06-01", pattern="sin"
    )
    (comparator_dir / "SHA256SUMS").write_text(
        f"{cmp_sha} *{cmp_csv.name}\n", encoding="utf-8"
    )

    oos_csv = run_dir / "Silver_e395_sl140_tp33_NYExt_oos.csv"
    _write_minimal_pnl_csv(
        oos_csv, n_days=200, daily_pnl=200.0, start="2025-06-01", pattern="sin"
    )

    grid_h = grid_hash_from_path(run_dir / "grid.json")
    fold_h = fold_spec_hash_from_path(run_dir / "fold_spec.json")

    past = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    manifest = {
        "run_id": "rho1",
        "grid_hash": grid_h, "fold_spec_hash": fold_h,
        "comparator_csv_sha256": cmp_sha,
        "bootstrap_seed": 42, "bootstrap_n_panels": 50,
        "ingests": [
            {
                "phase": "oos",
                "config_id": "Silver_e395_sl140_tp33_NYExt_oos",
                "path": str(oos_csv),
                "metrics": {"n_trades": 80, "pf": 2.0, "wr_pct": 22.0, "max_dd_pct": 4.0, "mfe_mae_ratio": 3.0},
            },
        ],
        "folds": [
            {
                "fold_id": "1",
                "train_selection_committed_utc": past,
                "expected_oos_csv_basename": "Silver_e395_sl140_tp33_NYExt_oos.csv",
                "oos_csv_paths": [str(oos_csv)],
            }
        ],
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (run_dir / "train_selection_lock.json").write_text(json.dumps({
        "fold_id": "1",
        "expected_oos_csv_basename": "Silver_e395_sl140_tp33_NYExt_oos.csv",
        "train_selection_committed_utc": past,
        "committed_utc": past,
        "selected_config_id": "Silver_e395_sl140_tp33_NYExt_train",
        "selection_status": "OK",
    }), encoding="utf-8")

    out = report.emit_reports(run_dir, comparator_dir=comparator_dir)
    assert out["mode"] == "full"
    assert out["gates"]["12_correlation"]["value"] == pytest.approx(1.0, abs=1e-6)
    assert out["disposition"] == "FALSIFIED"
