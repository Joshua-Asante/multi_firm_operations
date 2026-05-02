"""Post-exit excursion (50-bar MFE/MAE in trade direction).

For each completed trade exit, record running max-favorable and max-adverse
moves over the next N bars in the trade's continuation direction. Returned
as price-units; the runner converts to R-multiples using the strategy-
specific stop distance.

Sign convention (long-only at v5.5/v4.4/v4.3):
- continuation MFE = max(high[t_exit+1 : t_exit+1+N]) - exit_px
- continuation MAE = exit_px - min(low [t_exit+1 : t_exit+1+N])

Both reported as positive numbers in price units. A high MFE means "price
continued in the trade's favored direction past the exit" — a hint that
the exit may have been premature.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def post_exit_excursion(
    bars: pd.DataFrame,
    exit_ts: pd.Series,
    exit_px: pd.Series,
    *,
    n_bars: int = 50,
) -> pd.DataFrame:
    """Compute (mfe_px, mae_px) over the n_bars after each exit.

    Returns a DataFrame aligned with the input series, columns:
        exit_ts, exit_px, mfe_px, mae_px, n_window_bars

    `n_window_bars` reports the actual window size (may be < n_bars at the
    panel tail). Trades whose exit is at or after the last bar return NaN.
    """
    if not bars.index.is_monotonic_increasing:
        raise AssertionError("bars index must be monotonic increasing")

    bar_idx = bars.index
    high = bars["high"].values
    low = bars["low"].values

    out = pd.DataFrame({
        "exit_ts": pd.to_datetime(exit_ts).values,
        "exit_px": np.asarray(exit_px, dtype=float),
    })
    mfe = np.full(len(out), np.nan)
    mae = np.full(len(out), np.nan)
    n_win = np.zeros(len(out), dtype=int)

    pos = bar_idx.searchsorted(out["exit_ts"].values, side="right")

    for i, p in enumerate(pos):
        start = int(p)
        stop = min(start + n_bars, len(bar_idx))
        if start >= len(bar_idx):
            continue
        window_high = high[start:stop]
        window_low = low[start:stop]
        if len(window_high) == 0:
            continue
        mfe[i] = float(window_high.max() - out.at[i, "exit_px"])
        mae[i] = float(out.at[i, "exit_px"] - window_low.min())
        n_win[i] = stop - start

    out["mfe_px"] = mfe
    out["mae_px"] = mae
    out["n_window_bars"] = n_win
    return out


def random_window_excursion(
    bars: pd.DataFrame,
    n_samples: int,
    *,
    n_bars: int = 50,
    rng: np.random.Generator | None = None,
    excluded_ranges: list[tuple[pd.Timestamp, pd.Timestamp]] | None = None,
) -> pd.DataFrame:
    """Sample random non-overlapping 50-bar windows; return MFE/MAE per window.

    `excluded_ranges` is a list of (start, end) intervals (e.g. held-trade
    windows) to exclude from window-start eligibility. The exclusion is
    based on the *start* of the window only — overlap with the tail of an
    excluded range is permitted (the goal is "the strategy was not in a
    trade when this synthetic exit fires", not zero-overlap).

    Returns a DataFrame: anchor_ts, anchor_px, mfe_px, mae_px, n_window_bars.
    """
    if rng is None:
        rng = np.random.default_rng()

    bar_idx = bars.index
    high = bars["high"].values
    low = bars["low"].values
    close = bars["close"].values

    eligible = np.arange(len(bar_idx) - n_bars - 1)
    if excluded_ranges is not None and len(excluded_ranges) > 0:
        ts_arr = bar_idx.values
        keep = np.ones(len(eligible), dtype=bool)
        for start, end in excluded_ranges:
            in_range = (ts_arr[eligible] >= np.datetime64(start)) & (
                ts_arr[eligible] <= np.datetime64(end)
            )
            keep &= ~in_range
        eligible = eligible[keep]

    if len(eligible) < n_samples:
        raise AssertionError(
            f"Not enough eligible bar positions to sample {n_samples} "
            f"non-trade-window 50-bar windows (have {len(eligible)})"
        )

    chosen = rng.choice(eligible, size=n_samples, replace=False)
    rows = []
    for p in chosen:
        anchor_ts = bar_idx[p]
        anchor_px = float(close[p])
        window_high = high[p + 1 : p + 1 + n_bars]
        window_low = low[p + 1 : p + 1 + n_bars]
        rows.append({
            "anchor_ts": anchor_ts,
            "anchor_px": anchor_px,
            "mfe_px": float(window_high.max() - anchor_px),
            "mae_px": float(anchor_px - window_low.min()),
            "n_window_bars": len(window_high),
        })
    return pd.DataFrame(rows)
