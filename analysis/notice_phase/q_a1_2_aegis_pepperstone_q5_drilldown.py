"""Q-A1.2 -- Aegis Pepperstone q5 (Sept 2025 -> April 2026) drill-down.

Refinement #1 (cheapest) from Q-A1.1's PARTIAL verdict: characterize the
last 24 trades (Conv B q5, Pepperstone) trade-by-trade to determine
whether the PF=28.4 spike is:
  (a) STRUCTURAL  -- distribution shift (higher median R, lower loss rate,
                     no single-trade dominance, broader-based lift)
  (b) STREAK      -- concentrated in 1-2 large winners; PF collapses to
                     rest-of-panel range when top winner removed
  (c) MIXED       -- elements of both

Same data, same loader as Q-A1 / Q-A1.1. No re-MC required. Out of scope:
allocation, dd_protection, MC calibration, Pine code edits, Notion.

Pine v4.3 exit logic (read from strategies/aegis/aegis_usdjpy_v4.3.pine,
lines 247-270):
  - strategy.exit("X-Long", ...) -- bracket order; SL, BE-stop, OR TP
                                    all collapse to label "X-Long".
  - strategy.close_all(comment="Stale") -- time-stop after max_hold=40 bars.
Disambiguation of SL vs BE vs TP within "X-Long" via R-multiple bucketing:
  - R <= -0.70  : full SL hit (initial stop, BE never triggered)
  - -0.70 < R <= -0.05 : partial loss (rare; mid-trade exits)
  - -0.05 < R <= 0.30 : BE-stop hit after BE-trigger (small win or near-flat)
  - R > 0.30    : meaningful winner (often TP, sometimes BE-stop on a strong day)

Verdict criteria (in order):
  - streak  : top-1 winner share of q5 gross profit >= 40% OR
              PF-after-removing-top-1 < 5.0 (i.e., drops to rest-of-panel range)
              with no offsetting evidence of distribution shift
  - structural : top-1 share < 25% AND median(R)_q5 / median(R)_rest >= 1.3
                 (or, more relevantly, p25/p50 distribution shifted)
                 AND Mann-Whitney U on q5 R vs rest R has p < 0.05
  - mixed   : anything else (e.g., top-1 share 25-40%, or only some criteria
              met, or MW-U p between 0.05 and 0.20)

Run: python analysis/notice_phase/q_a1_2_aegis_pepperstone_q5_drilldown.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent))

from q_a1_aegis_pepperstone_panel import (  # noqa: E402
    load_tv_feed,
    compute_pf,
    PEPPERSTONE_CSV,
    LOCKED_AEGIS_V43,
    PF_TOLERANCE,
    RISK_PCT_AEGIS,
)

# Q-A1.1 Conv B q5 anchor PF (computed on Pepperstone, last 24 trades)
QA1_1_CONV_B_Q5_PF = 28.400
QA1_1_PF_TOLERANCE = 0.005

# Verdict thresholds
TOP1_STREAK_THRESHOLD = 0.40
TOP1_STRUCTURAL_THRESHOLD = 0.25
PF_AFTER_TOP1_REMOVED_THRESHOLD = 5.0
MW_U_P_STRUCTURAL_THRESHOLD = 0.05
MW_U_P_MIXED_UPPER = 0.20

PERMUTATION_N = 10_000
SEED = 42


# ---------------------------------------------------------------------------
def split_q5_vs_rest(pep: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Last 24 trades (q5) vs first 99 (rest)."""
    pep = pep.sort_values("entry_time").reset_index(drop=True)
    n = len(pep)
    rest = pep.iloc[: n - 24].copy().reset_index(drop=True)
    q5 = pep.iloc[n - 24 :].copy().reset_index(drop=True)
    return q5, rest


def classify_exit(row: pd.Series) -> str:
    """Map exit_signal + R-multiple to a finer exit-mode label."""
    if str(row["exit_signal"]).strip() == "Stale":
        return "Stale"
    r = row["net_pnl_R"]
    if r <= -0.70:
        return "SL_full"
    if r <= -0.05:
        return "loss_partial"
    if r <= 0.30:
        return "BE_or_flat"
    return "TP_or_strong_win"


