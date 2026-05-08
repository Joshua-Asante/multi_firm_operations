"""Step 3-4 - Tail stratum + Fisher exact + permutation + Rule-1 bootstrap.

Reads:  analysis/Q-DJ30-1/per_trade_proximity.csv
Writes: analysis/Q-DJ30-1/results.json

Primary stratum: base entries only (Signal == 'Long', n=197, tail=20).
Sensitivity:     all entries (n=224, tail=22) — matches brief's pre-reg.

Tests at primary 90-min window:
  1. Fisher exact (scipy.stats.fisher_exact, two-sided), with conditional
     odds-ratio CI (scipy.stats.contingency.odds_ratio, kind='conditional').
  2. Permutation test, n=10,000 resamples, shuffle is_tail label.
  3. Rule-1 bootstrap, n=1,000, sample-with-replacement on tail stratum;
     report p05/p50/p95 of in-window proportion. Gate:
     p05_tail_in_window - non_tail_in_window >= 5pp.

Sensitivity windows: {30, 60, 90, 120, 180}.
Sensitivity strata:  worst-decile (primary), worst-quintile, N=1-day-only-decile, <=-5R.
"""
from pathlib import Path
import csv
import json
import math
from collections import Counter

import numpy as np
from scipy import stats
from scipy.stats.contingency import odds_ratio as conditional_odds_ratio

CSV = Path("analysis/Q-DJ30-1/per_trade_proximity.csv")
OUT = Path("analysis/Q-DJ30-1/results.json")

WINDOWS = (30, 60, 90, 120, 180)
PRIMARY_WINDOW = 90
N_PERM = 10_000
N_BOOT = 1_000
SEED = 42

# Striker DJ30 nominal 1R at $200K @ 1.00% risk = $2,000 (proportional to risk_per_trade,
# which scales with equity in Pine; for tail-classification purposes we use a fixed
# nominal-R approximation per the brief: 1R ≈ $2,000 for "<= -5R" stratum).
NOMINAL_1R = 2000.0


def load_rows():
    with CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["net_pnl_usd"] = float(r["net_pnl_usd"])
        r["nearest_event_minutes_signed"] = int(r["nearest_event_minutes_signed"])
        r["n_entries_that_day"] = int(r["n_entries_that_day"])
        for w in WINDOWS:
            r[f"in_window_{w}"] = r[f"in_window_{w}"] == "True"
    return rows


def fisher_block(in_tail_in_w, in_tail_out_w, in_nontail_in_w, in_nontail_out_w):
    """Run Fisher + conditional odds-ratio CI on a 2x2 contingency table.

    Table layout:
        | in_window | outside_window
    tail|   a       |      b
    non |   c       |      d
    """
    a = in_tail_in_w
    b = in_tail_out_w
    c = in_nontail_in_w
    d = in_nontail_out_w
    table = [[a, b], [c, d]]

    fisher_or, fisher_p = stats.fisher_exact(table, alternative="two-sided")

    # Conditional OR with CI (Fisher-consistent)
    cor = conditional_odds_ratio(table, kind="conditional")
    ci_lo, ci_hi = cor.confidence_interval(confidence_level=0.95)
    cond_or = cor.statistic

    n_tail = a + b
    n_nontail = c + d
    p_tail = a / n_tail if n_tail else 0.0
    p_nontail = c / n_nontail if n_nontail else 0.0
    pp_diff = (p_tail - p_nontail) * 100  # in percentage points

    return {
        "table": [[int(a), int(b)], [int(c), int(d)]],
        "n_tail": int(n_tail),
        "n_nontail": int(n_nontail),
        "p_tail": float(p_tail),
        "p_nontail": float(p_nontail),
        "pp_diff": float(pp_diff),
        "fisher_p": float(fisher_p),
        "fisher_or": float(fisher_or) if math.isfinite(fisher_or) else None,
        "conditional_or": float(cond_or) if math.isfinite(cond_or) else None,
        "or_ci_95_lo": float(ci_lo) if math.isfinite(ci_lo) else None,
        "or_ci_95_hi": float(ci_hi) if math.isfinite(ci_hi) else None,
    }


