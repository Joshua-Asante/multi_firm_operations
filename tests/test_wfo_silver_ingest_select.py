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
