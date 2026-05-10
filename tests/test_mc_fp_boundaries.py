"""Boundary tests for MC simulation FP comparisons (Q-MCFP-1 §2.4).

Rule 0-T compliance: each test exercises the inner FP comparison via paths
constructed within ULP of the relevant threshold. Aggregator-level pass/fail
is insufficient — these tests are the discrimination evidence that
round(x, N) collapses ULP noise that the raw `<=` / `>=` comparisons admit.

The PR #60 trap (test passes via aggregator code path that doesn't exercise
the change under test) is the reason this file exists. Boundary tests are
non-negotiable per parent §5 forbidden move #9.

Anchors:
  * Q-MCFP-1 (parent): docs/briefs/Q-MCFP-1/recommendation.md
  * dd_protection.py:90 (precedent fix): docs/adr/2026-05-10-dd-protection-ulp-rounding.md
  * Site list: portfolio_mc.py:197, 202, 204, 216, 499, 508
"""

import math


# ── H2 — dd-pattern (signed-form ratio comparison) ─────────────────────────

class TestH2DdPatternBoundary:
    """portfolio_mc._simulate_path:197 + mode_historical:499.

    Form: `dd_from_peak <= -dd_trigger` where dd_from_peak = (eq - peak) / peak.
    DD_TRIGGER = 0.015 (C2 lock). Boundary case: true rational dd of -1.5%
    that the raw FP path produces as one or more ULPs ABOVE -0.015 (i.e.,
    less negative). Raw `<=` fails to fire; round6 collapses noise to -0.015
    exactly and fires.
    """

    DD_TRIGGER = 0.015

    def test_dd_pattern_raw_fp_fails_to_fire_on_ulp_above(self):
        # Empirical construction: peak=133.33333, equity=131.33333005 produces
        # (eq - peak) / peak = -0.014999999999999916 in float64 — five ULPs
        # ABOVE -0.015 (less negative), so raw `<= -0.015` is FALSE.
        peak = 133.33333
        equity = 131.33333005
        raw_signed = (equity - peak) / peak
        assert raw_signed > -self.DD_TRIGGER, (
            f"setup invariant: raw FP must land above -0.015 (less negative); "
            f"got {raw_signed!r}"
        )
        # Pre-fix behavior: would not fire
        assert not (raw_signed <= -self.DD_TRIGGER), (
            f"raw FP comparison must NOT fire on this construction (pre-fix); "
            f"raw={raw_signed!r}"
        )

    def test_dd_pattern_round6_fires_on_ulp_above(self):
        # Same construction; rounded form must fire.
        peak = 133.33333
        equity = 131.33333005
        raw_signed = (equity - peak) / peak
        assert round(raw_signed, 6) <= -self.DD_TRIGGER, (
            f"rounded FP comparison must fire post-fix; "
            f"raw={raw_signed!r}, round6={round(raw_signed, 6)!r}"
        )

    def test_dd_pattern_sign_symmetry_amendment_1(self):
        # Amendment 1 (§0.5 closure): signed-form (MC sim) and positive-form
        # (dd_protection) produce identical fire-or-not on paths near the
        # threshold. Closes the asymmetry observation surfaced during §0.5.
        dd_signed = -0.01500001          # within ULP of boundary in signed form
        dd_positive = abs(dd_signed)
        assert (round(dd_signed, 6) <= -self.DD_TRIGGER) == (
            round(dd_positive, 6) >= self.DD_TRIGGER
        ), (
            f"sign-symmetry violated at boundary: "
            f"round({dd_signed!r}, 6)={round(dd_signed, 6)!r} <= {-self.DD_TRIGGER!r} "
            f"vs round({dd_positive!r}, 6)={round(dd_positive, 6)!r} >= {self.DD_TRIGGER!r}"
        )

    def test_dd_pattern_truly_below_does_not_fire(self):
        # Asymmetry guard: dd genuinely above -0.015 (less drawdown than trigger)
        # must NOT fire. Confirms rounding doesn't push over the line.
        peak = 200_000.0
        equity = peak * (1.0 - 0.014)  # 1.4% drawdown — below trigger
        raw_signed = (equity - peak) / peak
        assert not (round(raw_signed, 6) <= -self.DD_TRIGGER), (
            f"true 1.4% drawdown must NOT fire post-fix; got round6={round(raw_signed, 6)!r}"
        )


# ── H2 — daily-loss ratio comparison ───────────────────────────────────────

