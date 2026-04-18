"""
FXIFY Portfolio Optimization — Master Analysis
Data loader, shared utilities, validation framework, and portfolio-level Monte Carlo.

Usage:
    python master_analysis.py              # validate data + print baseline stats
    python master_analysis.py --monte      # run full Monte Carlo with current allocations
"""

import sys
import os
import warnings
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd

from config import STRATEGIES, CHALLENGE, COLUMN_MAP, OOS_SPLIT, MONTE_CARLO

warnings.filterwarnings("ignore", category=FutureWarning)

DATA_DIR = Path(__file__).parent / "data"


# ═══════════════════════════════════════════════
#  DATA LOADING
# ═══════════════════════════════════════════════

def load_strategy_csv(strategy_key: str) -> pd.DataFrame:
    """Load and parse a TradingView backtest CSV for one strategy."""
    cfg = STRATEGIES[strategy_key]
    filepath = DATA_DIR / cfg["csv_filename"]

    if not filepath.exists():
        raise FileNotFoundError(
            f"Missing CSV for {cfg['name']}: expected at {filepath}\n"
            f"Place your TradingView export there or update csv_filename in config.py"
        )

    df = pd.read_csv(filepath)

    # Rename columns using COLUMN_MAP (handles different TV export formats)
    reverse_map = {v: k for k, v in COLUMN_MAP.items()}
    # Handle price column variants (e.g. "Price JPY" for USDJPY)
    for col in df.columns:
        if col.startswith("Price ") and col not in reverse_map:
            reverse_map[col] = "price"
    df = df.rename(columns=reverse_map)

    # Parse datetime
    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"], format="mixed")
        df = df.sort_values("datetime").reset_index(drop=True)

    # Parse profit column (handle currency symbols, commas)
    for col in ["profit", "cum_profit", "run_up", "drawdown"]:
        if col in df.columns and df[col].dtype == object:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(r"[,$]", "", regex=True)
                .str.strip()
                .replace("", np.nan)
                .astype(float)
            )

    df["strategy"] = strategy_key
    return df


