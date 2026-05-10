# fxify_rule_validator — design

**Status:** approved (brainstorming phase, 2026-05-10) · ready for writing-plans handoff
**Author:** Claude (CC) with Joshua review
**Code path:** `fxify_rule_validator.py` (single file, repo root)
**Test path:** `tests/test_fxify_rule_validator.py`
**Source-of-truth:** FXIFY 3-Phase Challenge FAQ pages (URLs cited inline + below)

---

## §1 — Purpose

A pure-function validator package that encodes the FXIFY 3-Phase $200K Challenge rules so any caller (the existing `cli.py`, future automation, or ad-hoc scripts) can ask "is this account state in good standing?" without re-deriving the math.

Five validators, all returning `tuple[bool, Literal["limit", "completion"], str]` — `(passed, kind, reason)`.

The validator answers:
- **Limit checks** — has a hard-breach threshold been crossed? (daily-loss, max static DD, inactivity)
- **Completion checks** — has a phase-pass requirement been met yet? (profit target, min trading days)

The validator does NOT answer pre-trade sizing questions (min/max lot, leverage cap — broker-enforced) or market-condition gating (news blackout — FXIFY 3-Phase has no such rule per the rulebook). Those are deliberately out of scope; if a future firm imposes them, they go in a separate module.

---

## §2 — Scope reconciliation (why these five, not the originally-named five)

The original task brief named five rules: daily-loss, max-drawdown, min-lot-size, max-lot-size, news-blackout. After re-fetching the FXIFY rulebook (Rule-0 discipline, "do not infer rules from memory"), three of those five are not in the FXIFY 3-Phase rulebook:

| Originally requested | Rulebook reality | Resolution |
|---|---|---|
| daily-loss limit | ✅ "Daily drawdown – 5% (Based on previous day balance)" | encode |
| max-drawdown limit | ✅ "Max total Drawdown – 5% Static (Based on initial balance)" | encode |
| min-lot-size | ❌ Not in rulebook | drop |
| max-lot-size | ❌ Not in rulebook (only leverage caps, broker-enforced) | drop |
| news-blackout window | ❌ Inverted: "we do not restrict news trading" on 1/2/3-Phase | drop |

Three rules from the rulebook were not in the original brief but are encoded here because they are part of the same "is the account in good standing / has the phase been passed?" question:

| Rulebook rule | Encoded as |
|---|---|
| "Phase 1 – 5%, Phase 2 – 5%, Phase 3 – 5%" profit target | `validate_profit_target` |
| "Min Trading Days – 5 days (For each phase)" | `validate_min_trading_days` |
| "Must place a trade once in 60 days to avoid inactivity. If not, this would be considered a hard breach." | `validate_inactivity` |

Joshua confirmed this scope reconciliation on 2026-05-09 ("Strict: only encode rules that exist in the rulebook").

---

## §3 — Module surface

### File location

`fxify_rule_validator.py` at repo root, alongside `accounts.py`, `dd_protection.py`, `firm_rules.py`. Single file, ~150 lines. Add `"fxify_rule_validator"` to `[tool.setuptools] py-modules` in `pyproject.toml`.

### Module docstring (top-of-file)

```python
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
```

### Public API

```python
from datetime import datetime
from typing import Literal

from firm_rules import FIRM_RULES

_FXIFY = FIRM_RULES["FXIFY"]

RuleKind = Literal["limit", "completion"]
RuleResult = tuple[bool, RuleKind, str]  # (passed, kind, reason)

def validate_daily_loss(
    current_equity: float,
    prior_day_eod_balance: float,
    daily_loss_pct: float = _FXIFY["daily_loss_pct"],
) -> RuleResult: ...

def validate_max_drawdown(
    current_equity: float,
    initial_balance: float,
    max_dd_pct: float = _FXIFY["max_dd_pct"],
) -> RuleResult: ...

def validate_profit_target(
    current_equity: float,
    initial_balance: float,
    profit_target_pct: float = _FXIFY["profit_target_pct"],
) -> RuleResult: ...

def validate_min_trading_days(
    trading_days_completed: int,
    min_trading_days: int = _FXIFY["min_trading_days"],
) -> RuleResult: ...

def validate_inactivity(
    last_trade_at: datetime,
    now: datetime,
    max_idle_days: int = _FXIFY["inactivity_max_idle_days"],
) -> RuleResult: ...
```

### Constants source

