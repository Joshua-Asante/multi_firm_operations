"""
Phase 2/3 — variable-allocation portfolio MC for the var-alloc Inquire loop.

Builds on portfolio_mc.py's panel/block/simulator structure but accepts a
per-week allocation-ratio policy r = (r_g, r_s, r_a) where the actual PnL
contribution per strategy on a given day is:

    var_pnl[d, k] = panel_locked[d, k] * ratio_at_week[d, k]

This is mathematically equivalent to running the canonical MC at allocation
(locked_alloc[k] * ratio[k]) per strategy, but lets the policy change weekly
without rebuilding the panel.

Three policy conditions:
    cond_1 (control)         : ratio = 1.0 every week (== fixed locked)
    cond_2 (full-future)     : oracle sees next week's PnL block, picks ratios
                               from a constrained grid that maximize objective
    cond_3 (rolling-PF only) : oracle picks ratios as a function of rolling
                               60d PF state observed at week start; the policy
                               is a lookup table optimized across all sim-weeks

Constraints for cond_2 / cond_3:
  - Per-strategy ratio: r_k ∈ [0.0, alloc_max_k / alloc_locked_k] where
    alloc_max = 2.0%. Locked allocs G/S/A = 0.34/1.00/1.50%, so r_max =
    (5.88, 2.00, 1.33) per strategy.
  - Sum risk budget: 0.34*r_g + 1.00*r_s + 1.50*r_a ≤ 3.0  (in % units).
  - Week-over-week ratio change: |r_new - r_prev| / r_prev ≤ 0.5 per strategy.

Run:  python -m scripts.var_alloc_inquire.var_alloc_mc
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Tuple

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from portfolio_mc import (  # noqa: E402
    STARTING_EQUITY, PROFIT_TARGET, DAILY_LOSS_PCT, STATIC_DD_PCT,
    MIN_TRADING_DAYS, HORIZON_DAYS, SIMS_PER_SEED, SEEDS,
    ALLOCATIONS, STRATS,
    load_trades, build_daily_panel, build_week_blocks,
    OANDA_PANELS,
)
from dd_protection import DD_TRIGGER, DD_SCALE  # noqa: E402

PEP_DIR = REPO / "data" / "tv_exports" / "pepperstone"
PEP_PANELS: Dict[str, Path] = {
    "guardian": PEP_DIR / "Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-04-26_87e73.csv",
    "striker":  PEP_DIR / "Striker_DJ30_v4.4_PEPPERSTONE_US30_2026-04-26_3eea0.csv",
    "aegis":    PEP_DIR / "Aegis_USDJPY_v4.3_PEPPERSTONE_USDJPY_2026-04-26_0bf1b.csv",
}

ALLOC_VEC = np.array([ALLOCATIONS[s] for s in STRATS])
ALLOC_MAX = 0.020
SUM_BUDGET = 0.030
WOW_MAX_CHANGE = 0.5
ROLL_DAYS = 60
PF_BIN_EDGES = np.array([0.0, 1.0, 2.0, 3.0, 5.0, np.inf])


# ── Pepperstone panel loader (uses portfolio_mc.load_trades + build_daily_panel) ─

def load_pepperstone_panel():
    trades_by_strat = {s: load_trades(PEP_PANELS[s]) for s in STRATS}
    panel, scale_info = build_daily_panel(trades_by_strat, ALLOCATIONS)
    blocks = build_week_blocks(panel)
    return trades_by_strat, panel, blocks, scale_info


# ── Core var-alloc simulator ──────────────────────────────────────────────

def simulate_var_alloc(path: np.ndarray,
                       weekly_ratios: np.ndarray,
                       dd_trigger: float = DD_TRIGGER,
                       dd_scale: float = DD_SCALE,
                       horizon: int = HORIZON_DAYS) -> Tuple[str, int, float, np.ndarray, np.ndarray]:
    """Run one sim with a sequence of weekly ratio vectors.

    path:           (horizon, n_strats) — locked-alloc-scaled PnL.
    weekly_ratios:  (n_weeks, n_strats) — per-strategy multiplier vs locked.

    Returns (outcome, day_terminated, max_dd, equity_series, daily_pnl_series).
    """
    eq = peak = float(STARTING_EQUITY)
    trade_days = 0
    max_dd = 0.0
    equity_series = np.empty(horizon)
    daily_pnl_series = np.empty(horizon)

    for day in range(horizon):
        week_idx = min(day // 5, len(weekly_ratios) - 1)
        ratios = weekly_ratios[week_idx]
        dd_from_peak = (eq - peak) / peak if peak > 0 else 0.0
        prot_scale = dd_scale if dd_from_peak <= -dd_trigger else 1.0
        strat_pnls = path[day] * ratios * prot_scale
        pnl = float(strat_pnls.sum())

        daily_pnl_series[day] = pnl
        equity_series[day] = eq + pnl

        if pnl / STARTING_EQUITY <= DAILY_LOSS_PCT:
            return "bust_daily", day + 1, max_dd, equity_series[:day + 1], daily_pnl_series[:day + 1]
        if (eq + pnl - STARTING_EQUITY) / STARTING_EQUITY <= STATIC_DD_PCT:
            return "bust_static", day + 1, max_dd, equity_series[:day + 1], daily_pnl_series[:day + 1]

        eq = eq + pnl
        if eq > peak:
            peak = eq
        dd_now = (peak - eq) / peak if peak > 0 else 0.0
        if dd_now > max_dd:
            max_dd = dd_now
        if pnl != 0:
            trade_days += 1

        if eq >= PROFIT_TARGET and trade_days >= MIN_TRADING_DAYS:
            return "pass", day + 1, max_dd, equity_series[:day + 1], daily_pnl_series[:day + 1]

    return "timeout", horizon, max_dd, equity_series, daily_pnl_series


# ── Rolling-PF observation in-simulation ──────────────────────────────────

def in_sim_rolling_pf(per_strat_daily_pnl: np.ndarray, lookback_days: int = ROLL_DAYS) -> np.ndarray:
    """Compute rolling PF per strategy from the most recent `lookback_days` of
    in-sim per-strategy PnL.

    per_strat_daily_pnl: (n_days_so_far, n_strats)
    Returns: (n_strats,) PF values, NaN when window has < 5 nonzero days.
    """
    n_strats = per_strat_daily_pnl.shape[1]
    out = np.full(n_strats, np.nan)
    if per_strat_daily_pnl.shape[0] == 0:
        return out
    window = per_strat_daily_pnl[-lookback_days:]
    for k in range(n_strats):
        col = window[:, k]
        nonzero = col[col != 0]
        if len(nonzero) < 5:
            continue
        gp = nonzero[nonzero > 0].sum()
        gl = -nonzero[nonzero < 0].sum()
        if gl <= 1e-9:
            out[k] = np.inf
        else:
            out[k] = gp / gl
    return out


def pf_to_bin(pf: float) -> int:
    if np.isnan(pf):
        return 0  # treat warmup as low-PF bin
    return int(np.searchsorted(PF_BIN_EDGES[1:], pf))


# ── Allocation grid (constrained) ─────────────────────────────────────────

def build_alloc_grid(grid_levels: int = 5) -> np.ndarray:
    """Per-strategy ratio grid satisfying:
      - r_k * locked_k ∈ [0, ALLOC_MAX]
      - sum_k r_k * locked_k ≤ SUM_BUDGET
    Levels include 0.0 (zero allocation).
    """
    candidates = []
    for k, locked in enumerate(ALLOC_VEC):
        max_r = min(ALLOC_MAX / locked, SUM_BUDGET / locked)
        candidates.append(np.linspace(0.0, max_r, grid_levels))
    grid = []
    for r_g in candidates[0]:
        for r_s in candidates[1]:
            for r_a in candidates[2]:
                r = np.array([r_g, r_s, r_a])
                if (r * ALLOC_VEC).sum() <= SUM_BUDGET + 1e-9:
                    grid.append(r)
    return np.array(grid)


def apply_wow_constraint(prev: np.ndarray, candidate: np.ndarray) -> bool:
    """Reject candidate if any per-strategy ratio changes by > WOW_MAX_CHANGE
    of prev. If prev component is 0, allow up to 1× absolute jump."""
    for k in range(len(prev)):
        if prev[k] < 1e-9:
            if candidate[k] > 1.0:
                return False
        else:
            if abs(candidate[k] - prev[k]) / prev[k] > WOW_MAX_CHANGE + 1e-9:
                return False
    return True


# ── Policies ──────────────────────────────────────────────────────────────

@dataclass
class PolicyResult:
    outcome: str
    day: int
    max_dd: float


def run_fixed_policy(seed: int, n_sims: int, blocks: np.ndarray) -> List[PolicyResult]:
    rng = np.random.default_rng(seed)
    n_blocks = len(blocks)
    blocks_per_sim = (HORIZON_DAYS + 4) // 5
    results: List[PolicyResult] = []
    for _ in range(n_sims):
        idx = rng.integers(0, n_blocks, blocks_per_sim)
        path = np.concatenate([blocks[i] for i in idx])[:HORIZON_DAYS]
        weekly_ratios = np.ones((blocks_per_sim, len(STRATS)))
        outcome, day, max_dd, _, _ = simulate_var_alloc(path, weekly_ratios)
        results.append(PolicyResult(outcome, day, max_dd))
    return results


def run_oracle_full_future(seed: int, n_sims: int, blocks: np.ndarray,
                           grid: np.ndarray, apply_wow: bool = True) -> List[PolicyResult]:
    """Cond 2: oracle sees next-week PnL block, picks ratio that maximizes
    next-week portfolio PnL subject to constraints. apply_wow=False is the
    brief's "unconstrained" sanity-check oracle (no WoW, full grid)."""
    rng = np.random.default_rng(seed)
    n_blocks = len(blocks)
    blocks_per_sim = (HORIZON_DAYS + 4) // 5
    results: List[PolicyResult] = []
    for _ in range(n_sims):
        idx = rng.integers(0, n_blocks, blocks_per_sim)
        path = np.concatenate([blocks[i] for i in idx])[:HORIZON_DAYS]

        weekly_ratios = np.empty((blocks_per_sim, len(STRATS)))
        prev = np.ones(len(STRATS))  # start from locked
        for w in range(blocks_per_sim):
            week_path = path[w * 5: (w + 1) * 5]
            if week_path.shape[0] == 0:
                weekly_ratios[w] = prev
                continue
            week_strat_sums = week_path.sum(axis=0)
            best_score = -np.inf
            best_r = prev
            for r in grid:
                if apply_wow and not apply_wow_constraint(prev, r):
                    continue
                score = (week_strat_sums * r).sum()
                if score > best_score:
                    best_score = score
                    best_r = r
            weekly_ratios[w] = best_r
            prev = best_r

        outcome, day, max_dd, _, _ = simulate_var_alloc(path, weekly_ratios)
        results.append(PolicyResult(outcome, day, max_dd))
    return results


