# ADR: Sentinel USDCHF H4 build/no-build gate — REJECTED

**Date:** 2026-05-03
**Status:** Accepted
**Scope:** No production code change. Records the gate verdict on a candidate
strategy that never reached build phase.
**Supersedes:** Sentinel v2.0 design intent (filed 2026-04-13, off-repo).

## Context

Sentinel was scoped 2026-04-13 as a short-only USDCHF safe-haven hedge. v1.0
required a realized-vol gate; backtest produced 44 trades / 4 yr (10× below
the parent brief's N≥80 floor). v2.0 design intent deleted the vol gate per
The Algorithm. Strategy never reached build phase. Iran/Hormuz overlay was
deactivated 2026-04-23, codifying "no regime overlays on physical facts" —
internally consistent with v2.0's vol-gate deletion.

This ADR records the build/no-build gate result authored 2026-05-03 to
answer: does Sentinel deserve to enter the portfolio at all, or is it
AUDNZD-shaped (statistically dead on the chosen rule × instrument × TF)?

## Decision

**Reject.** Sentinel (no-overlay short-Donchian on USDCHF H4) is not built.
The strategy operates on the existing locked corpus of three (Guardian
v5.5, Striker v4.4, Aegis v4.3). No fourth strategy is added.

## Gate result (parent brief §6 + §8)

| Criterion | Threshold | Measured | Pass? |
|---|---:|---:|:---:|
| (a) N | ≥ 80 | 84 | ✅ |
| (b) PF | ≥ 2.0 | **1.026** | ❌ |
| (c) max DD | < 3.0% | **4.252%** | ❌ |
| (d) permutation p | < 0.05 | **0.944** | ❌ |

Verdict: **H2_KILL** — entries indistinguishable from random within the
(session × weekday) candidate pool. Permutation null PF p50 = 1.076; observed
PF (1.026) sits *below* the null median.

Daily P&L correlation vs G/S/A all |r| < 0.07 (well below 0.30 park
threshold) — moot under the kill, but recorded for completeness.

Full numerical record:
[docs/methodology/findings/2026-05-03_usdchf_h4_sentinel_gate.md](../methodology/findings/2026-05-03_usdchf_h4_sentinel_gate.md).

## Alternatives considered

1. **Re-MC trigger (H1 path).** Not applicable. Gate failed; no fourth
   strategy to add, no re-MC required. Locked MC anchor (Pepperstone
   2022-01-04 → 2026-04-20, 92.73% pass / 0.65% bust / 4.94% p99 DD)
   stands.

2. **Park (H3 path).** Not applicable. H3 requires all four gate criteria
   to clear with corr-vs-A > 0.30. Three gate criteria failed; corr was
   far below threshold anyway.

3. **Re-spec at lower risk to clear (c).** Considered and rejected. Even at
   0.25% risk per trade, max DD scales linearly to 2.13% — clears (c) — but
   (b) and (d) are unaffected by sizing. No size produces a tradeable
   edge from a non-edge rule.

4. **Re-test with different SL/TP multiples.** Considered and rejected.
   Doing so without a fresh pre-Q gate is the parameter-retry failure mode
   AUDNZD's closure explicitly forbids ("rejected hypotheses stay rejected").
   The brief's parameters were literature-default and the gate's purpose
   was to falsify the *concept*, not to optimize within the concept.

5. **Filter to ATR-Q4 (post-hoc PF=2.231 in highest-vol quartile).**
   Considered and rejected as the explicitly-forbidden Pre-Q-D test "keep
   only trades that fit the CHF thesis" applied via vol filtering. Recorded
   as a forward observation in the finding, not as a rescue path.

## Consequences

- **Positive.** Time budget contained: ~1 Claude Code session (data import
  + harness + report + ADR), well under the parent brief's "≤10% of v2.0
  build effort" guardrail.
- **Positive.** Methodology consistency preserved: the no-overlay rule
  (codified 2026-04-23) is what made the v1.0 vol gate inadmissible and
  thus made the v2.0 question well-posed. Outcome confirms the v2.0
  design intent was correct as a methodological move (kept the answer
  honest), independent of the strategy's failure.
- **Neutral.** "Sentinel" name remains reserved. A different
  operationalization (different timeframe, different pair-correlation
  signal, different direction) would be a separate brief with its own
  pre-Q gate.
- **Neutral.** Bar panel
  `data/bar_data/USDCHF_pepperstone_h4_2020-06-25_to_2026-05-03.csv` stays
  in repo as audit-trail substrate; not migrated to operational pipeline.

## Forbidden-D-test audit

Throughout the gate execution:

- **Pre-Q gate (§3):** out-of-scope panels deleted (pre-2022-01-04, non-
  Pepperstone) at bar-loader window-slice. No "delete crisis windows" or
  "delete calm windows" tests applied.
- **Permutation null (§6):** mask is (session × weekday), preserving the
  Pre-Q-D scope; ATR-quartile is *not* in the mask, kept as post-hoc
  diagnostic per Q2 decision and Pre-Q-S contract.
- **Verdict (§8):** mechanically follows from §4 gate criteria. The Q4
  ATR PF=2.231 finding was *not* used to rescue the verdict — recorded as
  a forward observation only.

## Out of scope (confirmed unmoved)

- ❌ No Pine v6 implementation
- ❌ No portfolio Monte Carlo run (no candidate to add)
- ❌ No allocation change (G 0.34% / S 1.00% / A 1.50% remain locked)
- ❌ No dd_protection retuning
- ❌ No re-lock of v5.5 / v4.4 / v4.3
- ❌ No CLAUDE.md headline MC update
- ❌ No /loop or recurring task; this is a one-shot closure

## Re-open triggers (per parent brief §9)

This ADR is not re-opened by future losses on G/S/A or by changes in
portfolio composition. It is re-opened only if:

- A separate INQHIORI loop produces a *different* USDCHF operationalization
  (different rule × TF × direction) and its own pre-Q gate clears.
- The forward observation at §"Notice-routed observation" in the finding
  document fires — i.e., a structural/macro shift specifically named there.

Otherwise, **no follow-up loop, no parameter retry, no broader framework
search.**

## Cross-references

- Finding (technical record): [docs/methodology/findings/2026-05-03_usdchf_h4_sentinel_gate.md](../methodology/findings/2026-05-03_usdchf_h4_sentinel_gate.md)
- Parent brief: chat 2026-05-03 (Sentinel USDCHF build/no-build gate)
- AUDNZD precedent: [docs/methodology/archive/findings/2026-04-26_audnzd_REJECTED.md](../methodology/archive/findings/2026-04-26_audnzd_REJECTED.md)
- No-overlay rule (Iran/Hormuz deactivation): [docs/overlays/guardian_conflict_risk.md](../overlays/guardian_conflict_risk.md)
- Two-tier canonical (Pepperstone-anchored): user memory `feedback_two_tier_canonical_pepperstone_oanda.md`
