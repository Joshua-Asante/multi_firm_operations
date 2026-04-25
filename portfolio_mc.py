"""
portfolio_mc — challenge-outcome simulator (single-tier)
========================================================
Answers one question: given the locked strategies and DD-protection config,
what is the challenge pass/bust distribution?

Not in scope: per-strategy diagnostics, allocation tuning, live integration.
See the FINAL decision page: https://www.notion.so/346dc0b53c11816085bbf2292be934cc

Invocation:
    python -m prop_firm_pipeline.portfolio_mc                   # default run
    python -m prop_firm_pipeline.portfolio_mc --historical      # deterministic
    python -m prop_firm_pipeline.portfolio_mc --sensitivity     # DD-trigger grid
    python -m prop_firm_pipeline.portfolio_mc --dd-trigger 0.01 --dd-scale 0.40
    python -m prop_firm_pipeline.portfolio_mc --no-protection
    python -m prop_firm_pipeline.portfolio_mc --guardian-risk 0.0025   # what-if at reduced Guardian risk
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd

try:
    from .dd_protection import DD_TRIGGER, DD_SCALE
    from .lib.mvd import assert_min_rows, assert_window, assert_no_fallback
except ImportError:
    from dd_protection import DD_TRIGGER, DD_SCALE
    from lib.mvd import assert_min_rows, assert_window, assert_no_fallback

STARTING_EQUITY = 200_000
PROFIT_TARGET = 210_000
DAILY_LOSS_PCT = -0.05
STATIC_DD_PCT = -0.05
MIN_TRADING_DAYS = 5
HORIZON_DAYS = 150
SIMS_PER_SEED = 10_000
SEEDS = (42, 123, 2026)

ALLOCATIONS: Dict[str, float] = {
    "guardian": 0.0034,
    "striker":  0.0100,
    "aegis":    0.0150,
}
STRATS = tuple(ALLOCATIONS.keys())

CSV_DIR = Path(__file__).parent / "data" / "tv_exports"


# ── Data pipeline ─────────────────────────────────────────────────────────

def load_trades(path: Path) -> pd.DataFrame:
    """Load TV List-of-Trades CSV. Return DataFrame with ['exit_date', 'pnl']
    for exit rows only (P&L is carried identically on entry+exit; we use exit
    for timing)."""
    df = pd.read_csv(path, encoding="utf-8-sig")
    # MVD cardinality — catches OANDA short-fetch class (audit instance #2).
    # Floor at 100 raw rows: panels are entry+exit pairs, so 100 ≈ 50 trades,
    # well below any plausible 4yr canonical panel.
    assert_min_rows(len(df), 100, label=f"MC input panel {path.name}")
    exits = df[df["Type"].astype(str).str.startswith("Exit")].copy()
    exits["exit_date"] = pd.to_datetime(exits["Date and time"]).dt.normalize()
    exits = exits.rename(columns={"Net P&L USD": "pnl"})
    out = exits[["exit_date", "pnl"]].sort_values("exit_date").reset_index(drop=True)
    if not out.empty:
        # MVD window — catches "4yr panel actually 14mo" class (audit instance #8).
        assert_window(
            out["exit_date"].iloc[0].to_pydatetime(),
            out["exit_date"].iloc[-1].to_pydatetime(),
            expected_min_days=4 * 365,
            label=f"MC input panel {path.name}",
            tolerance_days=60,
        )
    return out


def implied_1r(pnl: pd.Series, strategy: str,
               account: float = STARTING_EQUITY) -> Tuple[float, bool]:
    """Implied 1R in dollars. Returns (r1, fell_back).

    Guardian: median loss (pure trend-rider, no BE) — by design, fell_back=False.
    Striker/Aegis: mean of |losses| > 1% of account (full-stop cohort).
    Falls back to median if fewer than 5 full stops — fell_back=True.

    The fallback path is the silent-trigger case named in audit instance #1
    (user memory `portfolio_mc_1r_fallback_trap.md`). It can swing MC by ~10pp.
    Callers must `assert_no_fallback` on the aggregated count for any
    canonical run.
    """
    abs_losses = pnl[pnl < 0].abs()
    if strategy == "guardian":
        return float(abs_losses.median()), False
    full_stops = abs_losses[abs_losses > 0.01 * account]
    if len(full_stops) < 5:
        return float(abs_losses.median()), True
    return float(full_stops.mean()), False


def build_daily_panel(trades_by_strat: Dict[str, pd.DataFrame],
                      allocations: Dict[str, float]) -> Tuple[pd.DataFrame, Dict[str, dict]]:
    """Scale each strategy's realized P&L so 1R maps to allocation × $200K, then
    aggregate to a business-day panel."""
    scale_info: Dict[str, dict] = {}
    series = []
    for strat, trades in trades_by_strat.items():
        r1, fell_back = implied_1r(trades["pnl"], strat)
        target_dollars = allocations[strat] * STARTING_EQUITY
        scale = target_dollars / r1 if r1 > 0 else 1.0
        scale_info[strat] = {
            "implied_1r": r1,
            "scale": scale,
            "n_trades": len(trades),
            "fell_back": fell_back,
        }
        s = trades.groupby("exit_date")["pnl"].sum() * scale
        s.name = strat
        series.append(s)
    panel = pd.concat(series, axis=1, sort=True).fillna(0.0)
    bdays = pd.bdate_range(panel.index.min(), panel.index.max())
    return panel.reindex(bdays).fillna(0.0), scale_info


def build_week_blocks(panel: pd.DataFrame) -> np.ndarray:
    """Mon-anchored non-overlapping 5-day blocks. Returns shape (n_blocks, 5, n_strats)."""
    vals = panel.values  # (n_days, n_strats)
    blocks = []
    for i, d in enumerate(panel.index):
        if d.weekday() == 0 and i + 5 <= len(panel):
            blocks.append(vals[i:i + 5])
    return np.array(blocks)


# ── Simulation ────────────────────────────────────────────────────────────

def _simulate_path(path: np.ndarray, dd_trigger: float, dd_scale: float,
                   horizon: int) -> Tuple[str, int, float, int | None]:
    """Run one deterministic sim over a (horizon, n_strats) path.
    Returns (outcome, day_terminated, max_dd, culprit_strat_idx)."""
    eq = peak = float(STARTING_EQUITY)
    trade_days = 0
    max_dd = 0.0

    for day in range(horizon):
        dd_from_peak = (eq - peak) / peak if peak > 0 else 0.0
        scale = dd_scale if dd_from_peak <= -dd_trigger else 1.0
        strat_pnls = path[day] * scale
        pnl = float(strat_pnls.sum())
        eq_new = eq + pnl

        if pnl / STARTING_EQUITY <= DAILY_LOSS_PCT:
            return "bust_daily", day + 1, max_dd, int(np.argmin(strat_pnls))
        if (eq_new - STARTING_EQUITY) / STARTING_EQUITY <= STATIC_DD_PCT:
            return "bust_static", day + 1, max_dd, int(np.argmin(strat_pnls))

        eq = eq_new
        if eq > peak:
            peak = eq
        dd_now = (peak - eq) / peak if peak > 0 else 0.0
        if dd_now > max_dd:
            max_dd = dd_now
        if pnl != 0:
            trade_days += 1

        if eq >= PROFIT_TARGET and trade_days >= MIN_TRADING_DAYS:
            return "pass", day + 1, max_dd, None

    return "timeout", horizon, max_dd, None


def run_seed(seed: int, n_sims: int, blocks: np.ndarray,
             dd_trigger: float, dd_scale: float, horizon: int = HORIZON_DAYS) -> dict:
    """Run n_sims bootstrap simulations for one seed."""
    rng = np.random.default_rng(seed)
    n_blocks = len(blocks)
    blocks_per_sim = (horizon + 4) // 5

    outcomes = {"pass": 0, "bust_daily": 0, "bust_static": 0, "timeout": 0}
    days_to_pass: list[int] = []
    max_dds: list[float] = []
    bust_attrib = {s: 0 for s in STRATS}

    for _ in range(n_sims):
        idx = rng.integers(0, n_blocks, blocks_per_sim)
        path = np.concatenate([blocks[i] for i in idx])[:horizon]

        outcome, day, max_dd, culprit = _simulate_path(path, dd_trigger, dd_scale, horizon)
        outcomes[outcome] += 1
        max_dds.append(max_dd)
        if outcome == "pass":
            days_to_pass.append(day)
        elif outcome in ("bust_daily", "bust_static") and culprit is not None:
            bust_attrib[STRATS[culprit]] += 1

    return {
        "outcomes": outcomes,
        "days_to_pass": days_to_pass,
        "max_dds": max_dds,
        "bust_attribution": bust_attrib,
    }


# ── Reporting ─────────────────────────────────────────────────────────────

def _fmt_config(dd_trigger: float, dd_scale: float, no_protection: bool) -> str:
    if no_protection:
        return "no protection (--no-protection)"
    return f"DD {dd_trigger:.1%} / {dd_scale}× (single-tier)"


def _fmt_alloc(allocs: Dict[str, float]) -> str:
    return (f"G {allocs['guardian']:.2%} / "
            f"S {allocs['striker']:.2%} / "
            f"A {allocs['aegis']:.2%}")


def report_default(seeds_results: list, dd_trigger: float, dd_scale: float,
                   allocs: Dict[str, float], no_protection: bool):
    """Print the default MC output block."""
    per_seed = len(seeds_results[0]["max_dds"])
    pass_r = [r["outcomes"]["pass"] / per_seed for r in seeds_results]
    bd_r   = [r["outcomes"]["bust_daily"] / per_seed for r in seeds_results]
    bs_r   = [r["outcomes"]["bust_static"] / per_seed for r in seeds_results]
    to_r   = [r["outcomes"]["timeout"] / per_seed for r in seeds_results]
    bust_r = [d + s for d, s in zip(bd_r, bs_r)]

    all_days = [d for r in seeds_results for d in r["days_to_pass"]]
    all_dds  = [d for r in seeds_results for d in r["max_dds"]]

    attrib = {s: sum(r["bust_attribution"][s] for r in seeds_results) for s in STRATS}
    total_busts = sum(attrib.values())

    print("=== Portfolio MC ===")
    print(f"Config: {_fmt_config(dd_trigger, dd_scale, no_protection)}")
    print(f"Allocations: {_fmt_alloc(allocs)}")
    print(f"Sims: {per_seed:,} × {len(seeds_results)} seeds, horizon {HORIZON_DAYS} days")
    print()
    print(f"Pass:         {np.mean(pass_r):>6.2%} (sigma {np.std(pass_r):.2%})")
    print(f"Bust:         {np.mean(bust_r):>6.2%} (sigma {np.std(bust_r):.2%})")
    print(f"  Daily:      {np.mean(bd_r):>6.2%}")
    print(f"  Static:     {np.mean(bs_r):>6.2%}")
    print(f"Timeout:      {np.mean(to_r):>6.2%}")
    if all_days:
        print(f"Median days to pass: {int(np.median(all_days))}")
    print(f"p50 DD:       {np.percentile(all_dds, 50):.2%}")
    print(f"p95 DD:       {np.percentile(all_dds, 95):.2%}")
    print(f"p99 DD:       {np.percentile(all_dds, 99):.2%}")
    print()
    print("Bust attribution:")
    if total_busts > 0:
        for s in ("aegis", "striker", "guardian"):
            pct = attrib[s] / total_busts
            print(f"  {s.capitalize():<10} {pct:>5.1%}")
    else:
        print("  (no busts)")


# ── CLI modes ─────────────────────────────────────────────────────────────

def _load_all(allocs: Dict[str, float]):
    trades_by_strat = {s: load_trades(CSV_DIR / f"{s}.csv") for s in STRATS}
    panel, scale_info = build_daily_panel(trades_by_strat, allocs)
    blocks = build_week_blocks(panel)
    return trades_by_strat, panel, blocks, scale_info


def mode_default(dd_trigger: float, dd_scale: float, no_protection: bool,
                 allocs: Dict[str, float], verbose: bool = True):
    trades_by_strat, panel, blocks, scale_info = _load_all(allocs)

    # MVD contract — catches the implied_1r silent-fallback case
    # (audit instance #1). Guardian's median path is by design and reports
    # fell_back=False. Striker/Aegis fall back to median when full-stop
    # cohort is under-populated (n<5); for any canonical run this must be 0.
    fallback_count = sum(1 for info in scale_info.values() if info["fell_back"])
    assert_no_fallback(
        fallback_count,
        label="portfolio_mc implied_1r (Striker/Aegis full-stop cohort)",
    )

    if verbose:
        print("Scale factors:")
        for s, info in scale_info.items():
            tag = "  [fallback: median]" if info["fell_back"] else ""
            print(f"  {s:<9} 1R=${info['implied_1r']:>7,.2f}  scale={info['scale']:>6.3f}  n={info['n_trades']}{tag}")
        print(f"Historical panel: {panel.index.min().date()} → {panel.index.max().date()}  "
              f"({len(panel)} bdays, {len(blocks)} week-blocks)")
        print()

    effective_trigger = 10.0 if no_protection else dd_trigger
    seeds_results = [run_seed(seed, SIMS_PER_SEED, blocks, effective_trigger, dd_scale)
                     for seed in SEEDS]
    report_default(seeds_results, dd_trigger, dd_scale, allocs, no_protection)


def mode_historical(dd_trigger: float, dd_scale: float, no_protection: bool,
                    allocs: Dict[str, float]):
    _, panel, _, scale_info = _load_all(allocs)
    path = panel.values

    effective_trigger = 10.0 if no_protection else dd_trigger
    outcome, day, max_dd, culprit = _simulate_path(path, effective_trigger, dd_scale, len(path))

    # Count protection trigger days across the walk
    eq = peak = float(STARTING_EQUITY)
    trigger_days = 0
    for i in range(min(day, len(path))):
        dd_from_peak = (eq - peak) / peak if peak > 0 else 0.0
        if not no_protection and dd_from_peak <= -dd_trigger:
            trigger_days += 1
            scale = dd_scale
        else:
            scale = 1.0
        pnl = float((path[i] * scale).sum())
        eq = eq + pnl
        if eq > peak:
            peak = eq
        if outcome == "pass" and eq >= PROFIT_TARGET:
            break

    print("=== Portfolio MC — Historical (deterministic) ===")
    print(f"Config: {_fmt_config(dd_trigger, dd_scale, no_protection)}")
    print(f"Allocations: {_fmt_alloc(allocs)}")
    print(f"Panel: {panel.index.min().date()} → {panel.index.max().date()}  ({len(panel)} bdays)")
    print()
    print(f"Outcome:         {outcome.upper()}")
    print(f"Day terminated:  {day} ({panel.index[min(day - 1, len(panel) - 1)].date()})")
    print(f"Max DD:          {max_dd:.2%}")
    print(f"DD tier trigger days (through terminating day): {trigger_days}")
    if culprit is not None:
        print(f"Bust culprit:    {STRATS[culprit]}")


def mode_sensitivity(dd_scale: float, allocs: Dict[str, float]):
    _, _, blocks, _ = _load_all(allocs)
    grid = [0.005, 0.010, 0.015, 0.020, 0.025]
    print("=== Portfolio MC — Sensitivity grid ===")
    print(f"Allocations: {_fmt_alloc(allocs)}")
    print(f"Sims: {SIMS_PER_SEED:,} × {len(SEEDS)} seeds (DD_SCALE fixed at {dd_scale}×)")
    print()
    print(f"{'DD_TRIGGER':<12} {'Pass':>8} {'Bust':>8} {'Timeout':>9} {'p99 DD':>8}")
    print("-" * 48)
    for trig in grid:
        results = [run_seed(seed, SIMS_PER_SEED, blocks, trig, dd_scale) for seed in SEEDS]
        per_seed = SIMS_PER_SEED
        pass_r = np.mean([r["outcomes"]["pass"] / per_seed for r in results])
        bust_r = np.mean([(r["outcomes"]["bust_daily"] + r["outcomes"]["bust_static"]) / per_seed for r in results])
        to_r   = np.mean([r["outcomes"]["timeout"] / per_seed for r in results])
        dds    = [d for r in results for d in r["max_dds"]]
        p99    = np.percentile(dds, 99)
        print(f"{trig:<12.3%} {pass_r:>8.2%} {bust_r:>8.2%} {to_r:>9.2%} {p99:>8.2%}")
    # Also no-protection row
    np_results = [run_seed(seed, SIMS_PER_SEED, blocks, 10.0, dd_scale) for seed in SEEDS]
    pass_r = np.mean([r["outcomes"]["pass"] / SIMS_PER_SEED for r in np_results])
    bust_r = np.mean([(r["outcomes"]["bust_daily"] + r["outcomes"]["bust_static"]) / SIMS_PER_SEED for r in np_results])
    to_r   = np.mean([r["outcomes"]["timeout"] / SIMS_PER_SEED for r in np_results])
    dds    = [d for r in np_results for d in r["max_dds"]]
    p99    = np.percentile(dds, 99)
    print(f"{'no-protect':<12} {pass_r:>8.2%} {bust_r:>8.2%} {to_r:>9.2%} {p99:>8.2%}")


# ── Entry ─────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(prog="portfolio_mc",
                                description="Single-tier challenge-outcome simulator")
    p.add_argument("--dd-trigger", type=float, default=DD_TRIGGER,
                   help=f"DD trigger (default {DD_TRIGGER} from dd_protection.py)")
    p.add_argument("--dd-scale", type=float, default=DD_SCALE,
                   help=f"DD scale (default {DD_SCALE} from dd_protection.py)")
    p.add_argument("--no-protection", action="store_true",
                   help="Run without DD protection")
    p.add_argument("--historical", action="store_true",
                   help="Deterministic walk through the historical panel")
    p.add_argument("--sensitivity", action="store_true",
                   help="DD-trigger sensitivity grid")
    p.add_argument("--guardian-risk", type=float, default=None,
                   help="Override Guardian allocation for what-if MC (e.g. 0.0025 to simulate a reduced-risk overlay)")
    args = p.parse_args()

    allocs = dict(ALLOCATIONS)
    if args.guardian_risk is not None:
        allocs["guardian"] = args.guardian_risk

    if args.sensitivity:
        mode_sensitivity(args.dd_scale, allocs)
    elif args.historical:
        mode_historical(args.dd_trigger, args.dd_scale, args.no_protection, allocs)
    else:
        mode_default(args.dd_trigger, args.dd_scale, args.no_protection, allocs)


if __name__ == "__main__":
    main()