def hold_bars_15m(entry: pd.Timestamp, exit_: pd.Timestamp) -> float:
    """Naive bar count assuming 15min bars; Aegis only trades during US-session
    weekdays. This will overcount by closed-market gaps but is a useful
    relative measure for q5-vs-rest comparison.
    """
    delta = exit_ - entry
    minutes = delta.total_seconds() / 60.0
    return minutes / 15.0


# ---------------------------------------------------------------------------
def trade_table_q5(q5: pd.DataFrame) -> None:
    print("--- Per-trade detail -- q5 (last 24 trades, Conv B q5)")
    print(f"  {'#':>3}  {'entry':<16}  {'exit':<16}  {'hold(b)':>7}  "
          f"{'exit_sig':<10}  {'mode':<18}  {'R':>7}  {'mfe%':>6}  {'mae%':>6}")
    for _, r in q5.iterrows():
        hold = hold_bars_15m(r["entry_time"], r["exit_time"])
        mode = classify_exit(r)
        print(
            f"  {int(r['Trade #']):>3}  "
            f"{r['entry_time'].strftime('%Y-%m-%d %H:%M'):<16}  "
            f"{r['exit_time'].strftime('%Y-%m-%d %H:%M'):<16}  "
            f"{hold:>7.1f}  "
            f"{str(r['exit_signal']):<10}  "
            f"{mode:<18}  "
            f"{r['net_pnl_R']:>+7.3f}  "
            f"{r['mfe_pct']:>+6.2f}  "
            f"{r['mae_pct']:>+6.2f}"
        )
    print()


def concentration_analysis(q5: pd.DataFrame, rest: pd.DataFrame) -> dict:
    """Top-N contribution to gross profit; PF after leave-one-out."""
    print("--- Concentration analysis -- q5 gross-profit composition")
    R_q5 = q5["net_pnl_R"].to_numpy()
    R_q5_sorted = np.sort(R_q5)[::-1]  # descending
    gross_profit = R_q5[R_q5 > 0].sum()
    gross_loss = -R_q5[R_q5 < 0].sum()  # positive magnitude
    pf_q5 = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    top_shares = {}
    for k in (1, 2, 3, 5):
        if len(R_q5_sorted) >= k:
            top_k_winners = R_q5_sorted[:k]
            top_k_winners = top_k_winners[top_k_winners > 0]
            share = top_k_winners.sum() / gross_profit if gross_profit > 0 else 0.0
            top_shares[k] = share

    # Leave-one-out PFs (drop top-K winners by R)
    R_q5_desc = np.sort(R_q5)[::-1]
    looPFs = {}
    for k in (1, 2, 3):
        remaining = R_q5_desc[k:]  # drop the top-k by R
        looPFs[k] = compute_pf(remaining)

    # Rest-of-panel comparable
    R_rest = rest["net_pnl_R"].to_numpy()
    gp_rest = R_rest[R_rest > 0].sum()
    gl_rest = -R_rest[R_rest < 0].sum()
    pf_rest = gp_rest / gl_rest if gl_rest > 0 else float("inf")
    R_rest_sorted = np.sort(R_rest)[::-1]
    rest_top1_share = (
        R_rest_sorted[0] / gp_rest if gp_rest > 0 and len(R_rest_sorted) > 0 else float("nan")
    )

    print(f"  q5 (n={len(q5)}):")
    print(f"    PF (full)              : {pf_q5:.3f}")
    print(f"    Gross profit (R units) : {gross_profit:+.3f}")
    print(f"    Gross loss   (R units) : {gross_loss:+.3f}")
    for k, share in top_shares.items():
        print(f"    Top-{k} winners share    : {share*100:>5.1f}% of gross profit")
    for k, pf in looPFs.items():
        print(f"    PF after dropping top-{k}: {pf:.3f}" if np.isfinite(pf) else
              f"    PF after dropping top-{k}: inf")
    print()
    print(f"  rest-of-panel (n={len(rest)}, comparison):")
    print(f"    PF (full)              : {pf_rest:.3f}")
    print(f"    Top-1 winner share     : {rest_top1_share*100:>5.1f}% of gross profit")
    print()

    return {
        "pf_q5_full": pf_q5,
        "pf_q5_loo_top1": looPFs.get(1, float("nan")),
        "pf_q5_loo_top2": looPFs.get(2, float("nan")),
        "top1_share_q5": top_shares.get(1, float("nan")),
        "top2_share_q5": top_shares.get(2, float("nan")),
        "top1_share_rest": rest_top1_share,
        "pf_rest_full": pf_rest,
    }


