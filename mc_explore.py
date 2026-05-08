"""mc_explore — EXPLORATORY MC variant for MSEE Phase 6.

NOT FOR LOCK DECISIONS. portfolio_mc.py remains the canonical lock-decision
MC; this module mirrors its block-bootstrap and 1R logic verbatim and adds:

  --retain-curves       write per-sim daily equity curves to mc_runs/
  --perturb-alloc       scale per-strategy allocations multiplicatively
                        (e.g. --perturb-alloc guardian=1.10 striker=0.90)
  --sims                override SIMS_PER_SEED for fast exploration
  --seed                run a single seed (default: all three from portfolio_mc)

Outputs always include the banner `EXPLORATORY — not for lock decisions`
and `canonical_status: EXPLORATORY` in any JSON written. Lock-path
verification: `python -m portfolio_mc` baseline must produce identical
numbers before and after any session that uses this module.

Reproducibility: `python mc_explore.py [--retain-curves] [--perturb-alloc ...]`
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd

# Reuse portfolio_mc primitives verbatim. NEVER monkey-patch them.
from portfolio_mc import (  # noqa: E402
    STARTING_EQUITY, PROFIT_TARGET, DAILY_LOSS_PCT, STATIC_DD_PCT,
    MIN_TRADING_DAYS, HORIZON_DAYS, SIMS_PER_SEED, SEEDS,
    ALLOCATIONS, STRATS, OANDA_PANELS,
    load_trades, build_daily_panel, build_week_blocks,
)
from lib.mvd import assert_no_fallback, assert_tv_export

BANNER = "*** EXPLORATORY — not for lock decisions ***"
RUNS_DIR = Path(__file__).parent / "mc_runs"


def simulate_path_with_curve(path: np.ndarray, dd_trigger: float,
                             dd_scale: float, horizon: int
                             ) -> Tuple[str, int, float, np.ndarray, np.ndarray]:
    """Like portfolio_mc._simulate_path but also returns the daily
    equity curve and the per-day DD-trigger flag."""
    eq = peak = float(STARTING_EQUITY)
    trade_days = 0
    max_dd = 0.0
    curve = np.full(horizon + 1, np.nan)
    triggered = np.zeros(horizon, dtype=bool)
    curve[0] = eq

    for day in range(horizon):
        dd_from_peak = (eq - peak) / peak if peak > 0 else 0.0
        is_trig = dd_from_peak <= -dd_trigger
        scale = dd_scale if is_trig else 1.0
        triggered[day] = bool(is_trig)
        strat_pnls = path[day] * scale
        pnl = float(strat_pnls.sum())
        eq_new = eq + pnl

        if pnl / STARTING_EQUITY <= DAILY_LOSS_PCT:
            curve[day + 1] = eq_new
            return "bust_daily", day + 1, max_dd, curve[:day + 2], triggered[:day + 1]
        if (eq_new - STARTING_EQUITY) / STARTING_EQUITY <= STATIC_DD_PCT:
            curve[day + 1] = eq_new
            return "bust_static", day + 1, max_dd, curve[:day + 2], triggered[:day + 1]

        eq = eq_new
        if eq > peak:
            peak = eq
        dd_now = (peak - eq) / peak if peak > 0 else 0.0
        if dd_now > max_dd:
            max_dd = dd_now
        if pnl != 0:
            trade_days += 1
        curve[day + 1] = eq

        if eq >= PROFIT_TARGET and trade_days >= MIN_TRADING_DAYS:
            return "pass", day + 1, max_dd, curve[:day + 2], triggered[:day + 1]

    return "timeout", horizon, max_dd, curve, triggered


def run_seed_explore(seed: int, n_sims: int, blocks: np.ndarray,
                     dd_trigger: float, dd_scale: float,
                     retain_curves: bool, horizon: int = HORIZON_DAYS) -> dict:
    rng = np.random.default_rng(seed)
    n_blocks = len(blocks)
    blocks_per_sim = (horizon + 4) // 5
    outcomes = {"pass": 0, "bust_daily": 0, "bust_static": 0, "timeout": 0}
    days_to_pass: list[int] = []
    max_dds: list[float] = []
    curves = []  # only retained when retain_curves=True

    for k in range(n_sims):
        idx = rng.integers(0, n_blocks, blocks_per_sim)
        path = np.concatenate([blocks[i] for i in idx])[:horizon]
        outcome, day, max_dd, curve, _ = simulate_path_with_curve(
            path, dd_trigger, dd_scale, horizon
        )
        outcomes[outcome] += 1
        max_dds.append(max_dd)
        if outcome == "pass":
            days_to_pass.append(day)
        if retain_curves:
            curves.append({"sim_id": k, "outcome": outcome,
                           "day_terminated": day,
                           "curve": curve.tolist()})
    return {
        "outcomes": outcomes,
        "days_to_pass": days_to_pass,
        "max_dds": max_dds,
        "curves": curves,
    }


def parse_perturb(items: list[str] | None) -> Dict[str, float]:
    """Parse --perturb-alloc guardian=1.10 striker=0.95 etc."""
    if not items:
        return {s: 1.0 for s in STRATS}
    out = {s: 1.0 for s in STRATS}
    for it in items:
        if "=" not in it:
            raise SystemExit(f"--perturb-alloc expects key=value, got '{it}'")
        k, v = it.split("=", 1)
        k = k.strip().lower()
        if k not in STRATS:
            raise SystemExit(f"unknown strategy '{k}' (expected one of {STRATS})")
        out[k] = float(v)
    return out


def load_panel_with_perturb(perturb: Dict[str, float]
                            ) -> Tuple[pd.DataFrame, np.ndarray, dict, Dict[str, float]]:
    for s, expected in [
        ("guardian", ("Guardian", "v5.5", "OANDA", "XAUUSD")),
        ("striker", ("Striker", "v4.4", "OANDA", "US30USD")),
        ("aegis", ("Aegis", "v4.3", "OANDA", "USDJPY")),
    ]:
        assert_tv_export(
            OANDA_PANELS[s],
            expected_strategy=expected[0], expected_version=expected[1],
            expected_broker=expected[2], expected_symbol=expected[3],
        )
    trades_by_strat = {s: load_trades(OANDA_PANELS[s]) for s in STRATS}
    perturbed_alloc = {s: ALLOCATIONS[s] * perturb[s] for s in STRATS}
    panel, scale_info = build_daily_panel(trades_by_strat, perturbed_alloc)

    # Same MVD contract as lock-path: full-stop fallback must not silently fire.
    fb = sum(1 for info in scale_info.values() if info["fell_back"])
    assert_no_fallback(fb,
                       label="mc_explore implied_1r (Striker/Aegis full-stop cohort)")

    blocks = build_week_blocks(panel)
    return panel, blocks, scale_info, perturbed_alloc


def main():
    p = argparse.ArgumentParser(prog="mc_explore",
                                description=("EXPLORATORY portfolio MC. "
                                             "Not for lock decisions."))
    p.add_argument("--dd-trigger", type=float, default=0.015)
    p.add_argument("--dd-scale", type=float, default=0.40)
    p.add_argument("--perturb-alloc", nargs="+", default=None,
                   help="Allocation multiplicative perturbation, "
                        "e.g. guardian=1.10 striker=0.95")
    p.add_argument("--sims", type=int, default=SIMS_PER_SEED,
                   help=f"Sims per seed (default {SIMS_PER_SEED})")
    p.add_argument("--seed", type=int, default=None,
                   help="Single-seed override (else all 3 portfolio_mc seeds)")
    p.add_argument("--retain-curves", action="store_true",
                   help="Write per-sim daily equity curves to mc_runs/")
    args = p.parse_args()

    perturb = parse_perturb(args.perturb_alloc)
    panel, blocks, scale_info, alloc = load_panel_with_perturb(perturb)

    seeds = (args.seed,) if args.seed is not None else SEEDS

    print(BANNER)
    print(f"Allocations (perturbed): " +
          " / ".join(f"{s} {alloc[s]*100:.3f}%" for s in STRATS))
    print(f"Perturb multipliers:    " +
          " / ".join(f"{s} {perturb[s]:.3f}" for s in STRATS))
    print(f"DD: trigger={args.dd_trigger:.4f}  scale={args.dd_scale:.3f}  "
          f"sims/seed={args.sims:,}  seeds={seeds}")
    print(f"Panel: {panel.index.min().date()} -> {panel.index.max().date()}  "
          f"({len(panel)} bdays, {len(blocks)} week-blocks)")
    print()

    seeds_results = []
    for seed in seeds:
        r = run_seed_explore(seed, args.sims, blocks,
                             args.dd_trigger, args.dd_scale,
                             retain_curves=args.retain_curves)
        seeds_results.append({"seed": seed, **r})

    per_seed = args.sims
    pass_r = [r["outcomes"]["pass"] / per_seed for r in seeds_results]
    bd_r = [r["outcomes"]["bust_daily"] / per_seed for r in seeds_results]
    bs_r = [r["outcomes"]["bust_static"] / per_seed for r in seeds_results]
    to_r = [r["outcomes"]["timeout"] / per_seed for r in seeds_results]
    bust_r = [d + s for d, s in zip(bd_r, bs_r)]
    all_dds = [d for r in seeds_results for d in r["max_dds"]]
    all_days = [d for r in seeds_results for d in r["days_to_pass"]]

    print(f"Pass:    {np.mean(pass_r):>6.2%} (sigma {np.std(pass_r):.2%})")
    print(f"Bust:    {np.mean(bust_r):>6.2%} (sigma {np.std(bust_r):.2%})")
    print(f"Timeout: {np.mean(to_r):>6.2%}")
    if all_days:
        print(f"Median days to pass: {int(np.median(all_days))}")
    print(f"p99 DD:  {np.percentile(all_dds, 99):.2%}")
    print(BANNER)

    if args.retain_curves:
        RUNS_DIR.mkdir(exist_ok=True, parents=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        out_meta = {
            "canonical_status": "EXPLORATORY",
            "banner": BANNER,
            "perturb": perturb,
            "perturbed_alloc": alloc,
            "dd_trigger": args.dd_trigger,
            "dd_scale": args.dd_scale,
            "sims_per_seed": args.sims,
            "seeds": list(seeds),
            "summary": {
                "pass_mean": float(np.mean(pass_r)),
                "bust_mean": float(np.mean(bust_r)),
                "timeout_mean": float(np.mean(to_r)),
                "p99_dd": float(np.percentile(all_dds, 99)),
                "median_days_to_pass": (int(np.median(all_days))
                                        if all_days else None),
            },
        }
        for r in seeds_results:
            curve_path = RUNS_DIR / f"{ts}_seed_{r['seed']}_curves.json"
            curve_path.write_text(json.dumps({
                "canonical_status": "EXPLORATORY",
                "seed": r["seed"],
                "perturb": perturb,
                "curves": r["curves"],
            }, default=str))
            print(f"Wrote curves: {curve_path.relative_to(Path(__file__).parent)}")
        meta_path = RUNS_DIR / f"{ts}_summary.json"
        meta_path.write_text(json.dumps(out_meta, indent=2, default=str))
        print(f"Wrote summary: {meta_path.relative_to(Path(__file__).parent)}")


if __name__ == "__main__":
    main()
