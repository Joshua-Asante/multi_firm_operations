# fxify_rule_validator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-file pure-function validator (`fxify_rule_validator.py`) encoding the FXIFY 3-Phase $200K Challenge rules: daily-loss, max static drawdown, profit-target, min-trading-days, and inactivity. Each function returns `(passed: bool, kind: Literal["limit", "completion"], reason: str)`.

**Architecture:** Five pure functions at repo root. No I/O, no `datetime.now()`, no broker calls — caller assembles inputs as primitives. Constants live in `firm_rules.FIRM_RULES["FXIFY"]` (one-line extension to add `inactivity_max_idle_days: 60`); validator imports defaults from there. Money math uses `round(x, 2)` before compare. Money inclusivity is `equity <= floor` (breach inclusive). Bad inputs raise `ValueError`.

**Tech Stack:** Python 3.11+, pytest, stdlib only (`datetime`, `typing`). No new deps. Pinned by `pyproject.toml` `py-modules` entry.

**Spec:** `docs/superpowers/specs/2026-05-10-fxify-rule-validator-design.md`

---

## File structure

| File | Action | Responsibility |
|---|---|---|
| `firm_rules.py` | edit (1 line) | Add `"inactivity_max_idle_days": 60` to `FIRM_RULES["FXIFY"]` |
| `pyproject.toml` | edit (1 line) | Add `"fxify_rule_validator"` to `[tool.setuptools] py-modules` |
| `fxify_rule_validator.py` | create | 5 validators + types + constants from `firm_rules` |
| `tests/test_fxify_rule_validator.py` | create | One test class per validator, ~60 tests total |

No edits to `accounts.py`, `dd_protection.py`, `cli.py`, `portfolio_mc.py`, or any test other than the new file.

---

## Task 1: Extend firm_rules and pyproject

**Files:**
- Modify: `firm_rules.py` (FXIFY dict)
- Modify: `pyproject.toml` (`py-modules`)

- [ ] **Step 1: Add `inactivity_max_idle_days` to firm_rules**

Edit `firm_rules.py`. The current FXIFY dict ends with `"weekend_holds": True,`. Add the inactivity key as the last entry (before the closing brace).

```python
FIRM_RULES = {
    "FXIFY": {
        "dd_type": "static",
        "max_dd_pct": 5.0,
        "daily_loss_pct": 5.0,
        "profit_target_pct": 5.0,
        "min_trading_days": 5,
        "news_trading": True,
        "weekend_holds": True,
        "inactivity_max_idle_days": 60,  # https://fxify.com/faqs/all-faqs/what-are-the-rules-for-the-assessment-account/
    },
    # ... rest unchanged
}
```

- [ ] **Step 2: Verify firm_rules still imports cleanly**

Run: `python -c "from firm_rules import FIRM_RULES; print(FIRM_RULES['FXIFY']['inactivity_max_idle_days'])"`
Expected output: `60`

- [ ] **Step 3: Add fxify_rule_validator to pyproject py-modules**

Edit `pyproject.toml`. The current `py-modules` line is:
```toml
py-modules = ["accounts", "cli", "csv_parser", "dd_protection", "firm_rules", "portfolio_mc"]
```

Replace it with (alphabetical insertion):
```toml
py-modules = ["accounts", "cli", "csv_parser", "dd_protection", "firm_rules", "fxify_rule_validator", "portfolio_mc"]
```

- [ ] **Step 4: Run existing test suite to confirm nothing broke**

Run: `pytest tests/ -x --no-header -q 2>&1 | tail -20`
Expected: all existing tests still pass (no new module exists yet, so no fxify tests are collected).

- [ ] **Step 5: Commit**

```bash
git add firm_rules.py pyproject.toml
git commit -m "$(cat <<'EOF'
prep(fxify_rule_validator): firm_rules + pyproject scaffolding

Add inactivity_max_idle_days=60 to FIRM_RULES["FXIFY"] (FXIFY 3-Phase
rulebook: "Must place a trade once in 60 days to avoid inactivity. If
not, this would be considered a hard breach."). Register
fxify_rule_validator in py-modules ahead of module file landing.
EOF
)"
```

---

## Task 2: Create module skeleton + empty test file

Create the module shell with full docstring, imports, types, and constants — but no validator functions yet. Create the test file with a single import-smoke test. Verify both load cleanly under pytest.

**Files:**
- Create: `fxify_rule_validator.py`
- Create: `tests/test_fxify_rule_validator.py`

- [ ] **Step 1: Create `fxify_rule_validator.py` with skeleton**

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

from __future__ import annotations

from datetime import datetime
from typing import Literal

from firm_rules import FIRM_RULES

_FXIFY = FIRM_RULES["FXIFY"]

RuleKind = Literal["limit", "completion"]
RuleResult = tuple[bool, RuleKind, str]
```

- [ ] **Step 2: Create `tests/test_fxify_rule_validator.py` with import smoke test**

```python
"""Tests for fxify_rule_validator.

Source-of-truth pins (FXIFY rulebook URLs cited inline in each test class):
  * https://fxify.com/faqs/all-faqs/how-do-you-calculate-the-daily-loss-limit/
  * https://fxify.com/faqs/all-faqs/what-is-static-drawdown/
  * https://fxify.com/faqs/all-faqs/what-are-the-rules-for-the-assessment-account/
"""


def test_module_imports_cleanly():
    import fxify_rule_validator  # noqa: F401
```

- [ ] **Step 3: Run smoke test**

Run: `pytest tests/test_fxify_rule_validator.py -v`
Expected: 1 passed (the import smoke test).

- [ ] **Step 4: Commit**

```bash
git add fxify_rule_validator.py tests/test_fxify_rule_validator.py
git commit -m "$(cat <<'EOF'
feat(fxify_rule_validator): module skeleton + import smoke test

