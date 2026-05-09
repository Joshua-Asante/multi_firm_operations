"""dd_protection.py log parser — BLOCKED per handoff §8 (2026-05-09).

Rule-0 read of dd_protection.py invalidated the log-shape hypothesis below:
dd_protection.py is a state machine, not an event log. It writes a single
JSON state file (dd_protection_state.json next to dd_protection.py) with
equity-update snapshots — no `event` field, no `tier_change` /
`risk_multiplier_change` / `FIRE-alert` taxonomy in source. The state file
does not exist until the first equity update.

Handoff §8 covers this exact case ("dd_protection.py doesn't log events at
all and only writes state snapshots") and instructs: DO NOT improvise.
The wrapper stays as NotImplementedError until upstream resolves whether to:
    (a) extend dd_protection.py with a real event-log emit path,
    (b) redefine this wrapper as 'count multiplier transitions from snapshot
        history' (a derived heuristic, not a per-existing-convention event),
    (c) accept that dd_events is unsupported until the underlying module
        changes.

See weekly_review_feeder/WIRING_NOTES.md "§8 BLOCKED — dd_wrapper" for the
full structural finding and recommended upstream follow-ups.

The original log-shape hypothesis is preserved below as historical context;
the OPTIONS A/B/C did not survive Rule-0.

ORIGINAL HYPOTHESIS (now falsified):

A) Append-only JSONL at WRF_DD_LOG path, one event per line:
    {"timestamp": "2026-05-08T13:00:00Z", "event": "tier_change",
     "from": "C0", "to": "C2", "reason": "rolling_pnl_lt_p5_floor"}

B) Structured log via Python logging:
    2026-05-08 13:00:00 INFO dd_protection trigger=tier_change C0->C2

C) CLI with state-snapshot mode:
    python dd_protection.py --events --since 2026-05-04 --until 2026-05-08

Definition of 'event' assumed by the original handoff:
    Any tier change OR risk-multiplier change OR explicit FIRE-alert.
    Per existing dd_protection convention. (No such convention exists.)
"""
from __future__ import annotations

from datetime import date


def count_dd_events_for_week(log_path: str, week_start: date, week_end: date) -> int:
    """Count dd_protection trigger events in the inclusive week range.

    BLOCKED per handoff §8 (2026-05-09). See module docstring + WIRING_NOTES.md.
    """
    raise NotImplementedError(
        "BLOCKED per handoff §8: dd_protection.py is a state machine, not an "
        "event log. See weekly_review_feeder/WIRING_NOTES.md for the full "
        "structural finding and upstream follow-ups."
    )


def latest_dd_state(log_path: str) -> dict[str, object]:
    """Optional: return latest dd_protection state for the Pre-Market routine.

    Output: {tier, risk_multiplier, current_equity, peak_equity, current_dd_pct}
    Not strictly required by the Weekly Review feeder — present for symmetry
    with the Pre-Market Routine artifact.
    """
    raise NotImplementedError("Optional — wire if used by Pre-Market routine.")
