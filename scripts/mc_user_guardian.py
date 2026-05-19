"""
One-off: run portfolio_mc with the user's Guardian CSV in the Guardian slot,
canonical Pepperstone Striker/Aegis/NAS in the other slots.

Bypasses the MVD filename gate (user's CSVs aren't canonical exports); every
other step — load_trades, implied_1r, build_daily_panel, run_seed, aggregation
— uses the production functions unchanged.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import portfolio_mc as pmc  # noqa: E402


def run(guardian_csv: Path, guardian_alloc: float, label: str):
    panels = dict(pmc.PEPPERSTONE_PANELS)
    panels["guardian"] = guardian_csv

    allocs = dict(pmc.ALLOCATIONS)
    allocs["guardian"] = guardian_alloc
    panel_strats = tuple(panels.keys())

    trades_by_strat = {s: pmc.load_trades(panels[s]) for s in panel_strats}
    panel_allocs = {s: allocs[s] for s in panel_strats}
    panel, scale_info = pmc.build_daily_panel(trades_by_strat, panel_allocs)
    blocks = pmc.build_week_blocks(panel)

    fallback_count = sum(1 for info in scale_info.values() if info["fell_back"])
    if fallback_count:
        raise SystemExit(f"FAIL: implied_1r fallback fired ({fallback_count}); abort")

    from dd_protection import DD_TRIGGER, DD_SCALE

    seeds_results = [
        pmc.run_seed(seed, pmc.SIMS_PER_SEED, blocks, DD_TRIGGER, DD_SCALE, strats=panel_strats)
        for seed in pmc.SEEDS
    ]
    per_seed = pmc.SIMS_PER_SEED
    pass_r = [r["outcomes"]["pass"] / per_seed for r in seeds_results]
    bd_r   = [r["outcomes"]["bust_daily"] / per_seed for r in seeds_results]
    bs_r   = [r["outcomes"]["bust_static"] / per_seed for r in seeds_results]
    bi_r   = [r["outcomes"].get("bust_inactivity", 0) / per_seed for r in seeds_results]
    hc_r   = [r["outcomes"].get("horizon_cap", r["outcomes"].get("timeout", 0)) / per_seed for r in seeds_results]
    bust_r = [d + s + i for d, s, i in zip(bd_r, bs_r, bi_r)]
    all_days = [d for r in seeds_results for d in r["days_to_pass"]]
    all_dds  = [d for r in seeds_results for d in r["max_dds"]]
    attrib = {s: sum(r["bust_attribution"][s] for r in seeds_results) for s in panel_strats}
    total_busts = sum(attrib.values())

    print(f"=== {label} ===")
    print(f"Guardian CSV: {guardian_csv.name}")
    print(f"Guardian alloc: {guardian_alloc:.2%}")
    print("Scale factors:")
    for s, info in scale_info.items():
        print(f"  {s:<15} 1R=${info['implied_1r']:>8,.2f}  scale={info['scale']:>6.3f}  n={info['n_trades']}")
    print(f"Panel: {panel.index.min().date()} -> {panel.index.max().date()}  "
          f"({len(panel)} bdays, {len(blocks)} week-blocks)")
    print()
    print(f"Pass:         {np.mean(pass_r):>7.2%} (sigma {np.std(pass_r):.2%})")
    print(f"Bust:         {np.mean(bust_r):>7.2%} (sigma {np.std(bust_r):.2%})")
    print(f"  Daily:      {np.mean(bd_r):>7.2%}")
    print(f"  Static:     {np.mean(bs_r):>7.2%}")
    print(f"  Inactivity: {np.mean(bi_r):>7.2%}")
    print(f"Horizon cap:  {np.mean(hc_r):>7.2%}")
    if all_days:
        print(f"Median days to pass: {int(np.median(all_days))}")
    print(f"p50 DD:       {np.percentile(all_dds,50):.2%}")
    print(f"p95 DD:       {np.percentile(all_dds,95):.2%}")
    print(f"p99 DD:       {np.percentile(all_dds,99):.2%}")
    print("Bust attribution:")
    if total_busts:
        for s, n in sorted(attrib.items(), key=lambda kv: kv[1], reverse=True):
            print(f"  {s:<15} {n/total_busts:>5.1%}")
    else:
        print("  (no busts)")
    print()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True, type=Path)
    p.add_argument("--alloc", required=True, type=float)
    p.add_argument("--label", required=True)
    args = p.parse_args()
    run(args.csv, args.alloc, args.label)


if __name__ == "__main__":
    main()
