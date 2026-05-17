# Notice-phase log — Q-CORR-2: pyramid-active conditional correlation (DJ30 × NAS100)

**Date opened:** 2026-05-16
**Phase:** Notice (pre-hypothesis; pre-Pre-Q)
**Q-code candidate:** Q-CORR-2 (sibling to closed Q-CORR-1 series)
**Author:** claude.ai (advisor); to be ratified by Joshua (CEO)
**Status:** OPEN — Notice. Transitions to Inquire only after §6 pre-conditions met.

---

## §1 Context

The Q-CORR-1 programme closed 2026-05-14 with Guardian-family-on-XAGUSD rejected, but its load-bearing belt finding survived independently: **instrument-level correlation is not a reliable proxy for strategy-level correlation.** That finding was generalized from a NAS100/DJ30 strategy-level decorrelation observation despite tight instrument-level correlation.

This Notice formalizes a one-layer-down extension of that finding. The DJ30 and NAS100 strategy locks each have pyramid components that contribute a material share of P&L (DJ30 ~42.7%; NAS100 v1 ~88.5%). The portfolio MC currently produces a 99.88 / 0.12 / 4.21 anchor (pass / bust / p99DD) under the 2026-05-15 FXIFY-correct lock. The question this Notice opens: **does strategy-level decorrelation between DJ30 and NAS100 survive conditioning on pyramid-active state?**

If conditional correlation under pyramid-active state is materially higher than unconditional correlation, the MC's joint-tail estimate is structurally optimistic and the 4.21 p99DD claim has an unmodeled wing. This would propagate into both the dd_protection safety story and any forward sizing decision.

The Notice is being opened in the orthodox INQHIORI sequence (Notice → Pre-Q → Inquire) rather than skipping straight to Pre-Q. The motivation is the 2026-05-14 Programme Audit closure on Guardian Silver, which found premature Inquire-phase entry on hints that hadn't been properly Noticed. Even when the mechanism feels obvious, the Notice step is cheap insurance against the same failure mode.

---

## §2 Observation (the phenomenon)

Three load-bearing facts, none of them new:

- **F1 — Pyramid contribution.** DJ30 v4.5: pyramid contributes ~42.7% of P&L (corrected figure; previously mis-propagated as ~94%). NAS100 v1: pyramid contributes 88.5% of P&L. Both are above the threshold where pyramid mechanics are load-bearing for the strategy's risk profile.

- **F2 — Pyramid trigger.** Both strategies stack additional fire on continuation signal after the base entry. Continuation in DJ30 and NAS100 is not stochastic across instruments — both indices select for broad equity-momentum regimes when they continue.

- **F3 — Q-CORR-1 belt finding.** Strategy-level correlation can diverge from instrument-level correlation. This was observed for NAS100/DJ30 unconditionally. The conditional-on-pyramid-active subset has not been examined.

**No phenomenon has been measured yet.** This is a structural suspicion derived from mechanism, not from data. That is what Notice-phase is for.

---

## §3 Mechanism candidate

The conjecture, stated as a non-falsifiable mechanism (Pre-Q phase will sharpen it into a falsifier):

> *Pyramid-active days select for a subset of the panel where both strategies are most likely to be exposed in the same direction with amplified size, because pyramid firing in both strategies is conditional on continuation signal, and continuation signal in DJ30 and NAS100 is regime-driven by broad equity momentum.*

Two ways this could fail to bite:
1. Pyramid firings in DJ30 and NAS100 are temporally separated enough (different sessions, different DoW filters, different lookback windows) that their pyramid-active days don't overlap.
2. The strategy-level decorrelation observed unconditionally is robust *through* the pyramid-active subset — i.e., even when both strategies are stacking, their P&L correlation stays low.

Either failure mode invalidates the conjecture cleanly. That is the shape of a falsifiable Inquire-phase question waiting to be authored.

---

## §4 Cross-reference to forward asymmetry observation

Memory entry #15 (forward asymmetry observation, 2026-05-15): live execution Apr 13–May 14 realized −$1,673 vs counterfactual $7K–$20K. The framing in that entry is **execution-discipline leakage**, with marginal-hour return placed decisively in execution-discipline work rather than portfolio optimization.

Q-CORR-2 partially competes with that framing. **If** pyramid-conditional joint correlation is materially elevated, then "live underperformance vs counterfactual" has a methodology component (MC optimistic on joint tail), not only an execution component. This does not invalidate the execution-leakage finding — it would mean both are real and the leakage figure is being measured against a counterfactual that is itself overstated.

The Notice flags this competition but does not adjudicate it. If Q-CORR-2 closes with a null result, the forward-asymmetry framing is unaffected. If it closes with a positive finding, the counterfactual side of the forward asymmetry needs re-calibration.

---

## §5 What is NOT being claimed here

To prevent Notice→Inquire drift:

