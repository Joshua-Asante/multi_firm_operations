"""mc_wrapper.py acceptance test.

Verifies the composed Pattern A wiring against the real Pepperstone panel.
The wrapper imports portfolio_mc which loads data/tv_exports/pepperstone/ via
paths anchored at portfolio_mc.__file__ — runs correctly regardless of cwd.

Run with (mirrors test_w19.py invocation):
    cd weekly_review_feeder
    python -m tests.test_mc_wrapper
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

# Make package importable when run as a script.
sys.path.insert(0, str(Path(__file__).parent.parent))

from weekly_review_feeder.mc_wrapper import get_mc_band_for_week


def test_mc_wrapper():
    failures: list[str] = []

    band = get_mc_band_for_week(date(2026, 5, 4), date(2026, 5, 8))

    # Schema
    if set(band.keys()) != {"p10", "p50", "p90"}:
        failures.append(f"  schema: got keys {set(band.keys())!r}, expected {{'p10','p50','p90'}}")
    for k in ("p10", "p50", "p90"):
        if k in band and not isinstance(band[k], float):
            failures.append(f"  type: band[{k!r}] is {type(band[k]).__name__}, expected float")

    # Ordering
    if not (band["p10"] < band["p50"] < band["p90"]):
        failures.append(f"  ordering: expected p10 < p50 < p90, got {band}")

    # Sanity bounds (Pepperstone panel: ~98% pass, so weekly P&L distribution
    # straddles zero with a right tail).
    if band["p10"] >= 0:
        failures.append(f"  p10 >= 0: {band['p10']!r} — expected losing weeks in left tail")
    if band["p90"] <= 0:
        failures.append(f"  p90 <= 0: {band['p90']!r} — expected winning weeks in right tail")

    # Stability contract: week_start/week_end are accepted-but-unused. A
    # different week range MUST return the same band. If this test starts
    # failing, the wrapper has been refactored to filter by week — re-read
    # the wrapper docstring before "fixing" the test.
    band_other = get_mc_band_for_week(date(2024, 3, 4), date(2024, 3, 8))
    for k in ("p10", "p50", "p90"):
        if band[k] != band_other[k]:
            failures.append(
                f"  stability: band[{k!r}] differs across week args "
                f"({band[k]!r} vs {band_other[k]!r}) — wrapper now filters by week, "
                f"contract changed; update the docstring + this test deliberately."
            )

    print("=== MC WRAPPER BAND ===")
    print(f"p10: {band['p10']:>12,.2f}")
    print(f"p50: {band['p50']:>12,.2f}")
    print(f"p90: {band['p90']:>12,.2f}")
    print()
    if failures:
        print("=== FAILURES ===")
        for f in failures:
            print(f)
        return False
    print("=== ALL CHECKS PASSED ===")
    return True


if __name__ == "__main__":
    ok = test_mc_wrapper()
    sys.exit(0 if ok else 1)
