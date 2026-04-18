"""
Module 05 — Session & Time Filter Analysis

For each strategy, decompose P&L by session windows, hour-by-hour,
and day-of-week to identify provably unprofitable time slots.

If a strategy consistently loses during specific hours, a simple
session filter could improve risk-adjusted returns at zero complexity cost.

Usage:
    python 05_session_time_filters.py
"""

import numpy as np
import pandas as pd
from scipy import stats

from config import STRATEGIES, ANALYSIS, OOS_SPLIT
from master_analysis import load_all_strategies, compute_metrics, split_oos


def hourly_pnl_heatmap(trades: pd.DataFrame, strategy_key: str):
    """Hour-by-hour P&L decomposition."""
    name = STRATEGIES[strategy_key]["name"]
    print(f"\n  ── Hourly P&L: {name} ──")

    if "entry_hour_utc" not in trades.columns:
        print("  Entry hour data not available.")
        return

    hourly = trades.groupby("entry_hour_utc").agg(
        trades=("profit", "count"),
        total_pnl=("profit", "sum"),
        avg_pnl=("profit", "mean"),
        win_rate=("is_winner", "mean"),
        avg_winner=("profit", lambda x: x[x > 0].mean() if (x > 0).sum() > 0 else 0),
        avg_loser=("profit", lambda x: x[x < 0].mean() if (x < 0).sum() > 0 else 0),
    ).reset_index()

    overall_wr = trades["is_winner"].mean()
    overall_avg = trades["profit"].mean()

    print(f"\n  {'Hour(UTC)':>10} {'Trades':>7} {'PnL':>12} {'Avg':>10} "
          f"{'WR':>7} {'AvgW':>10} {'AvgL':>10} {'Flag':>6}")
    print(f"  {'─' * 74}")

    flagged_hours = []
    for _, row in hourly.iterrows():
        flag = ""
        if row["trades"] >= 5:
            if row["total_pnl"] < 0 and row["win_rate"] < overall_wr - 0.10:
                flag = "⚠ BAD"
                flagged_hours.append(int(row["entry_hour_utc"]))
            elif row["avg_pnl"] > overall_avg * 1.5:
                flag = "★ GOOD"

        print(f"  {int(row['entry_hour_utc']):>9}h {row['trades']:>7} "
              f"${row['total_pnl']:>11,.0f} ${row['avg_pnl']:>9,.0f} "
              f"{row['win_rate']:>6.0%} ${row['avg_winner']:>9,.0f} "
              f"${row['avg_loser']:>9,.0f} {flag}")

    return flagged_hours


def dow_pnl_analysis(trades: pd.DataFrame, strategy_key: str):
    """Day-of-week P&L decomposition."""
    name = STRATEGIES[strategy_key]["name"]
    active_days = STRATEGIES[strategy_key]["active_days"]

    print(f"\n  ── Day-of-Week P&L: {name} ──")
    print(f"  Configured active days: {', '.join(active_days)}")

    if "entry_dow" not in trades.columns:
        print("  Day-of-week data not available.")
        return

    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    dow = trades.groupby("entry_dow").agg(
        trades=("profit", "count"),
        total_pnl=("profit", "sum"),
        avg_pnl=("profit", "mean"),
        win_rate=("is_winner", "mean"),
        max_loss=("profit", "min"),
    ).reindex(dow_order).dropna(how="all")

    print(f"\n  {'Day':<12} {'Trades':>7} {'PnL':>12} {'Avg':>10} "
          f"{'WR':>7} {'MaxLoss':>12} {'Status':>8}")
    print(f"  {'─' * 70}")

    flagged_days = []
    for day, row in dow.iterrows():
        scheduled = "active" if day in active_days else "OFF"
        flag = ""
        if row["trades"] >= 5 and row["total_pnl"] < 0:
            flag = "⚠"
            flagged_days.append(day)
        if scheduled == "OFF" and row["trades"] > 0:
            flag = "⚠ LEAK"  # trades on days the strategy should be off

        print(f"  {day:<12} {row['trades']:>7} ${row['total_pnl']:>11,.0f} "
              f"${row['avg_pnl']:>9,.0f} {row['win_rate']:>6.0%} "
              f"${row['max_loss']:>11,.0f} {scheduled:>6} {flag}")

    return flagged_days


