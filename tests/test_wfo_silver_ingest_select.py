"""Q-CORR-1.2 Silver filename parser and WFO ingest/select wiring."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
WFO = REPO / "scripts" / "wfo"
EXAMPLES = WFO / "examples"
PEPPERSTONE_DIR = REPO / "data" / "tv_exports" / "pepperstone"


def test_silver_filename_roundtrip():
    sys.path.insert(0, str(WFO))
    import silver_filename  # noqa: E402

    name = silver_filename.format_silver_basename(
        ema_slow_len=395,
        stop_atr=1.4,
        tp_atr=33,
        session="NY_Extended",
        phase="train",
    )
    assert name == "Silver_e395_sl140_tp33_NYExt_train.csv"
    p = silver_filename.parse_silver_export_basename(name)
    assert p["ema_slow_len"] == 395
    assert abs(p["stop_atr"] - 1.4) < 1e-9
    assert p["tp_atr"] == 33
    assert p["session"] == "NY_Extended"
    assert p["phase"] == "train"


def test_expected_oos_basename():
    sys.path.insert(0, str(WFO))
    from silver_filename import expected_oos_basename  # noqa: E402

    assert (
        expected_oos_basename("Silver_e395_sl140_tp33_NYExt_train.csv")
        == "Silver_e395_sl140_tp33_NYExt_oos.csv"
    )


@pytest.fixture()
def run_with_manifest(tmp_path):
    run_dir = tmp_path / "r1"
    run_dir.mkdir()
    shutil.copy(EXAMPLES / "grid.json", run_dir / "grid.json")
    shutil.copy(EXAMPLES / "fold_spec.json", run_dir / "fold_spec.json")
    manifest = {
        "run_id": "t",
        "ingests": [
            {
                "basename": "Silver_e395_sl140_tp33_NYExt_train.csv",
                "phase": "train",
                "config_id": "Silver_e395_sl140_tp33_NYExt_train",
                "metrics": {
                    "n_trades": 60,
                    "pf": 1.4,
                    "wr_pct": 16.0,
                    "max_dd_pct": 7.0,
                    "mfe_mae_ratio": 3.0,
                },
            },
            {
                "basename": "Silver_e395_sl155_tp29_NYExt_train.csv",
                "phase": "train",
                "config_id": "Silver_e395_sl155_tp29_NYExt_train",
                "metrics": {
                    "n_trades": 55,
                    "pf": 1.6,
                    "wr_pct": 18.0,
                    "max_dd_pct": 6.0,
                    "mfe_mae_ratio": 2.5,
                },
            },
            {
                "basename": "Silver_e450_sl175_tp25_LdnNY_train.csv",
                "phase": "train",
                "config_id": "Silver_e450_sl175_tp25_LdnNY_train",
                "metrics": {
                    "n_trades": 80,
                    "pf": 1.6,
                    "wr_pct": 20.0,
                    "max_dd_pct": 5.0,
                    "mfe_mae_ratio": 2.1,
                },
            },
        ],
        "folds": [],
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return run_dir


def test_select_prefers_lower_dd_at_equal_pf(run_with_manifest):
    sys.path.insert(0, str(WFO))
    import operations  # noqa: E402

    out = operations.select_train_fold(run_with_manifest, fold_id="1")
    assert out["selected"]["config_id"] == "Silver_e450_sl175_tp25_LdnNY_train"
    lock = json.loads((run_with_manifest / "train_selection_lock.json").read_text(encoding="utf-8"))
    assert lock["expected_oos_csv_basename"] == "Silver_e450_sl175_tp25_LdnNY_oos.csv"
    assert "train_selection_committed_utc" in lock


def test_ingest_guardian_renamed_silver_train(tmp_path):
    src = PEPPERSTONE_DIR / "Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-05_33781.csv"
    if not src.is_file():
        pytest.skip("Pepperstone Guardian CSV not present")
    sys.path.insert(0, str(WFO))
    import operations  # noqa: E402

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    shutil.copy(EXAMPLES / "grid.json", run_dir / "grid.json")
    shutil.copy(EXAMPLES / "fold_spec.json", run_dir / "fold_spec.json")
    manifest = {
        "run_id": "ingest_smoke",
        "ingests": [],
        "folds": [],
        "grid_hash": "x",
        "fold_spec_hash": "y",
        "comparator_csv_sha256": "z" * 64,
        "seed": 1,
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    dst = run_dir / "Silver_e395_sl140_tp33_NYExt_train.csv"
    shutil.copy(src, dst)

    row = operations.ingest_tv_csv(
        run_dir,
        dst,
        min_raw_rows=100,
        min_trades=50,
        max_trades=500,
    )
    assert row["phase"] == "train"
    assert row["metrics"]["n_trades"] >= 50
    data = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert len(data["ingests"]) == 1


# ---------------------------------------------------------------------------
# Q-CORR-1.2 seam-1 handoff: extended lock schema + NO_CANDIDATE + §4 acceptance
# ---------------------------------------------------------------------------


def _synth_train_row(config_id: str, *, n: int, pf: float, wr: float, dd: float, mfe_mae: float = 3.0) -> dict:
    return {
        "basename": f"{config_id}.csv",
        "phase": "train",
        "config_id": config_id,
        "metrics": {
            "n_trades": n,
            "pf": pf,
            "wr_pct": wr,
            "max_dd_pct": dd,
            "mfe_mae_ratio": mfe_mae,
        },
    }


def _bootstrap_manifest(run_dir, ingests, *, grid_hash="a" * 64, fold_spec_hash="b" * 64):
    import shutil

    run_dir.mkdir(exist_ok=True)
    shutil.copy(EXAMPLES / "grid.json", run_dir / "grid.json")
    shutil.copy(EXAMPLES / "fold_spec.json", run_dir / "fold_spec.json")
    manifest = {
        "run_id": "t",
        "grid_hash": grid_hash,
        "fold_spec_hash": fold_spec_hash,
        "ingests": ingests,
        "folds": [],
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_extended_lock_schema_fields(tmp_path):
    sys.path.insert(0, str(WFO))
    import operations  # noqa: E402

    run_dir = tmp_path / "ext"
    rows = [
        _synth_train_row("Silver_e395_sl140_tp33_NYExt_train", n=60, pf=1.4, wr=16.0, dd=7.0),
        _synth_train_row("Silver_e395_sl155_tp29_NYExt_train", n=55, pf=1.6, wr=18.0, dd=6.0),
        _synth_train_row("Silver_e450_sl175_tp25_LdnNY_train", n=80, pf=1.6, wr=20.0, dd=5.0),
    ]
    _bootstrap_manifest(
        run_dir, rows,
        grid_hash="a8fdd34e800f312e6c064a595ee9ae3565472d0da0a0990348e07d28076f85b1",
        fold_spec_hash="5591f024515f422548bf9e60a7f23225e559a05346e8911e6397346acad6673e",
    )

    out = operations.select_train_fold(run_dir, fold_id="1")
    lock = json.loads((run_dir / "train_selection_lock.json").read_text(encoding="utf-8"))

    assert lock["selection_status"] == "OK"
    assert lock["constraint_floors"] == {"DD_max": 8.0, "WR_min": 15.0, "trades_min": 50}
    assert lock["candidate_count"] == 3
    assert lock["grid_hash"] == "a8fdd34e800f312e6c064a595ee9ae3565472d0da0a0990348e07d28076f85b1"
    assert lock["fold_spec_hash"] == "5591f024515f422548bf9e60a7f23225e559a05346e8911e6397346acad6673e"
    # PF tie between #2 (1.6/dd=6) and #3 (1.6/dd=5) → dd breaks → tie_break_applied=["pf_tie"]
    assert lock["tie_break_applied"] == ["pf_tie"]
    assert out["tie_break_applied"] == ["pf_tie"]


def test_no_candidate_writes_lock_and_raises(tmp_path):
    sys.path.insert(0, str(WFO))
    import operations  # noqa: E402

    run_dir = tmp_path / "noc"
    rows = [
        _synth_train_row("Silver_e395_sl140_tp33_NYExt_train", n=20, pf=2.0, wr=22.0, dd=4.0),  # trades<50
        _synth_train_row("Silver_e395_sl155_tp29_NYExt_train", n=60, pf=1.4, wr=10.0, dd=6.0),  # WR<15
        _synth_train_row("Silver_e450_sl175_tp25_LdnNY_train", n=80, pf=1.6, wr=22.0, dd=12.0),  # DD>8
    ]
    _bootstrap_manifest(run_dir, rows)

    with pytest.raises(ValueError, match="NO_CANDIDATE"):
        operations.select_train_fold(run_dir, fold_id="1")
    lock = json.loads((run_dir / "train_selection_lock.json").read_text(encoding="utf-8"))
    assert lock["selection_status"] == "NO_CANDIDATE"
    assert lock["candidate_count"] == 0
    assert lock["selected_config_id"] == ""


def test_no_tie_break_when_unique_pf(tmp_path):
    sys.path.insert(0, str(WFO))
    import operations  # noqa: E402

    run_dir = tmp_path / "unique"
    rows = [
        _synth_train_row("Silver_e395_sl140_tp33_NYExt_train", n=60, pf=1.4, wr=16.0, dd=7.0),
        _synth_train_row("Silver_e395_sl155_tp29_NYExt_train", n=55, pf=1.6, wr=18.0, dd=6.0),
        _synth_train_row("Silver_e450_sl175_tp25_LdnNY_train", n=80, pf=2.0, wr=20.0, dd=5.0),
    ]
    _bootstrap_manifest(run_dir, rows)
    operations.select_train_fold(run_dir, fold_id="1")
    lock = json.loads((run_dir / "train_selection_lock.json").read_text(encoding="utf-8"))
    assert lock["tie_break_applied"] is None
    assert lock["selected_config_id"] == "Silver_e450_sl175_tp25_LdnNY_train"


def test_section_4_synthetic_winner(tmp_path):
    """Q-CORR-1.2 handoff §4 acceptance hypothesis: 250-row sweep, single feasible row."""
    sys.path.insert(0, str(WFO))
    import operations  # noqa: E402

    run_dir = tmp_path / "s4"
    # Build 249 rows that each fail at least one constraint, plus 1 winner.
    rows = []
    # 249 failers, each different config_id, alternating failure modes.
    for i in range(249):
        fail_mode = i % 3
        if fail_mode == 0:
            metrics = {"n_trades": 30, "pf": 3.0, "wr_pct": 22.0, "max_dd_pct": 5.0, "mfe_mae_ratio": 3.0}
        elif fail_mode == 1:
            metrics = {"n_trades": 80, "pf": 3.0, "wr_pct": 10.0, "max_dd_pct": 5.0, "mfe_mae_ratio": 3.0}
        else:
            metrics = {"n_trades": 80, "pf": 3.0, "wr_pct": 22.0, "max_dd_pct": 12.0, "mfe_mae_ratio": 3.0}
        rows.append({
            "basename": f"Silver_e395_sl140_tp{15 + i % 5}_NYExt_train_{i:03d}.csv",
            "phase": "train",
            "config_id": f"loser_{i:03d}",
            "metrics": metrics,
        })
    rows.append({
        "basename": "Silver_e395_sl140_tp33_NYExt_train.csv",
        "phase": "train",
        "config_id": "synthetic_winner",
        "metrics": {"n_trades": 80, "pf": 3.0, "wr_pct": 22.0, "max_dd_pct": 5.0, "mfe_mae_ratio": 3.0},
    })
    _bootstrap_manifest(run_dir, rows)
    out = operations.select_train_fold(run_dir, fold_id="1")
    assert out["selected"]["config_id"] == "synthetic_winner"
    assert out["candidate_count"] == 1
    assert out["tie_break_applied"] is None
    lock = json.loads((run_dir / "train_selection_lock.json").read_text(encoding="utf-8"))
    assert lock["candidate_count"] == 1
    assert lock["selection_status"] == "OK"


def test_batch_ingest_empty_dir_returns_nonzero(tmp_path):
    """cmd_ingest with empty dir → batch_count=0, exit 1."""
    import subprocess

    run_dir = tmp_path / "run"
    cmd = [
        sys.executable,
        str(WFO / "run_path_b.py"),
        "init-run",
        "--run-id",
        "batch_empty",
        "--grid",
        str(EXAMPLES / "grid.json"),
        "--fold-spec",
        str(EXAMPLES / "fold_spec.json"),
        "--out-dir",
        str(run_dir),
        "--comparator-sha256",
        "f" * 64,
    ]
    subprocess.run(cmd, check=True, cwd=str(REPO))

    empty_dir = tmp_path / "no_csvs"
    empty_dir.mkdir()
    ingest_cmd = [
        sys.executable,
        str(WFO / "run_path_b.py"),
        "ingest",
        "--run-dir",
        str(run_dir),
        "--csv",
        str(empty_dir),
    ]
    r = subprocess.run(ingest_cmd, capture_output=True, text=True, cwd=str(REPO))
    assert r.returncode == 1
    assert "batch_count" in r.stdout and "0" in r.stdout


def test_section_12_grid_contains_v15_hint_and_v55_reference():
    """Q-CORR-1.2 §15 Conceptual sanity: v1.5 hint + v5.5 reference are in the Cartesian product."""
    grid = json.loads((EXAMPLES / "grid.json").read_text(encoding="utf-8"))
    td = grid["tunable_dimensions"]
    # v1.5 hint anchor: ema=395, stop=1.4, tp=33, session=NY_Extended
    assert 395 in td["ema_slow_len"], "v1.5 hint ema_slow=395 missing"
    assert 1.4 in td["stop_atr"], "v1.5 hint stop_atr=1.4 missing"
    assert 33 in td["tp_atr"], "v1.5 hint tp_atr=33 missing"
    assert "NY_Extended" in td["session"], "v1.5 hint session=NY_Extended missing"
    # v5.5 reference anchor: ema=385, stop=1.55, tp=29, session=NY_Extended
    assert 385 in td["ema_slow_len"], "v5.5 ref ema_slow=385 missing"
    assert 1.55 in td["stop_atr"], "v5.5 ref stop_atr=1.55 missing"
    assert 29 in td["tp_atr"], "v5.5 ref tp_atr=29 missing"
    # Cartesian product is 5x5x5x2 = 250
    expected_count = (
        len(td["ema_slow_len"]) * len(td["stop_atr"]) * len(td["tp_atr"]) * len(td["session"])
    )
    assert expected_count == 250
    assert grid["expected_config_count"] == 250


def test_section_13_fold_window_pinned():
    """§15 Conceptual sanity: fold spec date window matches §13."""
    fold = json.loads((EXAMPLES / "fold_spec.json").read_text(encoding="utf-8"))
    assert fold["n_folds"] == 1
    assert fold["train_start"] == "2022-01-11"
    assert fold["train_end"] == "2025-05-10"
    assert fold["oos_start"] == "2025-05-11"
    assert fold["oos_end"] == "2026-04-20"


def test_batch_ingest_directory_dispatch(tmp_path):
    """Batch ingest finds *.csv files in a directory and routes each through ingest_tv_csv."""
    src = PEPPERSTONE_DIR / "Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-05_33781.csv"
    if not src.is_file():
        pytest.skip("Pepperstone Guardian CSV not present")

    sys.path.insert(0, str(WFO))
    import operations  # noqa: E402

    run_dir = tmp_path / "batch"
    run_dir.mkdir()
    shutil.copy(EXAMPLES / "grid.json", run_dir / "grid.json")
    shutil.copy(EXAMPLES / "fold_spec.json", run_dir / "fold_spec.json")
    manifest = {
        "run_id": "batch_smoke",
        "ingests": [],
        "folds": [],
        "grid_hash": "x", "fold_spec_hash": "y",
        "comparator_csv_sha256": "z" * 64, "seed": 1,
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    batch_dir = tmp_path / "csvs"
    batch_dir.mkdir()
    shutil.copy(src, batch_dir / "Silver_e395_sl140_tp33_NYExt_train.csv")

    # Drive cmd_ingest directly via subprocess to exercise the auto-detect branch.
    import subprocess
    r = subprocess.run(
        [
            sys.executable,
            str(WFO / "run_path_b.py"),
            "ingest",
            "--run-dir",
            str(run_dir),
            "--csv",
            str(batch_dir),
            "--min-trades", "50",
        ],
        capture_output=True, text=True, cwd=str(REPO),
        env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert r.returncode == 0, f"stderr={r.stderr}\nstdout={r.stdout}"
    data = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert len(data["ingests"]) == 1
    assert data["ingests"][0]["phase"] == "train"
