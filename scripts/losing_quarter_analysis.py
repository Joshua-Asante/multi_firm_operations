"""Structural analysis of losing quarters across the 4 locked strategies.

For each (strategy, losing_quarter) event:
  - Trade-level signature: WR, avg_win, avg_loss, largest single loss
  - Streak signature: max consecutive losers
  - Concentration: top-3 losers / total negative P&L
  - DD timing: when within the quarter did the trough occur, and how long to recover
  - Single-event dominance: did one or two bad days carry the quarter?

Then portfolio cross-cut: do losing quarters across strategies share weeks?
"""

import pandas as pd
import numpy as np
from pathlib import Path

BASE = Path(r"C:\Users\joshu\multi_firm_operations\data\tv_exports\pepperstone")

FILES = {
    "Guardian":     BASE / "Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-05_33781.csv",
    "DJ30":         BASE / "Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv",
    "NAS100":       BASE / "Striker_NAS100_v1_PEPPERSTONE_NAS100_2026-05-05_7ca6f.csv",
    "Aegis":        BASE / "Aegis_USDJPY_v4.3_PEPPERSTONE_USDJPY_2026-04-26_0bf1b.csv",
}

# From prior analysis
LOSING_QUARTERS = {
    "Guardian": ["2022Q2", "2022Q4"],
    "DJ30":     ["2024Q2", "2025Q1", "2025Q3"],
    "NAS100":   ["2022Q2", "2022Q4", "2025Q1", "2026Q1"],
    "Aegis":    ["2022Q1", "2022Q2", "2022Q4"],
}

def load_exits(path):
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
    df["dt"] = pd.to_datetime(df["Date and time"], errors="coerce")
    ex = df[df["Type"].str.startswith("Exit", na=False)].copy()
    ex = ex.sort_values("dt").reset_index(drop=True)
    ex["pnl"] = ex["Net P&L USD"].astype(float)
    ex["yq"] = ex["dt"].dt.to_period("Q")
    ex["ymw"] = ex["dt"].dt.to_period("W")
    ex["ym"] = ex["dt"].dt.to_period("M")
    return ex

def analyze_losing_quarter(name, qstr, grp):
    n = len(grp)
    pnl = grp["pnl"].values
    dates = grp["dt"].values
    wins = int((pnl > 0).sum())
    losses = n - wins

    # Trade-level signature
    win_pnl = pnl[pnl > 0]
    loss_pnl = pnl[pnl <= 0]
    avg_win = win_pnl.mean() if len(win_pnl) else 0
    avg_loss = loss_pnl.mean() if len(loss_pnl) else 0
    largest_loss = loss_pnl.min() if len(loss_pnl) else 0
    largest_loss_date = grp.iloc[np.argmin(pnl)]["dt"] if n else None
    largest_loss_share = largest_loss / loss_pnl.sum() if loss_pnl.sum() else 0

    # Top-3 loser concentration
    sorted_pnl = np.sort(pnl)
    top3 = sorted_pnl[:3].sum() if len(sorted_pnl) >= 3 else sorted_pnl.sum()
    top3_share = top3 / loss_pnl.sum() if loss_pnl.sum() else 0

    # Max consecutive loser streak
    streak = 0; max_streak = 0
    for v in pnl:
        if v <= 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0

    # DD reconstruction within quarter: cumulative equity, find trough date and recovery
    eq = 0.0; peak = 0.0; trough = 0.0; trough_idx = 0
    cum = []
    for i, v in enumerate(pnl):
        eq += v
        cum.append(eq)
        if eq > peak: peak = eq
        if eq < trough: trough = eq; trough_idx = i
    trough_date = grp.iloc[trough_idx]["dt"]
    final_eq = cum[-1]
    cum = np.array(cum)

    # DD onset: first trade where cum < 0 (or first material decline)
    onset_idx = next((i for i, v in enumerate(cum) if v < 0), 0)
    onset_date = grp.iloc[onset_idx]["dt"]

    # Quarter quartile of trough: 1st/2nd/3rd/4th quarter of the calendar quarter
    q_start = grp["dt"].min()
    q_end = grp["dt"].max()
    span = (q_end - q_start).total_seconds()
    rel_trough = (trough_date - q_start).total_seconds() / span if span > 0 else 0
    quarter_quartile = int(rel_trough * 4) + 1
    quarter_quartile = min(4, quarter_quartile)

    return dict(
        strategy=name, quarter=qstr, N=n, wins=wins, losses=losses,
        WR=wins/n*100,
        avg_win=avg_win, avg_loss=avg_loss,
        largest_loss=largest_loss,
        largest_loss_date=largest_loss_date.strftime("%Y-%m-%d") if largest_loss_date is not None else None,
        largest_loss_share_pct=largest_loss_share*100,
        top3_share_pct=top3_share*100,
        max_loss_streak=max_streak,
        net=final_eq, trough=trough,
        trough_date=trough_date.strftime("%Y-%m-%d"),
        trough_quartile=quarter_quartile,
        onset_date=onset_date.strftime("%Y-%m-%d"),
    )

print("=" * 130)
print("PER-LOSING-QUARTER STRUCTURAL TABLE")
print("=" * 130)
header = f"{'Strat':9s} | {'Q':6s} | {'N':>3s} | {'WR%':>5s} | {'avgW':>6s} | {'avgL':>7s} | {'maxL':>7s} | {'maxL%':>6s} | {'top3%':>6s} | {'strk':>4s} | {'trgh':>10s} | {'qtl':>3s}"
print(header)
print("-" * 130)

