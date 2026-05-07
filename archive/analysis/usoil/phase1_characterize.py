"""Phase 1 — USOIL M15 behavioral characterization (T1-T3 stats + verdict).

Brief: 2026-05-02 USOIL 15min behavioral characterization (§4 statistics).
Plan: ~/.claude/plans/usoil-15min-behavioral-composed-tower.md (Stage C step 11).

Pre-Q gate domain: data. No strategy hypothesis encoded; only descriptive
measurements that preserve the unformed question "what regime structure does
USOIL 15min exhibit?".

Computes (per brief §4):
  T1.1 ACF on log returns at lags {1,2,4,8,16,32,96,192} + Bartlett + bootstrap CI
  T1.2 Lo-MacKinlay variance ratio VR(q) for q in {2,4,8,16,32}, hetero-robust z*
  T1.3 Hurst via DFA + R/S on log RETURNS (NOT log-prices — see lib/nonlinear.py),
       both estimators with bootstrap CIs; flag if estimator-difference exceeds
       bootstrap CI width
  T1.4 ACF on |r_t| and r_t^2 at the T1.1 lag set
  T1.5 Intraday ATR(14) by 96 15min-bins (chart-TZ EST/EDT), peak-detected,
       cross-tabbed by DOW
  T1.6 Cost-floor: ATR(14) vs 3x and 5x Alchemy round-trip cost.
       HARD KILL: <30% bars clear 3x cost in 08:00-16:00 ET
  T2.1 Variance of log returns by DOW with bootstrap CI
  T2.2 EIA Wed 10:30-11:30 ET event study (4 bars), N>=30 per cell
  T2.3 Vol-expansion: low-vol regime (<25th pct trailing-20 ATR) -> next |r|, CI
  T2.4 Range/body ratio, conditional on top-quartile |r|
  T3.1 Excess kurtosis + top-N |r| share of weekly variance
  T3.2 Daily 3-sigma event count + clustering (small-cell warning per Rule 1)
  T3.3 Joint DOW x bin ATR heatmap

Outputs:
  docs/methodology/findings/2026-05-02_usoil_phase1_results.json   (full machine-readable)
  docs/methodology/findings/2026-05-02_usoil_acf.png              (T1.1 + T1.4)
  docs/methodology/findings/2026-05-02_usoil_vr.png               (T1.2)
  docs/methodology/findings/2026-05-02_usoil_hurst.png            (T1.3)
  docs/methodology/findings/2026-05-02_usoil_intraday_atr.png     (T1.5 + T3.3)
  docs/methodology/findings/2026-05-02_usoil_cost_floor.png       (T1.6)
  docs/methodology/findings/2026-05-02_usoil_eia_event.png        (T2.2)

Verdict (per brief §5 matrix; plan §Verdict logic for unmatched routing):
  abort | mean-revert | persistence | vol-gated | indeterminate

Cost reference: Alchemy DXTrade USOIL spread (Joshua-supplied; placeholder
default of $0.05 spread + $0 commission round-trip = $0.10; verify before
locking the verdict).
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
CLEAN_CSV = DATA_DIR / "bar_data" / "USOIL_oanda_m15_2022-01-04_to_2026-04-20_clean.csv"
CLEAN_HASH_FILE = DATA_DIR / "USOIL_oanda_m15_2022-01-04_to_2026-04-20_clean.sha256"

FINDINGS_DIR = REPO_ROOT / "docs" / "methodology" / "findings"
PREFIX = "2026-05-02_usoil"
RESULTS_JSON = FINDINGS_DIR / f"{PREFIX}_phase1_results.json"

NY_TZ = ZoneInfo("America/New_York")
RNG_SEED = 42

# Alchemy DXTrade USOIL cost reference (placeholder — verify before locking verdict)
ALCHEMY_USOIL_SPREAD_USD = 0.05      # $0.05 per barrel typical
ALCHEMY_USOIL_COMMISSION_USD = 0.00  # commission included in spread
ALCHEMY_RT_COST = (ALCHEMY_USOIL_SPREAD_USD + ALCHEMY_USOIL_COMMISSION_USD) * 2  # $0.10
COST_FLOOR_PRIME_HOURS_ET = (8, 16)  # 08:00-16:00 ET inclusive
COST_FLOOR_KILL_THRESHOLD_PCT = 30.0  # <30% bars clear 3x cost = HARD KILL

# T2.2 EIA Wednesday window (chart-TZ EST/EDT)
EIA_DOW = 2  # Wednesday
EIA_BIN_RANGE = (10 * 4 + 2, 11 * 4 + 1)  # bins 42..45 inclusive (10:30, 10:45, 11:00, 11:15)

LAGS = [1, 2, 4, 8, 16, 32, 96, 192]  # T1.1 / T1.4
VR_QS = [2, 4, 8, 16, 32]              # T1.2

MIN_CELL_N = 30  # T2.2 / Rule 1 small-cell threshold


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _verify_hash() -> str:
    expected = CLEAN_HASH_FILE.read_text().strip().split()[0]
    h = hashlib.sha256()
    with CLEAN_CSV.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    actual = h.hexdigest()
    if actual != expected:
        raise SystemExit(f"clean CSV hash mismatch: got {actual} expected {expected}")
    print(f"data hash OK: {actual}")
    return actual


def _bartlett_ci(n: int, alpha: float = 0.05) -> float:
    """Bartlett's white-noise null CI half-width for ACF."""
    z = 1.96 if alpha == 0.05 else 2.576
    return z / np.sqrt(n)


