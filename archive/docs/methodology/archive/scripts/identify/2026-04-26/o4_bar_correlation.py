"""O4 — Bar-level cross-instrument correlation + simultaneous-adverse windows.

Static and rolling 60-day pairwise correlations of 15min log returns on
XAUUSD / US30USD / USDJPY. Plus: 15min windows where all three instruments
moved adversely (signed against each strategy's bias) within the same window.

All three locked strategies are LONG-ONLY. So "adverse" = down move.

Scope guard (per parent brief): most plausible MC-input candidate. Under the
OANDA-rescope amendment, demoted explicitly to pattern-spotting; no MC re-run
flows from this. Routes to Notice as OANDA-only pattern.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from common import OUT_DIR, META, load_bars, add_meta_cols


SYMBOLS = ["XAUUSD", "US30USD", "USDJPY"]


def make_returns_panel() -> pd.DataFrame:
    """Build aligned 15min log-return panel across the three instruments."""
    closes = {}
    for sym in SYMBOLS:
        df = load_bars(sym)
        closes[sym] = df["close"]
    px = pd.concat(closes, axis=1)
    # Inner join — only timestamps where all three have a bar
    px = px.dropna()
    rets = np.log(px / px.shift(1)).dropna()
    return rets


def static_corr(rets: pd.DataFrame) -> pd.DataFrame:
    return rets.corr()


def rolling_corr(rets: pd.DataFrame, window_bars: int = 60 * 24 * 4) -> pd.DataFrame:
    """60-day rolling pairwise corr. 60d × 24h × 4bars/h ≈ 5760 bars."""
    pairs = [("XAUUSD", "US30USD"), ("XAUUSD", "USDJPY"), ("US30USD", "USDJPY")]
    out = {}
    for a, b in pairs:
        out[f"{a}__{b}"] = rets[a].rolling(window_bars, min_periods=window_bars // 4).corr(rets[b])
    return pd.DataFrame(out).dropna(how="all")


def simultaneous_adverse(rets: pd.DataFrame, threshold_sigma: float = 1.0) -> pd.DataFrame:
    """Windows where all three instruments moved adversely (down) simultaneously.

    'Adversely' for long-only strategies = negative return on the same 15min bar.
    Magnitude threshold: each instrument's move must be at least 1σ of its own
    rolling 60-day return distribution (sized so we're flagging meaningful
    co-moves, not random noise).
    """
    rolling_std = rets.rolling(60 * 24 * 4, min_periods=500).std()
    adverse = rets < -threshold_sigma * rolling_std
    triple = adverse.all(axis=1)
    flagged = rets.loc[triple].copy()
    flagged["sigma_threshold"] = threshold_sigma
    flagged = flagged.reset_index().rename(columns={
        "time": "utc_window",
        "XAUUSD": "ret_XAUUSD",
        "US30USD": "ret_US30USD",
        "USDJPY": "ret_USDJPY",
    })
    return flagged


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rets = make_returns_panel()
    print(f"[O4] aligned panel: {len(rets):,} 15min bars across {SYMBOLS}", flush=True)

    s = static_corr(rets).round(4)
    s_out = s.reset_index().rename(columns={"index": "instrument"})
    s_out = add_meta_cols(s_out)
    s_out.to_csv(OUT_DIR / "O4_bar_corr_static.csv", index=False)
    print(f"[O4] static corr → O4_bar_corr_static.csv", flush=True)

    r = rolling_corr(rets).reset_index().rename(columns={"time": "utc"})
    # Downsample rolling to daily-end for compactness (5min×96=daily)
    r["utc"] = pd.to_datetime(r["utc"], utc=True)
    r = r.set_index("utc").resample("1D").last().dropna(how="all").reset_index()
    r = add_meta_cols(r, window_days=60)
    r.to_csv(OUT_DIR / "O4_bar_corr_rolling.csv", index=False)
    print(f"[O4] rolling corr (daily-end) → O4_bar_corr_rolling.csv ({len(r)} days)", flush=True)

    sim = simultaneous_adverse(rets, threshold_sigma=1.0)
    sim = add_meta_cols(sim, threshold_sigma=1.0,
                        long_only_universe="all three locked strategies long-only")
    sim.to_csv(OUT_DIR / "O4_simultaneous_adverse_windows.csv", index=False)
    print(f"[O4] simultaneous-adverse 1σ windows: n={len(sim)}", flush=True)


if __name__ == "__main__":
    main()
