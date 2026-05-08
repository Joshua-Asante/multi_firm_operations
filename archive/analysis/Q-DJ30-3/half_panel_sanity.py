"""Phase D — half-panel sanity check (NOT canonical regime-robustness gate).

Reads:  analysis/Q-DJ30-3/per_trade_gap.csv
Writes: analysis/Q-DJ30-3/half_panel_results.json (also stdout)

Per pre-reg §4.3, this is a 3-test sanity gate adapted from Q-DJ30-2's H1↔H2
PF-spread protocol but reframed for partition-hypothesis pp-lift.

Split point: trade_num 98 (matching Q-DJ30-2). H1 = trade_num 1-98, H2 = 99-197.

NOTE: Phase C verdict was NULL (all three primary gates failed). This Phase D
is run for diagnostic completeness in the closure findings doc, not to flip
the verdict. Per pre-reg §4.4, NULL fires on any single Phase C gate failure;
Phase D matters only if Phase C passes.
"""
from pathlib import Path
import csv
import json

import numpy as np

CSV = Path("analysis/Q-DJ30-3/per_trade_gap.csv")
OUT = Path("analysis/Q-DJ30-3/half_panel_results.json")

PRIMARY_Q = 90
SPLIT_TRADE_NUM = 98


def load_rows():
    with CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["trade_num"] = int(r["trade_num"])
        r["net_pnl_usd"] = float(r["net_pnl_usd"])
        for q in (80, 85, 90, 95):
            r[f"in_gap_p{q}"] = r[f"in_gap_p{q}"] == "True"
    return rows


def half_lift(rows, q):
    """For a given half-panel slice, compute (p_tail_in_q - p_nontail_in_q) in pp.
    Tail = worst-decile of THIS slice (separate from full-panel tail).
    """
    n = len(rows)
    pnls = np.array([r["net_pnl_usd"] for r in rows])
    sorted_idx = np.argsort(pnls)
    tail_count = max(1, round(0.10 * n))
    is_tail = np.zeros(n, dtype=bool)
    is_tail[sorted_idx[:tail_count]] = True
    in_q = np.array([r[f"in_gap_p{q}"] for r in rows])
    p_tail = in_q[is_tail].mean() * 100 if is_tail.any() else 0.0
    p_non = in_q[~is_tail].mean() * 100 if (~is_tail).any() else 0.0
    return {
        "n": n,
        "tail_count": int(tail_count),
        "in_q_count_tail": int((is_tail & in_q).sum()),
        "in_q_count_non": int((~is_tail & in_q).sum()),
        "p_tail_pct": float(p_tail),
        "p_nontail_pct": float(p_non),
        "lift_pp": float(p_tail - p_non),
    }


rows = load_rows()
bases = [r for r in rows if r["signal"] == "Long"]

h1 = [r for r in bases if r["trade_num"] <= SPLIT_TRADE_NUM]
h2 = [r for r in bases if r["trade_num"] > SPLIT_TRADE_NUM]

print(f"Loaded {len(rows)} entries (base={len(bases)})")
print(f"  H1 (trade_num <= {SPLIT_TRADE_NUM}): {len(h1)} base trades")
print(f"  H2 (trade_num >  {SPLIT_TRADE_NUM}): {len(h2)} base trades")
print()

# Date ranges for context
h1_dates = sorted(r["entry_date_utc"] for r in h1)
h2_dates = sorted(r["entry_date_utc"] for r in h2)
print(f"  H1 calendar range: {h1_dates[0]} -> {h1_dates[-1]}")
print(f"  H2 calendar range: {h2_dates[0]} -> {h2_dates[-1]}")
print()

results = {
    "metadata": {
        "split_trade_num": SPLIT_TRADE_NUM,
        "h1_n": len(h1),
        "h2_n": len(h2),
        "h1_calendar_range": [h1_dates[0], h1_dates[-1]],
        "h2_calendar_range": [h2_dates[0], h2_dates[-1]],
        "primary_quantile": PRIMARY_Q,
    }
}

# Per pre-reg §4.3 thresholds: H1 lift >= 0pp; H2 lift >= 0pp; |spread| <= 10pp
print(f"=== Phase D sanity gate at p{PRIMARY_Q} (per pre-reg §4.3) ===")
h1_p90 = half_lift(h1, PRIMARY_Q)
h2_p90 = half_lift(h2, PRIMARY_Q)
spread = abs(h1_p90["lift_pp"] - h2_p90["lift_pp"])

print(f"  H1 lift  : {h1_p90['lift_pp']:+.1f} pp  (tail {h1_p90['p_tail_pct']:.1f}% / nontail {h1_p90['p_nontail_pct']:.1f}%)")
print(f"  H2 lift  : {h2_p90['lift_pp']:+.1f} pp  (tail {h2_p90['p_tail_pct']:.1f}% / nontail {h2_p90['p_nontail_pct']:.1f}%)")
print(f"  Spread   : {spread:.1f} pp")
print()
print(f"  Gate H1 >= 0pp     : {'PASS' if h1_p90['lift_pp'] >= 0 else 'FAIL'}")
print(f"  Gate H2 >= 0pp     : {'PASS' if h2_p90['lift_pp'] >= 0 else 'FAIL'}")
print(f"  Gate spread <= 10pp: {'PASS' if spread <= 10 else 'FAIL'}")
print()

results["primary_p90"] = {
    "h1": h1_p90,
    "h2": h2_p90,
    "spread_pp": spread,
    "passes_h1_gate": h1_p90["lift_pp"] >= 0,
    "passes_h2_gate": h2_p90["lift_pp"] >= 0,
    "passes_spread_gate": spread <= 10,
    "all_three_pass": (h1_p90["lift_pp"] >= 0) and (h2_p90["lift_pp"] >= 0) and (spread <= 10),
}

# Sweep across all bins for diagnostic
print("=== Diagnostic: half-panel lift across bins ===")
print(f"{'bin':>5} | {'H1 lift':>8} | {'H2 lift':>8} | {'spread':>8}")
results["sweep"] = {}
for q in (80, 85, 90, 95):
    a = half_lift(h1, q)
    b = half_lift(h2, q)
    s = abs(a["lift_pp"] - b["lift_pp"])
    results["sweep"][f"p{q}"] = {"h1_lift_pp": a["lift_pp"], "h2_lift_pp": b["lift_pp"], "spread_pp": s}
    print(f"  p{q:>2} | {a['lift_pp']:+7.1f} pp | {b['lift_pp']:+7.1f} pp | {s:7.1f} pp")
print()

OUT.write_text(json.dumps(results, indent=2))
print(f"Wrote {OUT}")
