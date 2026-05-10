#!/usr/bin/env python3
"""H5 historical replay — Q-MCFP-1 §2.6.

Replays every recorded equity entry in `dd_protection_state.json` against
post-fix `calculate_protection`. Reports any firing-or-not flips between
recorded multiplier and replayed multiplier.

Usage:
    python scripts/replay_state_h5.py

Output: prints summary + per-flip JSON lines to stdout. Tee to
`docs/briefs/Q-MCFP-1/H5_replay_log.md` for the closure record.

Exit codes:
    0 — replay completed (zero or more flips logged)
    2 — state file missing or unparseable (BLOCKED per parent §2.6)
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = REPO_ROOT / "dd_protection_state.json"

sys.path.insert(0, str(REPO_ROOT))
from dd_protection import calculate_protection  # noqa: E402


def main() -> int:
    if not STATE_FILE.exists():
        print(f"BLOCKED: state file missing at {STATE_FILE}")
        print("  Either Joshua has not run `python dd_protection.py <equity>` yet")
        print("  (state created on first equity log), or the file lives elsewhere.")
        print("  H5 cannot resolve without the state file. Per parent section 2.6:")
        print("  'dd_protection_state.json missing or unparseable -> BLOCKED")
        print("   (context-problem; raise to parent for state recovery).'")
        return 2

    try:
        state = json.loads(STATE_FILE.read_text())
    except json.JSONDecodeError as e:
        print(f"BLOCKED: state file unparseable at {STATE_FILE}: {e}")
        return 2

    history = state.get("history", [])
    flips = []
    for entry in history:
        eq = entry.get("equity")
        peak = entry.get("peak")
        recorded_mult = entry.get("multiplier")
        if eq is None or peak is None or recorded_mult is None:
            continue
        new_result = calculate_protection(eq, peak)
        new_mult = new_result["multiplier"]
        recorded_fired = recorded_mult < 1.0
        new_fired = new_mult < 1.0
        if recorded_fired != new_fired:
            flips.append({
                "timestamp": entry.get("timestamp"),
                "equity": eq,
                "peak": peak,
                "dd_from_peak_logged": entry.get("dd_from_peak"),
                "dd_from_peak_replayed": new_result["dd_from_peak"],
                "recorded_mult": recorded_mult,
                "new_mult": new_mult,
                "direction": (
                    "recorded_fired_new_did_not"
                    if recorded_fired
                    else "new_fires_recorded_did_not"
                ),
            })

    print(f"total_entries: {len(history)}")
    print(f"flips: {len(flips)}")
    for f in flips:
        print(json.dumps(f))
    return 0


if __name__ == "__main__":
    sys.exit(main())
