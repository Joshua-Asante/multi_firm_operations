# Methodology: Observation routing — three-bucket gate

**Date established:** 2026-04-25
**Status:** Active. Replaces the prior Notice / Inquire two-phase framework.
**Scope:** Every market observation, bar-data finding, anomaly, or "interesting
thing" that surfaces between locked decision points.

## Why

The Notice / Inquire framework produced forward-loaded multi-file artefact sets
as a hedge against discipline failures (overlay-from-observation, re-MC drift).
Those failures are already prevented by:

- **Rule 0** — read production code before any decision touching risk controls.
- **Iran/Hormuz lesson (generalized)** — headlines drive markets regardless of
  physical ground-truth; no overlay from regime story alone.
- **Overlay-proposal trigger discipline** — only a live-PnL gap vs MC justifies
  an overlay; bar-stat shifts do not.
- **Documented re-MC triggers** — 6mo live data, version bump, allocation
  outside G 0.30–0.34% safe band, `dd_protection` constant change.

With those four rules in place, the Notice phase's protective benefit is
redundant. Audit of the original 2026-04 Notice run: of three threads (A / B / C),
two produced "no action" outputs against material analytical cost (12 JSON +
5 figures + 6 CSV + a self-contained script). One thread (B) routed Forward.
Cost-to-yield ratio was bad — Notice was producing analysis, not protection.

The three-bucket gate is the lighter replacement. Same discipline outputs, no
phase ceremony.

## The gate

Every observation routes to exactly one of:

### Closed
**No action attached.** One-paragraph entry in the relevant findings doc
documenting "investigated and closed", with one sentence on what was checked
and why it does not move policy. No standing JSON / figure / CSV artefacts
required — anything regenerable from a script in under 5 minutes is regenerable
on demand if a future decision needs it. Add-back rule: regenerate only to
defend a specific decision, not preemptively.

### Action
**Specific code or config change with owner and verification criteria.**
Routes to a normal task / commit / ADR. The artefact is the change itself plus
the verification log. This is the bucket where overlays, allocation tweaks, and
`dd_protection` constants would live — and they are gated by the four rules
above; observation alone never lands here.

### Forward
**Becomes a numbered question on the Open Questions list, ordered by
cheapest-falsification-first.** The observation produces only the scaffolding
needed to support that question (input data, one figure, summary table).
Standing artefacts are pruned to that scaffolding. Forward questions are
gated downstream on their own logic — not all of them run; some get
superseded.

## How to apply

1. **State the observation** in one sentence.
2. **Pick the bucket.** If the observation closes a door, it is Closed. If the
   observation prescribes a code change *and* the change clears the four rules
   above, it is Action. If the observation suggests a question whose answer
   could change policy, and the question is decidable with a cheaper test than
   running the analysis, it is Forward.
3. **For Closed:** write the one-paragraph archive entry. Delete or do not
   produce standing artefacts beyond what is needed for the archive.
4. **For Action:** open the change, log the verification, reference the
   triggering rule.
5. **For Forward:** state the question on the parent Open Questions list with
   a falsification-first ordering. Retain only the scaffolding needed to
   support the question.

## Common failure modes

- **Producing Forward-bucket artefacts as Closed-bucket archive.** If the
  observation routes Closed, do not produce or retain a multi-file artefact set
  "in case it's useful later." It is regenerable on demand.
- **Routing observation directly to Action without the four rules.** Action
  requires a triggering rule — Rule 0, an overlay-discipline live-PnL gap, or
  a documented re-MC trigger. An observation alone is not a trigger.
- **Promoting Forward questions before their gate fires.** A Forward question
  is gated; do not pull it forward into the current session unless its gate
  has actually fired (e.g., live-PnL gap appears, version bump committed,
  6mo live data accumulated).
- **Replacing the Notice framework with a heavier framework.** The three-bucket
  gate must stay lighter than what it replaces. If a sub-procedure is being
  added that produces the same forward-loaded artefact problem, simplify
  further.

## Retroactive routing of the 2026-04 Notice run

Per `docs/methodology/archive/analysis/notice_phase/findings.md`:

- A1, A2, A3, A4 — **Closed.** ATR sizing arithmetic is intact; bar-stat
  shifts do not justify an overlay; overlay door already closed by ATR-based
  sizing locked in Guardian v5.5.
- B1, B2 — **Forward.** Q5 (XAU-USDJPY break-window strategy P&L) is the
  cheapest falsification of B2's pervasive-drift finding. Q3 (full pairwise
  strategy-P&L correlation) is conditional on Q5 showing breakdown. B3 is
  Closed-supporting (rules out daily-aggregation artefact for B1/B2).
- C1, C2, C3, C4 — **Closed.** Single-fact comparison; paired stationary-
  bootstrap vs fixed-block (Q6) remains gated on a documented re-MC trigger.

Standing JSON / figure / CSV outputs for the Closed-bucket findings were
deleted in the same compression. Regenerable from `docs/methodology/archive/analysis/notice_phase/notice_phase.py`.

## Cross-references

- Notion: [Claude Code brief — 1R diagnosis + Open Questions reorder + Notice phase compression — 2026-04-25](https://www.notion.so/34ddc0b53c1181199976c9b1b4effb17).
- Repo: [`docs/methodology/archive/analysis/notice_phase/findings.md`](archive/analysis/notice_phase/findings.md) — first application of the gate.
- Methodology: this gate is an Algorithm-driven simplification (Question / Delete / Simplify) of the prior Notice/Inquire framework. See the permanent Algorithm reference page for context on the framework that produced it.