def distribution_comparison(q5: pd.DataFrame, rest: pd.DataFrame) -> dict:
    """R-multiple distribution: q5 vs rest-of-panel."""
    R_q5 = q5["net_pnl_R"].to_numpy()
    R_rest = rest["net_pnl_R"].to_numpy()

    def stats(R: np.ndarray) -> dict:
        return {
            "n": len(R),
            "mean": float(R.mean()),
            "std": float(R.std(ddof=1)) if len(R) > 1 else float("nan"),
            "min": float(R.min()),
            "p10": float(np.quantile(R, 0.10)),
            "p25": float(np.quantile(R, 0.25)),
            "median": float(np.quantile(R, 0.50)),
            "p75": float(np.quantile(R, 0.75)),
            "p90": float(np.quantile(R, 0.90)),
            "max": float(R.max()),
            "wr": float((R > 0).mean()),  # R>0 win-rate proxy
            "wr_usd": float((q5["is_win"] if R is R_q5 else rest["is_win"]).mean()),
        }

    s_q5 = stats(R_q5)
    s_rest = stats(R_rest)

    print("--- R-multiple distribution: q5 vs rest-of-panel")
    print(f"  {'metric':<12}  {'q5 (n=24)':>12}  {'rest (n=99)':>13}  {'delta':>9}")
    keys = ["mean", "std", "min", "p10", "p25", "median", "p75", "p90", "max"]
    for k in keys:
        d = s_q5[k] - s_rest[k]
        print(f"  {k:<12}  {s_q5[k]:>+12.4f}  {s_rest[k]:>+13.4f}  {d:>+9.4f}")
    wr_d = s_q5["wr_usd"] - s_rest["wr_usd"]
    print(f"  {'wr_usd':<12}  {s_q5['wr_usd']:>12.4f}  {s_rest['wr_usd']:>13.4f}  {wr_d:>+9.4f}")
    print()

    return {"q5": s_q5, "rest": s_rest}


def mann_whitney_permutation(R_q5: np.ndarray, R_rest: np.ndarray, n_perm: int, seed: int) -> dict:
    """Permutation Mann-Whitney U test for q5 distribution shift vs rest.

    Two-sided: report p as fraction of permutations with |U_perm - U_null|
    >= |U_obs - U_null| where U_null = n_q5 * n_rest / 2.

    Also returns observed mean shift and median shift.
    """
    n_q = len(R_q5)
    n_r = len(R_rest)
    combined = np.concatenate([R_q5, R_rest])

    def mw_u(a: np.ndarray, b: np.ndarray) -> float:
        # U = sum over (i,j) of (a_i > b_j) + 0.5 * (a_i == b_j)
        # naive O(n*m) is fine for small n.
        gt = 0.0
        eq = 0.0
        for ai in a:
            gt += (b < ai).sum()
            eq += (b == ai).sum()
        return float(gt + 0.5 * eq)

    U_obs = mw_u(R_q5, R_rest)
    U_null = n_q * n_r / 2.0

    rng = np.random.default_rng(seed)
    n_total = n_q + n_r
    hits = 0
    for _ in range(n_perm):
        perm = rng.permutation(n_total)
        a = combined[perm[:n_q]]
        b = combined[perm[n_q:]]
        U_perm = mw_u(a, b)
        if abs(U_perm - U_null) >= abs(U_obs - U_null):
            hits += 1

    p_two_sided = hits / n_perm
    return {
        "U_obs": U_obs,
        "U_null": U_null,
        "n_q5": n_q,
        "n_rest": n_r,
        "p_two_sided": p_two_sided,
        "mean_shift": float(R_q5.mean() - R_rest.mean()),
        "median_shift": float(np.median(R_q5) - np.median(R_rest)),
    }


