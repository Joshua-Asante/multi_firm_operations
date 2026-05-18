"""DJ30 vs NAS100 streak analysis + MC allocation sweep over joint-losing cohort.

Steps:
  1. Build weekly Net per strategy from exit-only trades.
  2. Classify weeks where both strategies are active: BothLose / Mixed / BothWin.
  3. Identify streaks (consecutive weeks of same class).
  4. MC: in the joint-losing week cohort, bootstrap-resample week-blocks and
     sweep allocation weights w_DJ30 ∈ [0, 1.40] (w_NAS = 1.40 - w_DJ30).
     Compute distribution of Net, MaxDD, RF per allocation. Maximize median RF.

CSV vintage: 2026-05-05 full-range Pepperstone exports.
Panel risk: DJ30 1.00% / NAS100 0.40%. P&L scaled per-1%-risk then re-applied
at allocation candidates.
"""

import pandas as pd
import numpy as np
from pathlib import Path

BASE = Path(r"C:\Users\joshu\multi_firm_operations\data\tv_exports\pepperstone")
RNG_SEED = 42

DJ30_FILE = BASE / "Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv"
NAS_FILE  = BASE / "Striker_NAS100_v1_PEPPERSTONE_NAS100_2026-05-05_7ca6f.csv"

PANEL_RISK = {"DJ30": 1.00, "NAS100": 0.40}  # % per trade, panel basis

def load_exits(path):
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
    df["dt"] = pd.to_datetime(df["Date and time"], errors="coerce")
    ex = df[df["Type"].str.startswith("Exit", na=False)].copy()
    ex = ex.sort_values("dt").reset_index(drop=True)
    ex["pnl"] = ex["Net P&L USD"].astype(float)
    ex["week"] = ex["dt"].dt.to_period("W")
    return ex

dj30 = load_exits(DJ30_FILE)
nas = load_exits(NAS_FILE)

# Weekly aggregate
dj_w = dj30.groupby("week")["pnl"].agg(["sum", "count"]).rename(columns={"sum":"dj_pnl","count":"dj_n"})
nas_w = nas.groupby("week")["pnl"].agg(["sum", "count"]).rename(columns={"sum":"nas_pnl","count":"nas_n"})
w = dj_w.join(nas_w, how="outer").fillna(0)
w[["dj_n","nas_n"]] = w[["dj_n","nas_n"]].astype(int)
w["both_active"] = (w["dj_n"] > 0) & (w["nas_n"] > 0)

# Classification
def classify(row):
    if not row["both_active"]:
        return "OneOnly"
    dj_pos = row["dj_pnl"] > 0
    nas_pos = row["nas_pnl"] > 0
    if dj_pos and nas_pos: return "BothWin"
    if (not dj_pos) and (not nas_pos): return "BothLose"
    if dj_pos and not nas_pos: return "DJwin_NASlose"
    return "NASwin_DJlose"

w["class"] = w.apply(classify, axis=1)

print("=" * 90)
print("WEEKLY CLASSIFICATION (both DJ30 and NAS100 had at least one closed trade)")
print("=" * 90)
both_w = w[w["both_active"]].copy()
class_summary = both_w.groupby("class").agg(
    weeks=("dj_pnl","count"),
    dj_total=("dj_pnl","sum"),
    nas_total=("nas_pnl","sum"),
    combined=("dj_pnl", lambda s: s.sum() + both_w.loc[s.index, "nas_pnl"].sum())
).reset_index()
total_both = len(both_w)
print(f"\nTotal both-active weeks: {total_both} (of {len(w)} total weeks since 2022-01)")
print()
print(f"{'Class':16s} | {'weeks':>5s} | {'%':>5s} | {'DJ Net':>10s} | {'NAS Net':>10s} | {'Combined':>10s}")
print("-" * 70)
for _, r in class_summary.iterrows():
    pct = r["weeks"] / total_both * 100
    print(f"{r['class']:16s} | {int(r['weeks']):>5d} | {pct:>5.1f} | {r['dj_total']:>10,.0f} | {r['nas_total']:>10,.0f} | {r['combined']:>10,.0f}")

