"""DJ30+NAS100 allocation MC over the LOSS-CYCLE cohort (BothLose week + N
following weeks). RF in a pure-loss cohort is degenerate (~-1); the loss-cycle
window lets RF capture loss-and-recovery, which is the actual question.

Also runs full-record MC as the reference baseline.
"""

import pandas as pd
import numpy as np
from pathlib import Path

BASE = Path(r"C:\Users\joshu\multi_firm_operations\data\tv_exports\pepperstone")
RNG_SEED = 42

DJ30_FILE = BASE / "Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv"
NAS_FILE  = BASE / "Striker_NAS100_v1_PEPPERSTONE_NAS100_2026-05-05_7ca6f.csv"
PANEL_RISK = {"DJ30": 1.00, "NAS100": 0.40}

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

dj30["per1"] = dj30["pnl"] / PANEL_RISK["DJ30"]
nas["per1"] = nas["pnl"] / PANEL_RISK["NAS100"]

# Build week classification (re-derive for completeness)
dj_w = dj30.groupby("week")["pnl"].agg(["sum", "count"]).rename(columns={"sum":"dj_pnl","count":"dj_n"})
nas_w = nas.groupby("week")["pnl"].agg(["sum", "count"]).rename(columns={"sum":"nas_pnl","count":"nas_n"})
w = dj_w.join(nas_w, how="outer").fillna(0)
w[["dj_n","nas_n"]] = w[["dj_n","nas_n"]].astype(int)
w["both_active"] = (w["dj_n"] > 0) & (w["nas_n"] > 0)
w["both_lose"] = w["both_active"] & (w["dj_pnl"] < 0) & (w["nas_pnl"] < 0)

bl_weeks = w[w["both_lose"]].index.tolist()
all_weeks = w.index.tolist()
all_weeks_sorted = sorted(all_weeks)

# Per-strategy per-1%-risk averages by cohort
print("=" * 90)
print("PER-1%-RISK COHORT SIGNATURE")
print("=" * 90)

cohorts = {
    "BothLose": w[w["both_lose"]].index.tolist(),
    "BothWin": w[w["both_active"] & (w["dj_pnl"] > 0) & (w["nas_pnl"] > 0)].index.tolist(),
    "DJwin_NASlose": w[w["both_active"] & (w["dj_pnl"] > 0) & (w["nas_pnl"] < 0)].index.tolist(),
    "NASwin_DJlose": w[w["both_active"] & (w["dj_pnl"] < 0) & (w["nas_pnl"] > 0)].index.tolist(),
}

print(f"\n{'Cohort':16s} | {'weeks':>5s} | {'DJ/wk @1%':>11s} | {'NAS/wk @1%':>11s} | {'DJ:NAS ratio':>13s}")
print("-" * 70)
for name, weeks_list in cohorts.items():
    if not weeks_list: continue
    sub_dj = dj30[dj30["week"].isin(weeks_list)]
    sub_nas = nas[nas["week"].isin(weeks_list)]
    dj_per1_pwk = sub_dj["per1"].sum() / len(weeks_list)
    nas_per1_pwk = sub_nas["per1"].sum() / len(weeks_list)
    ratio = abs(dj_per1_pwk / nas_per1_pwk) if nas_per1_pwk != 0 else float("inf")
    print(f"{name:16s} | {len(weeks_list):>5d} | {dj_per1_pwk:>11,.0f} | {nas_per1_pwk:>11,.0f} | {ratio:>13.3f}")

# ============================================================================
# LOSS-CYCLE MC — BothLose week + 4 follow-up weeks
# ============================================================================
print()
print("=" * 90)
print("LOSS-CYCLE MC — BothLose week + 4 following weeks (captures recovery)")
print("=" * 90)

