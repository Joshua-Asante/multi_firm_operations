"""
Module 02 — Losing Trade Pattern Mining

Searches for filterable patterns among losing trades that don't overlap
with winning trades. If 10-15% of losers share a pattern that isn't
also shared by winners, filtering them could improve PF and reduce DD.

Dimensions analyzed:
  - Time of day (entry hour)
  - Day of week
  - Duration (bars held)
  - Streak position (loss after N wins, etc.)
  - Consecutive loss sequences
  - Trade size relative to ATR (if available via run_up/drawdown)

Usage:
    python 02_losing_trade_patterns.py
"""

import numpy as np
import pandas as pd
from scipy import stats
from itertools import combinations

from config import STRATEGIES, OOS_SPLIT
from master_analysis import (
    load_all_strategies, compute_metrics, split_oos, compute_equity_curve
)


def add_derived_features(trades: pd.DataFrame) -> pd.DataFrame:
    """Add computed features for pattern mining."""
    df = trades.copy()

    # Streak tracking
    df["prev_result"] = df["is_winner"].shift(1)
    df["streak_count"] = 0
    streak = 0
    prev_win = None
    streaks = []
    for _, row in df.iterrows():
        if prev_win is None:
            streak = 0
        elif row["is_winner"] == prev_win:
            streak += 1
        else:
            streak = 0
        streaks.append(streak)
        prev_win = row["is_winner"]
    df["streak_count"] = streaks

    # Position in sequence
    df["trade_index"] = range(len(df))
    df["trade_pct"] = df["trade_index"] / len(df)  # 0-1 position in backtest

    # Recent performance (rolling windows)
    df["rolling_5_pnl"] = df["profit"].rolling(5, min_periods=1).sum().shift(1)
    df["rolling_10_pnl"] = df["profit"].rolling(10, min_periods=1).sum().shift(1)
    df["rolling_5_wr"] = df["is_winner"].rolling(5, min_periods=1).mean().shift(1)

    # Profit magnitude features
    if "run_up" in df.columns and df["run_up"].notna().sum() > 0:
        df["mae_ratio"] = df["drawdown"].abs() / (df["run_up"].abs() + 1e-10)
        df["mfe_ratio"] = df["run_up"].abs() / (df["drawdown"].abs() + 1e-10)

    # Duration buckets
    if "duration_bars" in df.columns:
        df["duration_bucket"] = pd.cut(
            df["duration_bars"],
            bins=[0, 2, 5, 10, 20, 40, 100, float("inf")],
            labels=["1-2", "3-5", "6-10", "11-20", "21-40", "41-100", "100+"]
        )

    # Hour buckets
    if "entry_hour_utc" in df.columns:
        df["session"] = pd.cut(
            df["entry_hour_utc"],
            bins=[-1, 7, 13, 16, 22, 24],
            labels=["Asian", "London", "Overlap", "NY_PM", "After_Hours"]
        )

    return df


def analyze_single_dimension(
    trades: pd.DataFrame,
    feature: str,
    strategy_name: str,
) -> list[dict]:
    """
    For a given feature column, find values where losers are disproportionately
    concentrated vs winners.
    """
    findings = []
    if feature not in trades.columns:
        return findings
    if trades[feature].isna().all():
        return findings

    # Group by feature value
    for value, group in trades.groupby(feature):
        n_total = len(group)
        n_losers = group["is_loser"].sum()
        n_winners = group["is_winner"].sum()

        if n_total < 5:  # minimum sample
            continue

        loss_rate = n_losers / n_total
        overall_loss_rate = trades["is_loser"].sum() / len(trades)

        # Is this value significantly worse than average?
        if loss_rate > overall_loss_rate + 0.05 and n_total >= 8:
            # Chi-squared test for significance
            observed = [n_winners, n_losers]
            expected_wr = 1 - overall_loss_rate
            expected = [n_total * expected_wr, n_total * (1 - expected_wr)]
            try:
                chi2, p_value = stats.chisquare(observed, expected)
            except Exception:
                p_value = 1.0

            if n_losers > 0:
                avg_loss_here = group[group["is_loser"]]["profit"].mean()
                avg_loss_overall = trades[trades["is_loser"]]["profit"].mean()
            else:
                avg_loss_here = 0
                avg_loss_overall = 0

            findings.append({
                "strategy": strategy_name,
                "feature": feature,
                "value": value,
                "total_trades": n_total,
                "losers": n_losers,
                "winners": n_winners,
                "loss_rate": loss_rate,
                "overall_loss_rate": overall_loss_rate,
                "excess_loss_rate": loss_rate - overall_loss_rate,
                "p_value": p_value,
                "avg_loss_this_group": avg_loss_here,
                "avg_loss_overall": avg_loss_overall,
                "total_pnl_this_group": group["profit"].sum(),
                "pct_of_all_trades": n_total / len(trades) * 100,
            })

    return findings


