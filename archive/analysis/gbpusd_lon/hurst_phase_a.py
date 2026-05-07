"""§0a Component 3 — Conditional persistence diagnostic gate (Phase A) for H-LORB.

Compute Hurst on the post-OR window 09:00-11:00 BST log-RETURNS of M15 bid+ask
mid-price (memory feedback_hurst_rs_log_prices_trap.md — log-returns only,
NEVER log-prices).

Threshold (parent Notice §1.5 + §6, INVERTED from PDSB G2 audit):
  - nolds.hurst_rs Hurst >= 0.50 (canonical estimator)
  - inline R/S Hurst >= 0.50 (cross-check estimator)
  - lag-1 ACF on log-returns >= 0
  Conjunctive: ANY single condition failing -> ABORT G1 to G3.

The threshold is INVERTED relative to the EURUSD predecessor (which used H<0.65
to abort the FADE prior — high persistence falsifies a fade strategy). H-LORB is
a BREAKOUT strategy; high persistence FAVORS it. The gate asks: "is the
post-OR window persistent / momentum-continuing enough to support a breakout
mechanism?" If the answer is no (anti-persistent dynamics, mean-reverting), the
breakout prior is falsified.

Two estimators (inline R/S + nolds.hurst_rs) plus sanity checks on a random
walk (H~0.5 expected) and the log-levels trap. Lag-1 ACF computed
within-day-adjacent (no cross-day pairs) and aggregated.
"""
from __future__ import annotations

import json
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

BST = ZoneInfo("Europe/London")
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


