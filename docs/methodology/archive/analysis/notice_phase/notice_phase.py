"""
Notice phase: drill-down on the three highest-leverage findings from
analysis/bar_data_high_leverage.md.

Threads (observation only — no recommendations, no MC reruns, no overlay
proposals, no strategy changes):
  A. XAUUSD regime: WHEN and HOW (inflection, drift attribution, ATR
     auto-sizing fidelity, run-length).
  B. Joint correlation: WHEN and HOW (rolling traces, event vs pervasive,
     intraday vs daily structure).
  C. Vol clustering vs portfolio_mc bootstrap (empirical vs bootstrap
     max-consecutive-negative-week distributions, GARCH(1,1) fit).

Reuses load/daily semantics from analysis/bar_analysis.py.
Bootstrap semantics for Thread C2 mirror portfolio_mc.build_week_blocks +
run_seed (Mon-anchored 5-day non-overlapping blocks, sampled with replacement).
"""

import json
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.stattools import acf
from arch import arch_model

ROOT = Path(__file__).resolve().parent
FIG = ROOT / "figures"
FIG.mkdir(parents=True, exist_ok=True)

BAR_DIR = Path("C:/Users/joshu/prop_firm_pipeline/data/bar_data")
PATHS = {
    "XAUUSD": BAR_DIR / "XAUUSD.csv",
    "US30":   BAR_DIR / "US30USD.csv",
    "USDJPY": BAR_DIR / "USDJPY.csv",
}

# ── Loader (matches bar_analysis.py semantics) ───────────────────────────

def load_bars(name, path):
    df = pd.read_csv(path)
    df["time_utc"] = pd.to_datetime(df["time"], utc=True)
    df["time_ny"]  = df["time_utc"].dt.tz_convert("America/New_York")
    df = df.set_index("time_ny").drop(columns=["time"]).sort_index()
    df["ret"]   = np.log(df["close"]).diff()
    df["range"] = (df["high"] - df["low"]) / df["close"]
    df["sym"]   = name
    return df


def daily_panel(df):
    """Per-NY-date close-to-close log return + true-range % aggregated from 15m."""
    g = df.groupby(df.index.date)
    out = pd.DataFrame({
        "open":  g["open"].first(),
        "high":  g["high"].max(),
        "low":   g["low"].min(),
        "close": g["close"].last(),
        "ret":   g["close"].last().apply(np.log).diff(),
        "rv":    g["ret"].apply(lambda x: np.sqrt(np.sum(x**2))),
        "range_pct": (g["high"].max() - g["low"].min()) / g["close"].last(),
        "n_bars": g.size(),
    })
    out.index = pd.to_datetime(out.index)
    return out


print("Loading bar data ...")
bars = {n: load_bars(n, p) for n, p in PATHS.items()}
D = {n: daily_panel(df) for n, df in bars.items()}

# Sanity dump for Rule 0 audit trail
sanity = {
    n: {
        "n_bars": int(len(df)),
        "first_bar": str(df.index[0]),
        "last_bar":  str(df.index[-1]),
        "n_nan": int(df["ret"].isna().sum() - 1),  # first-row NaN expected
        "n_days": int(len(D[n])),
    } for n, df in bars.items()
}
with open(ROOT / "rule0_sanity.json", "w") as f:
    json.dump(sanity, f, indent=2)
print(json.dumps(sanity, indent=2))


# ════════════════════════════════════════════════════════════════════════
# THREAD A — XAUUSD regime: WHEN and HOW
# ════════════════════════════════════════════════════════════════════════

xau = D["XAUUSD"].dropna(subset=["ret"]).copy()
xau_15m = bars["XAUUSD"].dropna(subset=["ret"]).copy()

# ── A1. Inflection date ──────────────────────────────────────────────────

def rolling_annvol(daily_ret, window):
    return daily_ret.rolling(window).std() * np.sqrt(252) * 100


a1_results = {}
for win in (20, 30, 60):
    rv = rolling_annvol(xau["ret"], win)
    above_20 = rv > 20.0
    if not above_20.any():
        a1_results[f"win_{win}"] = {"crossover_date": None}
        continue
    # First date where rolling vol crosses above 20% AND never falls back below 15% afterwards
    crossover = None
    cross_dates = rv.index[above_20]
    for cdate in cross_dates:
        post = rv.loc[cdate:]
        if (post < 15.0).any():
            continue
        crossover = cdate
        break
    a1_results[f"win_{win}"] = {
        "crossover_date": str(crossover.date()) if crossover is not None else None,
        "vol_at_crossover_pct": float(rv.loc[crossover]) if crossover is not None else None,
        "rolling_vol_post_min_pct": float(rv.loc[crossover:].min()) if crossover is not None else None,
        "rolling_vol_post_max_pct": float(rv.loc[crossover:].max()) if crossover is not None else None,
    }

