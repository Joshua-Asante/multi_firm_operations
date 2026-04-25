# Changelog

**Scope:** repo, methodology, and tooling changes only. Per-strategy version history lives in `strategies/<name>/<name>_CHANGELOG.md` (e.g. `strategies/aegis/aegis_CHANGELOG.md`).

## 2026-04-24

- Added `docs/adr/2026-04-24-mvd-discipline.md` — ADR formalizing the Minimum Viable Defense discipline for load-bearing artifacts crossing the live capital boundary.
- Added `docs/methodology/mvd.md` — methodology reference: 5 families, worked examples, 9-instance audit table, producer/consumer rules.
- Added `lib/mvd.py` — assertion library (9 helpers across 5 families: cardinality, identity, contract, cross-source, code-vs-doc).
- Added `docs/templates/lock_decision.md` — lock brief template with verification preamble and MVD-attest section.
- Added `docs/templates/calibration_brief.md` — calibration brief template with identity-assertion preamble.
- Added `docs/templates/bust_analysis.md` — bust analysis template requiring script-generated event-count + $ attribution.
- **MVD-attest:** the audit table in `docs/methodology/mvd.md` is the source for all numbers cited in the ADR (`67%`, `6/9`, `9 instances`, etc.); numbers traced on first read.