Top-of-file docstring states scope (post-trade account-state) and
explicit non-scope (lot-size, news-blackout). Constants imported from
firm_rules.FIRM_RULES["FXIFY"]; types pinned (RuleKind, RuleResult).
No validators yet — TDD cycles per validator follow.
EOF
)"
```

---

## Task 3: validate_max_drawdown (TDD cycle)

Simplest validator — two-arg, single threshold, single comparison direction. Establishes the pattern (round-then-compare, ValueError contract, reason content) for the other money validators.

**Files:**
- Modify: `fxify_rule_validator.py` (add function)
- Modify: `tests/test_fxify_rule_validator.py` (add `TestMaxDrawdown` class)

- [ ] **Step 1: Write failing tests for `validate_max_drawdown`**

Append to `tests/test_fxify_rule_validator.py`:

```python
import pytest


class TestMaxDrawdown:
    """validate_max_drawdown — FXIFY 3-Phase rule:
    "Max total Drawdown – 5% Static (Based on initial balance)"
    https://fxify.com/faqs/all-faqs/what-are-the-rules-for-the-assessment-account/

    "When you open the account, your max drawdown is set at 5% max
    drawdown on the 3 phase. This will be static for the life of the
    account."
    https://fxify.com/faqs/all-faqs/what-is-static-drawdown/
    """

    # --- Happy path: above the floor ---

    def test_equity_above_floor_passes(self):
        from fxify_rule_validator import validate_max_drawdown
        passed, kind, reason = validate_max_drawdown(
            current_equity=195_000.00,
            initial_balance=200_000.00,
            max_dd_pct=5.0,
        )
        assert passed is True
        assert kind == "limit"
        assert "195,000.00" in reason
        assert "190,000.00" in reason

    # --- Boundary: exactly at floor (inclusive breach per spec §5a) ---

    def test_equity_at_exact_floor_breaches(self):
        from fxify_rule_validator import validate_max_drawdown
        passed, kind, reason = validate_max_drawdown(
            current_equity=190_000.00,
            initial_balance=200_000.00,
            max_dd_pct=5.0,
        )
        assert passed is False
        assert kind == "limit"

    def test_equity_one_cent_below_floor_breaches(self):
        from fxify_rule_validator import validate_max_drawdown
        passed, _, _ = validate_max_drawdown(
            current_equity=189_999.99,
            initial_balance=200_000.00,
            max_dd_pct=5.0,
        )
        assert passed is False

    def test_equity_one_cent_above_floor_passes(self):
        from fxify_rule_validator import validate_max_drawdown
        passed, _, _ = validate_max_drawdown(
            current_equity=190_000.01,
            initial_balance=200_000.00,
            max_dd_pct=5.0,
        )
        assert passed is True

    # --- FP-boundary defense (spec §5b) ---

    def test_at_exact_floor_breaches_despite_float_imprecision(self):
        # 200_000 * (1 - 0.05) == 189999.99999999997 in float;
        # without round(2), equity=190000.00 would NOT detect breach.
        from fxify_rule_validator import validate_max_drawdown
        passed, kind, reason = validate_max_drawdown(
            current_equity=190_000.00,
            initial_balance=200_000.00,
            max_dd_pct=5.0,
        )
        assert passed is False
        assert kind == "limit"
        assert "190,000.00" in reason

    # --- Reason-string content (failure branch) ---

    def test_breach_reason_names_floor_equity_and_pct(self):
        from fxify_rule_validator import validate_max_drawdown
        _, _, reason = validate_max_drawdown(
            current_equity=185_000.00,
            initial_balance=200_000.00,
            max_dd_pct=5.0,
        )
        assert "185,000.00" in reason
        assert "190,000.00" in reason
        assert "5" in reason

    # --- Reason-string content (pass branch) ---

    def test_pass_reason_is_populated(self):
        from fxify_rule_validator import validate_max_drawdown
        _, _, reason = validate_max_drawdown(
            current_equity=210_000.00,
            initial_balance=200_000.00,
            max_dd_pct=5.0,
        )
        assert reason  # non-empty
        assert "210,000.00" in reason

    # --- Default override (firm_rules import) ---

    def test_default_pct_comes_from_firm_rules(self):
        # No max_dd_pct kwarg — should use firm_rules.FIRM_RULES["FXIFY"]["max_dd_pct"] (5.0).
        from fxify_rule_validator import validate_max_drawdown
        passed, _, _ = validate_max_drawdown(
            current_equity=190_000.00,
            initial_balance=200_000.00,
        )
        assert passed is False  # exact-5%-floor breach

    # --- ValueError contract (spec §6) ---

    def test_negative_equity_raises(self):
        from fxify_rule_validator import validate_max_drawdown
        with pytest.raises(ValueError, match="current_equity"):
            validate_max_drawdown(
                current_equity=-1.0,
                initial_balance=200_000.00,
            )

    def test_zero_initial_balance_raises(self):
        from fxify_rule_validator import validate_max_drawdown
        with pytest.raises(ValueError, match="initial_balance"):
            validate_max_drawdown(
                current_equity=100.0,
                initial_balance=0.0,
            )

    def test_negative_initial_balance_raises(self):
        from fxify_rule_validator import validate_max_drawdown
        with pytest.raises(ValueError, match="initial_balance"):
            validate_max_drawdown(
                current_equity=100.0,
                initial_balance=-1.0,
            )

    def test_negative_pct_raises(self):
        from fxify_rule_validator import validate_max_drawdown
        with pytest.raises(ValueError, match="max_dd_pct"):
            validate_max_drawdown(
                current_equity=100.0,
                initial_balance=200_000.00,
                max_dd_pct=-1.0,
            )

    # --- Type contract: int accepted (spec §5d) ---

    def test_all_int_inputs_accepted(self):
        from fxify_rule_validator import validate_max_drawdown
        passed, kind, _ = validate_max_drawdown(
            current_equity=190_000,  # int
            initial_balance=200_000,  # int
            max_dd_pct=5,             # int
        )
        assert passed is False
        assert kind == "limit"

    # --- Inclusive-interpretation pin against the only FXIFY worked example
    #     for static DD (spec §7h, 2-Phase) ---

    def test_2phase_faq_example_inclusive_interpretation(self):
        # FXIFY 2-Phase static-DD FAQ verbatim:
        # "Example: 1000 balance. 10% of 1000 is 100. Lowest the balance or
        #  equity can go before the breach is 900 USD (1000 - 100 = 900)."
        # Source: https://fxify.com/faqs/all-faqs/what-is-static-drawdown/
        #
        # The FAQ wording is borderline-exclusive ("lowest before breach is
        # 900"). Per spec §5a we apply <= (inclusive — asymmetric error
        # costs justify the conservative-of-trader reading). This test pins
        # our INTERPRETATION, not the FAQ value as-is.
        from fxify_rule_validator import validate_max_drawdown
        passed, kind, _ = validate_max_drawdown(
            current_equity=900.00,
            initial_balance=1000.00,
            max_dd_pct=10.0,
        )
        assert passed is False  # inclusive interpretation
        assert kind == "limit"
