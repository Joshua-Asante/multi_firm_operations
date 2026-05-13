# ADR: Objective Map spec §4 — tighten falsifier thresholds

**Date:** 2026-05-11
**Status:** Proposed (operational tightening adopted in Notion 2026-05-11; spec amendment pending review)
**Scope:** `docs/spec/objective_map/objective_map_spec.md` (§4 falsifier definition), Y2-O2 Notion Objective, Calibration Scores DB downstream test logic
**Supersedes:** None — first amendment to spec §4 since LOCK 2026-05-10

## Context

The Objective Map spec at ac7afa9 (LOCKED 2026-05-10 with §12 UX addendum) defines the load-bearing falsifier in §4 as a three-condition conjunction evaluated at end of Q8 (2026-10-19):

> (a) **Calibration is learning.** For at least 60% of tracked metrics in the Registry, the calibration score at end of Q8 is BETTER than at end of Q7.
> (b) **Forecast gap drives revision.** At least one Plan revision OR Conditions Event with `forced refresh = true` per quarter is traceable to a Forecast↔Objective gap signal.
> (c) **Review cadence holds.** ≥80% Weekly close in Q7+Q8 (~26 weeks), ≥80% Monthly, 2/2 Quarterly.

During the Cycle/Year-level Objective Map authoring session 2026-05-11, an inconsistency audit surfaced a statistical-power concern on §4(a):

- Q7 close 2026-07-19 ≈ **10 weeks of observation data** (system built 2026-05-10, observations start ~W19)
- Q8 close 2026-10-19 ≈ **22 weeks of cumulative observation data** (per metric, less)
- Per-metric N typically <12 in Q7 and <12 in Q8 across the 32-active-metric Registry
- Calibration score variance dominates the "learning" signal at these sample sizes

The §4(a) test as specified ≈ a coin flip: noise-driven improvements register as "learning" (false positive), and real learning gets masked by small-N variance (false negative). The falsifier is load-bearing per spec §1 — its statistical underpowering converts the whole methodology layer's load-bearing test into a ceremonial check.

A second, narrower concern emerged on §4(c) cadence-window scope as Y2-O2 was being authored. Y2-O2 initially extended the cadence test from "Q7+Q8 only" (per spec §4(c)) to "through Y2 close (2027-01-19)" — adding ~13 weeks of cadence-gate beyond what the spec requires. This created an unintentional second, stricter test of cadence beyond the spec falsifier window, violating the locked spec's scope.

## Decision

Tighten §4(a) thresholds operationally as follows (formal spec amendment pending):

1. **Threshold raised: ≥60% → ≥70%** of metrics in the Registry must improve calibration score Q7→Q8.
2. **N≥8 inclusion filter:** metrics with fewer than 8 observations per evaluation period are excluded from the test population (treated as "insufficient evidence" rather than "improved" or "declined").
3. **§4(c) cadence-window scope re-affirmed:** Q7+Q8 window only. Y2 close is NOT a §4-mandated cadence checkpoint.

The Y2-O2 Notion Objective (URL: `35ddc0b53c1181c1b685e19216881629`) was authored 2026-05-11 with these tightened thresholds in its Description and Notes, implementing the operational version ahead of formal spec amendment.

### Acceptance criteria for ADR closure
- §4(a) test runs at Q8 close using the tightened thresholds (≥70%, N≥8 filter)
- §4(c) cadence test runs against the Q7+Q8 window only, not extended
- Y2-O2 status at Q8 close reflects the tightened-threshold result
- A successor spec revision (objective_map_spec.md v2) incorporates these changes formally before the next cycle's falsifier evaluation (Q12 close 2027-10-19)

## Alternatives considered

- **Defer thresholds to next spec revision.** Keep operational tightening only in Y2-O2's Description; leave the spec untouched until Q8 closes. **Rejected:** the spec is the canonical source of the falsifier definition; a Notion-side override without ADR creates source-of-truth ambiguity. ADR documents the deviation explicitly.

