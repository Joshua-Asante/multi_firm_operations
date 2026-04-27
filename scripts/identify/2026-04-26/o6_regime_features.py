"""O6 — Regime characterization independent of strategy outcomes.

For each instrument: monthly summaries of ATR(14) distribution, realized vol
of 15min log returns, range expansion frequency (bars where high-low > 1.5×
rolling-ATR), and session-open gap distribution (Sunday-evening ET reopen).

Scope guard (per parent brief + amendment): canonical input for asking
"is the 4yr panel regime-representative of the live tape?" Under OANDA-rescope:
no regime overlay flows from this; demoted to pattern-spotting; routes to Notice.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from common import OUT_DIR, load_bars, add_meta_cols, compute_atr


SYMBOLS = ["XAUUSD", "US30USD", "USDJPY"]


def regime_features(symbol: str) -> pd.DataFrame:
    bars = load_bars(symbol)
    bars["atr14"] = compute_atr(bars, 14)
    bars["log_ret"] = np.log(bars["close"] / bars["close"].shift(1))
    bars["range"] = bars["high"] - bars["low"]
    bars["range_atr_ratio"] = bars["range"] / bars["atr14"]
    bars["range_exp_flag"] = (bars["range_atr_ratio"] > 1.5).astype(int)

    # Session-open gap detection: Sunday evening ET reopen.
    # In UTC: roughly Sun 22:00 UTC (winter EST: 17:00 ET) or 21:00 UTC (summer EDT: 17:00 ET).
    bars_dt = bars.index
    bars["dow"] = bars_dt.dayofweek  # Mon=0..Sun=6
    bars["hour"] = bars_dt.hour
    # Mark first bar of week (Sunday afternoon ET = Sunday evening UTC)
    bars["bar_idx_in_run"] = (
        bars["log_ret"].notna().astype(int).groupby(
            bars_dt.to_series().diff().gt(pd.Timedelta(hours=2)).cumsum()
        ).cumsum()
    )
    # First bar after a >2h gap = session-open gap candidate
    is_first = bars_dt.to_series().diff().gt(pd.Timedelta(hours=2))
    bars["session_open_flag"] = is_first.astype(int).values

    # Gap = abs(open - prev_close) for first bars
    bars["prev_close"] = bars["close"].shift(1)
    bars["gap_abs"] = (bars["open"] - bars["prev_close"]).abs()
    session_gaps = bars.loc[bars["session_open_flag"] == 1, "gap_abs"]

    # Monthly summary
    monthly = bars.groupby(bars.index.to_period("M")).agg(
        n_bars=("close", "size"),
        atr14_mean=("atr14", "mean"),
        atr14_median=("atr14", "median"),
        atr14_p95=("atr14", lambda x: x.quantile(0.95)),
        ret_std=("log_ret", "std"),
        ret_p99_abs=("log_ret", lambda x: x.abs().quantile(0.99)),
        range_exp_freq=("range_exp_flag", "mean"),
        n_session_opens=("session_open_flag", "sum"),
        gap_abs_mean=("gap_abs", lambda x: x[x > 0].mean() if (x > 0).any() else np.nan),
        gap_abs_max=("gap_abs", "max"),
    )

    # Session-open-only gap stats
    session_gaps_monthly = bars.loc[bars["session_open_flag"] == 1].groupby(
        bars.loc[bars["session_open_flag"] == 1].index.to_period("M")
    )["gap_abs"].agg([
        ("session_gap_n", "count"),
        ("session_gap_mean", "mean"),
        ("session_gap_p95", lambda x: x.quantile(0.95)),
        ("session_gap_max", "max"),
    ])
    monthly = monthly.join(session_gaps_monthly, how="left")
    monthly = monthly.reset_index().rename(columns={"time": "month"})
    monthly["month"] = monthly["month"].astype(str)
    monthly["instrument"] = symbol
    monthly = add_meta_cols(monthly)
    return monthly


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for sym in SYMBOLS:
        df = regime_features(sym)
        out = OUT_DIR / f"O6_regime_features_{sym}.csv"
        df.to_csv(out, index=False)
        print(f"[O6] {sym}: {len(df)} months → {out.name}", flush=True)


if __name__ == "__main__":
    main()