def run_oracle_unconstrained(seed: int, n_sims: int, blocks: np.ndarray) -> List[PolicyResult]:
    """Brief's sanity check #1: oracle with NO constraints at all (per-strategy
    risk can be 0 to a very high cap, no sum constraint, no WoW). Picks per-week
    per-strategy ratio = K_high if week_strat_sum > 0 else 0. Should strictly
    beat fixed; if not, simulator is broken."""
    rng = np.random.default_rng(seed)
    n_blocks = len(blocks)
    blocks_per_sim = (HORIZON_DAYS + 4) // 5
    results: List[PolicyResult] = []
    K_HIGH = 5.0  # ~max per-strategy risk if locked is 1% (5% absolute)
    for _ in range(n_sims):
        idx = rng.integers(0, n_blocks, blocks_per_sim)
        path = np.concatenate([blocks[i] for i in idx])[:HORIZON_DAYS]

        weekly_ratios = np.empty((blocks_per_sim, len(STRATS)))
        for w in range(blocks_per_sim):
            week_path = path[w * 5: (w + 1) * 5]
            if week_path.shape[0] == 0:
                weekly_ratios[w] = np.ones(len(STRATS))
                continue
            week_strat_sums = week_path.sum(axis=0)
            weekly_ratios[w] = np.where(week_strat_sums > 0, K_HIGH, 0.0)

        outcome, day, max_dd, _, _ = simulate_var_alloc(path, weekly_ratios)
        results.append(PolicyResult(outcome, day, max_dd))
    return results


