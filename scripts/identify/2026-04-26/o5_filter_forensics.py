"""O5 — Filter forensics: bar-level distribution comparison for each
locked filter window vs the unblocked sessions of the same instrument.

For each filter, segments the bars into:
  - blocked   = bars where the filter is currently blocking
  - unblocked = bars in the same instrument's session window (i.e., comparable
                trading-time bars), with the blocking filter NOT firing

Compares:
  - ATR distribution (mean, median, p95)
  - Range expansion frequency (range / ATR > 1.5)
  - Gap frequency (|open - prev_close| > 1×ATR)
  - Signed-move frequency (close > open)

Each filter cell is flagged with cohort size and structural-vs-idiosyncratic
heuristic: if blocked-bar count is dominated (>50% concentrated) by <5
distinct calendar dates, mark idiosyncratic.

Rule 1: every cell with n<10 carries thin_cohort=1.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from common import OUT_DIR, load_bars, add_meta_cols, compute_atr
from filters import EVAL, add_local_time


# Filter inventory: (strategy, filter_label, evaluator → blocked-bool-Series, comparison-pool-Series)
def gather_guardian():
    bars = load_bars("XAUUSD")
    df = EVAL["guardian"](bars)
    pool = (df["session_pass"] == 1) & (df["day_pass"] == 1)  # comparable session bars
    filters = {
        "guardian_block_TueH08": df["block_TueH08"] == 1,
        "guardian_block_MonH08": df["block_MonH08"] == 1,
        "guardian_block_MonH09": df["block_MonH09"] == 1,
        "guardian_block_MonH12": df["block_MonH12"] == 1,
        "guardian_block_TueH12": df["block_TueH12"] == 1,
        "guardian_block_ThuH12": df["block_ThuH12"] == 1,
        # Whole-day blocks (Wed and Fri excluded by day_pass)
        "guardian_block_Wed": df["is_wed"] == 1,
        "guardian_block_Fri": df["is_fri"] == 1,
    }
    # For Wed/Fri whole-day blocks, the comparison pool is all session-hour bars on any day
    pool_wholeday = (df["session_pass"] == 1)
    pools = {k: (pool_wholeday if k.endswith(("_Wed", "_Fri")) else pool) for k in filters}
    return bars, df, filters, pools


def gather_striker():
    bars = load_bars("US30USD")
    df = EVAL["striker"](bars)
    pool = (df["session_pass"] == 1)
    filters = {
        "striker_block_Mon": df["is_mon"] == 1,
        "striker_block_Wed": df["is_wed"] == 1,
        "striker_block_Thu": df["is_thu"] == 1,
        # ATR-expansion gate
        "striker_block_atrNotExpanding": df["atr_expanding"] == 0,
    }
    return bars, df, filters, {k: pool for k in filters}


def gather_aegis():
    bars = load_bars("USDJPY")
    df = EVAL["aegis"](bars)
    pool = (df["in_session"] == 1) & (df["day_pass"] == 1)
    pool_session_only = (df["in_session"] == 1)  # for whole-day excluded filters
    filters = {
        "aegis_block_TueH10": df["block_TueH10"] == 1,
        "aegis_block_EOM": df["block_EOM"] == 1,
        "aegis_block_H11_or_1045": df["hour_pass"] == 0,
        "aegis_block_lowATR": df["vol_pass"] == 0,
        "aegis_block_Thu": df["is_thu"] == 1,  # Aegis trades Mon/Tue/Wed only
        "aegis_block_Fri": df["is_fri"] == 1,
    }
    pools = {k: pool for k in filters}
    pools["aegis_block_Thu"] = pool_session_only
    pools["aegis_block_Fri"] = pool_session_only
    return bars, df, filters, pools


def features_for_mask(bars: pd.DataFrame, df: pd.DataFrame, mask: pd.Series) -> dict:
    sub_bars = bars.loc[mask]
    sub_df = df.loc[mask]
    if len(sub_bars) == 0:
        return {"n": 0}
    rng = sub_bars["high"] - sub_bars["low"]
    atr = sub_df["atr"]
    range_atr = (rng / atr).where(atr > 0)
    prev_close = sub_bars["close"].shift(1)
    gap_abs = (sub_bars["open"] - prev_close).abs()
    gap_atr = (gap_abs / atr).where(atr > 0)
    bullish = (sub_bars["close"] > sub_bars["open"]).astype(int)
    distinct_dates = sub_bars.index.normalize().nunique()
    # Idiosyncratic if top-5 dates account for >50% of bars
    date_counts = sub_bars.index.normalize().value_counts().head(5).sum()
    idiosyncratic = int(date_counts > 0.5 * len(sub_bars) and distinct_dates < 20)
    return {
        "n": len(sub_bars),
        "n_distinct_dates": int(distinct_dates),
        "atr_mean": float(atr.mean()),
        "atr_median": float(atr.median()),
        "atr_p95": float(atr.quantile(0.95)),
        "range_atr_mean": float(range_atr.mean()),
        "range_exp_freq": float((range_atr > 1.5).mean()),
        "gap_atr_mean": float(gap_atr.mean()),
        "gap_freq_1xATR": float((gap_atr > 1.0).mean()),
        "bullish_freq": float(bullish.mean()),
        "idiosyncratic_flag": idiosyncratic,
    }


def forensics_for_filter(bars, df, blocked_mask, pool_mask) -> pd.DataFrame:
    blocked = features_for_mask(bars, df, blocked_mask & pool_mask)
    unblocked = features_for_mask(bars, df, pool_mask & ~blocked_mask)
    rows = []
    for cohort_label, feats in [("blocked", blocked), ("unblocked", unblocked)]:
        row = {"cohort": cohort_label, **feats}
        row["thin_cohort"] = int(row["n"] < 10)
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for gather_fn in (gather_guardian, gather_striker, gather_aegis):
        bars, df, filters, pools = gather_fn()
        for label, mask in filters.items():
            out = forensics_for_filter(bars, df, mask, pools[label])
            out["filter"] = label
            out = add_meta_cols(out)
            cols = ["filter", "cohort"] + [c for c in out.columns if c not in ("filter", "cohort")]
            out = out[cols]
            fname = OUT_DIR / f"O5_filter_forensics_{label}.csv"
            out.to_csv(fname, index=False)
            n_block = out.loc[out["cohort"] == "blocked", "n"].iloc[0]
            thin = int(out["thin_cohort"].sum())
            print(f"[O5] {label}: blocked n={n_block} (thin={thin}) → {fname.name}", flush=True)


if __name__ == "__main__":
    main()