def _acf(x: np.ndarray, lag: int) -> float:
    """Sample ACF at a single lag, normalized by var(x). Cheap O(n)."""
    n = len(x)
    if lag >= n:
        return float("nan")
    xm = x - x.mean()
    num = np.sum(xm[:n - lag] * xm[lag:])
    den = np.sum(xm * xm)
    return float(num / den) if den > 0 else float("nan")


def _bootstrap_acf_ci(x: np.ndarray, lag: int, B: int = 1000, seed: int = RNG_SEED) -> tuple[float, float]:
    """Block bootstrap CI for ACF at one lag. Block size = max(50, lag*4)."""
    rng = np.random.default_rng(seed)
    n = len(x)
    block = max(50, lag * 4)
    n_blocks = n // block
    if n_blocks < 10:
        return float("nan"), float("nan")
    acfs = []
    for _ in range(B):
        idx = rng.integers(0, n_blocks, size=n_blocks)
        sample = np.concatenate([x[i * block:(i + 1) * block] for i in idx])
        acfs.append(_acf(sample, lag))
    lo, hi = np.percentile(acfs, [2.5, 97.5])
    return float(lo), float(hi)


def _lo_mackinlay_vr(r: np.ndarray, q: int) -> tuple[float, float, float]:
    """Lo-MacKinlay variance ratio VR(q), heteroscedasticity-robust z*, p-value (two-sided).

    VR(q) = Var(r_q) / (q * Var(r_1))
    Hetero-robust z* = sqrt(nq) * (VR(q) - 1) / sqrt(theta(q))
    where theta(q) = sum_{j=1}^{q-1} ((2(q-j)/q)^2 * delta_j) and
    delta_j = sum (mu_t * mu_{t-j})^2 / (sum mu_t^2)^2
    with mu_t = (r_t - mean(r)).
    """
    nq = len(r)
    if nq < q + 10:
        return float("nan"), float("nan"), float("nan")
    mu = r - r.mean()
    var_r = np.sum(mu * mu) / nq
    # q-period overlapping returns
    rq = np.array([r[i:i + q].sum() for i in range(nq - q + 1)])
    mq = rq - rq.mean()
    var_rq = np.sum(mq * mq) / (nq - q + 1)
    vr = var_rq / (q * var_r) if var_r > 0 else float("nan")
    # Hetero-robust theta
    mu2 = mu * mu
    den = mu2.sum() ** 2
    theta = 0.0
    for j in range(1, q):
        prod = mu[j:] * mu[:-j]
        delta_j = np.sum(prod * prod) / den * nq
        weight = (2.0 * (q - j) / q) ** 2
        theta += weight * delta_j
    if theta <= 0:
        return float(vr), float("nan"), float("nan")
    z_star = np.sqrt(nq) * (vr - 1.0) / np.sqrt(theta)
    # Two-sided p-value
    from math import erfc, sqrt
    p = erfc(abs(z_star) / sqrt(2.0))
    return float(vr), float(z_star), float(p)


def _rs_one_window(window: np.ndarray) -> float:
    """R/S statistic for a single window (called inside hurst_rs estimator)."""
    x = window - window.mean()
    z = np.cumsum(x)
    r = z.max() - z.min()
    s = window.std(ddof=0)
    return float(r / s) if s > 0 else float("nan")


def _hurst_rs(returns: np.ndarray, lags: np.ndarray) -> tuple[float, float, float, list, list]:
    """R/S Hurst slope over a band of lags, with bootstrap CI.

    Returns (H, lo95, hi95, lags_used, log_rs_means).
    """
    rng = np.random.default_rng(RNG_SEED)
    log_lags = []
    log_rs = []
    for L in lags:
        n_win = len(returns) // int(L)
        if n_win < 2:
            continue
        rs_vals = [_rs_one_window(returns[i * int(L):(i + 1) * int(L)]) for i in range(n_win)]
        rs_vals = [v for v in rs_vals if not np.isnan(v) and v > 0]
        if not rs_vals:
            continue
        log_lags.append(np.log(int(L)))
        log_rs.append(np.log(np.mean(rs_vals)))
    if len(log_lags) < 4:
        return float("nan"), float("nan"), float("nan"), [], []
    log_lags = np.array(log_lags)
    log_rs = np.array(log_rs)
    slope, intercept = np.polyfit(log_lags, log_rs, 1)
    fitted = slope * log_lags + intercept
    resid = log_rs - fitted
    boot_slopes = []
    for _ in range(2000):
        b_resid = rng.choice(resid, size=len(resid), replace=True)
        b_y = fitted + b_resid
        b_slope, _ = np.polyfit(log_lags, b_y, 1)
        boot_slopes.append(b_slope)
    lo, hi = np.percentile(boot_slopes, [2.5, 97.5])
    return float(slope), float(lo), float(hi), log_lags.tolist(), log_rs.tolist()


