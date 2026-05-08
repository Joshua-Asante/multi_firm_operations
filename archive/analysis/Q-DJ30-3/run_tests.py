"""Phase C/F — Tail stratum + Fisher exact + permutation + Rule-1 bootstrap on gap-quantile membership.

Reads:  analysis/Q-DJ30-3/per_trade_gap.csv
Writes: analysis/Q-DJ30-3/results.json

Ported from analysis/Q-DJ30-1/run_tests.py with the membership column renamed
from in_window_{30,60,90,120,180} (event proximity) to in_gap_p{80,85,90,95}
(panel-quantile gap magnitude).

Primary stratum: base entries (Signal == 'Long', n=197, tail=20).
Sensitivity:     all entries (n=224, tail=22).

Tests at primary p90:
  1. Fisher exact, two-sided  (gate: p < 0.10)
  2. Permutation, n=10,000     (gate: p < 0.10)
  3. Rule-1 bootstrap, n=1,000 (gate: p05_tail_in_p90 - p_nontail_in_p90 >= 5pp)

All three must clear for non-null verdict.
Sensitivity sweep: {p80, p85, p90, p95} bin × {worst_decile, worst_quintile, n1_decile, lte_neg_5r} stratum.
"""
from pathlib import Path
import csv
import json
import math

import numpy as np
from scipy import stats
from scipy.stats.contingency import odds_ratio as conditional_odds_ratio

CSV = Path("analysis/Q-DJ30-3/per_trade_gap.csv")
OUT = Path("analysis/Q-DJ30-3/results.json")

QUANTILES = (80, 85, 90, 95)
PRIMARY_Q = 90
N_PERM = 10_000
N_BOOT = 1_000
SEED = 42

NOMINAL_1R = 2000.0  # Striker DJ30 nominal R = 1.00% × $200K (approximation)


def load_rows():
    with CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["net_pnl_usd"] = float(r["net_pnl_usd"])
        r["n_entries_that_day"] = int(r["n_entries_that_day"])
        r["abs_gap_atr"] = float(r["abs_gap_atr"])
        for q in QUANTILES:
            r[f"in_gap_p{q}"] = r[f"in_gap_p{q}"] == "True"
    return rows


def fisher_block(a, b, c, d):
    table = [[int(a), int(b)], [int(c), int(d)]]
    fisher_or, fisher_p = stats.fisher_exact(table, alternative="two-sided")
    cor = conditional_odds_ratio(table, kind="conditional")
    ci_lo, ci_hi = cor.confidence_interval(confidence_level=0.95)
    cond_or = cor.statistic
    n_tail = a + b
    n_non = c + d
    p_tail = a / n_tail if n_tail else 0.0
    p_non = c / n_non if n_non else 0.0
    pp_diff = (p_tail - p_non) * 100
    return {
        "table": table,
        "n_tail": int(n_tail),
        "n_nontail": int(n_non),
        "p_tail": float(p_tail),
        "p_nontail": float(p_non),
        "pp_diff": float(pp_diff),
        "fisher_p": float(fisher_p),
        "fisher_or": float(fisher_or) if math.isfinite(fisher_or) else None,
        "conditional_or": float(cond_or) if math.isfinite(cond_or) else None,
        "or_ci_95_lo": float(ci_lo) if math.isfinite(ci_lo) else None,
        "or_ci_95_hi": float(ci_hi) if math.isfinite(ci_hi) else None,
    }


def perm_test(in_bin: np.ndarray, is_tail: np.ndarray, n_perm: int, seed: int):
    rng = np.random.default_rng(seed)
    obs = in_bin[is_tail].mean() - in_bin[~is_tail].mean()
    nulls = np.empty(n_perm)
    n_tail = is_tail.sum()
    indices = np.arange(len(in_bin))
    for i in range(n_perm):
        shuffled = rng.choice(indices, size=n_tail, replace=False)
        m = np.zeros(len(in_bin), dtype=bool)
        m[shuffled] = True
        nulls[i] = in_bin[m].mean() - in_bin[~m].mean()
    return {
        "observed_diff_pp": float(obs * 100),
        "p_two_sided": float((np.abs(nulls) >= abs(obs)).mean()),
        "null_p05_pp": float(np.percentile(nulls, 5) * 100),
        "null_p50_pp": float(np.percentile(nulls, 50) * 100),
        "null_p95_pp": float(np.percentile(nulls, 95) * 100),
    }


