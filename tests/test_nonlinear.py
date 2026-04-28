"""Tests for lib/nonlinear.hurst_rs and the price-series boundary guard.

The guard encodes feedback_hurst_rs_log_prices_trap.md: R/S Hurst on
log-prices silently returns H >= 0.9. The wrapper converts that silent
trap into a loud failure.
"""

import numpy as np
import pytest

from lib.nonlinear import _looks_like_price_series, hurst_rs


def test_random_walk_returns_yields_hurst_near_half():
    """White-noise returns -> Hurst ≈ 0.5 (uncorrelated)."""
    rng = np.random.default_rng(42)
    returns = rng.standard_normal(10_000)
    h = hurst_rs(returns)
    assert 0.40 < h < 0.60, f"expected H ≈ 0.5 for random returns, got {h}"


def test_log_prices_raises_via_guard():
    """Cumulative random walk (price-like series) trips the guard."""
    rng = np.random.default_rng(42)
    log_prices = np.cumsum(rng.standard_normal(10_000))
    with pytest.raises(ValueError, match="price-like series"):
        hurst_rs(log_prices)


def test_biased_returns_pass_guard():
    """Positive-EV returns (drift << noise) must NOT trip the guard.

    A real trading strategy with a small positive expected R per trade
    is exactly this shape. False-positive here would block legitimate use.
    """
    rng = np.random.default_rng(42)
    returns = rng.standard_normal(10_000) + 0.01  # mean=0.01, std≈1
    h = hurst_rs(returns)
    assert 0.40 < h < 0.60


def test_short_series_does_not_trip_guard():
    """Series under 100 points: heuristic abstains rather than guess."""
    rng = np.random.default_rng(42)
    short_prices = np.cumsum(rng.standard_normal(50))  # would be price-like at length
    # Should not raise — len < 100, guard returns False unconditionally.
    assert _looks_like_price_series(short_prices) is False


def test_constant_series_treated_as_degenerate():
    """Zero-noise constant series: noise == 0 path -> guard fires."""
    arr = np.full(1000, 42.0)
    assert _looks_like_price_series(arr) is True
    with pytest.raises(ValueError):
        hurst_rs(arr)
