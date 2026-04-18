"""
Module 01 — Challenge Equity Curve Optimization

The FXIFY challenge has asymmetric rules: 5% target vs 5% DD.
This module tests adaptive risk scaling strategies:
  - Reduce risk after reaching equity milestones (protect gains)
  - Reduce risk after drawdown thresholds (survive to fight another day)
  - Combined: scale up early, scale down when leading or bleeding

Key question: Does protecting a lead improve pass rate even if it costs speed?

Usage:
    python 01_challenge_equity_optimization.py
"""

import numpy as np
import pandas as pd
from itertools import product

from config import STRATEGIES, CHALLENGE, MONTE_CARLO, ANALYSIS
from master_analysis import load_all_strategies, scale_profit


def simulate_adaptive_challenge(
    all_profits: list[dict],
    base_risks: dict[str, float],
    equity_scale_rules: list[dict],
    n_sims: int = 10_000,
    seed: int = 42,
) -> dict:
    """
    Monte Carlo with adaptive risk scaling based on current equity state.

    equity_scale_rules: list of dicts with:
        - "trigger_type": "equity_above" or "dd_below"
        - "threshold_pct": float (equity gain % or DD %)
        - "scale_factor": float (multiply all risks by this, e.g. 0.5 = half risk)
    """
    np.random.seed(seed)

    account = CHALLENGE["account_size"]
    target = account * (CHALLENGE["profit_target_pct"] / 100)
    dd_limit = account * (CHALLENGE["max_total_dd_pct"] / 100)

    # Pre-compute profit arrays per strategy
    strategy_profits = {}
    for item in all_profits:
        key = item["strategy"]
        if key not in strategy_profits:
            strategy_profits[key] = []
        strategy_profits[key].append(item["profit"])

    # Build a flat array of (strategy_key, base_profit) tuples
    trade_pool = [(item["strategy"], item["profit"]) for item in all_profits]
    n_trades = len(trade_pool)

    passes = 0
    days_to_pass = []
    max_dds = []

    for _ in range(n_sims):
        perm = np.random.permutation(n_trades)
        equity = 0.0
        peak = 0.0
        passed = False

        for idx in perm:
            strat_key, base_pnl = trade_pool[idx]
            base_risk = base_risks[strat_key]

            # Determine current scaling factor
            equity_pct = (equity / account) * 100
            dd_pct = ((peak - equity) / account) * 100
            scale = 1.0

            for rule in equity_scale_rules:
                if rule["trigger_type"] == "equity_above":
                    if equity_pct >= rule["threshold_pct"]:
                        scale = min(scale, rule["scale_factor"])
                elif rule["trigger_type"] == "dd_below":
                    if dd_pct >= rule["threshold_pct"]:
                        scale = min(scale, rule["scale_factor"])

            # Apply scaling
            adjusted_pnl = base_pnl * scale
            equity += adjusted_pnl
            peak = max(peak, equity)

            if equity >= target:
                passed = True
                est_days = max(5, int(np.ceil((list(perm).index(idx) + 1) / 2.5)))
                days_to_pass.append(est_days)
                break

            if (peak - equity) >= dd_limit:
                break

        if passed:
            passes += 1
        max_dds.append((peak - equity) / account * 100)

    return {
        "pass_rate": passes / n_sims * 100,
        "median_days": int(np.median(days_to_pass)) if days_to_pass else None,
        "avg_max_dd": np.mean(max_dds),
        "p95_max_dd": np.percentile(max_dds, 95),
        "p99_max_dd": np.percentile(max_dds, 99),
        "rules": equity_scale_rules,
    }


def run_equity_threshold_sweep(all_trades: dict[str, pd.DataFrame]):
    """
    Test equity-based risk reduction: after reaching X% profit, 
    scale risk down to protect the lead.
    """
    print("\n" + "=" * 60)
    print("  EQUITY THRESHOLD RISK REDUCTION SWEEP")
    print("=" * 60)

    # Build profit pool
    all_profits = []
    for key, trades in all_trades.items():
        for _, trade in trades.iterrows():
            all_profits.append({
                "strategy": key,
                "profit": trade["profit"],
            })

    base_risks = {k: STRATEGIES[k]["risk_pct_challenge"] for k in all_trades}

    # Test: reduce risk by various factors after hitting equity thresholds
    thresholds = [2.0, 2.5, 3.0, 3.5, 4.0]
    scale_factors = [0.40, 0.50, 0.60, 0.70, 0.80]

    results = []
    print(f"\n  {'Threshold':>10} {'Scale':>8} {'Pass%':>8} {'MedDays':>8} "
          f"{'AvgDD':>8} {'p95DD':>8}")
    print(f"  {'─' * 58}")

    # Baseline (no scaling)
    baseline = simulate_adaptive_challenge(
        all_profits, base_risks, equity_scale_rules=[], n_sims=10_000
    )
    print(f"  {'BASELINE':>10} {'1.00':>8} {baseline['pass_rate']:>7.1f}% "
          f"{baseline['median_days'] or 'N/A':>8} "
          f"{baseline['avg_max_dd']:>7.2f}% {baseline['p95_max_dd']:>7.2f}%")

    for thresh, scale in product(thresholds, scale_factors):
        rules = [{"trigger_type": "equity_above", "threshold_pct": thresh,
                  "scale_factor": scale}]
        result = simulate_adaptive_challenge(
            all_profits, base_risks, rules, n_sims=10_000
        )
        result["threshold"] = thresh
        result["scale_factor"] = scale
        results.append(result)

        # Highlight improvements
        marker = " ←" if result["pass_rate"] > baseline["pass_rate"] + 0.1 else ""
        print(f"  {thresh:>9.1f}% {scale:>7.2f}x {result['pass_rate']:>7.1f}% "
              f"{result['median_days'] or 'N/A':>8} "
              f"{result['avg_max_dd']:>7.2f}% {result['p95_max_dd']:>7.2f}%{marker}")

    return results


