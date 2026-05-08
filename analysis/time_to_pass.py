"""
time_to_pass — extract days-to-pass distribution from the locked portfolio MC.

Pure measurement: reuses portfolio_mc.run_seed as-is (which already collects
days_to_pass for passing sims and timeout/bust counts). Adds p10/p50/p90
percentiles and right-censored %.

Run from the main pipeline dir so data/tv_exports/*.csv resolves.
    python -m prop_firm_pipeline.tools.time_to_pass

Modes:
    (default)        full-panel time-to-pass distribution + halt gate
    --regime-check   rolling 6-month MC pass-rate check; fires the C2 → C0
                     revert trigger from ADR 2026-05-08-dd-trigger-c2-relock if
                     two consecutive 6-month windows show pass-rate <95%

Quarterly cadence target dates (per the C2 relock ADR):
    2026-08-08, 2026-11-08, 2027-02-08, 2027-05-08 (minimum)
The check is meaningful only as the panel live-extends post-2026-05-08; early
runs against the pre-relock panel produce a baseline reading, not a regime test.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# Allow running as a script from the worktree by adding parent on path.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import portfolio_mc as pmc  # noqa: E402


# ── Regime-check trigger constants ────────────────────────────────────
# Per docs/adr/2026-05-08-dd-trigger-c2-relock.md "Forward revert trigger":
#   "If rolling 6-month MC pass-rate on the live-extended Pepperstone panel
#   falls below 95% for two consecutive 6-month windows after this override,
#   treat as evidence the regime-fragility risk has materialized and
#   re-open the C0/C2 question with the new panel data."
WINDOW_MONTHS = 6
PASS_RATE_FLOOR = 0.95
MIN_BLOCKS_PER_WINDOW = 10  # bootstrap sanity floor


def main_default():
    # Load panel + blocks via the MC's own loader (locked 2026-04-17 config).
    trades_by_strat, panel, blocks, scale_info, panel_strats = pmc._load_all(pmc.ALLOCATIONS)

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
    print(f"Sims: {total:,} ({pmc.SIMS_PER_SEED:,} x {len(pmc.SEEDS)} seeds), "
          f"horizon {pmc.HORIZON_DAYS} days")
    print(f"Pass:             {pass_rate:>7.2%}  (baseline 98.09% under C2)")
    print(f"Bust:             {bust_rate:>7.2%}")
    print(f"Right-censored:   {timeout_rate:>7.2%}  (timeout >= 150d)")
    print()
    print("Days-to-pass (passing sims only):")
    print(f"  p10:  {p10}")
    print(f"  p50:  {p50}")
    print(f"  p90:  {p90}")
    print()

    # Halt-condition check (baseline updated 2026-05-08 to C2 anchor 98.09%)
    delta_pp = abs(pass_rate - 0.9809) * 100
    print(f"Deviation from 98.09% C2 baseline: {delta_pp:.2f} pp")
    if delta_pp > 2.0:
        print("HALT: >2pp drift — do NOT post to Notion.")
        sys.exit(2)
    print("OK: within +/-2pp band.")

    # Machine-readable tail for the caller to grep.
    print("---RESULT---")
    print(f"p10={p10}")
    print(f"p50={p50}")
    print(f"p90={p90}")
    print(f"pass_rate={pass_rate:.4f}")
    print(f"timeout_pct={timeout_rate * 100:.2f}")


# ── Regime check ─────────────────────────────────────────────────────────

def _run_window_mc(panel_slice: pd.DataFrame, label: str) -> dict | None:
    """Build blocks from a date-sliced panel and run the standard 3-seed MC.

    Returns the aggregated result dict or None if the slice has too few
    blocks to bootstrap meaningfully.
    """
    blocks = pmc.build_week_blocks(panel_slice)
    if len(blocks) < MIN_BLOCKS_PER_WINDOW:
        print(f"  [{label}] only {len(blocks)} week-blocks "
              f"(need >= {MIN_BLOCKS_PER_WINDOW}); skipping.")
        return None

    seeds_results = [
        pmc.run_seed(seed, pmc.SIMS_PER_SEED, blocks,
                     pmc.DD_TRIGGER, pmc.DD_SCALE, pmc.HORIZON_DAYS)
        for seed in pmc.SEEDS
    ]
    total = pmc.SIMS_PER_SEED * len(pmc.SEEDS)
    passes = sum(r["outcomes"]["pass"] for r in seeds_results)
    busts = sum(r["outcomes"]["bust_daily"] + r["outcomes"]["bust_static"]
                for r in seeds_results)
    return {
        "n_blocks": len(blocks),
        "n_bdays": len(panel_slice),
        "start": panel_slice.index.min().date(),
        "end":   panel_slice.index.max().date(),
        "pass_rate": passes / total,
        "bust_rate": busts / total,
    }


def regime_check():
    """Slice the live-extended panel into rolling 6-month windows and report
    pass-rate per window. Fires the C2 -> C0 revert trigger if the two most
    recent windows both show pass-rate < 95%."""
    _, panel, _, _, _ = pmc._load_all(pmc.ALLOCATIONS)

    print("=" * 72)
    print("REGIME-CHECK MODE — C2 -> C0 revert trigger")
    print("=" * 72)
    print(f"Reference: docs/adr/2026-05-08-dd-trigger-c2-relock.md")
    print(f"Trigger:   2 consecutive 6-month windows with pass-rate "
          f"< {PASS_RATE_FLOOR:.0%}")
    print()
    print(f"Panel: {panel.index.min().date()} -> {panel.index.max().date()}  "
          f"({len(panel)} bdays)")
    print(f"DD config: trigger={pmc.DD_TRIGGER:.3f}, scale={pmc.DD_SCALE:.2f}")
    print()

    # Construct the two trailing 6-month windows.
    end = panel.index.max()
    mid = end - pd.DateOffset(months=WINDOW_MONTHS)
    start = end - pd.DateOffset(months=2 * WINDOW_MONTHS)

    recent = panel.loc[(panel.index > mid) & (panel.index <= end)]
    prior  = panel.loc[(panel.index > start) & (panel.index <= mid)]

    print(f"Recent window: {mid.date()} -> {end.date()} "
          f"({len(recent)} bdays)")
    print(f"Prior  window: {start.date()} -> {mid.date()} "
          f"({len(prior)} bdays)")
    print()

    print("Running 6-month-window MC (3 seeds x "
          f"{pmc.SIMS_PER_SEED:,} sims, horizon {pmc.HORIZON_DAYS}d)...")
    recent_r = _run_window_mc(recent, "recent")
    prior_r  = _run_window_mc(prior,  "prior")
    print()

    print("Window results:")
    for label, r in (("recent", recent_r), ("prior", prior_r)):
        if r is None:
            print(f"  {label:<7}: SKIPPED (insufficient blocks)")
            continue
        flag = " <" if r["pass_rate"] < PASS_RATE_FLOOR else ""
        print(f"  {label:<7}: {r['start']} -> {r['end']}  "
              f"pass={r['pass_rate']:.2%}{flag}  "
              f"bust={r['bust_rate']:.2%}  "
              f"({r['n_blocks']} blocks, {r['n_bdays']} bdays)")
    print()

    # Trigger logic
    available = [r for r in (recent_r, prior_r) if r is not None]
    if len(available) < 2:
        print("VERDICT: INDETERMINATE — at least one window had insufficient")
        print("blocks. Re-run after the panel grows (live-extension).")
        sys.exit(0)

    both_below = all(r["pass_rate"] < PASS_RATE_FLOOR for r in available)
    if both_below:
        print("=" * 72)
        print("REVERT TRIGGER FIRED.")
        print("=" * 72)
        print(f"Both 6-month windows show pass-rate below {PASS_RATE_FLOOR:.0%}.")
        print("Per ADR 2026-05-08-dd-trigger-c2-relock, re-open the C0/C2")
        print("question with the new panel data and consider reverting")
        print("DD_TRIGGER 0.015 -> 0.010.")
        print()
        print("Next steps:")
        print("  1. Confirm panel cardinality has grown materially since the")
        print("     2026-05-08 relock (otherwise this is the same regime data")
        print("     re-read).")
        print("  2. Re-run portfolio_mc on the full live-extended panel and")
        print("     compare to the C2 anchor 98.09 / 0.36 / 4.73.")
        print("  3. Author docs/briefs/Q-DDP-2/ if the live data confirms the")
        print("     regime-fragility risk materialized.")
        sys.exit(3)

    print("VERDICT: PASS — trigger conditions not met.")
    print(f"At least one window is at or above the {PASS_RATE_FLOOR:.0%} floor.")


def main():
    p = argparse.ArgumentParser(prog="time_to_pass",
                                description=("Time-to-pass distribution + "
                                             "C2 revert trigger check."))
    p.add_argument("--regime-check", action="store_true",
                   help="Run the rolling 6-month MC pass-rate regime check "
                        "(quarterly cadence per ADR 2026-05-08-dd-trigger-"
                        "c2-relock).")
    args = p.parse_args()

    if args.regime_check:
        regime_check()
    else:
        main_default()


if __name__ == "__main__":
    main()