data = {name: load_exits(p) for name, p in FILES.items()}
rows = []
for name, qs in LOSING_QUARTERS.items():
    ex = data[name]
    for qstr in qs:
        q = pd.Period(qstr, "Q")
        grp = ex[ex["yq"] == q].sort_values("dt").reset_index(drop=True)
        r = analyze_losing_quarter(name, qstr, grp)
        rows.append(r)
        print(f"{r['strategy']:9s} | {r['quarter']:6s} | {r['N']:>3d} | {r['WR']:>5.1f} | "
              f"{r['avg_win']:>6.0f} | {r['avg_loss']:>7.0f} | {r['largest_loss']:>7.0f} | "
              f"{r['largest_loss_share_pct']:>5.1f}% | {r['top3_share_pct']:>5.1f}% | "
              f"{r['max_loss_streak']:>4d} | {r['trough_date']:>10s} | {r['trough_quartile']:>3d}")

print()
print("Legend:")
print("  maxL%   = largest single loss / sum of all losses in quarter (concentration of pain)")
print("  top3%   = sum of 3 worst losers / sum of all losses (tail-loss concentration)")
print("  strk    = max consecutive loser streak")
print("  qtl     = which quartile of the quarter the equity trough hit (1=early, 4=late)")
print()

# === Cross-strategy week clustering ===
print("=" * 130)
print("WEEKLY P&L MATRIX — focus on losing-quarter spans (and overlap detection)")
print("=" * 130)

# Build weekly Net per strategy
weekly = {}
for name, ex in data.items():
    w = ex.groupby("ymw")["pnl"].sum()
    weekly[name] = w

# Combine into a single DataFrame
weeks = sorted(set().union(*[set(w.index) for w in weekly.values()]))
wdf = pd.DataFrame(index=weeks)
for name, w in weekly.items():
    wdf[name] = w
wdf = wdf.fillna(0)
wdf["Portfolio"] = wdf.sum(axis=1)
wdf["losing_strats"] = (wdf[["Guardian","DJ30","NAS100","Aegis"]] < 0).sum(axis=1)

# Where do ≥2 strategies lose in same week?
mult = wdf[wdf["losing_strats"] >= 2].sort_values("Portfolio")
print(f"\nTotal week-events where 2+ strategies lost simultaneously: {len(mult)}")
print(f"Total week-events where 3+ strategies lost simultaneously: {(wdf['losing_strats']>=3).sum()}")
print(f"Total week-events where all 4 lost simultaneously: {(wdf['losing_strats']==4).sum()}")
print()

print("Worst portfolio weeks (sorted by Portfolio Net, top 15):")
worst = wdf.sort_values("Portfolio").head(15)
print(f"{'Week':18s} | {'Guard':>7s} | {'DJ30':>7s} | {'NAS':>7s} | {'Aegis':>7s} | {'Port':>8s} | {'#los':>4s}")
for idx, r in worst.iterrows():
    print(f"{str(idx):18s} | {r['Guardian']:>7,.0f} | {r['DJ30']:>7,.0f} | {r['NAS100']:>7,.0f} | {r['Aegis']:>7,.0f} | {r['Portfolio']:>8,.0f} | {int(r['losing_strats']):>4d}")

print()

# Where do worst weeks fall by year?
print("Worst-week distribution by year (top 30 weeks by Portfolio Net):")
worst30 = wdf.sort_values("Portfolio").head(30)
worst30_yrs = pd.Series([w.year for w in worst30.index]).value_counts().sort_index()
print(worst30_yrs.to_string())
print()

# === Monthly view of losing quarters ===
print("=" * 130)
print("MONTHLY P&L WITHIN LOSING-QUARTER SPANS")
print("=" * 130)
losing_q_periods = set()
for name, qs in LOSING_QUARTERS.items():
    for qstr in qs:
        losing_q_periods.add(pd.Period(qstr, "Q"))

for q in sorted(losing_q_periods):
    print(f"\n--- {q} ---")
    print(f"{'Month':10s} | {'Guard':>8s} | {'DJ30':>8s} | {'NAS':>8s} | {'Aegis':>8s} | {'Port':>9s}")
    months_in_q = pd.period_range(start=q.start_time, end=q.end_time, freq="M")
    for m in months_in_q:
        row = {}
        for name, ex in data.items():
            mp = ex[ex["ym"] == m]["pnl"].sum()
            row[name] = mp
        port = sum(row.values())
        print(f"{str(m):10s} | {row['Guardian']:>8,.0f} | {row['DJ30']:>8,.0f} | {row['NAS100']:>8,.0f} | {row['Aegis']:>8,.0f} | {port:>9,.0f}")

# === Day-of-week loss profile across all losing quarters ===
print()
print("=" * 130)
print("DAY-OF-WEEK LOSS DISTRIBUTION (across all losing quarters)")
print("=" * 130)
DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
for name, ex in data.items():
    losing_qs = [pd.Period(q, "Q") for q in LOSING_QUARTERS[name]]
    sub = ex[ex["yq"].isin(losing_qs)]
    if len(sub) == 0: continue
    sub = sub.copy()
    sub["dow"] = sub["dt"].dt.dayofweek
    by_dow = sub.groupby("dow").agg(N=("pnl", "count"), Net=("pnl", "sum"), Avg=("pnl", "mean")).reset_index()
    print(f"\n{name}:")
    print(f"  {'DOW':4s} {'N':>4s} {'Net':>9s} {'Avg':>7s}")
    for _, r in by_dow.iterrows():
        print(f"  {DOW[int(r['dow'])]:4s} {int(r['N']):>4d} {r['Net']:>9,.0f} {r['Avg']:>7,.0f}")
