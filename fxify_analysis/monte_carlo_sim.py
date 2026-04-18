"""
Monte Carlo Simulation — FXIFY $200K Challenge Portfolio
=========================================================
Strategies: Guardian Gold v3.7, Striker DJ30 v4.1, Aegis-Reversion v4
Parameters: $200K account, 5% profit target ($10K), 5% static DD ($10K),
            5% daily loss limit ($10K), min 5 trading days, 10K simulations.
            No time limit — inactivity breach only if 60 days with no trade.
Schedule:   Guardian Mon/Tue/Thu, Striker Tue/Fri, Aegis Mon/Tue/Wed
Risk:       G 0.30%, S 0.70%, A 0.75%
"""

import csv
import os
import random
import statistics
from collections import defaultdict
from datetime import datetime

import numpy as np

# --Configuration --────────────────────────────────────────────────────────
ACCOUNT_SIZE = 200_000
PROFIT_TARGET = 10_000       # 5%
DD_LIMIT = 10_000            # 5% static from starting balance
DAILY_LOSS_LIMIT = 10_000    # 5% daily loss limit
MIN_TRADING_DAYS = 5
INACTIVITY_LIMIT = 60        # breach if 60 calendar days with no trade
MAX_CALENDAR_DAYS = 365      # hard safety cap (should never hit with active portfolio)
NUM_SIMS = 10_000
SEED = 42

# Day-of-week schedule (0=Mon .. 4=Fri)
SCHEDULE = {
    "guardian": {0, 1, 3},      # Mon, Tue, Thu
    "striker":  {1, 4},          # Tue, Fri
    "aegis":    {0, 1, 2},       # Mon, Tue, Wed
}

CSV_FILES = {
    "guardian": "Guardian_Gold_v3.7_FXIFY_OANDA_XAUUSD_2026-04-10_c5683.csv",
    "striker":  "Striker_DJ30_v4.1_FINAL_VANTAGE_DJ30_2026-04-10_03f6f.csv",
    "aegis":    "Aegis-Reversion_USDJPY_v4_OANDA_USDJPY_2026-04-10_318eb.csv",
}


def parse_trades(filepath):
    """Parse TradingView CSV, return list of (date, pnl_usd, cumul_pnl_before) for Exit rows."""
    trades = []
    prev_cumul = 0.0
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            if len(row) < 14:
                continue
            trade_type = row[1].strip()
            if "Exit" not in trade_type:
                continue
            date_str = row[2].strip()
            pnl_usd = float(row[7])
            cumul_pnl = float(row[13])
            # cumul_pnl_before = cumul_pnl - pnl_usd for this trade
            cumul_before = cumul_pnl - pnl_usd
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
            trades.append({
                "date": dt,
                "weekday": dt.weekday(),
                "pnl_usd": pnl_usd,
                "cumul_before": cumul_before,
            })
    return trades


def normalize_trades(trades):
    """Normalize each trade's P&L to a flat $200K account.

    The backtest compounds, so later trades have inflated P&L.
    Normalize: pnl_normalized = pnl_raw * (200000 / (200000 + cumul_pnl_before))
    """
    normalized = []
    for t in trades:
        equity_at_trade = ACCOUNT_SIZE + t["cumul_before"]
        if equity_at_trade <= 0:
            continue
        scale = ACCOUNT_SIZE / equity_at_trade
        normalized.append(t["pnl_usd"] * scale)
    return normalized


def compute_trade_frequency(trades):
    """Compute average trades per active day and the distribution of trades-per-day."""
    day_counts = defaultdict(int)
    for t in trades:
        day_key = t["date"].date()
        day_counts[day_key] += 1

    counts = list(day_counts.values())
    if not counts:
        return 0.0, []

    # Total trading days in the ~4yr period (approximate from date range)
    first_date = min(t["date"] for t in trades).date()
    last_date = max(t["date"] for t in trades).date()
    total_days = (last_date - first_date).days + 1

    # Count how many of the scheduled weekdays existed in the period
    # We'll return: P(trade fires on an active day), and trades-per-day distribution
    return counts, total_days, first_date, last_date


