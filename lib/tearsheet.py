"""HTML tearsheet generator for DXTrade trade history.

Pairs csv_parser.parse_dxtrade_csv with quantstats' standard prop-firm
metrics (Sharpe, Sortino, max DD, win rate, monthly heatmap, equity
curve). Output is a single self-contained HTML file.

quantstats benchmark is forced to None — the SPY default would require
yfinance network access and isn't relevant to prop-firm analysis.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from csv_parser import Trade, parse_dxtrade_csv


def trades_to_returns(trades: list[Trade], starting_equity: float) -> pd.Series:
    """Convert a list of Trade objects to a daily returns series.

    Daily P&L is summed by exit-time date and divided by starting_equity.
    The series is reindexed onto a business-day range so weekends don't
    dilute the Sharpe ratio.
    """
    if not trades:
        raise ValueError("No trades to convert")
    pnl_by_day: dict[pd.Timestamp, float] = {}
    for t in trades:
        day = pd.Timestamp(t.exit_time.date())
        pnl_by_day[day] = pnl_by_day.get(day, 0.0) + t.net_pnl
    series = pd.Series(pnl_by_day, dtype=float).sort_index()
    bdays = pd.bdate_range(series.index.min(), series.index.max())
    series = series.reindex(bdays).fillna(0.0)
    return series / starting_equity


def from_trades(trades: list[Trade], starting_equity: float, out_path: Path,
                title: str = "Prop Firm Tearsheet") -> Path:
    """Generate an HTML tearsheet from a list of Trade objects."""
    import quantstats as qs
    returns = trades_to_returns(trades, starting_equity)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    qs.reports.html(returns, output=str(out_path), benchmark=None, title=title)
    return out_path


def from_csv(csv_path: Path | str, starting_equity: float, out_path: Path,
             title: str = "Prop Firm Tearsheet") -> Path:
    """Generate a tearsheet from a DXTrade CSV path."""
    trades = parse_dxtrade_csv(str(csv_path))
    if not trades:
        raise ValueError(f"No trades parsed from {csv_path}")
    return from_trades(trades, starting_equity, out_path, title=title)