`firm_rules.FIRM_RULES["FXIFY"]` is the single source of truth for the four numeric defaults. **One-line extension to `firm_rules.py` lands as part of this PR**: add `"inactivity_max_idle_days": 60` to the FXIFY dict.

```python
# in fxify_rule_validator.py
from firm_rules import FIRM_RULES

_FXIFY = FIRM_RULES["FXIFY"]
# Defaults (overridable per-call):
#   _FXIFY["daily_loss_pct"]              -> 5.0
#   _FXIFY["max_dd_pct"]                  -> 5.0
#   _FXIFY["profit_target_pct"]           -> 5.0
#   _FXIFY["min_trading_days"]            -> 5
#   _FXIFY["inactivity_max_idle_days"]    -> 60  (added in this PR)
```

---

## §4 — Return-value semantics

### Shape

`tuple[bool, Literal["limit", "completion"], str]` — `(passed, kind, reason)`.

### Per-validator mapping

| Validator | kind | passed=True meaning | passed=False meaning |
|---|---|---|---|
| `validate_daily_loss` | `"limit"` | equity above prior-day floor | floor reached or breached |
| `validate_max_drawdown` | `"limit"` | equity above static initial-balance floor | floor reached or breached |
| `validate_inactivity` | `"limit"` | last trade within max_idle_days | last trade ≥ max_idle_days ago |
| `validate_profit_target` | `"completion"` | target equity reached | target equity not yet reached |
| `validate_min_trading_days` | `"completion"` | days_completed ≥ min | days_completed < min |

### Caller filter idiom (in module docstring)

```python
breached = [r for r in results if r[1] == "limit" and not r[0]]
unmet = [r for r in results if r[1] == "completion" and not r[0]]
in_good_standing = not breached            # account survival
phase_passed = not breached and not unmet  # phase advancement
```

### Reason-string content contract

`reason` is populated **on both branches** (passed=True and passed=False) so callers can log it unconditionally. For money validators, dollar values are formatted `${x:,.2f}` and the percentage rule is named explicitly. For day validators, the integer day count is named.

---

## §5 — Threshold semantics (the subtle resolutions)

### 5a. Inclusive vs exclusive at the boundary

**Decision: `equity <= floor → breach` (inclusive) for daily-loss and max-DD.**

The two FAQ pages disagree:
- Daily-loss page: "should your equity ... fall to $95,000" → reaching $95,000 IS the breach (inclusive).
- Static-DD page (2-Phase example): "Lowest the balance or equity can go before the breach is 900 USD" → 900 is the *last safe* value (exclusive).

Resolution rationale:
1. The daily-loss page wording is unambiguous and explicit; the static-DD page wording requires interpretation.
2. The conservative-of-trader reading (assume FXIFY rules in their favor at the borderline) treats the floor as the breach.
3. Applying both rules consistently matters more than matching either page's narrow phrasing exactly.

**Asymmetry of error costs** (load-bearing reasoning, not just preference): if FXIFY's actual operator is `<` and we use `<=`, the worst case is a fractional-cent-early breach flag — lost trading opportunity, recoverable. If FXIFY uses `<=` and we use `<`, the worst case is the validator says "ok" while the broker fails the account — unrecoverable. Asymmetric error costs justify `<=` uniformly even setting the daily-loss page wording aside.

Both FAQ quotes will be pinned in test docstrings so the choice is auditable.

### 5b. Floating-point money math

**Decision: `round(x, 2)` before compare for all money math.**

Justification:
- `200_000 - (200_000 * 5 / 100) = 189999.99999999997` and `200_000 * (1 - 0.05) = 190000.00000000003` — both real outcomes in IEEE 754, depending on operation order. Without rounding, `equity == 190000.00 <= 189999.99999999997` evaluates `False` and a real breach goes undetected.
- Existing `accounts.py` (lines 17-49) and `dd_protection.py` (line 87) both use raw `float` for money/equity fields. Forcing `Decimal` in the validator would create a type-impedance boundary at every call site against this convention. Cent-precision rounding matches the broker reporting precision and suffices.

Pattern:
```python
floor = round(initial_balance * (1 - max_dd_pct / 100), 2)
equity = round(current_equity, 2)
if equity <= floor: ...  # breach
```

Test pins the exact case (see §7).

