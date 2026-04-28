#!/usr/bin/env python3
"""
lock_event_hook — Claude Code PostToolUse hook for lock-event detection.

Triggers per Rule 6 (`docs/operational_rules.md`): the audit fires on the
**lock event itself**, not on every edit. Lock events are characterized by
changes to numeric constants on locked-allocation / dd_protection lines OR
to strategy version strings.

Hook protocol:
- Reads tool-call JSON from stdin (Claude Code hook input).
- If the touched file is firm_rules.py or dd_protection.py AND the working-tree
  diff against HEAD includes a locked-constant or version-string change,
  shell out to scripts/verify_lock_anchors.py.
- Otherwise: silent no-op.
- Always exits 0. Never blocks the edit (moderate posture).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCKED_FILES = {"firm_rules.py", "dd_protection.py"}

# Lines that, if added or removed, indicate a lock event.
LOCK_LINE_PATTERNS = [
    re.compile(r"^[+-].*\b(?:DD_TRIGGER|DD_SCALE)\b\s*="),
    re.compile(r'^[+-].*"(?:guardian|striker|aegis|Guardian|Striker|Aegis)"\s*:\s*[0-9.]+'),
    re.compile(r"^[+-].*\bv[0-9]+\.[0-9]+\b"),
]


def _read_hook_input() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _touched_file(payload: dict) -> str | None:
    tool_input = payload.get("tool_input") or {}
    fp = tool_input.get("file_path")
    if not fp:
        return None
    name = Path(fp).name
    return name if name in LOCKED_FILES else None


def _diff_has_lock_change(filename: str) -> bool:
    """Return True if `git diff HEAD -- <file>` contains a locked-constant or
    version-string +/- line. Falls back to False if git is unavailable.
    """
    target = REPO_ROOT / filename
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD", "--", str(target)],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    if result.returncode != 0:
        return False
    for line in result.stdout.splitlines():
        for pat in LOCK_LINE_PATTERNS:
            if pat.match(line):
                return True
    return False


def main() -> int:
    payload = _read_hook_input()
    filename = _touched_file(payload)
    if not filename:
        return 0
    if not _diff_has_lock_change(filename):
        return 0

    verify = REPO_ROOT / "scripts" / "verify_lock_anchors.py"
    if not verify.exists():
        return 0
    try:
        subprocess.run(
            [sys.executable, str(verify)],
            cwd=str(REPO_ROOT),
            timeout=30,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