with open(ROOT / "A1_inflection.json", "w") as f:
    json.dump(a1_results, f, indent=2)

# Plot rolling vol traces
fig, ax = plt.subplots(figsize=(13, 4.5))
for win, color in [(20, "tab:gray"), (30, "tab:blue"), (60, "tab:orange")]:
    rv = rolling_annvol(xau["ret"], win)
    ax.plot(rv.index, rv.values, label=f"{win}d", color=color, alpha=0.85, lw=1.0)
ax.axhline(15, color="green", ls="--", lw=0.7, label="15% floor")
ax.axhline(20, color="red", ls="--", lw=0.7, label="20% threshold")
for win, marker in [(20, "v"), (30, "o"), (60, "s")]:
    cd = a1_results[f"win_{win}"]["crossover_date"]
    if cd:
        cd_ts = pd.Timestamp(cd)
        v = a1_results[f"win_{win}"]["vol_at_crossover_pct"]
        ax.plot(cd_ts, v, marker, markersize=10, color="black",
                label=f"{win}d crossover {cd}")
ax.set_title("XAUUSD rolling annualized vol (%) — A1 inflection")
ax.set_ylabel("ann vol %")
ax.legend(loc="upper left", fontsize=8); ax.grid(alpha=0.3)
plt.tight_layout(); plt.savefig(FIG / "A1_rolling_vol.png", dpi=110); plt.close()


# ── A2. Drift attribution ────────────────────────────────────────────────

# A2a — session-time decomposition
def session_bucket(hour):
    if 8 <= hour < 16:
        return "NY_08_16"
    if 16 <= hour < 24:
        return "Late_16_24"
    return "Asia_00_08"

xau_15m["session"] = xau_15m.index.hour.map(session_bucket)
xau_15m["era"] = np.where(xau_15m.index.year == 2026, "2026YTD", "2022_2025")
a2a = (xau_15m
       .groupby(["era", "session"])["ret"]
       .agg(n="count",
            mean_abs_bp=lambda x: x.abs().mean()*1e4,
            std_bp=lambda x: x.std()*1e4,
            p95_abs_bp=lambda x: x.abs().quantile(0.95)*1e4)
       .round(3))
a2a.to_csv(ROOT / "A2a_session_decomp.csv")

# Compute the elevation ratio (2026 / 2022_2025) for each session
ratios = {}
for sess in ["Asia_00_08", "NY_08_16", "Late_16_24"]:
    r2026 = a2a.loc[("2026YTD", sess), "mean_abs_bp"]
    r2022 = a2a.loc[("2022_2025", sess), "mean_abs_bp"]
    ratios[sess] = float(r2026 / r2022)
with open(ROOT / "A2a_session_ratios.json", "w") as f:
    json.dump(ratios, f, indent=2)


# A2b — sign-symmetry QQ
xau_2026 = xau[xau.index.year == 2026]["ret"].dropna()
xau_prior = xau[xau.index.year < 2026]["ret"].dropna()

q_levels = np.linspace(0.01, 0.99, 99)
q_2026 = np.quantile(xau_2026, q_levels)
q_prior = np.quantile(xau_prior, q_levels)

# Sign-asymmetry summary
def tail_summary(s):
    return {
        "n": int(len(s)),
        "p01_bp": float(np.quantile(s, 0.01)*1e4),
        "p05_bp": float(np.quantile(s, 0.05)*1e4),
        "p95_bp": float(np.quantile(s, 0.95)*1e4),
        "p99_bp": float(np.quantile(s, 0.99)*1e4),
        "abs_p99_lower": float(abs(np.quantile(s, 0.01))*1e4),
        "abs_p99_upper": float(np.quantile(s, 0.99)*1e4),
        "ratio_lower_to_upper_p99": float(abs(np.quantile(s, 0.01))/np.quantile(s, 0.99))
                                    if np.quantile(s, 0.99) > 0 else None,
        "skew": float(stats.skew(s)),
        "kurt_excess": float(stats.kurtosis(s)),
    }
