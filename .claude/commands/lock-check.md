---
description: Run lock-anchor verifier; surface Closed/Action/Forward routing
allowed-tools: Bash(python scripts/verify_lock_anchors.py:*), Read
---

Run `python scripts/verify_lock_anchors.py` and report the result verbatim.

Then:

- If routing is **Closed**: confirm in one line. No further action.
- If routing is **Action**: list the drift lines. Propose CLAUDE.md edits as a unified diff for the user to apply manually. Do NOT run `git apply`. Do NOT auto-edit.
- If routing is **Forward**: state the re-MC trigger that fired. Suggest the user run `python -m portfolio_mc` (or `python portfolio_mc.py`) and update CLAUDE.md MC anchors after re-MC completes. Do NOT run portfolio_mc automatically.

Reference: routing semantics defined in [docs/methodology/observation_routing.md](docs/methodology/observation_routing.md).