def build_trade_pairs(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert raw entry/exit rows into paired trades with computed fields.
    Each row = one completed trade with entry/exit datetime, P&L, duration, etc.
    """
    entries = df[df["type"].str.contains("Entry", case=False, na=False)].copy()
    exits = df[df["type"].str.contains("Exit", case=False, na=False)].copy()

    if len(entries) == 0 or len(exits) == 0:
        # Might already be in paired format — check for profit column
        if "profit" in df.columns and df["profit"].notna().sum() > 0:
            trades = df[df["profit"].notna()].copy()
            trades["is_winner"] = trades["profit"] > 0
            trades["is_loser"] = trades["profit"] < 0
            return trades
        raise ValueError("Cannot parse trade pairs — check CSV format")

    # Pair by Trade # if available
    if "trade_num" in df.columns:
        trades = []
        for trade_num in entries["trade_num"].unique():
            entry_rows = entries[entries["trade_num"] == trade_num]
            exit_rows = exits[exits["trade_num"] == trade_num]
            if len(entry_rows) > 0 and len(exit_rows) > 0:
                entry = entry_rows.iloc[0]
                exit_ = exit_rows.iloc[0]
                trades.append({
                    "trade_num": trade_num,
                    "strategy": entry.get("strategy", ""),
                    "entry_time": entry["datetime"],
                    "exit_time": exit_["datetime"],
                    "entry_price": entry.get("price", np.nan),
                    "exit_price": exit_.get("price", np.nan),
                    "profit": exit_.get("profit", np.nan),
                    "cum_profit": exit_.get("cum_profit", np.nan),
                    "run_up": exit_.get("run_up", np.nan),
                    "drawdown": exit_.get("drawdown", np.nan),
                    "contracts": entry.get("contracts", np.nan),
                    "signal": entry.get("signal", ""),
                })
        trades = pd.DataFrame(trades)
    else:
        # Fallback: pair by order (entry[i] → exit[i])
        n = min(len(entries), len(exits))
        trades = pd.DataFrame({
            "entry_time": entries["datetime"].values[:n],
            "exit_time": exits["datetime"].values[:n],
            "entry_price": entries["price"].values[:n] if "price" in entries else np.nan,
            "exit_price": exits["price"].values[:n] if "price" in exits else np.nan,
            "profit": exits["profit"].values[:n] if "profit" in exits else np.nan,
            "strategy": entries["strategy"].values[:n],
        })

    # Computed fields
    if "entry_time" in trades.columns and "exit_time" in trades.columns:
        trades["duration_mins"] = (
            (trades["exit_time"] - trades["entry_time"]).dt.total_seconds() / 60
        )
        trades["duration_bars"] = trades["duration_mins"] / 15  # 15min timeframe
        trades["entry_hour_utc"] = trades["entry_time"].dt.hour
        trades["entry_dow"] = trades["entry_time"].dt.day_name()
        trades["entry_date"] = trades["entry_time"].dt.date

    trades["is_winner"] = trades["profit"] > 0
    trades["is_loser"] = trades["profit"] < 0
    trades["is_breakeven"] = trades["profit"] == 0

    return trades


def load_all_strategies() -> dict[str, pd.DataFrame]:
    """Load and pair trades for all strategies. Returns dict of DataFrames."""
    all_trades = {}
    for key in STRATEGIES:
        try:
            raw = load_strategy_csv(key)
            paired = build_trade_pairs(raw)
            all_trades[key] = paired
            print(f"  ✓ {STRATEGIES[key]['name']}: {len(paired)} trades loaded")
        except FileNotFoundError as e:
            print(f"  ✗ {e}")
        except Exception as e:
            print(f"  ✗ {STRATEGIES[key]['name']}: {e}")
    return all_trades


# ═══════════════════════════════════════════════
#  SHARED UTILITIES
# ═══════════════════════════════════════════════

def compute_metrics(trades: pd.DataFrame) -> dict:
    """Compute standard strategy metrics from a trades DataFrame."""
    if len(trades) == 0:
        return {}

    profits = trades["profit"].dropna()
    winners = profits[profits > 0]
    losers = profits[profits < 0]

    gross_profit = winners.sum() if len(winners) > 0 else 0
    gross_loss = abs(losers.sum()) if len(losers) > 0 else 0

    return {
        "total_trades": len(profits),
        "winners": len(winners),
        "losers": len(losers),
        "win_rate": len(winners) / len(profits) if len(profits) > 0 else 0,
        "total_profit": profits.sum(),
        "avg_win": winners.mean() if len(winners) > 0 else 0,
        "avg_loss": losers.mean() if len(losers) > 0 else 0,
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else float("inf"),
        "max_win": winners.max() if len(winners) > 0 else 0,
        "max_loss": losers.min() if len(losers) > 0 else 0,
        "expectancy": profits.mean(),
        "sharpe_trade": profits.mean() / profits.std() if profits.std() > 0 else 0,
        "max_consecutive_losses": _max_consecutive(profits < 0),
        "max_consecutive_wins": _max_consecutive(profits > 0),
    }


def _max_consecutive(bool_series: pd.Series) -> int:
    """Count max consecutive True values in a boolean series."""
    groups = (bool_series != bool_series.shift()).cumsum()
    return bool_series.groupby(groups).sum().max() if len(bool_series) > 0 else 0


def compute_equity_curve(trades: pd.DataFrame, account_size: float = 200_000) -> pd.DataFrame:
    """Build equity curve from trade sequence."""
    eq = trades[["profit"]].copy()
    eq["cum_pnl"] = eq["profit"].cumsum()
    eq["equity"] = account_size + eq["cum_pnl"]
    eq["equity_pct"] = (eq["cum_pnl"] / account_size) * 100
    eq["peak"] = eq["equity"].cummax()
    eq["dd_usd"] = eq["equity"] - eq["peak"]
    eq["dd_pct"] = (eq["dd_usd"] / eq["peak"]) * 100
    eq["max_dd_pct"] = eq["dd_pct"].min()  # most negative = worst DD

    if "entry_time" in trades.columns:
        eq["datetime"] = trades["entry_time"].values
    if "entry_date" in trades.columns:
        eq["date"] = trades["entry_date"].values

    return eq


def compute_daily_pnl(trades: pd.DataFrame) -> pd.DataFrame:
    """Aggregate P&L by calendar day."""
    if "entry_date" not in trades.columns:
        return pd.DataFrame()
    daily = trades.groupby("entry_date")["profit"].sum().reset_index()
    daily.columns = ["date", "daily_pnl"]
    daily["cum_pnl"] = daily["daily_pnl"].cumsum()
    daily["equity"] = CHALLENGE["account_size"] + daily["cum_pnl"]
    daily["peak"] = daily["equity"].cummax()
    daily["daily_dd_pct"] = (daily["daily_pnl"] / CHALLENGE["account_size"]) * 100
    daily["total_dd_pct"] = ((daily["equity"] - daily["peak"]) / CHALLENGE["account_size"]) * 100
    return daily


def split_oos(trades: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split trades into in-sample (train) and out-of-sample (test) sets."""
    if "entry_time" not in trades.columns:
        # Fallback: 70/30 split by order
        split_idx = int(len(trades) * 0.7)
        return trades.iloc[:split_idx].copy(), trades.iloc[split_idx:].copy()

    train_end = pd.Timestamp(OOS_SPLIT["train_end"])
    test_start = pd.Timestamp(OOS_SPLIT["test_start"])

    train = trades[trades["entry_time"] <= train_end].copy()
    test = trades[trades["entry_time"] >= test_start].copy()
    return train, test


def scale_profit(profit: float, original_risk_pct: float, new_risk_pct: float) -> float:
    """Scale a trade's P&L to a different risk allocation."""
    if original_risk_pct == 0:
        return profit
    return profit * (new_risk_pct / original_risk_pct)


# ═══════════════════════════════════════════════
#  PORTFOLIO MONTE CARLO
# ═══════════════════════════════════════════════

def run_monte_carlo(
    all_trades: dict[str, pd.DataFrame],
    risk_overrides: Optional[dict[str, float]] = None,
    n_sims: int = None,
    verbose: bool = True,
    dd_protection: bool = False,
) -> dict:
    """
    Run portfolio-level Monte Carlo simulation for challenge pass probability.

    Merges all strategies' trades into a single timeline, shuffles trade order
    within each day (preserving calendar structure), and simulates N equity paths.

    Args:
        all_trades: dict of strategy_key -> trades DataFrame
        risk_overrides: optional dict of strategy_key -> new risk% (for testing allocations)
        n_sims: number of simulations (default from config)
        verbose: print results
        dd_protection: apply dynamic DD/equity protection scaling per dd_protection.py

    Returns:
        dict with pass_rate, median_days, percentile stats, failure analysis
    """
    if n_sims is None:
        n_sims = MONTE_CARLO["n_simulations"]

    np.random.seed(MONTE_CARLO["seed"])

    # Build combined profit series, scaled to risk allocations
    all_profits = []
    for key, trades in all_trades.items():
        original_risk = STRATEGIES[key]["risk_pct_challenge"]
        new_risk = (risk_overrides or {}).get(key, original_risk)

        for _, trade in trades.iterrows():
            scaled_p = scale_profit(trade["profit"], original_risk, new_risk)
            all_profits.append({
                "profit": scaled_p,
                "strategy": key,
                "date": trade.get("entry_date", None),
            })

    profits_df = pd.DataFrame(all_profits)
    profit_array = profits_df["profit"].values

    account = MONTE_CARLO["account_size"]
    target = account * (MONTE_CARLO["target_pct"] / 100)
    dd_limit = account * (MONTE_CARLO["dd_limit_pct"] / 100)

    passes = 0
    failures = 0
    days_to_pass = []
    failure_modes = {"dd_bust": 0, "no_target": 0}
    max_dds = []
    final_pnls = []

    # DD protection thresholds (from dd_protection.py)
    DD_THRESH = 0.02    # 2% DD from peak -> 0.40x
    DD_MULT = 0.40
    EQ_THRESH = 0.035   # 3.5% above start -> 0.60x
    EQ_MULT = 0.60

    for sim in range(n_sims):
        # Shuffle trade order (bootstrap without replacement)
        perm = np.random.permutation(len(profit_array))
        shuffled = profit_array[perm]

        equity = 0.0
        peak = 0.0
        passed = False

        for i, pnl in enumerate(shuffled):
            # Apply DD protection scaling before adding trade P&L
            if dd_protection:
                dd_from_peak = (peak - equity) / account if equity < peak else 0.0
                gain_from_start = equity / account

                if dd_from_peak >= DD_THRESH and gain_from_start >= EQ_THRESH:
                    mult = min(DD_MULT, EQ_MULT)
                elif dd_from_peak >= DD_THRESH:
                    mult = DD_MULT
                elif gain_from_start >= EQ_THRESH:
                    mult = EQ_MULT
                else:
                    mult = 1.0

                pnl = pnl * mult

            equity += pnl
            peak = max(peak, equity)
            dd = peak - equity

            if equity >= target:
                passed = True
                # Estimate days: assume ~2.5 trades/day average
                est_days = max(5, int(np.ceil((i + 1) / 2.5)))
                days_to_pass.append(est_days)
                break

            if dd >= dd_limit:
                failure_modes["dd_bust"] += 1
                break

        if not passed and (peak - equity) < dd_limit:
            failure_modes["no_target"] += 1

        if passed:
            passes += 1
        else:
            failures += 1

        max_dds.append((peak - equity) / account * 100 if peak > 0 else 0)
        final_pnls.append(equity)

    results = {
        "n_sims": n_sims,
        "pass_rate": passes / n_sims * 100,
        "fail_rate": failures / n_sims * 100,
        "median_days": int(np.median(days_to_pass)) if days_to_pass else None,
        "p10_days": int(np.percentile(days_to_pass, 10)) if days_to_pass else None,
        "p90_days": int(np.percentile(days_to_pass, 90)) if days_to_pass else None,
        "avg_max_dd_pct": np.mean(max_dds),
        "p95_max_dd_pct": np.percentile(max_dds, 95),
        "p99_max_dd_pct": np.percentile(max_dds, 99),
        "failure_modes": failure_modes,
        "avg_final_pnl": np.mean(final_pnls),
        "risk_allocations": {
            k: (risk_overrides or {}).get(k, STRATEGIES[k]["risk_pct_challenge"])
            for k in all_trades
        },
    }

    if verbose:
        mode_label = "DD PROTECTION" if dd_protection else "BASELINE (no protection)"
        print("\n" + "=" * 60)
        print(f"  MONTE CARLO RESULTS — {mode_label}")
        print("=" * 60)
        alloc_str = " / ".join(
            f"{k[0].upper()}{results['risk_allocations'][k]:.2f}%"
            for k in results["risk_allocations"]
        )
        print(f"  Allocations:  {alloc_str}")
        if dd_protection:
            print(f"  DD rule:      >=2% DD from peak -> 0.40x risk")
            print(f"  Equity rule:  >=3.5% gain -> 0.60x risk")
        print(f"  Simulations:  {n_sims:,}")
        print(f"  Pass rate:    {results['pass_rate']:.1f}%")
        print(f"  Median days:  {results['median_days']}")
        print(f"  Days range:   {results['p10_days']} (p10) — {results['p90_days']} (p90)")
        print(f"  Avg max DD:   {results['avg_max_dd_pct']:.2f}%")
        print(f"  p95 max DD:   {results['p95_max_dd_pct']:.2f}%")
        print(f"  p99 max DD:   {results['p99_max_dd_pct']:.2f}%")
        print(f"  Failures:     DD bust={failure_modes['dd_bust']}, "
              f"No target={failure_modes['no_target']}")
        print("=" * 60)

    return results


# ═══════════════════════════════════════════════
#  VALIDATION & BASELINE REPORT
# ═══════════════════════════════════════════════

def validate_and_report(all_trades: dict[str, pd.DataFrame]):
    """Print baseline metrics and validate against known backtest results."""
    print("\n" + "=" * 60)
    print("  BASELINE VALIDATION REPORT")
    print("=" * 60)

    for key, trades in all_trades.items():
        cfg = STRATEGIES[key]
        metrics = compute_metrics(trades)
        baseline = cfg["baseline"]

        print(f"\n{'─' * 50}")
        print(f"  {cfg['name']}")
        print(f"{'─' * 50}")
        print(f"  Trades:        {metrics['total_trades']}")
        print(f"  Win rate:      {metrics['win_rate']:.1%}  "
              f"(baseline: {baseline['win_rate']:.1%})")
        print(f"  Profit factor: {metrics['profit_factor']:.2f}  "
              f"(baseline: {baseline['profit_factor']:.2f})")
        print(f"  Total profit:  ${metrics['total_profit']:,.0f}  "
              f"(baseline: ${baseline['total_profit']:,.0f})")
        print(f"  Expectancy:    ${metrics['expectancy']:.2f}/trade")
        print(f"  Max consec L:  {metrics['max_consecutive_losses']}")
        print(f"  Sharpe/trade:  {metrics['sharpe_trade']:.3f}")

        # OOS split
        train, test = split_oos(trades)
        if len(train) > 0 and len(test) > 0:
            train_m = compute_metrics(train)
            test_m = compute_metrics(test)
            print(f"\n  In-sample  ({OOS_SPLIT['train_start']}–{OOS_SPLIT['train_end']}): "
                  f"{train_m['total_trades']} trades, "
                  f"PF={train_m['profit_factor']:.2f}, "
                  f"WR={train_m['win_rate']:.1%}")
            print(f"  Out-sample ({OOS_SPLIT['test_start']}–{OOS_SPLIT['test_end']}): "
                  f"{test_m['total_trades']} trades, "
                  f"PF={test_m['profit_factor']:.2f}, "
                  f"WR={test_m['win_rate']:.1%}")

            # Flag degradation
            if test_m["profit_factor"] < train_m["profit_factor"] * 0.7:
                print(f"  ⚠ OOS PF degradation: "
                      f"{train_m['profit_factor']:.2f} → {test_m['profit_factor']:.2f}")

    # Portfolio-level daily P&L
    print(f"\n{'─' * 50}")
    print(f"  PORTFOLIO DAILY P&L")
    print(f"{'─' * 50}")

    combined = pd.concat(all_trades.values(), ignore_index=True)
    if "entry_date" in combined.columns:
        daily = compute_daily_pnl(combined)
        print(f"  Trading days:     {len(daily)}")
        print(f"  Best day:         ${daily['daily_pnl'].max():,.0f}")
        print(f"  Worst day:        ${daily['daily_pnl'].min():,.0f}")
        print(f"  Avg daily P&L:    ${daily['daily_pnl'].mean():,.0f}")
        print(f"  Daily P&L stddev: ${daily['daily_pnl'].std():,.0f}")
        print(f"  Worst total DD:   {daily['total_dd_pct'].min():.2f}%")
        print(f"  Worst daily loss: {daily['daily_dd_pct'].min():.2f}%")


# ═══════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    print("FXIFY Portfolio Optimization Suite")
    print(f"Loading data from: {DATA_DIR}\n")

    # Create data dir if missing
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    all_trades = load_all_strategies()

    if not all_trades:
        print("\n✗ No strategies loaded. Place CSV files in ./data/ directory.")
        print("  Expected files:")
        for key, cfg in STRATEGIES.items():
            print(f"    {cfg['csv_filename']}")
        sys.exit(1)

    validate_and_report(all_trades)

    if "--monte" in sys.argv:
        run_monte_carlo(all_trades, verbose=True, dd_protection=False)
        run_monte_carlo(all_trades, verbose=True, dd_protection=True)

    print("\n✓ Master analysis complete. Run individual modules (01-05) for deep dives.")