def analyze_two_dimension_combos(
    trades: pd.DataFrame,
    features: list[str],
    strategy_name: str,
    min_trades: int = 8,
) -> list[dict]:
    """
    Find 2-feature combos that concentrate losers.
    E.g., "Monday + first 2 hours" might be worse than either alone.
    """
    findings = []
    valid_features = [f for f in features if f in trades.columns
                      and not trades[f].isna().all()]

    for f1, f2 in combinations(valid_features, 2):
        for (v1, v2), group in trades.groupby([f1, f2]):
            n_total = len(group)
            if n_total < min_trades:
                continue

            n_losers = group["is_loser"].sum()
            loss_rate = n_losers / n_total
            overall_loss_rate = trades["is_loser"].sum() / len(trades)

            if loss_rate > overall_loss_rate + 0.10 and n_losers >= 4:
                findings.append({
                    "strategy": strategy_name,
                    "feature_combo": f"{f1}={v1} & {f2}={v2}",
                    "total_trades": n_total,
                    "losers": n_losers,
                    "loss_rate": loss_rate,
                    "excess_loss_rate": loss_rate - overall_loss_rate,
                    "total_pnl": group["profit"].sum(),
                    "pct_of_all_trades": n_total / len(trades) * 100,
                })

    return sorted(findings, key=lambda x: x["excess_loss_rate"], reverse=True)


def filter_impact_analysis(
    trades: pd.DataFrame,
    filter_mask: pd.Series,
    label: str,
) -> dict:
    """
    Compute before/after metrics if we filter out trades matching the mask.
    """
    before = compute_metrics(trades)
    filtered = trades[~filter_mask]
    after = compute_metrics(filtered)
    removed = trades[filter_mask]

    return {
        "label": label,
        "trades_removed": filter_mask.sum(),
        "pct_removed": filter_mask.sum() / len(trades) * 100,
        "pnl_removed": removed["profit"].sum() if len(removed) > 0 else 0,
        "before_pf": before["profit_factor"],
        "after_pf": after["profit_factor"],
        "before_wr": before["win_rate"],
        "after_wr": after["win_rate"],
        "before_total": before["total_profit"],
        "after_total": after["total_profit"],
        "pf_change": after["profit_factor"] - before["profit_factor"],
        "wr_change": after["win_rate"] - before["win_rate"],
        "profit_change": after["total_profit"] - before["total_profit"],
    }


