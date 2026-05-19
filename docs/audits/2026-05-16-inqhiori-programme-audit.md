# 2026-05-16 INQHIORI programme audit — executable falsification tests proposal

**Programme:** INQHIORI (meta layer)
**Audit window:** 2026-04-01 through 2026-05-15 (~6 weeks of closed loops)
**Trigger:** Belt-patch proposal raised mid-session — formalizing executable falsification tests at the hypothesis-to-investigation gate.
**Layer:** Meta. Per two-layer rule, no portfolio P&L cited as evidence.
**Author:** claude.ai (Tech Advisor)
**Lock owner:** Joshua

## §1 Context

The proposal contained two gaps sharing a symptom but at different layers:

- **Gap 1** — code-level fixture tests for analysis scripts that produce investigation evidence. Engineering hygiene; not an INQHIORI modification.
- **Gap 2** — executable verdict assertions replacing textual §6 gates. True methodology proposal.

Pre-registered falsifier (Joshua, in-session): of the last ~6 closed loops, ≥3 of 6 would-have-benefited = load-bearing; ≤1 = belt-patch.

Cross-cutting concern: 2026-05-15 forward-asymmetry note (methodology refinement ~0.1pp scale; execution leakage ~50%). Methodology expansion is a degeneration risk under this priority unless the falsifier clears cleanly.

## §3 Seven diagnostic questions

**1. Hard core integrity — Preserved.** Falsifiable-H gating exists in textual form via brief-authoring §4 + §6. No specific past loop shows the textual form being violated under INQHIORI's name. Proposal asks whether to strengthen the gate, not whether to repair a breach.

**2. Belt churn balance — Yellow flag (net positive).** Adds in window: brief-authoring (2026-05-07), trade-csv-reconcile, live-execution-journal, programme-audit (2026-05-13 lock), CC-handoff hygiene rule (2026-05-15). Prunes: DJ30 methodology budget formally exhausted; rejected-candidates list as standing prune mechanism. Adding executable falsification tests would extend the streak.

**3. Progressive evidence — Strong.** Aegis EOM filter (predicted improvement, confirmed: PF 3.23 → 4.16, MaxDD 5.83% → 3.76%). Q-CORR-1.1 Guardian-Silver (predicted rejection, confirmed 2026-05-14). 2026-05-12 audit produced strategy-vs-instrument correlation finding as surplus content. DJ30 SNAG budget exhausted as pre-registered.

**4. Degeneration evidence — Load-bearing question for the proposal.** Walking the 6 most recent closed loops against the falsifier:

| Loop | Would-have-benefited? | Reasoning |
|---|---|---|
| Q-CORR-1.1 Guardian-Silver | Marginal | Mechanism-based rejection. Assertion mechanizes threshold portion; not the structural judgment. |
| Q-DJ30-1 macro-release | Marginal | Cleaner null comparison; verdict unchanged. |
| Q-DJ30-2 hard cap | **Yes** | Pre-committed criteria would have collapsed AMBIGUOUS into yes/no. |
| Q-DJ30-3 opening-gap | Marginal | Cleaner null; verdict unchanged. |
| Q-MT5-TV equivalence | **Yes (Gap 1) + Yes (Gap 2)** | JPY 153× defect caught by Gap 1 fixture test. Gap 2 mechanizes the equivalence comparison. |
| Aegis EOM filter | No | Improvement magnitude overwhelming; any threshold triggers promote. |

**Tally — Gap 2 only:** 2 clear yes, 3 marginal/no, 1 no. Below pre-registered 3-of-6 threshold.
**Tally — Gap 1:** 1 clear yes (Q-MT5-TV defect). Specific anchor sufficient for engineering hygiene.

**5. Boundary respected — Yes.** No instance of running INQHIORI without a falsifiable H in the window. The "boundary in name only" risk the proposal raises is structural, not evidenced.

**6. Theory-comparison performance — Insufficient data.** No specific tiebreaker-routed instance in the window where chosen-vs-unchosen counterfactual is evaluable.

**7. Falsifier check — Held.** DJ30 SNAG budget triggered and held per pre-reg §7. No drift evidence.

## §4 Verdicts

**INQHIORI itself:** **Progressive.** Continue.

**Gap 1 (code-level fixture tests):** **Adopt as engineering hygiene — not as INQHIORI modification.** Specific defect anchor (JPY 153× inflation, Q-MT5-TV) clears the falsifier on its own merits. Adoption codified in `docs/adr/2026-05-16-fixture-test-requirement.md` (Rule 0 sub-clause), not in INQHIORI SKILL.md.

**Gap 2 (executable verdict assertions in INQHIORI):** **Ambiguous, leaning rejected.** 2-of-6 sits between pre-registered load-bearing (≥3) and belt-patch (≤1) thresholds. AMBIGUOUS requires named re-test conditions per protocol §96.

**Re-test condition (Gap 2):** Of the next 4 closed INQHIORI loops (target window: through 2026-08-15), if ≥2 would have had different/cleaner verdicts from executable assertion — specifically, ambiguity resolved or interpretive slack caused a verdict mechanical computation would have inverted — reconsider. Target date: 2026-08-15 or next quarterly methodology audit, whichever first.

## §5 Spawned follow-ups

1. **`docs/adr/2026-05-16-fixture-test-requirement.md`.** Authored same day; locks Gap 1.
2. **TV/MT5 pilot.** `tv_mt5_pnl_reconciliation.py` + `tests/test_tv_mt5_pnl_reconciliation.py` landed 2026-05-16 (`8e2a2d6`). Establishes canonical pattern.
3. **Notice log for Gap 2.** Not yet authored. Re-test conditions and target date recorded above.
4. **INQHIORI SKILL.md edit — explicitly held.** No edit until Gap 2 re-test clears falsifier.
5. **Belt-churn watch flag.** Raised. If next methodology audit shows net-positive belt growth for INQHIORI specifically, escalate to red flag.

## §10 Audit hooks for next cycle (2026-08-15 or triggered)

```bash
# Hook A: Gap 2 re-test — count closed loops since this audit where executable
# assertion would have changed/cleaned the verdict.
# Manual review — no mechanical extraction. Update this file with tally.

# Hook B: belt churn for INQHIORI specifically.
git log --since='2026-05-16' --until='2026-08-15' --oneline -- 'skills/inqhiori/**' | wc -l

# Hook C: confirm INQHIORI SKILL.md was NOT edited to add executable-test language
# before Gap 2 re-test cleared.
git log --since='2026-05-16' --oneline -- skills/user/inqhiori/SKILL.md
```

## Discipline check

- [x] Seven diagnostic questions answered with evidence anchors
- [x] Belt churn counted (5+ adds, 1 explicit prune visible)
- [x] Falsifier check executed (DJ30 SNAG §7; user pre-reg threshold applied to proposal)
- [x] Cross-layer contamination check (no portfolio P&L cited)
- [x] Disposition verdict assigned with reasoning per programme
- [x] Ambiguous verdict has named re-test conditions and target date
- [x] §10 hooks runnable
