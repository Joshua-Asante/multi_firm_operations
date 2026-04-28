---
description: Generate a per-decision skew-audit table for a given date window (Rule 6 Q8a format).
---

Build the per-decision audit table that `docs/operational_rules.md` Rule 6 Q8a
requires when a doc/code skew window is discovered retroactively.

Workflow:
1. Ask the user for the skew window (start commit / end commit, or a date range).
2. Run `git log --oneline <start>..<end>` to enumerate every commit in the window.
3. For each commit, identify what decision it embodies (commit subject + brief diff scan).
4. List the stale `Code:` pointers / version strings that existed during that window (the user provides this list, or it can be extracted from `docs/adr/` files at the window-start commit).
5. For each (commit, stale-pointer) cell, ask:
   a. Could this decision plausibly have consulted the stale pointer?
   b. Did it actually consult it? (Use `git show <commit>` to inspect the diff for references.)
   c. If yes: was the deprecated code logically equivalent at the relevant logic layer?

Render the table in the format used at `docs/operational_rules.md:111-124`:

| Commit  | Decision                                  | Stale pointer it could consult     | Consulted? | Equivalent at relevant logic? |
|---------|-------------------------------------------|------------------------------------|------------|-------------------------------|

Conclude with: total commits audited, count of "Yes consulted", count of "Yes consulted AND not equivalent" (the only category that requires action).

Output is paste-ready markdown for the operational_rules.md addendum or a new ADR. Do NOT modify any file automatically — surface the table for the user to commit themselves.