**Audit finding (separately flagged, NOT addressed in this PR):** the existing money-using modules in this repo do not apply round-before-compare guards. Specifically:
- `accounts.py:30-32` — `dd_remaining_pct` uses raw float subtraction/division then rounds at the end for display; the `flags()` comparison `dd_remaining_pct <= 0` operates on the rounded value so is internally consistent.
- `dd_protection.py:89-90` — `dd_from_peak = (peak - equity) / peak; dd_triggered = dd_from_peak >= DD_TRIGGER` is a raw-float compare. At the exact 1.5% trigger boundary, ULP error can cause the trigger to mis-fire by 1 step. The MVD self-check in `_validate_protection_rule()` uses an explicit epsilon (line 131) to avoid exact-boundary testing, which acknowledges but does not fix the production-path issue. This is a **latent defect**: triggers only when equity hits the protection boundary to ULP precision (rare in live use), but the failure mode (protection silently failing to fire) is unrecoverable. Suggested follow-up: apply the same round-before-compare guard to `dd_protection.py:89-90` in a separate PR with its own MC re-validation. **Not in scope for this PR.**

### 5c. Inactivity calendar vs business days

**Decision: calendar days.** FXIFY says "60 days" plain — no mention of business-day calendar. `(now - last_trade_at).days >= 60 → breach`.

### 5d. Type contract