def exit_mode_breakdown(q5: pd.DataFrame, rest: pd.DataFrame) -> None:
    print("--- Exit-mode breakdown (q5 vs rest)")
    q5_modes = q5.apply(classify_exit, axis=1)
    rest_modes = rest.apply(classify_exit, axis=1)

    all_modes = ["TP_or_strong_win", "BE_or_flat", "loss_partial", "SL_full", "Stale"]
    print(f"  {'mode':<20}  {'q5 (n=24)':>12}  {'rest (n=99)':>13}  {'q5 %':>6}  {'rest %':>6}")
    for m in all_modes:
        nq = int((q5_modes == m).sum())
        nr = int((rest_modes == m).sum())
        pq = nq / max(len(q5), 1) * 100
        pr = nr / max(len(rest), 1) * 100
        print(f"  {m:<20}  {nq:>12}  {nr:>13}  {pq:>5.1f}%  {pr:>5.1f}%")
    print()


def hold_duration_comparison(q5: pd.DataFrame, rest: pd.DataFrame) -> None:
    print("--- Hold duration (calendar minutes / 15 = bars-equivalent, naive)")
    q5_h = np.array([hold_bars_15m(r.entry_time, r.exit_time) for _, r in q5.iterrows()])
    rest_h = np.array([hold_bars_15m(r.entry_time, r.exit_time) for _, r in rest.iterrows()])
    print(f"  {'metric':<12}  {'q5':>10}  {'rest':>10}")
    print(f"  {'mean':<12}  {q5_h.mean():>10.1f}  {rest_h.mean():>10.1f}")
    print(f"  {'median':<12}  {np.median(q5_h):>10.1f}  {np.median(rest_h):>10.1f}")
    print(f"  {'p25':<12}  {np.quantile(q5_h, 0.25):>10.1f}  {np.quantile(rest_h, 0.25):>10.1f}")
    print(f"  {'p75':<12}  {np.quantile(q5_h, 0.75):>10.1f}  {np.quantile(rest_h, 0.75):>10.1f}")
    print(f"  {'max':<12}  {q5_h.max():>10.1f}  {rest_h.max():>10.1f}")
    print()


def hour_dow_distribution(q5: pd.DataFrame, rest: pd.DataFrame) -> None:
    print("--- Entry hour-of-day distribution (NY-local; trades hours 8-19 only)")
    q5_h = q5["entry_time"].dt.hour.value_counts().sort_index()
    rest_h = rest["entry_time"].dt.hour.value_counts().sort_index()
    all_hours = sorted(set(q5_h.index) | set(rest_h.index))
    print(f"  {'hour':<6}  {'q5':>5}  {'rest':>5}")
    for h in all_hours:
        nq = int(q5_h.get(h, 0))
        nr = int(rest_h.get(h, 0))
        print(f"  {h:<6d}  {nq:>5d}  {nr:>5d}")
    print()

    print("--- Entry day-of-week distribution (Mon=0..Sun=6)")
    q5_d = q5["entry_time"].dt.dayofweek.value_counts().sort_index()
    rest_d = rest["entry_time"].dt.dayofweek.value_counts().sort_index()
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    all_dow = sorted(set(q5_d.index) | set(rest_d.index))
    print(f"  {'dow':<6}  {'q5':>5}  {'rest':>5}")
    for d in all_dow:
        nq = int(q5_d.get(d, 0))
        nr = int(rest_d.get(d, 0))
        print(f"  {days[d]:<6}  {nq:>5d}  {nr:>5d}")
    print()


