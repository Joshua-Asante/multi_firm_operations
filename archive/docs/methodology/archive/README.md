# Strategy-research-phase methodology — archived 2026-04-29

The methodology layer (INQHIORI ⊕ The Algorithm framework, Pre-Q gates, Case B audits, backfill discipline, mandatory header ordering, MVD framing) was load-bearing during the lock-three-strategies phase (Feb–Apr 2026). That phase delivered G v5.5 / S v4.4 / A v4.3 locked, MC Pepperstone-calibrated 2026-04-23, FXIFY $200K challenge live.

Operation has shifted to execution phase. Execution-phase failure modes (per-firm rule drift, copier latency, DD watch, payout cycle integrity, multi-firm lot sizing) are not addressed by these rules. Pre-building scaffolding against hypothesized execution failures was rejected as a methodology-rebound trap.

## What survived

[`docs/rule_0.md`](../../rule_0.md) — Rule 0 (audit-first). Cross-phase track record: 2026-04-17 (`dd_protection` misstatement), 2026-04-27 (Q-meta-a brief). The MVD principle folds in as Rule 0 corollary #4. Assertion library at `lib/mvd.py` stays live as execution infrastructure (multi-firm expansion makes it more load-bearing, not less).

Two methodology docs remain active outside this archive:

- [`docs/methodology/observation_routing.md`](../observation_routing.md) — three-bucket gate (Closed / Action / Forward).
- [`docs/methodology/1r_estimation.md`](../1r_estimation.md) — per-strategy 1R, equity-compounding normalization.

## What is here

### Methodology framing (archived)
- `mvd.md` — MVD methodology doc (5 families, audit table, worked examples).

### Notice/Inquire phase work
- `analysis/notice_phase/` — Notice-phase scans (2026-04-26 and 2026-04-27 OANDA-proxy bar-corpus runs, O1–O6 extractions, phase 0 logs).
- `analysis/inquire_phase/` — Q-T (Tuesday-cohort concurrent-loss) closed with watchlist tripwire.
- `analysis/archive/` — Q3 / Q5 / Q11 / Q12 / Q14 / Q15 closures, pre-locked bar-analysis, `1r_diagnosis.py` (codified into `1r_estimation.md`).
- `analysis/skew_audit/2026-04-27.md` — first and only Case B doc/code skew audit.
- `scripts/var_alloc_inquire/` — variable-allocation MC harness (verdict 4A REJECTED; var_alloc + dd-state observable bottlenecked).

### Identify-corpus work (research-phase loops)
- `identify_corpus/2026-04-26/` — OANDA-proxy bar-corpus (XAUUSD/US30/USDJPY 15m, 2022→2026), `AMENDMENT_oanda_rescope.md`, phase 0 logs.
- `identify_corpus/2026-04-27/` — Q-A Aegis panel-mechanism gated parent brief, backfilled 2026-04-29.
- `identify_corpus/2026-04-29/` — Q-A1 chain (panel-thirds → quintile → q5 drilldown), closed-loop verdict PARTIAL.

### Findings (4A REJECTED verdicts and source diagnostics)
- `findings/` — AUDNZD framework screen + structural characterization, `var_alloc_observables_stage0`, `var_alloc_dd_state_REJECTED`.
- `data_provenance/2026-04-26_audnzd_oanda_verification.md` — OANDA vs Pepperstone bar-data feed verification.

### Gate audits
- `gate_audits/2026-04-25_q3_halt_rules_design_skew.md` — first and only Case B audit.
- `gate_audits/README.md` — Case A/B tally.

### MSEE framework (research-phase ecology model)
- `msee/framework.md` — Market Storage-Effect Ecology framework.
- `msee/open_questions.md` — H1–H10 falsifiable hypotheses.
- `msee/watch_list.md` — Phase 8 early-warning signals (live tripwires read from this archived doc; live digests at `analysis/msee/watch_*.md`).
- `msee/findings/` — H1–H10 phase-specific test results.
- `analysis/msee/archive/` — H1–H10 individual hypothesis runs.

### Iran/Hormuz overlay (kept live, not archived)

The Iran/Hormuz conflict overlay was deactivated 2026-04-23 after revert triggers met. Historical record retained at [`docs/overlays/guardian_conflict_risk.md`](../../overlays/guardian_conflict_risk.md) — referenced from CLAUDE.md as the canonical overlay-discipline case (per memory `feedback_overlay_trigger_discipline.md`).

## Q-A1-d / Q-A1 chain status (at archive time)

- **Q-A1-d** — CLOSED 2026-04-29 (commit `2be984f`); parent brief backfilled.
- **Q-A1 chain** — closed-loop, verdict PARTIAL. Q15 monotonic-PF-lift framing dissolves under refinement; Conv B q5 PF=28.4 is denominator-driven (zero-loss accident, fragile). Routing: forward live-PnL tripwire on next Aegis full-SL hit. No allocation / `dd_protection` / calibration change.
- **Q-A (parent)** — REMAINS GATED on Pepperstone-canonical access. Resurrection rule below applies if Pepperstone re-verification ever fires.
- **Q-A2** — NOT escalated.

## Resurrection rule

Resurrect any individual rule only on concrete observed recurrence of its triggering failure during execution phase. Hypothesized recurrence does not qualify.

## Review gate

**2026-07-29** — review whether any new rule has been written since archive.
- If yes: evaluate against observed-failure standard. Apply the same Question step (Algorithm §1) applied 2026-04-29.
- If no: methodology layer is empirically dead. Correct outcome. Close the gate.

References at gate review time should still be: [`docs/rule_0.md`](../../rule_0.md) (Rule 0 standalone) and this README (resurrection rule).

## Post-move structure note (2026-05-07)

This methodology archive moved from `docs/methodology/archive/` to `archive/docs/methodology/archive/` under Approach D consolidation (commit a59985e). The two inner `archive/` segments are preserved as-is:

- `analysis/archive/` — Q-series closures (Q3 / Q5 / Q11 / Q12 / Q14 / Q15) + pre-locked bar-analysis (per "What is here" §Notice/Inquire-phase-work above).
- `analysis/msee/archive/` — H1–H10 individual hypothesis runs (per "What is here" §MSEE-framework above).

Depth is the cost of truthful provenance — three nested `archive/` segments document three distinct retirements (top-level consolidation, methodology-phase retirement, individual workstream closures).