def run_pattern_mining(all_trades: dict[str, pd.DataFrame]):
    """Main analysis: mine losing trade patterns for each strategy."""
    
    single_features = [
        "entry_hour_utc", "entry_dow", "duration_bucket", "session",
        "streak_count",
    ]
    combo_features = ["entry_hour_utc", "entry_dow", "session", "duration_bucket"]

    for key, trades in all_trades.items():
        name = STRATEGIES[key]["name"]
        print(f"\n{'=' * 60}")
        print(f"  LOSING TRADE PATTERNS: {name}")
        print(f"{'=' * 60}")

        df = add_derived_features(trades)
        train, test = split_oos(df)

        if len(train) == 0:
            print("  No in-sample data available. Using full dataset (⚠ no OOS validation).")
            train = df

        # ── Single dimension analysis ──
        print(f"\n  ── Single-Feature Patterns (in-sample) ──")
        all_findings = []
        for feat in single_features:
            findings = analyze_single_dimension(train, feat, name)
            all_findings.extend(findings)

        # Sort by excess loss rate
        all_findings = sorted(all_findings, key=lambda x: x["excess_loss_rate"], reverse=True)

        if not all_findings:
            print("  No significant single-feature patterns found.")
        else:
            print(f"\n  {'Feature':<18} {'Value':<12} {'Trades':>7} {'LossRate':>9} "
                  f"{'Excess':>8} {'p-val':>8} {'GroupPnL':>10}")
            print(f"  {'─' * 76}")
            for f in all_findings[:15]:
                sig = "**" if f["p_value"] < 0.05 else "  "
                print(f"  {f['feature']:<18} {str(f['value']):<12} {f['total_trades']:>7} "
                      f"{f['loss_rate']:>8.1%} {f['excess_loss_rate']:>+7.1%} "
                      f"{f['p_value']:>8.3f} ${f['total_pnl_this_group']:>9,.0f} {sig}")

        # ── Two-dimension combos ──
        print(f"\n  ── Two-Feature Combo Patterns (in-sample) ──")
        combo_findings = analyze_two_dimension_combos(train, combo_features, name)

        if not combo_findings:
            print("  No significant two-feature patterns found.")
        else:
            for cf in combo_findings[:10]:
                print(f"  {cf['feature_combo']:<40} "
                      f"N={cf['total_trades']:>3} "
                      f"LR={cf['loss_rate']:.1%} "
                      f"Excess={cf['excess_loss_rate']:>+.1%} "
                      f"PnL=${cf['total_pnl']:>,.0f}")

        # ── OOS Validation of top patterns ──
        if len(test) > 0 and all_findings:
            print(f"\n  ── OOS Validation ──")
            for f in all_findings[:5]:
                if f["p_value"] < 0.10:
                    # Build filter mask on test set
                    feat = f["feature"]
                    val = f["value"]
                    if feat in test.columns:
                        oos_group = test[test[feat] == val]
                        if len(oos_group) >= 3:
                            oos_lr = oos_group["is_loser"].mean()
                            oos_overall = test["is_loser"].mean()
                            holds = oos_lr > oos_overall
                            status = "✓ HOLDS" if holds else "✗ FAILS"
                            print(f"  {feat}={val}: OOS LR={oos_lr:.1%} "
                                  f"vs overall={oos_overall:.1%} → {status}")

        # ── Filter impact simulation ──
        if all_findings:
            print(f"\n  ── Filter Impact Analysis (full dataset) ──")
            sig_findings = [f for f in all_findings if f["p_value"] < 0.10]
            for f in sig_findings[:5]:
                feat = f["feature"]
                val = f["value"]
                if feat in df.columns:
                    mask = df[feat] == val
                    impact = filter_impact_analysis(df, mask, f"{feat}={val}")
                    direction = "↑" if impact["pf_change"] > 0 else "↓"
                    print(f"  Filter out {impact['label']}: "
                          f"PF {impact['before_pf']:.2f}→{impact['after_pf']:.2f} {direction} "
                          f"| WR {impact['before_wr']:.1%}→{impact['after_wr']:.1%} "
                          f"| Removed {impact['trades_removed']} trades "
                          f"({impact['pct_removed']:.1f}%) "
                          f"| PnL impact: ${impact['profit_change']:>+,.0f}")


def run_streak_analysis(all_trades: dict[str, pd.DataFrame]):
    """Analyze how strategies perform based on recent streaks."""
    print(f"\n{'=' * 60}")
    print(f"  STREAK & MOMENTUM ANALYSIS")
    print(f"{'=' * 60}")

    for key, trades in all_trades.items():
        name = STRATEGIES[key]["name"]
        df = add_derived_features(trades)

        print(f"\n  {name}:")

        # Performance after N consecutive losses
        for n_losses in [1, 2, 3, 4]:
            # Find trades that follow exactly N consecutive losses
            after_streak = df[
                (df["streak_count"] >= n_losses) &
                (df["prev_result"] == False)  # previous was a loss
            ].shift(-1).dropna(subset=["profit"])

            if len(after_streak) >= 5:
                wr = after_streak["is_winner"].mean()
                avg_pnl = after_streak["profit"].mean()
                print(f"    After {n_losses} consecutive losses: "
                      f"WR={wr:.1%}, Avg=${avg_pnl:,.0f}, N={len(after_streak)}")

        # Performance when rolling 5-trade P&L is negative
        if "rolling_5_pnl" in df.columns:
            cold_trades = df[df["rolling_5_pnl"] < 0]
            hot_trades = df[df["rolling_5_pnl"] > 0]
            if len(cold_trades) > 10 and len(hot_trades) > 10:
                cold_wr = cold_trades["is_winner"].mean()
                hot_wr = hot_trades["is_winner"].mean()
                print(f"    Cold streak (5-trade PnL < 0): "
                      f"WR={cold_wr:.1%}, N={len(cold_trades)}")
                print(f"    Hot streak  (5-trade PnL > 0): "
                      f"WR={hot_wr:.1%}, N={len(hot_trades)}")


if __name__ == "__main__":
    print("Module 02: Losing Trade Pattern Mining")
    print("Loading strategies...")

    all_trades = load_all_strategies()
    if not all_trades:
        print("No data loaded.")
        exit(1)

    run_pattern_mining(all_trades)
    run_streak_analysis(all_trades)

    print("\n✓ Module 02 complete.")
    print("  → Only act on patterns that hold in OOS validation.")
    print("  → Patterns removing <5% of trades with significant PF improvement are ideal.")
    print("  → Never filter based on p > 0.10 — that's noise, not signal.")
