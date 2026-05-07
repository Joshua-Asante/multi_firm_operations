"""Phase 2 — structural characterization of AUDNZD M15.

Computes the 8 measurements the brief specifies, emits a JSON results file
plus plots, and writes a stub of the findings markdown for the analyst (me)
to flesh out the synthesis from the numbers.

Brief: 2026-04-26 AUDNZD candidate-strategy discovery.
Data: data/audnzd_oanda_m15_2022-01-01_to_2026-04-26_clean.csv
      SHA256 6ff6cc3ce9f3f7ac825b2bae8e1d0cd82295564ca909ba6698f523606fba2d92

Pre-Q gate domain: data. No strategy hypotheses are encoded in any deletion
or transformation here — only structural compression that preserves the
unformed question 'what regime structure does AUDNZD exhibit'.
"""
from __future__ import annotations

import json
import pathlib
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from statsmodels.tsa.stattools import adfuller, acf

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CLEAN_CSV = REPO_ROOT / "data" / "audnzd_oanda_m15_2022-01-01_to_2026-04-26_clean.csv"
EXPECTED_SHA = "6ff6cc3ce9f3f7ac825b2bae8e1d0cd82295564ca909ba6698f523606fba2d92"
FINDINGS_DIR = REPO_ROOT / "docs" / "methodology" / "findings"
PLOTS_DIR = FINDINGS_DIR
RESULTS_JSON = FINDINGS_DIR / "2026-04-26_audnzd_structural_results.json"