def _hurst_dfa(returns: np.ndarray, scales: np.ndarray) -> tuple[float, float, float, list, list]:
    """DFA-1 Hurst exponent (alpha) over scales, with bootstrap CI.

    For DFA on a returns series: integrate to a profile y_t = cumsum(returns - mean).
    For each scale n, split y into windows of size n, polynomial(degree=1)-detrend
    each window, compute RMS. Slope of log(RMS) vs log(n) = alpha (Hurst-like).
    For random-walk increments alpha ~ 0.5; persistent ~ >0.5; mean-rev ~ <0.5.
    """
    rng = np.random.default_rng(RNG_SEED + 1)
    y = np.cumsum(returns - returns.mean())
    log_n = []
    log_f = []
    for n in scales:
        n = int(n)
        n_win = len(y) // n
        if n_win < 4:
            continue
        rms_vals = []
        for i in range(n_win):
            seg = y[i * n:(i + 1) * n]
            t = np.arange(n)
            coeffs = np.polyfit(t, seg, 1)
            trend = np.polyval(coeffs, t)
            rms_vals.append(np.sqrt(np.mean((seg - trend) ** 2)))
        rms_mean = np.mean(rms_vals) if rms_vals else 0
        if rms_mean > 0:
            log_n.append(np.log(n))
            log_f.append(np.log(rms_mean))
    if len(log_n) < 4:
        return float("nan"), float("nan"), float("nan"), [], []
    log_n = np.array(log_n)
    log_f = np.array(log_f)
    slope, intercept = np.polyfit(log_n, log_f, 1)
    fitted = slope * log_n + intercept
    resid = log_f - fitted
    boot_slopes = []
    for _ in range(2000):
        b_resid = rng.choice(resid, size=len(resid), replace=True)
        b_y = fitted + b_resid
        b_slope, _ = np.polyfit(log_n, b_y, 1)
        boot_slopes.append(b_slope)
    lo, hi = np.percentile(boot_slopes, [2.5, 97.5])
    return float(slope), float(lo), float(hi), log_n.tolist(), log_f.tolist()


def _bootstrap_var_ci(x: np.ndarray, B: int = 1000, seed: int = RNG_SEED) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    n = len(x)
    if n < 30:
        return float("nan"), float("nan")
    vars_ = [np.var(rng.choice(x, size=n, replace=True)) for _ in range(B)]
    lo, hi = np.percentile(vars_, [2.5, 97.5])
    return float(lo), float(hi)


