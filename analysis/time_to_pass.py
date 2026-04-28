"""
time_to_pass — extract days-to-pass distribution from the locked portfolio MC.

Pure measurement: reuses portfolio_mc.run_seed as-is (which already collects
days_to_pass for passing sims and timeout/bust counts). Adds p10/p50/p90
percentiles and right-censored %.

Run from the main pipeline dir so data/tv_exports/*.csv resolves.
    python -m prop_firm_pipeline.tools.time_to_pass
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# Allow running as a script from the worktree by adding parent on path.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import portfolio_mc as pmc  # noqa: E402

# Worktree has no data/ (CSVs are gitignored). Point at the main repo's data.
MAIN_DATA = Path(r"C:/Users/joshu/prop_firm_pipeline/data/tv_exports")
if not pmc.CSV_DIR.exists() and MAIN_DATA.exists():
    pmc.CSV_DIR = MAIN_DATA


def main():
    # Load panel + blocks via the MC's own loader (locked 2026-04-17 config).
    trades_by_strat, panel, blocks, scale_info = pmc._load_all(pmc.ALLOCATIONS)

    print("Scale factors (for sanity):")
    for s, info in scale_info.items():
        print(f"  {s:<9} 1R=${info['implied_1r']:>7,.2f}  "
              f"scale={info['scale']:>6.3f}  n={info['n_trades']}")
    print(f"Panel: {panel.index.min().date()} -> {panel.index.max().date()}  "
          f"({len(panel)} bdays, {len(blocks)} week-blocks)")
    print()

    seeds_results = [
        pmc.run_seed(seed, pmc.SIMS_PER_SEED, blocks,
                     pmc.DD_TRIGGER, pmc.DD_SCALE, pmc.HORIZON_DAYS)
        for seed in pmc.SEEDS
    ]

    total = pmc.SIMS_PER_SEED * len(pmc.SEEDS)
    passes = sum(r["outcomes"]["pass"] for r in seeds_results)
    busts = sum(r["outcomes"]["bust_daily"] + r["outcomes"]["bust_static"]
                for r in seeds_results)
    timeouts = sum(r["outcomes"]["timeout"] for r in seeds_results)

    pass_rate = passes / total
    bust_rate = busts / total
    timeout_rate = timeouts / total  # right-censored

    all_days = [d for r in seeds_results for d in r["days_to_pass"]]
    p10 = int(np.percentile(all_days, 10))
    p50 = int(np.percentile(all_days, 50))
    p90 = int(np.percentile(all_days, 90))

    print("=== Time-to-pass distribution ===")
    print(f"Sims: {total:,} ({pmc.SIMS_PER_SEED:,} × {len(pmc.SEEDS)} seeds), "
          f"horizon {pmc.HORIZON_DAYS} days")
    print(f"Pass:             {pass_rate:>7.2%}  (baseline 93.00%)")
    print(f"Bust:             {bust_rate:>7.2%}")
    print(f"Right-censored:   {timeout_rate:>7.2%}  (timeout >= 150d)")
    print()
    print("Days-to-pass (passing sims only):")
    print(f"  p10:  {p10}")
    print(f"  p50:  {p50}")
    print(f"  p90:  {p90}")
    print()

    # Halt-condition check
    delta_pp = abs(pass_rate - 0.9300) * 100
    print(f"Deviation from 93.00% baseline: {delta_pp:.2f} pp")
    if delta_pp > 2.0:
        print("HALT: >2pp drift — do NOT post to Notion.")
        sys.exit(2)
    print("OK: within ±2pp band.")

    # Machine-readable tail for the caller to grep.
    print("---RESULT---")
    print(f"p10={p10}")
    print(f"p50={p50}")
    print(f"p90={p90}")
    print(f"pass_rate={pass_rate:.4f}")
    print(f"timeout_pct={timeout_rate * 100:.2f}")


if __name__ == "__main__":
    main()
