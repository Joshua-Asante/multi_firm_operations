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

Asymmetric error costs (inclusive-at-boundary reading):

  All validators apply inclusive comparisons at boundary values:
    * limit rules (daily-loss, max-DD, inactivity):
        breach inclusive  -> equity <= floor / idle_days >= max
    * completion rules (profit-target, min-trading-days):
        met inclusive     -> equity >= target / days >= min

  Inclusive readings are chosen on asymmetric-error-costs grounds, not
  on FAQ wording (some FAQ examples are borderline-exclusive — see
  test_2phase_faq_example_inclusive_interpretation).

  For limit rules: false-pass at exact boundary masks an account-loss-
  class breach; false-breach at exact boundary costs at most one trading
  cycle. Account loss is unrecoverable; missed cycle is recoverable.

  For completion rules: false-met at exact target lets the trader
  advance one cent early (negligible); false-unmet at exact target
  blocks advancement when the trader did the work (operational cost).

  Conservative-of-trader picks the inclusive direction in both cases.
  Same reasoning applies one layer earlier on the precision dimension —
  see docs/adr/2026-05-10-dd-protection-ulp-rounding.md for the
  asymmetric-error-cost framing applied to FP precision at threshold
  comparisons.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from firm_rules import FIRM_RULES

_FXIFY = FIRM_RULES["FXIFY"]

RuleKind = Literal["limit", "completion"]
RuleResult = tuple[bool, RuleKind, str]

# Clock-skew tolerance for validate_inactivity. DXTrade fill timestamps
# vs local now() routinely differ by sub-second to seconds; raising on
# microsecond skew would be a constant false positive. Sub-5-min future
# stamps are silently clamped to "fresh"; beyond 5 min raises. Spec §6a.
_CLOCK_SKEW_TOLERANCE_SECONDS = 300


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


def validate_inactivity(
    last_trade_at: datetime,
    now: datetime,
    max_idle_days: int = _FXIFY["inactivity_max_idle_days"],
) -> RuleResult:
    """Inactivity hard-breach check.

    FXIFY all-accounts: "Must place a trade once in 60 days to avoid
    inactivity. If not, this would be considered a hard breach."
    Calendar days; breach inclusive at day boundary
    ((now - last_trade_at).days >= max_idle_days).

    Clock-skew tolerance: last_trade_at up to 5 min after now is
    silently clamped to now (treated as fresh). Beyond 5 min raises
    ValueError. See spec §6a.
    """
    if max_idle_days < 0:
        raise ValueError("max_idle_days must be >= 0")

    if last_trade_at > now:
        skew_seconds = (last_trade_at - now).total_seconds()
        if skew_seconds > _CLOCK_SKEW_TOLERANCE_SECONDS:
            raise ValueError(
                "last_trade_at is more than 5 minutes in the future "
                "(clock skew tolerance exceeded)"
            )
        # Within tolerance: clamp to now -> idle_days = 0.
        last_trade_at = now

    idle_days = (now - last_trade_at).days

    if idle_days >= max_idle_days:
        return (
            False,
            "limit",
            f"Inactivity hard breach: {idle_days} days since last trade "
            f"(max {max_idle_days})",
        )
    return (
        True,
        "limit",
        f"Inactivity ok: {idle_days} days since last trade "
        f"(max {max_idle_days})",
    )