def perm_test(in_window_arr: np.ndarray, is_tail_arr: np.ndarray, n_perm: int, seed: int):
    """Two-sided permutation test on the in-window proportion difference.

    Statistic: p(in_window | tail) - p(in_window | non-tail), in pp.
    """
    rng = np.random.default_rng(seed)
    obs = in_window_arr[is_tail_arr].mean() - in_window_arr[~is_tail_arr].mean()
    nulls = np.empty(n_perm)
    n_tail = is_tail_arr.sum()
    indices = np.arange(len(in_window_arr))
    for i in range(n_perm):
        shuffled_tail_idx = rng.choice(indices, size=n_tail, replace=False)
        mask = np.zeros(len(in_window_arr), dtype=bool)
        mask[shuffled_tail_idx] = True
        nulls[i] = in_window_arr[mask].mean() - in_window_arr[~mask].mean()
    p_two = float((np.abs(nulls) >= abs(obs)).mean())
    return {
        "observed_diff": float(obs * 100),  # pp
        "p_two_sided": p_two,
        "null_p05": float(np.percentile(nulls, 5) * 100),
        "null_p50": float(np.percentile(nulls, 50) * 100),
        "null_p95": float(np.percentile(nulls, 95) * 100),
    }


def rule1_bootstrap(tail_in_window: np.ndarray, n_boot: int, seed: int):
    """Bootstrap on the tail stratum only, sample-with-replacement.

    Returns p05/p50/p95 of in-window proportion in the bootstrapped tail.
    """
    rng = np.random.default_rng(seed + 1)
    n = len(tail_in_window)
    boots = np.empty(n_boot)
    for i in range(n_boot):
        sample = rng.choice(tail_in_window, size=n, replace=True)
        boots[i] = sample.mean()
    return {
        "p05": float(np.percentile(boots, 5) * 100),
        "p50": float(np.percentile(boots, 50) * 100),
        "p95": float(np.percentile(boots, 95) * 100),
    }


