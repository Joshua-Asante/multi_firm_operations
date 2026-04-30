"""
Bar-level high-leverage analysis: XAUUSD / US30 / USDJPY 15min, 2022-01 -> 2026-04.

Goal: surface findings backtests cannot show. Strategies are LOCKED.
Outputs feed risk decisions (re-MC triggers, allocation candidates, MC assumption checks).
"""
import os
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

OUT = "/home/claude/analysis"
FIG = os.path.join(OUT, "figures")
os.makedirs(FIG, exist_ok=True)

PATHS = {
    "XAUUSD": "/mnt/user-data/uploads/XAUUSD.csv",
    "US30":   "/mnt/user-data/uploads/US30USD.csv",
    "USDJPY": "/mnt/user-data/uploads/USDJPY.csv",
}

# ----------------------------- LOAD ---------------------------------------

def load(name, path):
    df = pd.read_csv(path)
    df["time_utc"] = pd.to_datetime(df["time"], utc=True)
    df["time_ny"]  = df["time_utc"].dt.tz_convert("America/New_York")
    df = df.set_index("time_ny").drop(columns=["time"]).sort_index()
    df["ret"]   = np.log(df["close"]).diff()         # 15-min log returns
    df["range"] = (df["high"] - df["low"]) / df["close"]
    df["sym"]   = name
    return df

bars = {n: load(n, p) for n, p in PATHS.items()}

# Daily panels (NY date based on bar open)
def daily(df):
    g = df.groupby(df.index.date)
    out = pd.DataFrame({
        "open":  g["open"].first(),
        "high":  g["high"].max(),
        "low":   g["low"].min(),
        "close": g["close"].last(),
        "ret":   g["close"].last().apply(np.log).diff(),  # close-to-close
        "rv":    g["ret"].apply(lambda x: np.sqrt(np.sum(x**2))),  # realized vol from 15m
        "range_pct": (g["high"].max() - g["low"].min()) / g["close"].last(),
        "n_bars":    g.size(),
    })
    out.index = pd.to_datetime(out.index)
    return out

D = {n: daily(df) for n, df in bars.items()}

# ----------------------------- 1. REGIME DRIFT ----------------------------

def yearbucket(idx):
    y = idx.year
    return y.astype(str)

regime_rows = []
for name, d in D.items():
    d = d.dropna(subset=["ret"]).copy()
    d["year"] = d.index.year
    for y, sub in d.groupby("year"):
        regime_rows.append({
            "sym": name, "year": y, "n_days": len(sub),
            "mean_ret_bp": sub["ret"].mean() * 1e4,
            "std_ret_bp":  sub["ret"].std()  * 1e4,
            "skew":        stats.skew(sub["ret"].dropna()),
            "kurt_excess": stats.kurtosis(sub["ret"].dropna()),
            "p99_abs_bp":  sub["ret"].abs().quantile(0.99) * 1e4,
            "mean_rv":     sub["rv"].mean(),
            "mean_range_pct": sub["range_pct"].mean(),
        })
regime_df = pd.DataFrame(regime_rows)
regime_df.to_csv(os.path.join(OUT, "regime_by_year.csv"), index=False)

# KS test: 2026 YTD vs prior years pooled, per instrument
ks_rows = []
for name, d in D.items():
    d = d.dropna(subset=["ret"])
    recent = d[d.index.year == 2026]["ret"].values
    prior  = d[d.index.year <  2026]["ret"].values
    ks_d, ks_p = stats.ks_2samp(recent, prior)
    # Vol level test (Levene on absolute returns)
    lev_w, lev_p = stats.levene(np.abs(recent), np.abs(prior))
    ks_rows.append({
        "sym": name,
        "n_recent": len(recent), "n_prior": len(prior),
        "ks_stat": ks_d, "ks_p": ks_p,
        "levene_p": lev_p,
        "recent_std_bp": recent.std()*1e4,
        "prior_std_bp":  prior.std()*1e4,
        "vol_ratio_recent_vs_prior": (recent.std() / prior.std()),
    })
