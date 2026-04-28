"""
Nonlinear time-series measures (Hurst).

Thin wrapper over `nolds` that enforces input-shape correctness at the
boundary. The guard exists to encode a real bug we hit:

  feedback_hurst_rs_log_prices_trap.md (memory): R/S Hurst on log-prices
  silently returns H ≈ 1 — a diagnostic for the bug, not a real
  measurement. The fix is to pass log returns (np.diff(np.log(prices))),
  not log-prices.

The guard converts that silent-trap class into a loud failure.
"""

from __future__ import annotations

import numpy as np


def _looks_like_price_series(x: np.ndarray) -> bool:
    """Heuristic: returns are stationary I(0); prices are unit-root I(1).

    This is an I(1)-vs-I(0) discriminator dressed up as a one-liner:
      - I(1) (prices, unit root): variance grows in t. After N steps,
        std(x) ≈ std(diff(x)) · √N. The accumulation is the signature.
      - I(0) (returns, stationary): variance is constant in t.
        std(x) ≈ std(diff(x)) (ratio ≈ 0.7 for Gaussian, since diff of
        independent Gaussians has variance 2σ²).

    Threshold std(x)/std(diff(x)) > 5 cleanly separates: an N=10K random
    walk has ratio ≈ 100, while stationary returns rarely exceed 1
    (would require pathological outliers). Short series (<100) abstain.

    DO NOT "simplify" this back to a drift check (|mean(diff)| > k·std(diff)).
    A random-walk price series has zero-mean diffs *by construction* — its
    diffs ARE the underlying returns. The drift heuristic fires on biased
    returns and silently misses the canonical price-series shape, exactly
    inverting what the guard needs to do. The series itself must be inspected,
    not just its diffs. test_log_prices_raises_via_guard pins this.
    """
    if len(x) < 100:
        return False  # too short to discriminate reliably
    diffs = np.diff(x)
    noise = float(np.std(diffs))
    if noise == 0:
        return True  # constant series — degenerate
    series_std = float(np.std(x))
    return series_std / noise > 5.0


def hurst_rs(returns: np.ndarray) -> float:
    """R/S Hurst exponent of a returns series.

    Wraps nolds.hurst_rs with a boundary guard. Pass log returns
    (np.diff(np.log(prices))), NOT log-prices — the latter triggers the
    trap documented in feedback_hurst_rs_log_prices_trap.md.
    """
    arr = np.asarray(returns, dtype=float)
    if _looks_like_price_series(arr):
        raise ValueError(
            "hurst_rs got a price-like series (drift comparable to noise). "
            "Pass log returns (np.diff(np.log(prices))), not log-prices. "
            "See feedback_hurst_rs_log_prices_trap.md."
        )
    import nolds  # lazy: only required when this function is called
    return float(nolds.hurst_rs(arr))
