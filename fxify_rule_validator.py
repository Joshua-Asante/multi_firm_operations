"""FXIFY 3-Phase Challenge rule validators.

Covers post-trade account-state rules — does the current account state
breach a hard-breach limit, or has it satisfied a phase-completion
requirement?

  * Limit checks (kind='limit'):       daily-loss, max-static-DD, inactivity
  * Completion checks (kind='completion'): profit-target, min-trading-days

Does NOT cover:
  * Pre-trade sizing rules (min/max lot, leverage cap)        — broker enforces
  * Market-condition gating rules (news blackout, weekend hold) — FXIFY 3-Phase
       does not impose these (https://fxify.com/faqs/all-faqs/can-i-trade-the-news/);
       if a future firm does, it goes in a separate module, NOT this one.

Source of truth (re-fetched and verbatim-quoted 2026-05-09):
  * Daily loss:        https://fxify.com/faqs/all-faqs/how-do-you-calculate-the-daily-loss-limit/
  * Static drawdown:   https://fxify.com/faqs/all-faqs/what-is-static-drawdown/
  * Phase rules:       https://fxify.com/faqs/all-faqs/what-are-the-rules-for-the-assessment-account/
  * News (no rule):    https://fxify.com/faqs/all-faqs/can-i-trade-the-news/

Constants live in `firm_rules.FIRM_RULES["FXIFY"]`. Validators import defaults
from there; per-call overrides accepted for testing/edge cases.

Caller-side filter idiom for combining validator results:

    results = [
        validate_daily_loss(eq, prior_eod),
        validate_max_drawdown(eq, init),
        validate_inactivity(last_t, now),
        validate_profit_target(eq, init),
        validate_min_trading_days(days),
    ]
    breached = [r for r in results if r[1] == "limit" and not r[0]]
    unmet = [r for r in results if r[1] == "completion" and not r[0]]
    in_good_standing = not breached            # account survival
    phase_passed = not breached and not unmet  # phase advancement
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from firm_rules import FIRM_RULES

_FXIFY = FIRM_RULES["FXIFY"]

RuleKind = Literal["limit", "completion"]
RuleResult = tuple[bool, RuleKind, str]


def validate_max_drawdown(
    current_equity: float,
    initial_balance: float,
    max_dd_pct: float = _FXIFY["max_dd_pct"],
) -> RuleResult:
    """Static max-drawdown limit.

    FXIFY 3-Phase: "Max total Drawdown - 5% Static (Based on initial balance)".
    Breach inclusive at floor (equity <= floor).
    """
    if current_equity < 0:
        raise ValueError("current_equity must be >= 0")
    if initial_balance <= 0:
        raise ValueError("initial_balance must be > 0")
    if max_dd_pct < 0:
        raise ValueError("max_dd_pct must be >= 0")

    floor = round(initial_balance * (1 - max_dd_pct / 100), 2)
    equity = round(current_equity, 2)
    initial = round(initial_balance, 2)

    if equity <= floor:
        return (
            False,
            "limit",
            f"Max DD breached: equity ${equity:,.2f} <= floor ${floor:,.2f} "
            f"(rule: {max_dd_pct}% of initial ${initial:,.2f})",
        )
    return (
        True,
        "limit",
        f"Max DD ok: equity ${equity:,.2f} > floor ${floor:,.2f}",
    )


def validate_daily_loss(
    current_equity: float,
    prior_day_eod_balance: float,
    daily_loss_pct: float = _FXIFY["daily_loss_pct"],
) -> RuleResult:
    """Daily-loss limit, basis = prior-day balance recorded at 5pm EST.

    FXIFY 3-Phase: "Daily drawdown - 5% (Based on previous day balance)".
    Breach inclusive at floor (equity <= floor).
    """
    if current_equity < 0:
        raise ValueError("current_equity must be >= 0")
    if prior_day_eod_balance <= 0:
        raise ValueError("prior_day_eod_balance must be > 0")
    if daily_loss_pct < 0:
        raise ValueError("daily_loss_pct must be >= 0")

    floor = round(prior_day_eod_balance * (1 - daily_loss_pct / 100), 2)
    equity = round(current_equity, 2)
    prior = round(prior_day_eod_balance, 2)

    if equity <= floor:
        return (
            False,
            "limit",
            f"Daily loss breached: equity ${equity:,.2f} <= floor ${floor:,.2f} "
            f"(rule: {daily_loss_pct}% of prior-day EOD ${prior:,.2f})",
        )
    return (
        True,
        "limit",
        f"Daily loss ok: equity ${equity:,.2f} > floor ${floor:,.2f}",
    )


def validate_profit_target(
    current_equity: float,
    initial_balance: float,
    profit_target_pct: float = _FXIFY["profit_target_pct"],
) -> RuleResult:
    """Profit-target completion check.

    FXIFY 3-Phase: "Profit Targets: Phase 1 - 5%, Phase 2 - 5%, Phase 3 - 5%".
    Met inclusive at target (equity >= target).
    """
    if current_equity < 0:
        raise ValueError("current_equity must be >= 0")
    if initial_balance <= 0:
        raise ValueError("initial_balance must be > 0")
    if profit_target_pct < 0:
        raise ValueError("profit_target_pct must be >= 0")

    target = round(initial_balance * (1 + profit_target_pct / 100), 2)
    equity = round(current_equity, 2)
    initial = round(initial_balance, 2)

    if equity >= target:
        return (
            True,
            "completion",
            f"Profit target met: equity ${equity:,.2f} >= target ${target:,.2f} "
            f"(rule: {profit_target_pct}% of initial ${initial:,.2f})",
        )
    return (
        False,
        "completion",
        f"Profit target not met: equity ${equity:,.2f} < target ${target:,.2f}",
    )


def validate_min_trading_days(
    trading_days_completed: int,
    min_trading_days: int = _FXIFY["min_trading_days"],
) -> RuleResult:
    """Min-trading-days completion check.

    FXIFY 3-Phase: "Min Trading Days - 5 days (For each phase)".
    Met inclusive (days_completed >= min).
    """
    if trading_days_completed < 0:
        raise ValueError("trading_days_completed must be >= 0")
    if min_trading_days < 0:
        raise ValueError("min_trading_days must be >= 0")

    if trading_days_completed >= min_trading_days:
        return (
            True,
            "completion",
            f"Min trading days met: {trading_days_completed} of {min_trading_days} required",
        )
    return (
        False,
        "completion",
        f"Min trading days not met: {trading_days_completed} of {min_trading_days} required",
    )
