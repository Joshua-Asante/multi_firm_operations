"""Tests for lib.correlation (zero-fill daily Pearson)."""
from pathlib import Path

import pandas as pd
import pytest

from lib.correlation import (
    align_two_daily_series_zero_fill,
    pearson_daily_pnl,
    pearson_daily_series,
)

PEPPERSTONE_DIR = Path(__file__).resolve().parent.parent / "data" / "tv_exports" / "pepperstone"


def test_align_zero_fill_inserts_zeros():
    s1 = pd.Series([1.0, 2.0], index=pd.to_datetime(["2020-01-02", "2020-01-03"]))
    s2 = pd.Series([3.0], index=pd.to_datetime(["2020-01-03"]))
    x, y = align_two_daily_series_zero_fill(s1, s2)
    assert len(x) == 2
    assert float(x.iloc[0]) == 1.0
    assert float(y.iloc[0]) == 0.0
    assert float(y.iloc[1]) == 3.0


def test_pearson_daily_series_weak_corr():
    rng = pd.date_range("2022-01-01", periods=100, freq="B")
    a = pd.Series(rng.dayofweek.astype(float), index=rng)
    b = pd.Series((rng.dayofweek * 0.1 + 0.01).astype(float), index=rng)
    r = pearson_daily_series(a, b)
    assert r > 0.9


@pytest.mark.parametrize(
    "dj_name,nas_name,expected_rho",
    [
        (
            "Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv",
            "Striker_NAS100_v1_PEPPERSTONE_NAS100_2026-05-05_7ca6f.csv",
            0.021704118183897454,
        ),
    ],
)
def test_pearson_daily_pnl_dj_nas_anchor(dj_name, nas_name, expected_rho):
    dj = PEPPERSTONE_DIR / dj_name
    nas = PEPPERSTONE_DIR / nas_name
    if not dj.exists() or not nas.exists():
        pytest.skip("Pepperstone DJ30/NAS CSVs not present (gitignored vendor data).")
    rho = pearson_daily_pnl(dj, nas)
    assert abs(rho - expected_rho) < 1e-3, rho
    x = rho + 0.10
    assert abs(x - 0.12170411818389745) < 2e-3