ks_df = pd.DataFrame(ks_rows)
ks_df.to_csv(os.path.join(OUT, "regime_ks_2026_vs_prior.csv"), index=False)

# Plot: realized vol by year, per instrument
fig, axes = plt.subplots(1, 3, figsize=(15, 4))
for i, (name, d) in enumerate(D.items()):
    d = d.dropna(subset=["ret"]).copy()
    d["year"] = d.index.year
    annual_vol = d.groupby("year")["ret"].std() * np.sqrt(252) * 100
    axes[i].bar(annual_vol.index.astype(str), annual_vol.values)
    axes[i].set_title(f"{name} annualized vol (%) by year")
    axes[i].set_ylabel("ann. vol %")
    axes[i].grid(alpha=0.3)
plt.tight_layout(); plt.savefig(os.path.join(FIG, "01_annual_vol.png"), dpi=110); plt.close()

# ----------------------------- 2. JOINT TAILS -----------------------------

# Build aligned daily return panel
panel = pd.DataFrame({n: D[n]["ret"] for n in D}).dropna()
panel.to_csv(os.path.join(OUT, "daily_returns_panel.csv"))

# Pairwise correlations - full and recent
def corr_block(df):
    return df.corr().round(4)

corr_full   = corr_block(panel)
corr_2026   = corr_block(panel[panel.index.year == 2026])
corr_2024_25 = corr_block(panel[panel.index.year.isin([2024, 2025])])

with open(os.path.join(OUT, "joint_correlations.json"), "w") as f:
    json.dump({
        "full_2022_2026": corr_full.to_dict(),
        "recent_2026":    corr_2026.to_dict(),
        "calib_2024_25":  corr_2024_25.to_dict(),
    }, f, indent=2)

# Conditional correlation: when ANY instrument has |z| > 2 daily
z = (panel - panel.mean()) / panel.std()
big_move_mask = (z.abs() > 2).any(axis=1)
panel_big = panel[big_move_mask]
panel_calm = panel[~big_move_mask]
cond = {
    "n_big": int(big_move_mask.sum()),
    "n_calm": int((~big_move_mask).sum()),
    "corr_big": panel_big.corr().round(4).to_dict(),
    "corr_calm": panel_calm.corr().round(4).to_dict(),
}
with open(os.path.join(OUT, "conditional_corr.json"), "w") as f:
    json.dump(cond, f, indent=2)

# Joint negative days: how often do all three move down? Two of three down >1σ?
sgn = panel.apply(np.sign)
all_neg = (sgn < 0).all(axis=1)
two_or_more_neg_1sigma = ((panel < -panel.std()).sum(axis=1) >= 2)
all_three_neg_1sigma = (panel < -panel.std()).all(axis=1)

joint_summary = {
    "total_days":       int(len(panel)),
    "all_neg_days":     int(all_neg.sum()),
    "all_neg_pct":      round(all_neg.mean() * 100, 2),
    "two_plus_neg_1sig": int(two_or_more_neg_1sigma.sum()),
    "two_plus_neg_1sig_pct": round(two_or_more_neg_1sigma.mean() * 100, 2),
    "all_three_neg_1sig": int(all_three_neg_1sigma.sum()),
    "all_three_neg_1sig_pct": round(all_three_neg_1sigma.mean() * 100, 2),
}
with open(os.path.join(OUT, "joint_tails.json"), "w") as f:
    json.dump(joint_summary, f, indent=2)

# Worst joint days (sum of z-scores, equal-weighted)
panel_z = (panel - panel.mean()) / panel.std()
panel_zsum = panel_z.sum(axis=1)
worst_days = panel.assign(z_sum=panel_zsum).sort_values("z_sum").head(15)
worst_days.to_csv(os.path.join(OUT, "worst_joint_days.csv"))

# Plot rolling 60-day correlation, all three pairs
fig, ax = plt.subplots(figsize=(13, 4))
pairs = [("XAUUSD","US30"),("XAUUSD","USDJPY"),("US30","USDJPY")]
for a, b in pairs:
    s = panel[a].rolling(60).corr(panel[b])
    ax.plot(s.index, s.values, label=f"{a}-{b}", alpha=0.85)