def cycle_trades(bl_week, follow=4):
    """Return list of trades (per-1%-risk, with src label) over a BothLose week + N follow weeks."""
    idx = all_weeks_sorted.index(bl_week) if bl_week in all_weeks_sorted else None
    if idx is None: return []
    cycle_weeks = all_weeks_sorted[idx : idx + 1 + follow]
    rows = []
    for wk in cycle_weeks:
        for _, r in dj30[dj30["week"] == wk][["dt","per1"]].iterrows():
            rows.append((r["dt"], r["per1"], "DJ30"))
        for _, r in nas[nas["week"] == wk][["dt","per1"]].iterrows():
            rows.append((r["dt"], r["per1"], "NAS100"))
    rows.sort(key=lambda x: x[0])
    return rows

cycle_blocks = [cycle_trades(wk, follow=4) for wk in bl_weeks]
# Drop empty
cycle_blocks = [b for b in cycle_blocks if b]
print(f"Cohort: {len(cycle_blocks)} loss-cycle windows (5-week windows starting at each BothLose event)")

def path_metrics_rows(rows, w_dj, w_nas):
    if not rows: return (0, 0, 0)
    eq = 0.0; peak = 0.0; max_dd = 0.0
    for _, per1, src in rows:
        scale = w_dj if src == "DJ30" else w_nas
        eq += per1 * scale
        if eq > peak: peak = eq
        dd = peak - eq
        if dd > max_dd: max_dd = dd
    net = eq
    rf = net / max_dd if max_dd > 0 else float("inf")
    return (net, max_dd, rf)

TOTAL_BUDGET = 1.40
GRID = np.arange(0.0, 1.41, 0.10)
N_BOOT = 2000
rng = np.random.default_rng(RNG_SEED)

results = []
for w_dj in GRID:
    w_nas = TOTAL_BUDGET - w_dj
    if w_nas < -1e-9: continue
    nets = np.empty(N_BOOT); rfs = np.empty(N_BOOT); dds = np.empty(N_BOOT)
    for b in range(N_BOOT):
        sampled_idx = rng.integers(0, len(cycle_blocks), size=len(cycle_blocks))
        # Concatenate sampled cycle windows
        all_rows = []
        for i in sampled_idx:
            all_rows.extend(cycle_blocks[i])
        net, dd, rf = path_metrics_rows(all_rows, w_dj, w_nas)
        nets[b] = net; dds[b] = dd; rfs[b] = rf
    rfs_f = rfs[np.isfinite(rfs)]
    results.append({
        "w_dj": w_dj, "w_nas": w_nas,
        "net_p25": np.percentile(nets, 25), "net_med": np.median(nets), "net_p75": np.percentile(nets, 75),
        "dd_med": np.median(dds),
        "rf_p25": np.percentile(rfs_f, 25) if len(rfs_f) else np.nan,
        "rf_med": np.median(rfs_f) if len(rfs_f) else np.nan,
        "rf_p75": np.percentile(rfs_f, 75) if len(rfs_f) else np.nan,
        "frac_pos": (nets > 0).mean(),
    })

rdf = pd.DataFrame(results)
print(f"\n{'w_DJ%':>5s} | {'w_NAS%':>6s} | {'Net p25':>9s} | {'Net med':>9s} | {'Net p75':>9s} | "
      f"{'DD med':>8s} | {'RF p25':>7s} | {'RF med':>7s} | {'RF p75':>7s} | {'P(Net>0)':>8s}")
print("-" * 110)
for _, r in rdf.iterrows():
    print(f"{r['w_dj']:>5.2f} | {r['w_nas']:>6.2f} | "
          f"{r['net_p25']:>9,.0f} | {r['net_med']:>9,.0f} | {r['net_p75']:>9,.0f} | "
          f"{r['dd_med']:>8,.0f} | "
          f"{r['rf_p25']:>7.3f} | {r['rf_med']:>7.3f} | {r['rf_p75']:>7.3f} | "
          f"{r['frac_pos']:>8.2%}")

best_rf = rdf.iloc[rdf["rf_med"].idxmax()]
best_net = rdf.iloc[rdf["net_med"].idxmax()]
print()
print(f"BEST median RF (loss-cycle cohort): "
      f"w_DJ={best_rf['w_dj']:.2f}% w_NAS={best_rf['w_nas']:.2f}% -> RF={best_rf['rf_med']:.3f}, Net=${best_rf['net_med']:,.0f}, P(Net>0)={best_rf['frac_pos']:.1%}")
