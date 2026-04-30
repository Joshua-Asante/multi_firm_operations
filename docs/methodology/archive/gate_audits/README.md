# Gate audit tally

Running record of pre-Q gate case classifications per question. Tracks Case A/B
base rates as a framework-health metric. **If Case B fires faster than question
complexity grows, that is a gate-sensitivity signal (gates miscalibrated), not
a question-difficulty signal.**

## Cases (current set)

- **Case A — clean.** D-tests permitted, S preserves N, A bounded, time budget
  within brief band. No audit file.
- **Case B — audit fires.** At least one halt rule fired or pre-spec was
  violated. Audit file in this directory documents the failure mode and what
  (if anything) it changed about the verdict. Case B is **not** automatically
  a verdict-blocking failure — methodology learning is one valid Case B mode.

No Case C defined as of 2026-04-25. Add a definition here if a future
iteration introduces one.

## Tally

| Date | Question | Case | Complexity tags | Audit slug | Notes |
|---|---|---|---|---|---|
| 2026-04-25 | Q1 — Guardian 1R reconciliation | A | iter-1, 0 partial-D's, single-tail | — | Clean. Gate effort ~5–8%. |
| 2026-04-25 | Q5 — break-window P&L falsification | A | iter-2, 2 partial-D's, single-tail, sensitivity-on-escalation | — | Clean. Gate effort ~10–15%. ESCALATE Q3. |
| 2026-04-25 | Q3 — pairwise correlation + symmetric joint-tail | B | iter-3, 3 partial-D's, dual-tail, sample-size asymmetry, halt-rule classification, direction-of-effect | `q3_halt_rules_design_skew` | Verdict reached cleanly; audit is methodology learning (brief's halt rules direction-blind on panel-split catcher; rare-event mean smallness on noise gate). |

## Reading the trend

Two ratios to watch as iterations accumulate:

1. **Case B rate vs iteration count.** Currently 1/3 ≈ 33%. With n=3 the rate
   is essentially uninformative — a single fire dominates. Re-evaluate at n≥6.
2. **Case B rate vs complexity-tag growth.** If the complexity-tags column
   keeps gaining new tags (more partial-D's, more tails, novel halt rules,
   multi-period, etc.) and Case A still holds, that is **healthy
   discrimination** — gates are catching the cases they were designed to
   catch and ignoring the ones they were not. If complexity tags stay flat
   but Case B starts firing repeatedly, that is **gate creep** — the rules
   are getting easier to trip without the underlying question getting harder.

The substrate for both ratios is this table; do not let it stagnate.

## Watchlist (active)

- **First-Case-B-at-iter-3.** Q3 is the first Case B. The audit
  (`q3_halt_rules_design_skew`) was triggered by halt rules the brief's v2.1
  patch round added. If iters 4–6 produce ≥2 more Case B's *without* a
  corresponding step-up in complexity tags, the v2.1 halt-rule additions
  are over-reactive and need to be dropped or rewritten with the patches in
  the audit's "Methodology learning" section.
- **Halt-rule design skew (per audit).** Three concrete patches proposed in
  `2026-04-25_q3_halt_rules_design_skew.md` §"Methodology learning": (i)
  panel-split halt should be conditional on direction; (ii) noise gate should
  consider direction-of-effect; (iii) halt rules should declare their
  failure modes. Brief authors for iters ≥4 should consult the audit before
  copying Q3's halt-rule pattern verbatim.

## Cross-references

- Framework: https://www.notion.so/34ddc0b53c1181479d7bdecc61f47078
- Skill: `inqhiori-algorithm/SKILL.md`
- Q1 close-out: https://www.notion.so/34ddc0b53c118101b26bfaf7c1f2173a
- Q5 close-out: https://www.notion.so/34edc0b53c118142a0c1fe26fac09179
- Q3 close-out: https://www.notion.so/34edc0b53c11819fa919cdf265a45490