def run_dd_protection_sweep(all_trades: dict[str, pd.DataFrame]):
    """
    Test DD-based risk reduction: after hitting X% drawdown,
    scale risk down to avoid busting.
    """
    print("\n" + "=" * 60)
    print("  DRAWDOWN PROTECTION SWEEP")
    print("=" * 60)

    all_profits = []
    for key, trades in all_trades.items():
        for _, trade in trades.iterrows():
            all_profits.append({"strategy": key, "profit": trade["profit"]})

    base_risks = {k: STRATEGIES[k]["risk_pct_challenge"] for k in all_trades}

    dd_thresholds = [1.5, 2.0, 2.5, 3.0, 3.5]
    scale_factors = [0.30, 0.40, 0.50, 0.60, 0.70]

    print(f"\n  {'DD Trigger':>10} {'Scale':>8} {'Pass%':>8} {'MedDays':>8} "
          f"{'AvgDD':>8} {'p95DD':>8}")
    print(f"  {'─' * 58}")

    for dd_thresh, scale in product(dd_thresholds, scale_factors):
        rules = [{"trigger_type": "dd_below", "threshold_pct": dd_thresh,
                  "scale_factor": scale}]
        result = simulate_adaptive_challenge(
            all_profits, base_risks, rules, n_sims=10_000
        )
        print(f"  {dd_thresh:>9.1f}% {scale:>7.2f}x {result['pass_rate']:>7.1f}% "
              f"{result['median_days'] or 'N/A':>8} "
              f"{result['avg_max_dd']:>7.2f}% {result['p95_max_dd']:>7.2f}%")


def run_combined_adaptive_sweep(all_trades: dict[str, pd.DataFrame]):
    """
    Combined strategy: protect gains AND reduce on DD simultaneously.
    Test the best combos from the individual sweeps.
    """
    print("\n" + "=" * 60)
    print("  COMBINED ADAPTIVE RISK SCALING")
    print("=" * 60)
    print("  (Top equity + DD combos)")

    all_profits = []
    for key, trades in all_trades.items():
        for _, trade in trades.iterrows():
            all_profits.append({"strategy": key, "profit": trade["profit"]})

    base_risks = {k: STRATEGIES[k]["risk_pct_challenge"] for k in all_trades}

    # Test promising combos
    combos = [
        # (equity_thresh, equity_scale, dd_thresh, dd_scale)
        (3.0, 0.60, 2.5, 0.50),
        (3.0, 0.70, 3.0, 0.50),
        (3.5, 0.60, 2.0, 0.40),
        (2.5, 0.50, 2.0, 0.50),
        (3.0, 0.50, 2.5, 0.40),
        (3.5, 0.70, 3.0, 0.60),
        (4.0, 0.60, 2.5, 0.50),
    ]

    print(f"\n  {'EqThresh':>8} {'EqScale':>8} {'DDThresh':>8} {'DDScale':>8} "
          f"{'Pass%':>8} {'MedDays':>8} {'p95DD':>8}")
    print(f"  {'─' * 66}")

    for eq_t, eq_s, dd_t, dd_s in combos:
        rules = [
            {"trigger_type": "equity_above", "threshold_pct": eq_t, "scale_factor": eq_s},
            {"trigger_type": "dd_below", "threshold_pct": dd_t, "scale_factor": dd_s},
        ]
        result = simulate_adaptive_challenge(
            all_profits, base_risks, rules, n_sims=10_000
        )
        print(f"  {eq_t:>7.1f}% {eq_s:>7.2f}x {dd_t:>7.1f}% {dd_s:>7.2f}x "
              f"{result['pass_rate']:>7.1f}% {result['median_days'] or 'N/A':>8} "
              f"{result['p95_max_dd']:>7.2f}%")


if __name__ == "__main__":
    print("Module 01: Challenge Equity Curve Optimization")
    print("Loading strategies...")

    all_trades = load_all_strategies()
    if not all_trades:
        print("No data loaded. Place CSVs in ./data/")
        exit(1)

    run_equity_threshold_sweep(all_trades)
    run_dd_protection_sweep(all_trades)
    run_combined_adaptive_sweep(all_trades)

    print("\n✓ Module 01 complete.")
    print("  → Look for combos that improve pass_rate without excessive median_days increase.")
    print("  → Best combos should reduce p95 DD while maintaining or improving pass rate.")
