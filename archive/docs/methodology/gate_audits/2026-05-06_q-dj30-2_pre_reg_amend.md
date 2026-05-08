# Q-DJ30-2 — pre-registration amendment

**Date:** 2026-05-06
**Brief:** Q-DJ30-2 — DJ30 base-stop hard dollar cap
**Discovered in:** Phase B (reproduction gate)
**Resolution chosen:** Option 1 (amend pre-registration, paired with this audit entry)
**Pre-registration commit (pre-amend):** `eb5310b` — `archive/analysis/Q-DJ30-2/verdict_pre_registration.md`

---

## What changed

Two corrections to `archive/analysis/Q-DJ30-2/verdict_pre_registration.md`:

### Change 1 — PF anchor cardinality

**Before (commit eb5310b):**

| Anchor | Value | Source |
|---|---|---|
| Primary panel | n = 197 base entries | ... |
| Baseline PF | 2.755 | v4.5 lock memo |

**After:**

| Anchor | Value | Source |
|---|---|---|
| Primary panel (PF/WR/p99 DD comparisons) | n = 197 base entries | ... |
| Sensitivity panel (PF anchor source) | n = 224 (197 base + 27 pyramid) | ... |
| Baseline PF (n=224 all entries) | 2.7528 | reproduced 2026-05-06; matches v4.5 lock memo's PF=2.755 to 0.08% |
| Baseline PF (n=197 base only) | 2.3294 | reproduced 2026-05-06 from CSV; **derived anchor** (not in lock memo) |

**Phase B gate update:**

| Metric | Before | After |
|---|---|---|
| Reproduced PF | "(n=197) within 0.5% of 2.755" — INCONSISTENT | "(n=224, all entries) within 0.5% of 2.7528" |
| Reproduced base-only PF | n/a | "(n=197) within 0.5% of 2.3294" — pinned at this reproduction |

**Phase C derived value:** `Δ PF ≥ −5%` floor reads against **base-only PF baseline**, since brief Step 3 specifies metrics "on n=197 primary panel." Numerically: `0.95 × 2.3294 = 2.213` (was incorrectly stated as `0.95 × 2.755 = 2.617`).

### Change 2 — Pyramid contribution baseline

**Before:**

| Anchor | Value | Source |
|---|---|---|
| Baseline pyramid contribution | ≈ 94% of strategy P&L | v4.5 lock memo |

**After:**

| Anchor | Value | Source |
|---|---|---|
| Baseline pyramid contribution | 42.7% of strategy P&L | reproduced 2026-05-06; sum_pyramid $154,944.05 / sum_all $363,113.05 |

The ≈94% figure traces to `project_pyramid_is_strategy_for_nas100.md` (memory): NAS100 pyramid contribution measured at 81–99% per year. That figure was misattributed to DJ30 in the pre-registration. DJ30's actual pyramid contribution is ~42.7% — still load-bearing (not negligible), but materially smaller than NAS100's.

**Phase E threshold interpretation (no text change):** "within ±2% of baseline" is read as relative (±2% × 42.7% = ±0.85pp absolute). The mechanism the audit detects (capping base-leg trades shifts pyramid's relative share) is unchanged; only the pinned baseline value moves.

---

## Why

### PF cardinality (change 1)

TradingView's Strategy Tester computes PF across all trades, including pyramid legs. The v4.5 lock memo PF=2.755 is therefore an all-entries figure (n=224), not base-only. The pre-registration's table paired the 2.755 anchor with the row labeled "Primary panel = n=197 base entries," creating an internal inconsistency that surfaced cleanly in Phase B (PF on n=197 base reproduces to 2.3294, drift 15.45%; PF on n=224 reproduces to 2.7528, drift 0.08%).

Worst-loss anchor (−$11,871) and trade counts (224 / 197 / 27) reproduce exactly, so this is a pre-registration framing artifact, not a data discrepancy. CSV is the right vintage.

### Pyramid contribution (change 2)

The ≈94% claim has no on-disk basis for DJ30. Sum-of-pyramid-P&L vs sum-of-all-P&L on the locked CSV gives 42.7%. The 94% figure appears in memory only for NAS100 (Q-NAS-1 finding). This is a cross-strategy attribution error in the pre-reg.

The amendment doesn't change Phase E's mechanism — it still tests for cap-induced pyramid destabilization — but the audit becomes calibrated against the correct baseline.

---

## Why option 1 (not option 2 or 3)

- **Option 2 (re-anchor to base-only PF=2.3294 as the lock-memo source).** Rejected: would imply the v4.5 lock memo's PF=2.755 was wrong at source. PF=2.7528 reproducing to 0.08% on all-entries confirms the lock memo is correct; the pre-reg's framing was wrong.
- **Option 3 (re-fetch CSV).** Rejected: worst-loss anchor reproduces exactly, indicating CSV is the right vintage. Re-fetch would surface no change.

---

## Forward applicability

Two reusable lessons surface from this amendment:

1. **PF anchor source declaration.** Future briefs should state the cohort over which any PF anchor is computed, not just the value. The v4.5 lock memo's PF=2.755 is correct; what's missing in the chain to Q-DJ30-2 is the cardinality association.

2. **Cross-strategy attribution audit.** The pyramid-contribution claim in the pre-reg was a cross-strategy borrowing error. Any future "≈X% of P&L" claim about a strategy should be traceable to a per-strategy reproduction or a per-strategy memory entry, not borrowed from a different strategy's measurement. Worth filing as a feedback memory.

---

## Audit chain

- Pre-registration original: commit `eb5310b`
- Discrepancy surfaced: `archive/analysis/Q-DJ30-2/PHASE_B_HALT.md` (this run, 2026-05-06)
- Pre-registration amended: commit (TBD, alongside this entry)
- Phase B re-run after amendment: pending in same commit; expected PASS

The amendment commits this audit entry and the updated pre-registration in the same commit so git history shows them together.
