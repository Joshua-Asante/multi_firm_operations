# Q-CORR-2 pre-condition B — pyramid-active operational definition

**Date authored:** 2026-05-17
**Parent:** `2026-05-16-q-corr-2-pyramid-conditional-correlation.md` (§6 pre-condition B)
**Sibling:** `q-corr-2-precondition-a-report.md` (resolved A as A1 — empirical block bootstrap)
**Author:** parent session (claude.ai dispatched in Claude Code worktree)
**Status:** parameterization scoping note. NOT a Pre-Q, NOT an ADR, NOT a brief that prescribes action. Uncommitted for Joshua's review.

---

## §1 Context

The Notice §6 specifies two pre-conditions that gate the Notice→Pre-Q transition. Pre-condition A is resolved (sibling report: branch A1, empirical block bootstrap on union-aligned daily panel; joint structure inherited implicitly from realized historical co-movement, no parametric coupling). Pre-condition B remains open.

Per Notice §9 disposition table, **pre-condition B requires no production read** — it is a Pre-Q drafting choice. The Notice §6 carries four candidate definitions:

- **B1** — any day on which either strategy fired pyramid orders
- **B2** — any day on which both strategies fired pyramid orders
- **B3** — any day on which the pyramid stack reached ≥N pyramids deep on either side
- **B4** — continuous (correlation as a function of stack depth)

This note scopes the trade-offs and recommends a primary choice **so the Pre-Q author can draft against a fixed parameterization**. The recommendation is parent-session judgment; Joshua's override stands.

---

## §2 Candidate trade-offs (Notice §6 carried forward, with augmentation)

| Candidate | What it isolates | Subset size (qualitative) | Researcher DoF added | Falsifier directness |
|---|---|---|---|---|
| **B1** any-fire | Pyramid-period regime effect (broad) | Largest (union of two firing schedules) | None | Indirect — pyramid-period correlation, not pyramid-firing-coincidence |
| **B2** both-fire | The conjecture as stated (both stacking simultaneously) | Smallest (intersection of two firing schedules) | None | **Direct** — matches Notice §3 mechanism verbatim |
| **B3** depth-threshold | Amplified-size piece of the mechanism | Threshold-dependent | One free parameter (N) | Direct on the size dimension, but parameterized |
| **B4** continuous | Full conditional dependence as function of stack depth | All days, weighted | Implicit (functional form) | Most informative; most expensive |

The Notice §3 conjecture stated verbatim:
> *Pyramid-active days select for a subset of the panel where both strategies are most likely to be exposed in the same direction with amplified size, because pyramid firing in both strategies is conditional on continuation signal, and continuation signal in DJ30 and NAS100 is regime-driven by broad equity momentum.*

Two mechanism components: **(i) both-firing** and **(ii) amplified-size via stack depth**. B2 isolates (i). B3 and B4 add specificity on (ii). B1 brackets the whole pyramid-period without isolating either.

---

## §3 Primary recommendation: B2 (primary) + B1 (adjacent), B3/B4 deferred

**Run B2 and B1 as parallel cuts on the same panel.** The pair forms a 2×2 evidence table that disambiguates mechanism from regime:

| B2 elevated? | B1 elevated? | Reading |
|---|---|---|
| YES | YES | Both-fire stacking AND pyramid-period regime are real; mechanism + scope both present |
| YES | NO | Mechanism present but only when both fire simultaneously; unusual — investigate sampling artefact |
| NO | YES | Pyramid-period regime is real but coincident stacking is not the mechanism; reframe Pre-Q |
| NO | NO | Conjecture falsified; Notice closes WITHDRAWN |

**Why B2 primary, not B1 primary.** B1 is the data-richer option and tempting on N grounds, but B1's positive signal is mechanistically ambiguous (could be coincident stacking, could be broader regime, could be either strategy's solo pyramid-period). B2 is the operational form of the Notice §3 mechanism statement — running anything else as primary means the Pre-Q is testing a different question than the Notice opened.

**Why B1 adjacent, not deferred.** B1 is essentially free to compute once the panel is set up for B2 (same data, different mask). The adjacent cut adds the disambiguation table above at near-zero cost.

**Why B3 deferred.** B3 introduces a free parameter (N) at Pre-Q draft time. Researcher-degrees-of-freedom inflation is the documented risk pattern (Joshua memory: "Soften Pareto adoption criteria against MC sampling noise" + "Anchor sizing-rule effect on K-matched residual"). If B2 produces a positive signal, B3 becomes a follow-up Pre-Q with the threshold N chosen against B2's evidence — that ordering keeps the N choice principled.

**Why B4 deferred.** B4 is the most informative cut but requires per-day stack-depth time-series for both strategies, which is a richer data extraction than the daily P&L panel currently supports. Deferring to a follow-up Pre-Q (gated on B2 outcome) avoids paying the extraction cost before the question is shown to merit it.

---

## §4 Data-availability check

