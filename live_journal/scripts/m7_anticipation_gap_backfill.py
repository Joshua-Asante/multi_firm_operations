#!/usr/bin/env python3
"""
m7_anticipation_gap_backfill.py — Route A quantification for methodology
lesson M-7 (alert() vs alertcondition() audit gap).

Route A premise: the M-7 lesson is currently CANDIDATE (~$103 single-incident
anchor on the 2026-05-07 Guardian late fill). Promotion to PROMOTED requires
either (a) a single-incident dollar cost ≥ $3K, or (b) three independent
firings across separate review windows. This script implements path (a) via
backfill: sum the entry slippage cost across all live fills during the
period when one or more strategies were running with the alertcondition()-
only anticipation-alert bug. If the cumulative cost across the portfolio
exceeds $3K, the lesson promotes on the original anchor with backfill data
attached.

Bug exposure timeline (per memory + 2026-05-07 patch session):
  - Aegis v4.3:    locked 2026-04-22, patched 2026-04-27 → 5 days bugged
  - Guardian v5.5: locked 2026-04-23, patched 2026-05-07 → 14 days bugged
  - DJ30 v4.5:     locked 2026-05-05, patched 2026-05-07 → 2 days bugged
  - NAS100 v1.0:   locked 2026-05-05, patched 2026-05-07 → 2 days bugged

The window argument (--start / --end) defaults to the union exposure period
2026-04-22 → 2026-05-07 (i.e. the day Aegis was locked through the day all
four were patched). Aegis fills before its 04-27 patch are kept in scope;
Aegis fills after are control-sample for the natural experiment subset.

This script complements (does NOT replace) journal_review.py. It reuses
journal_review's loaders and pairing logic — both scripts must live in the
same directory.

Entry slippage formula (the M-7 cost proxy):
  slippage_price = actual_fill_price - signal_bar_close      [for longs]
  slippage_usd   = slippage_price × lots × contract_value_usd

Where contract_value_usd is strategy-specific:
  Guardian (XAUUSD):  $100/$1.00 price move per lot
  DJ30 (US30):        $10/point per lot
  NAS100 (NDX):       $10/point per lot
  Aegis (USDJPY):     forex pip math — pip_value_usd = lot_units × 0.01 / fill_price
                      (uses fill_price as approximation for current_price)

Usage:
  python m7_anticipation_gap_backfill.py \\
    --dxtrade <fills.csv> \\
    --backtest guardian:<csv> aegis:<csv> [striker_dj30:<csv>] [striker_nas:<csv>] \\
    [--start 2026-04-22] [--end 2026-05-07] \\
    [--natural-experiment]

Output:
  - Per-strategy slippage table (n trades, total slippage, mean slippage)
  - Portfolio total entry slippage in USD
  - M-7 promotion verdict (PROMOTE if ≥ $3K, else KEEP CANDIDATE)
  - Optional natural experiment: Aegis pre-patch (bugged) vs post-patch (clean)
    if both buckets have n ≥ 3

Limitations explicitly out of scope:
  - This script measures ENTRY slippage only. Exit slippage (BE/trail/TP
    drift, late stop placement) is a separate failure mode tracked by
    journal_review's edge-captured ratio, not here.
  - Slippage is the gross proxy for the anticipation gap, not a clean
    isolation. Some baseline slippage exists even with anticipation alerts
    delivering correctly (broker latency, manual entry time). The natural
    experiment subset on Aegis controls for this if sample sizes permit.
  - Pyramid-add fills are excluded (only primary entries count for M-7).
  - Short fills are excluded (all four locked strategies are long-only;
    short fills indicate off-spec activity outside M-7's scope).
"""

from __future__ import annotations
import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd  # type: ignore

# Reuse journal_review's loaders and pairing — sibling script.
try:
    from journal_review import (
        Fill,
        Signal,
        Pairing,
        load_dxtrade,
        load_backtest,
        filter_to_window,
        pair_signals_to_fills,
        parse_backtest_args,
        STRATEGIES,
    )
except ImportError as e:
    sys.stderr.write(
        "ERROR: cannot import from journal_review.py.\n"
        "This script must live in the same directory as journal_review.py.\n"
        f"Underlying ImportError: {e}\n"
    )
    sys.exit(2)


# ---------------------------------------------------------------------------
# Strategy contract value for entry-slippage USD conversion
# ---------------------------------------------------------------------------

