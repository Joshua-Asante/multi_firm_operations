"""
Module 04 — Exit Optimization Sweep

Entry signals are locked. This module tests whether alternative exit
management could improve risk-adjusted returns without changing entries.

Tests:
  - Time-based exits (close after N bars if not at target)
  - Partial profit-taking (simulate 50% at 1R, rest at full TP)
  - Earlier breakeven triggers
  - Tighter trailing stops
  - Maximum adverse excursion (MAE) based filters

Requires: run_up and drawdown columns from TradingView exports.

Usage:
    python 04_exit_optimization.py
"""

import numpy as np
import pandas as pd

from config import STRATEGIES, OOS_SPLIT
from master_analysis import load_all_strategies, compute_metrics, split_oos


def has_excursion_data(trades: pd.DataFrame) -> bool:
    """Check if MFE/MAE (run_up/drawdown) data is available."""
    return (
        "run_up" in trades.columns
        and "drawdown" in trades.columns
        and trades["run_up"].notna().sum() > len(trades) * 0.5
    )


def time_exit_analysis(trades: pd.DataFrame, strategy_key: str):
    """
    Analyze P&L by trade duration to find optimal time-based exit windows.
    If most profits are captured within N bars, a time exit could
    reduce exposure without sacrificing much return.
    """
    name = STRATEGIES[strategy_key]["name"]
    print(f"\n  ── Time-Based Exit Analysis: {name} ──")

    if "duration_bars" not in trades.columns:
        print("  Duration data not available.")
        return

    # P&L contribution by duration bucket
    buckets = [
        (0, 5, "0-5 bars"),
        (5, 10, "5-10 bars"),
        (10, 20, "10-20 bars"),
        (20, 40, "20-40 bars"),
        (40, 80, "40-80 bars"),
        (80, float("inf"), "80+ bars"),
    ]

    total_pnl = trades["profit"].sum()
    print(f"\n  {'Duration':<15} {'Trades':>7} {'PnL':>12} {'% of Total':>10} "
          f"{'WR':>8} {'Avg PnL':>10}")
    print(f"  {'─' * 64}")

    cumulative_pnl = 0
    for low, high, label in buckets:
        bucket = trades[
            (trades["duration_bars"] >= low) &
            (trades["duration_bars"] < high)
        ]
        if len(bucket) == 0:
            continue

        pnl = bucket["profit"].sum()
        cumulative_pnl += pnl
        wr = bucket["is_winner"].mean()
        avg = bucket["profit"].mean()
        pct = pnl / total_pnl * 100 if total_pnl != 0 else 0
        cum_pct = cumulative_pnl / total_pnl * 100 if total_pnl != 0 else 0

        print(f"  {label:<15} {len(bucket):>7} ${pnl:>11,.0f} {pct:>9.1f}% "
              f"{wr:>7.0%} ${avg:>9,.0f}  [cum: {cum_pct:.0f}%]")

    # Simulate hard time exits at various bar counts
    print(f"\n  Simulated time exit impacts:")
    for max_bars in [10, 15, 20, 30, 40, 55]:
        would_be_cut = trades[trades["duration_bars"] > max_bars]
        if len(would_be_cut) == 0:
            continue
        # These trades would be exited early — assume breakeven for simplicity
        # (conservative estimate; reality depends on price at exit bar)
        cut_pnl = would_be_cut["profit"].sum()
        remaining = trades[trades["duration_bars"] <= max_bars]
        remaining_pnl = remaining["profit"].sum()
        print(f"    Exit at {max_bars:>3} bars: "
              f"keep {len(remaining)} trades (${remaining_pnl:+,.0f}), "
              f"cut {len(would_be_cut)} trades (${cut_pnl:+,.0f} forfeited)")


