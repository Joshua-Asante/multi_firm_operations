"""MSEE H8 — Invasion-fitness battery for new-strategy candidates.

Q-MSEE-8 from docs/methodology/msee/open_questions.md.

For any candidate strategy, evaluates three things:

  (a) Standalone fitness:
        - Daily R Sharpe (annualized)
        - Daily R win-rate
        - Daily R PF
        - Realized max drawdown on portfolio-equity scale at proposed
          allocation
  (b) Normal-regime correlation matrix to existing G/S/A
  (c) Stress-regime correlation matrix to existing G/S/A
        (stress-day flag from h6c_conditional_correlations.py)

Reject criterion (P9): stress-regime correlation to ANY existing
strategy > 0.3 — even if normal-regime correlation is near zero. The
ecological rationale: a candidate that becomes correlated under stress
defeats the storage-effect benefit precisely when it is most needed.

Usage:
    python analysis/msee/h8_invasion_fitness.py \\
        --candidate path/to/candidate_daily_R.csv \\
        --candidate-name <name> \\
        --proposed-alloc 0.005

The candidate CSV must contain columns ['date', 'R'] where R is the
strategy's daily R-multiple sum (compatible with the foundation
primitive's per-strategy R semantics).

PRE-Q GATE:
  D: Restricted to candidates whose backtest passed the project's
     existing Phase-0 verification (otherwise H8 is wasted on bad data).
  S: Three correlation matrices (full, normal, stress).
  A: O(seconds).

Reproducibility: `python analysis/msee/h8_invasion_fitness.py [--demo]`
The --demo flag generates a synthetic candidate to verify the battery
runs end-to-end; replace with --candidate <csv> for real candidates.
"""
from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "identify" / "2026-04-26"))

from common import STRATEGIES, PARAMS, load_bars  # noqa: E402

DAILY_CSV = ROOT / "analysis" / "msee" / "daily_strategy_returns.csv"
OUT_JSON = ROOT / "analysis" / "msee" / "h8_invasion_fitness.json"

ANNUALIZE = np.sqrt(252)
STRESS_PCTILE = 0.95
STRESS_THRESHOLD_R = 0.30  # reject criterion

INSTRUMENT_BAR = {
    "guardian": "XAUUSD",
    "striker": "US30USD",
    "aegis": "USDJPY",
}


def stress_flag_series() -> pd.DataFrame:
    """Reproduce the H6c stress flag on the same bar corpus."""
    out = None
    for s, sym in INSTRUMENT_BAR.items():
        bars = load_bars(sym)
        bars["date"] = bars.index.normalize().date
        daily_close = bars.groupby("date")["close"].last()
        ret = daily_close.pct_change().rename(f"{s}_idx_ret")
        out = ret.to_frame() if out is None else out.join(ret, how="outer")
    out["stress_proxy"] = out.abs().max(axis=1)
    threshold = float(np.nanpercentile(out["stress_proxy"].dropna(),
                                       STRESS_PCTILE * 100))
    out["is_stress"] = (out["stress_proxy"] >= threshold).astype(int)
    out.attrs["stress_threshold"] = threshold
    return out.reset_index().rename(columns={"index": "date"})


def standalone_fitness(candidate: pd.DataFrame, alloc: float) -> dict:
    r = candidate["R"]
    contrib = r * alloc
    cum = contrib.cumsum().values
    peak = np.maximum.accumulate(cum)
    max_dd = float((peak - cum).max())
    wins = r[r > 0].sum()
    losses = -r[r < 0].sum()
    n = len(r)
    return {
        "n_days": int(n),
        "sum_R": float(r.sum()),
        "mean_daily_R": float(r.mean()),
        "std_daily_R": float(r.std(ddof=1)) if n > 1 else float("nan"),
        "annualized_R_sharpe": (float((r.mean() / r.std(ddof=1)) * ANNUALIZE)
                                if n > 1 and r.std(ddof=1) > 0 else float("nan")),
        "win_rate": float((r > 0).mean()),
        "profit_factor": (float(wins / losses) if losses > 0 else float("inf")),
        "proposed_alloc_w": float(alloc),
        "realized_max_dd_at_alloc_pct": max_dd,
    }


