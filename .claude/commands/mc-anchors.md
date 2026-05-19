---
description: Reformat latest portfolio_mc output as the CLAUDE.md MC anchor block, diff against current
allowed-tools: Bash(python -m portfolio_mc:*), Bash(python portfolio_mc.py:*), Read, Grep
---

Steps:

1. **Run** `python -m portfolio_mc` (fall back to `python portfolio_mc.py` if the module form fails). Capture full stdout.
2. **Extract** the headline numbers from the output:
   - pass-rate %
   - bust % (broken into daily + static)
   - timeout %
   - p99 DD %
   - median days-to-pass
3. **Format** the anchor block to match the existing CLAUDE.md "Protection" section line style:

   ```
   * MC at current 4-strategy config (G 0.34% / DJ30 v4.5 1.00% / A 1.50% / NAS v1 0.40%, dd_protection C2 1.5%/0.40×, Pepperstone <vintage>, <N> week-blocks, 10K × 3 seeds):
     **XX.XX% pass / X.XX% bust (X.XX% daily + X.XX% static) / X.XX% timeout**, p99 DD X.XX%, median days-to-pass XX.
   ```

4. **Diff** the formatted block against the current "MC at current 4-strategy config" line in CLAUDE.md.
5. **Output** the proposed replacement as a unified diff. Do NOT auto-apply.
6. If diff is empty: report "MC anchors current — no update needed."

Note: also check the "Strategy Reference" section's latest panel-refresh MC anchor block — the headline MC line there mirrors the Protection block headline.
