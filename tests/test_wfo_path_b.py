"""Smoke tests for scripts/wfo Path B helpers."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
WFO = REPO / "scripts" / "wfo"
EXAMPLES = WFO / "examples"


def test_grid_hash_stable():
    sys.path.insert(0, str(WFO))
    import grid_hash  # noqa: E402

    h1 = grid_hash.grid_hash_from_path(EXAMPLES / "grid.json")
    h2 = grid_hash.grid_hash_from_path(EXAMPLES / "grid.json")
    assert h1 == h2
    assert len(h1) == 64


def test_init_run_and_audit(tmp_path):
    run_dir = tmp_path / "run0"
    sha = "f" * 64
    cmd = [
        sys.executable,
        str(WFO / "run_path_b.py"),
        "init-run",
        "--run-id",
        "test_run",
        "--grid",
        str(EXAMPLES / "grid.json"),
        "--fold-spec",
        str(EXAMPLES / "fold_spec.json"),
        "--out-dir",
        str(run_dir),
        "--comparator-sha256",
        sha,
    ]
    subprocess.run(cmd, check=True, cwd=str(REPO))
    manifest = run_dir / "run_manifest.json"
    assert manifest.is_file()
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["grid_hash"]
    assert (run_dir / "report.md").is_file()

    audit = [
        sys.executable,
        str(WFO / "audit_path_b_ordering.py"),
        str(manifest),
    ]
    subprocess.run(audit, check=True, cwd=str(REPO))


def test_audit_detects_oos_before_commit(tmp_path):
    oos = tmp_path / "oos.csv"
    oos.write_text("stub", encoding="utf-8")
    past = "2020-01-01T00:00:00Z"
    old = time.mktime((1999, 1, 1, 0, 0, 0, 0, 0, -1))
    try:
        import os

        os.utime(oos, (old, old))
    except OSError:
        pytest.skip("cannot set utime on this platform")

    manifest = {
        "folds": [
            {
                "fold_id": "f1",
                "train_selection_committed_utc": past,
                "oos_csv_paths": [str(oos.resolve())],
            }
        ]
    }
    mp = tmp_path / "run_manifest.json"
    mp.write_text(json.dumps(manifest), encoding="utf-8")
    audit = [
        sys.executable,
        str(WFO / "audit_path_b_ordering.py"),
        str(mp),
    ]
    r = subprocess.run(audit, cwd=str(REPO))
    assert r.returncode == 1


def test_train_selection_lock(tmp_path):
    sys.path.insert(0, str(WFO))
    import train_selection_lock  # noqa: E402

    lockp = tmp_path / "lock.json"
    train_selection_lock.write_train_selection_lock(
        lockp,
        fold_id="1",
        expected_oos_csv_basename="Guardian_Silver_v1_PEPPERSTONE_XAGUSD_2026-05-13_deadbeef.csv",
    )
    oos = tmp_path / "Guardian_Silver_v1_PEPPERSTONE_XAGUSD_2026-05-13_deadbeef.csv"
    oos.write_text("x", encoding="utf-8")
    train_selection_lock.assert_oos_matches_lock(oos, lockp)
    bad = tmp_path / "wrong.csv"
    bad.write_text("y", encoding="utf-8")
    with pytest.raises(AssertionError):
        train_selection_lock.assert_oos_matches_lock(bad, lockp)