- **Tighten further to ≥75% + N≥10.** Maximally rigorous. **Rejected:** at ~12-observation-per-period maximum, N≥10 would exclude most metrics from the test entirely, leaving the test population so thin that the threshold itself becomes meaningless. ≥70% + N≥8 keeps a meaningful test population (~10–15 of 32 metrics will likely qualify) while reducing noise.

- **Extend the comparison window: Q6→Q8 instead of Q7→Q8.** Adds ~10 weeks of Q6 baseline data. **Rejected at this ADR:** the spec defines Q7→Q8 explicitly; widening the comparison window is a bigger spec change than threshold tightening and merits its own ADR if pursued. Flag for future consideration.

- **Replace §4(a) with a different test (e.g., Bayesian model comparison on prior vs posterior).** Theoretically stronger but requires non-trivial Python infrastructure (per Q-OM-2). **Rejected at this ADR:** out of scope; revisit if Q-OM-2 elevates to Python implementation post-Q7.

- **Accept the underpowering and let the spec falsifier be a "no-egregious-failure" check rather than a learning test.** Lowest-effort path. **Rejected:** spec §4 is the load-bearing falsifier per §1; downgrading its semantic load implicitly downgrades the methodology layer's load-bearing claim.

## Consequences

Positive:
- §4(a) test becomes statistically meaningful rather than a coin flip at small-N regime
- N≥8 filter formalizes the "insufficient evidence" verdict for metrics with thin observation pipelines, preventing them from contributing noise to the learning signal
- §4(c) cadence-window scope is re-affirmed (no second, stricter cadence test smuggled in via Y2-O2)
- Source-of-truth ambiguity between locked spec and Y2-O2 operational implementation is resolved via this ADR

Negative / watched:
- **Locked spec at ac7afa9 retains original thresholds** until formal v2 spec revision lands. Any external reader of the locked spec sees ≥60%, no N filter, through-Y2-close cadence; this ADR is the canonical override notice.
- **Tightening might cause Y2-O2 to FALSIFY at Q8 even if original spec would have PASSED.** This is the intended direction of the tightening — stricter test, higher bar — but means the falsifier branch (strip-to-journal per spec §6) becomes meaningfully more likely. If Y2-O2 falsifies under tightened thresholds but would have passed under spec thresholds, document explicitly at Q8 close review.
- **Test-population size depends on observation pipeline reliability.** With N≥8 filter, the §4(a) test population can shrink if observation cadence is poor in Q7. If test population drops below ~5 metrics, the percentage threshold (≥70%) becomes statistically meaningless on a different axis. Audit hook needed at Q7 close: count metrics that will qualify for §4(a) inclusion; if <5, flag for re-evaluation.

### Forward audit hooks
- **Q7 close (2026-07-19):** count metrics with N≥8 observations in Q7. If <5, raise concern; consider extending the window or relaxing the N filter for Q8 specifically.
- **Q8 close (2026-10-19):** run §4(a) with tightened thresholds. Document both tightened-threshold result AND original-spec-threshold result for forensic comparison.
- **Pre-Q12 (target 2027-10-19):** author objective_map_spec.md v2 formalizing these thresholds. Either commit alongside this ADR's "Accepted" status flip, or supersede this ADR if thresholds change again before Q12.

## Cross-references

- Parent spec: `docs/spec/objective_map/objective_map_spec.md` (LOCKED 2026-05-10 at ac7afa9)
- Companion brief: `docs/spec/objective_map/metrics_registry_seed.md` (LOCKED 2026-05-10 §11 at ac7afa9)
- Build log: `docs/spec/objective_map/build_log.md` (DONE_WITH_CONCERNS at 4f3f913)
- Y2-O2 Notion Objective: `https://www.notion.so/35ddc0b53c1181c1b685e19216881629`
- Cycle Objective Notion: `https://www.notion.so/35ddc0b53c11815189cdfe5b24eabc60`
- Open question deferred: window-extension to Q6→Q8 comparison (future ADR if pursued)