ax.axhline(0, color="k", lw=0.5)
ax.set_title("60-day rolling correlation, daily returns")
ax.legend(); ax.grid(alpha=0.3)
plt.tight_layout(); plt.savefig(os.path.join(FIG, "02_rolling_corr.png"), dpi=110); plt.close()

# ----------------------------- 3. VOL CLUSTERING --------------------------

# Autocorrelation of |ret| at daily horizon (Ljung-Box style at lags 1..20)
from statsmodels.tsa.stattools import acf

clust_rows = []
for name, d in D.items():
    r = d["ret"].dropna()
    abs_acf = acf(np.abs(r), nlags=20, fft=True)
    sq_acf  = acf(r**2,      nlags=20, fft=True)
    clust_rows.append({
        "sym": name,
        "n": len(r),
        "abs_acf_lag1":  round(abs_acf[1], 4),
        "abs_acf_lag5":  round(abs_acf[5], 4),
        "abs_acf_lag10": round(abs_acf[10], 4),
        "sq_acf_lag1":   round(sq_acf[1], 4),
        "sq_acf_lag5":   round(sq_acf[5], 4),
        "sq_acf_lag10":  round(sq_acf[10], 4),
    })
clust_df = pd.DataFrame(clust_rows)
clust_df.to_csv(os.path.join(OUT, "vol_clustering.csv"), index=False)

# Plot ACF
fig, axes = plt.subplots(1, 3, figsize=(15, 4))
for i, (name, d) in enumerate(D.items()):
    r = d["ret"].dropna()
    abs_a = acf(np.abs(r), nlags=20, fft=True)
    axes[i].bar(range(21), abs_a)
    axes[i].axhline(1.96/np.sqrt(len(r)), color="r", ls="--", lw=0.8, label="±1.96/√n")
    axes[i].axhline(-1.96/np.sqrt(len(r)), color="r", ls="--", lw=0.8)
    axes[i].set_title(f"{name} ACF of |daily ret|")
    axes[i].set_xlabel("lag (days)")
    axes[i].grid(alpha=0.3); axes[i].legend()
plt.tight_layout(); plt.savefig(os.path.join(FIG, "03_vol_acf.png"), dpi=110); plt.close()

# ----------------------------- 4. GAP ANALYSIS (DJ30 priority) ------------

def gaps(d):
    """Open-vs-prior-close gap, in % terms."""
    g = (d["open"] - d["close"].shift(1)) / d["close"].shift(1)
    out = pd.DataFrame({
        "gap_pct": g * 100,
        "dow": d.index.dayofweek,
        "prior_dow": d.index.to_series().shift(1).dt.dayofweek,
    })
    return out.dropna()

gap_us30 = gaps(D["US30"])
gap_jpy  = gaps(D["USDJPY"])
gap_xau  = gaps(D["XAUUSD"])

def gap_summary(g, name):
    by_dow = g.groupby("dow")["gap_pct"].agg(["count","mean","std",
                                              lambda x: x.abs().quantile(0.95),
                                              lambda x: x.abs().quantile(0.99),
                                              lambda x: x.abs().max()])
    by_dow.columns = ["n","mean_pct","std_pct","p95_abs","p99_abs","max_abs"]
    return by_dow.round(3)

gap_us30_dow = gap_summary(gap_us30, "US30")
gap_jpy_dow  = gap_summary(gap_jpy,  "USDJPY")
gap_xau_dow  = gap_summary(gap_xau,  "XAUUSD")

gap_us30_dow.to_csv(os.path.join(OUT, "gap_us30_by_dow.csv"))
gap_jpy_dow.to_csv(os.path.join(OUT, "gap_usdjpy_by_dow.csv"))
gap_xau_dow.to_csv(os.path.join(OUT, "gap_xauusd_by_dow.csv"))