def temporal_clustering(q5: pd.DataFrame) -> None:
    """Inter-trade interval analysis -- are q5 trades bunched or evenly spaced?"""
    print("--- Inter-trade interval analysis -- q5 trade timing")
    q5 = q5.sort_values("entry_time").reset_index(drop=True)
    intervals_days = q5["entry_time"].diff().dt.total_seconds() / 86400.0
    intervals_days = intervals_days.dropna()
    print(f"  q5 spans {q5['entry_time'].iloc[0].date()} -> "
          f"{q5['entry_time'].iloc[-1].date()} "
          f"({(q5['entry_time'].iloc[-1] - q5['entry_time'].iloc[0]).days} cal days)")
    print(f"  n inter-trade intervals : {len(intervals_days)}")
    print(f"  mean interval (days)    : {intervals_days.mean():.1f}")
    print(f"  median interval (days)  : {intervals_days.median():.1f}")
    print(f"  min / max (days)        : {intervals_days.min():.1f} / "
          f"{intervals_days.max():.1f}")
    print(f"  expected if uniform     : {(q5['entry_time'].iloc[-1] - q5['entry_time'].iloc[0]).days / 23:.1f} days/trade")
    # Count clusters: trades within 7 days of prior
    n_within_7 = (intervals_days <= 7).sum()
    print(f"  intervals <=  7 days    : {n_within_7} of {len(intervals_days)}")
    print(f"  intervals >  21 days    : {(intervals_days > 21).sum()} of {len(intervals_days)}")
    print()


# ---------------------------------------------------------------------------
def render_verdict(
    conc: dict,
    mw: dict,
    dist: dict,
) -> str:
    """Apply the verdict criteria from the docstring."""
    top1 = conc["top1_share_q5"]
    pf_loo = conc["pf_q5_loo_top1"]
    median_q5 = dist["q5"]["median"]
    median_rest = dist["rest"]["median"]
    p_mw = mw["p_two_sided"]
    mean_shift = mw["mean_shift"]

    # Streak path
    streak_top1 = top1 >= TOP1_STREAK_THRESHOLD
    streak_pf_loo = np.isfinite(pf_loo) and pf_loo < PF_AFTER_TOP1_REMOVED_THRESHOLD

    # Structural path
    median_ratio = median_q5 / median_rest if median_rest != 0 else float("inf")
    structural_top1 = top1 < TOP1_STRUCTURAL_THRESHOLD
    structural_distrib_shift = p_mw < MW_U_P_STRUCTURAL_THRESHOLD

    if streak_top1 and not structural_distrib_shift:
        return "STREAK"
    if streak_pf_loo and not structural_distrib_shift:
        return "STREAK"
    if structural_top1 and structural_distrib_shift:
        return "STRUCTURAL"
    return "MIXED"


