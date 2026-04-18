"""
Module 03 — Cross-Strategy Drawdown Correlation Analysis

Average cross-strategy correlation is ~0, but averages hide tails.
This module identifies periods where 2+ strategies drew down simultaneously,
quantifies conditional correlation during stress, and tests whether
staggering entries could reduce portfolio max DD.

Usage:
    python 03_cross_strategy_drawdown.py
"""

import numpy as np
import pandas as pd
from scipy import stats

from config import STRATEGIES, CHALLENGE
from master_analysis import load_all_strategies, compute_metrics


def build_daily_pnl_matrix(all_trades: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Build a matrix of daily P&L per strategy with aligned dates."""
    daily_series = {}

    for key, trades in all_trades.items():
        if "entry_date" not in trades.columns:
            continue
        daily = trades.groupby("entry_date")["profit"].sum()
        daily_series[key] = daily

    if not daily_series:
        return pd.DataFrame()

    matrix = pd.DataFrame(daily_series)
    matrix = matrix.sort_index()
    matrix = matrix.fillna(0)  # no trade = 0 P&L
    matrix["portfolio"] = matrix.sum(axis=1)

    return matrix


def correlation_analysis(daily_matrix: pd.DataFrame):
    """Compute full and conditional correlations."""
    strat_cols = [c for c in daily_matrix.columns if c != "portfolio"]

    if len(strat_cols) < 2:
        print("  Need at least 2 strategies for correlation analysis.")
        return

    print(f"\n  ── Full-Period Correlations ──")
    corr = daily_matrix[strat_cols].corr()
    for i, s1 in enumerate(strat_cols):
        for s2 in strat_cols[i + 1:]:
            print(f"  {s1:>10} ↔ {s2:<10}: r = {corr.loc[s1, s2]:+.3f}")

    # Conditional correlation: only on days where at least one strategy lost
    print(f"\n  ── Conditional Correlation (loss days only) ──")
    loss_days = daily_matrix[(daily_matrix[strat_cols] < 0).any(axis=1)]
    if len(loss_days) > 10:
        loss_corr = loss_days[strat_cols].corr()
        for i, s1 in enumerate(strat_cols):
            for s2 in strat_cols[i + 1:]:
                r = loss_corr.loc[s1, s2]
                flag = " ⚠ ELEVATED" if r > 0.3 else ""
                print(f"  {s1:>10} ↔ {s2:<10}: r = {r:+.3f} "
                      f"(N={len(loss_days)} loss days){flag}")

    # Tail correlation: worst 10% of portfolio days
    print(f"\n  ── Tail Correlation (worst 10% portfolio days) ──")
    threshold = daily_matrix["portfolio"].quantile(0.10)
    tail_days = daily_matrix[daily_matrix["portfolio"] <= threshold]
    if len(tail_days) > 5:
        print(f"  Portfolio P&L threshold: ≤ ${threshold:,.0f} ({len(tail_days)} days)")
        for s in strat_cols:
            avg_pnl = tail_days[s].mean()
            pct_losing = (tail_days[s] < 0).mean()
            print(f"    {s:>10}: avg PnL=${avg_pnl:,.0f}, "
                  f"{pct_losing:.0%} of these days are losers")

        if len(strat_cols) >= 2:
            tail_corr = tail_days[strat_cols].corr()
            for i, s1 in enumerate(strat_cols):
                for s2 in strat_cols[i + 1:]:
                    r = tail_corr.loc[s1, s2]
                    print(f"    Tail corr {s1} ↔ {s2}: r = {r:+.3f}")


def simultaneous_loss_analysis(daily_matrix: pd.DataFrame):
    """Identify and analyze days where multiple strategies lost simultaneously."""
    strat_cols = [c for c in daily_matrix.columns if c != "portfolio"]

    print(f"\n  ── Simultaneous Loss Events ──")

    # Count days by number of strategies losing
    n_losing = (daily_matrix[strat_cols] < 0).sum(axis=1)

    for n in range(1, len(strat_cols) + 1):
        days_n = daily_matrix[n_losing >= n]
        if len(days_n) > 0:
            avg_portfolio = days_n["portfolio"].mean()
            worst_portfolio = days_n["portfolio"].min()
            print(f"  {n}+ strategies losing: {len(days_n)} days, "
                  f"avg portfolio=${avg_portfolio:,.0f}, "
                  f"worst=${worst_portfolio:,.0f}")

    # Detail the worst joint loss days
    print(f"\n  ── Worst 10 Portfolio Days ──")
    worst = daily_matrix.nsmallest(10, "portfolio")
    for date, row in worst.iterrows():
        strat_pnls = " | ".join(
            f"{s}: ${row[s]:+,.0f}" for s in strat_cols if row[s] != 0
        )
        print(f"  {date}: Portfolio ${row['portfolio']:+,.0f} [{strat_pnls}]")

    # Which strategy drives the worst days?
    print(f"\n  ── Strategy Contribution to Worst 20 Days ──")
    worst20 = daily_matrix.nsmallest(20, "portfolio")
    for s in strat_cols:
        contribution = worst20[s].sum()
        pct = contribution / worst20["portfolio"].sum() * 100 if worst20["portfolio"].sum() != 0 else 0
        print(f"  {s:>10}: ${contribution:+,.0f} ({pct:.1f}% of losses)")


def stagger_simulation(all_trades: dict[str, pd.DataFrame], daily_matrix: pd.DataFrame):
    """
    Test if pausing one strategy after another strategies stopped out
    reduces portfolio DD. 
    
    Logic: After strategy A takes a loss, skip the next trade from strategy B
    if it occurs within N hours.
    """
    strat_cols = [c for c in daily_matrix.columns if c != "portfolio"]

    if len(strat_cols) < 2:
        return

    print(f"\n{'=' * 60}")
    print(f"  STAGGER ENTRY SIMULATION")
    print(f"{'=' * 60}")
    print(f"  Concept: After strategy X stops out, skip next trade from Y")
    print(f"  within a cooldown window.\n")

    # For each pair, test cooldown windows
    cooldown_hours = [1, 2, 4, 8, 24]

    for trigger_strat in strat_cols:
        for target_strat in strat_cols:
            if trigger_strat == target_strat:
                continue

            trigger_trades = all_trades.get(trigger_strat)
            target_trades = all_trades.get(target_strat)

            if trigger_trades is None or target_trades is None:
                continue
            if "entry_time" not in trigger_trades.columns or "entry_time" not in target_trades.columns:
                continue

            trigger_losses = trigger_trades[trigger_trades["is_loser"]].copy()
            if len(trigger_losses) == 0:
                continue

            print(f"  Trigger: {trigger_strat} loss → Skip {target_strat}")

            for hours in cooldown_hours:
                # Find target trades that fall within cooldown of a trigger loss
                skip_mask = pd.Series(False, index=target_trades.index)
                for _, loss in trigger_losses.iterrows():
                    if "exit_time" in loss and pd.notna(loss["exit_time"]):
                        loss_time = loss["exit_time"]
                    else:
                        loss_time = loss["entry_time"]

                    window_end = loss_time + pd.Timedelta(hours=hours)
                    in_window = (
                        (target_trades["entry_time"] > loss_time) &
                        (target_trades["entry_time"] <= window_end)
                    )
                    skip_mask = skip_mask | in_window

                n_skipped = skip_mask.sum()
                if n_skipped == 0:
                    continue

                skipped_pnl = target_trades[skip_mask]["profit"].sum()
                skipped_wr = target_trades[skip_mask]["is_winner"].mean()
                kept_metrics = compute_metrics(target_trades[~skip_mask])

                direction = "✓" if skipped_pnl < 0 else "✗"
                print(f"    {hours:>2}h cooldown: skip {n_skipped} trades, "
                      f"skipped PnL=${skipped_pnl:+,.0f} "
                      f"(WR={skipped_wr:.0%}), "
                      f"kept PF={kept_metrics['profit_factor']:.2f} {direction}")


def weekly_rhythm_analysis(daily_matrix: pd.DataFrame):
    """Analyze if certain days of the week have correlated strategy losses."""
    strat_cols = [c for c in daily_matrix.columns if c != "portfolio"]

    print(f"\n{'=' * 60}")
    print(f"  WEEKLY RHYTHM ANALYSIS")
    print(f"{'=' * 60}")

    daily_matrix["dow"] = pd.to_datetime(daily_matrix.index).day_name()

    for dow in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
        day_data = daily_matrix[daily_matrix["dow"] == dow]
        if len(day_data) < 5:
            continue

        avg_pnl = day_data["portfolio"].mean()
        wr = (day_data["portfolio"] > 0).mean()
        n_all_losing = ((day_data[strat_cols] < 0).all(axis=1)).sum()

        strat_detail = " | ".join(
            f"{s}: ${day_data[s].mean():+,.0f}" for s in strat_cols
        )
        flag = " ⚠" if avg_pnl < 0 or wr < 0.45 else ""
        print(f"  {dow:<10}: avg=${avg_pnl:+,.0f} WR={wr:.0%} "
              f"AllLosing={n_all_losing} [{strat_detail}]{flag}")


if __name__ == "__main__":
    print("Module 03: Cross-Strategy Drawdown Correlation")
    print("Loading strategies...")

    all_trades = load_all_strategies()
    if not all_trades:
        print("No data loaded.")
        exit(1)

    daily_matrix = build_daily_pnl_matrix(all_trades)
    if daily_matrix.empty:
        print("Could not build daily P&L matrix (need datetime data).")
        exit(1)

    print(f"\n  Daily P&L matrix: {len(daily_matrix)} trading days, "
          f"{len(daily_matrix.columns) - 1} strategies")

    correlation_analysis(daily_matrix)
    simultaneous_loss_analysis(daily_matrix)
    stagger_simulation(all_trades, daily_matrix)
    weekly_rhythm_analysis(daily_matrix)

    print("\n✓ Module 03 complete.")
    print("  → Tail correlations > 0.3 between strategies are concerning.")
    print("  → If one strategy dominates worst days, consider reducing its risk allocation.")
    print("  → Stagger logic only worth implementing if skipped trades have negative PnL.")