def analyze_strategy(name, filepath):
    """Full analysis of a single strategy."""
    trades = parse_trades(filepath)
    normalized_pnl = normalize_trades(trades)

    # Day-of-week distribution of trades
    dow_counts = defaultdict(int)
    day_trade_counts = defaultdict(int)  # date -> num trades
    for t in trades:
        dow_counts[t["weekday"]] += 1
        day_trade_counts[t["date"].date()] += 1

    # Trades per active day distribution
    trades_per_day = list(day_trade_counts.values())

    # Date range for calculating trade probability
    first_date = min(t["date"] for t in trades).date()
    last_date = max(t["date"] for t in trades).date()

    # Count scheduled weekdays in the period
    from datetime import timedelta
    scheduled_days = SCHEDULE[name]
    total_scheduled_days = 0
    d = first_date
    while d <= last_date:
        if d.weekday() in scheduled_days:
            total_scheduled_days += 1
        d += timedelta(days=1)

    active_days = len(day_trade_counts)
    trade_probability = active_days / total_scheduled_days if total_scheduled_days > 0 else 0

    print(f"\n{'='*60}")
    print(f"  {name.upper()} — {os.path.basename(filepath)}")
    print(f"{'='*60}")
    print(f"  Total trades:          {len(trades)}")
    print(f"  Date range:            {first_date} -> {last_date}")
    print(f"  Scheduled days:        {total_scheduled_days}")
    print(f"  Days with trades:      {active_days}")
    print(f"  P(trade on sched day): {trade_probability:.2%}")
    print(f"  Trades/active day:     mean={np.mean(trades_per_day):.2f}, "
          f"median={np.median(trades_per_day):.1f}, max={max(trades_per_day)}")
    print(f"  Normalized P&L stats:")
    print(f"    Mean:    ${np.mean(normalized_pnl):,.2f}")
    print(f"    Median:  ${np.median(normalized_pnl):,.2f}")
    print(f"    StdDev:  ${np.std(normalized_pnl):,.2f}")
    print(f"    Min:     ${min(normalized_pnl):,.2f}")
    print(f"    Max:     ${max(normalized_pnl):,.2f}")
    print(f"    Win rate:{sum(1 for p in normalized_pnl if p > 0)/len(normalized_pnl):.1%}")

    return {
        "name": name,
        "pnl_pool": np.array(normalized_pnl),
        "trades_per_day": trades_per_day,
        "trade_probability": trade_probability,
    }


def run_simulation(strategies, num_sims=NUM_SIMS, seed=SEED):
    """Run Monte Carlo simulation."""
    rng = np.random.default_rng(seed)

    # Pre-compute trades-per-day distributions as arrays
    for s in strategies.values():
        s["tpd_array"] = np.array(s["trades_per_day"])

    results = []

    for sim in range(num_sims):
        equity = 0.0  # relative to starting $200K
        max_dd_from_start = 0.0  # static DD = drop from starting balance
        worst_daily_loss = 0.0
        trading_days = 0
        calendar_day = 0
        days_since_last_trade = 0
        weekday = 0  # start on Monday
        daily_pnl_list = []

        outcome = None

        while calendar_day < MAX_CALENDAR_DAYS:
            # Skip weekends
            if weekday >= 5:
                weekday = (weekday + 1) % 7
                calendar_day += 1
                days_since_last_trade += 1
                # Check inactivity (weekends still count toward 60-day clock)
                if days_since_last_trade >= INACTIVITY_LIMIT:
                    outcome = "fail_inactive"
                    break
                continue

            daily_pnl = 0.0
            traded_today = False

            for sname, sdata in strategies.items():
                # Check if this strategy is active today
                if weekday not in SCHEDULE[sname]:
                    continue

                # Determine if a trade fires (based on historical probability)
                if rng.random() > sdata["trade_probability"]:
                    continue

                # How many trades today? Sample from historical distribution
                num_trades = rng.choice(sdata["tpd_array"])

                # Sample trades from the P&L pool
                trade_pnls = rng.choice(sdata["pnl_pool"], size=num_trades)
                daily_pnl += trade_pnls.sum()
                traded_today = True

            if traded_today:
                trading_days += 1
                days_since_last_trade = 0
                equity += daily_pnl
                daily_pnl_list.append(daily_pnl)

                # Check daily loss limit first
                if daily_pnl <= -DAILY_LOSS_LIMIT:
                    worst_daily_loss = min(worst_daily_loss, daily_pnl)
                    outcome = "fail_daily"
                    break

                # Static DD: how far below starting balance
                if equity < 0:
                    max_dd_from_start = max(max_dd_from_start, -equity)

                # Worst single daily loss
                if daily_pnl < worst_daily_loss:
                    worst_daily_loss = daily_pnl

                # Check DD limit (static from start)
                if max_dd_from_start >= DD_LIMIT:
                    outcome = "fail_dd"
                    break

                # Check profit target (must have min trading days)
                if equity >= PROFIT_TARGET and trading_days >= MIN_TRADING_DAYS:
                    outcome = "pass"
                    break
            else:
                days_since_last_trade += 1

            # Check inactivity
            if days_since_last_trade >= INACTIVITY_LIMIT:
                outcome = "fail_inactive"
                break

            weekday = (weekday + 1) % 7
            calendar_day += 1

        # If we hit the hard safety cap without resolution
        if outcome is None:
            outcome = "timeout"

        results.append({
            "outcome": outcome,
            "equity": equity,
            "max_dd": max_dd_from_start,
            "worst_daily": worst_daily_loss,
            "trading_days": trading_days,
            "calendar_days": calendar_day,
            "daily_pnls": daily_pnl_list,
        })

    return results


