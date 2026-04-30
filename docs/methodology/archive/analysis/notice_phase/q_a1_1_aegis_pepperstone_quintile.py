"""Q-A1.1 -- Aegis Pepperstone Panel-Quintile Replication Test.

Refinement #1 from Q-A1's PARTIAL verdict: tests whether the monotonic PF
lift pattern (replicated qualitatively but failing the strict perm-p<0.05
threshold at tertile resolution) holds at finer resolution (quintile).

Same data, same loader, no re-MC required. Out of scope: any allocation,
dd_protection, MC calibration, Notion, or Pine code change.

Methodology:
  - Convention A: calendar-year quintile -- one calendar year per bin
    (2022 / 2023 / 2024 / 2025 / 2026, n = 13 / 31 / 28 / 41 / 10).
    Aggregation self-test: q1+q2 / q3 / q4+q5 must reproduce Q-A1 Conv A
    tertile PFs (2.468 / 4.500 / 5.561) exactly (within numerical
    precision), since aggregating gross-pos / gross-neg sums gives
    identical PF.
  - Convention B: equal-N trade-index quintile -- sort by entry_time, split
    into 5 most-even bins (24 / 25 / 25 / 25 / 24 for N=123). Self-test:
    column sums reconcile to panel (sum n = 123, sum sum_R = panel sum_R).

  - Verdict criteria (per convention, generalized for 5 bins):
      Spearman rank correlation between bin index (1..5) and per-bin PF.
      Permutation test on Spearman: shuffle trade R, recompute per-bin PFs
      and Spearman, p-value = fraction with Spearman >= observed AND
      PF_q5/PF_q1 >= observed ratio. Pepperstone only (Q-A1 scope rationale:
      Pepperstone is the canonical hypothesis-test target; OANDA is fixed
      reference).
        - Replication        : Spearman > 0.5, perm p < 0.05, ratio >= 2.0
        - Non-replication    : Spearman <= 0 (flat or declining)
                               OR ratio < 1.3 OR strictly-decreasing
                               (Spearman = -1) -> monotonic-decline flag
        - Partial            : anything else
  - Combined verdict: dual-convention rule from Q-A1 (both replicate ->
    CONFIRMED; both non-replicate -> NON-REPLICATION; else PARTIAL).

Run: python analysis/notice_phase/q_a1_1_aegis_pepperstone_quintile.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Reuse Q-A1's loader, constants, and PF computation -- single source of truth.
HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent))

from q_a1_aegis_pepperstone_panel import (  # noqa: E402
    load_tv_feed,
    compute_pf,
    PEPPERSTONE_CSV,
    OANDA_CSV,
    LOCKED_AEGIS_V43,
    PF_TOLERANCE,
    RISK_PCT_AEGIS,
)

# Q-A1 Conv A tertile PFs on Pepperstone (computed verbatim from Q-A1 run).
# These are the aggregation self-test target.
QA1_CONV_A_PEP_TERTILE_PFS = {"early": 2.468, "mid": 4.500, "late": 5.561}
# Q-A1 Conv B tertile PFs on Pepperstone (column-sum cross-check anchor).
QA1_CONV_B_PEP_TERTILE_PFS = {"early": 2.535, "mid": 3.620, "late": 7.324}

AGG_SELF_TEST_TOLERANCE = 0.005  # |delta| per per-tertile PF after quintile->tertile aggregation

BOOTSTRAP_N = 10_000
PERMUTATION_N = 10_000
SEED = 42


# ---------------------------------------------------------------------------
def split_convention_a_quintile(df: pd.DataFrame) -> list[pd.DataFrame]:
    """Convention A -- calendar-year quintile.

    q1 == 2022, q2 == 2023, q3 == 2024, q4 == 2025, q5 == 2026.
    """
    yr = df["entry_time"].dt.year
    return [df[yr == y].copy() for y in (2022, 2023, 2024, 2025, 2026)]


def split_convention_b_quintile(df: pd.DataFrame) -> list[pd.DataFrame]:
    """Convention B -- equal-N trade-index quintile.

    For N=123: bin sizes 24 / 25 / 25 / 25 / 24 (most-even split).
    Implementation: numpy.array_split returns the most-even partition.
    """
    n = len(df)
    indices = np.array_split(np.arange(n), 5)
    return [df.iloc[idx].copy() for idx in indices]


# ---------------------------------------------------------------------------
def per_bin_metrics(b: pd.DataFrame, label: str) -> dict:
    r = b["net_pnl_R"].to_numpy()
    return {
        "label": label,
        "n": int(len(b)),
        "pf": compute_pf(r),
        "win_rate": float(b["is_win"].mean()) if len(b) else float("nan"),
        "mean_R": float(r.mean()) if len(r) else float("nan"),
        "median_R": float(np.median(r)) if len(r) else float("nan"),
        "ret_std": float(r.std(ddof=1)) if len(r) > 1 else float("nan"),
        "sum_R": float(r.sum()),
        "n_wins": int(b["is_win"].sum()),
        "date_lo": b["entry_time"].min() if len(b) else None,
        "date_hi": b["entry_time"].max() if len(b) else None,
    }


def bootstrap_pf_ci(r: np.ndarray, n_boot: int, seed: int, ci: float = 0.95) -> tuple[float, float]:
    if len(r) == 0:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    pfs = np.empty(n_boot)
    n = len(r)
    for i in range(n_boot):
        sample = rng.choice(r, size=n, replace=True)
        pfs[i] = compute_pf(sample)
    finite = pfs[np.isfinite(pfs)]
    if len(finite) == 0:
        return (float("nan"), float("nan"))
    lo = float(np.quantile(finite, (1 - ci) / 2))
    hi = float(np.quantile(finite, 1 - (1 - ci) / 2))
    return (lo, hi)


def spearman_rank_corr(x: np.ndarray, y: np.ndarray) -> float:
    """Spearman rank correlation between x and y. Returns NaN if undefined."""
    if len(x) != len(y) or len(x) < 2:
        return float("nan")
    rx = pd.Series(x).rank().to_numpy()
    ry = pd.Series(y).rank().to_numpy()
    rx_m, ry_m = rx.mean(), ry.mean()
    cov = ((rx - rx_m) * (ry - ry_m)).mean()
    sx, sy = rx.std(ddof=0), ry.std(ddof=0)
    if sx == 0 or sy == 0:
        return float("nan")
    return float(cov / (sx * sy))


def permutation_test_spearman(
    df: pd.DataFrame,
    splitter,
    n_perm: int,
    seed: int,
) -> dict:
    """Permutation test: under H0 of i.i.d. R across the panel, how often
    does a random shuffle produce Spearman(bin_idx, PF) >= observed AND
    PF_q5 / PF_q1 >= observed ratio?

    Bin sizes are preserved (we permute R values across the trade index,
    keeping n per bin fixed).
    """
    bins0 = splitter(df)
    pfs0 = np.array([compute_pf(b["net_pnl_R"].to_numpy()) for b in bins0])
    bin_idx = np.arange(1, len(bins0) + 1, dtype=float)
    spearman0 = spearman_rank_corr(bin_idx, pfs0)
    ratio0 = pfs0[-1] / pfs0[0] if pfs0[0] > 0 and np.isfinite(pfs0[-1]) else float("nan")
    monotonic0 = bool(np.all(np.diff(pfs0) > 0))
    decline_strict = bool(np.all(np.diff(pfs0) < 0))

    bin_sizes = [len(b) for b in bins0]
    rng = np.random.default_rng(seed)
    R_all = df["net_pnl_R"].to_numpy()
    n_total = len(R_all)
    hits_spearman_only = 0
    hits_joint = 0
    for _ in range(n_perm):
        perm = rng.permutation(n_total)
        R_shuffled = R_all[perm]
        offset = 0
        pfs = np.empty(len(bin_sizes))
        for i, sz in enumerate(bin_sizes):
            pfs[i] = compute_pf(R_shuffled[offset:offset + sz])
            offset += sz
        sp = spearman_rank_corr(bin_idx, pfs)
        if not np.isfinite(sp):
            continue
        if sp >= spearman0:
            hits_spearman_only += 1
            ratio = pfs[-1] / pfs[0] if pfs[0] > 0 and np.isfinite(pfs[-1]) else float("inf")
            if np.isfinite(ratio0) and ratio >= ratio0:
                hits_joint += 1

    return {
        "observed_pfs": pfs0.tolist(),
        "observed_spearman": spearman0,
        "observed_ratio_q5_over_q1": ratio0,
        "observed_strictly_monotonic_increase": monotonic0,
        "observed_strictly_monotonic_decline": decline_strict,
        "p_value_spearman_only": hits_spearman_only / n_perm,
        "p_value_joint_spearman_and_ratio": hits_joint / n_perm,
        "n_perm": n_perm,
    }


# ---------------------------------------------------------------------------
def aggregation_self_test_conv_a(pep: pd.DataFrame) -> None:
    """Conv A self-test: aggregate q1+q2 / q3 / q4+q5 -> reproduce Q-A1 tertiles."""
    bins = split_convention_a_quintile(pep)
    early = pd.concat([bins[0], bins[1]])  # 2022 + 2023
    mid = bins[2]                            # 2024
    late = pd.concat([bins[3], bins[4]])    # 2025 + 2026

    pfs = {
        "early": compute_pf(early["net_pnl_R"].to_numpy()),
        "mid": compute_pf(mid["net_pnl_R"].to_numpy()),
        "late": compute_pf(late["net_pnl_R"].to_numpy()),
    }

    print("--- Conv A self-test: aggregate q1+q2 / q3 / q4+q5 -> Q-A1 Conv A tertiles")
    print(f"  {'tertile':<10}  {'n agg':>5}  {'observed':>9}  {'Q-A1':>9}  "
          f"{'|delta|':>8}  result")
    fail = False
    n_agg = {"early": len(early), "mid": len(mid), "late": len(late)}
    for k, target in QA1_CONV_A_PEP_TERTILE_PFS.items():
        obs = pfs[k]
        d = abs(obs - target)
        passed = d <= AGG_SELF_TEST_TOLERANCE
        if not passed:
            fail = True
        print(f"  {k:<10}  {n_agg[k]:>5}  {obs:>9.3f}  {target:>9.3f}  "
              f"{d:>8.4f}  {'PASS' if passed else 'FAIL'}")
    print()
    print(f"  n aggregated (Pep Conv A): early=44 (q1+q2={n_agg['early']}), "
          f"mid=28 (q3={n_agg['mid']}), late=51 (q4+q5={n_agg['late']})")
    print(f"  expected match: 44 / 28 / 51 from Q-A1")
    print()
    if fail:
        print("FATAL: Conv A aggregation self-test failed -- halting. Indicates a")
        print("       loader / split-logic divergence between Q-A1 and Q-A1.1.")
        sys.exit(1)
    print("  Conv A self-test status: PASS")
    print()


def column_sum_self_test_conv_b(pep: pd.DataFrame) -> None:
    """Conv B self-test: column-sum reconciliation against the panel."""
    bins = split_convention_b_quintile(pep)
    n_total = sum(len(b) for b in bins)
    sum_R_quintile = sum(b["net_pnl_R"].sum() for b in bins)
    sum_R_panel = float(pep["net_pnl_R"].sum())
    n_wins_quintile = sum(int(b["is_win"].sum()) for b in bins)
    n_wins_panel = int(pep["is_win"].sum())

    print("--- Conv B self-test: column-sum reconciliation (quintile -> panel)")
    print(f"  {'metric':<24}  {'quintile sum':>14}  {'panel':>14}  result")
    bin_sizes = [len(b) for b in bins]
    checks = [
        ("n_trades", n_total, len(pep), n_total == len(pep)),
        ("sum_R", sum_R_quintile, sum_R_panel,
         abs(sum_R_quintile - sum_R_panel) < 1e-9),
        ("n_wins", n_wins_quintile, n_wins_panel, n_wins_quintile == n_wins_panel),
    ]
    fail = False
    for name, q, p, ok in checks:
        if isinstance(q, float):
            print(f"  {name:<24}  {q:>14.6f}  {p:>14.6f}  "
                  f"{'PASS' if ok else 'FAIL'}")
        else:
            print(f"  {name:<24}  {q:>14d}  {p:>14d}  "
                  f"{'PASS' if ok else 'FAIL'}")
        if not ok:
            fail = True
    print(f"  bin sizes (Conv B)        : {' / '.join(str(s) for s in bin_sizes)}")
    print()
    if fail:
        print("FATAL: Conv B column-sum self-test failed -- halting.")
        sys.exit(1)
    print("  Conv B self-test status: PASS")
    print()


# ---------------------------------------------------------------------------
def per_bin_table(rows: list[dict], title: str) -> None:
    print(f"--- {title}")
    print(f"  {'Bin':<8}  {'n':>3}  {'PF':>7}  {'WR%':>5}  {'meanR':>7}  "
          f"{'medR':>7}  {'retstd':>7}  {'sumR':>7}  date range")
    for r in rows:
        date_str = (
            f"{r['date_lo'].date()} -> {r['date_hi'].date()}"
            if r["date_lo"] is not None else "--"
        )
        pf_str = f"{r['pf']:>7.3f}" if np.isfinite(r["pf"]) else "    inf"
        print(f"  {r['label']:<8}  {r['n']:>3}  {pf_str}  "
              f"{r['win_rate']*100:>5.2f}  {r['mean_R']:>+7.3f}  "
              f"{r['median_R']:>+7.3f}  {r['ret_std']:>7.4f}  {r['sum_R']:>+7.3f}  "
              f"{date_str}")
    print()


# ---------------------------------------------------------------------------
def classify_replication_quintile(
    pfs: list[float],
    spearman: float,
    perm_p_joint: float,
    ratio: float,
) -> tuple[str, bool]:
    """Per-convention 5-bin classification + monotonic-decline flag.

    decline_flag = True iff PF strictly decreases across all 5 bins.
    """
    decline_strict = all(pfs[i] > pfs[i + 1] for i in range(len(pfs) - 1))

    if not all(np.isfinite([*pfs, spearman, perm_p_joint, ratio])):
        return ("partial", decline_strict)

    # Replication: positive monotonic signal AND meets ratio bar AND p < 0.05
    if spearman > 0.5 and ratio >= 2.0 and perm_p_joint < 0.05:
        return ("replication", decline_strict)

    # Non-replication: flat / declining / well-shy of ratio
    if spearman <= 0 or ratio < 1.3 or decline_strict:
        return ("non_replication", decline_strict)

    return ("partial", decline_strict)


def combine_verdicts(class_a: str, class_b: str) -> str:
    if class_a == "replication" and class_b == "replication":
        return "REPLICATION CONFIRMED"
    if class_a == "non_replication" and class_b == "non_replication":
        return "NON-REPLICATION"
    return "PARTIAL"


# ---------------------------------------------------------------------------
def run_convention(
    df: pd.DataFrame,
    splitter,
    labels: list[str],
    feed_label: str,
    convention_label: str,
    do_bootstrap: bool,
    do_permutation: bool,
) -> dict:
    bins = splitter(df)
    rows = [per_bin_metrics(b, lbl) for b, lbl in zip(bins, labels)]
    out: dict = {"rows": rows, "feed": feed_label, "convention": convention_label}

    if do_bootstrap:
        boot = []
        for lbl, b in zip(labels, bins):
            r = b["net_pnl_R"].to_numpy()
            lo, hi = bootstrap_pf_ci(r, BOOTSTRAP_N, seed=SEED)
            boot.append({"label": lbl, "pf_ci_lo": lo, "pf_ci_hi": hi, "n": len(r)})
        out["bootstrap"] = boot

    if do_permutation:
        out["permutation"] = permutation_test_spearman(df, splitter, PERMUTATION_N, seed=SEED)

    return out


# ---------------------------------------------------------------------------
def main() -> None:
    print()
    print("Q-A1.1 -- Aegis Pepperstone Panel-Quintile Replication Test")
    print(f"          (refinement of Q-A1 PARTIAL verdict; quintile resolution)")
    print()

    pep = load_tv_feed(PEPPERSTONE_CSV)
    oanda = load_tv_feed(OANDA_CSV)

    # Brief Rule 0 echo (Q-A1 already gated on this; just verify N + USD-PF)
    n_pep = len(pep)
    pf_pep_usd = compute_pf(pep["net_pnl_usd"].to_numpy())
    print(f"  Rule 0 echo  : N={n_pep} (locked {LOCKED_AEGIS_V43['trades']}), "
          f"PF(USD)={pf_pep_usd:.3f} (locked {LOCKED_AEGIS_V43['pf']:.3f})  "
          f"-> {'PASS' if (n_pep == LOCKED_AEGIS_V43['trades'] and abs(pf_pep_usd - LOCKED_AEGIS_V43['pf']) <= PF_TOLERANCE) else 'FAIL'}")
    if n_pep != LOCKED_AEGIS_V43["trades"] or abs(pf_pep_usd - LOCKED_AEGIS_V43["pf"]) > PF_TOLERANCE:
        print("FATAL: Pepperstone Rule 0 echo failed -- halting.")
        sys.exit(1)
    print()

    # Self-tests
    aggregation_self_test_conv_a(pep)
    column_sum_self_test_conv_b(pep)

    # Convention A
    print("=" * 78)
    print("Convention A -- calendar-year quintile (1 year per bin)")
    print("           q1=2022, q2=2023, q3=2024, q4=2025, q5=2026")
    print("=" * 78)
    print()

    labels_a = ["q1=2022", "q2=2023", "q3=2024", "q4=2025", "q5=2026"]
    pep_a = run_convention(pep, split_convention_a_quintile, labels_a,
                           "Pepperstone", "A", do_bootstrap=True, do_permutation=True)
    oanda_a = run_convention(oanda, split_convention_a_quintile, labels_a,
                             "OANDA", "A", do_bootstrap=False, do_permutation=False)

    per_bin_table(oanda_a["rows"], "Per-quintile -- OANDA -- Convention A (reference)")
    per_bin_table(pep_a["rows"], "Per-quintile -- Pepperstone -- Convention A")

    print(f"--- Bootstrap 95% CI on PF -- Pepperstone -- Conv A "
          f"({BOOTSTRAP_N:,} resamples, seed={SEED})")
    print(f"  {'Bin':<8}  {'n':>3}  {'CI_lo':>7}  {'CI_hi':>7}")
    for b in pep_a["bootstrap"]:
        print(f"  {b['label']:<8}  {b['n']:>3}  {b['pf_ci_lo']:>7.3f}  {b['pf_ci_hi']:>7.3f}")
    print()

    perm_a = pep_a["permutation"]
    print(f"--- Spearman permutation -- Pepperstone -- Conv A "
          f"({PERMUTATION_N:,} shuffles, seed={SEED})")
    pfs_a = perm_a["observed_pfs"]
    print(f"  observed PFs              : "
          f"{pfs_a[0]:.3f} / {pfs_a[1]:.3f} / {pfs_a[2]:.3f} / "
          f"{pfs_a[3]:.3f} / {pfs_a[4]:.3f}")
    print(f"  observed Spearman         : {perm_a['observed_spearman']:+.3f}")
    ratio_a = perm_a["observed_ratio_q5_over_q1"]
    print(f"  PF_q5 / PF_q1             : "
          f"{ratio_a:.3f}" if np.isfinite(ratio_a) else f"  PF_q5 / PF_q1             : {ratio_a}")
    print(f"  strictly monotonic ^      : {perm_a['observed_strictly_monotonic_increase']}")
    print(f"  strictly monotonic v      : {perm_a['observed_strictly_monotonic_decline']}")
    print(f"  p (Spearman >= obs)       : {perm_a['p_value_spearman_only']:.4f}")
    print(f"  p (Spearman AND ratio)    : {perm_a['p_value_joint_spearman_and_ratio']:.4f}")
    print()

    # Convention B
    print("=" * 78)
    print("Convention B -- equal-N trade-index quintile")
    print("           bin sizes 24 / 25 / 25 / 25 / 24 (most-even split for N=123)")
    print("=" * 78)
    print()

    labels_b = ["q1", "q2", "q3", "q4", "q5"]
    pep_b = run_convention(pep, split_convention_b_quintile, labels_b,
                           "Pepperstone", "B", do_bootstrap=True, do_permutation=True)
    oanda_b = run_convention(oanda, split_convention_b_quintile, labels_b,
                             "OANDA", "B", do_bootstrap=False, do_permutation=False)

    per_bin_table(oanda_b["rows"], "Per-quintile -- OANDA -- Convention B (reference)")
    per_bin_table(pep_b["rows"], "Per-quintile -- Pepperstone -- Convention B")

    print(f"--- Bootstrap 95% CI on PF -- Pepperstone -- Conv B "
          f"({BOOTSTRAP_N:,} resamples, seed={SEED})")
    print(f"  {'Bin':<8}  {'n':>3}  {'CI_lo':>7}  {'CI_hi':>7}")
    for b in pep_b["bootstrap"]:
        print(f"  {b['label']:<8}  {b['n']:>3}  {b['pf_ci_lo']:>7.3f}  {b['pf_ci_hi']:>7.3f}")
    print()

    perm_b = pep_b["permutation"]
    print(f"--- Spearman permutation -- Pepperstone -- Conv B "
          f"({PERMUTATION_N:,} shuffles, seed={SEED})")
    pfs_b = perm_b["observed_pfs"]
    print(f"  observed PFs              : "
          f"{pfs_b[0]:.3f} / {pfs_b[1]:.3f} / {pfs_b[2]:.3f} / "
          f"{pfs_b[3]:.3f} / {pfs_b[4]:.3f}")
    print(f"  observed Spearman         : {perm_b['observed_spearman']:+.3f}")
    ratio_b = perm_b["observed_ratio_q5_over_q1"]
    print(f"  PF_q5 / PF_q1             : "
          f"{ratio_b:.3f}" if np.isfinite(ratio_b) else f"  PF_q5 / PF_q1             : {ratio_b}")
    print(f"  strictly monotonic ^      : {perm_b['observed_strictly_monotonic_increase']}")
    print(f"  strictly monotonic v      : {perm_b['observed_strictly_monotonic_decline']}")
    print(f"  p (Spearman >= obs)       : {perm_b['p_value_spearman_only']:.4f}")
    print(f"  p (Spearman AND ratio)    : {perm_b['p_value_joint_spearman_and_ratio']:.4f}")
    print()

    # Verdict
    class_a, decline_a = classify_replication_quintile(
        pfs_a, perm_a["observed_spearman"], perm_a["p_value_joint_spearman_and_ratio"], ratio_a,
    )
    class_b, decline_b = classify_replication_quintile(
        pfs_b, perm_b["observed_spearman"], perm_b["p_value_joint_spearman_and_ratio"], ratio_b,
    )
    verdict = combine_verdicts(class_a, class_b)

    print("=" * 78)
    print("VERDICT -- dual-convention routing rule (5-bin Spearman generalization)")
    print("=" * 78)
    print(f"  Convention A  : {class_a}")
    print(f"  Convention B  : {class_b}")
    print(f"  Combined      : {verdict}")
    if decline_a:
        print("  *** STRICT MONOTONIC DECLINE -- Conv A on Pepperstone")
    if decline_b:
        print("  *** STRICT MONOTONIC DECLINE -- Conv B on Pepperstone")
    print()

    print("=" * 78)
    print("CONSOLE SUMMARY")
    print("=" * 78)
    print(f"  VERDICT (Q-A1.1)              : {verdict}")
    print(f"  Pep Conv A quintile PFs       : "
          f"{pfs_a[0]:.2f} / {pfs_a[1]:.2f} / {pfs_a[2]:.2f} / "
          f"{pfs_a[3]:.2f} / {pfs_a[4]:.2f}")
    print(f"     Spearman = {perm_a['observed_spearman']:+.2f}, "
          f"q5/q1 = {ratio_a:.2f}, "
          f"p_joint = {perm_a['p_value_joint_spearman_and_ratio']:.4f}")
    print(f"  Pep Conv B quintile PFs       : "
          f"{pfs_b[0]:.2f} / {pfs_b[1]:.2f} / {pfs_b[2]:.2f} / "
          f"{pfs_b[3]:.2f} / {pfs_b[4]:.2f}")
    print(f"     Spearman = {perm_b['observed_spearman']:+.2f}, "
          f"q5/q1 = {ratio_b:.2f}, "
          f"p_joint = {perm_b['p_value_joint_spearman_and_ratio']:.4f}")
    print(f"  Q-A1 tertile recap (Pep Conv A): 2.47 / 4.50 / 5.56  "
          f"ratio=2.25  perm_p=0.0667")
    print(f"  Q-A1 tertile recap (Pep Conv B): 2.54 / 3.62 / 7.32  "
          f"ratio=2.89  perm_p=0.0559")
    if decline_a or decline_b:
        flags = []
        if decline_a:
            flags.append("Conv A")
        if decline_b:
            flags.append("Conv B")
        print(f"  *** STRICT MONOTONIC DECLINE  : {', '.join(flags)}")
    print()


if __name__ == "__main__":
    main()