```

- [ ] **Step 2: Run tests — expect all to fail with ImportError on `validate_max_drawdown`**

Run: `pytest tests/test_fxify_rule_validator.py::TestMaxDrawdown -v`
Expected: 14 errors/fails — `cannot import name 'validate_max_drawdown' from 'fxify_rule_validator'`.

- [ ] **Step 3: Implement `validate_max_drawdown`**

Append to `fxify_rule_validator.py`:

```python
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
```

- [ ] **Step 4: Run tests — expect all 14 to pass**

Run: `pytest tests/test_fxify_rule_validator.py::TestMaxDrawdown -v`
Expected: 14 passed.

- [ ] **Step 5: Commit**

```bash
git add fxify_rule_validator.py tests/test_fxify_rule_validator.py
git commit -m "$(cat <<'EOF'
feat(fxify_rule_validator): validate_max_drawdown

Inclusive 5%-static floor on initial balance. Round-before-compare
defends against the 200_000 * 0.95 float trap; explicit boundary
test at equity=190000.00 pins the defense. 14 tests cover boundary,
FP-boundary, reason content, default import from firm_rules,
ValueError contract, int-type acceptance, plus an inclusive-
interpretation pin against the only FXIFY worked example for
static DD (2-Phase, 10%).
EOF
)"
```

---

## Task 4: validate_daily_loss (TDD cycle)

Same shape as max_drawdown but basis is prior-day-EOD balance instead of initial balance. Includes the rulebook-anchored worked-example test ($100K → $95K from the FXIFY FAQ).

**Files:**
- Modify: `fxify_rule_validator.py` (add function)
- Modify: `tests/test_fxify_rule_validator.py` (add `TestDailyLoss` class)

- [ ] **Step 1: Write failing tests for `validate_daily_loss`**

Append to `tests/test_fxify_rule_validator.py`:

```python
class TestDailyLoss:
    """validate_daily_loss — FXIFY 3-Phase rule:
    "Daily drawdown - 5% (Based on previous day balance)"
    https://fxify.com/faqs/all-faqs/what-are-the-rules-for-the-assessment-account/

    "Daily Loss Limit is calculated based on the balance at the end of
    the previous day, the balance recorded at 5PM EST time."
    https://fxify.com/faqs/all-faqs/how-do-you-calculate-the-daily-loss-limit/
    """

    # --- Rulebook-anchored worked example (spec §7g) ---

    def test_fxify_3phase_faq_example_100k_to_95k(self):
        # Verbatim FXIFY 3-Phase FAQ:
        # "On a Three phase account, if your prior day's end of day
        #  balance was $100,000 you would breach the Daily Loss Limit
        #  of 5% should your equity the next day fall to $95,000."
        # Source: how-do-you-calculate-the-daily-loss-limit/
        from fxify_rule_validator import validate_daily_loss
        passed, kind, reason = validate_daily_loss(
            current_equity=95_000.00,
            prior_day_eod_balance=100_000.00,
            daily_loss_pct=5.0,
        )
        assert passed is False
        assert kind == "limit"
        assert "95,000.00" in reason

    # --- Boundary ---

    def test_equity_above_floor_passes(self):
        from fxify_rule_validator import validate_daily_loss
        passed, _, _ = validate_daily_loss(
            current_equity=96_000.00,
            prior_day_eod_balance=100_000.00,
            daily_loss_pct=5.0,
        )
        assert passed is True

    def test_one_cent_below_floor_breaches(self):
        from fxify_rule_validator import validate_daily_loss
        passed, _, _ = validate_daily_loss(
            current_equity=94_999.99,
            prior_day_eod_balance=100_000.00,
            daily_loss_pct=5.0,
        )
        assert passed is False

    def test_one_cent_above_floor_passes(self):
        from fxify_rule_validator import validate_daily_loss
        passed, _, _ = validate_daily_loss(
            current_equity=95_000.01,
            prior_day_eod_balance=100_000.00,
            daily_loss_pct=5.0,
        )
        assert passed is True

    # --- FP-boundary defense ---

    def test_at_exact_floor_breaches_despite_float_imprecision(self):
        from fxify_rule_validator import validate_daily_loss
        passed, _, reason = validate_daily_loss(
            current_equity=95_000.00,
            prior_day_eod_balance=100_000.00,
            daily_loss_pct=5.0,
        )
        assert passed is False
        assert "95,000.00" in reason

    # --- Reason content ---

    def test_breach_reason_names_floor_equity_and_pct(self):
        from fxify_rule_validator import validate_daily_loss
        _, _, reason = validate_daily_loss(
            current_equity=90_000.00,
            prior_day_eod_balance=100_000.00,
            daily_loss_pct=5.0,
        )
        assert "90,000.00" in reason
        assert "95,000.00" in reason
        assert "5" in reason

    def test_pass_reason_is_populated(self):
        from fxify_rule_validator import validate_daily_loss
        _, _, reason = validate_daily_loss(
            current_equity=99_500.00,
            prior_day_eod_balance=100_000.00,
            daily_loss_pct=5.0,
        )
        assert reason
        assert "99,500.00" in reason

    # --- Default override ---

    def test_default_pct_comes_from_firm_rules(self):
        from fxify_rule_validator import validate_daily_loss
        passed, _, _ = validate_daily_loss(
            current_equity=95_000.00,
            prior_day_eod_balance=100_000.00,
        )
        assert passed is False  # 5% default

    # --- ValueError contract ---

    def test_negative_equity_raises(self):
        from fxify_rule_validator import validate_daily_loss
        with pytest.raises(ValueError, match="current_equity"):
            validate_daily_loss(
                current_equity=-1.0,
                prior_day_eod_balance=100_000.00,
            )

    def test_zero_prior_day_balance_raises(self):
        from fxify_rule_validator import validate_daily_loss
        with pytest.raises(ValueError, match="prior_day_eod_balance"):
            validate_daily_loss(
                current_equity=100.0,
                prior_day_eod_balance=0.0,
            )

    def test_negative_pct_raises(self):
        from fxify_rule_validator import validate_daily_loss
        with pytest.raises(ValueError, match="daily_loss_pct"):
            validate_daily_loss(
                current_equity=100.0,
                prior_day_eod_balance=100_000.00,
                daily_loss_pct=-1.0,
            )

    # --- Type contract ---

    def test_all_int_inputs_accepted(self):
        from fxify_rule_validator import validate_daily_loss
        passed, _, _ = validate_daily_loss(
            current_equity=95_000,
            prior_day_eod_balance=100_000,
            daily_loss_pct=5,
        )
        assert passed is False
