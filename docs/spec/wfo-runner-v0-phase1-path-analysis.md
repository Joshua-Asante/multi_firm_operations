# WFO runner v0 — Phase 1 path analysis (CC)

**STATUS:** DONE_WITH_CONCERNS (2026-05-13)  
**Scope:** Choose between Path A (Python / structural OOS) vs Path B (TV-native coarse grid) for Q-CORR-1.2.

---

## Decision

**Accepted:** (Coarse, **Path B**)

**Decider:** Joshua — 2026-05-13

---

## Summary rationale

- Estimated **3.25–5.25 dev-days** vs Path A **7.5–14** dev-days.
- Comparable wall-clock under bandwidth constraints (TV batch exports vs translated execution).
- Native Pine on Pepperstone removes Pine↔Python translation risk for admission-only scope.
- Sufficient for Q-CORR-1.2’s **binary admission** gate; global optimization deferred.

---

## Concerns (carried to implementation)

1. **Procedural OOS risk:** Path B lacks structural `Window` isolation. Mitigation: manifest timestamps + §6.5 train-selection lock + `scripts/wfo/audit_path_b_ordering.py`.
2. **Batching cheat:** Single end-of-run git batch can weaken timestamp audits; discipline requires committing train artifacts + manifest **before** OOS exports per fold.

---

## Deferred work

- Sequenced (Wide, Path A) optimization → possible **Q-CORR-1.3** iff Q-CORR-1.2 RESOLVED.
