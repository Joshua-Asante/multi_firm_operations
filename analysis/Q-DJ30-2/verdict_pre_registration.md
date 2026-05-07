# Q-DJ30-2 — verdict pre-registration

**Brief:** Q-DJ30-2 — DJ30 base-stop hard dollar cap
**Pre-registered:** 2026-05-06 (Phase A, before any cap function touches data)
**Layer:** INQHIORI (structural, low-reversibility, statistically gated)
**Lock target:** Striker DJ30 v4.5 → no artefact moves until verdict PROMOTE

**Immutability:** this file's gate thresholds, baseline anchors, and verdict mapping are FROZEN as of the pre-registration date above. Edits post-Phase A require a `docs/methodology/gate_audits/2026-MM-DD_q-dj30-2_pre_reg_amend.md` entry stating (a) what changed, (b) why, (c) which Phase the change was discovered in. Silent edits are a methodology violation per the inqhiori skill §12 audit-trail format.

---

## Baseline anchors (locked at pre-registration)

All gate comparisons resolve against these v4.5 baseline values. If Phase B reproduction disagrees, the brief halts (see Halt protocols below) — the baseline is not retroactively re-defined.

| Anchor | Value | Source |
|---|---|---|
| Strategy | Striker DJ30 v4.5 | `strategies/striker/striker_dj30_v4.5.pine` |
| Primary panel | n = 197 base entries | `data/tv_exports/pepperstone/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv`, EXIT rows where `Signal != "Long Add"` |
| Sensitivity panel | n = 224 (197 base + 27 pyramid) | same file, all EXIT rows |
| Allocation | 1.00% per trade | 2026-05-05 lock memo |
| Account size | $200,000 | DXTrade account spec |
| Nominal R (dollars) | $2,000 | 1.00% × $200,000 |
| Baseline PF | 2.755 | v4.5 lock memo |
| Baseline worst single-trade loss | −$11,871 | v4.5 lock memo; equals 5.94 × nominal R |
| Baseline pyramid contribution | ≈ 94% of strategy P&L | v4.5 lock memo |
| Cap formulation | `capped_pnl = max(actual_pnl, −cap_R × $2,000)` | brief Step 2 |
| Cap-level sweep | {1.5R, 2.0R, 2.5R, 3.0R, 3.5R} | brief Step 3 |

---

## Phase B — reproduction gate

Acceptance: ALL of the following.

| Metric | Threshold |
|---|---|
| Reproduced PF (n=197) | within 0.5% of 2.755 |
| Reproduced worst single-trade loss | within 0.5% of −$11,871 |
| Reproduced base-trade count | exactly 197 |
| Reproduced pyramid-trade count | exactly 27 |

Failure on any line → HALT, surface to Joshua, no further phases run. The CSV is canonical; reproduction failure means the brief was drafted against a different snapshot.

---

## Phase C — single-pass cap-level acceptance

Per cap level, all three thresholds must clear for the cap to advance to Phase D:

| Metric | Threshold (vs uncapped baseline) |
|---|---|
| Δ PF | ≥ −5% (i.e., ≥ 0.95 × 2.755 = 2.617) |
| Δ p99 DD | ≤ −1.0 pp (cap reduces tail) |
| Δ WR | ≥ −5 pp |

If zero cap levels pass: skip to Phase G with verdict **CLOSE / NULL**.

---

## Phase D — regime-robustness gate (load-bearing)

Q-DDP-1 protocol. Per cap level surviving Phase C, all three thresholds must clear:

| Metric | Threshold |
|---|---|
| Bootstrap p05 PF (n=100, 6-month-block) | ≥ 0.95 × full-panel PF for that cap |
| H1 ↔ H2 PF spread (H1 = trades 1–98, H2 = trades 99–197) | ≤ 10 pp |
| Bootstrap p05 p99 DD | ≤ full-panel p99 DD + 0.5 pp |

Skipping this gate is forbidden. Q-DDP-1 (2026-05-06) is the worked false-positive case: candidate C2 cleared full-panel single-pass and decisively failed regime-robustness. Same protocol applies here.

If no Phase C survivor passes Phase D: verdict **AMBIGUOUS / HOLD** (cap reduces tail but is not regime-robust).

---

## Phase E — pyramid audit (non-negotiable veto)

Per cap level surviving Phase D, all three thresholds must clear:

| Metric | Threshold |
|---|---|
| Pyramid-add WR (capped sequence) | ≥ baseline pyramid WR − 2 pp |
| Pyramid contribution to total P&L | within ±2% of baseline |
| Pyramid trigger times | unchanged from baseline (mechanism check) |

Failure on any line for any cap → that cap is closed regardless of Phase C/D/F results. Pyramid-load-bearing is canonical (≈ 94% of P&L), not conditional on Phase D performance.