# RBA + RBNZ decision dates 2022-04-26 - 2026-04-26.
# Best-effort from public schedules; minor errors are acceptable for an
# aggregate ATR-shift test (sample size is tens of dates, not single-event).
RBA_DATES = [
    "2022-02-01","2022-03-01","2022-04-05","2022-05-03","2022-06-07","2022-07-05",
    "2022-08-02","2022-09-06","2022-10-04","2022-11-01","2022-12-06",
    "2023-02-07","2023-03-07","2023-04-04","2023-05-02","2023-06-06","2023-07-04",
    "2023-08-01","2023-09-05","2023-10-03","2023-11-07","2023-12-05",
    "2024-02-06","2024-03-19","2024-05-07","2024-06-18","2024-08-06","2024-09-24",
    "2024-11-05","2024-12-10",
    "2025-02-18","2025-04-01","2025-05-20","2025-07-08","2025-08-12","2025-09-30",
    "2025-11-04","2025-12-09",
    "2026-02-17","2026-04-01",
]
RBNZ_DATES = [
    "2022-02-23","2022-04-13","2022-05-25","2022-07-13","2022-08-17","2022-10-05","2022-11-23",
    "2023-02-22","2023-04-05","2023-05-24","2023-07-12","2023-08-16","2023-10-04","2023-11-29",
    "2024-02-28","2024-04-10","2024-05-22","2024-07-10","2024-08-14","2024-10-09","2024-11-27",
    "2025-02-19","2025-04-09","2025-05-28","2025-07-09","2025-08-20","2025-10-08","2025-11-26",
    "2026-02-25","2026-04-08",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def verify_hash() -> None:
    import hashlib
    h = hashlib.sha256()
    with CLEAN_CSV.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    got = h.hexdigest()
    if got != EXPECTED_SHA:
        raise SystemExit(f"clean CSV hash mismatch: got {got}, expected {EXPECTED_SHA}")
    print(f"data hash OK: {got}")


def parse_iso_series(s: pd.Series) -> pd.DatetimeIndex:
    # OANDA emits nanosecond-precision RFC3339; pandas handles it natively but
    # the 'Z' must be tz-aware.
    return pd.to_datetime(s.str.replace("Z", "+00:00", regex=False), utc=True)


def hurst_rs(series: np.ndarray, lag: int) -> float:
    """Rescaled-range Hurst at one lag. Returns log(R/S) for that window len.

    For a single H estimate, we slice the series into non-overlapping windows
    of length `lag`, compute R/S per window, and average. Then H is fit from
    log(<R/S>) vs log(lag) over multiple lags.
    """
    n = len(series)
    n_windows = n // lag
    if n_windows < 1:
        return np.nan
    rs_values = []
    for i in range(n_windows):
        window = series[i * lag : (i + 1) * lag]
        x = window - window.mean()
        z = np.cumsum(x)
        r = z.max() - z.min()
        s = window.std(ddof=0)
        if s > 0:
            rs_values.append(r / s)
    if not rs_values:
        return np.nan
    return float(np.mean(rs_values))


def hurst_at_horizon(series: np.ndarray, target_lag: int) -> tuple[float, float, float]:
    """Estimate H at a given horizon via R/S regression over a lag-band centered on target.

    Returns (H, lo95, hi95).
    """
    # Use a band of lags around the target to fit the slope of log(R/S) vs log(lag).
    # This gives both a point estimate and a confidence interval.
    half_decade = max(1, int(round(np.log10(target_lag) - 0.5)))
    lags = np.unique(np.round(np.geomspace(
        max(8, target_lag // 4), target_lag * 2, num=10
    )).astype(int))
    rs_means = []
    valid_lags = []
    for L in lags:
        rs = hurst_rs(series, int(L))
        if rs is not None and not np.isnan(rs) and rs > 0:
            rs_means.append(rs)
            valid_lags.append(int(L))
    if len(valid_lags) < 4:
        return (np.nan, np.nan, np.nan)
    log_lags = np.log(valid_lags)
    log_rs = np.log(rs_means)
    # Linear fit; slope = H
    slope, intercept = np.polyfit(log_lags, log_rs, 1)
    # 95% CI via residual bootstrap on the slope estimate
    fitted = slope * log_lags + intercept
    resid = log_rs - fitted
    n = len(log_lags)
    rng = np.random.default_rng(seed=42)
    boot_slopes = []
    for _ in range(2000):
        b_resid = rng.choice(resid, size=n, replace=True)
        b_y = fitted + b_resid
        b_slope, _ = np.polyfit(log_lags, b_y, 1)
        boot_slopes.append(b_slope)
    lo, hi = np.percentile(boot_slopes, [2.5, 97.5])
    return float(slope), float(lo), float(hi)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    FINDINGS_DIR.mkdir(parents=True, exist_ok=True)
    verify_hash()

    df = pd.read_csv(CLEAN_CSV)
    print(f"loaded {len(df):,} rows")

    # Build mid OHLC
    df["dt_utc"] = parse_iso_series(df["datetime_utc"])
    df = df.sort_values("dt_utc").reset_index(drop=True)
    df["open"]  = (df["open_bid"]  + df["open_ask"])  / 2.0
    df["high"]  = (df["high_bid"]  + df["high_ask"])  / 2.0
    df["low"]   = (df["low_bid"]   + df["low_ask"])   / 2.0
    df["close"] = (df["close_bid"] + df["close_ask"]) / 2.0
    df["spread_pips"] = (df["close_ask"] - df["close_bid"]) * 10000.0

    # Returns
    df["ret"] = df["close"].pct_change()
    df["log_ret"] = np.log(df["close"]).diff()

    # NY-time and DOW
    df["dt_ny"] = df["dt_utc"].dt.tz_convert("America/New_York")
    df["hour_ny"] = df["dt_ny"].dt.hour
    df["dow_utc"] = df["dt_utc"].dt.dayofweek  # 0=Mon

    # M15 ATR(14): true range = max(h-l, |h-prev_close|, |l-prev_close|)
    pc = df["close"].shift(1)
    tr = np.maximum.reduce([
        (df["high"] - df["low"]).values,
        np.abs((df["high"] - pc).values),
        np.abs((df["low"]  - pc).values),
    ])
    df["tr"] = tr
    df["atr14_m15"] = pd.Series(tr).rolling(14, min_periods=14).mean()

    results: dict = {
        "data_hash": EXPECTED_SHA,
        "n_bars": int(len(df)),
        "first_bar_utc": df["datetime_utc"].iloc[0],
        "last_bar_utc": df["datetime_utc"].iloc[-1],
    }

    # -------- 1. Hurst at horizons 16/64/256 bars --------
    # R/S Hurst is applied to log RETURNS (the increments), not log prices.
    # On an integrated process like log-price, R/S yields a spurious H near 1.
    # H of returns: 0.5=random-walk increments, <0.5=mean-reverting,
    # >0.5=trending/persistent.
    log_ret_clean = df["log_ret"].dropna().values
    hurst_results = {}
    for h_bars in [16, 64, 256]:
        H, lo, hi = hurst_at_horizon(log_ret_clean, h_bars)
        hurst_results[str(h_bars)] = {"H": H, "ci95_lo": lo, "ci95_hi": hi}
        print(f"Hurst @ {h_bars}bar (returns): H={H:.3f} CI95=[{lo:.3f}, {hi:.3f}]")
    results["hurst"] = hurst_results

    # Plot R/S regression for the broadest band (informative)
    fig, ax = plt.subplots(figsize=(6, 4))
    lags = np.unique(np.round(np.geomspace(8, 1024, num=18)).astype(int))
    rs_vals = [hurst_rs(log_ret_clean, int(L)) for L in lags]
    valid = [(L, rs) for L, rs in zip(lags, rs_vals) if rs is not None and not np.isnan(rs)]
    if valid:
        lL, lRS = zip(*valid)
        ax.loglog(lL, lRS, "o-")
        slope, _ = np.polyfit(np.log(lL), np.log(lRS), 1)
        ax.set_xlabel("lag (M15 bars)")
        ax.set_ylabel("R/S of log returns")
        ax.set_title(f"AUDNZD M15 R/S vs lag (log returns)  (slope=H={slope:.3f})")
        ax.grid(True, which="both", alpha=0.3)
        plt.tight_layout()
        plt.savefig(PLOTS_DIR / "2026-04-26_audnzd_hurst_rs.png", dpi=120)
        plt.close()

    # -------- 2. ADF on price levels and on log returns --------
    adf_levels = adfuller(df["close"].dropna().values, autolag="AIC")
    adf_logret = adfuller(df["log_ret"].dropna().values, autolag="AIC")
    results["adf"] = {
        "levels":   {"stat": float(adf_levels[0]), "pvalue": float(adf_levels[1]), "nlags": int(adf_levels[2])},
        "log_ret":  {"stat": float(adf_logret[0]), "pvalue": float(adf_logret[1]), "nlags": int(adf_logret[2])},
    }
    print(f"ADF levels:  stat={adf_levels[0]:.3f} p={adf_levels[1]:.4f}")
    print(f"ADF log_ret: stat={adf_logret[0]:.3f} p={adf_logret[1]:.4g}")

    # -------- 3. Volatility profile by NY hour --------
    vol_by_hour = df.groupby("hour_ny")["atr14_m15"].median()
    vol_dict = {int(h): float(v) if pd.notna(v) else None for h, v in vol_by_hour.items()}
    results["vol_by_hour_ny_median_atr"] = vol_dict
    sorted_hours = sorted(vol_dict.items(), key=lambda kv: -(kv[1] or 0))
    # Find the 3-hour contiguous window with highest summed median ATR
    hours_array = np.array([vol_dict.get(h, 0) or 0 for h in range(24)])
    win3 = np.array([hours_array[i] + hours_array[(i+1) % 24] + hours_array[(i+2) % 24] for i in range(24)])
    peak_start = int(win3.argmax())
    peak_window = (peak_start, (peak_start + 2) % 24)
    results["peak_3h_window_ny"] = {"start_hour": peak_window[0], "end_hour": peak_window[1],
                                     "summed_median_atr": float(win3[peak_start])}
    print(f"Peak 3h window NY: {peak_window[0]:02d}:00 - {(peak_window[1]+1)%24:02d}:00 "
          f"(sum median ATR={win3[peak_start]:.6f})")

    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.bar(range(24), hours_array)
    ax.set_xlabel("Hour (NY time)")
    ax.set_ylabel("Median ATR(14) on M15 (price)")
    ax.set_title("AUDNZD M15 — median volatility by NY hour")
    ax.set_xticks(range(0, 24, 2))
    ax.grid(True, alpha=0.3)
    ax.axvspan(peak_start - 0.5, peak_start + 2.5, color="orange", alpha=0.2,
               label=f"peak 3h: {peak_start:02d}-{(peak_start+3)%24:02d} NY")
    ax.legend()
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "2026-04-26_audnzd_vol_by_hour.png", dpi=120)
    plt.close()

    # -------- 4. Spread profile by NY hour --------
    sp_by_hour = df.groupby("hour_ny")["spread_pips"].median()
    sp_dict = {int(h): float(v) for h, v in sp_by_hour.items()}
    results["spread_pips_by_hour_ny_median"] = sp_dict
    overall_med_spread = float(df["spread_pips"].median())
    wide_hours = [h for h, v in sp_dict.items() if v > 2.0 * overall_med_spread]
    results["overall_median_spread_pips"] = overall_med_spread
    results["hours_with_spread_gt_2x_overall_median"] = wide_hours

    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.bar(range(24), [sp_dict.get(h, 0) for h in range(24)])
    ax.axhline(overall_med_spread, color="red", linestyle="--",
               label=f"overall median {overall_med_spread:.2f}p")
    ax.axhline(2 * overall_med_spread, color="orange", linestyle="--",
               label=f"2x median {2*overall_med_spread:.2f}p")
    ax.set_xlabel("Hour (NY time)")
    ax.set_ylabel("Median spread (pips)")
    ax.set_title("AUDNZD M15 — median spread by NY hour")
    ax.set_xticks(range(0, 24, 2))
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "2026-04-26_audnzd_spread_by_hour.png", dpi=120)
    plt.close()

    # -------- 5. Day-of-week effects --------
    daily = df.set_index("dt_utc").resample("1D").agg(
        d_open=("open", "first"),
        d_high=("high", "max"),
        d_low=("low", "min"),
        d_close=("close", "last"),
        d_count=("close", "count"),
    ).dropna()
    daily = daily[daily["d_count"] > 0]
    daily["d_ret"] = daily["d_close"].pct_change()
    daily["d_dow"] = daily.index.dayofweek
    daily["d_atr"] = (daily["d_high"] - daily["d_low"])

    dow_ret_stats = {}
    dow_atr_stats = {}
    for dow in range(7):
        sub = daily[daily["d_dow"] == dow]
        if len(sub) > 0:
            dow_ret_stats[dow] = {
                "n": int(len(sub)),
                "mean_ret_bps": float(sub["d_ret"].mean() * 10000) if pd.notna(sub["d_ret"].mean()) else None,
                "std_ret_bps":  float(sub["d_ret"].std(ddof=1) * 10000) if len(sub) > 1 else None,
            }
            dow_atr_stats[dow] = {
                "n": int(len(sub)),
                "mean_dailyrange_pips": float(sub["d_atr"].mean() * 10000),
            }
    results["dow_returns"] = dow_ret_stats
    results["dow_dailyrange"] = dow_atr_stats

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.5))
    dow_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    means = [dow_ret_stats.get(d, {}).get("mean_ret_bps") or 0 for d in range(7)]
    stds = [dow_ret_stats.get(d, {}).get("std_ret_bps") or 0 for d in range(7)]
    axes[0].bar(dow_labels, means, yerr=stds, capsize=4)
    axes[0].axhline(0, color="black", linewidth=0.5)
    axes[0].set_ylabel("Mean daily return (bps)")
    axes[0].set_title("Daily return by DOW")
    ranges = [dow_atr_stats.get(d, {}).get("mean_dailyrange_pips") or 0 for d in range(7)]
    axes[1].bar(dow_labels, ranges)
    axes[1].set_ylabel("Mean daily range (pips)")
    axes[1].set_title("Daily range by DOW")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "2026-04-26_audnzd_dow.png", dpi=120)
    plt.close()

    # -------- 6. Range vs trend day classification --------
    # Use ATR(14) on daily series for the denominator
    daily["d_atr14"] = (daily["d_high"] - daily["d_low"]).rolling(14, min_periods=14).mean()
    daily["d_dir"] = (daily["d_close"] - daily["d_open"]) / daily["d_atr14"]
    valid_d = daily["d_dir"].dropna()
    n_total = len(valid_d)
    pct_trend = float((valid_d.abs() > 1.0).sum()) / n_total * 100 if n_total else 0
    pct_range = float((valid_d.abs() < 0.3).sum()) / n_total * 100 if n_total else 0
    pct_mid   = 100 - pct_trend - pct_range
    results["daily_range_vs_trend"] = {
        "n_days": int(n_total),
        "pct_trend_abs_gt_1.0": pct_trend,
        "pct_range_abs_lt_0.3": pct_range,
        "pct_mid": pct_mid,
        "mean_abs_dir": float(valid_d.abs().mean()),
        "median_abs_dir": float(valid_d.abs().median()),
    }
    print(f"Daily range/trend: trend={pct_trend:.1f}% range={pct_range:.1f}% mid={pct_mid:.1f}%")

    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.hist(valid_d.values, bins=40, edgecolor="black", alpha=0.7)
    ax.axvline(-1.0, color="red", linestyle="--", alpha=0.7)
    ax.axvline(1.0, color="red", linestyle="--", alpha=0.7, label="|x|=1.0 trend")
    ax.axvline(-0.3, color="orange", linestyle="--", alpha=0.7)
    ax.axvline(0.3, color="orange", linestyle="--", alpha=0.7, label="|x|=0.3 range")
    ax.set_xlabel("(close - open) / ATR14_daily")
    ax.set_ylabel("Days")
    ax.set_title(f"Daily directional ratio (n={n_total})")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "2026-04-26_audnzd_range_trend.png", dpi=120)
    plt.close()

    # -------- 7. RBA / RBNZ decision day classification --------
    # Tag the M15 bars whose date falls on a decision day; compute next-24h ATR
    # vs baseline ATR.
    df["date_utc"] = df["dt_utc"].dt.date
    rba_set = set(pd.to_datetime(RBA_DATES).date)
    rbnz_set = set(pd.to_datetime(RBNZ_DATES).date)
    df["is_rba"]  = df["date_utc"].isin(rba_set)
    df["is_rbnz"] = df["date_utc"].isin(rbnz_set)

    # Compute daily summed TR for next-24h ATR comparison.
    daily_tr = df.set_index("dt_utc")["tr"].resample("1D").sum()
    # Tag dates on the daily index
    daily_dates = pd.Series(daily_tr.index.date, index=daily_tr.index)
    daily_is_rba  = daily_dates.isin(rba_set)
    daily_is_rbnz = daily_dates.isin(rbnz_set)
    baseline_tr_mean = float(daily_tr[~daily_is_rba & ~daily_is_rbnz].mean())
    rba_tr_mean = float(daily_tr[daily_is_rba].mean()) if daily_is_rba.any() else None
    rbnz_tr_mean = float(daily_tr[daily_is_rbnz].mean()) if daily_is_rbnz.any() else None
    n_rba_obs = int(daily_is_rba.sum())
    n_rbnz_obs = int(daily_is_rbnz.sum())
    results["decision_days"] = {
        "n_rba_dates_in_window":  n_rba_obs,
        "n_rbnz_dates_in_window": n_rbnz_obs,
        "baseline_daily_tr_sum":  baseline_tr_mean,
        "rba_daily_tr_sum":       rba_tr_mean,
        "rbnz_daily_tr_sum":      rbnz_tr_mean,
        "rba_to_baseline_ratio":  (rba_tr_mean / baseline_tr_mean) if rba_tr_mean else None,
        "rbnz_to_baseline_ratio": (rbnz_tr_mean / baseline_tr_mean) if rbnz_tr_mean else None,
    }
    print(f"RBA  n={n_rba_obs}  daily TR sum: rba={rba_tr_mean} baseline={baseline_tr_mean}")
    print(f"RBNZ n={n_rbnz_obs} daily TR sum: rbnz={rbnz_tr_mean} baseline={baseline_tr_mean}")

    # -------- 8. Weekly seasonality / autocorrelation --------
    # M15 returns autocorr at lags 1, 5, 20, 96 (= 15min, 75min, 5h, 24h)
    log_ret = df["log_ret"].dropna().values
    acf_vals = acf(log_ret, nlags=200, fft=True)
    autocorr = {
        "lag_1_15min":  float(acf_vals[1]),
        "lag_5_75min":  float(acf_vals[5]),
        "lag_20_5h":    float(acf_vals[20]),
        "lag_96_24h":   float(acf_vals[96]),
    }
    results["log_return_autocorr"] = autocorr
    print(f"log-return ACF: lag1={autocorr['lag_1_15min']:.4f} lag5={autocorr['lag_5_75min']:.4f} "
          f"lag20={autocorr['lag_20_5h']:.4f} lag96={autocorr['lag_96_24h']:.4f}")

    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.bar(range(1, 121), acf_vals[1:121])
    ax.axhline(0, color="black", linewidth=0.5)
    ci = 1.96 / np.sqrt(len(log_ret))
    ax.axhline(ci, color="red", linestyle="--", alpha=0.5, label=f"95% CI ±{ci:.4f}")
    ax.axhline(-ci, color="red", linestyle="--", alpha=0.5)
    ax.set_xlabel("Lag (M15 bars)")
    ax.set_ylabel("ACF of log returns")
    ax.set_title("AUDNZD M15 log-return autocorrelation (first 120 lags = 30h)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "2026-04-26_audnzd_acf.png", dpi=120)
    plt.close()

    # -------- Persist results --------
    RESULTS_JSON.write_text(json.dumps(results, indent=2, default=str))
    print(f"\nresults written: {RESULTS_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