- **Not claimed:** that the MC anchor is wrong. The 99.88 / 0.12 / 4.21 figures stand unless Inquire-phase produces evidence.
- **Not claimed:** that pyramid mechanics should be revised. The DJ30 v4.5 and NAS100 v1 locks are not under review.
- **Not claimed:** that dd_protection C2 is mis-calibrated. The 1.5% / 0.40× settings stand unless Inquire-phase produces evidence.
- **Not claimed:** that the asymmetric pyramid parameters (DJ30 500% vs NAS100 1000%) are themselves suspect. That is candidate shape #3 from the framing discussion and was deferred.

Notice phase observes; it does not propose action. Forbidden moves at this layer are any code change, any allocation change, any methodology amendment.

---

## §6 Pre-conditions for transition to Inquire (Pre-Q draft)

This Notice transitions to Pre-Q when **both** of the following are resolved:

**Pre-condition A — Rule 0 on MC correlation assumption.** A specific path/function in the `portfolio_mc` module is identified, read, and its joint-day sampling assumption is named in writing. Three possibilities (re-stated from chat):
- A1: empirical unconditional correlation from the panel
- A2: zero correlation / independence
- A3: parametric copula or stress-correlation assumption

The Pre-Q's falsifier threshold depends on which is true:
- Under A1, the test is `corr(pyramid-active subset) − corr(unconditional)` with a Δ threshold to be set.
- Under A2, the test is `corr(pyramid-active subset)` against a zero null with a materiality threshold to be set.
- Under A3, the test is empirical conditional vs the stress assumption, with the gate depending on which direction the assumption errs.

Pre-Q cannot be authored honestly without this. The CC handoff or your direct read closes this gap.

**Pre-condition B — pyramid-active definition operationalized.** "Pyramid-active" must be specified precisely enough to subset the panel. Candidate definitions, all defensible:
- B1: any day on which either strategy fired pyramid orders
- B2: any day on which both strategies fired pyramid orders
- B3: any day on which the pyramid stack reached ≥N pyramids deep on either side
- B4: continuous (correlation as a function of stack depth)

B2 is the strongest test of the conjecture as stated. B1 is the weakest but most data-rich. B4 is most informative but most expensive. Pre-Q picks one as primary and may carry the others as sensitivity.

Once both pre-conditions are resolved, this Notice can be closed (transitioning to Pre-Q) or held open (if pre-conditions resolve in a way that suggests the question is not worth pursuing — e.g., A2/B2 with negligible pyramid-day overlap).

---

## §7 Audit hooks (mechanical)

- `grep -r "Q-CORR-2" docs/` — confirms Notice is filed in repo (currently zero hits expected; should be one after this commit)
- `grep -r "Q-CORR-2" notion-export/` — confirms Command Center awareness once Notion entry created
- File path expected after commit: `docs/briefs/notice/2026-05-16-q-corr-2-pyramid-conditional-correlation.md`
- STATE.md open-questions row expected: one line referencing this Notice and the two pre-conditions

If audit fires (in 2–3 weeks per the forward-asymmetry observation clock) and either:
- both pre-conditions resolved but Pre-Q not drafted → flag as Notice-stuck, transition or close
- both pre-conditions still open → flag as drift; ratify hold or close as deferred

---

## §8 Cross-system implications (informational)

- **STATE.md:** needs an open-questions row referencing this Notice. The pyramid-load-bearing facts (memory entries on DJ30 ~42.7% and NAS100 88.5%) should now point at Q-CORR-2 as the relevant open question rather than sitting as orphan findings.
- **Methodology Canon (Notion):** no change yet; Q-CORR-2 entered to Open Questions section when transitioned to Pre-Q.
- **Lesson registry:** no entry yet; Notice-phase observations do not become lessons until they close.
- **dd_protection ADR:** no change yet; would be revisited only if Inquire-phase closes with a positive finding.
- **Forward asymmetry observation (#15):** flagged in §4 as competing framing. Re-examine on the same 2–3 week cadence.

---

## §9 Disposition summary

| Item | Status |
|---|---|
| Q-CORR-2 Notice filed | YES (this document) |
| Pre-Q drafted | NO (gated on §6 pre-conditions) |
| Inquire phase opened | NO |
| Production read on MC correlation | PENDING (CC handoff or direct) |
| STATE.md open-questions row | PENDING (this commit) |
| Notion Command Center entry | DEFERRED (until Pre-Q) |

**Next action (owner: Joshua):** decide whether to resolve §6 pre-condition A via direct read or via CC handoff. Pre-condition B requires no production read — it's a Pre-Q drafting choice and can be made at Pre-Q time.

---

## §10 Closure conditions

This Notice closes (one of):
- **TRANSITION:** §6 pre-conditions resolved → Pre-Q drafted → Inquire phase opened → Notice marked CLOSED-TRANSITIONED.
- **WITHDRAWN:** §6 pre-conditions resolve in a way that demonstrates the question is not worth pursuing (e.g., negligible pyramid-day overlap). Notice marked CLOSED-WITHDRAWN with stated rationale.
- **STALE:** 90 days elapse without §6 pre-conditions resolving. Force a decision: transition, withdraw, or explicitly defer with new clock.

No other closure routes admissible.
