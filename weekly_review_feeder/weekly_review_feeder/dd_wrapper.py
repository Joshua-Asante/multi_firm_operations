"""dd_protection.py log parser — STUB.

Per spec §0 Rule-0: confirm dd_protection.py log format before implementing.

Likely log shapes (one of):

A) Append-only JSONL at WRF_DD_LOG path, one event per line:
    {"timestamp": "2026-05-08T13:00:00Z", "event": "tier_change",
     "from": "C0", "to": "C2", "reason": "rolling_pnl_lt_p5_floor"}

B) Structured log via Python logging:
    2026-05-08 13:00:00 INFO dd_protection trigger=tier_change C0->C2

C) CLI with state-snapshot mode:
    python dd_protection.py --events --since 2026-05-04 --until 2026-05-08

Wire `count_dd_events_for_week` to whichever your dd_protection.py uses.

Definition of 'event' for this purpose:
    Any tier change OR risk-multiplier change OR explicit FIRE-alert.
    Per existing dd_protection convention.
"""
from __future__ import annotations

from datetime import date


def count_dd_events_for_week(log_path: str, week_start: date, week_end: date) -> int:
    """Count dd_protection trigger events in the inclusive week range.

    STUB — wire to your dd_protection.py log per docstring above.
    """
    raise NotImplementedError(
        "Wire to dd_protection.py log per spec §0 Rule-0 read. "
        "See module docstring for likely log shapes."
    )


def latest_dd_state(log_path: str) -> dict[str, object]:
    """Optional: return latest dd_protection state for the Pre-Market routine.

    Output: {tier, risk_multiplier, current_equity, peak_equity, current_dd_pct}
    Not strictly required by the Weekly Review feeder — present for symmetry
    with the Pre-Market Routine artifact.
    """
    raise NotImplementedError("Optional — wire if used by Pre-Market routine.")
