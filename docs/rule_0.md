# Rule 0 — Audit-first

Before any decision brief or implementation step touching risk controls
(`dd_protection`, lot sizing, protection tiers, allocation, calibration constants),
read the production code directly first. Not memory. Not prior decision docs.

Order: production file → brief against ground truth → validate → lock → implementation.

## Corollaries

- Suspect single-rule descriptions of multi-rule systems.
- Data-source labels are NOT data-source verification.
- Where prior docs and code disagree, code wins; flag the discrepancy.
- Load-bearing claims without code-resident verification are unverified, regardless of how they're phrased in prose. Identity, contract, and cardinality assertions are the baseline; helpers in `lib/mvd.py`.

## Triggering failures

- 2026-04-17: `dd_protection` misstatement against production constants. Brief described a single rule; production carried a second equity tier that was dead under the live `min()` combining semantics. The dead tier was deleted (Algorithm step 2: Delete) only after Rule 0 read of production; brief had been authored from prior-doc memory.
- 2026-04-27: weakened-form Rule 0 (read-prior-doc-not-code) produced wrong audit verdict on Q-meta-a brief. Strengthened: prior decision docs are not a Rule 0 substrate.

## Scope

Only methodology rule that survived the 2026-04-29 archive. Other rules
(INQHIORI ⊕ The Algorithm framework, Pre-Q gates, Case B audits, backfill
discipline, mandatory header ordering, MVD methodology framing) were retired
with the strategy-research phase. New rules are written only against observed
failures during execution phase, not hypothesized ones.

See [`docs/methodology/archive/README.md`](methodology/archive/README.md) for the resurrection rule and 90-day review gate.
