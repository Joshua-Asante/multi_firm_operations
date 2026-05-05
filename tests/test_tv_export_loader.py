"""Smoke tests for the TV-export loader across all four canonical Pepperstone panels.

Pyramid-aware test added 2026-05-05 alongside Striker NAS100 v1 add. Confirms:
- All four strategies load without identity / pairing / side errors.
- `leg_type` column splits correctly between `base` and `pyramid_add`.
- Per-strategy trade counts match brief-stated panel sizes.
"""
from pathlib import Path

import pytest

from analysis.oanda_stage1.tv_export_loader import load_tv_export


PEPPERSTONE_DIR = Path(__file__).resolve().parent.parent / "data" / "tv_exports" / "pepperstone"


@pytest.mark.parametrize(
    "csv_name, strategy, version, symbol, n_trades, n_base, n_pyramid",
    [
        (
            "Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-04-26_87e73.csv",
            "Guardian", "v5.5", "XAUUSD", 209, 209, 0,
        ),
        (
            "Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv",
            "Striker", "v4.5", "US30", 224, 197, 27,
        ),
        (
            "Aegis_USDJPY_v4.3_PEPPERSTONE_USDJPY_2026-04-26_0bf1b.csv",
            "Aegis", "v4.3", "USDJPY", 123, 123, 0,
        ),
        (
            "Striker_NAS100_v1_PEPPERSTONE_NAS100_2026-05-05_7ca6f.csv",
            "Striker", "v1", "NAS100", 200, 166, 34,
        ),
    ],
)
def test_pepperstone_loader(csv_name, strategy, version, symbol, n_trades, n_base, n_pyramid):
    path = PEPPERSTONE_DIR / csv_name
    df = load_tv_export(
        path,
        expected_strategy=strategy,
        expected_version=version,
        expected_symbol=symbol,
        expected_broker="PEPPERSTONE",
    )
    assert len(df) == n_trades, f"{csv_name}: expected {n_trades} trades, got {len(df)}"

    counts = df["leg_type"].value_counts().to_dict()
    assert counts.get("base", 0) == n_base, f"{csv_name}: base count {counts.get('base', 0)} != {n_base}"
    assert counts.get("pyramid_add", 0) == n_pyramid, f"{csv_name}: pyramid count {counts.get('pyramid_add', 0)} != {n_pyramid}"

    assert (df["side"] == 1).all(), f"{csv_name}: non-long rows present"
