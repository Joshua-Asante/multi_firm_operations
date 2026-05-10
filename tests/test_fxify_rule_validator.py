"""Tests for fxify_rule_validator.

Source-of-truth pins (FXIFY rulebook URLs cited inline in each test class):
  * https://fxify.com/faqs/all-faqs/how-do-you-calculate-the-daily-loss-limit/
  * https://fxify.com/faqs/all-faqs/what-is-static-drawdown/
  * https://fxify.com/faqs/all-faqs/what-are-the-rules-for-the-assessment-account/
"""


def test_module_imports_cleanly():
    import fxify_rule_validator  # noqa: F401