def collect_policy_from_oracle(seeds: Tuple[int, ...], n_sims_per_seed: int,
                                blocks: np.ndarray, grid: np.ndarray) -> Dict:
    """Pass 1 for cond 3: run the full-future oracle (cond 2) and record
    (rolling_pf_state_at_week_start, optimal_alloc_for_that_week) pairs.
    For each state bin, accumulate the per-strategy mean of optimal allocations
    chosen by the oracle. This becomes the cond3 policy: 'if the oracle picks
    these allocations on average given this state, that's the best a state-only
    rule could do.'
    """
    blocks_per_sim = (HORIZON_DAYS + 4) // 5
    bin_sums: Dict[Tuple[int, int, int], Tuple[np.ndarray, int]] = {}
    for seed in seeds:
        rng = np.random.default_rng(seed)
        n_blocks = len(blocks)
        for _ in range(n_sims_per_seed):
            idx = rng.integers(0, n_blocks, blocks_per_sim)
            path = np.concatenate([blocks[i] for i in idx])[:HORIZON_DAYS]
            running = []
            prev = np.ones(len(STRATS))
            for w in range(blocks_per_sim):
                week_path = path[w * 5: (w + 1) * 5]
                if week_path.shape[0] == 0:
                    continue
                pf_state = in_sim_rolling_pf(np.array(running) if running else np.empty((0, len(STRATS))))
                bin_state = tuple(pf_to_bin(p) for p in pf_state)
                # Find oracle's optimal allocation for this week (within constraints)
                week_strat_sums = week_path.sum(axis=0)
                best_score = -np.inf
                best_r = prev
                for r in grid:
                    if not apply_wow_constraint(prev, r):
                        continue
                    score = (week_strat_sums * r).sum()
                    if score > best_score:
                        best_score = score
                        best_r = r
                if bin_state not in bin_sums:
                    bin_sums[bin_state] = (np.zeros(len(STRATS)), 0)
                cur_sum, cur_n = bin_sums[bin_state]
                bin_sums[bin_state] = (cur_sum + best_r, cur_n + 1)
                running.extend(list(week_path))
                prev = best_r
    # Snap each per-state mean allocation to the closest valid grid point.
    policy: Dict[Tuple[int, int, int], np.ndarray] = {}
    for bin_state, (s, n) in bin_sums.items():
        if n == 0:
            continue
        mean_r = s / n
        # Snap to closest grid point that satisfies sum-budget
        dists = np.linalg.norm(grid - mean_r, axis=1)
        policy[bin_state] = grid[int(np.argmin(dists))]
    return policy


