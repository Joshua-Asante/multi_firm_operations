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
    """Heuristic: returns are stationary, prices grow with √N.

    Discriminator is std(series) / std(diffs):
      - Stationary returns: std(x) ≈ std(diff(x)), ratio ≈ 0.7
      - Random-walk prices: std(x) ≈ std(diff(x)) * √N, ratio grows with length

    For N=10K random walk, ratio ≈ 100. For zero-mean returns, ratio ≈ 0.7.
    Threshold 5 cleanly separates: long stationary returns rarely exceed it
    (would require pathological outliers), while a price series with N≥25
    typically does.

    The earlier drift-vs-noise heuristic was wrong: a random-walk price series
    has zero-mean diffs (returns) by construction, so |drift|/noise stays
    near zero on the diffs and the guard never fires. The series must itself
    be inspected, not just its diffs.
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