def mfe_mae_analysis(trades: pd.DataFrame, strategy_key: str):
    """
    Maximum Favorable/Adverse Excursion analysis.
    Identifies if winners could be exited more efficiently
    and if losers share early warning MAE patterns.
    """
    name = STRATEGIES[strategy_key]["name"]
    print(f"\n  ── MFE/MAE Analysis: {name} ──")

    if not has_excursion_data(trades):
        print("  MFE/MAE data not available in CSV (need run_up/drawdown columns).")
        return

    winners = trades[trades["is_winner"]].copy()
    losers = trades[trades["is_loser"]].copy()

    # Winner efficiency: what % of MFE was captured?
    if len(winners) > 0:
        winners["capture_ratio"] = winners["profit"] / winners["run_up"].abs().clip(lower=1e-10)
        avg_capture = winners["capture_ratio"].mean()
        median_capture = winners["capture_ratio"].median()
        print(f"  Winner MFE capture: avg={avg_capture:.1%}, median={median_capture:.1%}")
        print(f"  → If <70%, consider tighter trailing or partial TP")

        # How much MFE are winners giving back?
        winners["giveback"] = winners["run_up"].abs() - winners["profit"]
        avg_giveback = winners["giveback"].mean()
        print(f"  Avg giveback (MFE - actual profit): ${avg_giveback:,.0f}")

        # Distribution of MFE for winners
        mfe_pcts = [25, 50, 75, 90]
        mfe_vals = np.percentile(winners["run_up"].abs(), mfe_pcts)
        print(f"  Winner MFE percentiles: " +
              " | ".join(f"p{p}=${v:,.0f}" for p, v in zip(mfe_pcts, mfe_vals)))

    # Loser MAE: do losers show early warning signals?
    if len(losers) > 0:
        print(f"\n  Loser MAE analysis:")
        losers["mae_to_loss_ratio"] = losers["drawdown"].abs() / losers["profit"].abs().clip(lower=1e-10)
        avg_ratio = losers["mae_to_loss_ratio"].mean()
        print(f"  Avg MAE/Loss ratio: {avg_ratio:.2f}")
        print(f"  → Ratio > 1.5 means losers often recover partially before final stop")

        mae_pcts = [25, 50, 75, 90]
        mae_vals = np.percentile(losers["drawdown"].abs(), mae_pcts)
        print(f"  Loser MAE percentiles: " +
              " | ".join(f"p{p}=${v:,.0f}" for p, v in zip(mae_pcts, mae_vals)))


def partial_profit_simulation(trades: pd.DataFrame, strategy_key: str):
    """
    Simulate partial profit-taking: close X% at target T1, rest at full TP.
    
    Uses MFE to determine if T1 would have been hit before the trade resolved.
    """
    name = STRATEGIES[strategy_key]["name"]
    params = STRATEGIES[strategy_key]["params"]
    print(f"\n  ── Partial Profit Simulation: {name} ──")

    if not has_excursion_data(trades):
        print("  MFE/MAE data needed for partial profit simulation.")
        return

    # Test various partial TP levels
    # Express as fraction of full TP (e.g., 0.3 = 30% of full TP distance)
    partial_levels = [0.20, 0.30, 0.40, 0.50, 0.60]
    partial_sizes = [0.25, 0.33, 0.50]  # fraction of position to close at T1

    full_profit = trades["profit"].sum()
    full_pf = compute_metrics(trades)["profit_factor"]

    print(f"  Full TP baseline: ${full_profit:,.0f}, PF={full_pf:.2f}")
    print(f"\n  {'T1 Level':>10} {'T1 Size':>8} {'Adj PnL':>12} {'vs Full':>10} {'Est PF':>8}")
    print(f"  {'─' * 52}")

    for level in partial_levels:
        for size in partial_sizes:
            adjusted_profits = []

            for _, trade in trades.iterrows():
                mfe = abs(trade["run_up"]) if pd.notna(trade["run_up"]) else 0
                original_pnl = trade["profit"]

                if original_pnl <= 0:
                    # Loser: partial doesn't help (T1 not reached)
                    # But if MFE reached T1 level, partial would lock in some profit
                    t1_value = abs(original_pnl) * level  # estimate T1 distance
                    if mfe >= t1_value and t1_value > 0:
                        # Would have taken partial at T1
                        partial_profit = t1_value * size
                        remaining_loss = original_pnl * (1 - size)
                        adjusted_profits.append(partial_profit + remaining_loss)
                    else:
                        adjusted_profits.append(original_pnl)
                else:
                    # Winner: T1 definitely hit if MFE >= T1
                    t1_value = original_pnl * level
                    if mfe >= t1_value:
                        partial_profit = t1_value * size
                        remaining_profit = original_pnl * (1 - size)
                        adjusted_profits.append(partial_profit + remaining_profit)
                    else:
                        adjusted_profits.append(original_pnl)

            adj_total = sum(adjusted_profits)
            diff = adj_total - full_profit
            adj_winners = sum(1 for p in adjusted_profits if p > 0)
            adj_losers = sum(1 for p in adjusted_profits if p < 0)
            adj_gross_win = sum(p for p in adjusted_profits if p > 0)
            adj_gross_loss = abs(sum(p for p in adjusted_profits if p < 0))
            adj_pf = adj_gross_win / adj_gross_loss if adj_gross_loss > 0 else float("inf")

            marker = " ←" if adj_total > full_profit else ""
            print(f"  {level:>9.0%} {size:>7.0%} ${adj_total:>11,.0f} "
                  f"${diff:>+9,.0f} {adj_pf:>7.2f}{marker}")