def _bootstrap_mean_ci(x: np.ndarray, B: int = 1000, seed: int = RNG_SEED) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    n = len(x)
    if n < 10:
        return float("nan"), float("nan")
    means = [np.mean(rng.choice(x, size=n, replace=True)) for _ in range(B)]
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(lo), float(hi)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    FINDINGS_DIR.mkdir(parents=True, exist_ok=True)
    data_hash = _verify_hash()

    df = pd.read_csv(CLEAN_CSV)
    print(f"loaded {len(df):,} rows")

    # Parse times. NY fields derived from time_utc; the dt_ny string column from
    # phase1_clean is informational and not parsed here (mixed -05:00/-04:00 across
    # DST would require utc=True which loses the local-clock info anyway).
    df["time_utc"] = pd.to_datetime(df["time"].str[:23] + "Z", format="%Y-%m-%dT%H:%M:%S.%fZ", utc=True)
    df["ny_dt"] = df["time_utc"].dt.tz_convert(NY_TZ)
    df["ny_hour"] = df["ny_dt"].dt.hour
    df["ny_minute"] = df["ny_dt"].dt.minute
    df["ny_dow"] = df["ny_dt"].dt.dayofweek  # 0=Mon
    df["ny_bin"] = df["ny_hour"] * 4 + df["ny_minute"] // 15  # 0..95
    df["utc_date"] = df["time_utc"].dt.date

    # Numeric
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["is_maintenance"] = df["is_maintenance"].astype(str).str.lower() == "true"
    df["is_holiday_short"] = df["is_holiday_short"].astype(str).str.lower() == "true"

    # Returns (exclude maintenance bars from return-distribution per Pre-Q gate D1)
    df["log_ret"] = np.log(df["close"]).diff()
    df.loc[df["is_maintenance"], "log_ret"] = np.nan

    # ATR(14) on M15
    pc = df["close"].shift(1)
    tr = np.maximum.reduce([
        (df["high"] - df["low"]).values,
        np.abs((df["high"] - pc).values),
        np.abs((df["low"] - pc).values),
    ])
    df["tr"] = tr
    df["atr14"] = pd.Series(tr).rolling(14, min_periods=14).mean().values

    log_ret = df["log_ret"].dropna().values
    n_ret = len(log_ret)
    print(f"clean returns (excl maintenance): {n_ret:,}")

    results: dict = {
        "data_hash": data_hash,
        "n_bars": int(len(df)),
        "n_returns": int(n_ret),
        "first_bar_utc": str(df["time_utc"].iloc[0]),
        "last_bar_utc": str(df["time_utc"].iloc[-1]),
        "alchemy_rt_cost_usd": ALCHEMY_RT_COST,
        "alchemy_spread_usd": ALCHEMY_USOIL_SPREAD_USD,
        "alchemy_commission_usd": ALCHEMY_USOIL_COMMISSION_USD,
    }

    # ---- T1.1 ACF on log returns ----
    bartlett = _bartlett_ci(n_ret)
    t11 = {}
    for L in LAGS:
        rho = _acf(log_ret, L)
        boot_lo, boot_hi = _bootstrap_acf_ci(log_ret, L, B=500)
        t11[str(L)] = {
            "rho": rho, "bartlett_ci": bartlett,
            "boot_ci95_lo": boot_lo, "boot_ci95_hi": boot_hi,
            "sig_at_bartlett": abs(rho) > bartlett,
        }
    results["T1_1_acf_returns"] = t11
    print(f"T1.1 ACF lag1 = {t11['1']['rho']:.4f} (Bartlett ±{bartlett:.4f})")

    # ---- T1.2 Lo-MacKinlay VR ----
    t12 = {}
    for q in VR_QS:
        vr, z, p = _lo_mackinlay_vr(log_ret, q)
        t12[str(q)] = {"vr": vr, "z_star": z, "p_two_sided": p,
                       "interpretation": (
                           "trending" if vr > 1 and p < 0.05 else
                           "mean-reverting" if vr < 1 and p < 0.05 else
                           "random-walk consistent"
                       )}
    results["T1_2_variance_ratio"] = t12
    print(f"T1.2 VR(8) = {t12['8']['vr']:.4f} z* = {t12['8']['z_star']:.3f} p = {t12['8']['p_two_sided']:.4g}")

    # ---- T1.3 Hurst (DFA + R/S) ----
    rs_lags = np.unique(np.round(np.geomspace(16, 4096, num=18)).astype(int))
    rs_H, rs_lo, rs_hi, rs_loglag, rs_logrs = _hurst_rs(log_ret, rs_lags)
    dfa_H, dfa_lo, dfa_hi, dfa_logn, dfa_logf = _hurst_dfa(log_ret, rs_lags)
    rs_ci_width = rs_hi - rs_lo if not np.isnan(rs_hi) else float("nan")
    dfa_ci_width = dfa_hi - dfa_lo if not np.isnan(dfa_hi) else float("nan")
    estimator_diff = abs(rs_H - dfa_H) if not (np.isnan(rs_H) or np.isnan(dfa_H)) else float("nan")
    max_ci_width = max(rs_ci_width, dfa_ci_width) if not (np.isnan(rs_ci_width) or np.isnan(dfa_ci_width)) else float("nan")
    needs_review = estimator_diff > max_ci_width if not np.isnan(max_ci_width) else False
    t13 = {
        "rs":  {"H": rs_H, "ci95_lo": rs_lo, "ci95_hi": rs_hi, "ci_width": rs_ci_width},
        "dfa": {"H": dfa_H, "ci95_lo": dfa_lo, "ci95_hi": dfa_hi, "ci_width": dfa_ci_width},
        "estimator_difference": estimator_diff,
        "max_ci_width": max_ci_width,
        "needs_joint_review": bool(needs_review),
    }
    results["T1_3_hurst"] = t13
    print(f"T1.3 Hurst R/S = {rs_H:.4f} CI=[{rs_lo:.3f},{rs_hi:.3f}]  DFA = {dfa_H:.4f} CI=[{dfa_lo:.3f},{dfa_hi:.3f}]")
    print(f"     diff = {estimator_diff:.4f} max_CI_width = {max_ci_width:.4f} needs_review = {needs_review}")

    # ---- T1.4 ACF on |r| and r^2 ----
    abs_ret = np.abs(log_ret)
    sq_ret = log_ret ** 2
    t14_abs = {str(L): {"rho": _acf(abs_ret, L), "bartlett_ci": bartlett,
                         "sig_at_bartlett": abs(_acf(abs_ret, L)) > bartlett}
               for L in LAGS}
    t14_sq  = {str(L): {"rho": _acf(sq_ret, L),  "bartlett_ci": bartlett,
                         "sig_at_bartlett": abs(_acf(sq_ret, L)) > bartlett}
               for L in LAGS}
    results["T1_4_acf_abs_returns"] = t14_abs
    results["T1_4_acf_sq_returns"]  = t14_sq
    print(f"T1.4 ACF|r| lag1 = {t14_abs['1']['rho']:.4f}  ACF|r| lag96 = {t14_abs['96']['rho']:.4f}")

    # ---- T1.5 Intraday ATR by NY 15min bin ----
    bin_atr = df.groupby("ny_bin")["atr14"].agg(["mean", "median", "count"]).to_dict("index")
    bin_atr_clean = {int(b): {"mean": float(d["mean"]), "median": float(d["median"]), "count": int(d["count"])}
                     for b, d in bin_atr.items() if not np.isnan(d["mean"])}
    # Peak-detect: top-3 bins by median ATR
    sorted_bins = sorted(bin_atr_clean.items(), key=lambda kv: -kv[1]["median"])
    top3_bins = [int(b) for b, _ in sorted_bins[:3]]
    bottom3_bins = [int(b) for b, _ in sorted_bins[-3:]]
    peak_to_trough_ratio = sorted_bins[0][1]["median"] / max(sorted_bins[-1][1]["median"], 1e-9)
    # DOW cross-tab
    dow_bin_atr = df.groupby(["ny_dow", "ny_bin"])["atr14"].median().unstack(fill_value=np.nan)
    results["T1_5_intraday_atr"] = {
        "bin_atr": bin_atr_clean,
        "top3_bins_by_median": top3_bins,
        "bottom3_bins_by_median": bottom3_bins,
        "peak_to_trough_ratio": float(peak_to_trough_ratio),
        "dow_bin_atr_median": {int(d): {int(b): (float(v) if not np.isnan(v) else None)
                                          for b, v in row.items()}
                                for d, row in dow_bin_atr.iterrows()},
    }
    print(f"T1.5 top-3 bins (by median ATR): {top3_bins}  peak/trough ratio = {peak_to_trough_ratio:.2f}")

    # ---- T1.6 Cost floor ----
    df_active = df[(df["ny_hour"] >= COST_FLOOR_PRIME_HOURS_ET[0]) &
                   (df["ny_hour"] < COST_FLOOR_PRIME_HOURS_ET[1]) &
                   (df["ny_dow"] < 5) & (~df["is_maintenance"])].copy()
    n_active = len(df_active)
    n_clear_3x = int((df_active["atr14"] > 3 * ALCHEMY_RT_COST).sum())
    n_clear_5x = int((df_active["atr14"] > 5 * ALCHEMY_RT_COST).sum())
    pct_3x = n_clear_3x / max(1, n_active) * 100
    pct_5x = n_clear_5x / max(1, n_active) * 100
    cost_floor_pass = pct_3x >= COST_FLOOR_KILL_THRESHOLD_PCT
    # By hour
    hourly = df_active.groupby("ny_hour").apply(
        lambda g: pd.Series({
            "n": len(g),
            "median_atr": float(g["atr14"].median()),
            "pct_clear_3x_cost": float((g["atr14"] > 3 * ALCHEMY_RT_COST).mean() * 100),
            "pct_clear_5x_cost": float((g["atr14"] > 5 * ALCHEMY_RT_COST).mean() * 100),
        }), include_groups=False
    ).to_dict("index")
    results["T1_6_cost_floor"] = {
        "round_trip_cost_usd": ALCHEMY_RT_COST,
        "n_active_window_bars": n_active,
        "n_clear_3x_cost": n_clear_3x,
        "n_clear_5x_cost": n_clear_5x,
        "pct_clear_3x_cost": pct_3x,
        "pct_clear_5x_cost": pct_5x,
        "kill_threshold_pct": COST_FLOOR_KILL_THRESHOLD_PCT,
        "cost_floor_pass": cost_floor_pass,
        "by_hour_active": {int(h): {k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
                                     for k, v in d.items()} for h, d in hourly.items()},
    }
    print(f"T1.6 cost floor: {pct_3x:.1f}% bars clear 3x cost (kill if <{COST_FLOOR_KILL_THRESHOLD_PCT}%) -> {'PASS' if cost_floor_pass else 'KILL'}")

    # ---- T2.1 Variance by DOW ----
    t21 = {}
    for d in range(7):
        sub = log_ret[df.dropna(subset=["log_ret"])["ny_dow"].values == d] if False else None  # avoid alignment bug
        sub = df[df["ny_dow"] == d]["log_ret"].dropna().values
        if len(sub) < MIN_CELL_N:
            t21[d] = {"n": int(len(sub)), "var": None, "ci_lo": None, "ci_hi": None,
                      "note": f"underpowered (n={len(sub)}<{MIN_CELL_N})"}
            continue
        v = float(np.var(sub))
        lo, hi = _bootstrap_var_ci(sub, B=500)
        t21[d] = {"n": int(len(sub)), "var": v, "ci_lo": lo, "ci_hi": hi}
    results["T2_1_variance_by_dow"] = {int(k): v for k, v in t21.items()}
    print(f"T2.1 variance by DOW: " + ", ".join(
        f"{['M','T','W','R','F','S','U'][d]}={t21[d].get('var', float('nan')):.2e}" if t21[d].get("var") else f"{['M','T','W','R','F','S','U'][d]}=n/a"
        for d in range(7)
    ))

    # ---- T2.2 EIA event study ----
    eia_mask = ((df["ny_dow"] == EIA_DOW) &
                (df["ny_bin"] >= EIA_BIN_RANGE[0]) & (df["ny_bin"] <= EIA_BIN_RANGE[1]))
    other_wkday_mask = ((df["ny_dow"].isin([0, 1, 3, 4])) &
                        (df["ny_bin"] >= EIA_BIN_RANGE[0]) & (df["ny_bin"] <= EIA_BIN_RANGE[1]))
    eia_abs = df.loc[eia_mask, "log_ret"].dropna().abs().values
    other_abs = df.loc[other_wkday_mask, "log_ret"].dropna().abs().values
    if len(eia_abs) < MIN_CELL_N:
        t22 = {"n_eia": int(len(eia_abs)), "n_other": int(len(other_abs)),
               "note": f"underpowered (n_eia={len(eia_abs)}<{MIN_CELL_N})"}
    else:
        ratio = float(eia_abs.mean() / max(other_abs.mean(), 1e-12))
        eia_ci = _bootstrap_mean_ci(eia_abs, B=500)
        other_ci = _bootstrap_mean_ci(other_abs, B=500)
        t22 = {
            "n_eia": int(len(eia_abs)),
            "n_other": int(len(other_abs)),
            "mean_abs_ret_eia": float(eia_abs.mean()),
            "mean_abs_ret_other": float(other_abs.mean()),
            "eia_to_other_ratio": ratio,
            "eia_ci95": eia_ci,
            "other_ci95": other_ci,
        }
    results["T2_2_eia_event_study"] = t22
    print(f"T2.2 EIA n_eia={t22.get('n_eia', 0)} n_other={t22.get('n_other', 0)} " +
          (f"ratio={t22['eia_to_other_ratio']:.2f}x" if "eia_to_other_ratio" in t22 else "(underpowered)"))

    # ---- T2.3 Vol expansion ----
    df["atr_pct25_trail20"] = df["atr14"].rolling(20, min_periods=20).quantile(0.25)
    df["is_low_vol"] = df["atr14"] < df["atr_pct25_trail20"]
    # Transition: low_vol bar followed by next-bar (which is by definition not low-vol if we condition)
    df["next_abs_ret"] = df["log_ret"].shift(-1).abs()
    df["next4_abs_ret"] = df["log_ret"].shift(-1).abs() + df["log_ret"].shift(-2).abs() + \
                          df["log_ret"].shift(-3).abs() + df["log_ret"].shift(-4).abs()
    transitions = df[df["is_low_vol"] & ~df["is_maintenance"]].dropna(subset=["next_abs_ret"])
    uncond = df["log_ret"].dropna().abs()
    n_trans = len(transitions)
    if n_trans < MIN_CELL_N:
        t23 = {"n_transitions": int(n_trans), "note": "underpowered"}
    else:
        next1_mean = float(transitions["next_abs_ret"].mean())
        uncond_mean = float(uncond.mean())
        ratio = next1_mean / max(uncond_mean, 1e-12)
        next1_ci = _bootstrap_mean_ci(transitions["next_abs_ret"].values, B=500)
        t23 = {
            "n_transitions": int(n_trans),
            "next_bar_abs_ret_mean": next1_mean,
            "uncond_abs_ret_mean": uncond_mean,
            "ratio_next_to_uncond": ratio,
            "next_bar_ci95": next1_ci,
        }
    results["T2_3_vol_expansion"] = t23
    print(f"T2.3 vol-expansion ratio = {t23.get('ratio_next_to_uncond', float('nan')):.3f}")

    # ---- T2.4 Range/body ratio (conditional on top-quartile |r|) ----
    df["bar_range"] = df["high"] - df["low"]
    df["bar_body"] = (df["close"] - df["open"]).abs()
    df["range_body_ratio"] = df["bar_body"] / df["bar_range"].replace(0, np.nan)
    df["abs_ret"] = df["log_ret"].abs()
    q75 = df["abs_ret"].quantile(0.75)
    top_q = df[df["abs_ret"] > q75]
    rb_top_median = float(top_q["range_body_ratio"].median())
    rb_uncond_median = float(df["range_body_ratio"].median())
    results["T2_4_range_body_ratio"] = {
        "uncond_median_body_over_range": rb_uncond_median,
        "topq_median_body_over_range": rb_top_median,
        "topq_n": int(len(top_q)),
        "q75_abs_ret_threshold": float(q75),
    }
    print(f"T2.4 body/range median: uncond={rb_uncond_median:.3f}  top-q={rb_top_median:.3f}")

    # ---- T3.1 Tails ----
    excess_kurt = float(pd.Series(log_ret).kurtosis())  # pandas excess (Fisher)
    weekly_var_breakdown = {}
    df_w = df.dropna(subset=["log_ret"]).copy()
    df_w["week"] = df_w["time_utc"].dt.isocalendar().week.astype(int)
    df_w["year"] = df_w["time_utc"].dt.isocalendar().year.astype(int)
    week_groups = df_w.groupby(["year", "week"])
    var_share_top1 = []
    var_share_top5 = []
    var_share_top20 = []
    for _, g in week_groups:
        if len(g) < 50:
            continue
        sq = (g["log_ret"] ** 2).sort_values(ascending=False).values
        total = sq.sum()
        if total <= 0:
            continue
        var_share_top1.append(sq[:1].sum() / total)
        var_share_top5.append(sq[:5].sum() / total)
        var_share_top20.append(sq[:20].sum() / total)
    results["T3_1_tails"] = {
        "excess_kurtosis": excess_kurt,
        "weekly_var_share_top1_mean": float(np.mean(var_share_top1)) if var_share_top1 else None,
        "weekly_var_share_top5_mean": float(np.mean(var_share_top5)) if var_share_top5 else None,
        "weekly_var_share_top20_mean": float(np.mean(var_share_top20)) if var_share_top20 else None,
    }
    print(f"T3.1 excess kurt = {excess_kurt:.2f}")

    # ---- T3.2 3-sigma daily events ----
    daily = df.groupby("utc_date")["log_ret"].sum().rename("daily_ret")
    daily_std = daily.std()
    n_3sig = int((daily.abs() > 3 * daily_std).sum())
    results["T3_2_three_sigma_days"] = {
        "n_days_total": int(len(daily)),
        "daily_std": float(daily_std),
        "n_3sigma_days": n_3sig,
        "small_cell_warning": n_3sig < MIN_CELL_N,
    }
    print(f"T3.2 3-sigma days = {n_3sig} (daily_std={daily_std:.4f})")

    # ---- T3.3 Joint DOW x bin heatmap is already in T1_5; data captured there. ----

    # ---------------- VERDICT (per brief §5 + plan unmatched routing) ----------------
    acf1 = t11["1"]["rho"]
    acf1_sig = abs(acf1) > bartlett
    vr8 = t12["8"]["vr"]
    vr8_sig = (t12["8"]["p_two_sided"] is not None) and (t12["8"]["p_two_sided"] < 0.05)
    H_use = rs_H if not np.isnan(rs_H) else dfa_H
    acf_abs1 = t14_abs["1"]["rho"]
    acf_abs96 = t14_abs["96"]["rho"]
    intraday_strong = peak_to_trough_ratio > 1.5

    verdict_path = []
    if not cost_floor_pass:
        verdict = "abort"
        verdict_path.append("T1.6 cost floor failed: insufficient bars clear 3x Alchemy round-trip cost in active window")
    elif acf1 < -0.05 and acf1_sig and vr8 < 1 and vr8_sig and H_use < 0.45:
        verdict = "mean-revert"
        verdict_path.append(f"ACF(1)={acf1:.3f} sig negative; VR(8)={vr8:.3f} sig <1; H={H_use:.3f}<0.45")
    elif acf1 > 0.05 and acf1_sig and vr8 > 1 and vr8_sig and H_use > 0.55:
        verdict = "persistence"
        verdict_path.append(f"ACF(1)={acf1:.3f} sig positive; VR(8)={vr8:.3f} sig >1; H={H_use:.3f}>0.55")
    elif abs(acf1) < 0.05 and acf_abs1 > 0.10 and intraday_strong:
        verdict = "vol-gated"
        verdict_path.append(f"ACF(1)={acf1:.3f} weak; ACF|r|(1)={acf_abs1:.3f}>0.10; intraday peak/trough={peak_to_trough_ratio:.2f}>1.5")
    elif abs(acf1) < 0.05 and not vr8_sig and 0.45 <= H_use <= 0.55 and abs(acf_abs1) < 0.10:
        verdict = "abort"
        verdict_path.append("All four T1 dimensions random-walk consistent — coin flip")
    else:
        verdict = "indeterminate"
        verdict_path.append("Pattern does not cleanly match abort / mean-revert / persistence / vol-gated; explicit description required in brief")

    results["verdict"] = verdict
    results["verdict_rationale"] = verdict_path
    print(f"\n=== VERDICT: {verdict} ===")
    for p in verdict_path:
        print(f"  - {p}")

    # ---------------- PLOTS ----------------
    print("\nGenerating plots...")

    # ACF (T1.1 + T1.4)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    lags_plot = np.array(LAGS)
    axes[0].bar(range(len(lags_plot)), [t11[str(L)]["rho"] for L in lags_plot])
    axes[0].axhline(bartlett, color="red", ls="--", alpha=0.5, label=f"±Bartlett {bartlett:.4f}")
    axes[0].axhline(-bartlett, color="red", ls="--", alpha=0.5)
    axes[0].axhline(0, color="black", lw=0.5)
    axes[0].set_xticks(range(len(lags_plot)))
    axes[0].set_xticklabels([str(L) for L in lags_plot])
    axes[0].set_xlabel("Lag (M15 bars)")
    axes[0].set_ylabel("ACF of log returns")
    axes[0].set_title("T1.1 ACF(returns)")
    axes[0].legend(fontsize=8)
    axes[0].grid(True, alpha=0.3)
    axes[1].bar(range(len(lags_plot)), [t14_abs[str(L)]["rho"] for L in lags_plot], color="orange")
    axes[1].axhline(bartlett, color="red", ls="--", alpha=0.5, label=f"±Bartlett {bartlett:.4f}")
    axes[1].axhline(-bartlett, color="red", ls="--", alpha=0.5)
    axes[1].set_xticks(range(len(lags_plot)))
    axes[1].set_xticklabels([str(L) for L in lags_plot])
    axes[1].set_xlabel("Lag (M15 bars)")
    axes[1].set_ylabel("ACF of |log returns|")
    axes[1].set_title("T1.4 ACF(|returns|)")
    axes[1].legend(fontsize=8)
    axes[1].grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(FINDINGS_DIR / f"{PREFIX}_acf.png", dpi=120)
    plt.close()

    # VR (T1.2)
    fig, ax = plt.subplots(figsize=(7, 4))
    qs = np.array(VR_QS)
    vrs = np.array([t12[str(q)]["vr"] for q in qs])
    zs = np.array([t12[str(q)]["z_star"] for q in qs])
    ax.plot(qs, vrs, "o-", label="VR(q)")
    ax.axhline(1.0, color="black", ls="--", lw=0.5, label="VR=1 (random walk)")
    for x, v, z in zip(qs, vrs, zs):
        ax.annotate(f"z*={z:.2f}", (x, v), textcoords="offset points", xytext=(5, 5), fontsize=8)
    ax.set_xscale("log")
    ax.set_xticks(qs)
    ax.set_xticklabels(qs)
    ax.set_xlabel("Aggregation q (M15 bars)")
    ax.set_ylabel("VR(q)")
    ax.set_title("T1.2 Lo-MacKinlay variance ratio")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(FINDINGS_DIR / f"{PREFIX}_vr.png", dpi=120)
    plt.close()

    # Hurst (T1.3)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    if rs_loglag:
        axes[0].plot(rs_loglag, rs_logrs, "o-")
        axes[0].set_xlabel("log(lag)")
        axes[0].set_ylabel("log(R/S)")
        axes[0].set_title(f"T1.3 R/S Hurst: H={rs_H:.3f} CI=[{rs_lo:.3f},{rs_hi:.3f}]")
        axes[0].grid(True, alpha=0.3)
    if dfa_logn:
        axes[1].plot(dfa_logn, dfa_logf, "o-", color="orange")
        axes[1].set_xlabel("log(scale n)")
        axes[1].set_ylabel("log(F(n))")
        axes[1].set_title(f"T1.3 DFA-1: alpha={dfa_H:.3f} CI=[{dfa_lo:.3f},{dfa_hi:.3f}]")
        axes[1].grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(FINDINGS_DIR / f"{PREFIX}_hurst.png", dpi=120)
    plt.close()

    # Intraday ATR heatmap (T1.5 + T3.3)
    fig, axes = plt.subplots(1, 2, figsize=(13, 4))
    bins = sorted(bin_atr_clean.keys())
    medians = [bin_atr_clean[b]["median"] for b in bins]
    axes[0].bar(bins, medians)
    for tb in top3_bins:
        axes[0].axvspan(tb - 0.4, tb + 0.4, color="orange", alpha=0.3)
    axes[0].set_xlabel("15min bin of day (NY)")
    axes[0].set_ylabel("Median ATR(14)")
    axes[0].set_title(f"T1.5 Intraday ATR by NY 15min bin (peak/trough = {peak_to_trough_ratio:.2f})")
    axes[0].grid(True, alpha=0.3)
    # Heatmap DOW × bin
    heatmap = dow_bin_atr.values
    im = axes[1].imshow(heatmap, aspect="auto", origin="lower", cmap="viridis")
    axes[1].set_yticks(range(7))
    axes[1].set_yticklabels(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    axes[1].set_xlabel("15min bin of day (NY)")
    axes[1].set_title("T3.3 ATR heatmap DOW × bin")
    plt.colorbar(im, ax=axes[1], label="Median ATR(14)")
    plt.tight_layout()
    plt.savefig(FINDINGS_DIR / f"{PREFIX}_intraday_atr.png", dpi=120)
    plt.close()

    # Cost floor (T1.6)
    fig, ax = plt.subplots(figsize=(8, 4))
    hours = sorted(results["T1_6_cost_floor"]["by_hour_active"].keys())
    pct3 = [results["T1_6_cost_floor"]["by_hour_active"][h]["pct_clear_3x_cost"] for h in hours]
    pct5 = [results["T1_6_cost_floor"]["by_hour_active"][h]["pct_clear_5x_cost"] for h in hours]
    x = np.arange(len(hours))
    ax.bar(x - 0.2, pct3, 0.4, label="% clear 3× cost")
    ax.bar(x + 0.2, pct5, 0.4, label="% clear 5× cost")
    ax.axhline(COST_FLOOR_KILL_THRESHOLD_PCT, color="red", ls="--",
               label=f"kill threshold {COST_FLOOR_KILL_THRESHOLD_PCT}%")
    ax.set_xticks(x)
    ax.set_xticklabels(hours)
    ax.set_xlabel("Hour (NY)")
    ax.set_ylabel("% bars (active hours, weekdays)")
    ax.set_title(f"T1.6 ATR(14) vs Alchemy round-trip cost ${ALCHEMY_RT_COST:.2f}")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(FINDINGS_DIR / f"{PREFIX}_cost_floor.png", dpi=120)
    plt.close()

    # EIA (T2.2)
    fig, ax = plt.subplots(figsize=(7, 4))
    if "eia_to_other_ratio" in t22:
        labels = ["Wed 10:30-11:15 ET\n(EIA window)", "Mon/Tue/Thu/Fri\nsame bins"]
        vals = [t22["mean_abs_ret_eia"], t22["mean_abs_ret_other"]]
        ax.bar(labels, vals, color=["red", "gray"])
        ax.set_ylabel("Mean |log return|")
        ax.set_title(f"T2.2 EIA window vs baseline (ratio = {t22['eia_to_other_ratio']:.2f}×)")
    else:
        ax.text(0.5, 0.5, "EIA: underpowered", ha="center", va="center", transform=ax.transAxes)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(FINDINGS_DIR / f"{PREFIX}_eia_event.png", dpi=120)
    plt.close()

    print(f"plots written to {FINDINGS_DIR}")

    # ---- Persist results ----
    RESULTS_JSON.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"\nresults: {RESULTS_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