CONTRACT_VALUE_USD_PER_PRICE_UNIT = {
    # USD per 1.0 price move per lot (matches Pine indicator inputs)
    "guardian":     100.0,   # XAUUSD: $100 / $1.00 / lot (1 lot = 100 oz)
    "striker_dj30": 10.0,    # US30:   $10 / point / lot (DXTrade locked)
    "striker_nas":  10.0,    # NDX:    $10 / point / lot (DXTrade locked)
    # Aegis is forex — handled separately via pip_value_usd math
}

# Aegis lot size in base-currency units (matches Pine indicator's lotSizeUnits)
AEGIS_LOT_UNITS = 100_000

# Patch dates per strategy (anticipation-alert patch ship dates)
PATCH_DATES = {
    "aegis":        date(2026, 4, 27),
    "guardian":     date(2026, 5, 7),
    "striker_dj30": date(2026, 5, 7),
    "striker_nas":  date(2026, 5, 7),
}

# Default window: union exposure period
DEFAULT_START = date(2026, 4, 22)
DEFAULT_END   = date(2026, 5, 7)

# M-7 promotion threshold (per brief-authoring lesson_capture template)
PROMOTION_THRESHOLD_USD = 3000.0


# ---------------------------------------------------------------------------
# Slippage computation
# ---------------------------------------------------------------------------

def compute_entry_slippage_usd(
    pairing: Pairing,
    strategy: str,
) -> Optional[float]:
    """
    Compute entry-slippage USD cost for a single pairing.

    Returns None if pairing is not eligible (skipped, off-spec, short, etc.).
    Returns float (signed) otherwise — positive = cost (bought higher than
    spec on a long), negative = unexpected gain (bought lower than spec).

    For pyramid strategies, only the FIRST fill (primary entry) is used.
    Pyramid legs are excluded — anticipation alerts only apply to primary
    entries.
    """
    # Skip non-execution pairings
    if pairing.classification not in ("TAKEN-ON-SPEC", "TAKEN-DISCRETIONARY"):
        return None

    if not pairing.fills:
        return None
    if pairing.signal is None:
        return None

    # Long-only check (all four locked strategies are long-only)
    primary_fill = pairing.fills[0]
    if primary_fill.side.lower() != "long":
        return None

    actual_price = primary_fill.open_price
    signal_price = pairing.signal.entry_price
    lots         = primary_fill.quantity

    # Defensive: skip degenerate fills
    if actual_price <= 0 or signal_price <= 0 or lots <= 0:
        return None

    slippage_price = actual_price - signal_price

    # Convert to USD
    if strategy in CONTRACT_VALUE_USD_PER_PRICE_UNIT:
        cv = CONTRACT_VALUE_USD_PER_PRICE_UNIT[strategy]
        return slippage_price * lots * cv

    if strategy == "aegis":
        # Forex: pip_value_usd ≈ lot_units × 0.01 / current_price
        # We use actual fill price as proxy for current price at entry.
        # slippage_price is in JPY (USDJPY quote convention).
        # Convert to USD: (slippage in JPY) × (lots × 100_000 base-units) / fill_price_jpy
        usd_value_per_jpy_movement = (lots * AEGIS_LOT_UNITS) / actual_price
        return slippage_price * usd_value_per_jpy_movement

    sys.stderr.write(f"WARN: unknown strategy '{strategy}' — skipping pairing\n")
    return None


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate_slippage(
    pairings: list[Pairing],
) -> tuple[dict[str, dict], float, int]:
    """
    Aggregate per-strategy slippage from a list of pairings.

    Returns:
        per_strategy: { strategy_key: {n, total_usd, mean_usd, fills: [(date, slippage)]} }
        total_usd: float
        excluded_count: int (pairings that failed eligibility for any reason)
    """
    per_strategy: dict[str, dict] = {}
    total_usd = 0.0
    excluded = 0

    for p in pairings:
        if p.signal is None:
            excluded += 1
            continue

        strat = p.signal.strategy
        slip = compute_entry_slippage_usd(p, strat)
        if slip is None:
            excluded += 1
            continue

        agg = per_strategy.setdefault(strat, {"n": 0, "total_usd": 0.0, "fills": []})
        agg["n"] += 1
        agg["total_usd"] += slip
        agg["fills"].append((p.signal.entry_time, slip, p.fills[0].open_price, p.signal.entry_price, p.fills[0].quantity))

        total_usd += slip

    for strat in per_strategy:
        n = per_strategy[strat]["n"]
        per_strategy[strat]["mean_usd"] = per_strategy[strat]["total_usd"] / n if n else 0.0

    return per_strategy, total_usd, excluded


