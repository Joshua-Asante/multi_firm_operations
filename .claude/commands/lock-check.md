---
description: Run the doc/code skew checker (verify_lock_anchors.py) and report Closed / Action / Forward routing.
---

Run `python scripts/verify_lock_anchors.py` from the repo root. Surface the route
(Closed / Action / Forward) and any drift or re-MC trigger lines verbatim.

Per `docs/methodology/observation_routing.md`:
- **Closed** — all CLAUDE.md anchors agree with `firm_rules.py` and `dd_protection.py`. Logged as a 0-day skew window per Rule 6 fallback.
- **Action** — drift between doc and code. The script prints a unified diff for the user to apply manually. Do NOT call `git apply`.
- **Forward** — re-MC trigger fired (allocation outside Guardian 0.30-0.34% safe band, or any `dd_protection` constant change). The script prints the suggested re-MC invocation; do NOT auto-run.

Surface the audit log path so the user can inspect `analysis/skew_audit/<date>.md` if they want.