If trigger-time check fails (mechanism invariance), the Rule 0 assumption from `striker_dj30_v4.5.pine:274` (`profitAtr >= pyramidTrigger`) has been violated by the cap — HALT and surface to Joshua before continuing. This is a deeper failure than a metric drift.

If no Phase D survivor passes Phase E: verdict **CLOSE / NULL**.

---

## Phase F — permutation test (Rule 1 partition gate)

Best Phase D + E survivor only.

| Setup | Value |
|---|---|
| Permutations | 1,000 |
| Null preserved | Total cap-touched trade count |
| Null randomized | Identity of which trades the cap floor applies to |
| Statistic | Observed lift in {PF, p99 DD} vs permutation null distribution |
| Test | Two-sided |
| Screen-out threshold | p ≥ 0.10 |

p ≥ 0.10 on either {PF, p99 DD} → verdict **CLOSE / NULL** (improvement consistent with random assignment; not a real mechanism).

---

## Phase G — verdict mapping (no goalpost moves)

| Verdict | Trigger | Artefacts written |
|---|---|---|
| **PROMOTE (LOCK CANDIDATE)** | Best cap level clears Phases C + D + E + F | (1) `Striker_DJ30_v4.6.pine` draft → (2) full portfolio re-MC via `python portfolio_mc.py --panel pepperstone` → (3) PROMOTE-only sanity gate: fresh v4.6 backtest export vs simulated-cap metrics; if ΔPF > 5pp drift, re-litigate verdict before re-MC stands → (4) pin update in `tests/test_mc_anchors.py` → (5) `docs/briefs/Q-DJ30-2/recommendation.md` (cites new MC pass/bust/p99 DD) → (6) `docs/locks/striker_dj30_v4.6_lock_2026-05-XX.md` from `docs/templates/lock_decision.md` → (7) `docs/methodology/findings/2026-05-XX_dj30_stop_cap.md` (verdict pointer, brief postmortem). **Sequence is mandatory** — recommendation.md and lock memo author last because they cite re-MC numbers. |
| **AMBIGUOUS / HOLD** | Phase C passes but no cap clears Phase D regime gate, OR Phase C ΔPF > 5% drop on otherwise-tail-reducing variant | `docs/methodology/findings/2026-05-XX_dj30_stop_cap.md` only. Default action: **no change to v4.5**. Match Q-DDP-1 sentinel precedent. |
| **CLOSE / NULL** | No Phase C survivor, OR Phase E veto fires on all Phase D survivors, OR Phase F p ≥ 0.10 | `docs/methodology/findings/2026-05-XX_dj30_stop_cap.md` only. No `recommendation.md`. Match 2026-05-03 / 2026-05-06 sentinel precedent. |

Re-MC trigger attribution (PROMOTE only): the trigger is the **v4.5 → v4.6 version bump**, which is canonically on the re-MC list (2026-05-05 lock memo). Bust-attribution shift is the consequence, not the trigger. The audit trail in recommendation.md must state this correctly.

---

## Halt protocols

- **Phase B reproduction failure** → HALT before Phase C. Surface to Joshua. CSV / brief snapshot mismatch is a question, not something to paper over.
- **Phase E trigger-time mechanism break** → HALT, do not advance to Phase F. Rule 0 invariance assumption from `striker_dj30_v4.5.pine:274` failed; the brief's mechanism scope is wrong, not the cap level.
- **Forbidden D-test discovered mid-execution** (per inqhiori skill §5) → HALT, write `docs/methodology/gate_audits/2026-MM-DD_q-dj30-2_<slug>.md`, surface to Joshua. Do not silently substitute a permitted test (Iran-Hormuz failure mode).
- **Locked artefact write attempted pre-verdict** → HALT immediately. The "DO NOT TOUCH" list in the brief is canonical; any attempted edit is a Rule 0 violation and the run is invalid.

---

## Forward-queue commitment

If Q-DJ30-2 closes NULL or AMBIGUOUS, the next Pre-Q forks on **DJ30 opening-gap magnitude only** (Q-DJ30-1 close-note pre-registration). The other two candidates (realized-vol-at-entry, S&P futures overnight range) collapse to the same underlying signal class and are not opened as separate Pre-Q gates. This commitment is also frozen at pre-registration; the verdict cannot license parallel exploration of all three.

---

## Audit attestation

This file was authored at Phase A of the Q-DJ30-2 execution plan, before:
- any capped-P&L vector was computed
- any sweep result was generated
- any bootstrap / permutation was run
- any data was loaded by `analysis/Q-DJ30-2/baseline_repro.py` or downstream scripts

Git commit history of this file is the canonical audit anchor. Any commit modifying gate thresholds, baseline anchors, or verdict mapping after the pre-registration date is a methodology violation unless paired with a `gate_audits/` entry as specified in the Immutability clause above.