def correlation_matrix(candidate: pd.DataFrame, existing: pd.DataFrame,
                       label: str) -> dict:
    """Pairwise candidate-to-existing correlations on shared dates."""
    cand = candidate[["date", "R"]].rename(columns={"R": "R_cand"})
    df = cand.merge(existing, on="date", how="inner")
    n = len(df)
    out = {"label": label, "n_days": int(n), "candidate_vs_existing": {}}
    if n < 5:
        for s in STRATEGIES:
            out["candidate_vs_existing"][s] = {"r": float("nan"),
                                               "n": int(n)}
        return out
    for s in STRATEGIES:
        a = df["R_cand"].values
        b = df[f"{s}_R"].values
        if np.std(a) == 0 or np.std(b) == 0:
            r = float("nan")
        else:
            r = float(np.corrcoef(a, b)[0, 1])
        out["candidate_vs_existing"][s] = {"r": r, "n": int(n)}
    return out


def evaluate_candidate(candidate: pd.DataFrame, name: str,
                       proposed_alloc: float) -> dict:
    candidate = candidate.copy()
    candidate["date"] = pd.to_datetime(candidate["date"]).dt.date

    existing = pd.read_csv(DAILY_CSV, parse_dates=["exit_date_ny"])
    existing["date"] = existing["exit_date_ny"].dt.date

    stress = stress_flag_series()
    stress["date"] = pd.to_datetime(stress["date"]).dt.date

    # Align candidate to existing date axis (inner join).
    cand_aligned = candidate.merge(
        existing[["date"] + [f"{s}_R" for s in STRATEGIES]],
        on="date", how="inner",
    )

    # Standalone fitness on candidate's own date axis (unaligned).
    standalone = standalone_fitness(candidate, proposed_alloc)
    standalone_aligned = standalone_fitness(cand_aligned[["date", "R"]],
                                            proposed_alloc)

    full = correlation_matrix(candidate, existing, "full")

    # Stress / calm slices.
    cand_with_stress = candidate.merge(stress[["date", "is_stress"]],
                                       on="date", how="inner")
    cand_stress = cand_with_stress[cand_with_stress["is_stress"] == 1]
    cand_calm = cand_with_stress[cand_with_stress["is_stress"] == 0]

    stress_corr = correlation_matrix(cand_stress, existing, "stress")
    calm_corr = correlation_matrix(cand_calm, existing, "calm")

    # Reject criterion.
    rejected_pairs = []
    for s in STRATEGIES:
        r = stress_corr["candidate_vs_existing"][s]["r"]
        if r is not None and not np.isnan(r) and r > STRESS_THRESHOLD_R:
            rejected_pairs.append({"existing_strategy": s, "stress_r": r})

    accepted = (len(rejected_pairs) == 0
                and standalone["annualized_R_sharpe"] > 0)

    return {
        "candidate_name": name,
        "proposed_alloc": proposed_alloc,
        "standalone_fitness_full_axis": standalone,
        "standalone_fitness_overlap_with_existing_panel": standalone_aligned,
        "correlation_full": full,
        "correlation_calm": calm_corr,
        "correlation_stress": stress_corr,
        "stress_threshold": STRESS_THRESHOLD_R,
        "rejected_pairs_under_stress_rule": rejected_pairs,
        "battery_verdict": (
            f"ACCEPTED: stress correlations all <= {STRESS_THRESHOLD_R}; "
            f"standalone Sharpe {standalone['annualized_R_sharpe']:.2f} > 0"
            if accepted
            else f"REJECTED: " + (
                f"{len(rejected_pairs)} stress correlation(s) > {STRESS_THRESHOLD_R}"
                if rejected_pairs
                else f"standalone Sharpe {standalone['annualized_R_sharpe']:.2f} <= 0"
            )
        ),
    }


