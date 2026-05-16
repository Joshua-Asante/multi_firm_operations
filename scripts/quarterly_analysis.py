"""Quarter-by-quarter performance for the 4 locked strategies since 2022-01-01.

Uses full-range Pepperstone TV exports (2026-05-05 vintage) which extend back to
2022-01. These are documented archival panels in references/baselines.md but
contain the trade record needed for a quarterly cut. Per-strategy risk is what
the Pine file emitted — Guardian 0.34%, DJ30 1.00%, NAS100 0.40%, Aegis 1.50%
(unified-allocation lock as of 2026-04-17).
"""

import pandas as pd
from pathlib import Path

BASE = Path(r"C:\Users\joshu\multi_firm_operations\data\tv_exports\pepperstone")

FILES = {
    "Guardian":     BASE / "Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-05_33781.csv",
    "DJ30":         BASE / "Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv",
    "NAS100":       BASE / "Striker_NAS100_v1_PEPPERSTONE_NAS100_2026-05-05_7ca6f.csv",
    "Aegis":        BASE / "Aegis_USDJPY_v4.3_PEPPERSTONE_USDJPY_2026-04-26_0bf1b.csv",
}

def load_exits(path):
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
    df["dt"] = pd.to_datetime(df["Date and time"], errors="coerce")
    ex = df[df["Type"].str.startswith("Exit", na=False)].copy()
    ex = ex.sort_values("dt").reset_index(drop=True)
    ex["pnl"] = ex["Net P&L USD"].astype(float)
    ex["yq"] = ex["dt"].dt.to_period("Q")
    return ex

def metrics_block(grp):
    n = len(grp)
    w = int((grp["pnl"] > 0).sum())
    L = n - w
    gw = float(grp.loc[grp["pnl"] > 0, "pnl"].sum())
    gl = float(grp.loc[grp["pnl"] <= 0, "pnl"].sum())  # negative
    pf = gw / abs(gl) if gl != 0 else float("inf")
    net = float(grp["pnl"].sum())
    wr = (w / n * 100) if n else 0.0
    # DD reconstruction WITHIN the quarter (start at 0)
    eq = 0.0; peak = 0.0; max_dd = 0.0
    for v in grp["pnl"]:
        eq += v
        if eq > peak: peak = eq
        dd = peak - eq
        if dd > max_dd: max_dd = dd
    return dict(N=n, WR=wr, PF=pf, Net=net, MaxDD_in_q=max_dd, GW=gw, GL=gl)

# Load all four
data = {name: load_exits(p) for name, p in FILES.items()}

# Print sanity totals
print("=== File sanity (full-range totals) ===")
for name, ex in data.items():
    print(f"{name:10s}  n={len(ex):4d}  start={ex['dt'].min().date()}  end={ex['dt'].max().date()}  Net=${ex['pnl'].sum():>12,.0f}")
print()

# Build quarterly table per strategy
ALL_QS = sorted(set().union(*[set(ex["yq"].unique()) for ex in data.values()]))
ALL_QS = [q for q in ALL_QS if q.start_time >= pd.Timestamp("2022-01-01")]

# Per-strategy quarterly rows
print("=== Quarterly per-strategy ===")
header = f"{'Quarter':8s} | {'Strat':9s} | {'N':>4s} | {'WR%':>6s} | {'PF':>6s} | {'Net $':>11s} | {'qDD $':>9s}"
print(header)
print("-" * len(header))
rows = []
for q in ALL_QS:
    for name, ex in data.items():
        g = ex[ex["yq"] == q]
        if len(g) == 0:
            print(f"{str(q):8s} | {name:9s} | {0:>4d} | {'—':>6s} | {'—':>6s} | {'—':>11s} | {'—':>9s}")
            rows.append({"Quarter": str(q), "Strat": name, "N": 0, "WR": None, "PF": None, "Net": 0.0, "qDD": 0.0})
            continue
        m = metrics_block(g)
        pf_str = f"{m['PF']:.2f}" if m['PF'] != float('inf') else "inf"
        print(f"{str(q):8s} | {name:9s} | {m['N']:>4d} | {m['WR']:>6.1f} | {pf_str:>6s} | {m['Net']:>11,.0f} | {m['MaxDD_in_q']:>9,.0f}")
        rows.append({"Quarter": str(q), "Strat": name, "N": m["N"], "WR": m["WR"], "PF": m["PF"], "Net": m["Net"], "qDD": m["MaxDD_in_q"]})

# Portfolio-level per quarter
print()
print("=== Portfolio aggregate (sum across 4 strategies) ===")
print(f"{'Quarter':8s} | {'N_tot':>5s} | {'Net $':>12s} | {'CumNet $':>13s}")
print("-" * 50)
df = pd.DataFrame(rows)
df_q = df.groupby("Quarter").agg(N_tot=("N", "sum"), Net=("Net", "sum")).reset_index()
df_q["CumNet"] = df_q["Net"].cumsum()
for _, r in df_q.iterrows():
    print(f"{r['Quarter']:8s} | {r['N_tot']:>5d} | {r['Net']:>12,.0f} | {r['CumNet']:>13,.0f}")

# Also: per-strategy yearly summary
print()
print("=== Per-strategy yearly (rolled up) ===")
df["Year"] = df["Quarter"].str[:4]
yearly = df.groupby(["Year", "Strat"]).agg(N=("N", "sum"), Net=("Net", "sum")).reset_index()
print(yearly.pivot(index="Year", columns="Strat", values="Net").fillna(0).round(0).to_string())
print()
print("--- Yearly trade counts ---")
print(yearly.pivot(index="Year", columns="Strat", values="N").fillna(0).astype(int).to_string())

# Cross-strategy correlation of quarterly Net
print()
print("=== Quarterly Net correlation (between strategies) ===")
pivot = df.pivot(index="Quarter", columns="Strat", values="Net").fillna(0)
print(pivot.corr().round(2).to_string())

# Drawdown quarters per strategy
print()
print("=== Losing quarters per strategy ===")
for name in ["Guardian", "DJ30", "NAS100", "Aegis"]:
    losers = df[(df["Strat"] == name) & (df["Net"] < 0)]
    print(f"{name:10s}: {len(losers)} losing q's, total $={losers['Net'].sum():,.0f}")
    for _, r in losers.iterrows():
        print(f"   {r['Quarter']}  N={r['N']:>3d}  Net=${r['Net']:>10,.0f}")