The branch-A1 panel (`build_daily_panel` at [portfolio_mc.py:151-172](portfolio_mc.py:151)) groups strategy P&L by `exit_date` and sums. The current panel is shape `(n_bdays, n_strats)` with one P&L number per strategy per business day. **Stack-depth and pyramid-firing flags are NOT carried into the panel as currently built.**

The TradingView strategy CSV exports (panel sources per CC report §4) carry per-trade rows. Pine v6 `strategy.entry()` calls typically use distinct `id` strings per pyramid layer (e.g., `"P0"` for base entry, `"P1"`, `"P2"`, ... for stack layers). If the locked DJ30 v4.5 and NAS100 v1 Pine scripts follow that convention, the per-trade CSV rows include an entry-ID column that distinguishes pyramid layers from base entries.

**HIGH-confidence prediction (not verified in this note):** the data exists in the source CSVs. Verification step at Pre-Q draft time:

```powershell
# Inspect Striker DJ30 v4.5 panel CSV for pyramid-distinguishing column
Get-Content "data\tv_exports\pepperstone\Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv" -Head 5
# Same for NAS100 v1
Get-Content "data\tv_exports\pepperstone\Striker_NAS100_v1_PEPPERSTONE_NAS100_2026-05-05_7ca6f.csv" -Head 5
```

If the CSV has a column like `Signal`, `Trade #`, or a labeled `id`, the B2 mask (both strategies fired ≥1 pyramid on the same business day) is a one-pass groupby+intersect on the per-trade frames before they get collapsed into the daily panel.

**Implication for cost:** B2 + B1 are cheap once an extension to `build_daily_panel` (or a sibling loader) produces a `pyramid_fired` flag column per strategy per business day. B3 and B4 require carrying stack depth — same cost shape but the loader change is slightly bigger. None of this is in-scope for this note.

---

## §5 Explicit non-claims (handoff §5 mirror)

This note does NOT:

1. **Compute conditional correlations.** Pre-Q work. The 2×2 disambiguation table in §3 names the evidence shapes, not the numbers.
2. **Propose Pre-Q falsifier Δ thresholds.** The materiality threshold for "corr(B2 subset) − corr(unconditional)" is the Pre-Q's central design decision and depends on the MC's joint-tail sensitivity (which itself is a re-MC question Joshua may or may not authorize).
3. **Propose subset N-floors or significance gates.** "What N below which the B2 subset is too small to test" is a Pre-Q-time decision informed by the actual intersection size at panel-load time. Picking N before the data is loaded encodes the conclusion (small N → "not enough data" → no test).
4. **Propose MC re-runs or sensitivity analyses.** The Pre-Q's gate decides what re-MC, if any, follows from a positive B2 signal.
5. **Pick a Notice-to-Pre-Q transition date.** That is Joshua's pacing decision based on competing priorities (CLAUDE.md notes 2026-05-08 anchor is current canonical; nothing on-deck forces Q-CORR-2 ahead).
6. **Edit the parent Notice.** Notice §6 update is parent-session work in Phase E, only after both A and B notes are accepted.

---

## §6 Recommendation summary

| Item | Recommendation |
|---|---|
| Primary B definition | **B2** (both strategies fired pyramid on the same business day) |
| Adjacent cut | **B1** (either strategy fired pyramid) — runs on same panel, near-zero marginal cost |
| Deferred to follow-up Pre-Q | B3 (stack-depth threshold N), B4 (continuous over stack depth) |
| Data extraction effort | Low — extend `build_daily_panel` (or sibling loader) with `pyramid_fired` boolean column per strategy. Verify CSV column at Pre-Q draft time per §4. |
| Researcher-DoF added | None (B2 + B1 are mechanically defined; no free parameters) |
| What this unblocks | Pre-Q drafting — both pre-conditions resolved, falsifier shape (per A1 from sibling report) is `corr(B2 subset) − corr(unconditional)` with Δ threshold set at Pre-Q time |

---

## §7 Audit hooks

- `grep -n "pre-condition B" docs/briefs/notice/2026-05-16-q-corr-2-precondition-b-note.md` → ≥1 hit (this section + §1)
- `grep -n "B2" docs/briefs/notice/2026-05-16-q-corr-2-precondition-b-note.md` → ≥4 hits (recommendation references)
- After Joshua accepts: `git log --oneline -- docs/briefs/notice/2026-05-16-q-corr-2-precondition-b-note.md` shows the commit landing this file
- After Phase E commit: `grep -n "pre-condition B" docs/briefs/notice/2026-05-16-q-corr-2-pyramid-conditional-correlation.md` shows Notice §6 updated to reference this note

---

## §8 Disposition

| Item | Status |
|---|---|
| Pre-condition B candidate trade-offs scoped | DONE |
| Primary + adjacent recommendation made (B2 + B1) | DONE |
| Data-availability check performed | DONE (HIGH-confidence prediction; explicit verification step at Pre-Q time) |
| Forbidden-move discipline applied | DONE (§5 explicit; no falsifier threshold, no MC re-run, no Pre-Q decisions) |
| Joshua review | PENDING |
| Notice §6 pre-condition B updated to RESOLVED | PENDING (Phase E, only after Joshua accepts) |

End of note.