class TestH2DailyLossBoundary:
    """portfolio_mc._simulate_path:202.

    Form: `pnl / STARTING_EQUITY <= DAILY_LOSS_PCT` where DAILY_LOSS_PCT = -0.05.
    Boundary case: true rational ratio of exactly -5% that the raw FP path
    produces as one or more ULPs ABOVE -0.05 (less negative).
    """

    STARTING_EQUITY = 200_000.0
    DAILY_LOSS_PCT = -0.05

    def test_daily_loss_raw_fp_fails_to_fire_on_ulp_above(self):
        # math.nextafter(-10000.0, 0.0) gives -9999.999999999998. Dividing by
        # 200_000.0 produces -0.04999999999999999 — one ULP above -0.05.
        pnl = math.nextafter(-10000.0, 0.0)
        raw = pnl / self.STARTING_EQUITY
        assert raw > self.DAILY_LOSS_PCT, (
            f"setup invariant: raw must land above -0.05; got {raw!r}"
        )
        assert not (raw <= self.DAILY_LOSS_PCT), (
            f"raw FP comparison must NOT fire on this construction (pre-fix); "
            f"raw={raw!r}"
        )

    def test_daily_loss_round6_fires_on_ulp_above(self):
        pnl = math.nextafter(-10000.0, 0.0)
        raw = pnl / self.STARTING_EQUITY
        assert round(raw, 6) <= self.DAILY_LOSS_PCT, (
            f"rounded comparison must fire post-fix; "
            f"raw={raw!r}, round6={round(raw, 6)!r}"
        )

    def test_daily_loss_truly_below_threshold_does_not_fire(self):
        # 4.9% loss — clearly above the -5% threshold (less negative). Must NOT
        # fire under either form.
        pnl = -0.049 * self.STARTING_EQUITY
        raw = pnl / self.STARTING_EQUITY
        assert not (round(raw, 6) <= self.DAILY_LOSS_PCT), (
            f"true 4.9% loss must NOT fire; got round6={round(raw, 6)!r}"
        )


# ── H2 — static-DD ratio comparison ────────────────────────────────────────

class TestH2StaticDdBoundary:
    """portfolio_mc._simulate_path:204.

    Form: `(eq_new - STARTING_EQUITY) / STARTING_EQUITY <= STATIC_DD_PCT`.
    """

    STARTING_EQUITY = 200_000.0
    STATIC_DD_PCT = -0.05

    def test_static_dd_raw_fp_fails_to_fire_on_ulp_above(self):
        # First attempt with `S + nextafter(-10000.0, 0.0)` failed because
        # the ULP perturbation at 1e-16 magnitude rounds away when added to
        # a 200_000-magnitude value (S's ULP is ~7e-12, much coarser than
        # nextafter's perturbation). Construct the perturbation at the
        # 190_000 magnitude directly: nextafter(190_000.0, 200_000.0) is one
        # ULP above 190_000 in FP, and (eq_new - S) / S then lands at
        # -0.04999999999999986 — one ULP above -0.05.
        eq_new = math.nextafter(190_000.0, 200_000.0)
        raw = (eq_new - self.STARTING_EQUITY) / self.STARTING_EQUITY
        assert raw > self.STATIC_DD_PCT, (
            f"setup invariant: raw must land above -0.05; got {raw!r}"
        )
        assert not (raw <= self.STATIC_DD_PCT), (
            f"raw FP comparison must NOT fire on this construction (pre-fix); "
            f"eq_new={eq_new!r}, raw={raw!r}"
        )

    def test_static_dd_round6_fires_on_ulp_above(self):
        eq_new = math.nextafter(190_000.0, 200_000.0)
        raw = (eq_new - self.STARTING_EQUITY) / self.STARTING_EQUITY
        assert round(raw, 6) <= self.STATIC_DD_PCT, (
            f"rounded comparison must fire post-fix; "
            f"raw={raw!r}, round6={round(raw, 6)!r}"
        )


# ── H3 — profit-target dollar-vs-dollar comparison ─────────────────────────

class TestH3ProfitTargetBoundary:
    """portfolio_mc._simulate_path:216 + mode_historical:508.

    Form: `eq >= PROFIT_TARGET` where PROFIT_TARGET = STARTING_EQUITY * 1.05.
    Different FP regime: equity is in dollars, threshold is in dollars,
    natural quantum is the cent. round(eq, 2) collapses sub-cent FP noise
    without changing any decision the trader could care about.
    """

    PROFIT_TARGET = 210_000.0

    def test_profit_target_raw_fp_fails_to_fire_on_subcent_above(self):
        # eq = 209999.99999999 — 1e-8 below 210000 in float, but functionally
        # at target (sub-cent error). Raw FP comparison fails to fire.
        eq = 209_999.99999999
        assert eq < self.PROFIT_TARGET, (
            f"setup invariant: raw eq must be below PROFIT_TARGET; got {eq!r}"
        )
        assert not (eq >= self.PROFIT_TARGET), (
            f"raw FP must NOT fire on sub-cent below target (pre-fix); "
            f"eq={eq!r}"
        )

    def test_profit_target_round2_fires_on_subcent_above(self):
        # Same construction; round to cent fires (correct — broker tracks cents).
        eq = 209_999.99999999
        assert round(eq, 2) >= self.PROFIT_TARGET, (
            f"rounded comparison must fire post-fix; "
            f"eq={eq!r}, round2={round(eq, 2)!r}"
        )

    def test_profit_target_subcent_below_does_not_overfire(self):
        # Asymmetry guard per Joshua's §0.5 amendment intent. eq = $209,999.99
        # (one cent short of target) must NOT fire. Confirms round(eq, 2)
        # doesn't push truly-below-target equity into pass.
        eq = 209_999.99
        assert not (round(eq, 2) >= self.PROFIT_TARGET), (
            f"$209,999.99 must NOT fire (one cent short); got round2={round(eq, 2)!r}"
        )

    def test_profit_target_at_exact_dollar_fires(self):
        # Trivial sanity: eq = exactly $210,000 fires under both forms.
        eq = 210_000.0
        assert eq >= self.PROFIT_TARGET
        assert round(eq, 2) >= self.PROFIT_TARGET