# Streaks: runs of consecutive same-class weeks (treating both_active timeline)
both_w_sorted = both_w.sort_index()
classes = both_w_sorted["class"].tolist()
weeks_idx = both_w_sorted.index.tolist()

def find_runs(seq):
    runs = []
    if not seq: return runs
    cur = seq[0]; start = 0
    for i in range(1, len(seq)):
        if seq[i] != cur:
            runs.append((cur, start, i-1, i-start))
            cur = seq[i]; start = i
    runs.append((cur, start, len(seq)-1, len(seq)-start))
    return runs

runs = find_runs(classes)

print()
print("=" * 90)
print("STREAK DISTRIBUTION (consecutive both-active weeks of same class)")
print("=" * 90)
from collections import Counter
streak_dist = {}
for cls in ["BothWin", "BothLose", "DJwin_NASlose", "NASwin_DJlose"]:
    lens = [r[3] for r in runs if r[0] == cls]
    if not lens: continue
    streak_dist[cls] = lens
    print(f"\n{cls}: {len(lens)} streaks, total weeks {sum(lens)}, "
          f"mean len {np.mean(lens):.2f}, max len {max(lens)}")
    c = Counter(lens)
    print(f"  Length distribution: {dict(sorted(c.items()))}")

# List the long joint-losing streaks (len >= 2)
print()
print("=== Joint-losing streaks (length >= 2) ===")
for cls, start, end, length in runs:
    if cls == "BothLose" and length >= 2:
        wk_start = weeks_idx[start]
        wk_end = weeks_idx[end]
        sub = both_w_sorted.iloc[start:end+1]
        print(f"  {wk_start} -> {wk_end} ({length}wk)  "
              f"DJ ${sub['dj_pnl'].sum():>8,.0f} ({int(sub['dj_n'].sum())}t)  "
              f"NAS ${sub['nas_pnl'].sum():>8,.0f} ({int(sub['nas_n'].sum())}t)  "
              f"Combined ${(sub['dj_pnl']+sub['nas_pnl']).sum():>8,.0f}")

# All single-week BothLose events
single_bl = [r for r in runs if r[0] == "BothLose" and r[3] == 1]
print(f"\n(Plus {len(single_bl)} single-week BothLose events)")

# === Recovery profile after joint-losing streaks ===
print()
print("=== Recovery profile: 4 weeks following a BothLose week (avg combined Net) ===")
all_bl_idx = [(weeks_idx[r[1]], weeks_idx[r[2]]) for r in runs if r[0] == "BothLose"]
follow_pnls = []
for _, end_wk in all_bl_idx:
    # find weeks in w (full timeline) after end_wk
    after_end = w.index > end_wk
    after_w = w[after_end].head(4)
    combined = (after_w["dj_pnl"] + after_w["nas_pnl"]).values
    follow_pnls.append(combined.tolist())
# pad
maxlen = max(len(p) for p in follow_pnls) if follow_pnls else 0
arr = np.array([p + [np.nan]*(maxlen-len(p)) for p in follow_pnls])
for i in range(maxlen):
    col = arr[:, i]
    col = col[~np.isnan(col)]
    print(f"  Week +{i+1}: mean ${col.mean():,.0f}, median ${np.median(col):,.0f}, pos {(col>0).sum()}/{len(col)}")

# ============================================================================
# MC ALLOCATION SWEEP over joint-losing cohort
# ============================================================================
print()
print("=" * 90)
print("MC ALLOCATION SWEEP — joint-losing week cohort")
print("=" * 90)

# Build joint-losing week-block list with per-1%-risk-normalized trade P&Ls
bl_weeks = both_w_sorted[both_w_sorted["class"] == "BothLose"].index.tolist()
print(f"\nCohort: {len(bl_weeks)} joint-losing weeks")