print(f"BEST median Net (loss-cycle cohort): "
      f"w_DJ={best_net['w_dj']:.2f}% w_NAS={best_net['w_nas']:.2f}% -> Net=${best_net['net_med']:,.0f}, RF={best_net['rf_med']:.3f}")

# ============================================================================
# FULL-RECORD MC — allocation sweep over entire DJ30+NAS100 trade record
# ============================================================================
print()
print("=" * 90)
print("FULL-RECORD MC — allocation sweep over entire DJ30+NAS100 record (reference)")
print("=" * 90)

# Build all-record per-week blocks (per-1% basis, with src labels)
all_blocks = []
for wk in all_weeks_sorted:
    rows = []
    for _, r in dj30[dj30["week"] == wk][["dt","per1"]].iterrows():
        rows.append((r["dt"], r["per1"], "DJ30"))
    for _, r in nas[nas["week"] == wk][["dt","per1"]].iterrows():
        rows.append((r["dt"], r["per1"], "NAS100"))
    if rows:
        rows.sort(key=lambda x: x[0])
        all_blocks.append(rows)

print(f"Cohort: {len(all_blocks)} weeks total\n")

results2 = []
for w_dj in GRID:
    w_nas = TOTAL_BUDGET - w_dj
    if w_nas < -1e-9: continue
    nets = np.empty(N_BOOT); rfs = np.empty(N_BOOT); dds = np.empty(N_BOOT)
    for b in range(N_BOOT):
        sampled_idx = rng.integers(0, len(all_blocks), size=len(all_blocks))
        all_rows = []
        for i in sampled_idx:
            all_rows.extend(all_blocks[i])
        net, dd, rf = path_metrics_rows(all_rows, w_dj, w_nas)
        nets[b] = net; dds[b] = dd; rfs[b] = rf
    rfs_f = rfs[np.isfinite(rfs)]
    results2.append({
        "w_dj": w_dj, "w_nas": w_nas,
        "net_med": np.median(nets), "dd_med": np.median(dds),
        "rf_p25": np.percentile(rfs_f, 25),
        "rf_med": np.median(rfs_f),
        "rf_p75": np.percentile(rfs_f, 75),
        "p99_dd": np.percentile(dds, 99),
    })

rdf2 = pd.DataFrame(results2)
print(f"{'w_DJ%':>5s} | {'w_NAS%':>6s} | {'Net med':>9s} | {'DD med':>8s} | {'p99 DD':>8s} | "
      f"{'RF p25':>7s} | {'RF med':>7s} | {'RF p75':>7s}")
print("-" * 90)
for _, r in rdf2.iterrows():
    print(f"{r['w_dj']:>5.2f} | {r['w_nas']:>6.2f} | "
          f"{r['net_med']:>9,.0f} | {r['dd_med']:>8,.0f} | {r['p99_dd']:>8,.0f} | "
          f"{r['rf_p25']:>7.2f} | {r['rf_med']:>7.2f} | {r['rf_p75']:>7.2f}")

best_rf2 = rdf2.iloc[rdf2["rf_med"].idxmax()]
print()
print(f"BEST median RF (full record): "
      f"w_DJ={best_rf2['w_dj']:.2f}% w_NAS={best_rf2['w_nas']:.2f}% -> RF={best_rf2['rf_med']:.2f}")

# Reference points for current locks
print()
print("Reference points (full-record MC):")
for label, w_dj_ref, w_nas_ref in [("2026-05-05 lock", 1.00, 0.40), ("2026-05-14 lock-equiv", 0.95, 0.45)]:
    # find closest grid
    nearest = rdf2.iloc[((rdf2["w_dj"] - w_dj_ref).abs()).idxmin()]
    print(f"  {label} (DJ {w_dj_ref:.2f}%, NAS {w_nas_ref:.2f}%): "
          f"closest grid Net=${nearest['net_med']:,.0f} RF={nearest['rf_med']:.2f}")