def run_oracle_rolling_pf(seed: int, n_sims: int, blocks: np.ndarray,
                          grid: np.ndarray,
                          policy: Dict[Tuple[int, int, int], np.ndarray]) -> List[PolicyResult]:
    """Cond 3: at each week, observe rolling-PF state and look up allocation
    in the (already optimized) policy table derived from cond2-oracle traces.
    WoW constraint applied as a projection — if the policy choice violates
    WoW, blend halfway."""
    rng = np.random.default_rng(seed)
    n_blocks = len(blocks)
    blocks_per_sim = (HORIZON_DAYS + 4) // 5
    results: List[PolicyResult] = []
    fallback_default = np.ones(len(STRATS))
    for _ in range(n_sims):
        idx = rng.integers(0, n_blocks, blocks_per_sim)
        path = np.concatenate([blocks[i] for i in idx])[:HORIZON_DAYS]
        weekly_ratios = np.empty((blocks_per_sim, len(STRATS)))
        prev = fallback_default.copy()
        running = []
        for w in range(blocks_per_sim):
            pf_state = in_sim_rolling_pf(np.array(running) if running else np.empty((0, len(STRATS))))
            bin_state = tuple(pf_to_bin(p) for p in pf_state)
            chosen = policy.get(bin_state, fallback_default)
            if not apply_wow_constraint(prev, chosen):
                # project halfway between prev and chosen, retry
                proj = prev + (chosen - prev) * WOW_MAX_CHANGE
                # clip to grid bounds
                proj = np.minimum(proj, ALLOC_MAX / ALLOC_VEC)
                proj = np.maximum(proj, 0.0)
                chosen = proj
            weekly_ratios[w] = chosen
            prev = chosen
            week_path = path[w * 5: (w + 1) * 5]
            running.extend(list(week_path))
        outcome, day, max_dd, _, _ = simulate_var_alloc(path, weekly_ratios)
        results.append(PolicyResult(outcome, day, max_dd))
    return results