# DJ30 weekend gap risk vs Striker -2% day-stop
# Striker trades Tue/Fri. Tue = post-Mon close. Fri = post-Thu close.
# Weekend gap = Mon open vs Fri close. Affects positions held through weekend (Striker doesn't hold,
# but we want to know if intraday gaps exceed -2%).
us30_big = gap_us30[gap_us30["gap_pct"].abs() >= 1.0].copy()
us30_big.to_csv(os.path.join(OUT, "us30_big_gaps_1pct_plus.csv"))

# How many days had intraday range > 2% (proxy for day-stop risk if entered)?
us30_big_range = D["US30"][D["US30"]["range_pct"] > 0.02].copy()

# ----------------------------- 5. SESSION EDGE MAPS -----------------------

def session_map(df, hours_range, days, label):
    """Mean abs ret and realized variance, hour by hour, on selected days."""
    df = df.dropna(subset=["ret"]).copy()
    ny = df.index
    df["hour"] = ny.hour
    df["dow"]  = ny.dayofweek
    sub = df[df["dow"].isin(days)]
    grp = sub.groupby("hour")["ret"]
    out = pd.DataFrame({
        "n_bars":     grp.size(),
        "mean_bp":    grp.mean()*1e4,
        "std_bp":     grp.std()*1e4,
        "abs_mean_bp": grp.apply(lambda x: x.abs().mean())*1e4,
    })
    return out

# Guardian: XAUUSD Mon(0), Tue(1), Thu(3), 8-16 EST
guardian = session_map(bars["XAUUSD"], (8,16), [0,1,3], "Guardian")
guardian.to_csv(os.path.join(OUT, "session_guardian_xauusd.csv"))

# Striker: US30 Tue(1), Fri(4), 8-12 EST
striker  = session_map(bars["US30"],   (8,12), [1,4], "Striker")
striker.to_csv(os.path.join(OUT, "session_striker_us30.csv"))

# Aegis: USDJPY Mon(0), Tue(1), Wed(2), 10-13:45 EST
aegis    = session_map(bars["USDJPY"], (10,14), [0,1,2], "Aegis")
aegis.to_csv(os.path.join(OUT, "session_aegis_usdjpy.csv"))

# Plot session hour-of-day vol maps (bracket each strategy's window)
fig, axes = plt.subplots(1, 3, figsize=(16, 4))
for i, (sub, label, win) in enumerate([
    (guardian, "Guardian XAUUSD Mon/Tue/Thu", (8,15)),
    (striker,  "Striker US30 Tue/Fri",        (8,11)),
    (aegis,    "Aegis USDJPY Mon/Tue/Wed",    (10,13)),
]):
    sub2 = sub[sub.index.isin(range(0,24))]
    colors = ["tab:orange" if win[0] <= h <= win[1] else "tab:gray" for h in sub2.index]
    axes[i].bar(sub2.index, sub2["abs_mean_bp"], color=colors)
    axes[i].set_title(f"{label}\nmean |bar return| bp by NY hour (orange=session)")
    axes[i].set_xlabel("NY hour")
    axes[i].grid(alpha=0.3)
plt.tight_layout(); plt.savefig(os.path.join(FIG, "04_session_maps.png"), dpi=110); plt.close()

# ----------------------------- 6. HOUR-BLOCK VALIDATION -------------------

# Aegis blocks: H11 entire hour, 10:45 bar specifically (15-min granular), Tue H10
# We need 15-min granular for Aegis 10:45.
def hour_minute_stats(df, days, hours, label):
    df = df.dropna(subset=["ret"]).copy()
    ny = df.index
    df["dow"] = ny.dayofweek
    df["hh"]  = ny.hour
    df["mm"]  = ny.minute
    sub = df[df["dow"].isin(days) & df["hh"].isin(hours)]
    grp = sub.groupby(["hh","mm"])["ret"]
    out = pd.DataFrame({
        "n_bars":  grp.size(),
        "mean_bp": grp.mean()*1e4,
        "std_bp":  grp.std()*1e4,
        "abs_mean_bp": grp.apply(lambda x: x.abs().mean())*1e4,
        "p95_abs_bp":  grp.apply(lambda x: x.abs().quantile(0.95))*1e4,
    })
    return out.round(2)

