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
    """Q-CORR-1.2 §15 historical anchor: p05_pf ≈ 1.05 ± 0.02 at the pinned params.

    Brief §15's 1.05 ± 0.02 reproduces against the Q-CORR-1.1 v5.5-on-Silver CSV
    only at (bootstrap_seed=7, bootstrap_n_panels=100, block_months=6). These are
    historical-anchor parameters; distinct from the §14 Gate 9 disposition
    convention (canonical bootstrap_seed=42, bootstrap_n_panels=1000 — orchestration
    metadata recorded in run_manifest.json at init-run per
    docs/spec/wfo-runner-v0.md §2).
    """
    p = os.environ.get("Q_CORR_SILVER_TV_CSV")
    if not p:
        pytest.skip("Q_CORR_SILVER_TV_CSV unset (Silver Guardian TV export).")
    path = Path(p)
    if not path.is_file():
        pytest.skip(f"missing {path}")
    daily = load_exit_date_daily_net(path)
    res = regime_bootstrap_daily_pnl(daily, n_panels=100, seed=7, block_months=6)
    assert abs(res.p05_pf - 1.05) <= 0.02, (
        f"§15 historical anchor drift: p05_pf={res.p05_pf:.4f}, expected 1.05 ± 0.02 "
        f"(seed=7, n_panels=100, block_months=6)"
    )
