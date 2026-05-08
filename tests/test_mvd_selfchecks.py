"""MVD self-check confirmation.

dd_protection._validate_protection_rule() runs at module import. If the
boundary check fails or the spec pin literal drifts past DD_TRIGGER=0.015 /
DD_SCALE=0.40, the import raises AssertionError. This test makes the
import-time guard visible at the test layer so it cannot be silently disabled.

Constants relocked 2026-05-08 from C0 (0.010, 0.40) to C2 (0.015, 0.40)
after bust_attribution_flip closed broker-feed-confirmed; see Q-DDP-1
recommendation.md OVERRIDE section.
"""


def test_dd_protection_self_check_passes_at_import():
    import dd_protection

    assert callable(dd_protection._validate_protection_rule)
    # Spec-pinned constants — duplicated here so a constant drift fails this
    # test even if the spec pin in dd_protection.py is also drifted.
    assert dd_protection.DD_TRIGGER == 0.015
    assert dd_protection.DD_SCALE == 0.40