`float` and `int` accepted for numeric inputs; `int` works because `int <= float` is exact in Python and `round(int, 2)` is a no-op. `Decimal` not officially supported and not tested. `datetime` inputs must be naive or both tz-aware (we don't mix).

---

## §6 — Input validation (programmer-error contract)

Bad inputs raise `ValueError`, not `passed=False`. Reason: `passed=False` is overloaded with "rule breached"; that's a meaningfully different state from "you passed garbage". A negative balance isn't a breach — it's a programmer error. Forcing `ValueError` makes callers fix the bug at the call site.

| Input condition | Behavior |
|---|---|
| `current_equity < 0` | raise `ValueError("current_equity must be ≥ 0")` |
| `initial_balance <= 0` | raise `ValueError("initial_balance must be > 0")` |
| `prior_day_eod_balance <= 0` | raise `ValueError("prior_day_eod_balance must be > 0")` |
| `trading_days_completed < 0` | raise `ValueError("trading_days_completed must be ≥ 0")` |
| `last_trade_at > now + 5 min` | raise `ValueError("last_trade_at is more than 5 minutes in the future (clock skew tolerance exceeded)")` — see §6a for sub-5-min behavior |
| any `*_pct < 0` | raise `ValueError("*_pct must be ≥ 0")` |

### 6a. Clock-skew tolerance for `validate_inactivity`

**Decision: tolerate up to 5 minutes of future-stamped `last_trade_at` silently; raise beyond.**

DXTrade fill timestamps and local `now()` will routinely differ by sub-second to seconds — even minutes if the local clock or broker server clock has drift. Raising `ValueError` on microsecond-level skew would be a constant false positive at every call site, forcing callers to either disable validation or to round timestamps themselves before passing — both bad outcomes.

Implementation:
```python
_CLOCK_SKEW_TOLERANCE_SECONDS = 300  # 5 min — covers typical broker/local drift

if last_trade_at > now:
    skew_seconds = (last_trade_at - now).total_seconds()
    if skew_seconds > _CLOCK_SKEW_TOLERANCE_SECONDS:
        raise ValueError(
            "last_trade_at is more than 5 minutes in the future "
            "(clock skew tolerance exceeded)"
        )
    # Within tolerance: silently clamp to now → idle_days = 0, passes as fresh.
    last_trade_at = now
```

Inclusive at the 5-minute boundary (5 min 0 sec → tolerated; 5 min 1 sec → raise). The `_CLOCK_SKEW_TOLERANCE_SECONDS` constant is module-private — not in `firm_rules` (it's an implementation tolerance, not a firm rule).

Each validator has at least one `pytest.raises(ValueError)` test pinning the contract above. `validate_inactivity` has three tests pinning the skew boundary (within tolerance / at boundary / beyond tolerance).

---

## §7 — Test plan

Test file: `tests/test_fxify_rule_validator.py`. One test class per validator. TDD red-green per validator, in this order (simplest first):

1. `validate_max_drawdown` — two-arg, single threshold
2. `validate_daily_loss` — same shape, different basis
3. `validate_profit_target` — same shape, opposite direction (≥ vs ≤)
4. `validate_min_trading_days` — int comparison, no money math
5. `validate_inactivity` — only one with `datetime` math

### Test categories per validator

For each validator:

**(a) Boundary tests** — exactly at threshold, just above (one cent / one day), just below.

**(b) Reason-string content tests** — assert key dollar/day values appear verbatim in `reason`. Catches "always returns False with empty reason" regressions.

**(c) Negative/zero input tests** — `pytest.raises(ValueError)` for each invalid input from §6.

**(d) Type contract tests** — one alt-type test per validator (e.g., all-int inputs to `validate_max_drawdown`) locks `int` acceptance.

**(e) Kind-field tests** — assert `result[1] == "limit"` or `"completion"` matches §4 mapping.

### Money-validator-specific tests

**(f) FP boundary test (money validators only — daily-loss, max-DD, profit-target)** — exact-floor case where naive float math would miss the breach:

```python
def test_max_drawdown_at_exact_floor_breaches_despite_float_imprecision():
    # 200_000 * (1 - 0.05) == 189999.99999999997 in float;
    # without round(2), an equity of exactly 190000.00 would NOT detect the breach.
    passed, kind, reason = validate_max_drawdown(
        current_equity=190_000.00,
        initial_balance=200_000.00,
        max_dd_pct=5.0,
    )
    assert passed is False
    assert kind == "limit"
    assert "190,000.00" in reason
```

### Rulebook-anchored worked-example tests (provenance-audited)

After auditing what FXIFY actually shows as worked examples in their FAQ:

**(g) `test_daily_loss_fxify_3phase_faq_example_100k_to_95k`** — pins:
> "On a Three phase account, if your prior day's end of day balance was $100,000 you would breach the Daily Loss Limit of 5% should your equity the next day fall to $95,000."
>
> *Source: https://fxify.com/faqs/all-faqs/how-do-you-calculate-the-daily-loss-limit/*

```python
def test_daily_loss_fxify_3phase_faq_example_100k_to_95k():
    # Verbatim FXIFY 3-Phase FAQ example. Source URL in module docstring.
    passed, kind, reason = validate_daily_loss(
        current_equity=95_000.00,
        prior_day_eod_balance=100_000.00,
        daily_loss_pct=5.0,
    )
    assert passed is False
    assert kind == "limit"
```

**(h) `test_max_drawdown_2phase_faq_example_inclusive_interpretation`** — pins our chosen inclusive interpretation against the only FXIFY-provided static-DD worked example (2-Phase, 10% static). The FAQ wording is borderline-exclusive ("lowest before breach is 900"); per §5a we apply `<=` (inclusive), so `equity=900.00` returns `passed=False`. Renamed deliberately: this test pins our **interpretation**, not the FAQ value as-is — `_inclusive_interpretation` is the load-bearing word, not `_faq_example`.

> *FAQ verbatim, for audit*: "Example: 1000 balance. 10% of 1000 is 100. Lowest the balance or equity can go before the breach is 900 USD (1000 – 100 = 900)."
>
> *Source: https://fxify.com/faqs/all-faqs/what-is-static-drawdown/*

No invented worked examples for `validate_profit_target`, `validate_min_trading_days`, `validate_inactivity` — those use plain unit-test values without claiming FXIFY provenance.

### Test count estimate

Per validator: ~6 boundary + 1 reason-content + 3-5 ValueError + 1 alt-type + 1 kind = ~12 tests. Money validators add 1 FP-boundary test. Two also have a rulebook-anchored test.

Total: ~60-65 test functions across 5 validators. Run via `pytest tests/test_fxify_rule_validator.py -v`.

---

## §8 — Out of scope (explicit, won't drift)

| Excluded | Why | Where it would go if needed |
|---|---|---|
| min-lot-size, max-lot-size | Not in FXIFY 3-Phase rulebook | not applicable for FXIFY |
| news-blackout window | Not in FXIFY 3-Phase rulebook (allowed) | separate `*_market_gate.py` module if a future firm restricts |
| Leverage cap enforcement | Broker-enforced, not trader-side | broker integration, not validator |
| Weekend-hold rule | FXIFY allows; `firm_rules` `weekend_holds=True` | separate module if a future firm restricts |
| CLI integration | Not requested in this PR | follow-up: `cli.py validate <account>` subcommand |
| Coupling to `accounts.Account` | Validator should be reusable across firms | callers compose snapshot from `Account` themselves |
| Multi-firm dispatch | Only FXIFY onboarded | future firms get their own `*_rule_validator.py` modules |

---

## §9 — Files touched

| File | Change |
|---|---|
| `fxify_rule_validator.py` | NEW — single file, ~150 lines |
| `tests/test_fxify_rule_validator.py` | NEW — ~60-65 tests |
| `firm_rules.py` | EDIT — add one line: `"inactivity_max_idle_days": 60` to `FIRM_RULES["FXIFY"]` |
| `pyproject.toml` | EDIT — add `"fxify_rule_validator"` to `[tool.setuptools] py-modules` |

No edits to `accounts.py`, `dd_protection.py`, `cli.py`, `portfolio_mc.py`, or any test other than the new one.

---

## §10 — Verbatim FXIFY rulebook quotes (audit anchor)

Re-fetched 2026-05-09 with strict verbatim-extraction prompt. Pinned here so future readers can compare against then-current FAQ content without re-fetching.

### Daily loss
> *Source: https://fxify.com/faqs/all-faqs/how-do-you-calculate-the-daily-loss-limit/*
>
> "Daily Loss Limit is calculated based on the balance at the end of the previous day, the balance recorded at 5PM EST time."
>
> "On a Three phase account, if your prior day's end of day balance was $100,000 you would breach the Daily Loss Limit of 5% should your equity the next day fall to $95,000."

### Static drawdown (3-Phase)
> *Source: https://fxify.com/faqs/all-faqs/what-is-static-drawdown/*
>
> "Maximum drawdown is the maximum your account can drawdown before you would hard breach your account. When you open the account, your max drawdown is set at 5% max drawdown on the 3 phase. This will be static for the life of the account."

### Static drawdown (2-Phase worked example, used in test (h))
> *Source: https://fxify.com/faqs/all-faqs/what-is-static-drawdown/*
>
> "Example: 1000 balance. 10% of 1000 is 100. Lowest the balance or equity can go before the breach is 900 USD (1000 – 100 = 900). 900 USD will always be the lowest right before equity breaches the account, this is what Static drawdown means."

### 3-Phase assessment rules
> *Source: https://fxify.com/faqs/all-faqs/what-are-the-rules-for-the-assessment-account/*
>
> Profit Targets: "Phase 1 – 5%, Phase 2 – 5%, Phase 3 – 5%"
> Drawdown: "Daily drawdown – 5% (Based on previous day balance)" / "Max total Drawdown – 5% Static (Based on initial balance)"
> Trading Days: "Min Trading Days – 5 days (For each phase)" / "Max Trading Days – Phase 1 (Unlimited Days), Phase 2 (Unlimited Days), Phase 3 (Unlimited Days)"
> Inactivity (all accounts): "Must place a trade once in 60 days to avoid inactivity. If not, this would be considered a hard breach."

### News (no rule, justifies omission)
> *Source: https://fxify.com/faqs/all-faqs/can-i-trade-the-news/*
>
> "Yes, you are able to trade new events on 1, 2 and 3-Phase accounts."
> "Although we do not restrict news trading, traders should be aware that trades might not get filled at desirable prices due to higher volatility and lower liquidity during these times."

---

## §11 — Open follow-ups (NOT in this PR)

- **Rulebook drift detection.** This validator pins constants and verbatim quotes as of 2026-05-09 fetch. FXIFY material rule changes typically arrive via direct communication (email / Discord / dashboard banner), not silent FAQ edits — but silent FAQ edits do happen (clarifications, footnote additions, "for accounts opened after [date]" carve-outs). The validator gives the operator no signal when this happens. Mitigation: **re-fetch the four cited FAQ URLs verbatim annually as part of CTA-prep / institutional-readiness review**, diff against the audit anchor in §10, and update both spec and constants if the rulebook moves. Add to Operational Risk Register. Suggested next re-fetch: 2027-05-09.
- **Apply round-before-compare guard to `dd_protection.py:89-90`** — separately-flagged audit finding from §5b. Latent ULP-precision defect at the exact 1.5% trigger boundary. Fix is a one-line change wrapped in its own MC re-validation per the 2026-04-24 ADR rule.
- **`cli.py validate <account>` subcommand** — would assemble a snapshot from `Account` + recent trade history and run all 5 validators, printing the report.
- **Snapshot-builder helper** — if a second caller wants to run all 5 validators, factor a `build_snapshot(account, trade_history)` helper. Premature now (zero callers).
- **Multi-firm dispatch** — `validate_account(firm, snapshot)` that routes to the right per-firm validator module. Premature; only FXIFY onboarded.

These are noted so future readers know they were considered and deliberately deferred (visible-restraint discipline).
