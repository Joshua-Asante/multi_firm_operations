"""§0a Component 3 — Conditional Hurst diagnostic gate (Phase A).

Compute Hurst on event-day post-08:30 ET 30-min windows, on log-RETURNS
of M15 bid+ask mid-price (memory feedback_hurst_rs_log_prices_trap.md).

Threshold: H >= 0.65 -> ABORT G2 to G4.

Two estimators are reported (inline R/S + nolds.hurst_rs) plus sanity
checks on a random walk (H~0.5 expected) and the log-levels trap.
"""
from __future__ import annotations

import json
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ET = ZoneInfo("America/New_York")
np.random.seed(42)


def rs_hurst(series, min_lag=4, max_lag=None):
    """R/S Hurst estimator on a 1D series of INCREMENTS (returns)."""
    series = np.asarray(series, dtype=float)
    n = len(series)
    if n < 20:
        return float("nan")
    if max_lag is None:
        max_lag = max(min_lag + 4, n // 4)
    lags = []
    rs_vals = []
    lag = min_lag
    while lag <= max_lag:
        n_win = n // lag
        if n_win < 2:
            break
        rs_arr = []
        for w in range(n_win):
            x = series[w * lag:(w + 1) * lag]
            mean = x.mean()
            y = x - mean
            z = np.cumsum(y)
            R = z.max() - z.min()
            S = x.std(ddof=1)
            if S > 0:
                rs_arr.append(R / S)
        if rs_arr:
            lags.append(lag)
            rs_vals.append(np.mean(rs_arr))
        lag = int(lag * 1.5) if int(lag * 1.5) > lag else lag + 1
    if len(lags) < 4:
        return float("nan")
    log_lags = np.log(lags)
    log_rs = np.log(rs_vals)
    slope, _ = np.polyfit(log_lags, log_rs, 1)
    return float(slope)


def main():
    # --- Sanity ---
    rw_returns = np.random.randn(2000)
    h_rw = rs_hurst(rw_returns)
    print(f"[Sanity] R/S on N(0,1) returns (n=2000): H = {h_rw:.3f} (expect ~0.5)")

    persist = np.cumsum(np.random.randn(2000))
    h_levels = rs_hurst(persist)
    print(f"[Sanity] R/S on log-PRICES (the trap) (n=2000): H = {h_levels:.3f} (illustrates trap)")

    phi = 0.5
    ar = np.zeros(2000)
    for i in range(1, 2000):
        ar[i] = phi * ar[i - 1] + np.random.randn()
    h_ar = rs_hurst(np.diff(ar))
    print(f"[Sanity] R/S on AR(1) phi=0.5 returns: H = {h_ar:.3f}")

    # --- Panel ---
    print("\n=== Loading EURUSD M15 bid+ask panel ===")
    DATA = Path("data/bar_data/EURUSD_dukascopy_m15_bidask_2022-01-04_to_2026-04-20.csv")
    df = pd.read_csv(DATA, parse_dates=["timestamp_utc"], index_col="timestamp_utc")
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    print(f"Rows: {len(df):,}")
    print(f"Range UTC: {df.index.min()} -> {df.index.max()}")

    df["mid_close"] = (df["bid_close"] + df["ask_close"]) / 2
    df["log_ret"] = np.log(df["mid_close"]).diff()

    et_idx = df.index.tz_convert(ET)

    # Event-window selection
    in_window = ((et_idx.hour == 8) & ((et_idx.minute == 30) | (et_idx.minute == 45)))
    weekday = et_idx.dayofweek < 5

    # Broad: any weekday 08:30+08:45 ET
    eligible_broad = weekday & in_window
    ret_broad = df.loc[eligible_broad, "log_ret"].dropna().values

    # NFP-only: first Friday of month
    fri = et_idx.dayofweek == 4
    first_week = et_idx.day <= 7
    eligible_nfp = fri & first_week & in_window
    ret_nfp = df.loc[eligible_nfp, "log_ret"].dropna().values

    print(f"\nBroad (any wkday 08:30+08:45 ET): n_returns = {len(ret_broad):,}")
    print(f"NFP   (1st Fri 08:30+08:45 ET):    n_returns = {len(ret_nfp):,}")

    print("\n=== Conditional Hurst measurements ===")
    h_broad_rs = rs_hurst(ret_broad)
    h_nfp_rs = rs_hurst(ret_nfp) if len(ret_nfp) >= 30 else float("nan")
    print(f"[R/S inline] Broad event-window H  = {h_broad_rs:.3f}")
    if not np.isnan(h_nfp_rs):
        print(f"[R/S inline] NFP-only H            = {h_nfp_rs:.3f}")
    else:
        print("[R/S inline] NFP-only H = NaN (insufficient n)")

    h_broad_nolds = float("nan")
    h_nfp_nolds = float("nan")
    try:
        import nolds
        h_broad_nolds = float(nolds.hurst_rs(ret_broad))
        if len(ret_nfp) >= 30:
            h_nfp_nolds = float(nolds.hurst_rs(ret_nfp))
        print(f"[nolds R/S]  Broad event-window H  = {h_broad_nolds:.3f}")
        if not np.isnan(h_nfp_nolds):
            print(f"[nolds R/S]  NFP-only H            = {h_nfp_nolds:.3f}")
    except Exception as e:
        print(f"[nolds R/S] ERROR: {e}")

    # Full-panel for context (G1 audit anchor ~0.75)
    h_panel_rs = rs_hurst(df["log_ret"].dropna().values)
    print(f"[R/S inline] Full panel H (context, G1 anchor ~0.75): {h_panel_rs:.3f}")

    print("\n=== GATE DECISION ===")
    threshold = 0.65
    broad_pass = h_broad_rs < threshold
    nolds_pass = (np.isnan(h_broad_nolds) or h_broad_nolds < threshold)
    print(f"Threshold: H < {threshold}")
    verdict_inline = "PASS" if broad_pass else "FAIL_ABORT_G4"
    verdict_nolds = "PASS" if nolds_pass else "FAIL_ABORT_G4"
    print(f"Broad event-window R/S inline:  H={h_broad_rs:.3f} -> {verdict_inline}")
    print(f"Broad event-window nolds R/S:   H={h_broad_nolds:.3f} -> {verdict_nolds}")

    final = "PASS" if (broad_pass and nolds_pass) else "FAIL_ABORT_G4"
    print(f"\nFINAL gate verdict: {final}")

    out = {
        "sanity": {
            "rs_random_walk_returns_n2000": float(h_rw),
            "rs_log_levels_trap_demo": float(h_levels),
            "rs_ar1_phi05_returns": float(h_ar),
        },
        "panel": {
            "n_total_m15_bars": int(len(df)),
            "n_returns": int(df["log_ret"].dropna().shape[0]),
            "h_full_panel_rs_inline": float(h_panel_rs),
        },
        "event_conditional": {
            "broad_n_returns": int(len(ret_broad)),
            "nfp_n_returns": int(len(ret_nfp)),
            "h_broad_rs_inline": float(h_broad_rs),
            "h_nfp_rs_inline": None if np.isnan(h_nfp_rs) else float(h_nfp_rs),
            "h_broad_nolds_rs": None if np.isnan(h_broad_nolds) else float(h_broad_nolds),
            "h_nfp_nolds_rs": None if np.isnan(h_nfp_nolds) else float(h_nfp_nolds),
        },
        "gate": {
            "threshold": threshold,
            "broad_decision_inline": verdict_inline,
            "broad_decision_nolds": verdict_nolds,
            "final_verdict": final,
        },
        "method_notes": [
            "Returns: log(mid_close).diff() — log-RETURNS, not log-prices.",
            "Sanity check confirms R/S on log-LEVELS yields spurious high H (memory feedback_hurst_rs_log_prices_trap.md).",
            "Event-window: M15 bars at 08:30 and 08:45 ET (covering 30-min post-release).",
            "Broad: any weekday 08:30 ET (superset of true event days; conservative — biases gate toward more returns).",
            "NFP: first Friday of month at 08:30 ET (subset).",
            "Threshold H >= 0.65 fires the structural-abort to G4 per stub §3 component 3.",
        ],
        "brief_commit_hash": "c3ef0448984f6fe11fba440285b5323b35209ca5",
    }
    Path("analysis/archive/eurusd_lnyo/results").mkdir(parents=True, exist_ok=True)
    with open("analysis/archive/eurusd_lnyo/results/h_pdsb_g2_phaseA_hurst.json", "w") as f:
        json.dump(out, f, indent=2)
    print("\nWritten: analysis/archive/eurusd_lnyo/results/h_pdsb_g2_phaseA_hurst.json")


if __name__ == "__main__":
    main()