def make_demo_candidate() -> tuple[pd.DataFrame, str, float]:
    """Synthetic candidate with normal-regime independence but stress
    correlation to Striker — illustrates the H8 reject criterion."""
    existing = pd.read_csv(DAILY_CSV, parse_dates=["exit_date_ny"])
    existing["date"] = existing["exit_date_ny"].dt.date
    stress = stress_flag_series()
    stress["date"] = pd.to_datetime(stress["date"]).dt.date
    merged = existing.merge(stress[["date", "is_stress"]], on="date", how="left")
    merged["is_stress"] = merged["is_stress"].fillna(0).astype(int)

    rng = np.random.default_rng(2026)
    base = rng.normal(0.05, 0.30, size=len(merged))
    # On stress days: copy 60% of Striker's daily R + noise => stress corr ~ 0.6
    stress_mask = (merged["is_stress"] == 1).values
    base[stress_mask] = (
        0.60 * merged.loc[stress_mask, "striker_R"].values
        + rng.normal(0.0, 0.15, size=int(stress_mask.sum()))
    )
    cand = pd.DataFrame({"date": merged["date"], "R": base})
    return cand, "demo_synthetic_stress_correlated", 0.005


def main() -> None:
    p = argparse.ArgumentParser(prog="h8_invasion_fitness")
    p.add_argument("--candidate", type=str, default=None,
                   help="CSV path with columns [date, R]")
    p.add_argument("--candidate-name", type=str, default=None)
    p.add_argument("--proposed-alloc", type=float, default=0.005,
                   help="Proposed allocation fraction (default 0.005)")
    p.add_argument("--demo", action="store_true",
                   help="Run synthetic stress-correlated demo candidate")
    args = p.parse_args()

    if args.demo or args.candidate is None:
        cand, name, alloc = make_demo_candidate()
        if args.proposed_alloc:
            alloc = args.proposed_alloc
    else:
        cand = pd.read_csv(args.candidate)
        if "date" not in cand.columns or "R" not in cand.columns:
            raise SystemExit("Candidate CSV must contain columns 'date' and 'R'")
        name = args.candidate_name or Path(args.candidate).stem
        alloc = args.proposed_alloc

    result = evaluate_candidate(cand, name, alloc)
    OUT_JSON.write_text(json.dumps(result, indent=2, default=str))

    print(f"MSEE H8 — Invasion-fitness battery: {name}")
    print(f"  Proposed alloc: {alloc*100:.3f}%")
    print()
    sd = result["standalone_fitness_full_axis"]
    sd_a = result["standalone_fitness_overlap_with_existing_panel"]
    print(f"  STANDALONE (full candidate axis, n={sd['n_days']}):")
    print(f"    Sharpe (annualized) = {sd['annualized_R_sharpe']:.3f}")
    print(f"    PF                  = {sd['profit_factor']:.3f}")
    print(f"    Win rate            = {sd['win_rate']:.3f}")
    print(f"    Realized max DD @{alloc*100:.2f}% = "
          f"{sd['realized_max_dd_at_alloc_pct']*100:.3f}%")
    print(f"  STANDALONE (panel overlap, n={sd_a['n_days']}):")
    print(f"    Sharpe (annualized) = {sd_a['annualized_R_sharpe']:.3f}")
    print()
    for label, key in [("CALM", "correlation_calm"),
                       ("STRESS", "correlation_stress"),
                       ("FULL", "correlation_full")]:
        block = result[key]
        print(f"  {label} correlations to existing (n={block['n_days']}):")
        for s in STRATEGIES:
            r = block["candidate_vs_existing"][s]["r"]
            print(f"    candidate vs {s:10s}  r={r:+.3f}")
    print()
    if result["rejected_pairs_under_stress_rule"]:
        print(f"  REJECTED PAIRS:")
        for rp in result["rejected_pairs_under_stress_rule"]:
            print(f"    stress r vs {rp['existing_strategy']} = "
                  f"{rp['stress_r']:.3f} > threshold {STRESS_THRESHOLD_R}")
    print()
    print(f"  VERDICT: {result['battery_verdict']}")
    print(f"Wrote: {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