```

- [ ] **Step 2: Run tests — expect all to fail with ImportError**

Run: `pytest tests/test_fxify_rule_validator.py::TestDailyLoss -v`
Expected: 12 errors — `cannot import name 'validate_daily_loss'`.

- [ ] **Step 3: Implement `validate_daily_loss`**

Append to `fxify_rule_validator.py`:

```python
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
```

- [ ] **Step 4: Run tests — expect all 12 to pass**

Run: `pytest tests/test_fxify_rule_validator.py::TestDailyLoss -v`
Expected: 12 passed.

- [ ] **Step 5: Commit**

```bash
git add fxify_rule_validator.py tests/test_fxify_rule_validator.py
git commit -m "$(cat <<'EOF'
feat(fxify_rule_validator): validate_daily_loss

5% daily floor based on prior-day EOD balance (5pm EST per FXIFY FAQ).
Rulebook-anchored test pins the verbatim FXIFY worked example:
$100K prior -> $95K equity = breach. 12 tests, same shape as
validate_max_drawdown.
EOF
)"
```

---

## Task 5: validate_profit_target (TDD cycle)

Same money-validator shape but **completion** kind, opposite direction (`>=` instead of `<=`). No FXIFY worked example — tests use plain values.

**Files:**
- Modify: `fxify_rule_validator.py` (add function)
- Modify: `tests/test_fxify_rule_validator.py` (add `TestProfitTarget` class)

- [ ] **Step 1: Write failing tests for `validate_profit_target`**

Append to `tests/test_fxify_rule_validator.py`:

```python
class TestProfitTarget:
    """validate_profit_target — FXIFY 3-Phase rule:
    "Profit Targets: Phase 1 - 5%, Phase 2 - 5%, Phase 3 - 5%"
    https://fxify.com/faqs/all-faqs/what-are-the-rules-for-the-assessment-account/

    Completion check: passed=True when equity >= initial * (1 + pct/100).
    """

    # --- Boundary (inclusive: equity at exact target = met) ---

    def test_equity_above_target_meets(self):
        from fxify_rule_validator import validate_profit_target
        passed, kind, reason = validate_profit_target(
            current_equity=215_000.00,
            initial_balance=200_000.00,
            profit_target_pct=5.0,
        )
        assert passed is True
        assert kind == "completion"
        assert "215,000.00" in reason
        assert "210,000.00" in reason

    def test_equity_at_exact_target_meets(self):
        from fxify_rule_validator import validate_profit_target
        passed, _, _ = validate_profit_target(
            current_equity=210_000.00,
            initial_balance=200_000.00,
            profit_target_pct=5.0,
        )
        assert passed is True

    def test_one_cent_below_target_does_not_meet(self):
        from fxify_rule_validator import validate_profit_target
        passed, _, _ = validate_profit_target(
            current_equity=209_999.99,
            initial_balance=200_000.00,
            profit_target_pct=5.0,
        )
        assert passed is False

    def test_one_cent_above_target_meets(self):
        from fxify_rule_validator import validate_profit_target
        passed, _, _ = validate_profit_target(
            current_equity=210_000.01,
            initial_balance=200_000.00,
            profit_target_pct=5.0,
        )
        assert passed is True

    # --- FP-boundary defense ---

    def test_at_exact_target_meets_despite_float_imprecision(self):
        # 200_000 * 1.05 == 210000.00000000003 in float;
        # without round(2), equity=210000.00 might not be detected as "met".
        from fxify_rule_validator import validate_profit_target
        passed, kind, _ = validate_profit_target(
            current_equity=210_000.00,
            initial_balance=200_000.00,
            profit_target_pct=5.0,
        )
        assert passed is True
        assert kind == "completion"

    # --- Reason content ---

    def test_unmet_reason_names_target_equity_and_pct(self):
        from fxify_rule_validator import validate_profit_target
        _, _, reason = validate_profit_target(
            current_equity=204_000.00,
            initial_balance=200_000.00,
            profit_target_pct=5.0,
        )
        assert "204,000.00" in reason
        assert "210,000.00" in reason

    def test_met_reason_is_populated(self):
        from fxify_rule_validator import validate_profit_target
        _, _, reason = validate_profit_target(
            current_equity=220_000.00,
            initial_balance=200_000.00,
            profit_target_pct=5.0,
        )
        assert reason
        assert "220,000.00" in reason

    # --- Kind field ---

    def test_kind_is_completion_when_met(self):
        from fxify_rule_validator import validate_profit_target
        _, kind, _ = validate_profit_target(
            current_equity=220_000.00,
            initial_balance=200_000.00,
            profit_target_pct=5.0,
        )
        assert kind == "completion"

    def test_kind_is_completion_when_unmet(self):
        from fxify_rule_validator import validate_profit_target
        _, kind, _ = validate_profit_target(
            current_equity=200_000.00,
            initial_balance=200_000.00,
            profit_target_pct=5.0,
        )
        assert kind == "completion"

    # --- Default override ---

    def test_default_pct_comes_from_firm_rules(self):
        from fxify_rule_validator import validate_profit_target
        passed, _, _ = validate_profit_target(
            current_equity=210_000.00,
            initial_balance=200_000.00,
        )
        assert passed is True  # 5% default, 210K target met

    # --- ValueError contract ---

    def test_negative_equity_raises(self):
        from fxify_rule_validator import validate_profit_target
        with pytest.raises(ValueError, match="current_equity"):
            validate_profit_target(
                current_equity=-1.0,
                initial_balance=200_000.00,
            )

    def test_zero_initial_balance_raises(self):
        from fxify_rule_validator import validate_profit_target
        with pytest.raises(ValueError, match="initial_balance"):
            validate_profit_target(
                current_equity=100.0,
                initial_balance=0.0,
            )

    def test_negative_pct_raises(self):
        from fxify_rule_validator import validate_profit_target
        with pytest.raises(ValueError, match="profit_target_pct"):
            validate_profit_target(
                current_equity=100.0,
                initial_balance=200_000.00,
                profit_target_pct=-1.0,
            )

    # --- Type contract ---

    def test_all_int_inputs_accepted(self):
        from fxify_rule_validator import validate_profit_target
        passed, kind, _ = validate_profit_target(
            current_equity=210_000,
            initial_balance=200_000,
            profit_target_pct=5,
        )
        assert passed is True
        assert kind == "completion"
