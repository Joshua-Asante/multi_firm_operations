"""Tests for lib.regime_bootstrap (daily P&L block bootstrap)."""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lib.correlation import load_exit_date_daily_net
from lib.regime_bootstrap import regime_bootstrap_daily_pnl


def test_regime_bootstrap_reproducible():
    rng = np.random.default_rng(7)
    idx = pd.bdate_range("2020-01-01", periods=260, freq="C")
    daily = pd.Series(rng.normal(0, 50, size=len(idx)), index=idx)
    a = regime_bootstrap_daily_pnl(daily, n_panels=30, seed=123)
    b = regime_bootstrap_daily_pnl(daily, n_panels=30, seed=123)
    assert a.p05_pf == b.p05_pf
    assert a.n_blocks >= 1


def test_silver_bootstrap_p05_optional():
    """Wide sanity band when Silver TV export supplied via env."""
    p = os.environ.get("Q_CORR_SILVER_TV_CSV")
    if not p:
        pytest.skip("Q_CORR_SILVER_TV_CSV unset (Silver Guardian TV export).")
    path = Path(p)
    if not path.is_file():
        pytest.skip(f"missing {path}")
    daily = load_exit_date_daily_net(path)
    res = regime_bootstrap_daily_pnl(daily, n_panels=100, seed=20260513)
    assert 0.5 < res.p05_pf < 1.8, res.p05_pf