def run_analysis(rows: list, label: str, tail_count: int) -> dict:
    """Run primary + sensitivity analyses on given row set with given tail_count."""
    n = len(rows)
    pnls = np.array([r["net_pnl_usd"] for r in rows])

    # Tail = lowest tail_count net_pnl
    sorted_idx = np.argsort(pnls)
    tail_idx = sorted_idx[:tail_count]
    is_tail = np.zeros(n, dtype=bool)
    is_tail[tail_idx] = True

    out = {"label": label, "n": n, "tail_count": int(tail_count)}

    # Primary 90-min window: full Fisher + permutation + Rule-1
    in_w = np.array([r[f"in_window_{PRIMARY_WINDOW}"] for r in rows])
    a = int(((is_tail) & (in_w)).sum())
    b = int(((is_tail) & (~in_w)).sum())
    c = int(((~is_tail) & (in_w)).sum())
    d = int(((~is_tail) & (~in_w)).sum())

    out["primary_90"] = fisher_block(a, b, c, d)
    out["permutation_90"] = perm_test(in_w, is_tail, N_PERM, SEED)
    out["rule1_90"] = rule1_bootstrap(in_w[is_tail].astype(int), N_BOOT, SEED)

    # Pre-registered gate: p05_tail - p_nontail >= 5pp
    out["rule1_90"]["p_nontail"] = float(in_w[~is_tail].mean() * 100)
    out["rule1_90"]["p05_lift_vs_nontail"] = (
        out["rule1_90"]["p05"] - out["rule1_90"]["p_nontail"]
    )
    out["rule1_90"]["passes_5pp_gate"] = out["rule1_90"]["p05_lift_vs_nontail"] >= 5

    # Sensitivity: all 5 windows × 4 strata (just contingency)
    out["sensitivity"] = {}

    strata = {"worst_decile": is_tail}
    # Worst quintile
    quintile_count = max(1, n // 5)
    is_quintile = np.zeros(n, dtype=bool)
    is_quintile[sorted_idx[:quintile_count]] = True
    strata["worst_quintile"] = is_quintile

    # N=1-day-only worst-decile
    n_entries_per_day = np.array([r["n_entries_that_day"] for r in rows])
    is_n1 = (n_entries_per_day == 1)
    n1_pnls_idx = sorted_idx[np.isin(sorted_idx, np.where(is_n1)[0])]
    n1_decile_count = max(1, n1_pnls_idx.size // 10)
    is_n1_decile = np.zeros(n, dtype=bool)
    is_n1_decile[n1_pnls_idx[:n1_decile_count]] = True
    strata["n1_decile"] = is_n1_decile

    # <= -5R = -$10,000
    is_5r = pnls <= -5 * NOMINAL_1R
    strata["lte_neg_5r"] = is_5r

    for stratum_name, mask in strata.items():
        if mask.sum() == 0:
            continue
        out["sensitivity"][stratum_name] = {"n": int(mask.sum())}
        for w in WINDOWS:
            in_w_w = np.array([r[f"in_window_{w}"] for r in rows])
            a_ = int(((mask) & (in_w_w)).sum())
            b_ = int(((mask) & (~in_w_w)).sum())
            c_ = int(((~mask) & (in_w_w)).sum())
            d_ = int(((~mask) & (~in_w_w)).sum())
            blk = fisher_block(a_, b_, c_, d_)
            out["sensitivity"][stratum_name][f"window_{w}"] = blk

    return out


# --- Main ---
rows = load_rows()
bases = [r for r in rows if r["signal"] == "Long"]

print(f"Loaded {len(rows)} entries (base={len(bases)}, pyramid={len(rows)-len(bases)})")
print()

# Primary: base only, tail = 10% of n
primary_tail = round(0.10 * len(bases))  # 20
sensitivity_tail = round(0.10 * len(rows))  # 22

result_base = run_analysis(bases, "primary_base_only", primary_tail)
result_all = run_analysis(rows, "sensitivity_all_entries", sensitivity_tail)

results = {
    "metadata": {
        "csv": str(CSV),
        "primary_window_min": PRIMARY_WINDOW,
        "windows": list(WINDOWS),
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

# --- Print primary results ---
def print_primary(label, r):
    p90 = r["primary_90"]
    perm = r["permutation_90"]
    rul = r["rule1_90"]
    print(f"=== {label} (n={r['n']}, tail={r['tail_count']}) ===")
    print(f"  contingency [tail x in_window90]    : {p90['table']}")
    print(f"  p_tail in window                    : {p90['p_tail']*100:.1f}%")
    print(f"  p_nontail in window (baseline)      : {p90['p_nontail']*100:.1f}%")
    print(f"  pp diff                             : {p90['pp_diff']:+.1f} pp")
    print(f"  Fisher exact p (two-sided)          : {p90['fisher_p']:.4f}")
    or_str = f"{p90['conditional_or']:.2f}" if p90['conditional_or'] is not None else "n/a"
    ci_str = f"[{p90['or_ci_95_lo']:.2f}, {p90['or_ci_95_hi']:.2f}]" if p90['or_ci_95_lo'] is not None else "n/a"
    print(f"  Conditional OR [95% CI]             : {or_str}  {ci_str}")
    print(f"  Permutation p (two-sided, n=10k)    : {perm['p_two_sided']:.4f}")
    print(f"  Rule-1 tail bootstrap p05/p50/p95   : {rul['p05']:.1f} / {rul['p50']:.1f} / {rul['p95']:.1f} %")
    print(f"  Rule-1 lift (p05_tail - p_nontail)  : {rul['p05_lift_vs_nontail']:+.1f} pp  -> "
          f"{'PASS' if rul['passes_5pp_gate'] else 'FAIL'} (>=5pp gate)")
    print()

print_primary("PRIMARY (base entries n=197)", result_base)
print_primary("SENSITIVITY (all entries n=224)", result_all)

# --- Window sensitivity ---
print("=== Window sensitivity (worst-decile stratum, primary base) ===")
print(f"{'window':>8} | {'p_tail':>7} | {'p_non':>7} | {'pp_diff':>8} | {'Fisher_p':>9}")
sens = result_base["sensitivity"]["worst_decile"]
for w in WINDOWS:
    blk = sens[f"window_{w}"]
    print(f"{w:>5} min | {blk['p_tail']*100:6.1f}% | {blk['p_nontail']*100:6.1f}% | {blk['pp_diff']:+7.1f} pp | {blk['fisher_p']:8.4f}")