```

- [ ] **Step 2: Run tests — expect all to fail**

Run: `pytest tests/test_fxify_rule_validator.py::TestProfitTarget -v`
Expected: 14 errors — `cannot import name 'validate_profit_target'`.

- [ ] **Step 3: Implement `validate_profit_target`**

Append to `fxify_rule_validator.py`:

```python
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
```

- [ ] **Step 4: Run tests — expect all 14 to pass**

Run: `pytest tests/test_fxify_rule_validator.py::TestProfitTarget -v`
Expected: 14 passed.

- [ ] **Step 5: Commit**

```bash
git add fxify_rule_validator.py tests/test_fxify_rule_validator.py
git commit -m "$(cat <<'EOF'
feat(fxify_rule_validator): validate_profit_target

5% per-phase target on initial balance. Completion kind, inclusive
at target (equity >= target). FP-boundary test pins exact-target
case at 210000.00. 14 tests cover boundary, kind field both
branches, reason content, ValueError contract, int-type.
EOF
)"
```

---

## Task 6: validate_min_trading_days (TDD cycle)

Integer-only completion check. No money math, no FP concerns.

**Files:**
- Modify: `fxify_rule_validator.py` (add function)
- Modify: `tests/test_fxify_rule_validator.py` (add `TestMinTradingDays` class)

- [ ] **Step 1: Write failing tests for `validate_min_trading_days`**

Append to `tests/test_fxify_rule_validator.py`:

```python
class TestMinTradingDays:
    """validate_min_trading_days — FXIFY 3-Phase rule:
    "Min Trading Days - 5 days (For each phase)"
    https://fxify.com/faqs/all-faqs/what-are-the-rules-for-the-assessment-account/

    Completion check: passed=True when trading_days_completed >= min.
    """

    # --- Boundary ---

    def test_above_minimum_meets(self):
        from fxify_rule_validator import validate_min_trading_days
        passed, kind, reason = validate_min_trading_days(
            trading_days_completed=10,
            min_trading_days=5,
        )
        assert passed is True
        assert kind == "completion"
        assert "10" in reason
        assert "5" in reason

    def test_at_minimum_meets(self):
        from fxify_rule_validator import validate_min_trading_days
        passed, _, _ = validate_min_trading_days(
            trading_days_completed=5,
            min_trading_days=5,
        )
        assert passed is True

    def test_one_below_minimum_does_not_meet(self):
        from fxify_rule_validator import validate_min_trading_days
        passed, _, _ = validate_min_trading_days(
            trading_days_completed=4,
            min_trading_days=5,
        )
        assert passed is False

    def test_zero_days_does_not_meet(self):
        from fxify_rule_validator import validate_min_trading_days
        passed, _, _ = validate_min_trading_days(
            trading_days_completed=0,
            min_trading_days=5,
        )
        assert passed is False

    # --- Reason content ---

    def test_unmet_reason_names_count_and_min(self):
        from fxify_rule_validator import validate_min_trading_days
        _, _, reason = validate_min_trading_days(
            trading_days_completed=3,
            min_trading_days=5,
        )
        assert "3" in reason
        assert "5" in reason

    def test_met_reason_is_populated(self):
        from fxify_rule_validator import validate_min_trading_days
        _, _, reason = validate_min_trading_days(
            trading_days_completed=7,
            min_trading_days=5,
        )
        assert reason
        assert "7" in reason

    # --- Kind field ---

    def test_kind_is_completion_when_met(self):
        from fxify_rule_validator import validate_min_trading_days
        _, kind, _ = validate_min_trading_days(
            trading_days_completed=5,
            min_trading_days=5,
        )
        assert kind == "completion"

    def test_kind_is_completion_when_unmet(self):
        from fxify_rule_validator import validate_min_trading_days
        _, kind, _ = validate_min_trading_days(
            trading_days_completed=2,
            min_trading_days=5,
        )
        assert kind == "completion"

    # --- Default override ---

    def test_default_min_comes_from_firm_rules(self):
        from fxify_rule_validator import validate_min_trading_days
        passed, _, _ = validate_min_trading_days(trading_days_completed=5)
        assert passed is True  # default min=5

    # --- ValueError contract ---

    def test_negative_days_raises(self):
        from fxify_rule_validator import validate_min_trading_days
        with pytest.raises(ValueError, match="trading_days_completed"):
            validate_min_trading_days(trading_days_completed=-1)

    def test_negative_min_raises(self):
        from fxify_rule_validator import validate_min_trading_days
        with pytest.raises(ValueError, match="min_trading_days"):
            validate_min_trading_days(
                trading_days_completed=5,
                min_trading_days=-1,
            )
