"""Q-CORR-1.2 Seam #3 closure-note skeleton generator tests."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
WFO = REPO / "scripts" / "wfo"
EXAMPLES = WFO / "examples"


def _bootstrap_run_dir(tmp_path: Path, *, with_report: bool = True, mode: str = "full") -> Path:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    shutil.copy(EXAMPLES / "grid.json", run_dir / "grid.json")
    shutil.copy(EXAMPLES / "fold_spec.json", run_dir / "fold_spec.json")
    manifest = {
        "run_id": "closure_test_run",
        "grid_hash": "a8fdd34e800f312e6c064a595ee9ae3565472d0da0a0990348e07d28076f85b1",
        "fold_spec_hash": "5591f024515f422548bf9e60a7f23225e559a05346e8911e6397346acad6673e",
        "comparator_csv_sha256": "e38e8fe80419a286666898e8cae41a3be796277844367b7f1dfdcc3a0feba124",
        "bootstrap_seed": 42,
        "bootstrap_n_panels": 1000,
        "ingests": [], "folds": [],
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    if with_report:
        if mode == "full":
            report = {
                "run_id": "closure_test_run",
                "grid_hash": manifest["grid_hash"],
                "fold_spec_hash": manifest["fold_spec_hash"],
                "status": "full_oos",
                "n_train_ingests": 250,
                "oos": {
                    "config_id": "Silver_e395_sl140_tp33_NYExt_oos",
                    "metrics": {"n_trades": 80, "pf": 2.0, "wr_pct": 22.0, "max_dd_pct": 4.0, "mfe_mae_ratio": 3.0},
                },
                "gates": {
                    "6_pf_min": {"pass": True, "value": 2.0, "threshold": 1.5},
                    "12_correlation": {"pass": True, "value": 0.05, "threshold_resolved": 0.10},
                },
            }
        elif mode == "stub":
            report = {"run_id": "closure_test_run", "status": "stub_no_metrics"}
        else:
            report = {"run_id": "closure_test_run", "status": "train_only", "n_train_ingests": 25}
        (run_dir / "report.json").write_text(json.dumps(report), encoding="utf-8")
    return run_dir


def test_closure_note_full_mode_contains_all_sections(tmp_path):
    sys.path.insert(0, str(WFO))
    from closure_note import build_skeleton  # type: ignore

    run_dir = _bootstrap_run_dir(tmp_path, mode="full")
    md = build_skeleton(run_dir)

    # Top-of-file structure
    assert "# Q-CORR-1.2 — Closure Note (DRAFT skeleton)" in md
    assert "CLOSED-<DISPOSITION>" in md  # placeholder per §5.8
    assert "<DISPOSITION: RESOLVED | FALSIFIED | AMBIGUOUS" in md
    # Run metadata
    assert "closure_test_run" in md
    assert "a8fdd34e" in md  # grid hash
    assert "5591f024" in md  # fold_spec hash
    assert "e38e8fe8" in md  # comparator sha
    # OOS section
    assert "Silver_e395_sl140_tp33_NYExt_oos" in md
    assert "n_trades" in md
    # Gate evidence
    assert "6_pf_min" in md and "12_correlation" in md
    # §17 all-branches structure
    assert "§4.A — If RESOLVED" in md
    assert "§4.B — If FALSIFIED" in md
    assert "§4.C — If AMBIGUOUS" in md
    # §17 specific action items
    assert "docs/notes/q-corr-1-hint-log.md" in md
    assert "docs/rejected_candidates.md" in md
    # Audit-hook attestations
    assert "audit_path_b_ordering.py" in md
    assert "grid_hash.py" in md


def test_closure_note_stub_mode_no_oos_section_data(tmp_path):
    sys.path.insert(0, str(WFO))
    from closure_note import build_skeleton  # type: ignore

    run_dir = _bootstrap_run_dir(tmp_path, mode="stub")
    md = build_skeleton(run_dir)
    # Stub mode has no OOS — but the skeleton itself should still render.
    assert "_No OOS metrics — train-only or stub run._" in md
    assert "_No §14 gates evaluated" in md
    # Disposition placeholder still present.
    assert "<DISPOSITION:" in md


def test_closure_note_train_only_mode(tmp_path):
    sys.path.insert(0, str(WFO))
    from closure_note import build_skeleton  # type: ignore

    run_dir = _bootstrap_run_dir(tmp_path, mode="train_only")
    md = build_skeleton(run_dir)
    assert "train_only" in md.lower() or "_No OOS metrics" in md


def test_closure_note_compliance_with_section_5_8_no_verdict_baked_in(tmp_path):
    """§5.8 hygiene: skeleton MUST NOT bake in a disposition verdict.

    The disposition is hand-filled by Joshua from emit-reports stdout. The
    skeleton may mention the three verdicts by name (in the §17 branches and
    the placeholder), but no statement should ASSERT a verdict.
    """
    sys.path.insert(0, str(WFO))
    from closure_note import build_skeleton  # type: ignore

    run_dir = _bootstrap_run_dir(tmp_path, mode="full")
    md = build_skeleton(run_dir)
    # Placeholder must be present (operator hand-fills).
    assert "<DISPOSITION: RESOLVED | FALSIFIED | AMBIGUOUS" in md
    # No standalone assertion of disposition (e.g., "Disposition: RESOLVED").
    bad_patterns = [
        "Disposition: RESOLVED",
        "Disposition: FALSIFIED",
        "Disposition: AMBIGUOUS",
        "CLOSED-RESOLVED",
        "CLOSED-FALSIFIED",
        "CLOSED-AMBIGUOUS",
    ]
    for p in bad_patterns:
        assert p not in md, f"§5.8 violation: skeleton bakes in {p!r}"


def test_closure_note_cli_writes_default_path(tmp_path):
    import subprocess

    run_dir = _bootstrap_run_dir(tmp_path, mode="full")
    cmd = [
        sys.executable,
        str(WFO / "closure_note.py"),
        "--run-dir",
        str(run_dir),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))
    assert r.returncode == 0, f"stderr={r.stderr}"
    default_path = run_dir / "closure_note_DRAFT.md"
    assert default_path.is_file()
    body = default_path.read_text(encoding="utf-8")
    assert "Q-CORR-1.2" in body


def test_closure_note_cli_missing_manifest_fails(tmp_path):
    import subprocess

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    cmd = [
        sys.executable,
        str(WFO / "closure_note.py"),
        "--run-dir",
        str(empty_dir),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))
    assert r.returncode == 1
    assert "no run_manifest.json" in r.stderr