a2b = {
    "2026YTD": tail_summary(xau_2026),
    "2022_2025": tail_summary(xau_prior),
}
with open(ROOT / "A2b_sign_symmetry.json", "w") as f:
    json.dump(a2b, f, indent=2)

# QQ plot
fig, ax = plt.subplots(figsize=(6, 6))
ax.scatter(q_prior * 1e4, q_2026 * 1e4, s=14, alpha=0.7)
lim = max(abs(q_prior).max(), abs(q_2026).max()) * 1e4
ax.plot([-lim, lim], [-lim, lim], "k--", lw=0.8, label="y=x")
ax.plot([-lim, lim], [-2*lim, 2*lim], "r:", lw=0.8, label="y=2x (vol 2×)")
ax.set_xlabel("2022-2025 daily return quantile (bp)")
ax.set_ylabel("2026 YTD daily return quantile (bp)")
ax.set_title("XAUUSD QQ: 2026 YTD vs 2022-2025 pooled — A2b")
ax.legend(); ax.grid(alpha=0.3)
plt.tight_layout(); plt.savefig(FIG / "A2b_qq_plot.png", dpi=110); plt.close()


# A2c — time-clustering: top 5 weeks share of 2026 vol
xau_w = xau[xau.index.year == 2026]["ret"].dropna()
# Build weekly variance contributions
xau_w_by_week = xau_w.groupby(pd.Grouper(freq="W-MON"))
weekly_var = xau_w_by_week.apply(lambda x: float(np.sum(x**2)))
weekly_var = weekly_var[weekly_var > 0].sort_values(ascending=False)
total_var = weekly_var.sum()
top5_share = weekly_var.head(5).sum() / total_var if total_var > 0 else None
# Also compute share by trading day
day_var = xau_w ** 2
day_var_sorted = day_var.sort_values(ascending=False)
top5_day_share = day_var_sorted.head(5).sum() / day_var_sorted.sum() if day_var_sorted.sum() > 0 else None
top10_day_share = day_var_sorted.head(10).sum() / day_var_sorted.sum() if day_var_sorted.sum() > 0 else None

a2c = {
    "n_weeks_2026": int(len(weekly_var)),
    "n_days_2026": int(len(xau_w)),
    "top5_weeks_var_share": float(top5_share) if top5_share is not None else None,
    "top5_days_var_share":  float(top5_day_share) if top5_day_share is not None else None,
    "top10_days_var_share": float(top10_day_share) if top10_day_share is not None else None,
    "weekly_var_top10_dates": [str(d.date()) for d in weekly_var.head(10).index],
    "weekly_var_top10_vals":  [float(v) for v in weekly_var.head(10).values],
}
with open(ROOT / "A2c_time_clustering.json", "w") as f:
    json.dump(a2c, f, indent=2)


# ── A3. Guardian's actual input — 15-min 14-bar ATR ──────────────────────