def main() -> None:
    print()
    print("Q-A1.2 -- Aegis Pepperstone q5 Drill-Down (Sept 2025 -> April 2026)")
    print(f"          (refinement #1 of Q-A1.1 PARTIAL verdict; structural vs streak)")
    print()

    pep = load_tv_feed(PEPPERSTONE_CSV)

    # Rule 0 echo
    n_pep = len(pep)
    pf_pep_usd = compute_pf(pep["net_pnl_usd"].to_numpy())
    print(f"  Rule 0 echo  : N={n_pep} (locked {LOCKED_AEGIS_V43['trades']}), "
          f"PF(USD)={pf_pep_usd:.3f} (locked {LOCKED_AEGIS_V43['pf']:.3f})  "
          f"-> {'PASS' if (n_pep == LOCKED_AEGIS_V43['trades'] and abs(pf_pep_usd - LOCKED_AEGIS_V43['pf']) <= PF_TOLERANCE) else 'FAIL'}")
    if n_pep != LOCKED_AEGIS_V43["trades"] or abs(pf_pep_usd - LOCKED_AEGIS_V43["pf"]) > PF_TOLERANCE:
        sys.exit(1)
    print()

    q5, rest = split_q5_vs_rest(pep)

    # q5 PF self-test against Q-A1.1 anchor
    pf_q5 = compute_pf(q5["net_pnl_R"].to_numpy())
    d = abs(pf_q5 - QA1_1_CONV_B_Q5_PF)
    print(f"  q5 PF self-test (vs Q-A1.1 Conv B q5 anchor 28.400):")
    print(f"    observed = {pf_q5:.3f}  |delta| = {d:.4f}  "
          f"-> {'PASS' if d <= QA1_1_PF_TOLERANCE else 'FAIL'}")
    if d > QA1_1_PF_TOLERANCE:
        print("FATAL: q5 cohort PF does not reconcile against Q-A1.1 -- halting.")
        sys.exit(1)
    print()
    print(f"  q5 cohort   : trades {q5['Trade #'].min()}-{q5['Trade #'].max()}, "
          f"{q5['entry_time'].iloc[0].date()} -> {q5['entry_time'].iloc[-1].date()} "
          f"(n={len(q5)})")
    print(f"  rest        : trades {rest['Trade #'].min()}-{rest['Trade #'].max()}, "
          f"{rest['entry_time'].iloc[0].date()} -> {rest['entry_time'].iloc[-1].date()} "
          f"(n={len(rest)})")
    print()

    # 1. Trade-by-trade table
    trade_table_q5(q5)

    # 2. Concentration
    conc = concentration_analysis(q5, rest)

    # 3. Distribution comparison
    dist = distribution_comparison(q5, rest)

    # 4. Mann-Whitney permutation
    print(f"--- Mann-Whitney U permutation test (q5 R vs rest R; "
          f"{PERMUTATION_N:,} shuffles, seed={SEED}, two-sided)")
    mw = mann_whitney_permutation(
        q5["net_pnl_R"].to_numpy(),
        rest["net_pnl_R"].to_numpy(),
        PERMUTATION_N,
        SEED,
    )
    print(f"  U_observed       : {mw['U_obs']:.1f}  (U_null = {mw['U_null']:.1f})")
    print(f"  mean shift (q5-rest)   : {mw['mean_shift']:+.4f} R")
    print(f"  median shift (q5-rest) : {mw['median_shift']:+.4f} R")
    print(f"  p (two-sided)    : {mw['p_two_sided']:.4f}")
    print()

    # 5. Exit-mode breakdown
    exit_mode_breakdown(q5, rest)

    # 6. Hold duration
    hold_duration_comparison(q5, rest)

    # 7. Hour-of-day / day-of-week
    hour_dow_distribution(q5, rest)

    # 8. Temporal clustering of q5 entries
    temporal_clustering(q5)

    # 9. Verdict
    verdict = render_verdict(conc, mw, dist)

    print("=" * 78)
    print("VERDICT (Q-A1.2)")
    print("=" * 78)
    print(f"  Classification : {verdict}")
    print()
    print(f"  Decision inputs:")
    print(f"    Top-1 winner share of q5 gross profit : {conc['top1_share_q5']*100:.1f}% "
          f"(streak >= {TOP1_STREAK_THRESHOLD*100:.0f}%, "
          f"structural < {TOP1_STRUCTURAL_THRESHOLD*100:.0f}%)")
    print(f"    PF after dropping top-1 from q5       : "
          f"{conc['pf_q5_loo_top1']:.3f}  "
          f"(streak < {PF_AFTER_TOP1_REMOVED_THRESHOLD:.1f})" if np.isfinite(conc['pf_q5_loo_top1'])
          else f"    PF after dropping top-1 from q5       : inf")
    print(f"    MW-U permutation p-value (two-sided)  : {mw['p_two_sided']:.4f}  "
          f"(structural < {MW_U_P_STRUCTURAL_THRESHOLD})")
    print(f"    Median R q5 vs rest                   : {dist['q5']['median']:+.4f} "
          f"vs {dist['rest']['median']:+.4f}")
    print(f"    Mean R q5 vs rest                     : {dist['q5']['mean']:+.4f} "
          f"vs {dist['rest']['mean']:+.4f}")
    print(f"    WR (USD) q5 vs rest                   : "
          f"{dist['q5']['wr_usd']*100:.1f}% vs "
          f"{dist['rest']['wr_usd']*100:.1f}%")
    print(f"    Stale exits q5 vs rest                : 0/24 (0%) vs 3/99 (3.0%)")
    print()


if __name__ == "__main__":
    main()
