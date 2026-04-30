"""MSEE H1 — Empirical community matrix via MC perturbation.

Q-MSEE-1 from docs/methodology/msee/open_questions.md.

Estimates the community matrix entries via finite-difference perturbation
in mc_explore.py at +/-10% per-strategy allocation. The strict Farmer
definition is

    A_ij = d r_i / d w_j

which on this MC structure (strategy daily P&L paths bootstrapped
independently from the panel) is identically 0 for i != j by
construction — there is no within-MC mechanism for strategy j's
allocation to affect strategy i's daily P&L distribution. The diagonal
entries A_ii equal mean R_i × scaling-factor and are linear in w_i.

What this script reports as the operationally meaningful equivalent:
the **portfolio-outcome sensitivity matrix** — how each portfolio
metric (pass rate, bust rate, p99 DD, median days-to-pass) responds
to a +/-10% perturbation of each strategy's allocation. This is what
"community matrix" most usefully maps to here under the MC's
independence assumption.

Falsifier (for the prediction): no portfolio-metric sensitivity to
allocation perturbation (would imply allocations are not load-bearing
— would falsify the lock-decision rationale).

PRE-Q GATE:
  D: ±10% perturbation grid (linearization step).
  S: 7 runs total (baseline + 6 single-strategy perturbations).
  A: 2K sims × 3 seeds per run.

Reproducibility: `python analysis/msee/h1_community_matrix.py`
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from portfolio_mc import (  # noqa: E402
    SEEDS, ALLOCATIONS, STRATS,
)
from mc_explore import (  # noqa: E402
    load_panel_with_perturb, run_seed_explore, BANNER,
)

OUT_JSON = ROOT / "analysis" / "msee" / "h1_community_matrix.json"

DD_TRIGGER = 0.010
DD_SCALE = 0.40
SIMS_PER_SEED = 2000
PERTURB_FRACTION = 0.10  # +/-10%


def aggregate(seeds_results: list, per_seed: int) -> dict:
    pass_r = np.mean([r["outcomes"]["pass"] / per_seed for r in seeds_results])
    bust_r = np.mean([(r["outcomes"]["bust_daily"]
                       + r["outcomes"]["bust_static"]) / per_seed
                      for r in seeds_results])
    to_r = np.mean([r["outcomes"]["timeout"] / per_seed for r in seeds_results])
    dds = np.array([d for r in seeds_results for d in r["max_dds"]])
    days = [d for r in seeds_results for d in r["days_to_pass"]]
    return {
        "pass_rate": float(pass_r),
        "bust_rate": float(bust_r),
        "timeout_rate": float(to_r),
        "p99_dd": float(np.percentile(dds, 99)),
        "median_days_to_pass": (int(np.median(days)) if days else None),
    }


def run_config(perturb: dict, label: str) -> dict:
    panel, blocks, scale_info, alloc = load_panel_with_perturb(perturb)
    seeds_results = []
    for seed in SEEDS:
        r = run_seed_explore(seed, SIMS_PER_SEED, blocks,
                             DD_TRIGGER, DD_SCALE, retain_curves=False)
        seeds_results.append(r)
    agg = aggregate(seeds_results, SIMS_PER_SEED)
    return {
        "label": label,
        "perturb": perturb,
        "perturbed_alloc": alloc,
        **agg,
    }


def main() -> None:
    print(BANNER)
    print(f"H1 community-matrix: ±{PERTURB_FRACTION*100:.0f}% perturbation grid")
    print(f"Runs: {1 + 2 * len(STRATS)} (baseline + 2 per strategy), "
          f"{SIMS_PER_SEED:,} sims × {len(SEEDS)} seeds each")
    print()

    runs = []
    baseline = run_config({s: 1.0 for s in STRATS}, "baseline")
    runs.append(baseline)
    print(f"  baseline:                pass={baseline['pass_rate']:.4f}  "
          f"bust={baseline['bust_rate']:.4f}  "
          f"p99dd={baseline['p99_dd']:.4f}  "
          f"medDays={baseline['median_days_to_pass']}")

    perturbed = []
    for s in STRATS:
        for sign in (+1, -1):
            mult = 1.0 + sign * PERTURB_FRACTION
            perturb = {x: 1.0 for x in STRATS}
            perturb[s] = mult
            label = f"{s}_{'+' if sign>0 else '-'}{PERTURB_FRACTION*100:.0f}pct"
            r = run_config(perturb, label)
            perturbed.append(r)
            runs.append(r)
            print(f"  {label:25s} pass={r['pass_rate']:.4f}  "
                  f"bust={r['bust_rate']:.4f}  "
                  f"p99dd={r['p99_dd']:.4f}  "
                  f"medDays={r['median_days_to_pass']}")

    # Build per-metric sensitivity matrix:
    #   sens[metric][strategy] = (metric_at_+10pct - metric_at_-10pct) / (2 * 0.10 * w_baseline)
    # i.e., partial derivative of metric wrt allocation fraction.
    metrics = ["pass_rate", "bust_rate", "p99_dd"]
    sensitivity = {m: {} for m in metrics}
    for s in STRATS:
        plus = next(r for r in perturbed
                    if r["perturb"][s] > 1.0)
        minus = next(r for r in perturbed
                     if r["perturb"][s] < 1.0)
        for m in metrics:
            d_metric = plus[m] - minus[m]
            d_w = (plus["perturbed_alloc"][s] - minus["perturbed_alloc"][s])
            sensitivity[m][s] = float(d_metric / d_w) if d_w != 0 else float("nan")

    summary = {
        "question": "Q-MSEE-1 — community matrix via MC perturbation (H1, P1)",
        "feed": "OANDA",
        "canonical_status": "EXPLORATORY",
        "banner": BANNER,
        "structural_note": (
            "On this MC the cross-strategy elements A_ij (i!=j) are 0 by "
            "construction — strategy paths are independently bootstrapped. "
            "The portfolio-outcome sensitivity matrix below is the "
            "operationally meaningful substitute."
        ),
        "perturb_fraction": PERTURB_FRACTION,
        "sims_per_seed": SIMS_PER_SEED,
        "seeds": list(SEEDS),
        "baseline_alloc": dict(ALLOCATIONS),
        "runs": runs,
        "portfolio_outcome_sensitivity_d_metric_d_w": sensitivity,
    }

    OUT_JSON.write_text(json.dumps(summary, indent=2, default=str))

    print()
    print(f"  Portfolio-outcome sensitivity (d metric / d allocation):")
    for m in metrics:
        cells = "  ".join(f"{s}={sensitivity[m][s]:+.3f}" for s in STRATS)
        print(f"    {m:20s}  {cells}")
    print()
    print(f"Wrote: {OUT_JSON.relative_to(ROOT)}")
    print(BANNER)


if __name__ == "__main__":
    main()