# ── Aggregation ───────────────────────────────────────────────────────────

def summarize(results_per_seed: List[List[PolicyResult]], label: str) -> Dict:
    n_per_seed = len(results_per_seed[0])
    pass_r = [sum(1 for x in r if x.outcome == "pass") / n_per_seed for r in results_per_seed]
    bust_r = [sum(1 for x in r if x.outcome.startswith("bust")) / n_per_seed for r in results_per_seed]
    to_r   = [sum(1 for x in r if x.outcome == "timeout") / n_per_seed for r in results_per_seed]
    all_dds = np.concatenate([np.array([x.max_dd for x in r]) for r in results_per_seed])
    all_days = [x.day for r in results_per_seed for x in r if x.outcome == "pass"]
    return {
        "label": label,
        "pass_mean": float(np.mean(pass_r)),
        "pass_sigma": float(np.std(pass_r)),
        "bust_mean": float(np.mean(bust_r)),
        "bust_sigma": float(np.std(bust_r)),
        "timeout_mean": float(np.mean(to_r)),
        "p99_dd": float(np.percentile(all_dds, 99)),
        "median_days_to_pass": int(np.median(all_days)) if all_days else -1,
    }


def fmt_summary(s: Dict) -> str:
    return (f"{s['label']:<28} "
            f"pass={s['pass_mean']:>6.2%} (σ={s['pass_sigma']:.2%})  "
            f"bust={s['bust_mean']:>6.2%}  "
            f"timeout={s['timeout_mean']:>6.2%}  "
            f"p99DD={s['p99_dd']:>6.2%}  "
            f"medDays={s['median_days_to_pass']}")


# ── CLI ───────────────────────────────────────────────────────────────────

