"""Pine v6 indicator math, ported to numpy/pandas.

Only the indicators the three Stage 1 runners need:
- EMA (ta.ema)
- SMA (ta.sma)
- Bollinger Bands (ta.bb) — basis = SMA, dev = stdev with ddof=0
- True Range + Wilder ATR (ta.atr)
- Highest / Lowest of last n (ta.highest / ta.lowest)

Pine's `ta.bb` documentation: "stdev with bias correction off" → numpy stdev with ddof=0.
Pine's `ta.atr` is RMA (running moving average) of true_range — Wilder's smoothing,
not SMA. RMA[i] = (RMA[i-1] * (n-1) + tr[i]) / n with seed = SMA of first n values.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def ema(series: pd.Series, length: int) -> pd.Series:
    """Pine ta.ema — exponential moving average, alpha = 2/(n+1)."""
    return series.ewm(span=length, adjust=False).mean()


def sma(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(length, min_periods=length).mean()


def bb(close: pd.Series, length: int, mult: float):
    """Pine ta.bb returning (basis, upper, lower)."""
    basis = sma(close, length)
    dev = close.rolling(length, min_periods=length).std(ddof=0) * mult
    return basis, basis + dev, basis - dev


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr


def rma(series: pd.Series, length: int) -> pd.Series:
    """Wilder's smoothing — Pine ta.rma."""
    arr = series.values.astype(float)
    out = np.full_like(arr, np.nan)
    if len(arr) < length:
        return pd.Series(out, index=series.index)
    seed = np.nanmean(arr[:length])
    out[length - 1] = seed
    for i in range(length, len(arr)):
        prev = out[i - 1]
        if np.isnan(prev) or np.isnan(arr[i]):
            out[i] = prev
        else:
            out[i] = (prev * (length - 1) + arr[i]) / length
    return pd.Series(out, index=series.index)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int) -> pd.Series:
    return rma(true_range(high, low, close), length)


def highest(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(length, min_periods=length).max()


def lowest(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(length, min_periods=length).min()


def csv_naive_to_utc(
    naive_ts: pd.Series | pd.Timestamp,
    chart_tz: str = "America/New_York",
) -> pd.Series | pd.Timestamp:
    """Convert TV-export 'Date and time' (naive, chart-TZ) to UTC-naive.

    Chart TZ for the three Stage 1 strategies is America/New_York (DST-aware).
    Pine's bare `hour` / `dayofweek` evaluate in the chart TZ; therefore the
    CSV records timestamps in that TZ. DST transitions are handled by
    pandas tz_localize.

    Returns the same type as the input (Series → Series, Timestamp → Timestamp).
    Ambiguous / nonexistent timestamps (DST spring-forward / fall-back) are
    coerced to NaT and filtered downstream.
    """
    is_scalar = isinstance(naive_ts, pd.Timestamp)
    s = pd.Series([naive_ts]) if is_scalar else pd.to_datetime(naive_ts)
    out = (
        s.dt.tz_localize(chart_tz, ambiguous="NaT", nonexistent="NaT")
        .dt.tz_convert("UTC")
        .dt.tz_localize(None)
    )
    return out.iloc[0] if is_scalar else out


def verify_csv_to_bar_alignment(
    bars: pd.DataFrame,
    csv_fill_ts_utc: pd.Series,
    csv_fill_px: pd.Series,
    *,
    n_check: int = 10,
    tol_pct: float = 0.005,
    price_col: str = "open",
) -> tuple[float, list[float]]:
    """Sanity check: the first n_check CSV fill bars should have bar `price_col`
    matching CSV fill price within tol_pct.

    Returns (median_gap_pct, gaps). A larger-than-expected gap indicates either
    a TZ misconfiguration or a real broker-feed price divergence.
    """
    gaps = []
    for ts, px in zip(csv_fill_ts_utc.iloc[:n_check], csv_fill_px.iloc[:n_check]):
        if pd.isna(ts) or ts not in bars.index:
            gaps.append(float("nan"))
            continue
        bar_px = float(bars.at[ts, price_col])
        gaps.append(abs(bar_px - float(px)) / float(px))
    finite = [g for g in gaps if not (g != g)]    # NaN check
    median_gap = sorted(finite)[len(finite) // 2] if finite else float("nan")
    return median_gap, gaps
