"""TV vs MT5 USDJPY P&L reconciliation — canonical USD conversion.

Anchor: TradingView <30-day JPY P&L inflation (~153×) from omitting JPY→USD
conversion on short holds (Q-MT5-TV). At ~150 USDJPY, reporting raw JPY P&L
as USD inflates by roughly the quote rate.

Reference formula (independent of TV display hooks):
    pnl_usd = (exit - entry) * direction * lot_size * contract_size / exit_price

contract_size = 100_000 base units per standard lot (DXTrade / MT5 USDJPY).
"""

from __future__ import annotations

from datetime import datetime
from typing import Union

import pandas as pd

USDJPY_CONTRACT_SIZE = 100_000
# TV short-horizon JPY hook applies to holds strictly under 30 calendar days.
TV_SHORT_HORIZON_MAX_DAYS = 30


def _normalize_direction(direction: Union[float, int, str]) -> float:
    if isinstance(direction, str):
        key = direction.strip().lower()
        if key in ("long", "buy", "1"):
            return 1.0
        if key in ("short", "sell", "-1"):
            return -1.0
        raise ValueError(f"unknown direction label: {direction!r}")
    sign = float(direction)
    if sign not in (1.0, -1.0):
        raise ValueError(f"direction must be +1 or -1, got {direction!r}")
    return sign


def holding_days(
    entry_time: Union[str, datetime, pd.Timestamp],
    exit_time: Union[str, datetime, pd.Timestamp],
) -> int:
    """Calendar days between entry and exit (exit date minus entry date)."""
    entry = pd.Timestamp(entry_time).normalize()
    exit_ = pd.Timestamp(exit_time).normalize()
    return int((exit_ - entry).days)


def is_tv_short_horizon(hold_days: int) -> bool:
    """True when TV's <30-day JPY conversion path would apply (strictly below 30)."""
    return hold_days < TV_SHORT_HORIZON_MAX_DAYS


def compute_pnl(
    entry_price: float,
    exit_price: float,
    lot_size: float,
    direction: Union[float, int, str],
    *,
    entry_time: Union[str, datetime, pd.Timestamp, None] = None,
    exit_time: Union[str, datetime, pd.Timestamp, None] = None,
) -> float:
    """USD P&L for a closed USDJPY position (MT5/DXTrade standard lot).

    Times are optional; when provided they support short-horizon window checks
    but do not change the canonical conversion (always JPY→USD via exit_price).
    """
    if exit_price <= 0:
        raise ValueError(f"exit_price must be positive, got {exit_price}")
    dir_mult = _normalize_direction(direction)
    price_delta = float(exit_price) - float(entry_price)
    pnl_jpy = price_delta * dir_mult * float(lot_size) * USDJPY_CONTRACT_SIZE
    return pnl_jpy / float(exit_price)


def compute_pnl_tv_buggy(
    entry_price: float,
    exit_price: float,
    lot_size: float,
    direction: Union[float, int, str],
    *,
    entry_time: Union[str, datetime, pd.Timestamp],
    exit_time: Union[str, datetime, pd.Timestamp],
) -> float:
    """Deliberate regression: omit JPY→USD divide on <30-day holds (~153× at 150 JPY)."""
    correct = compute_pnl(entry_price, exit_price, lot_size, direction)
    if is_tv_short_horizon(holding_days(entry_time, exit_time)):
        return correct * exit_price
    return correct
