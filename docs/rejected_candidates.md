# Rejected portfolio candidates

Standing registry of strategy / instrument / parameter combinations investigated and rejected as portfolio additions. One entry per direction. Re-proposal of any entry on this list requires **new mechanism evidence**, not new parameters or a wider sweep.

This file is appended to at the close of any Pre-Q that closes FALSIFIED on strategy grounds, or at the close of a parent programme on SNAG-budget-exhaustion grounds (the Guardian-on-XAGUSD precedent below). New entries link to the closure artifact authoritative for the rejection.

The intake bar is the same as for any candidate: a mechanism-level claim with falsifiable specifics, not "let's try a wider grid."

---

## Entries

### Guardian-family strategy on XAGUSD (Silver)

**Rejection scope:** the direction is rejected, not only a single parameter port.
**Closure date:** 2026-05-14
**Authoritative artifact:** [`docs/briefs/Q-CORR-1-closure.md`](briefs/Q-CORR-1-closure.md)
**Closure basis:** parent programme Q-CORR-1 closed on SNAG-budget exhaustion. Q-CORR-1.1 falsified the v5.5-parameter-equivalence port (DD 11.52% > 8.0%; WR 11.34% below band). Q-CORR-1.2 (parameter-freedom WFO) was withdrawn pre-lock as part of the parent closure. Parallel v1.5-sweep track yielded a single +2% tweak running in-sample; quarantined-hint, not evidence.
**Surviving belt finding (NOT rejected):** instrument-level correlation is not a reliable proxy for strategy-level correlation. The NAS100/DJ30 strategy-level decorrelation despite tight instrument correlation stands as a portfolio-construction belt finding, independent of this candidate's rejection. A 5th strategy on a different instrument, or on Silver with genuinely new mechanism evidence, remains open at the standard intake bar.
**Re-proposal bar:** new mechanism evidence. "New parameters" / "a wider sweep" / "longer panel" / "different correlation gate threshold" do not clear the bar — that is precisely the move the parent closure rejected.

### Other directions (entries pending formalization)

Directions named in `Q-CORR-1-closure.md` §3 as existing on this list under prior disposition. Each requires its own entry written at the close of its authoritative investigation; the closure note references them as comparators only, not as content for this file.

- AUDNZD
- CHN50U
- Sentinel USDCHF
- ORATS short-vol strangles
- Aegis SHORT v0.1
- Guardian-on-USOIL

When the next closure note appends to this registry, that closure's author writes the relevant entry above this list and removes the corresponding bullet.

---

## Audit hooks

```bash
# Closure-pointer integrity: every rejected direction names an authoritative artifact
grep -n "Authoritative artifact" docs/rejected_candidates.md
# Expected: one line per directional rejection

# Re-proposal-bar discipline: every direction states "new mechanism evidence"
grep -n "Re-proposal bar" docs/rejected_candidates.md
# Expected: one line per directional rejection; phrasing names mechanism evidence, not "new parameters"

# Pending-entry hygiene: directions in the pending list either gain a full entry above or are dropped
grep -A1 "Other directions" docs/rejected_candidates.md
# Expected: list shrinks monotonically; entries never reappear once promoted
```