```

- [ ] **Step 2: Run tests — expect all to fail**

Run: `pytest tests/test_fxify_rule_validator.py::TestMinTradingDays -v`
Expected: 11 errors — `cannot import name 'validate_min_trading_days'`.

- [ ] **Step 3: Implement `validate_min_trading_days`**

Append to `fxify_rule_validator.py`:

```python
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
```

- [ ] **Step 4: Run tests — expect all 11 to pass**

Run: `pytest tests/test_fxify_rule_validator.py::TestMinTradingDays -v`
Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add fxify_rule_validator.py tests/test_fxify_rule_validator.py
git commit -m "$(cat <<'EOF'
feat(fxify_rule_validator): validate_min_trading_days

5-day-per-phase minimum, inclusive (>=). Completion kind. 11 tests
cover boundary, kind field, reason content, ValueError contract,
default import from firm_rules.
EOF
)"
```

---

## Task 7: validate_inactivity (TDD cycle)

Only validator with `datetime` math. Calendar days via `(now - last_trade_at).days >= max_idle_days`. Inclusive breach at the day boundary (consistent with §5a).

**Files:**
- Modify: `fxify_rule_validator.py` (add function)
- Modify: `tests/test_fxify_rule_validator.py` (add `TestInactivity` class)

- [ ] **Step 1: Write failing tests for `validate_inactivity`**

Append to `tests/test_fxify_rule_validator.py`:

