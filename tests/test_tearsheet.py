"""Tests for lib/tearsheet.

trades_to_returns is the load-bearing logic — daily P&L bucketing, business-
day reindexing, division by starting equity. The HTML generation path is a
quantstats passthrough; we run it once end-to-end to confirm the call wires
correctly but rely on quantstats for the report content.
"""

import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from csv_parser import Trade
from lib.tearsheet import from_trades, trades_to_returns


def _make_trade(exit_dt: datetime, net_pnl: float) -> Trade:
    return Trade(
        trade_id=str(int(exit_dt.timestamp())),
        instrument="XAUUSD",
        direction="long",
        lots=0.1,
        entry_time=exit_dt,
        entry_price=2000.0,
        exit_time=exit_dt,
        exit_price=2010.0,
        pnl=net_pnl,
        net_pnl=net_pnl,
    )


def test_returns_basic_two_day():
    trades = [
        _make_trade(datetime(2024, 1, 2, 11, 0), 100.0),
        _make_trade(datetime(2024, 1, 3, 11, 0), -100.0),
    ]
    returns = trades_to_returns(trades, starting_equity=100_000.0)
    assert len(returns) == 2
    assert returns.iloc[0] == pytest.approx(0.001)
    assert returns.iloc[1] == pytest.approx(-0.001)


def test_returns_buckets_same_day_pnl():
    trades = [
        _make_trade(datetime(2024, 1, 2, 10, 0), 50.0),
        _make_trade(datetime(2024, 1, 2, 14, 0), 75.0),
        _make_trade(datetime(2024, 1, 3, 10, 0), -25.0),
    ]
    returns = trades_to_returns(trades, starting_equity=100_000.0)
    assert returns.iloc[0] == pytest.approx(125.0 / 100_000.0)
    assert returns.iloc[1] == pytest.approx(-25.0 / 100_000.0)


def test_returns_reindexes_business_days():
    """Days with no trades within the bdate_range get 0.0, not NaN."""
    trades = [
        _make_trade(datetime(2024, 1, 2, 11, 0), 100.0),
        _make_trade(datetime(2024, 1, 5, 11, 0), 200.0),
    ]
    returns = trades_to_returns(trades, starting_equity=100_000.0)
    # bdate_range from 2024-01-02 to 2024-01-05 = Tue/Wed/Thu/Fri = 4 days
    assert len(returns) == 4
    assert returns.iloc[1] == 0.0  # 2024-01-03 (Wed) — no trades
    assert returns.iloc[2] == 0.0  # 2024-01-04 (Thu) — no trades
    assert not returns.isna().any()


def test_empty_trades_raises():
    with pytest.raises(ValueError, match="No trades"):
        trades_to_returns([], starting_equity=100_000.0)


def test_html_generation_smoke(tmp_path):
    """End-to-end: real quantstats invocation produces a non-empty HTML file."""
    trades = [
        _make_trade(datetime(2024, 1, 2 + i % 27, 11, 0), 100.0 if i % 3 else -50.0)
        for i in range(60)
    ]
    out = tmp_path / "tearsheet.html"
    result = from_trades(trades, starting_equity=100_000.0, out_path=out,
                        title="Test Tearsheet")
    assert result == out
    assert out.exists()
    assert out.stat().st_size > 1000  # non-trivial HTML
    content = out.read_text(encoding="utf-8", errors="ignore")
    assert "Test Tearsheet" in content
