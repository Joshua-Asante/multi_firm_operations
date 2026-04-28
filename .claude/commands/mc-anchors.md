---
description: Render the latest portfolio_mc output as a CLAUDE.md "MC at current config" anchor block, diffed against the current CLAUDE.md.
---

Generate the paste-ready markdown block that goes into the **Protection** section of `CLAUDE.md` after a re-MC, then diff it against the current CLAUDE.md anchors.

Workflow:
1. Locate the latest `portfolio_mc` output. Check, in order:
   - `analysis/portfolio_mc_*.json` (most recent by mtime)
   - The user's most recent terminal output if no file is cached (ask the user to paste the run summary).
2. Extract the headline numbers: pass %, bust % (and the daily/static split), timeout %, p99 DD, median days-to-pass, panel description (broker, date range, week-block count, seed count).
3. Render the block exactly in the shape currently used at `CLAUDE.md:67-69`:

```
* MC at current config (G <g>% / S <s>% / A <a>%, <broker> <start>->\n  <end>, <N> week-blocks, <K>K x <seeds> seeds):\n  **<pass>% pass / <bust>% bust (<daily>% daily + <static>% static) / <timeout>% timeout**, p99 DD <p99>%, median days-to-pass <days>.
```

4. Read the current `CLAUDE.md`, locate the existing "MC at current config" line, and produce a unified diff (using `python -c "import difflib; ..."` or just rendering the before/after manually).
5. Surface the diff for the user to apply manually with `git apply` or by direct edit. Do NOT modify CLAUDE.md automatically.

Per Rule 0 / Rule 6: any change to CLAUDE.md MC anchors must be paired with the underlying lock-decision update, never written from numbers in isolation.