```python
from datetime import datetime, timedelta


class TestInactivity:
    """validate_inactivity — FXIFY all-accounts rule:
    "Must place a trade once in 60 days to avoid inactivity. If not,
    this would be considered a hard breach."
    https://fxify.com/faqs/all-faqs/what-are-the-rules-for-the-assessment-account/

    Limit check: passed=True when (now - last_trade_at).days < max_idle_days.
    Calendar days (timedelta.days truncates).
    """

    # --- Boundary ---

    def test_recent_trade_passes(self):
        from fxify_rule_validator import validate_inactivity
        now = datetime(2026, 5, 10, 12, 0, 0)
        last = now - timedelta(days=10)
        passed, kind, reason = validate_inactivity(
            last_trade_at=last,
            now=now,
            max_idle_days=60,
        )
        assert passed is True
        assert kind == "limit"
        assert "10" in reason
        assert "60" in reason

    def test_at_max_idle_days_breaches(self):
        # Inclusive at day boundary per spec §5a.
        from fxify_rule_validator import validate_inactivity
        now = datetime(2026, 5, 10, 12, 0, 0)
        last = now - timedelta(days=60)
        passed, _, _ = validate_inactivity(
            last_trade_at=last,
            now=now,
            max_idle_days=60,
        )
        assert passed is False

    def test_one_day_below_max_passes(self):
        from fxify_rule_validator import validate_inactivity
        now = datetime(2026, 5, 10, 12, 0, 0)
        last = now - timedelta(days=59)
        passed, _, _ = validate_inactivity(
            last_trade_at=last,
            now=now,
            max_idle_days=60,
        )
        assert passed is True

    def test_one_day_above_max_breaches(self):
        from fxify_rule_validator import validate_inactivity
        now = datetime(2026, 5, 10, 12, 0, 0)
        last = now - timedelta(days=61)
        passed, _, _ = validate_inactivity(
            last_trade_at=last,
            now=now,
            max_idle_days=60,
        )
        assert passed is False

    # --- Sub-day timedelta truncates to .days ---

    def test_60_days_minus_one_hour_does_not_breach(self):
        # 59 days 23 hours -> .days == 59 -> not yet breach
        from fxify_rule_validator import validate_inactivity
        now = datetime(2026, 5, 10, 12, 0, 0)
        last = now - timedelta(days=60) + timedelta(hours=1)
        passed, _, _ = validate_inactivity(
            last_trade_at=last,
            now=now,
            max_idle_days=60,
        )
        assert passed is True

    # --- Reason content ---

    def test_breach_reason_names_idle_count_and_max(self):
        from fxify_rule_validator import validate_inactivity
        now = datetime(2026, 5, 10, 12, 0, 0)
        last = now - timedelta(days=67)
        _, _, reason = validate_inactivity(
            last_trade_at=last,
            now=now,
            max_idle_days=60,
        )
        assert "67" in reason
        assert "60" in reason

    def test_pass_reason_is_populated(self):
        from fxify_rule_validator import validate_inactivity
        now = datetime(2026, 5, 10, 12, 0, 0)
        last = now - timedelta(days=3)
        _, _, reason = validate_inactivity(
            last_trade_at=last,
            now=now,
            max_idle_days=60,
        )
        assert reason
        assert "3" in reason

    # --- Kind field ---

    def test_kind_is_limit_when_passing(self):
        from fxify_rule_validator import validate_inactivity
        now = datetime(2026, 5, 10, 12, 0, 0)
        _, kind, _ = validate_inactivity(
            last_trade_at=now - timedelta(days=1),
            now=now,
        )
        assert kind == "limit"

    def test_kind_is_limit_when_breaching(self):
        from fxify_rule_validator import validate_inactivity
        now = datetime(2026, 5, 10, 12, 0, 0)
        _, kind, _ = validate_inactivity(
            last_trade_at=now - timedelta(days=70),
            now=now,
        )
        assert kind == "limit"

    # --- Default override ---

    def test_default_max_comes_from_firm_rules(self):
        from fxify_rule_validator import validate_inactivity
        now = datetime(2026, 5, 10, 12, 0, 0)
        last = now - timedelta(days=60)
        passed, _, _ = validate_inactivity(last_trade_at=last, now=now)
        assert passed is False  # default 60-day inclusive

    # --- Clock-skew tolerance (spec §6a): up to 5 min future-stamp ok,
    #     beyond raises. DXTrade fill timestamps vs local now() routinely
    #     skew sub-second to seconds; raising on microsecond skew is a
    #     constant false positive. ---

    def test_future_last_trade_within_skew_tolerance_passes(self):
        from fxify_rule_validator import validate_inactivity
        now = datetime(2026, 5, 10, 12, 0, 0)
        near_future = now + timedelta(minutes=4, seconds=59)
        passed, kind, _ = validate_inactivity(
            last_trade_at=near_future,
            now=now,
            max_idle_days=60,
        )
        # Within tolerance: clamped to fresh, passes.
        assert passed is True
        assert kind == "limit"

    def test_future_last_trade_at_exact_5min_boundary_passes(self):
        # Inclusive at boundary: 5 min 0 sec exactly -> tolerated.
        from fxify_rule_validator import validate_inactivity
        now = datetime(2026, 5, 10, 12, 0, 0)
        at_boundary = now + timedelta(minutes=5)
        passed, _, _ = validate_inactivity(
            last_trade_at=at_boundary,
            now=now,
            max_idle_days=60,
        )
        assert passed is True

    def test_future_last_trade_beyond_skew_tolerance_raises(self):
        # 5 min 1 sec -> beyond tolerance -> raise.
        from fxify_rule_validator import validate_inactivity
        now = datetime(2026, 5, 10, 12, 0, 0)
        far_future = now + timedelta(minutes=5, seconds=1)
        with pytest.raises(ValueError, match="last_trade_at"):
            validate_inactivity(last_trade_at=far_future, now=now)

    # --- ValueError contract (other) ---

    def test_negative_max_idle_days_raises(self):
        from fxify_rule_validator import validate_inactivity
        now = datetime(2026, 5, 10, 12, 0, 0)
        with pytest.raises(ValueError, match="max_idle_days"):
            validate_inactivity(
                last_trade_at=now,
                now=now,
                max_idle_days=-1,
            )
```

- [ ] **Step 2: Run tests — expect all to fail**

Run: `pytest tests/test_fxify_rule_validator.py::TestInactivity -v`
Expected: 14 errors — `cannot import name 'validate_inactivity'`.

- [ ] **Step 3: Add module-level skew-tolerance constant + implement `validate_inactivity`**

First, append the constant near the top of `fxify_rule_validator.py`, just below the `RuleResult` type alias:

```python
# Clock-skew tolerance for validate_inactivity. DXTrade fill timestamps
# vs local now() routinely differ by sub-second to seconds; raising on
# microsecond skew would be a constant false positive. Sub-5-min future
# stamps are silently clamped to "fresh"; beyond 5 min raises. Spec §6a.
_CLOCK_SKEW_TOLERANCE_SECONDS = 300
```

Then append the function at the bottom of `fxify_rule_validator.py`:

```python
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
```

- [ ] **Step 4: Run tests — expect all 14 to pass**

Run: `pytest tests/test_fxify_rule_validator.py::TestInactivity -v`
Expected: 14 passed.

- [ ] **Step 5: Commit**

```bash
git add fxify_rule_validator.py tests/test_fxify_rule_validator.py
git commit -m "$(cat <<'EOF'
feat(fxify_rule_validator): validate_inactivity

60-day calendar-day idle limit, inclusive at boundary. Limit kind.
5-minute clock-skew tolerance: sub-5-min future stamps silently
clamped to "fresh" (DXTrade vs local now() routinely skew this much);
beyond 5 min raises ValueError. 14 tests cover boundary (incl. sub-
day timedelta truncation, three skew-tolerance cases), kind field,
reason content, and ValueError contract.
EOF
)"
```

---

## Task 8: Final cross-cutting verification + caller-idiom doctest

After all 5 validators are in, run the full suite and add one cross-cutting test that exercises the caller filter idiom from the module docstring. This is the "downstream code that does `all(v[0] for v in validators)`" example from the brainstorming pushback — concretized as a regression-pin so the spec's filter idiom can't silently rot.

**Files:**
- Modify: `tests/test_fxify_rule_validator.py` (add `TestCallerIdiom` class)

- [ ] **Step 1: Add caller-idiom regression test**

Append to `tests/test_fxify_rule_validator.py`:

