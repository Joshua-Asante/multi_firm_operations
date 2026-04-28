---
description: Generate per-decision Q8a-style audit table for a doc/code skew window
allowed-tools: Bash(git log:*), Bash(git show:*), Bash(git diff:*), Read, Grep
---

Per Rule 6 in [docs/operational_rules.md](docs/operational_rules.md), Q8a section.

Steps:

1. **Identify the skew window.** Start = lock commit, end = fix commit. If the user did not provide bounds, ask which lock event this audit covers.
2. **List commits inside the window** via `git log --oneline <start>..<end>`.
3. **For each commit**, build a row:
   - SHA (short)
   - Decision (one short phrase: what the commit did)
   - Stale pointer it could plausibly consult (e.g., `aegis_v4.1.pine` ADR `Code:` line; "None" if none)
   - Consulted? (Yes / No / explanation)
   - Equivalent at relevant logic? (Yes / No / n/a)
4. **Render** as a markdown table matching the format in `operational_rules.md` lines 111-124.
5. **Close** the audit with either "zero corrupted decisions" or list the corrupted ones with the load-bearing logic that was wrong.

Output the table in chat. Do NOT write to any file. The user will paste it into the relevant ADR or operational_rules.md update if they want it persisted.
