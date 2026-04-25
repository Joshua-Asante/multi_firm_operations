# Operational rules

Hard rules. No exceptions. Each rule is here because it was violated or nearly violated in the past and the correction was costly.

---

## 1. Never override a valid signal based on a macro volatility forecast

If the strategy fires a valid signal per its Pine code, take the trade. Do not skip it because of a scheduled macro event, a conflict headline, a Fed meeting, a BOJ decision, or any other forecast about what volatility might do.

**Origin:** Guardian fired a valid long during the Iran ceasefire announcement (entry 4653.26, 1:18.1 R:R). Trade was skipped on the reasoning that ceasefire-driven gold volatility was unpredictable. The trade subsequently moved in favor through breakeven. The skip had no basis in the system's measured edge — it was intuition dressed up as risk management.

**The overlay mechanism exists for this.** If a regime genuinely warrants reduced exposure, apply a risk overlay (see `docs/overlays/`). Do not improvise per-trade skips.

---

## 2. Audit production code before authoring risk-control briefs

Before writing any brief, ADR, or decision document that specifies risk-control parameters, read the current state of the code being discussed. Do not author proposals against remembered or assumed code state.

**Origin:** 2026-04-17 session. A dd_protection retune brief was authored against an assumed single-tier architecture. The actual code had a two-tier architecture with `min()` combination. Three decision iterations occurred in one session (retune → reverse → delete equity tier) because the first two iterations were arguing about code that didn't match reality.

**Workflow:** `view` the relevant file(s) before the first line of the brief. Not after. Not "I remember what it does." Before.

---

## 3. DXTrade `contractValue` for DJ30 MUST be 10

Default DXTrade `contractValue` is 1. At `contractValue=1`, Striker position sizing produces approximately **7% per-trade risk** against a 1% intended risk. This is catastrophic and silent — the platform will execute the trade without warning.

**Check:** Before any Striker trade on DXTrade, verify `contractValue=10` is set on the account symbol configuration.

**Origin:** Prop firm setup phase. Caught during Pine-to-platform parameter reconciliation. Would have been account-ending if missed.

---

## 4. Three or more consecutive losses on one strategy = normal variance

Do not adjust strategy parameters, reduce size, or skip signals in response to 3+ consecutive losses on a single strategy. This is within the normal variance distribution of every strategy in the portfolio.

**What to do instead:** Log the losing streak in the weekly review. Continue executing signals per the Pine code. Only consider intervention if ALL of the following hold:
- Losing streak exceeds 5yr backtest p99 for that strategy
- No identifiable regime shift explains it (e.g., conflict overlay applies)
- Weekly review shows systematic issue (e.g., execution slippage materially different from backtest)

**Origin:** The Algorithm (Delete before Optimize). Reactive parameter tuning during drawdown is the most common failure mode in systematic trading. Intervention during losing streaks has, historically, made things worse more often than better.

---

## 5. Pine file is the source of truth for strategy parameters

If the Pine file and any document (CHANGELOG, ADR, Notion page, README) disagree on a parameter value, the Pine file wins. Fix the document.

The only exceptions are:
- `dd_protection.py` parameters — those live in the Python pipeline, not in Pine
- `firm_rules.py` allocations — same
- Active overlays (e.g., Guardian conflict risk) — those modify risk at the sizing layer, documented in `docs/overlays/`

---

## 6. Doc/code skew audit fires on every version lock

When any strategy's locked version changes (e.g., Guardian v5.4 → v5.5), or
when any locked risk/allocation/`dd_protection` constant changes, immediately
run a doc/code skew audit before closing the lock commit. The audit checks:

1. **`CLAUDE.md`** — strategy table, Multiplier System risk numbers, Protection
   constants, MC anchor lines. Anything pointing to a strategy version or risk
   value must reflect the new lock or be explicitly marked as historical
   record.
2. **All ADRs in `docs/adr/`** — every `Code:` cross-reference line, every
   inline version mention. Stale `Code:` pointers are updated; conclusion
   text is left intact (ADRs are historical records of decisions made under
   the prior version) but a parenthetical is added noting what changed
   between the decision-era version and current.
3. **`docs/overlays/`** — same as ADRs.
4. **`docs/methodology/`** — same as ADRs, plus measurement values that quote
   "Guardian v<X> observed" must be either re-measured or marked as
   pre-version-bump archival.

**Audit trigger is the lock event itself**, not calendar. Calendar audits
(weekly, monthly) produce mostly no-ops between locks and miss the high-risk
zero-day-after-lock window. Per-commit-touching-`strategies/` is too aggressive
(routine code-only edits without locks fire false positives, and `strategies/`
may not even be tracked).