# ---------------------------------------------------------------------------
# Natural experiment (Aegis only — has both pre-patch and post-patch data)
# ---------------------------------------------------------------------------

def aegis_natural_experiment(pairings: list[Pairing]) -> Optional[str]:
    """
    Compare Aegis slippage pre-patch (bugged) vs post-patch (clean).

    Patch date: 2026-04-27. Returns formatted comparison string, or None if
    either bucket has fewer than 3 fills (insufficient sample for inference).
    """
    patch = PATCH_DATES["aegis"]
    pre, post = [], []

    for p in pairings:
        if p.signal is None or p.signal.strategy != "aegis":
            continue
        slip = compute_entry_slippage_usd(p, "aegis")
        if slip is None:
            continue
        if p.signal.entry_time.date() < patch:
            pre.append(slip)
        else:
            post.append(slip)

    if len(pre) < 3 or len(post) < 3:
        return (
            f"  Aegis natural experiment: SKIPPED "
            f"(pre-patch n={len(pre)}, post-patch n={len(post)}; need ≥3 each)\n"
            f"  Aegis fills only Mon/Tue/Wed; the 04-22 → 04-26 pre-patch window\n"
            f"  contains at most 2 trading days — underpowered by design."
        )

    pre_mean = sum(pre) / len(pre)
    post_mean = sum(post) / len(post)
    delta = pre_mean - post_mean

    return (
        f"  Aegis natural experiment (pre-patch vs post-patch):\n"
        f"    Pre-patch  (n={len(pre):3d}): total ${sum(pre):>10,.2f}  mean ${pre_mean:>8,.2f}/trade\n"
        f"    Post-patch (n={len(post):3d}): total ${sum(post):>10,.2f}  mean ${post_mean:>8,.2f}/trade\n"
        f"    Delta (per-trade attribution to anticipation gap): ${delta:>+8,.2f}\n"
        f"    NOTE: small samples; treat as directional signal not point estimate."
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def format_report(
    per_strategy: dict[str, dict],
    total_usd: float,
    excluded: int,
    n_pairings: int,
    window_start: date,
    window_end: date,
    aegis_experiment: Optional[str] = None,
) -> str:
    lines = []
    lines.append("=" * 72)
    lines.append("M-7 ROUTE A BACKFILL — ANTICIPATION GAP ENTRY SLIPPAGE")
    lines.append("=" * 72)
    lines.append(f"Window:                    {window_start} → {window_end}")
    lines.append(f"Pairings examined:         {n_pairings}")
    lines.append(f"Pairings included:         {sum(s['n'] for s in per_strategy.values())}")
    lines.append(f"Pairings excluded:         {excluded}")
    lines.append("                           (skipped/off-spec/pyramid-leg/short/degenerate)")
    lines.append("")
    lines.append("PER-STRATEGY ENTRY SLIPPAGE")
    lines.append("-" * 72)
    lines.append(f"  {'Strategy':<16} {'Patched':<12} {'n':>4} {'Total $':>14} {'Mean $/trade':>14}")
    lines.append("-" * 72)

    # Order: Guardian, DJ30, NAS100, Aegis (matches portfolio convention)
    order = ["guardian", "striker_dj30", "striker_nas", "aegis"]
    for strat_key in order:
        if strat_key not in per_strategy:
            continue
        s = per_strategy[strat_key]
        label = STRATEGIES[strat_key]["label"]
        patch_date = PATCH_DATES.get(strat_key, "?")
        lines.append(
            f"  {label:<16} {str(patch_date):<12} {s['n']:>4} "
            f"${s['total_usd']:>12,.2f} ${s['mean_usd']:>12,.2f}"
        )

    lines.append("-" * 72)
    lines.append(f"  {'PORTFOLIO TOTAL':<33} ${total_usd:>12,.2f}")
    lines.append("")

    # Promotion verdict
    lines.append("M-7 PROMOTION VERDICT")
    lines.append("-" * 72)
    lines.append(f"Threshold (single-incident promotion):  ${PROMOTION_THRESHOLD_USD:,.2f}")
    lines.append(f"Measured (this window):                 ${total_usd:,.2f}")
    if total_usd >= PROMOTION_THRESHOLD_USD:
        lines.append("")
        lines.append("  >>> PROMOTE M-7 to PROMOTED status. <<<")
        lines.append("  Update the lesson capture file:")
        lines.append("    - Status: CANDIDATE → PROMOTED")
        lines.append(f"    - Promoted: {date.today()}")
        lines.append("    - Counterfactual: replace placeholder with this window's total.")
        lines.append("    - Versioning notes: append promotion date + this window's total.")
    else:
        lines.append("")
        lines.append("  >>> KEEP M-7 as CANDIDATE. <<<")
        gap = PROMOTION_THRESHOLD_USD - total_usd
        lines.append(f"  Below threshold by ${gap:,.2f}. Lesson stays observational.")
        lines.append("  Route B (third firing) remains available — pre-lock audit checklist")
        lines.append("  on indicator #5 is the next promotion opportunity.")

    if aegis_experiment:
        lines.append("")
        lines.append("NATURAL EXPERIMENT (control)")
        lines.append("-" * 72)
        lines.append(aegis_experiment)

    lines.append("")
    lines.append("CAVEATS")
    lines.append("-" * 72)
    lines.append("- Entry slippage only. Exit slippage tracked separately by journal_review.")
    lines.append("- Slippage is the gross proxy; baseline broker/manual latency contributes.")
    lines.append("- DJ30 v4.5 + NAS100 v1.0 had only ~2 days bugged exposure (locked 05-05);")
    lines.append("  expect small n on those rows.")
    lines.append("- Pyramid legs excluded (M-7 scope = primary entries only).")
    lines.append("=" * 72)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="M-7 Route A backfill: entry-slippage cost across the anticipation-gap exposure window.",
    )
    p.add_argument("--dxtrade", required=True, help="DXTrade fills CSV path")
    p.add_argument(
        "--backtest", nargs="+", required=True,
        help="Per-strategy backtest CSVs as <strategy>:<path>. "
             "Strategies: guardian, striker_dj30, striker_nas, aegis."
    )
    p.add_argument("--start", default=str(DEFAULT_START), help=f"Window start YYYY-MM-DD (default {DEFAULT_START})")
    p.add_argument("--end",   default=str(DEFAULT_END),   help=f"Window end YYYY-MM-DD (default {DEFAULT_END})")
    p.add_argument("--natural-experiment", action="store_true",
                   help="Include Aegis pre-patch vs post-patch comparison (n≥3 required each side)")
    p.add_argument("--per-trade-detail", action="store_true",
                   help="Print every contributing fill (date, signal_price, fill_price, lots, slippage_$)")
    args = p.parse_args(argv)

    try:
        window_start = date.fromisoformat(args.start)
        window_end   = date.fromisoformat(args.end)
    except ValueError as e:
        sys.stderr.write(f"ERROR: bad date format — {e}\n")
        return 2

    # Load fills
    fills = load_dxtrade(args.dxtrade)
    fills = filter_to_window(fills, window_start, window_end, "open_time")

    # Load backtest signals
    backtest_paths = parse_backtest_args(args.backtest)
    signals: list[Signal] = []
    for strat, path in backtest_paths.items():
        sigs = load_backtest(path, strat)
        signals.extend(filter_to_window(sigs, window_start, window_end, "entry_time"))

    if not signals:
        sys.stderr.write("ERROR: no backtest signals in window after filter — check --start/--end and CSV coverage.\n")
        return 1

    # Pair
    pairings = pair_signals_to_fills(signals, fills)

    # Aggregate
    per_strategy, total_usd, excluded = aggregate_slippage(pairings)

    # Natural experiment
    nat_exp = aegis_natural_experiment(pairings) if args.natural_experiment else None

    # Render
    print(format_report(per_strategy, total_usd, excluded, len(pairings),
                        window_start, window_end, nat_exp))

    # Per-trade detail
    if args.per_trade_detail:
        print("")
        print("PER-TRADE DETAIL")
        print("-" * 72)
        print(f"  {'Strategy':<14} {'Entry Time':<20} {'Signal $':>10} {'Fill $':>10} "
              f"{'Lots':>6} {'Slippage $':>12}")
        print("-" * 72)
        for strat_key in ["guardian", "striker_dj30", "striker_nas", "aegis"]:
            if strat_key not in per_strategy:
                continue
            for entry_time, slip, fill_p, sig_p, lots in sorted(per_strategy[strat_key]["fills"]):
                print(f"  {STRATEGIES[strat_key]['label']:<14} "
                      f"{str(entry_time):<20} "
                      f"{sig_p:>10.4f} {fill_p:>10.4f} "
                      f"{lots:>6.2f} ${slip:>+10,.2f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