def report(results):
    """Print simulation results."""
    n = len(results)
    passes = [r for r in results if r["outcome"] == "pass"]
    fails_dd = [r for r in results if r["outcome"] == "fail_dd"]
    fails_daily = [r for r in results if r["outcome"] == "fail_daily"]
    fails_inactive = [r for r in results if r["outcome"] == "fail_inactive"]
    timeouts = [r for r in results if r["outcome"] == "timeout"]

    pass_rate = len(passes) / n * 100
    fail_dd_rate = len(fails_dd) / n * 100
    fail_daily_rate = len(fails_daily) / n * 100
    fail_inactive_rate = len(fails_inactive) / n * 100
    timeout_rate = len(timeouts) / n * 100
    total_fail_rate = (len(fails_dd) + len(fails_daily) + len(fails_inactive) + len(timeouts)) / n * 100

    print(f"\n{'#'*60}")
    print(f"  MONTE CARLO RESULTS -- {n:,} simulations")
    print(f"{'#'*60}")
    print(f"\n  -- Outcome Rates --")
    print(f"  Pass (hit $10K target):    {len(passes):,} ({pass_rate:.1f}%)")
    print(f"  Fail - static DD breach:   {len(fails_dd):,} ({fail_dd_rate:.1f}%)")
    print(f"  Fail - daily loss breach:  {len(fails_daily):,} ({fail_daily_rate:.1f}%)")
    print(f"  Fail - 60d inactivity:     {len(fails_inactive):,} ({fail_inactive_rate:.1f}%)")
    print(f"  Timeout ({MAX_CALENDAR_DAYS}d safety cap):   {len(timeouts):,} ({timeout_rate:.1f}%)")
    print(f"  Total fail rate:           {total_fail_rate:.1f}%")

    if passes:
        pass_days = [r["trading_days"] for r in passes]
        pass_cal = [r["calendar_days"] for r in passes]
        print(f"\n  --Days to Target (passing sims) --")
        print(f"  Trading days:  median={int(np.median(pass_days))}, "
              f"mean={np.mean(pass_days):.1f}, "
              f"P10={int(np.percentile(pass_days, 10))}, "
              f"P90={int(np.percentile(pass_days, 90))}")
        print(f"  Calendar days: median={int(np.median(pass_cal))}, "
              f"mean={np.mean(pass_cal):.1f}, "
              f"P10={int(np.percentile(pass_cal, 10))}, "
              f"P90={int(np.percentile(pass_cal, 90))}")

    # DD distribution across ALL sims
    all_dd = [r["max_dd"] for r in results]
    print(f"\n  --Max Drawdown Distribution (all sims) --")
    for p in [10, 25, 50, 75, 90, 95, 99]:
        val = np.percentile(all_dd, p)
        pct = val / ACCOUNT_SIZE * 100
        print(f"  P{p:02d}: ${val:>8,.2f}  ({pct:.2f}% of account)")

    # Worst daily loss distribution
    all_worst = [r["worst_daily"] for r in results]
    print(f"\n  --Worst Single-Day Loss Distribution --")
    for p in [50, 75, 90, 95, 99]:
        val = np.percentile(all_worst, p)
        pct = abs(val) / ACCOUNT_SIZE * 100
        print(f"  P{p:02d}: ${val:>9,.2f}  ({pct:.2f}% of account)")

    # Daily P&L statistics (from all sims)
    all_daily = []
    for r in results:
        all_daily.extend(r["daily_pnls"])
    if all_daily:
        all_daily = np.array(all_daily)
        print(f"\n  --Daily P&L Statistics (all trading days, all sims) --")
        print(f"  Mean:   ${np.mean(all_daily):>9,.2f}")
        print(f"  Median: ${np.median(all_daily):>9,.2f}")
        print(f"  StdDev: ${np.std(all_daily):>9,.2f}")
        print(f"  Worst:  ${np.min(all_daily):>9,.2f}")
        print(f"  Best:   ${np.max(all_daily):>9,.2f}")

    # Risk thresholds: probability of daily loss exceeding X
    print(f"\n  --Daily Loss Risk Thresholds --")
    for threshold in [1000, 2000, 3000, 4000, 5000]:
        pct_account = threshold / ACCOUNT_SIZE * 100
        count = sum(1 for d in all_daily if d < -threshold)
        prob = count / len(all_daily) * 100
        print(f"  P(daily loss > ${threshold:,}) [{pct_account:.1f}%]: {prob:.2f}% of days")

    # Final equity distribution for all sims
    all_equity = [r["equity"] for r in results]
    print(f"\n  --Final Equity Change (all sims) --")
    for p in [5, 25, 50, 75, 95]:
        val = np.percentile(all_equity, p)
        print(f"  P{p:02d}: ${val:>9,.2f}")

    print(f"\n  --Comparison to Previous MC --")
    print(f"  Previous: 97.9% pass rate, 14 median trading days")
    print(f"  Current:  {pass_rate:.1f}% pass rate, "
          f"{int(np.median([r['trading_days'] for r in passes])) if passes else 'N/A'} median trading days")

    delta = pass_rate - 97.9
    print(f"  Delta:    {'+' if delta >= 0 else ''}{delta:.1f}pp pass rate")
    print()


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    print("Loading and analyzing backtest CSVs...")
    strategies = {}
    for name, csvfile in CSV_FILES.items():
        strategies[name] = analyze_strategy(name, csvfile)

    print(f"\nRunning {NUM_SIMS:,} Monte Carlo simulations...")
    results = run_simulation(strategies, NUM_SIMS, SEED)
    report(results)


if __name__ == "__main__":
    main()