def session_window_analysis(trades: pd.DataFrame, strategy_key: str):
    """Analyze P&L by major forex session windows."""
    name = STRATEGIES[strategy_key]["name"]
    print(f"\n  ── Session Window P&L: {name} ──")

    if "entry_hour_utc" not in trades.columns:
        print("  Hour data not available.")
        return

    sessions = ANALYSIS["session_windows_utc"]
    results = {}

    for session_name, (start_h, end_h) in sessions.items():
        if start_h < end_h:
            mask = (trades["entry_hour_utc"] >= start_h) & (trades["entry_hour_utc"] < end_h)
        else:  # wraps around midnight
            mask = (trades["entry_hour_utc"] >= start_h) | (trades["entry_hour_utc"] < end_h)

        session_trades = trades[mask]
        if len(session_trades) < 3:
            continue

        metrics = compute_metrics(session_trades)
        results[session_name] = metrics
        results[session_name]["n_trades"] = len(session_trades)
        results[session_name]["total_pnl"] = session_trades["profit"].sum()

    print(f"\n  {'Session':<20} {'Trades':>7} {'PnL':>12} {'PF':>7} "
          f"{'WR':>7} {'Expect':>10}")
    print(f"  {'─' * 65}")

    for session_name, m in results.items():
        flag = " ⚠" if m["total_pnl"] < 0 or m["profit_factor"] < 1.0 else ""
        print(f"  {session_name:<20} {m['n_trades']:>7} ${m['total_pnl']:>11,.0f} "
              f"{m['profit_factor']:>6.2f} {m['win_rate']:>6.0%} "
              f"${m['expectancy']:>9,.0f}{flag}")


def filter_simulation(
    trades: pd.DataFrame,
    strategy_key: str,
    hours_to_remove: list[int] = None,
    days_to_remove: list[str] = None,
):
    """
    Simulate impact of removing specific hours or days.
    Tests on full dataset AND validates OOS.
    """
    name = STRATEGIES[strategy_key]["name"]
    print(f"\n  ── Filter Impact Simulation: {name} ──")

    filters_applied = []
    mask = pd.Series(True, index=trades.index)

    if hours_to_remove and "entry_hour_utc" in trades.columns:
        hour_mask = ~trades["entry_hour_utc"].isin(hours_to_remove)
        mask = mask & hour_mask
        filters_applied.append(f"Remove hours: {hours_to_remove}")

    if days_to_remove and "entry_dow" in trades.columns:
        day_mask = ~trades["entry_dow"].isin(days_to_remove)
        mask = mask & day_mask
        filters_applied.append(f"Remove days: {days_to_remove}")

    if not filters_applied:
        print("  No filters to test.")
        return

    print(f"  Filters: {' | '.join(filters_applied)}")

    before = compute_metrics(trades)
    filtered = trades[mask]
    after = compute_metrics(filtered)
    removed = trades[~mask]

    print(f"\n  {'Metric':<20} {'Before':>12} {'After':>12} {'Change':>12}")
    print(f"  {'─' * 58}")
    print(f"  {'Trades':<20} {before['total_trades']:>12} {after['total_trades']:>12} "
          f"{after['total_trades'] - before['total_trades']:>+12}")
    print(f"  {'Total P&L':<20} ${before['total_profit']:>11,.0f} ${after['total_profit']:>11,.0f} "
          f"${after['total_profit'] - before['total_profit']:>+11,.0f}")
    print(f"  {'Profit Factor':<20} {before['profit_factor']:>12.2f} {after['profit_factor']:>12.2f} "
          f"{after['profit_factor'] - before['profit_factor']:>+12.2f}")
    print(f"  {'Win Rate':<20} {before['win_rate']:>11.1%} {after['win_rate']:>11.1%} "
          f"{(after['win_rate'] - before['win_rate'])*100:>+11.1f}%")
    print(f"  {'Expectancy':<20} ${before['expectancy']:>11,.0f} ${after['expectancy']:>11,.0f} "
          f"${after['expectancy'] - before['expectancy']:>+11,.0f}")

    removed_pnl = removed["profit"].sum() if len(removed) > 0 else 0
    print(f"\n  Removed {len(removed)} trades with total PnL: ${removed_pnl:+,.0f}")

    # OOS validation
    train, test = split_oos(trades)
    if len(train) > 0 and len(test) > 0:
        test_before = compute_metrics(test)
        test_mask = pd.Series(True, index=test.index)
        if hours_to_remove and "entry_hour_utc" in test.columns:
            test_mask = test_mask & ~test["entry_hour_utc"].isin(hours_to_remove)
        if days_to_remove and "entry_dow" in test.columns:
            test_mask = test_mask & ~test["entry_dow"].isin(days_to_remove)

        test_filtered = test[test_mask]
        test_after = compute_metrics(test_filtered)

        holds_oos = test_after["profit_factor"] >= test_before["profit_factor"]
        status = "✓ HOLDS OOS" if holds_oos else "✗ FAILS OOS"

        print(f"\n  OOS Validation ({OOS_SPLIT['test_start']}–{OOS_SPLIT['test_end']}):")
        print(f"    PF: {test_before['profit_factor']:.2f} → {test_after['profit_factor']:.2f}")
        print(f"    WR: {test_before['win_rate']:.1%} → {test_after['win_rate']:.1%}")
        print(f"    → {status}")


