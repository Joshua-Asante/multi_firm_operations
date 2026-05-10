"""Tests for dd_protection.calculate_protection — ULP-precision boundary.

Anchor: docs/adr/2026-05-10-dd-protection-ulp-rounding.md
Live binding: docs/adr/2026-05-08-dd-trigger-c2-relock.md (DD_TRIGGER = 0.015,
              DD_SCALE = 0.40 single-tier).
"""


def test_module_imports_cleanly():
    import dd_protection  # noqa: F401


class TestULPBoundary:
    """calculate_protection — trigger comparison must be precision-stable.

    The line-89 expression `(peak - equity) / peak` lands one or more ULPs
    below the true rational answer for ~half of realistic (peak, equity)
    pairs at the 1.5% boundary. The fix at line 90 rounds to 6 dp before
    the `>= DD_TRIGGER` compare. These tests pin both sides of the
    asymmetric-error-cost reading: must fire on true-1.5% drawdowns
    regardless of float path, must NOT fire on truly-below drawdowns.
    """

    # --- Boundary: dd computed exactly at trigger via clean ratio ---

    def test_dd_protection_fires_at_exact_trigger(self):
        from dd_protection import calculate_protection, DD_SCALE
        # peak=1000.0, equity=985.0 → (1000-985)/1000 = 0.015 (clean ratio,
        # rounds-to-nearest in float64 to the same float as the literal
        # 0.015). Both pre-fix and post-fix fire here; this pins that the
        # fix did not accidentally invert the comparison.
        result = calculate_protection(equity=985.0, peak=1000.0)
        assert result["dd_triggered"] is True
        assert result["multiplier"] == DD_SCALE

    # --- Load-bearing falsifier: float path lands below the literal ---

    def test_dd_protection_fires_one_ulp_below_via_float_path(self):
        from dd_protection import calculate_protection, DD_TRIGGER, DD_SCALE
        # peak=133.33333, equity=131.33333005 are constructed so the *true
        # rational* dd is 0.015 (within representable precision of the
        # inputs themselves), but the line-89 float arithmetic
        # (peak - equity) / peak lands at 0.014999999999999916 — five ULPs
        # below DD_TRIGGER. Pre-fix this DOES NOT fire (raw FP < 0.015);
        # post-fix this MUST fire (round(0.014999999999999916, 6) = 0.015).
        peak = 133.33333
        equity = 131.33333005
        raw_dd = (peak - equity) / peak
        assert raw_dd < DD_TRIGGER, (
            f"setup invariant: raw float path must produce dd < DD_TRIGGER; "
            f"got {raw_dd!r}"
        )
        assert round(raw_dd, 6) >= DD_TRIGGER, (
            f"setup invariant: rounded path must >= DD_TRIGGER; "
            f"got {round(raw_dd, 6)!r}"
        )
        result = calculate_protection(equity=equity, peak=peak)
        assert result["dd_triggered"] is True, (
            f"ULP-below true-1.5%-drawdown must fire post-fix; "
            f"raw_dd={raw_dd!r}"
        )
        assert result["multiplier"] == DD_SCALE

    # --- Asymmetry guard: rounding does not over-fire ---

    def test_dd_protection_does_not_fire_truly_below_trigger(self):
        from dd_protection import calculate_protection
        # 1.49% drawdown is well below trigger at 6 dp scale (0.014900 vs
        # 0.015000). Post-fix must NOT fire — rounding collapses ULP noise
        # but does not push truly-below-trigger drawdowns over the line.
        peak = 200_000.00
        equity = peak * (1.0 - 0.0149)  # true dd = 1.49%
        result = calculate_protection(equity=equity, peak=peak)
        assert result["dd_triggered"] is False
        assert result["multiplier"] == 1.0

    # --- Trivial above-trigger sanity ---

    def test_dd_protection_fires_above_trigger(self):
        from dd_protection import calculate_protection, DD_SCALE
        # 2.0% drawdown — comfortably above any precision question
        peak = 200_000.00
        equity = peak * (1.0 - 0.020)
        result = calculate_protection(equity=equity, peak=peak)
        assert result["dd_triggered"] is True
        assert result["multiplier"] == DD_SCALE

    # --- Idempotency: pure function, no state mutation ---

    def test_dd_protection_no_double_fire_on_repeat_evaluation(self):
        from dd_protection import calculate_protection
        # Same inputs called twice must yield identical results. Pins
        # that the fix did not introduce inadvertent state mutation
        # (the round() call is a pure operation; this guards against
        # future refactors that move state through the comparison path).
        peak = 200_000.00
        equity = 197_000.00  # exactly 1.5% drawdown
        first = calculate_protection(equity=equity, peak=peak)
        second = calculate_protection(equity=equity, peak=peak)
        assert first["dd_triggered"] == second["dd_triggered"]
        assert first["multiplier"] == second["multiplier"]
        assert first["dd_from_peak"] == second["dd_from_peak"]
        assert first["scaled_risk"] == second["scaled_risk"]