```python
class TestCallerIdiom:
    """Pins the caller-side filter idiom from the module docstring.

    A fresh, healthy account: limits all pass, completions all unmet
    (no profit yet, no trading days yet). Distinguishes 'in good
    standing' from 'phase passed'.
    """

    def test_fresh_account_in_good_standing_but_phase_not_passed(self):
        from fxify_rule_validator import (
            validate_daily_loss,
            validate_inactivity,
            validate_max_drawdown,
            validate_min_trading_days,
            validate_profit_target,
        )

        now = datetime(2026, 5, 10, 12, 0, 0)
        # Just-opened $200K account, traded 1 day ago, 0 trading days
        # complete, no PnL.
        results = [
            validate_daily_loss(
                current_equity=200_000.00,
                prior_day_eod_balance=200_000.00,
            ),
            validate_max_drawdown(
                current_equity=200_000.00,
                initial_balance=200_000.00,
            ),
            validate_inactivity(
                last_trade_at=now - timedelta(days=1),
                now=now,
            ),
            validate_profit_target(
                current_equity=200_000.00,
                initial_balance=200_000.00,
            ),
            validate_min_trading_days(trading_days_completed=0),
        ]

        breached = [r for r in results if r[1] == "limit" and not r[0]]
        unmet = [r for r in results if r[1] == "completion" and not r[0]]
        in_good_standing = not breached
        phase_passed = not breached and not unmet

        assert in_good_standing is True
        assert phase_passed is False
        assert len(unmet) == 2  # profit target + min trading days

    def test_breached_account_not_in_good_standing(self):
        from fxify_rule_validator import (
            validate_daily_loss,
            validate_inactivity,
            validate_max_drawdown,
            validate_min_trading_days,
            validate_profit_target,
        )

        now = datetime(2026, 5, 10, 12, 0, 0)
        # Equity at static-DD floor on day 10.
        results = [
            validate_daily_loss(
                current_equity=190_000.00,
                prior_day_eod_balance=195_000.00,
            ),
            validate_max_drawdown(
                current_equity=190_000.00,
                initial_balance=200_000.00,
            ),
            validate_inactivity(
                last_trade_at=now - timedelta(days=1),
                now=now,
            ),
            validate_profit_target(
                current_equity=190_000.00,
                initial_balance=200_000.00,
            ),
            validate_min_trading_days(trading_days_completed=10),
        ]

        breached = [r for r in results if r[1] == "limit" and not r[0]]
        in_good_standing = not breached

        assert in_good_standing is False
        assert len(breached) == 1  # max DD only — daily loss within 5% of prior day
```

- [ ] **Step 2: Run the full validator test file**

Run: `pytest tests/test_fxify_rule_validator.py -v`
Expected: All tests pass. Count should be 1 (smoke) + 14 (max_dd) + 12 (daily_loss) + 14 (profit_target) + 11 (min_trading_days) + 14 (inactivity) + 2 (caller idiom) = **68 passed**.

- [ ] **Step 3: Run full repo test suite to confirm no regressions**

Run: `pytest tests/ -v --no-header 2>&1 | tail -30`
Expected: All existing tests still pass alongside the 65 new ones.

- [ ] **Step 4: Confirm py-modules registration works post-install**

Run: `python -c "import fxify_rule_validator; print([n for n in dir(fxify_rule_validator) if n.startswith('validate_')])"`
Expected output: `['validate_daily_loss', 'validate_inactivity', 'validate_max_drawdown', 'validate_min_trading_days', 'validate_profit_target']`

- [ ] **Step 5: Commit**

```bash
git add tests/test_fxify_rule_validator.py
git commit -m "$(cat <<'EOF'
test(fxify_rule_validator): caller-idiom regression pin

Two end-to-end tests exercise the module-docstring filter idiom for
distinguishing 'in good standing' (no limit breaches) from 'phase
passed' (no breaches AND no unmet completions). Pins the public
contract against future drift.
EOF
)"
```

---

## Self-review (run by plan author after writing)

Spec coverage check:

| Spec section | Implemented in |
|---|---|
| §1 Purpose | Task 2 docstring |
| §2 Scope reconciliation | (audit-only; no code) |
| §3 Module surface | Task 2 (skeleton) + Tasks 3-7 (functions) |
| §4 Return semantics + caller idiom | Task 8 caller-idiom tests pin both |
| §5a Inclusive `<=` | Task 3 step 3 (max_dd) + Task 4 step 3 (daily_loss); §7 boundary tests |
| §5b FP money math + audit finding | Task 3, 4, 5 round-before-compare + dedicated FP-boundary tests; audit finding (dd_protection.py) is documentation-only, deferred per §11 |
| §5c Calendar-day inactivity | Task 7 |
| §5d Type contract | Tasks 3-7 each include `test_all_int_inputs_accepted` (where applicable) |
| §6 ValueError contract | Tasks 3-7 each include `pytest.raises(ValueError)` tests for each invalid input |
| §6a Clock-skew tolerance | Task 7: module constant `_CLOCK_SKEW_TOLERANCE_SECONDS=300` + 3 dedicated tests (within / at-boundary / beyond) |
| §7 Test plan | Tasks 3-7 (per-validator) + Task 8 (cross-cutting) |
| §8 Out of scope | (deliberate exclusions; no code) |
| §9 Files touched | Task 1 (firm_rules + pyproject) + Task 2 (module + test) |
| §10 Verbatim quotes | Class docstrings in each test class quote the rule and cite URL |
| §11 Open follow-ups | Deliberately not scheduled |

Placeholder scan: no `TBD`, `TODO`, `# similar to`, or "implement later" in any task. Every step has either runnable code or a runnable command with expected output.

Type consistency: `RuleKind = Literal["limit", "completion"]` defined in Task 2; every validator returns `RuleResult = tuple[bool, RuleKind, str]`; every test uses the exact `(passed, kind, reason)` unpacking. `validate_*` names consistent across spec, plan, and tests. Defaults named consistently as `_FXIFY[...]` lookups everywhere.

No issues found.
