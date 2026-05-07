# Q-DJ30-2 Phase B — HALT

**Date:** 2026-05-06
**Status:** Reproduction gate FAILED on PF; HALT before Phase C per pre-registration halt protocol #1.
**Action:** Surface to Joshua. Do not amend pre-registration without a paired `docs/methodology/gate_audits/` entry per immutability clause.

---

## Gate result

```
[PASS] Base count == 197                        (got 197)
[PASS] Pyramid count == 27                      (got 27)
[FAIL] PF within 0.5% of 2.755                  (got 2.3294, drift 15.45%)
[PASS] Worst loss within 0.5% of -$11,871       (got -$11,870.65, drift 0.00%)
```

Worst-loss reproduces exactly. Trade-count reproduces exactly. PF on the n=197 base panel does NOT match the pre-registration anchor.

---

## Diagnosis

PF computed three ways from the same CSV:

| Cohort | n | PF |
|---|---|---|
| All entries | 224 | **2.7528** ← matches v4.5 lock memo's 2.755 (drift 0.08%) |
| Base only (Signal=='Long') | 197 | 2.3294 |
| Pyramid only (Signal=='Long Add') | 27 | 4.0639 |

The lock memo's PF=2.755 is computed on **all 224 trades**, not the 197 base subset. This is consistent with how TradingView's Strategy Tester reports PF — across all trades including pyramid legs. The pre-registration's Baseline Anchors table pairs the PF anchor with the row labeled `Primary panel = n=197 base entries`, which is the framing error: the PF number is correct, the cardinality association is wrong.

## A second finding (more substantive)

Pyramid contribution to total P&L:

```
Sum base    = $208,169.00
Sum pyramid = $154,944.05
Sum all     = $363,113.05
Pyramid contribution = 42.7% of total
```

Pre-registration claims `Baseline pyramid contribution ≈ 94% of strategy P&L`. Actual is **42.7%**. The ≈94% figure appears to be misattributed — Q-NAS-1 found NAS100 pyramid contribution at 81–99% per year (memory: `project_pyramid_is_strategy_for_nas100.md`), and the pre-registration may have inherited that figure cross-strategy.

DJ30 pyramid is still load-bearing (42.7% is not negligible), but the magnitude is materially different. This affects Phase E's pyramid audit thresholds, which were calibrated as ±2% of P&L contribution — at 42.7% baseline, that band may be too tight or too loose depending on what the audit is intended to detect.

---

## What does NOT change

- Worst single-trade loss anchor: `-$11,870.65 ≈ -$11,871` ✓ (the −5.94R figure is correct)
- Trade counts: 224 / 197 / 27 ✓
- Cap-level sweep mechanics, regime-robustness protocol, permutation-test design — all unchanged
- Pre-registration immutability clause still applies; this finding does NOT license a silent edit

---

## Suggested resolutions (Joshua's call)

Three live options, presented without recommendation:

1. **Amend pre-registration** (paired with `gate_audits/2026-05-06_q-dj30-2_pre_reg_amend.md`): change Baseline Anchors → PF=2.755 attached to `n=224 all entries` (not `n=197 base`). Update pyramid contribution → 42.7% measured. Update Phase B gate to test PF on the all-entries cohort. Update Phase E pyramid audit's `±2%` threshold if needed.

2. **Re-anchor to base-only PF.** Re-derive the PF=2.755 source — if the lock memo intended base-only and the data shows 2.3294, that's a different (and more serious) issue. Worth a quick git-blame on the lock memo to see when 2.755 was authored and against what panel.

3. **Re-fetch the CSV.** Per memory `feedback_on_disk_artefact_can_be_wrong.md`, treat the on-disk CSV as a re-fetch candidate alongside the memo. The 2026-05-05 Guardian episode is the precedent. Less likely here because the worst-loss anchor reproduces exactly, suggesting the CSV is the right vintage.

Joshua's prior on similar discrepancies (Q-DDP-1 anchor reconciliation, 2026-05-04): treat anchor drift as a legitimate question, not a paperwork item. Most likely outcome here is option 1 (framing artifact in pre-reg, not a data issue), but the path requires the paired audit-trail entry.

---

## Files written this phase

- `analysis/Q-DJ30-2/baseline_repro.py` — the reproduction script (committed)
- `analysis/Q-DJ30-2/PHASE_B_HALT.md` — this file
- (no changes to pre-registration; that file remains as committed in `eb5310b`)