def run_main(n_sims: int, do_oracle: bool):
    print("Loading Pepperstone panel...")
    _, panel, blocks, scale_info = load_pepperstone_panel()
    print(f"Panel: {panel.index.min().date()} -> {panel.index.max().date()}  ({len(panel)} bdays, {len(blocks)} week-blocks)")
    for s, info in scale_info.items():
        tag = " [FALLBACK]" if info["fell_back"] else ""
        print(f"  {s:<10} 1R=${info['implied_1r']:>7,.2f}  scale={info['scale']:>6.3f}  n={info['n_trades']}{tag}")
    print()

    print(f"=== Condition 1 (fixed locked, control) — {n_sims:,} sims x {len(SEEDS)} seeds ===")
    cond1 = [run_fixed_policy(seed, n_sims, blocks) for seed in SEEDS]
    s1 = summarize(cond1, "cond_1_fixed")
    print(fmt_summary(s1))
    print()

    if not do_oracle:
        return

    grid = build_alloc_grid(grid_levels=5)
    print(f"Allocation grid: {len(grid)} candidate ratio vectors")
    print()

    # Brief sanity check #1: unconstrained oracle must beat fixed
    print(f"=== Sanity check (unconstrained oracle) — {n_sims:,} sims x {len(SEEDS)} seeds ===")
    sanity = [run_oracle_unconstrained(seed, n_sims, blocks) for seed in SEEDS]
    s_sanity = summarize(sanity, "sanity_unconstrained")
    print(fmt_summary(s_sanity))
    print(f"  Sanity: unconstrained oracle pass={s_sanity['pass_mean']:.2%} {'PASS' if s_sanity['pass_mean'] > s1['pass_mean'] else 'FAIL — simulator broken'}")
    print()

    print(f"=== Condition 2 (full-future oracle, brief constraints) — {n_sims:,} sims x {len(SEEDS)} seeds ===")
    cond2 = [run_oracle_full_future(seed, n_sims, blocks, grid) for seed in SEEDS]
    s2 = summarize(cond2, "cond_2_full_future")
    print(fmt_summary(s2))
    print()

    print(f"=== Condition 3 (rolling-PF oracle) — building policy table from cond2 traces ===")
    policy = collect_policy_from_oracle(SEEDS, n_sims, blocks, grid)
    print(f"Policy covers {len(policy)} unique PF-state bin-tuples")
    print()

    print(f"=== Condition 3 (rolling-PF oracle, applied) — {n_sims:,} sims x {len(SEEDS)} seeds ===")
    cond3 = [run_oracle_rolling_pf(seed, n_sims, blocks, grid, policy) for seed in SEEDS]
    s3 = summarize(cond3, "cond_3_rolling_pf")
    print(fmt_summary(s3))
    print()

    print("=== Verdict bar (≥2σ improvement on ALL four metrics required for 4C) ===")
    bar_pass = s1["pass_mean"] + 2 * s1["pass_sigma"]
    bar_bust = s1["bust_mean"] - 2 * s1["bust_sigma"]
    bar_dd   = s1["p99_dd"]
    bar_days = s1["median_days_to_pass"]
    print(f"  bar pass ≥ {bar_pass:.2%}     -> cond3 pass = {s3['pass_mean']:.2%}  {'PASS' if s3['pass_mean'] >= bar_pass else 'FAIL'}")
    print(f"  bar bust ≤ {bar_bust:.2%}     -> cond3 bust = {s3['bust_mean']:.2%}  {'PASS' if s3['bust_mean'] <= bar_bust else 'FAIL'}")
    print(f"  bar p99DD ≤ {bar_dd:.2%}    -> cond3 p99DD = {s3['p99_dd']:.2%}  {'PASS' if s3['p99_dd'] <= bar_dd else 'FAIL'}")
    print(f"  bar medDays ≤ {bar_days}      -> cond3 medDays = {s3['median_days_to_pass']}  {'PASS' if s3['median_days_to_pass'] <= bar_days else 'FAIL'}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-sims", type=int, default=SIMS_PER_SEED)
    ap.add_argument("--sanity-only", action="store_true",
                    help="Run only the fixed-allocation sanity check")
    ap.add_argument("--quick", action="store_true",
                    help="Quick sanity: 500 sims/seed (fixed only)")
    args = ap.parse_args()

    n = 500 if args.quick else args.n_sims
    run_main(n, do_oracle=not args.sanity_only and not args.quick)