# Aegis: validate 10:45 vs 10:30/10:15 vs 11:00/11:15/11:30/11:45
aegis_hm = hour_minute_stats(bars["USDJPY"], [0,1,2], [10,11,12,13], "Aegis")
aegis_hm.to_csv(os.path.join(OUT, "aegis_15min_block_validation.csv"))

# Aegis Tue H10 specifically
aegis_tue = bars["USDJPY"].dropna(subset=["ret"]).copy()
aegis_tue = aegis_tue[(aegis_tue.index.dayofweek == 1) & (aegis_tue.index.hour == 10)]
aegis_tue_g = aegis_tue.groupby(aegis_tue.index.minute)["ret"]
aegis_tue_stats = pd.DataFrame({
    "n":      aegis_tue_g.size(),
    "mean_bp": aegis_tue_g.mean()*1e4,
    "std_bp":  aegis_tue_g.std()*1e4,
    "abs_mean_bp": aegis_tue_g.apply(lambda x: x.abs().mean())*1e4,
}).round(2)
aegis_tue_stats.to_csv(os.path.join(OUT, "aegis_tue_h10_validation.csv"))

# Guardian: Mon H08, Mon H09, Tue H08, H12 all days
def hour_stats_with_dow(df, label):
    df = df.dropna(subset=["ret"]).copy()
    df["dow"] = df.index.dayofweek
    df["hh"]  = df.index.hour
    grp = df.groupby(["dow","hh"])["ret"]
    out = pd.DataFrame({
        "n_bars": grp.size(),
        "mean_bp": grp.mean()*1e4,
        "std_bp":  grp.std()*1e4,
        "abs_mean_bp": grp.apply(lambda x: x.abs().mean())*1e4,
    }).round(2)
    return out

guardian_hours = hour_stats_with_dow(bars["XAUUSD"], "Guardian")
guardian_hours.to_csv(os.path.join(OUT, "guardian_hour_dow_validation.csv"))

# ----------------------------- 7. SUMMARY ---------------------------------

print("\n=== REGIME (annualized vol % by year) ===")
for name, d in D.items():
    d2 = d.dropna(subset=["ret"]).copy()
    d2["y"] = d2.index.year
    annvol = d2.groupby("y")["ret"].std() * np.sqrt(252) * 100
    print(f"  {name}: " + " ".join(f"{y}={v:.1f}%" for y, v in annvol.items()))

print("\n=== KS TEST: 2026 YTD vs prior years pooled ===")
print(ks_df.to_string(index=False))

print("\n=== JOINT CORRELATIONS (full panel) ===")
print(corr_full)
print("\n=== JOINT CORRELATIONS (2026 YTD) ===")
print(corr_2026)
print("\n=== JOINT CORRELATIONS (2024-2025 calib middle) ===")
print(corr_2024_25)

print("\n=== JOINT TAIL SUMMARY ===")
print(json.dumps(joint_summary, indent=2))

print("\n=== CONDITIONAL CORR (high-vol days vs calm) ===")
print(f"  n_big: {cond['n_big']}, n_calm: {cond['n_calm']}")
print("  big-day corr:")
for k, v in cond["corr_big"].items():
    print(f"    {k}: {v}")
print("  calm-day corr:")
for k, v in cond["corr_calm"].items():
    print(f"    {k}: {v}")

print("\n=== VOL CLUSTERING (ACF of |ret|, daily) ===")
print(clust_df.to_string(index=False))

print("\n=== TOP 15 WORST JOINT DAYS ===")
print(worst_days.round(4).to_string())

print("\n=== US30 GAP RISK BY DOW ===")
print(gap_us30_dow.to_string())
print(f"\nUS30 days with intraday range > 2.0%: {len(us30_big_range)} (out of {len(D['US30'])} = {len(us30_big_range)/len(D['US30'])*100:.1f}%)")
print(f"  by year: {us30_big_range.groupby(us30_big_range.index.year).size().to_dict()}")

print("\n=== US30 GAPS >= 1.0% (count by year) ===")
print(us30_big.groupby(us30_big.index.year).size().to_dict())

print("\nDone. Outputs in", OUT)