# For each joint-losing week, gather trades scaled per-1%-risk
dj30["per1"] = dj30["pnl"] / PANEL_RISK["DJ30"]
nas["per1"] = nas["pnl"] / PANEL_RISK["NAS100"]

week_blocks = []  # list of (week, dj_trades_per1, nas_trades_per1, list of (dt, dj_per1, src))
for wk in bl_weeks:
    dj_trades = dj30[dj30["week"] == wk][["dt", "per1"]].copy()
    dj_trades["src"] = "DJ30"
    nas_trades = nas[nas["week"] == wk][["dt", "per1"]].copy()
    nas_trades["src"] = "NAS100"
    combined = pd.concat([dj_trades, nas_trades]).sort_values("dt").reset_index(drop=True)
    week_blocks.append(combined)

# MC: for each (w_dj, w_nas) with w_dj + w_nas = 1.40, run B bootstraps of N weeks
TOTAL_BUDGET = 1.40  # % combined
GRID = np.arange(0.0, 1.41, 0.10)
N_BOOT = 1000
N_WEEKS_PER_PATH = len(bl_weeks)  # resample full cohort length
rng = np.random.default_rng(RNG_SEED)

def path_metrics(path_trades, w_dj, w_nas):
    """Compute Net, MaxDD, RF on a single bootstrap path of weeks."""
    pnl = []
    for block in path_trades:
        for _, row in block.iterrows():
            scale = w_dj if row["src"] == "DJ30" else w_nas
            pnl.append(row["per1"] * scale)
    if not pnl:
        return (0, 0, 0)
    eq = 0.0; peak = 0.0; trough = 0.0; max_dd = 0.0
    for v in pnl:
        eq += v
        if eq > peak: peak = eq
        dd = peak - eq
        if dd > max_dd: max_dd = dd
    net = eq
    rf = net / max_dd if max_dd > 0 else float("inf")
    return (net, max_dd, rf)

print(f"\nMC: {N_BOOT} bootstraps × {len(GRID)} allocations × {N_WEEKS_PER_PATH} weeks/path")
print(f"Total budget fixed at {TOTAL_BUDGET:.2f}% combined; grid in 0.10 steps.\n")

results = []
for w_dj in GRID:
    w_nas = TOTAL_BUDGET - w_dj
    if w_nas < -1e-9: continue
    nets = np.empty(N_BOOT)
    dds = np.empty(N_BOOT)
    rfs = np.empty(N_BOOT)
    for b in range(N_BOOT):
        sampled_idx = rng.integers(0, len(week_blocks), size=N_WEEKS_PER_PATH)
        path = [week_blocks[i] for i in sampled_idx]
        net, dd, rf = path_metrics(path, w_dj, w_nas)
        nets[b] = net; dds[b] = dd; rfs[b] = rf
    rfs_finite = rfs[np.isfinite(rfs)]
    results.append({
        "w_dj": w_dj, "w_nas": w_nas,
        "net_med": np.median(nets), "net_p25": np.percentile(nets, 25), "net_p75": np.percentile(nets, 75),
        "dd_med": np.median(dds),
        "rf_med": np.median(rfs_finite) if len(rfs_finite) else np.nan,
        "rf_p25": np.percentile(rfs_finite, 25) if len(rfs_finite) else np.nan,
        "rf_p75": np.percentile(rfs_finite, 75) if len(rfs_finite) else np.nan,
        "frac_pos": (nets > 0).mean(),
    })

rdf = pd.DataFrame(results)
print(f"{'w_DJ%':>5s} | {'w_NAS%':>6s} | {'Net p25':>9s} | {'Net med':>9s} | {'Net p75':>9s} | "
      f"{'DD med':>8s} | {'RF p25':>7s} | {'RF med':>7s} | {'RF p75':>7s} | {'frac>0':>6s}")