**Fallback**: if the audit cannot run inline with the lock (e.g., lock is
committed off-hours), fire it on the *next* repo-touch session and gate that
session on completing the audit before any new decision work. The skew window
must be measured and logged on every lock — even a 0-day window is a logged
0.

**Origin:** 2026-04-23 lock of Guardian v5.5 / Striker v4.4 / Aegis v4.3 (and
Guardian risk 0.30% → 0.34%) introduced a 2-day doc/code skew window
(2026-04-23 → 2026-04-25). Four ADRs and one overlay carried stale `Code:`
pointers to old Pine filenames (`guardian_v5.1.pine`, `striker_v4.3.pine`,
`aegis_v4.1.pine`); `CLAUDE.md`'s strategy table was missing the new versions
and the post-relock MC anchors. The skew was caught when OANDA backtest
filenames (`Guardian_Gold_v5.5_OANDA_XAUUSD_2026-04-25_9ae1f.csv`) forced a
comparison and refreshed in commit `cfea4a2` on 2026-04-25.

**Q8a audit result (per-decision verification, not asserted).** Every commit
inside the 2-day skew window (2026-04-23 21:00 lock through 2026-04-25 11:39
fix) audited against the four stale `Code:` pointers (`aegis_v4.1.pine`,
`guardian_v5.1.pine`, `striker_v4.3.pine`, and `portfolio-allocations.md`'s
`Status: Accepted` line). Each row records (i) which stale pointer the
decision could plausibly have consulted, (ii) whether it did, and (iii) if it
did, whether the deprecated code was logically equivalent at the relevant
logic for that decision.

| Commit  | Decision                                  | Stale pointer it could consult     | Consulted? | Equivalent at relevant logic? |
|---------|-------------------------------------------|------------------------------------|------------|-------------------------------|
| edd0f39 | MVD discipline (ADR + methodology + lib)  | All four ADR `Code:` lines         | No — explicitly wrote current versions ("Guardian Gold v5.5, Striker DJ30 v4.4, Aegis v4.3 ... grandfathered"; example references `strategies/aegis_v4_3.pine`) | n/a |
| c9f6ab9 | Aegis v4.3 MVD helper dry-run             | `aegis_v4.1.pine` ADR pointer      | No — file name itself is "Aegis v4.3", panel is v4.3 | n/a |
| 4312865 | MVD methodology Aegis path fix            | `aegis_v4.1.pine` ADR pointer      | No — fix moved path to match repo layout, version-agnostic | n/a |
| a0a47bd | MVD meta-example + CHANGELOG scope        | None                               | No — methodology framing only | n/a |
| 6844fd0 | MVD retrofit ADR                          | All four                           | No — explicitly wrote "Guardian v5.5, Striker v4.4, Aegis v4.3 still locked" | n/a |
| b7211e4 | `portfolio_mc.py` MVD retrofit (code)     | None — consumes CSVs not Pine      | No — code change at the runtime model layer | n/a |
| 2147b75 | `dd_protection.py` MVD retrofit (code)    | None — consumes CSVs not Pine      | No — code change at the runtime model layer | n/a |
| cfcb3f0 | Notice phase bar-data drill-down          | All four ADR `Code:` lines         | No — analysis ran on raw 15-min bars (XAU/US30/USDJPY), did not load or reference any Pine file; `portfolio_mc.build_week_blocks` referenced by line, no version pointer involved | n/a |
| a05e9f3 | 1R methodology update (Guardian v5.5)     | `guardian_v5.1.pine` ADR pointer   | No — this commit *was* the lagging-artefact update; it wrote v5.5 explicitly and dropped the prior v5.1 1.37% figure | n/a |
| cb6fdbe | CSV-tracking policy + OANDA backtests     | None                               | No — admin policy + data ingestion | n/a |
| d0e75de | Ignore `data/live/*.csv`                  | None                               | No — `.gitignore` change | n/a |

The audit closes with **zero corrupted decisions**. The skew was
`Code:`-pointer-only across four cross-reference lines and one ADR `Status`
line; no decision in the window depended on what those lines pointed to.

For completeness on the equivalence column: the parentheticals added in fix
commit `cfea4a2` document what changed between the decision-era version and
the current code (Aegis: session-selection unchanged through v4.3; Guardian:
v5.5 adds hour filters only; Striker: v4.4 retains the 350% pyramid and
tightens SL to 1.25 × ATR only). None of the decisions in the window touched
hour filters, SL multipliers, or session-selection logic — so even
counter-factually-if-followed, the stale pointer would have shown the same
load-bearing logic for each decision's purpose.

---

## Rule maintenance

New operational rules are added here only after a specific failure or near-miss. Do not add preemptive rules based on what might go wrong. Rules earn their place by being paid for.

Edits to existing rules must be logged with a dated entry explaining what changed and why. Rules do not silently drift.
