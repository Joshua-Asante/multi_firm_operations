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