def auto_discover_filters(all_trades: dict[str, pd.DataFrame]):
    """
    Automatically discover the best single-hour and single-day filters
    for each strategy and validate OOS.
    """
    print(f"\n{'=' * 60}")
    print(f"  AUTO-DISCOVERED FILTER CANDIDATES")
    print(f"{'=' * 60}")

    for key, trades in all_trades.items():
        name = STRATEGIES[key]["name"]
        print(f"\n  {name}:")

        train, test = split_oos(trades)
        use_train = train if len(train) > 20 else trades

        # Find worst hours (in-sample)
        if "entry_hour_utc" in use_train.columns:
            hourly = use_train.groupby("entry_hour_utc").agg(
                n=("profit", "count"),
                pnl=("profit", "sum"),
                wr=("is_winner", "mean"),
            )
            # Hours with negative PnL and enough trades
            bad_hours = hourly[(hourly["pnl"] < 0) & (hourly["n"] >= 5)]
            if not bad_hours.empty:
                for hour in bad_hours.index:
                    # Validate OOS
                    if len(test) > 0 and "entry_hour_utc" in test.columns:
                        oos_hour = test[test["entry_hour_utc"] == hour]
                        if len(oos_hour) >= 3:
                            oos_pnl = oos_hour["profit"].sum()
                            oos_wr = oos_hour["is_winner"].mean()
                            is_pnl = bad_hours.loc[hour, "pnl"]
                            holds = oos_pnl < 0
                            status = "✓" if holds else "✗"
                            print(f"    Hour {int(hour):>2} UTC: IS=${is_pnl:+,.0f} "
                                  f"→ OOS=${oos_pnl:+,.0f} (WR={oos_wr:.0%}) {status}")

        # Find worst days (in-sample)
        if "entry_dow" in use_train.columns:
            daily = use_train.groupby("entry_dow").agg(
                n=("profit", "count"),
                pnl=("profit", "sum"),
                wr=("is_winner", "mean"),
            )
            bad_days = daily[(daily["pnl"] < 0) & (daily["n"] >= 5)]
            if not bad_days.empty:
                for day in bad_days.index:
                    if len(test) > 0 and "entry_dow" in test.columns:
                        oos_day = test[test["entry_dow"] == day]
                        if len(oos_day) >= 3:
                            oos_pnl = oos_day["profit"].sum()
                            is_pnl = bad_days.loc[day, "pnl"]
                            holds = oos_pnl < 0
                            status = "✓" if holds else "✗"
                            print(f"    {day:<10}: IS=${is_pnl:+,.0f} "
                                  f"→ OOS=${oos_pnl:+,.0f} {status}")


if __name__ == "__main__":
    print("Module 05: Session & Time Filter Analysis")
    print("Loading strategies...")

    all_trades = load_all_strategies()
    if not all_trades:
        print("No data loaded.")
        exit(1)

    for key, trades in all_trades.items():
        print(f"\n{'=' * 60}")
        print(f"  TIME ANALYSIS: {STRATEGIES[key]['name']}")
        print(f"{'=' * 60}")

        flagged_hours = hourly_pnl_heatmap(trades, key)
        flagged_days = dow_pnl_analysis(trades, key)
        session_window_analysis(trades, key)

        # Simulate removing flagged time slots
        if flagged_hours or flagged_days:
            filter_simulation(trades, key,
                            hours_to_remove=flagged_hours,
                            days_to_remove=flagged_days)

    auto_discover_filters(all_trades)

    print("\n✓ Module 05 complete.")
    print("  → Only implement filters that hold in OOS validation.")
    print("  → A filter removing <10% of trades with negative-PnL group is ideal.")
    print("  → Session filters are the cheapest complexity-wise — just skip hours in Pine Script.")