print("-" * 110)
for _, r in rdf.iterrows():
    print(f"{r['w_dj']:>5.2f} | {r['w_nas']:>6.2f} | "
          f"{r['net_p25']:>9,.0f} | {r['net_med']:>9,.0f} | {r['net_p75']:>9,.0f} | "
          f"{r['dd_med']:>8,.0f} | "
          f"{r['rf_p25']:>7.3f} | {r['rf_med']:>7.3f} | {r['rf_p75']:>7.3f} | "
          f"{r['frac_pos']:>6.2%}")

# Optimum
best_rf = rdf.iloc[rdf["rf_med"].idxmax()]
best_net = rdf.iloc[rdf["net_med"].idxmax()]
print()
print(f"BEST median RF: w_DJ={best_rf['w_dj']:.2f}% w_NAS={best_rf['w_nas']:.2f}% -> RF_med={best_rf['rf_med']:.3f}, Net_med=${best_rf['net_med']:,.0f}")
print(f"BEST median Net: w_DJ={best_net['w_dj']:.2f}% w_NAS={best_net['w_nas']:.2f}% -> Net_med=${best_net['net_med']:,.0f}, RF_med={best_net['rf_med']:.3f}")

# Current allocation reference points
print()
print("Reference points:")
for label, w_dj_ref, w_nas_ref in [("2026-05-05 lock", 1.00, 0.40), ("2026-05-14 lock", 0.75, 0.45)]:
    # find closest grid points
    nearest = rdf.iloc[((rdf["w_dj"] - w_dj_ref).abs()).idxmin()]
    print(f"  {label} (DJ {w_dj_ref:.2f}%, NAS {w_nas_ref:.2f}%, combined {w_dj_ref+w_nas_ref:.2f}%):")
    print(f"    closest grid (DJ {nearest['w_dj']:.2f}%, NAS {nearest['w_nas']:.2f}%, combined 1.40%): "
          f"Net_med=${nearest['net_med']:,.0f}, RF_med={nearest['rf_med']:.3f}")

# Also test 1.20% combined (current 2026-05-14 actual combined)
print()
print("=" * 90)
print("ROBUSTNESS: re-run at 1.20% combined budget (current 2026-05-14 lock total)")
print("=" * 90)
TOTAL2 = 1.20
GRID2 = np.arange(0.0, 1.21, 0.10)
results2 = []
for w_dj in GRID2:
    w_nas = TOTAL2 - w_dj
    if w_nas < -1e-9: continue
    nets = np.empty(N_BOOT)
    rfs = np.empty(N_BOOT)
    for b in range(N_BOOT):
        sampled_idx = rng.integers(0, len(week_blocks), size=N_WEEKS_PER_PATH)
        path = [week_blocks[i] for i in sampled_idx]
        net, dd, rf = path_metrics(path, w_dj, w_nas)
        nets[b] = net; rfs[b] = rf
    rfs_finite = rfs[np.isfinite(rfs)]
    results2.append({
        "w_dj": w_dj, "w_nas": w_nas,
        "net_med": np.median(nets),
        "rf_med": np.median(rfs_finite) if len(rfs_finite) else np.nan,
        "frac_pos": (nets > 0).mean(),
    })
rdf2 = pd.DataFrame(results2)
print(f"\n{'w_DJ%':>5s} | {'w_NAS%':>6s} | {'Net med':>9s} | {'RF med':>7s} | {'frac>0':>6s}")
print("-" * 50)
for _, r in rdf2.iterrows():
    print(f"{r['w_dj']:>5.2f} | {r['w_nas']:>6.2f} | {r['net_med']:>9,.0f} | {r['rf_med']:>7.3f} | {r['frac_pos']:>6.2%}")
best2 = rdf2.iloc[rdf2["rf_med"].idxmax()]
print(f"\nBEST median RF @ 1.20% budget: w_DJ={best2['w_dj']:.2f}% w_NAS={best2['w_nas']:.2f}% -> RF={best2['rf_med']:.3f}")