def breakeven_sensitivity(trades: pd.DataFrame, strategy_key: str):
    """
    Test how earlier/later breakeven triggers affect outcomes.
    Uses MAE to determine if trades would survive with tighter BE.
    """
    name = STRATEGIES[strategy_key]["name"]
    params = STRATEGIES[strategy_key]["params"]
    print(f"\n  ── Breakeven Trigger Sensitivity: {name} ──")

    if not has_excursion_data(trades):
        print("  MFE/MAE data needed.")
        return

    be_trigger = params.get("be_trigger_atr", None)
    if be_trigger is None:
        print("  No BE trigger parameter found in config.")
        return

    print(f"  Current BE trigger: {be_trigger} ATR")
    print(f"  (Lower = earlier BE activation = less risk but more BE stopouts)\n")

    # We can't directly simulate ATR-based BE changes from P&L data alone.
    # But we CAN analyze the distribution of MFE before losers close.
    winners = trades[trades["is_winner"]]
    losers = trades[trades["is_loser"]]

    if len(winners) > 0:
        # What fraction of winners had MFE > various thresholds?
        mfe_threshold_pcts = [0.1, 0.2, 0.3, 0.5, 0.7, 1.0]
        print(f"  Winner MFE distribution (fraction reaching threshold):")
        for pct in mfe_threshold_pcts:
            # Use median winner profit as rough MFE baseline
            threshold = winners["profit"].median() * pct
            frac_reaching = (winners["run_up"].abs() >= threshold).mean()
            print(f"    MFE ≥ {pct:.0%} of median win: {frac_reaching:.1%} of winners")

    if len(losers) > 0:
        # How many losers showed MFE ≥ BE trigger equivalent?
        avg_winner = winners["profit"].mean() if len(winners) > 0 else 1
        for pct in [0.3, 0.5, 0.7, 1.0]:
            threshold = avg_winner * pct
            losers_with_mfe = (losers["run_up"].abs() >= threshold).mean()
            print(f"    Losers where MFE reached {pct:.0%} of avg win: {losers_with_mfe:.1%}")
            if losers_with_mfe > 0.3:
                print(f"      → {losers_with_mfe:.0%} of losers went to profit first — "
                      f"tighter trailing could convert some")


def run_oos_validation(all_trades: dict[str, pd.DataFrame]):
    """
    Run OOS validation on any promising exit modifications.
    """
    print(f"\n{'=' * 60}")
    print(f"  OUT-OF-SAMPLE EXIT VALIDATION")
    print(f"{'=' * 60}")

    for key, trades in all_trades.items():
        name = STRATEGIES[key]["name"]
        train, test = split_oos(trades)

        if len(train) == 0 or len(test) == 0:
            continue

        train_m = compute_metrics(train)
        test_m = compute_metrics(test)

        print(f"\n  {name}:")
        print(f"    In-sample:  {train_m['total_trades']} trades, "
              f"PF={train_m['profit_factor']:.2f}, "
              f"WR={train_m['win_rate']:.1%}, "
              f"AvgWin/AvgLoss={abs(train_m['avg_win']/train_m['avg_loss']) if train_m['avg_loss'] != 0 else 0:.2f}")
        print(f"    Out-sample: {test_m['total_trades']} trades, "
              f"PF={test_m['profit_factor']:.2f}, "
              f"WR={test_m['win_rate']:.1%}, "
              f"AvgWin/AvgLoss={abs(test_m['avg_win']/test_m['avg_loss']) if test_m['avg_loss'] != 0 else 0:.2f}")

        # Key ratio: if OOS avg_win/avg_loss degrades more than WR,
        # exit management is the issue (entries still work, exits don't)
        if train_m["avg_loss"] != 0 and test_m["avg_loss"] != 0:
            train_rr = abs(train_m["avg_win"] / train_m["avg_loss"])
            test_rr = abs(test_m["avg_win"] / test_m["avg_loss"])
            rr_change = (test_rr - train_rr) / train_rr * 100
            wr_change = (test_m["win_rate"] - train_m["win_rate"]) / train_m["win_rate"] * 100

            if rr_change < -15 and wr_change > -5:
                print(f"    ⚠ R:R degraded {rr_change:+.1f}% while WR stable ({wr_change:+.1f}%)")
                print(f"    → Exit management may be the issue, not entry quality")
            elif wr_change < -15 and rr_change > -5:
                print(f"    ⚠ WR degraded {wr_change:+.1f}% while R:R stable ({rr_change:+.1f}%)")
                print(f"    → Entry quality shifted; exit changes won't help")


if __name__ == "__main__":
    print("Module 04: Exit Optimization Sweep")
    print("Loading strategies...")

    all_trades = load_all_strategies()
    if not all_trades:
        print("No data loaded.")
        exit(1)

    for key, trades in all_trades.items():
        print(f"\n{'=' * 60}")
        print(f"  EXIT ANALYSIS: {STRATEGIES[key]['name']}")
        print(f"{'=' * 60}")

        time_exit_analysis(trades, key)
        mfe_mae_analysis(trades, key)
        partial_profit_simulation(trades, key)
        breakeven_sensitivity(trades, key)

    run_oos_validation(all_trades)

    print("\n✓ Module 04 complete.")
    print("  → Focus on MFE capture ratio — if <60%, trailing/partial exits have room to improve.")
    print("  → Time exits only worth pursuing if long-duration trades are net negative.")
    print("  → All changes must validate OOS before implementation.")