def rule1_bootstrap(tail_in_bin: np.ndarray, n_boot: int, seed: int):
    rng = np.random.default_rng(seed + 1)
    n = len(tail_in_bin)
    boots = np.empty(n_boot)
    for i in range(n_boot):
        s = rng.choice(tail_in_bin, size=n, replace=True)
        boots[i] = s.mean()
    return {
        "p05_pct": float(np.percentile(boots, 5) * 100),
        "p50_pct": float(np.percentile(boots, 50) * 100),
        "p95_pct": float(np.percentile(boots, 95) * 100),
    }


def run_analysis(rows, label, tail_count):
    n = len(rows)
    pnls = np.array([r["net_pnl_usd"] for r in rows])
    sorted_idx = np.argsort(pnls)
    is_tail = np.zeros(n, dtype=bool)
    is_tail[sorted_idx[:tail_count]] = True

    out = {"label": label, "n": n, "tail_count": int(tail_count)}

    # Primary p90 — full Fisher + permutation + Rule-1
    in_p = np.array([r[f"in_gap_p{PRIMARY_Q}"] for r in rows])
    a = int(((is_tail) & (in_p)).sum())
    b = int(((is_tail) & (~in_p)).sum())
    c = int(((~is_tail) & (in_p)).sum())
    d = int(((~is_tail) & (~in_p)).sum())

    out["primary_p90"] = fisher_block(a, b, c, d)
    out["permutation_p90"] = perm_test(in_p, is_tail, N_PERM, SEED)
    out["rule1_p90"] = rule1_bootstrap(in_p[is_tail].astype(int), N_BOOT, SEED)

    # Pre-registered gates
    p_nontail = float(in_p[~is_tail].mean() * 100)
    out["rule1_p90"]["p_nontail_pct"] = p_nontail
    out["rule1_p90"]["p05_lift_vs_nontail_pp"] = (
        out["rule1_p90"]["p05_pct"] - p_nontail
    )
    out["rule1_p90"]["passes_5pp_gate"] = (
        out["rule1_p90"]["p05_lift_vs_nontail_pp"] >= 5
    )
    out["primary_p90"]["passes_fisher_gate"] = out["primary_p90"]["fisher_p"] < 0.10
    out["permutation_p90"]["passes_perm_gate"] = out["permutation_p90"]["p_two_sided"] < 0.10

    # Sensitivity sweep
    out["sensitivity"] = {}

    strata = {"worst_decile": is_tail}

    quintile_count = max(1, n // 5)
    is_quintile = np.zeros(n, dtype=bool)
    is_quintile[sorted_idx[:quintile_count]] = True
    strata["worst_quintile"] = is_quintile

    n1_per_day = np.array([r["n_entries_that_day"] for r in rows])
    is_n1 = (n1_per_day == 1)
    n1_idx = sorted_idx[np.isin(sorted_idx, np.where(is_n1)[0])]
    n1_decile_count = max(1, n1_idx.size // 10)
    is_n1_decile = np.zeros(n, dtype=bool)
    is_n1_decile[n1_idx[:n1_decile_count]] = True
    strata["n1_decile"] = is_n1_decile

    is_5r = pnls <= -5 * NOMINAL_1R
    strata["lte_neg_5r"] = is_5r

    for stratum_name, mask in strata.items():
        if mask.sum() == 0:
            continue
        out["sensitivity"][stratum_name] = {"n": int(mask.sum())}
        for q in QUANTILES:
            in_q = np.array([r[f"in_gap_p{q}"] for r in rows])
            a_ = int(((mask) & (in_q)).sum())
            b_ = int(((mask) & (~in_q)).sum())
            c_ = int(((~mask) & (in_q)).sum())
            d_ = int(((~mask) & (~in_q)).sum())
            out["sensitivity"][stratum_name][f"p{q}"] = fisher_block(a_, b_, c_, d_)

    return out


# --- Main ---
rows = load_rows()
bases = [r for r in rows if r["signal"] == "Long"]

print(f"Loaded {len(rows)} entries (base={len(bases)}, pyramid={len(rows)-len(bases)})")
print()

primary_tail = round(0.10 * len(bases))
sensitivity_tail = round(0.10 * len(rows))

result_base = run_analysis(bases, "primary_base_only", primary_tail)
result_all = run_analysis(rows, "sensitivity_all_entries", sensitivity_tail)

results = {
    "metadata": {
        "csv": str(CSV),
        "primary_quantile": PRIMARY_Q,
        "quantiles_swept": list(QUANTILES),
        "n_perm": N_PERM,
        "n_boot": N_BOOT,
        "seed": SEED,
        "nominal_1r_usd": NOMINAL_1R,
    },
    "primary_base_only": result_base,
    "sensitivity_all_entries": result_all,
}

OUT.write_text(json.dumps(results, indent=2))
print(f"Wrote {OUT}")
print()


def print_primary(label, r):
    p = r["primary_p90"]
    perm = r["permutation_p90"]
    rul = r["rule1_p90"]
    print(f"=== {label} (n={r['n']}, tail={r['tail_count']}, bin=in_gap_p{PRIMARY_Q}) ===")
    print(f"  contingency [tail x in_p90]      : {p['table']}")
    print(f"  p_tail in p90                    : {p['p_tail']*100:.1f}%")
    print(f"  p_nontail in p90 (baseline)      : {p['p_nontail']*100:.1f}%")
    print(f"  pp diff (tail - nontail)         : {p['pp_diff']:+.1f} pp")
    fp = "PASS" if p['passes_fisher_gate'] else "FAIL"
    print(f"  Fisher exact p (two-sided)       : {p['fisher_p']:.4f}  {fp} (gate p<0.10)")
    or_str = f"{p['conditional_or']:.2f}" if p['conditional_or'] is not None else "n/a"
    ci_str = f"[{p['or_ci_95_lo']:.2f}, {p['or_ci_95_hi']:.2f}]" if p['or_ci_95_lo'] is not None else "n/a"
    print(f"  Conditional OR [95% CI]          : {or_str}  {ci_str}")
    pp = "PASS" if perm['passes_perm_gate'] else "FAIL"
    print(f"  Permutation p (two-sided, 10k)   : {perm['p_two_sided']:.4f}  {pp} (gate p<0.10)")
    print(f"  Rule-1 tail bootstrap p05/50/95  : {rul['p05_pct']:.1f}/{rul['p50_pct']:.1f}/{rul['p95_pct']:.1f}%")
    rg = "PASS" if rul['passes_5pp_gate'] else "FAIL"
    print(f"  Rule-1 lift (p05 - p_nontail)    : {rul['p05_lift_vs_nontail_pp']:+.1f} pp  {rg} (gate >=5pp)")

    all_pass = p['passes_fisher_gate'] and perm['passes_perm_gate'] and rul['passes_5pp_gate']
    print(f"  ALL THREE GATES                  : {'PASS' if all_pass else 'FAIL'}")
    print()


print_primary("PRIMARY (base entries n=197)", result_base)
print_primary("SENSITIVITY (all entries n=224)", result_all)


# Sensitivity sweep table
print("=== Sensitivity sweep (worst-decile primary base) ===")
print(f"{'bin':>6} | {'p_tail':>7} | {'p_non':>7} | {'pp_diff':>8} | {'Fisher_p':>9}")
sens = result_base["sensitivity"]["worst_decile"]
for q in QUANTILES:
    blk = sens[f"p{q}"]
    print(f"  p{q:>2}  | {blk['p_tail']*100:6.1f}% | {blk['p_nontail']*100:6.1f}% | {blk['pp_diff']:+7.1f} pp | {blk['fisher_p']:8.4f}")
print()

print("=== Stratum sensitivity at p90 ===")
print(f"{'stratum':>20} | {'n':>4} | {'p_tail':>7} | {'p_non':>7} | {'pp_diff':>8} | {'Fisher_p':>9}")
for stratum_name in ["worst_decile", "worst_quintile", "n1_decile", "lte_neg_5r"]:
    s = result_base["sensitivity"].get(stratum_name)
    if s is None:
        continue
    blk = s.get("p90")
    if blk is None:
        continue
    print(f"  {stratum_name:>18} | {s['n']:>4} | {blk['p_tail']*100:6.1f}% | {blk['p_nontail']*100:6.1f}% | {blk['pp_diff']:+7.1f} pp | {blk['fisher_p']:8.4f}")