def lag1_acf_within_day(returns: pd.Series, dates: np.ndarray) -> tuple[float, int]:
    """Within-day-adjacent lag-1 ACF.

    Groups returns by date, takes adjacent (return[t-1], return[t]) pairs WITHIN
    each day, computes Pearson correlation of the pooled adjacent-pair series.
    Cross-day boundary pairs are excluded (a return at end-of-day-N vs
    start-of-day-N+1 is not lag-1 in any meaningful sense).

    Returns (rho, n_pairs).
    """
    df = pd.DataFrame({"r": returns.values, "d": dates}).dropna()
    pairs = []
    for _, grp in df.groupby("d", sort=False):
        r = grp["r"].values
        if len(r) < 2:
            continue
        for i in range(len(r) - 1):
            pairs.append((r[i], r[i + 1]))
    if len(pairs) < 5:
        return float("nan"), len(pairs)
    arr = np.asarray(pairs)
    if arr[:, 0].std() == 0 or arr[:, 1].std() == 0:
        return float("nan"), len(pairs)
    rho = float(np.corrcoef(arr[:, 0], arr[:, 1])[0, 1])
    return rho, len(pairs)


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

    # Anti-persistent sanity: AR(1) phi=-0.5 returns should give H<0.5
    phi_neg = -0.5
    ar_neg = np.zeros(2000)
    for i in range(1, 2000):
        ar_neg[i] = phi_neg * ar_neg[i - 1] + np.random.randn()
    h_ar_neg = rs_hurst(np.diff(ar_neg))
    print(f"[Sanity] R/S on AR(1) phi=-0.5 returns: H = {h_ar_neg:.3f} (expect H<0.5)")

    # --- Panel ---
    print("\n=== Loading GBPUSD M15 bid+ask panel ===")
    DATA = Path("data/bar_data/GBPUSD_dukascopy_m15_bidask_2022-01-04_to_2026-04-20.csv")
    df = pd.read_csv(DATA, parse_dates=["timestamp_utc"], index_col="timestamp_utc")
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    print(f"Rows: {len(df):,}")
    print(f"Range UTC: {df.index.min()} -> {df.index.max()}")

    df["mid_close"] = (df["bid_close"] + df["ask_close"]) / 2
    df["log_ret"] = np.log(df["mid_close"]).diff()

    bst_idx = df.index.tz_convert(BST)
    df["bst_hour"] = bst_idx.hour
    df["bst_minute"] = bst_idx.minute
    df["bst_dow"] = bst_idx.dayofweek
    df["bst_date"] = bst_idx.date

    # Post-OR window: 09:00-11:00 BST (M15 bars at 09:00, 09:15, 09:30, 09:45,
    # 10:00, 10:15, 10:30, 10:45). Weekdays only.
    in_window = (
        (df["bst_hour"] == 9) |
        ((df["bst_hour"] == 10) & (df["bst_minute"].isin([0, 15, 30, 45])))
    )
    weekday = df["bst_dow"] < 5
    eligible = weekday & in_window

    sub = df.loc[eligible].copy()
    ret = sub["log_ret"].dropna()
    print(f"\nPost-OR 09:00-11:00 BST weekday returns: n = {len(ret):,}")

    # --- Hurst measurements ---
    print("\n=== Conditional Hurst measurements (post-OR window 09:00-11:00 BST) ===")
    h_inline = rs_hurst(ret.values)
    print(f"[R/S inline]  H = {h_inline:.3f}")

    h_nolds = float("nan")
    try:
        import nolds
        h_nolds = float(nolds.hurst_rs(ret.values))
        print(f"[nolds R/S]   H = {h_nolds:.3f}")
    except Exception as e:
        print(f"[nolds R/S]   ERROR: {e}")

    # Full-panel for context
    h_panel_inline = rs_hurst(df["log_ret"].dropna().values)
    print(f"[R/S inline]  Full-panel H (context): {h_panel_inline:.3f}")

    # --- Lag-1 ACF within-day ---
    rho, n_pairs = lag1_acf_within_day(sub["log_ret"], sub["bst_date"].values)
    print(f"\n[lag-1 ACF]   within-day adjacent pairs: rho = {rho:.4f}  (n_pairs = {n_pairs:,})")

    # Also flat-series ACF as sanity
    r_flat = ret.values
    if len(r_flat) >= 5 and r_flat.std() > 0:
        rho_flat = float(np.corrcoef(r_flat[:-1], r_flat[1:])[0, 1])
    else:
        rho_flat = float("nan")
    print(f"[lag-1 ACF]   flat-series (cross-day boundary noise): rho = {rho_flat:.4f}")

    # --- Gate decision ---
    print("\n=== GATE DECISION (parent Notice §1.5 + §6) ===")
    threshold_h = 0.50
    threshold_acf = 0.0
    inline_pass = h_inline >= threshold_h
    nolds_pass = (not np.isnan(h_nolds)) and h_nolds >= threshold_h
    acf_pass = rho >= threshold_acf

    verdict_inline = "PASS" if inline_pass else "FAIL_ABORT_G3"
    verdict_nolds = "PASS" if nolds_pass else "FAIL_ABORT_G3"
    verdict_acf = "PASS" if acf_pass else "FAIL_ABORT_G3"

    print(f"Threshold: H >= {threshold_h}, lag-1 ACF >= {threshold_acf}")
    print(f"R/S inline:  H={h_inline:.3f} -> {verdict_inline}")
    print(f"nolds R/S:   H={h_nolds:.3f} -> {verdict_nolds}")
    print(f"lag-1 ACF:   rho={rho:.4f} -> {verdict_acf}")

    final = "PASS" if (inline_pass and nolds_pass and acf_pass) else "FAIL_ABORT_G3"
    print(f"\nFINAL conjunctive verdict: {final}")

    out = {
        "sanity": {
            "rs_random_walk_returns_n2000": float(h_rw),
            "rs_log_levels_trap_demo": float(h_levels),
            "rs_ar1_phi05_returns": float(h_ar),
            "rs_ar1_phineg05_returns": float(h_ar_neg),
        },
        "panel": {
            "n_total_m15_bars": int(len(df)),
            "n_returns": int(df["log_ret"].dropna().shape[0]),
            "h_full_panel_rs_inline": float(h_panel_inline),
        },
        "post_or_window": {
            "window_bst": "09:00-11:00 BST (8 M15 bars per weekday)",
            "n_returns": int(len(ret)),
            "h_rs_inline": float(h_inline),
            "h_nolds_rs": None if np.isnan(h_nolds) else float(h_nolds),
            "lag1_acf_within_day": float(rho),
            "lag1_acf_within_day_n_pairs": int(n_pairs),
            "lag1_acf_flat_series": float(rho_flat),
        },
        "gate": {
            "threshold_h": threshold_h,
            "threshold_lag1_acf": threshold_acf,
            "inline_decision": verdict_inline,
            "nolds_decision": verdict_nolds,
            "acf_decision": verdict_acf,
            "final_verdict": final,
        },
        "method_notes": [
            "Returns: log(mid_close).diff() — log-RETURNS, not log-prices.",
            "Sanity: R/S on log-LEVELS yields spurious high H (memory feedback_hurst_rs_log_prices_trap.md).",
            "Window: M15 bars at 09:00, 09:15, 09:30, 09:45, 10:00, 10:15, 10:30, 10:45 BST.",
            "lag-1 ACF computed within-day-adjacent (no cross-day boundary pairs).",
            "Threshold INVERTED from PDSB: H>=0.50 PASS supports breakout prior; H<0.50 falsifies.",
            "Conjunctive: ANY one of (inline, nolds, ACF) failing -> abort G1 to G3.",
        ],
        "brief_commit_hash": "158dc61d1aae7ed87717a7291c43df51c526c9b5",
    }
    Path("analysis/archive/gbpusd_lon/results").mkdir(parents=True, exist_ok=True)
    with open("analysis/archive/gbpusd_lon/results/h_lorb_g1_phaseA_hurst.json", "w") as f:
        json.dump(out, f, indent=2)
    print("\nWritten: analysis/archive/gbpusd_lon/results/h_lorb_g1_phaseA_hurst.json")


if __name__ == "__main__":
    main()