def true_range(df):
    """Bar-level true range. Uses prior-bar close for gap term."""
    h = df["high"]
    l = df["low"]
    pc = df["close"].shift(1)
    return pd.concat([(h - l), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)

def rma(series, period):
    """Pine Script RMA: alpha = 1/period; first value = SMA seed."""
    arr = series.values.astype(float)
    out = np.full_like(arr, np.nan)
    if len(arr) < period:
        return pd.Series(out, index=series.index)
    out[period - 1] = np.nanmean(arr[:period])
    alpha = 1.0 / period
    for i in range(period, len(arr)):
        prev = out[i - 1]
        x = arr[i]
        if np.isnan(x):
            out[i] = prev
        else:
            out[i] = alpha * x + (1 - alpha) * prev
    return pd.Series(out, index=series.index)

xau_15m_clean = bars["XAUUSD"].copy()
xau_15m_clean["tr"] = true_range(xau_15m_clean)
xau_15m_clean["atr14"] = rma(xau_15m_clean["tr"], 14)
xau_15m_clean["bar_range"] = xau_15m_clean["high"] - xau_15m_clean["low"]
xau_15m_clean["yyyymm"] = xau_15m_clean.index.strftime("%Y-%m")

# Monthly aggregates
monthly = xau_15m_clean.groupby("yyyymm").agg(
    n_bars=("close", "count"),
    mean_atr14=("atr14", "mean"),
    mean_bar_range=("bar_range", "mean"),
    median_atr14=("atr14", "median"),
).round(4)
monthly["atr_to_range_ratio"] = (monthly["mean_atr14"] / monthly["mean_bar_range"]).round(4)
monthly.to_csv(ROOT / "A3_monthly_atr.csv")

# Yearly ratio
xau_15m_clean["year"] = xau_15m_clean.index.year
yearly = xau_15m_clean.groupby("year").agg(
    n_bars=("close", "count"),
    mean_atr14=("atr14", "mean"),
    mean_bar_range=("bar_range", "mean"),
    median_atr14=("atr14", "median"),
).round(4)
yearly["atr_to_range_ratio"] = (yearly["mean_atr14"] / yearly["mean_bar_range"]).round(4)
yearly.to_csv(ROOT / "A3_yearly_atr.csv")

# Implied $-risk-per-trade if Guardian fired with current ATR vs 2024 ATR,
# holding lot size constant. Guardian SL = 1.55 × ATR × lots. $/lot for XAUUSD = 100.
ATR_MULT = 1.55
USD_PER_LOT_PER_DOLLAR = 100  # XAUUSD contractValue (CLAUDE.md)

# Locked lot size assumption: account = $200K, risk = 0.34%, 1R = $680.
# 1R = 1.55 * ATR_baseline * 100 * lots  =>  lots = 680 / (1.55 * ATR_baseline * 100)
# Use 2024 ATR mean as baseline anchor. Then test 2026 vs that.
atr_2024 = float(yearly.loc[2024, "mean_atr14"])
atr_2025 = float(yearly.loc[2025, "mean_atr14"])
atr_2026 = float(yearly.loc[2026, "mean_atr14"])
target_risk_dollars = 680.0
lots_2024_anchor = target_risk_dollars / (ATR_MULT * atr_2024 * USD_PER_LOT_PER_DOLLAR)

# If lot size is locked at the 2024-anchored value, what is implied $-risk-per-trade
# at 2025 / 2026 ATR?
def implied_dollar_risk(atr_now, lots):
    return ATR_MULT * atr_now * USD_PER_LOT_PER_DOLLAR * lots

implied_2025 = implied_dollar_risk(atr_2025, lots_2024_anchor)
implied_2026 = implied_dollar_risk(atr_2026, lots_2024_anchor)

# Now the more accurate scenario: Guardian recomputes lots EVERY entry from
# the *then-current* 14-bar ATR. So the *forward* error is between (14-bar ATR
# at entry) and (true forward bar range over the SL distance). If 14-bar RMA
# lags, lots are sized to a stale ATR.
# Compare: at each bar, what does ATR14 say vs what the contemporaneous
# 14-bar mean(true_range) say? RMA is a smooth; SMA is the contemporaneous mean.
xau_15m_clean["sma14_tr"] = xau_15m_clean["tr"].rolling(14).mean()
xau_15m_clean["atr_lag_ratio"] = xau_15m_clean["atr14"] / xau_15m_clean["sma14_tr"]
lag_yearly = xau_15m_clean.groupby("year")["atr_lag_ratio"].agg(["mean", "median", "std"]).round(4)
lag_yearly.to_csv(ROOT / "A3_atr_rma_vs_sma_lag.csv")

a3 = {
    "atr_mult": ATR_MULT,
    "usd_per_lot_per_dollar": USD_PER_LOT_PER_DOLLAR,
    "yearly_atr14_mean": {int(k): float(v) for k, v in yearly["mean_atr14"].items()},
    "yearly_bar_range_mean": {int(k): float(v) for k, v in yearly["mean_bar_range"].items()},
    "yearly_atr_to_range_ratio": {int(k): float(v) for k, v in yearly["atr_to_range_ratio"].items()},
    "yearly_rma_to_sma_ratio_mean": {int(k): float(v) for k, v in lag_yearly["mean"].items()},
    "lots_2024_anchor": float(lots_2024_anchor),
    "implied_dollar_risk_at_2024_atr": float(target_risk_dollars),
    "implied_dollar_risk_at_2025_atr_with_2024_lots": float(implied_2025),
    "implied_dollar_risk_at_2026_atr_with_2024_lots": float(implied_2026),
    "ratio_2026_to_2024_atr": float(atr_2026 / atr_2024),
    "ratio_2025_to_2024_atr": float(atr_2025 / atr_2024),
}
with open(ROOT / "A3_atr_summary.json", "w") as f:
    json.dump(a3, f, indent=2)

# Plot monthly ATR
fig, ax = plt.subplots(figsize=(14, 4.5))
mt = monthly.copy()
mt.index = pd.to_datetime(mt.index + "-01")
ax.plot(mt.index, mt["mean_atr14"], label="14-bar ATR (RMA)", color="tab:blue")
ax.plot(mt.index, mt["mean_bar_range"], label="mean 15m bar range", color="tab:orange", alpha=0.7)
ax.set_ylabel("$ per 15m bar")
ax.set_title("XAUUSD monthly mean 14-bar ATR vs raw bar range — A3 ATR fidelity")
ax.legend(loc="upper left"); ax.grid(alpha=0.3)
ax2 = ax.twinx()
ax2.plot(mt.index, mt["atr_to_range_ratio"], color="tab:green", lw=0.8, label="ATR/range")
ax2.set_ylabel("ATR / bar_range ratio", color="tab:green")
ax2.tick_params(axis="y", labelcolor="tab:green")
plt.tight_layout(); plt.savefig(FIG / "A3_atr_monthly.png", dpi=110); plt.close()


# ── A4. Trend persistence — run-length distribution by year ──────────────

def run_lengths(signs):
    """Lengths of consecutive identical signs. Drops zeros."""
    s = signs[signs != 0].values
    if len(s) == 0:
        return np.array([])
    runs = []
    cur = s[0]; n = 1
    for x in s[1:]:
        if x == cur:
            n += 1
        else:
            runs.append(n); cur = x; n = 1
    runs.append(n)
    return np.array(runs)

a4_rows = []
for year in sorted(xau.index.year.unique()):
    sub = xau[xau.index.year == year]["ret"].dropna()
    signs = np.sign(sub)
    rl = run_lengths(signs)
    pos_rl = run_lengths(signs[signs == 1])  # not really meaningful per-sign — recompute by sign
    # Compute per-sign run lengths
    s = signs.values
    pos_runs = []; neg_runs = []
    if len(s):
        cur = s[0]; n = 1
        for x in s[1:]:
            if x == cur:
                n += 1
            else:
                if cur > 0:
                    pos_runs.append(n)
                elif cur < 0:
                    neg_runs.append(n)
                cur = x; n = 1
        if cur > 0:
            pos_runs.append(n)
        elif cur < 0:
            neg_runs.append(n)
    a4_rows.append({
        "year": int(year),
        "n_days": int(len(sub)),
        "n_runs": int(len(rl)),
        "mean_run_len": float(rl.mean()) if len(rl) else None,
        "p95_run_len": float(np.quantile(rl, 0.95)) if len(rl) else None,
        "max_run_len": int(rl.max()) if len(rl) else None,
        "mean_pos_run": float(np.mean(pos_runs)) if pos_runs else None,
        "mean_neg_run": float(np.mean(neg_runs)) if neg_runs else None,
        "max_pos_run": int(max(pos_runs)) if pos_runs else None,
        "max_neg_run": int(max(neg_runs)) if neg_runs else None,
    })
a4 = pd.DataFrame(a4_rows)
a4.to_csv(ROOT / "A4_run_lengths.csv", index=False)


# ════════════════════════════════════════════════════════════════════════
# THREAD B — Joint correlation: WHEN and HOW
# ════════════════════════════════════════════════════════════════════════

panel = pd.DataFrame({n: D[n]["ret"] for n in D}).dropna()

# ── B1. Rolling traces ───────────────────────────────────────────────────

PAIRS = [("XAUUSD", "US30"), ("XAUUSD", "USDJPY"), ("US30", "USDJPY")]

fig, axes = plt.subplots(3, 1, figsize=(13, 9), sharex=True)
for ax, win in zip(axes, [30, 60, 120]):
    for a, b in PAIRS:
        s = panel[a].rolling(win).corr(panel[b])
        ax.plot(s.index, s.values, label=f"{a}-{b}", alpha=0.85, lw=0.9)
    ax.axhline(0, color="k", lw=0.4)
    ax.set_title(f"{win}-day rolling correlation")
    ax.legend(loc="upper left", fontsize=8); ax.grid(alpha=0.3)
plt.tight_layout(); plt.savefig(FIG / "B1_rolling_corr.png", dpi=110); plt.close()

# Find inflection date(s): for each pair, scan 60d corr, find date where rolling
# corr exits its full-history mean ± 1 std and stays there for >= 30 days
def detect_inflection(rolling_corr, full_mean, full_std):
    band_lo, band_hi = full_mean - full_std, full_mean + full_std
    out = rolling_corr.dropna()
    breaks = []
    in_break = False
    break_start = None
    break_dir = None
    for d, v in out.items():
        outside = (v < band_lo) or (v > band_hi)
        if outside and not in_break:
            in_break = True
            break_start = d
            break_dir = "below" if v < band_lo else "above"
        elif not outside and in_break:
            duration = (d - break_start).days
            if duration >= 30:
                breaks.append((break_start, d, break_dir, duration))
            in_break = False
    if in_break:
        duration = (out.index[-1] - break_start).days
        if duration >= 30:
            breaks.append((break_start, out.index[-1], break_dir, duration))
    return breaks

b1_inflections = {}
for a, b in PAIRS:
    rc = panel[a].rolling(60).corr(panel[b]).dropna()
    full_mu = float(rc.mean())
    full_sd = float(rc.std())
    breaks = detect_inflection(rc, full_mu, full_sd)
    b1_inflections[f"{a}-{b}"] = {
        "full_60d_corr_mean": full_mu,
        "full_60d_corr_std": full_sd,
        "sustained_breaks_ge_30d": [
            {"start": str(s.date()), "end": str(e.date()), "direction": d, "duration_days": int(dur)}
            for s, e, d, dur in breaks
        ],
    }
with open(ROOT / "B1_inflections.json", "w") as f:
    json.dump(b1_inflections, f, indent=2)


# ── B2. Event-driven vs pervasive ────────────────────────────────────────

p2026 = panel[panel.index.year == 2026]
p_calib = panel[panel.index.year.isin([2024, 2025])]

# Drop the 10 days with largest |z| in any instrument (within 2026)
z2026 = (p2026 - p2026.mean()) / p2026.std()
max_abs_z = z2026.abs().max(axis=1)
top10_dates = max_abs_z.sort_values(ascending=False).head(10).index
p2026_trim = p2026.drop(top10_dates)

corr_2026_full = p2026.corr().round(4)
corr_2026_trim = p2026_trim.corr().round(4)
corr_calib = p_calib.corr().round(4)

b2 = {
    "n_2026_full": int(len(p2026)),
    "n_2026_trim": int(len(p2026_trim)),
    "n_calib_2024_25": int(len(p_calib)),
    "top10_outlier_dates": [str(d.date()) for d in top10_dates],
    "corr_2026_full": corr_2026_full.to_dict(),
    "corr_2026_trim10": corr_2026_trim.to_dict(),
    "corr_calib_2024_25": corr_calib.to_dict(),
}
with open(ROOT / "B2_event_vs_pervasive.json", "w") as f:
    json.dump(b2, f, indent=2)


# ── B3. Intraday vs daily structure ──────────────────────────────────────

# Build aligned 15m return panel
m15_panel = pd.DataFrame({n: bars[n]["ret"] for n in bars}).dropna()
m15_2026 = m15_panel[m15_panel.index.year == 2026]
m15_calib = m15_panel[m15_panel.index.year < 2026]

corr_15m_2026 = m15_2026.corr().round(4)
corr_15m_calib = m15_calib.corr().round(4)
corr_15m_full  = m15_panel.corr().round(4)

b3 = {
    "n_15m_2026": int(len(m15_2026)),
    "n_15m_2022_2025": int(len(m15_calib)),
    "corr_15m_2026": corr_15m_2026.to_dict(),
    "corr_15m_2022_2025": corr_15m_calib.to_dict(),
    "corr_15m_full": corr_15m_full.to_dict(),
}
with open(ROOT / "B3_intraday_vs_daily.json", "w") as f:
    json.dump(b3, f, indent=2)


# ════════════════════════════════════════════════════════════════════════
# THREAD C — Vol clustering: empirical bootstrap miss
# ════════════════════════════════════════════════════════════════════════

# Build the same panel/blocks structure portfolio_mc.py would build, but on
# XAUUSD daily returns only (not strategy P&L). For C we want a 1-D weekly
# return series.

def build_weekly_xau():
    """Mon-anchored 5-day non-overlapping blocks of XAUUSD daily log returns,
    aggregated to weekly log return. Mirrors portfolio_mc.build_week_blocks
    semantics on a business-day reindexed panel."""
    s = xau["ret"].copy()
    # Reindex to bdays (mirror portfolio_mc business-day fill, but with 0 for
    # missing days — for vol-clustering experiments we want gaps as 0-return
    # to keep the weekly aggregation consistent with the bootstrap mechanics
    # that portfolio_mc uses.)
    bdays = pd.bdate_range(s.index.min(), s.index.max())
    s = s.reindex(bdays).fillna(0.0)
    # Mon-anchored 5-day non-overlapping blocks
    weeks = []
    week_dates = []
    for i, d in enumerate(s.index):
        if d.weekday() == 0 and i + 5 <= len(s):
            block = s.iloc[i:i+5]
            weeks.append(float(block.sum()))  # sum of log returns = weekly log return
            week_dates.append(d)
    return pd.Series(weeks, index=pd.DatetimeIndex(week_dates), name="xau_weekly_ret")

xau_weekly = build_weekly_xau()
xau_weekly.to_csv(ROOT / "C_xau_weekly.csv")
print(f"Built {len(xau_weekly)} XAUUSD Mon-anchored weekly returns")


# ── C1. Empirical max-consecutive-negative-weeks distribution ────────────

WIN = 32  # approx pass-horizon median in weeks

def max_consec_neg(arr):
    """Max run of strictly negative values."""
    best = 0; cur = 0
    for x in arr:
        if x < 0:
            cur += 1
            if cur > best:
                best = cur
        else:
            cur = 0
    return best

emp_max_runs = []
for i in range(len(xau_weekly) - WIN + 1):
    window = xau_weekly.iloc[i:i+WIN].values
    emp_max_runs.append(max_consec_neg(window))
emp_max_runs = np.array(emp_max_runs)

c1 = {
    "n_windows": int(len(emp_max_runs)),
    "window_weeks": WIN,
    "n_total_weeks": int(len(xau_weekly)),
    "mean": float(emp_max_runs.mean()),
    "p50": float(np.quantile(emp_max_runs, 0.50)),
    "p75": float(np.quantile(emp_max_runs, 0.75)),
    "p90": float(np.quantile(emp_max_runs, 0.90)),
    "p95": float(np.quantile(emp_max_runs, 0.95)),
    "p99": float(np.quantile(emp_max_runs, 0.99)),
    "max": int(emp_max_runs.max()),
    "share_of_neg_weeks": float((xau_weekly < 0).mean()),
}
with open(ROOT / "C1_empirical_max_runs.json", "w") as f:
    json.dump(c1, f, indent=2)


# ── C2. Bootstrap-replicated distribution ────────────────────────────────
# Mirror portfolio_mc semantics exactly: blocks are full 5-day Mon-anchored
# blocks of the daily panel (not weekly aggregates). Sample with replacement.
# For each sampled path, sum each block to a weekly return, then compute max
# consecutive negative weeks over the 32-week path.

def build_blocks_xau():
    s = xau["ret"].copy()
    bdays = pd.bdate_range(s.index.min(), s.index.max())
    s = s.reindex(bdays).fillna(0.0)
    blocks = []
    for i, d in enumerate(s.index):
        if d.weekday() == 0 and i + 5 <= len(s):
            blocks.append(s.iloc[i:i+5].values)
    return np.array(blocks)  # shape (n_blocks, 5)

blocks_xau = build_blocks_xau()
print(f"Built {blocks_xau.shape[0]} 5-day blocks (matches portfolio_mc build_week_blocks)")

def bootstrap_max_runs(n_sims, blocks, win_weeks, seed):
    rng = np.random.default_rng(seed)
    n_blocks = len(blocks)
    out = np.empty(n_sims, dtype=np.int64)
    for s in range(n_sims):
        idx = rng.integers(0, n_blocks, win_weeks)
        path_blocks = blocks[idx]              # (win_weeks, 5)
        weekly = path_blocks.sum(axis=1)       # (win_weeks,)
        out[s] = max_consec_neg(weekly)
    return out

# Pool 3 seeds × 1000 sims = 3000 paths for stability
boot_runs = np.concatenate([
    bootstrap_max_runs(1000, blocks_xau, WIN, seed)
    for seed in (42, 123, 2026)
])

c2 = {
    "n_sims_total": int(len(boot_runs)),
    "window_weeks": WIN,
    "mean": float(boot_runs.mean()),
    "p50": float(np.quantile(boot_runs, 0.50)),
    "p75": float(np.quantile(boot_runs, 0.75)),
    "p90": float(np.quantile(boot_runs, 0.90)),
    "p95": float(np.quantile(boot_runs, 0.95)),
    "p99": float(np.quantile(boot_runs, 0.99)),
    "max": int(boot_runs.max()),
}
with open(ROOT / "C2_bootstrap_max_runs.json", "w") as f:
    json.dump(c2, f, indent=2)


# ── C3. Compare ──────────────────────────────────────────────────────────

c3 = {
    "delta_p90": float(c1["p90"] - c2["p90"]),
    "delta_p95": float(c1["p95"] - c2["p95"]),
    "delta_p99": float(c1["p99"] - c2["p99"]),
    "delta_mean": float(c1["mean"] - c2["mean"]),
    "delta_max":  float(c1["max"] - c2["max"]),
    "empirical": c1,
    "bootstrap": c2,
}
with open(ROOT / "C3_comparison.json", "w") as f:
    json.dump(c3, f, indent=2)

# Overlay histogram
fig, ax = plt.subplots(figsize=(10, 4.5))
max_x = max(emp_max_runs.max(), boot_runs.max()) + 1
bins = np.arange(0, max_x + 1) - 0.5
ax.hist(boot_runs, bins=bins, alpha=0.55, label=f"Bootstrap (n={len(boot_runs):,})",
        color="tab:blue", density=True)
ax.hist(emp_max_runs, bins=bins, alpha=0.55, label=f"Empirical (n={len(emp_max_runs):,})",
        color="tab:orange", density=True)
ax.axvline(c1["p95"], color="tab:orange", ls="--", lw=0.8, label=f"emp p95={c1['p95']:.1f}")
ax.axvline(c2["p95"], color="tab:blue", ls="--", lw=0.8, label=f"boot p95={c2['p95']:.1f}")
ax.set_xlabel("max consecutive negative weeks in 32-week window")
ax.set_ylabel("density")
ax.set_title("XAUUSD vol-clustering: empirical vs bootstrap 32-week max-neg-run — C3")
ax.legend(); ax.grid(alpha=0.3)
plt.tight_layout(); plt.savefig(FIG / "C3_max_runs_overlay.png", dpi=110); plt.close()


# ── C4. GARCH(1,1) ───────────────────────────────────────────────────────

c4 = {}
for name, d in D.items():
    r = d["ret"].dropna() * 100  # arch wants %
    am = arch_model(r, mean="Constant", vol="Garch", p=1, q=1, dist="normal", rescale=False)
    res = am.fit(disp="off")
    params = res.params.to_dict()
    omega = float(params.get("omega", np.nan))
    alpha = float(params.get("alpha[1]", np.nan))
    beta  = float(params.get("beta[1]", np.nan))
    persistence = alpha + beta
    c4[name] = {
        "n_obs": int(len(r)),
        "omega": omega,
        "alpha": alpha,
        "beta":  beta,
        "persistence_alpha_plus_beta": persistence,
        "log_likelihood": float(res.loglikelihood),
        "aic": float(res.aic),
        "bic": float(res.bic),
        "summary_oneline": (f"omega={omega:.5f}, alpha={alpha:.4f}, beta={beta:.4f}, "
                            f"alpha+beta={persistence:.4f}, LL={res.loglikelihood:.2f}"),
    }
    print(f"  GARCH(1,1) {name}: {c4[name]['summary_oneline']}")

with open(ROOT / "C4_garch.json", "w") as f:
    json.dump(c4, f, indent=2)


# ════════════════════════════════════════════════════════════════════════
# Final dump
# ════════════════════════════════════════════════════════════════════════

print("\n=== A1 inflection (XAUUSD rolling vol crossover ≥20% never <15%) ===")
print(json.dumps(a1_results, indent=2))
print("\n=== A2a session ratios (2026 / 2022-2025) ===")
print(json.dumps(ratios, indent=2))
print("\n=== A2c time clustering ===")
print(json.dumps(a2c, indent=2))
print("\n=== A3 ATR fidelity ===")
print(json.dumps(a3, indent=2))
print("\n=== A4 run lengths ===")
print(a4.to_string(index=False))
print("\n=== B1 inflections ===")
print(json.dumps(b1_inflections, indent=2))
print("\n=== B2 event vs pervasive ===")
print(json.dumps({k: v for k, v in b2.items() if k != "top10_outlier_dates"}, indent=2))
print(f"  outliers: {b2['top10_outlier_dates']}")
print("\n=== B3 intraday vs daily ===")
print(json.dumps(b3, indent=2))
print("\n=== C3 comparison ===")
print(json.dumps(c3, indent=2))
print("\n=== C4 GARCH ===")
print(json.dumps(c4, indent=2))

print("\nDone. Outputs in", ROOT)
