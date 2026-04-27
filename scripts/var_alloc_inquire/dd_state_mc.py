"""
Stage 1 — variable-allocation MC conditioned on DD-state, survival objective,
scale-down-only grid.

Inquiry: `loop_2026-04-26_var_alloc_observables` (Stage 1 of staged inquiry).
Predecessor: `loop_2026-04-?_var_alloc_inquire` — verdict 4A REJECTED for
rolling-PF state under returns-max objective + symmetric WoW grid.

Stage 0 brief:
  docs/methodology/findings/2026-04-26_var_alloc_observables_stage0.md

Differences vs the prior var_alloc_mc.py harness (worktree elated-mcclintock-7ac85b):
  - Objective: SURVIVAL-weighted (no-bust + small DD aversion), not returns-max.
  - Policy grid: SCALE-DOWN ONLY (r_k in {0, 0.2, 0.4, 0.6, 0.8, 1.0}); never
    amplifies above locked allocation.
  - Cond 3 observable: (dd_bin, days_since_peak_bin) instead of per-strategy
    rolling-PF bins.
  - Verdict bar: must beat fixed+dd_protection (Cond 1 in this harness, since
    simulate_var_alloc already applies dd_protection internally) by:
      >= 1pp pass-rate beyond seed sigma-band, OR
      >= 0.2pp bust-rate reduction beyond seed sigma-band,
      AND no degradation > 0.5 sigma on p99 DD or median days-to-pass.

Run:
  python -m scripts.var_alloc_inquire.dd_state_mc --quick     # sanity (500/seed)
  python -m scripts.var_alloc_inquire.dd_state_mc             # full (10K x 3)
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from portfolio_mc import (  # noqa: E402
    STARTING_EQUITY, PROFIT_TARGET, DAILY_LOSS_PCT, STATIC_DD_PCT,
    MIN_TRADING_DAYS, HORIZON_DAYS, SIMS_PER_SEED, SEEDS,
    ALLOCATIONS, STRATS,
)
from dd_protection import DD_TRIGGER, DD_SCALE  # noqa: E402

# Reuse load_pepperstone_panel + summarize/fmt_summary from the prior harness.
from scripts.var_alloc_inquire.var_alloc_mc import (  # noqa: E402
    load_pepperstone_panel, simulate_var_alloc, run_fixed_policy,
    summarize, fmt_summary, ALLOC_VEC, WOW_MAX_CHANGE,
)

# ── Stage 1 constants ─────────────────────────────────────────────────────

# Scale-down-only grid levels per strategy.
GRID_LEVELS = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)

# DD-state binning. Bins are upper edges; values <= edge fall in that bin.
# dd_from_peak is reported as a positive fraction (e.g., 0.012 = 1.2% DD).
DD_BIN_EDGES = (0.005, 0.010, 0.020, np.inf)   # < 0.5%, 0.5-1.0%, 1.0-2.0%, >= 2.0%
DSP_BIN_EDGES = (4, 19, np.inf)                 # 0-4 days, 5-19 days, >= 20 days

# Survival objective coefficient (Stage 0 brief §"Stage 1 modifications" #1):
#   score = +pnl_sum - BUST_PENALTY * I(bust_in_week)
# Among non-busting candidates, pure returns-max. No standalone DD penalty —
# the dd_protection layer (active inside survival_score) already handles DD.
BUST_PENALTY = 1e9


# ── Scale-down-only grid ──────────────────────────────────────────────────

def build_scale_down_grid() -> np.ndarray:
    """Per-strategy ratio grid with r_k in GRID_LEVELS, r_k <= 1.0 always.
    Sum-budget is always satisfied (locked sum 2.84% < 3.0%).
    Returns array of shape (n_candidates, 3)."""
    g = []
    for r_g in GRID_LEVELS:
        for r_s in GRID_LEVELS:
            for r_a in GRID_LEVELS:
                g.append([r_g, r_s, r_a])
    return np.array(g)


def apply_wow_constraint_local(prev: np.ndarray, candidate: np.ndarray) -> bool:
    """WoW constraint: |Δr|/r_prev <= WOW_MAX_CHANGE per strategy.
    If prev_k = 0, allow the candidate up to 1.0 absolute (one-sided).
    Identical to var_alloc_mc.apply_wow_constraint, copied to keep dd_state_mc
    self-contained for read-review."""
    for k in range(len(prev)):
        if prev[k] < 1e-9:
            if candidate[k] > 1.0:
                return False
        else:
            if abs(candidate[k] - prev[k]) / prev[k] > WOW_MAX_CHANGE + 1e-9:
                return False
    return True


def no_wow_constraint(prev: np.ndarray, candidate: np.ndarray) -> bool:
    """No-WoW: any candidate within the grid is allowed. Used for the
    scale-down-only run that "drops the WoW asymmetry problem" per Stage 0
    brief — dd_protection itself has no WoW, so the WoW-constrained variant
    handicaps the oracle relative to the production analogue."""
    return True


# ── Survival score for a single week ──────────────────────────────────────

def survival_score(week_path: np.ndarray, candidate_r: np.ndarray,
                   eq_in: float, peak_in: float,
                   dsp_in: int,
                   dd_trigger: float = DD_TRIGGER,
                   dd_scale: float = DD_SCALE
                   ) -> Tuple[float, bool, float, float, int]:
    """Simulate one week starting from (eq_in, peak_in, dsp_in) using candidate_r.
    Returns (score, busted, eq_out, peak_out, dsp_out).

    Score:
      - busted week: -BUST_PENALTY (dominated by any non-busting candidate).
      - non-busting week: pnl_sum (pure returns-max). dd_protection runs
        inside this loop and already provides the DD-aversion mechanism.

    dd_protection is applied inside this loop, identical to simulate_var_alloc."""
    eq = eq_in
    peak = peak_in
    dsp = dsp_in
    pnl_sum = 0.0
    for day_pnl in week_path:
        dd_from_peak = (eq - peak) / peak if peak > 0 else 0.0
        prot = dd_scale if dd_from_peak <= -dd_trigger else 1.0
        pnl = float((day_pnl * candidate_r * prot).sum())

        if pnl / STARTING_EQUITY <= DAILY_LOSS_PCT:
            return -BUST_PENALTY, True, eq, peak, dsp
        if (eq + pnl - STARTING_EQUITY) / STARTING_EQUITY <= STATIC_DD_PCT:
            return -BUST_PENALTY, True, eq, peak, dsp

        eq = eq + pnl
        if eq > peak:
            peak = eq
            dsp = 0
        else:
            dsp += 1
        pnl_sum += pnl

    return pnl_sum, False, eq, peak, dsp


# ── DD-state binning ──────────────────────────────────────────────────────

def dd_state_to_bin(dd_from_peak: float, days_since_peak: int) -> Tuple[int, int]:
    """Bin (dd_from_peak, days_since_peak) into (dd_bin_idx, dsp_bin_idx).
    dd_from_peak is a non-negative fraction (eq <= peak)."""
    dd = max(0.0, dd_from_peak)
    dd_bin = int(np.searchsorted(DD_BIN_EDGES, dd, side="left"))
    dsp_bin = int(np.searchsorted(DSP_BIN_EDGES, days_since_peak, side="left"))
    return dd_bin, dsp_bin


# ── Cond 2: full-future SURVIVAL oracle ───────────────────────────────────

@dataclass
class PolicyResult:
    outcome: str
    day: int
    max_dd: float


def _run_oracle_full_future_survival_one(rng: np.random.Generator,
                                          blocks: np.ndarray,
                                          grid: np.ndarray,
                                          wow_fn) -> Tuple[PolicyResult, np.ndarray]:
    """Run one sim under the survival oracle. Returns (PolicyResult, weekly_ratios)."""
    n_blocks = len(blocks)
    blocks_per_sim = (HORIZON_DAYS + 4) // 5
    idx = rng.integers(0, n_blocks, blocks_per_sim)
    path = np.concatenate([blocks[i] for i in idx])[:HORIZON_DAYS]

    weekly_ratios = np.empty((blocks_per_sim, len(STRATS)))
    eq = peak = float(STARTING_EQUITY)
    dsp = 0
    prev = np.ones(len(STRATS))
    for w in range(blocks_per_sim):
        week_path = path[w * 5: (w + 1) * 5]
        if week_path.shape[0] == 0:
            weekly_ratios[w] = prev
            continue
        best_score = -np.inf
        best_r = prev
        for r in grid:
            if not wow_fn(prev, r):
                continue
            score, _, _, _, _ = survival_score(week_path, r, eq, peak, dsp)
            if score > best_score:
                best_score = score
                best_r = r
        weekly_ratios[w] = best_r
        # Advance shared state by the week we'll actually take.
        _, _, eq, peak, dsp = survival_score(week_path, best_r, eq, peak, dsp)
        prev = best_r

    outcome, day, max_dd, _, _ = simulate_var_alloc(path, weekly_ratios)
    return PolicyResult(outcome, day, max_dd), weekly_ratios


def run_oracle_full_future_survival(seed: int, n_sims: int, blocks: np.ndarray,
                                     grid: np.ndarray, wow_fn) -> List[PolicyResult]:
    rng = np.random.default_rng(seed)
    return [_run_oracle_full_future_survival_one(rng, blocks, grid, wow_fn)[0]
            for _ in range(n_sims)]


# ── Cond 3 collection: DD-state observable from Cond 2 traces ─────────────

def collect_dd_policy_from_oracle(seeds: Tuple[int, ...], n_sims_per_seed: int,
                                    blocks: np.ndarray,
                                    grid: np.ndarray,
                                    wow_fn
                                    ) -> Dict[Tuple[int, int], np.ndarray]:
    """Pass 1 for Cond 3: re-run survival oracle and record
    (dd_state_at_week_start, oracle_optimal_r) pairs. For each state bin,
    snap the per-state mean optimal allocation to the closest grid point."""
    blocks_per_sim = (HORIZON_DAYS + 4) // 5
    bin_sums: Dict[Tuple[int, int], Tuple[np.ndarray, int]] = {}
    for seed in seeds:
        rng = np.random.default_rng(seed)
        n_blocks = len(blocks)
        for _ in range(n_sims_per_seed):
            idx = rng.integers(0, n_blocks, blocks_per_sim)
            path = np.concatenate([blocks[i] for i in idx])[:HORIZON_DAYS]
            eq = peak = float(STARTING_EQUITY)
            dsp = 0
            prev = np.ones(len(STRATS))
            for w in range(blocks_per_sim):
                week_path = path[w * 5: (w + 1) * 5]
                if week_path.shape[0] == 0:
                    continue
                dd_at_start = (peak - eq) / peak if peak > 0 else 0.0
                state = dd_state_to_bin(dd_at_start, dsp)
                best_score = -np.inf
                best_r = prev
                for r in grid:
                    if not wow_fn(prev, r):
                        continue
                    score, _, _, _, _ = survival_score(week_path, r, eq, peak, dsp)
                    if score > best_score:
                        best_score = score
                        best_r = r
                if state not in bin_sums:
                    bin_sums[state] = (np.zeros(len(STRATS)), 0)
                cur_sum, cur_n = bin_sums[state]
                bin_sums[state] = (cur_sum + best_r, cur_n + 1)
                _, _, eq, peak, dsp = survival_score(week_path, best_r, eq, peak, dsp)
                prev = best_r
    policy: Dict[Tuple[int, int], np.ndarray] = {}
    for state, (s, n) in bin_sums.items():
        if n == 0:
            continue
        mean_r = s / n
        # Snap to closest grid point.
        dists = np.linalg.norm(grid - mean_r, axis=1)
        policy[state] = grid[int(np.argmin(dists))]
    return policy, bin_sums


# ── Cond 3: state-readable DD policy applied in-sim ───────────────────────

def run_oracle_dd_state(seed: int, n_sims: int, blocks: np.ndarray,
                        grid: np.ndarray,
                        policy: Dict[Tuple[int, int], np.ndarray],
                        wow_fn
                        ) -> List[PolicyResult]:
    """Cond 3: at each week, look up the policy for the observed DD-state at
    week start. Apply WoW projection if the policy choice violates WoW."""
    rng = np.random.default_rng(seed)
    n_blocks = len(blocks)
    blocks_per_sim = (HORIZON_DAYS + 4) // 5
    fallback_default = np.ones(len(STRATS))
    results: List[PolicyResult] = []
    for _ in range(n_sims):
        idx = rng.integers(0, n_blocks, blocks_per_sim)
        path = np.concatenate([blocks[i] for i in idx])[:HORIZON_DAYS]
        weekly_ratios = np.empty((blocks_per_sim, len(STRATS)))
        eq = peak = float(STARTING_EQUITY)
        dsp = 0
        prev = fallback_default.copy()
        for w in range(blocks_per_sim):
            dd_at_start = (peak - eq) / peak if peak > 0 else 0.0
            state = dd_state_to_bin(dd_at_start, dsp)
            chosen = policy.get(state, fallback_default)
            if not wow_fn(prev, chosen):
                # WoW projection: blend halfway, clip to [0, 1].
                proj = prev + (chosen - prev) * WOW_MAX_CHANGE
                proj = np.clip(proj, 0.0, 1.0)
                chosen = proj
            weekly_ratios[w] = chosen
            prev = chosen
            week_path = path[w * 5: (w + 1) * 5]
            if week_path.shape[0] == 0:
                continue
            # Advance state by simulating the week we'll actually take.
            _, _, eq, peak, dsp = survival_score(week_path, chosen, eq, peak, dsp)
        outcome, day, max_dd, _, _ = simulate_var_alloc(path, weekly_ratios)
        results.append(PolicyResult(outcome, day, max_dd))
    return results


# ── Verdict bar ───────────────────────────────────────────────────────────

def evaluate_verdict(s_baseline: Dict, s_candidate: Dict, label: str) -> Dict:
    """Pre-registered verdict bar from Stage 0 brief, tightened to Pareto-improvement
    discipline (a candidate that trades 15pp of pass-rate for 0.5pp of bust-rate
    is not actually a beat — dd_protection itself was held to a higher bar).

    Beats baseline if:
      Headline: pass-rate >= baseline + max(0.01, 2σ_pass), OR
                bust-rate <= baseline - max(0.002, 2σ_bust)
      AND no significant degradation on the other three metrics:
        pass-rate not worse by more than 1pp (within seed noise)
        bust-rate not worse by more than 0.2pp
        p99 DD not worse by more than 0.5pp
        median days-to-pass not worse by more than 5 days
    """
    pass_bar = s_baseline["pass_mean"] + max(0.01, 2 * s_baseline["pass_sigma"])
    bust_bar = s_baseline["bust_mean"] - max(0.002, 2 * s_baseline["bust_sigma"])
    pass_ok = s_candidate["pass_mean"] >= pass_bar
    bust_ok = s_candidate["bust_mean"] <= bust_bar

    # Non-degradation on all four metrics (regardless of which is the headline):
    pass_no_degrade = s_candidate["pass_mean"] >= s_baseline["pass_mean"] - 0.01
    bust_no_degrade = s_candidate["bust_mean"] <= s_baseline["bust_mean"] + 0.002
    dd_no_degrade = s_candidate["p99_dd"] <= s_baseline["p99_dd"] + 0.005
    days_no_degrade = s_candidate["median_days_to_pass"] <= s_baseline["median_days_to_pass"] + 5

    headline_ok = pass_ok or bust_ok
    pareto_ok = pass_no_degrade and bust_no_degrade and dd_no_degrade and days_no_degrade
    overall_ok = headline_ok and pareto_ok

    return {
        "label": label,
        "pass_bar": pass_bar,
        "pass_ok": pass_ok,
        "bust_bar": bust_bar,
        "bust_ok": bust_ok,
        "pass_baseline": s_baseline["pass_mean"],
        "pass_candidate": s_candidate["pass_mean"],
        "pass_no_degrade": pass_no_degrade,
        "bust_baseline": s_baseline["bust_mean"],
        "bust_candidate": s_candidate["bust_mean"],
        "bust_no_degrade": bust_no_degrade,
        "dd_baseline": s_baseline["p99_dd"],
        "dd_candidate": s_candidate["p99_dd"],
        "dd_no_degrade": dd_no_degrade,
        "days_baseline": s_baseline["median_days_to_pass"],
        "days_candidate": s_candidate["median_days_to_pass"],
        "days_no_degrade": days_no_degrade,
        "headline_ok": headline_ok,
        "pareto_ok": pareto_ok,
        "overall_ok": overall_ok,
    }


def fmt_verdict(v: Dict) -> str:
    def _ok(b: bool) -> str:
        return "PASS" if b else "fail"
    return (
        f"{v['label']}\n"
        f"  Headline (need at least one):\n"
        f"    pass-rate >= {v['pass_bar']:.2%}  -> candidate {v['pass_candidate']:.2%}  {_ok(v['pass_ok'])}\n"
        f"    bust-rate <= {v['bust_bar']:.2%}  -> candidate {v['bust_candidate']:.2%}  {_ok(v['bust_ok'])}\n"
        f"  Non-degradation (need all four):\n"
        f"    pass-rate not worse by >1pp ({v['pass_baseline']:.2%} - 1pp = {v['pass_baseline']-0.01:.2%})  "
        f"-> candidate {v['pass_candidate']:.2%}  {_ok(v['pass_no_degrade'])}\n"
        f"    bust-rate not worse by >0.2pp ({v['bust_baseline']:.2%} + 0.2pp = {v['bust_baseline']+0.002:.2%})  "
        f"-> candidate {v['bust_candidate']:.2%}  {_ok(v['bust_no_degrade'])}\n"
        f"    p99 DD not worse by >0.5pp ({v['dd_baseline']:.2%} + 0.5pp = {v['dd_baseline']+0.005:.2%})  "
        f"-> candidate {v['dd_candidate']:.2%}  {_ok(v['dd_no_degrade'])}\n"
        f"    median days-to-pass not worse by >5 ({v['days_baseline']} + 5 = {v['days_baseline']+5})  "
        f"-> candidate {v['days_candidate']}  {_ok(v['days_no_degrade'])}\n"
        f"  >>> verdict: {'BEATS BASELINE' if v['overall_ok'] else 'does NOT beat baseline'}  "
        f"(headline {_ok(v['headline_ok'])}, pareto {_ok(v['pareto_ok'])})"
    )


# ── Policy table debug print ──────────────────────────────────────────────

def print_policy_table(policy: Dict[Tuple[int, int], np.ndarray],
                        bin_sums: Dict[Tuple[int, int], Tuple[np.ndarray, int]]) -> None:
    """Print the (dd_bin, dsp_bin) -> r_vec table with sample counts.
    Also report degeneracy: is the policy effectively (1,1,1) everywhere?"""
    dd_labels = ["<0.5%", "0.5-1%", "1-2%", ">=2%"]
    dsp_labels = ["dsp<5", "dsp 5-19", "dsp>=20"]
    print(f"  {'state':<20} {'r_g':>5} {'r_s':>5} {'r_a':>5}  n_obs")
    print(f"  {'-' * 20} {'-' * 5} {'-' * 5} {'-' * 5}  -----")
    n_nontrivial = 0
    n_total = 0
    for dd_idx in range(len(DD_BIN_EDGES)):
        for dsp_idx in range(len(DSP_BIN_EDGES)):
            state = (dd_idx, dsp_idx)
            r = policy.get(state)
            n = bin_sums.get(state, (None, 0))[1]
            label = f"{dd_labels[dd_idx]:<8}/{dsp_labels[dsp_idx]:<10}"
            if r is None:
                print(f"  {label:<20} {'--':>5} {'--':>5} {'--':>5}  {n}")
                continue
            n_total += 1
            non_trivial = bool(np.any(r < 0.99))
            if non_trivial:
                n_nontrivial += 1
            mark = " *" if non_trivial else "  "
            print(f"  {label:<20} {r[0]:>5.2f} {r[1]:>5.2f} {r[2]:>5.2f}  {n}{mark}")
    print(f"  ({n_nontrivial}/{n_total} states with non-(1,1,1) policy)")


# ── Orchestrator ──────────────────────────────────────────────────────────

def _run_variant(label_suffix: str, wow_fn, n_sims: int, blocks: np.ndarray,
                  grid: np.ndarray, s1: Dict) -> Tuple[Dict, Dict]:
    """Run Cond 2 + Cond 3 for one constraint variant. Returns (v2, v3) verdict dicts."""
    print(f"=== Cond 2 (survival oracle, {label_suffix}) "
          f"- {n_sims:,} sims x {len(SEEDS)} seeds ===")
    cond2 = [run_oracle_full_future_survival(seed, n_sims, blocks, grid, wow_fn)
             for seed in SEEDS]
    s2 = summarize(cond2, f"cond_2_survival_{label_suffix}")
    print(fmt_summary(s2))
    v2 = evaluate_verdict(s1, s2, f"Cond 2 ({label_suffix}) vs Cond 1:")
    print(fmt_verdict(v2))
    print()

    print(f"=== Cond 3 ({label_suffix} policy table) - building from Cond 2 traces ===")
    policy, bin_sums = collect_dd_policy_from_oracle(SEEDS, n_sims, blocks, grid, wow_fn)
    print(f"Policy covers {len(policy)} of {len(DD_BIN_EDGES) * len(DSP_BIN_EDGES)} "
          f"possible (dd_bin, dsp_bin) states")
    print_policy_table(policy, bin_sums)
    print()

    print(f"=== Cond 3 ({label_suffix}, applied) "
          f"- {n_sims:,} sims x {len(SEEDS)} seeds ===")
    cond3 = [run_oracle_dd_state(seed, n_sims, blocks, grid, policy, wow_fn)
             for seed in SEEDS]
    s3 = summarize(cond3, f"cond_3_dd_state_{label_suffix}")
    print(fmt_summary(s3))
    v3 = evaluate_verdict(s1, s3, f"Cond 3 ({label_suffix}) vs Cond 1:")
    print(fmt_verdict(v3))
    print()
    return v2, v3


def run_main(n_sims: int, do_oracle: bool) -> int:
    print("Loading Pepperstone panel...")
    _, panel, blocks, scale_info = load_pepperstone_panel()
    print(f"Panel: {panel.index.min().date()} -> {panel.index.max().date()}  "
          f"({len(panel)} bdays, {len(blocks)} week-blocks)")
    for s, info in scale_info.items():
        tag = " [FALLBACK]" if info["fell_back"] else ""
        print(f"  {s:<10} 1R=${info['implied_1r']:>7,.2f}  scale={info['scale']:>6.3f}  "
              f"n={info['n_trades']}{tag}")
    print()

    print(f"=== Cond 1 (fixed + dd_protection, control) "
          f"- {n_sims:,} sims x {len(SEEDS)} seeds ===")
    cond1 = [run_fixed_policy(seed, n_sims, blocks) for seed in SEEDS]
    s1 = summarize(cond1, "cond_1_fixed_with_dd_protection")
    print(fmt_summary(s1))
    print(f"  expected anchor (10K x 3): pass=92.73%, bust=0.65%, p99DD=4.94%, medDays=32")
    print()

    if not do_oracle:
        return 0

    grid = build_scale_down_grid()
    print(f"Scale-down-only grid: {len(grid)} candidate ratio vectors "
          f"(r_k in {GRID_LEVELS})")
    print()

    # Variant A: with WoW (parity with prior var_alloc_inquire constraint set).
    print("###### Variant A: WoW constraint (parity with rolling-PF inquiry) ######")
    print()
    v2_wow, v3_wow = _run_variant("with_wow", apply_wow_constraint_local,
                                    n_sims, blocks, grid, s1)

    # Variant B: no WoW (Stage 0 brief: scale-down-only "drops the WoW asymmetry problem").
    print("###### Variant B: no WoW (matches dd_protection's no-WoW production analogue) ######")
    print()
    v2_now, v3_now = _run_variant("no_wow", no_wow_constraint,
                                    n_sims, blocks, grid, s1)

    print("=== Stage 1 verdict summary ===")
    print(f"  Variant A (with WoW):   Cond 2 {'PASS' if v2_wow['overall_ok'] else 'fail'},  "
          f"Cond 3 {'PASS' if v3_wow['overall_ok'] else 'fail'}")
    print(f"  Variant B (no WoW):     Cond 2 {'PASS' if v2_now['overall_ok'] else 'fail'},  "
          f"Cond 3 {'PASS' if v3_now['overall_ok'] else 'fail'}")
    any_pass = any(v["overall_ok"] for v in [v2_wow, v3_wow, v2_now, v3_now])
    if not any_pass:
        print()
        print(">>> Stage 1 REJECTS: no DD-state-conditioned variant Pareto-improves over")
        print(">>> fixed + dd_protection. Closes the inquiry across all four observables")
        print(">>> per the Cond 2 generalization argument from Stage 0.")

    return 0 if any_pass else 1


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-sims", type=int, default=SIMS_PER_SEED)
    ap.add_argument("--quick", action="store_true",
                    help="Quick sanity: 500 sims/seed (Cond 1 only)")
    args = ap.parse_args()
    n = 500 if args.quick else args.n_sims
    sys.exit(run_main(n, do_oracle=not args.quick))
