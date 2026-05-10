"""Tests for fxify_rule_validator.

Source-of-truth pins (FXIFY rulebook URLs cited inline in each test class):
  * https://fxify.com/faqs/all-faqs/how-do-you-calculate-the-daily-loss-limit/
  * https://fxify.com/faqs/all-faqs/what-is-static-drawdown/
  * https://fxify.com/faqs/all-faqs/what-are-the-rules-for-the-assessment-account/
"""


def test_module_imports_cleanly():
    import fxify_rule_validator  # noqa: F401


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
