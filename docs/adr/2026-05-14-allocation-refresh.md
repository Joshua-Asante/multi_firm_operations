# ADR: 2026-05-14 allocation refresh — DJ30 risk 1.00% → 0.75% (pyramid 350% → 500%), NAS100 0.40% → 0.45%

**Status:** ACCEPTED (with documented regime-robustness-gate override)
**Date:** 2026-05-14
**Authors:** Joshua
**Supersedes:** Allocation table fixed by 2026-04-17 lock cycle (challenge phase = funded phase, no re-sizing at pass) — for striker / striker_nas100 entries only. Guardian (0.34%) and Aegis (1.50%) unchanged.

---

## §0 — Rule 0 reads (production-source verification)

Verification anchors as of 2026-05-14 (commit `b54c02a` HEAD before this change):

- [`portfolio_mc.py`](../../portfolio_mc.py) — anchor `54d2285` (Q-MCFP-1 precision treatment). Verified: `ALLOCATIONS` dict at line 46–51 pre-edit reads `striker: 0.0100, striker_nas100: 0.0040`; `PEPPERSTONE_PANELS` at line 72–77 pre-edit references `Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-14_e3e3d.csv` and `Striker_NAS100_v1_PEPPERSTONE_NAS100_2026-05-14_36258.csv`. The change is a 2-line edit on each.
- [`dd_protection.py`](../../dd_protection.py) — anchor `6c7fa54` (ULP rounding fix). Verified: `DD_TRIGGER = 0.015`, `DD_SCALE = 0.40` unchanged; this ADR is **not** a dd_protection lock change.
- [`tests/test_mc_anchors.py`](../../tests/test_mc_anchors.py) — anchor `54d2285`. Pins prior to this ADR: Pepperstone 0.9865/0.0025/0.0469 (panel-refresh anchor from earlier today's working tree, not yet committed); OANDA 0.9623/0.0069/0.0491.
- [`CLAUDE.md`](../../CLAUDE.md) — anchor `51005fc` for committed text; working-tree state post-panel-refresh edits not yet committed. Strategy Reference table headline at line 43–48 lists DJ30 1.00% / NAS 0.40% (this ADR changes both).
- [`docs/methodology/regime_robustness_gate.md`](../methodology/regime_robustness_gate.md) — anchor `2567b15`. The gate is scoped to "any LOCK CANDIDATE on a `dd_protection`-class risk constant"; allocation changes are within scope by reasonable reading (same loss-magnitude family) and outside scope by literal reading. This ADR resolves the ambiguity by explicit override (see §Override below) rather than gate execution.
- [`docs/briefs/Q-DDP-1/recommendation.md`](../briefs/Q-DDP-1/recommendation.md) — anchor `dc75ffa`. C2 dd_protection lock and prior C2-override pattern; this ADR follows the same override-with-documented-grounds template.
- [`docs/adr/2026-05-08-dd-trigger-c2-relock.md`](2026-05-08-dd-trigger-c2-relock.md) — anchor `9268289`. Prior C2 lock ADR with documented dissent; structurally analogous to this one.
- CSV data files: `data/tv_exports/pepperstone/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-14_e4dd7.csv` (variant DJ30 at 0.75% risk / pyramid 500%, 209 trades, PF 2.877, Net $277,463, DD 4.78%, 1R $3,525) and `Striker_NAS100_v1_PEPPERSTONE_NAS100_2026-05-14_da880.csv` (variant NAS100 at 0.45% sizing, 188 trades, PF 4.659, Net $627,298, DD 4.74%, 1R $4,316). Both reconciled before MC. Trade-count drift vs prior canonical: DJ30 208 → 209 (pyramid 500% changed at least one day-soft-stop interaction); NAS100 188 → 188 (identical trade selection, sizing-only change).

---

## Context

Two events sequenced this lock event:

1. **2026-05-14 panel refresh.** All four Pepperstone canonical CSVs were swapped to a strict 2022-05-14 → 2026-05-14 vintage. Under the dd_protection C2 constants (DD_TRIGGER 0.015 / DD_SCALE 0.40, unchanged from 2026-05-08), the refreshed panel re-validated C2 with margin: 98.65% pass / 0.25% bust / 4.69% p99 DD (vs prior 98.09 / 0.36 / 4.73). The refresh produced a bust-attribution rotation: aegis 24.1% → 20.3% (earliest USDJPY weakness rolled off the window), guardian 21.3% → 27.0%, striker 44.4% → 43.2%, NAS 10.2% → 9.5%. The MVD `assert_window` tolerance was loosened 60d → 100d to accept Aegis's 1367-day span (filter warm-up delays first signal); the 1400d threshold still rejects ≥3-month coverage gaps.

2. **Bust-attribution read.** Striker DJ30 dominated the bust queue at 43.2% (largest contributor) on the panel-refresh anchor; NAS100 was the smallest at 9.5% — well below its 0.40% allocation share. The diversification thesis at NAS100 lock (`docs/briefs/striker_nas100_q_nas_3_mc_addition.md`) projected NAS as the lowest bust contributor by design, but the wider-than-expected gap (9.5% bust share vs 14.3% allocation share = 0.40 / 2.79 total allocation) suggested NAS was under-allocated relative to its variance-budget headroom. Concurrently, DJ30's bust dominance suggested capacity to reduce its allocation without breaking pass-rate.

Three-way knob exploration (in-session MC) produced the locked configuration:
- DJ30 risk **1.00% → 0.75%** (reduce dominant bust contributor)
- DJ30 pyramid **350% → 500%** (compensate for risk reduction by intensifying winners; Pine source change)
- NAS100 allocation **0.40% → 0.45%** (use the headroom; offset DJ30's expected pass-time cost)
- Guardian 0.34% and Aegis 1.50% **unchanged**

Standing doctrine touched:
- CLAUDE.md "Strategy Reference" / "Locked allocations (unified 2026-04-17): challenge phase = funded phase. No re-sizing at pass" — modified at the allocation level for striker and striker_nas100 only.
- CLAUDE.md "Key Principle: The portfolio and strategies are LOCKED. This pipeline manages the operational layer — it never touches strategy parameters." — **the DJ30 pyramid change (350% → 500%) is a Pine-source parameter change and breaches the strict reading** of this principle. See §Forbidden moves and §Open items below.
- `docs/methodology/regime_robustness_gate.md` — gate not executed; explicit override in §Override.

---

## Decision

Lock the following 4-strategy allocation + parameter configuration:

| Strategy | Risk | Pine parameter delta | CSV (Pepperstone) |
|---|---:|---|---|
| Guardian Gold v5.5 | 0.34% | none | `..._XAUUSD_2026-05-14_3b689.csv` |
| Striker DJ30 v4.5 | **0.75%** (was 1.00%) | **pyramid 350% → 500%** | `..._US30_2026-05-14_e4dd7.csv` |
| Aegis-Reversion v4.3 | 1.50% | none | `..._USDJPY_2026-05-14_d2682.csv` |
| Striker NAS100 v1 | **0.45%** (was 0.40%) | none (sizing-only re-export) | `..._NAS100_2026-05-14_da880.csv` |

dd_protection unchanged: **DD_TRIGGER = 0.015, DD_SCALE = 0.40** (C2, 2026-05-08 lock).

### Locked MC numbers (canonical reference)

Config above, 10,000 sims × 3 seeds (42 / 123 / 2026), horizon 150 days, Pepperstone panel 2022-05-23 → 2026-05-14 (1039 bdays, 207 week-blocks).

- **Pass: 98.78%** (sigma 0.02%)
- **Bust: 0.12%** (0.00% daily + 0.12% static, sigma 0.01%)
- **Timeout: 1.10%**
- **Median days to pass: 21** (unchanged from panel-refresh anchor; DJ30 reduction's expected +1d cost offset by NAS bump)
- **p50 DD: 1.28% / p95 DD: 3.28% / p99 DD: 4.17%**
- **Bust attribution:** guardian 34.3% / aegis 28.6% / striker 25.7% / striker_nas100 11.4% (35 total busts across 30K sims)

OANDA C2 anchor under the new allocations (3-strategy, no NAS100 panel): **96.33% pass / 0.40% bust / 4.73% p99 DD / median 26 days**. Pass +0.10pp, bust −0.29pp, p99 DD −0.18pp vs the pre-refresh OANDA anchor (96.23 / 0.69 / 4.91). Median rises 25 → 26 — the DJ30 risk reduction's pass-time cost is not offset on OANDA (no NAS panel to compensate).

Pinned by `tests/test_mc_anchors.py`.

---

## Falsifier

If rolling 6-month MC pass-rate on the live-extended Pepperstone panel falls below 95% for two consecutive 6-month windows, **OR** if Striker DJ30's live `journal_review.py` edge-captured ratio over a ≥30-trade post-lock window falls below 0.70 (with pyramid 500% live behavior at the centre of investigation), this ADR is invalidated and the allocation configuration requires re-evaluation. The minimum action is reversion to (DJ30 1.00% / pyramid 350%, NAS 0.40%) — the panel-refresh-only anchor at 98.65 / 0.25 / 4.69 — pending re-investigation.

---

## Consequences

### Positive

- **Pareto-better than panel-refresh-only anchor on every MC metric.** Pass +0.13pp (98.65 → 98.78), bust −0.13pp (-52% relative, 75 → 35 busts on 30K sims), p99 DD −0.52pp (4.69 → 4.17), timeout −0.01pp, median days unchanged at 21. Both lock criteria (bust < 1%, p99 DD < 5%) clear with **the widest margin of any anchor on record**.
- **Bust attribution rotates away from DJ30 dominance.** Striker share 43.2% → 25.7% (−17.5pp). DJ30 no longer the largest contributor; guardian becomes top (34.3%) by re-attribution. The re-attribution shifts the live-PnL attention budget commensurately.
- **NAS100 capacity utilized.** NAS bust share rises only 9.5% → 11.4% (+1.9pp) despite a 12.5% allocation increase — consistent with the diversification thesis that NAS sits well below its variance-budget headroom.
- **Median days-to-pass preserved at 21.** The DJ30 risk reduction's expected cost (panel-refresh-only at DJ30-variant-alone gave median 22) is fully offset by the NAS bump.
- **OANDA pattern-spotting validates direction.** OANDA panel (unchanged, 3-strategy) re-anchors under the new allocations at 96.33 / 0.40 / 4.73 — same directional improvement (pass up, bust down, p99 DD down) on the secondary panel.

### Negative / watched

- **Regime-robustness gate NOT run.** Per `docs/methodology/regime_robustness_gate.md`, the gate is mandatory for `dd_protection`-class risk constants; allocations are ambiguous-in-scope. Q-DDP-1's C2 candidate failed this gate decisively (H1 sub-panel pass-rate 86.78%) and was overridden on broker-feed grounds. This ADR overrides the gate's potential applicability on the explicit grounds enumerated in §Override below. The dissent on regime fragility persists: if Pepperstone re-exports in 2026-H2 / 2027-H1 show H1-like underperformance with these allocations, the regime-fragility risk has materialized.
- **DJ30 pyramid 350% → 500% is a Pine-source change, not a pure operational-layer adjustment.** This breaches the strict reading of CLAUDE.md "Key Principle: The portfolio and strategies are LOCKED ... it never touches strategy parameters." The version tag is retained as v4.5 (per user-provided filename `e4dd7`), but a future audit may legitimately require a v4.6 version-bump and a strategy-source lock ADR. See §Open items.
- **DJ30 trade-count drift 208 → 209.** Pyramid 500% changed at least one day-soft-stop interaction. Not strictly a like-for-like swap of v4.5 base behavior. The variant has slightly higher per-trade DD (4.78% vs 4.66% raw on the CSV) — the portfolio MC absorbs this via the implied_1r-based scaling.
- **NAS variant CSV `da880` has heavier pyramid than canonical `36258`.** Same 188 trades and identical PF/WR, but +22% Net and +12% DD on the raw CSV. portfolio_mc normalizes via implied_1r so the allocation-target sizing is preserved — but if NAS Pine pyramid was edited (not just risk), the v1 designation is also strained. The user-provided filename retains "v1"; a future audit may require a v1.x version-bump.
- **Guardian becomes the largest bust contributor (34.3%).** Mostly mechanical re-attribution from the smaller bust pool, not an absolute risk increase (Guardian bust count: 21.3% × 75 = 16 → 34.3% × 35 = 12 — count *decreased*). Forward live-PnL attention rotates: DJ30 was the prior watchlist top, now Guardian is.
- **Median days-to-pass on OANDA rises 25 → 26.** No NAS100 on OANDA to offset the DJ30 risk reduction. Pattern-spotting role unchanged; OANDA was never the lock-decision substrate. Watchlist only.

---

## Override — regime-robustness gate

This ADR proceeds without executing the regime-robustness gate (half-panel split + 6mo block bootstrap) on the explicit grounds:

1. **Bust direction is improving, not degrading.** The gate guards against silent regime-fragility under risk-increase changes. This change is a **risk-reduction** (DJ30 1.00% → 0.75% is a 25% relative risk reduction; pyramid 500% intensifies wins but does not increase loss magnitude; NAS 0.40% → 0.45% is a 12.5% allocation increase on the lowest-bust strategy). The asymmetric failure mode the gate targets is inverted here.

2. **Panel-refresh-only anchor already cleared lock criteria with margin.** The 2026-05-14 panel-refresh-only anchor (98.65 / 0.25 / 4.69) cleared both lock criteria. This ADR's anchor (98.78 / 0.12 / 4.17) clears them with wider margin still. The gate's purpose is to verify the same panel doesn't hide regime-fragility behind aggregate metrics; the regime that drove Q-DDP-1's C2 H1 sub-panel failure (2022-01 → 2024-04) has rolled off the new strict 4yr window by ~7 months. The half-panel split that previously surfaced fragility is partially de-confounded.

3. **dd_protection constants unchanged.** The gate's literal scope is `dd_protection`-class. This ADR does not touch DD_TRIGGER or DD_SCALE. The 2026-05-08 C2 relock (the gate's prior worked example) is preserved without modification.

4. **Forward revert trigger is operationalized.** The same quarterly `time_to_pass.py --regime-check` cadence from the 2026-05-08 C2 ADR (next dates 2026-08-08, 2026-11-08, 2027-02-08, 2027-05-08) catches the failure mode the gate would have caught — just retrospectively rather than pre-lock. Combined with the live-PnL edge-captured falsifier in §Falsifier, the regime-fragility risk has dual catch-paths.

The dissent on regime-robustness is preserved: a future panel update with materially different 2022 USDJPY / DJ30 / NAS dynamics could surface H1-like asymmetry. This override accepts that risk.

---

## Alternatives considered

- **Panel-refresh only (DJ30 1.00% / pyramid 350%, NAS 0.40%) at 98.65 / 0.25 / 4.69.** Strictly Pareto-dominated by this ADR's config on every metric. **Rejected** as the locked anchor but **preserved** as the documented revert target if §Falsifier fires.
- **DJ30 0.75% / pyramid 500% only (no NAS bump).** Pass 98.70 / bust 0.10 / p99 DD 4.17 / median 22. Better bust than this ADR's locked config (0.10 vs 0.12), but costs +1 day median pass-time. **Rejected** because median pass-time is the operational-velocity metric the C2 relock was justified by; preserving 21 is worth +0.02pp bust.
- **NAS 0.45% bump alone (DJ30 unchanged at 1.00% / 350%).** Not run as a discrete MC, but inferable: NAS bump on its own adds equity velocity without reducing DJ30's bust dominance — would give modest pass-rate improvement and small bust improvement, but leaves DJ30 as the dominant variance contributor. **Rejected** because the bust-attribution insight (DJ30 at 43.2%) was the load-bearing observation; not acting on it would forfeit the larger improvement.
- **NAS 0.50% (aggressive bump).** Not tested in this session. **Rejected** because 0.45% already delivers Pareto-better outcomes and 0.50% pushes NAS bust share into untested territory. Forward consideration if the live-extended panel shows NAS bust share remains < 12% over 6+ months.
- **Run the regime-robustness gate.** **Rejected** on the grounds enumerated in §Override above. This is the load-bearing alternative; the override is the load-bearing decision.

---

## Forbidden moves

- **Silently treating this as a "panel refresh" without acknowledging the strategy-parameter change.** The DJ30 pyramid 350% → 500% is a Pine-source change. Calling it operational-layer-only is wrong. This ADR documents the breach explicitly so a future audit doesn't have to reconstruct the call.
- **Bumping NAS allocation further (≥0.50%) without re-running MC and the live-PnL falsifier.** The 0.45% bump is at the edge of the in-session evidence; further capacity utilization needs forward data.
- **Reverting only the NAS bump while keeping DJ30 0.75% / pyramid 500%.** The two changes are coupled — NAS bump exists to offset DJ30 reduction's pass-time cost. Reverting NAS alone would push median pass-time to 22 without recovering the bust-side benefit of restoring DJ30 to 1.00%. If reverting, revert both.
- **Skipping the next four quarterly `time_to_pass.py --regime-check` runs.** The override's only retrospective safety net is the quarterly cadence. Skipping is equivalent to dropping the falsifier.
- **Editing this ADR mid-investigation if forward data goes sideways.** Per `brief-authoring` trap #12: if §Falsifier fires, the discipline is to close this ADR (status → SUPERSEDED-BY-NNN) and open a fresh ADR with the new gate criteria, not amend in place.

---

## Implementation notes

Changes landed in this same commit set:

- `portfolio_mc.py`: `ALLOCATIONS["striker"]` 0.0100 → 0.0075; `ALLOCATIONS["striker_nas100"]` 0.0040 → 0.0045; `PEPPERSTONE_PANELS["striker"]` → `e4dd7`; `PEPPERSTONE_PANELS["striker_nas100"]` → `da880`. `assert_window` tolerance 60 → 100 (carried from panel-refresh edit).
- `tests/test_mc_anchors.py`: Pepperstone pin 0.9865/0.0025/0.0469 → 0.9878/0.0012/0.0417; OANDA pin 0.9623/0.0069/0.0491 → 0.9633/0.0040/0.0473. Docstrings updated.
- `CLAUDE.md`: Strategy Reference table risk column (DJ30 0.75%, NAS 0.45%); Most recent version locks line adds 2026-05-14 allocation refresh annotation; 2026-05-14 panel-refresh anchor moves to historical, new 2026-05-14 allocation-refresh anchor becomes canonical; Protection section MC line updated.
- `README.md`: headline anchor 98.65/0.25/4.69 → 98.78/0.12/4.17; bust attribution updated.
- `analysis/time_to_pass.py`: baseline pass-rate references 98.65% → 98.78%.
- `docs/methodology/regime_robustness_gate.md`: production-pinned anchor line updated; this ADR added as the latest override-with-grounds example.
- `docs/notion/repo_context.md`: anchor pinned-by line updated; allocation note added.
- `data/tv_exports/pepperstone/SHA256SUMS`: regenerated to include `e4dd7` and `da880`.
- `~/.claude/skills/trade-csv-reconcile/references/baselines.md` (skill cache): per-strategy 2026-05-14 metrics for DJ30 variant and NAS100 variant; locked-allocations table updated.

No changes to:
- `dd_protection.py` (C2 constants unchanged).
- OANDA panel CSVs (no OANDA re-export at this point).
- Guardian or Aegis Pine source / CSV / allocation.

---

## Audit hooks

```
# Verify the allocations are still locked
$ grep -A6 "^ALLOCATIONS" portfolio_mc.py
# Expected: striker 0.0075, striker_nas100 0.0045

# Verify the variant CSVs are still wired
$ grep -E "(e4dd7|da880)" portfolio_mc.py
# Expected: two hits — striker and striker_nas100 entries

# Verify the MC anchor pin matches this ADR
$ grep -E "0.9878|0.0012|0.0417" tests/test_mc_anchors.py
# Expected: three hits in test_pepperstone_anchor

# Run the regime-robustness retrospective check (quarterly cadence)
$ python analysis/time_to_pass.py --regime-check
# Expected: pass-rate >= 95% on both recent and prior 6mo windows

# Verify the falsifier hasn't fired (live-PnL edge-captured ratio for DJ30)
$ python analysis/journal_review.py --strategy striker --since 2026-05-14
# Expected: edge_captured_ratio >= 0.70 over >= 30 trades

# Verify no superseding ADR has shipped without back-linking
$ grep -l "Supersedes: 2026-05-14-allocation-refresh" docs/adr/
# Expected: empty (or, if shipped, this ADR's status updated to SUPERSEDED-BY)
```

---

## Open items

1. **DJ30 version designation.** Pyramid 350% → 500% is a Pine-source parameter change. The user-provided CSV filename retains `v4.5`. Two coherent resolutions: (a) bump to v4.6 and author a Pine version-lock ADR; (b) re-document v4.5 as "v4.5 production parameters: risk 0.75%, pyramid 500%" and treat the prior 1.00% / 350% as the lock-cycle transitional config. Defer to next session; status of this ADR does not depend on the choice.
2. **NAS100 variant `da880` pyramid behavior.** The variant CSV has +22% raw Net vs canonical `36258` at unchanged trade selection, suggesting a Pine pyramid edit (or scaled pyramid baseline) in addition to the sizing change. If a Pine pyramid edit is real, NAS100 also faces the version-bump question above.
3. **OANDA re-export at the new allocations.** OANDA panel was not re-exported in this session. The OANDA anchor under new allocations (96.33 / 0.40 / 4.73) is reproducible against the existing 2026-04-25 / 2026-05-08 OANDA panel, but a 2026-05-14 OANDA re-export would close the panel-vintage parity gap. Forward consideration.
4. ~~**`firm_rules.py` / `accounts.py` baseline-risk constants.**~~ **RESOLVED in this same change set.** `firm_rules.py:30` had `_BASE_RISK = {"striker": 0.0100, "striker_nas100": 0.0040}` driving the `cli.py lots` multiplier formula. Updated to `striker: 0.0075, striker_nas100: 0.0045` in this same commit. `accounts.py` consumes `BASELINE_RISK` from `firm_rules.py` so propagation is automatic. `live_journal/scripts/journal_review.py:72-73` `STRATEGIES.risk_pct` also updated (was 1.00 / 0.40). Verified by full test suite green (170 passed, 1 skipped) under the new constants.

---

## Cross-references

- Prior C2 ADR (analogous override pattern): [`docs/adr/2026-05-08-dd-trigger-c2-relock.md`](2026-05-08-dd-trigger-c2-relock.md)
- Regime-robustness gate (this ADR's override target): [`docs/methodology/regime_robustness_gate.md`](../methodology/regime_robustness_gate.md)
- Q-DDP-1 (worked example for override-with-documented-grounds): [`docs/briefs/Q-DDP-1/recommendation.md`](../briefs/Q-DDP-1/recommendation.md)
- NAS100 addition decision audit (diversification thesis): [`docs/briefs/striker_nas100_q_nas_3_mc_addition.md`](../briefs/striker_nas100_q_nas_3_mc_addition.md)
- Code:
  - `portfolio_mc.py` — `ALLOCATIONS` + `PEPPERSTONE_PANELS`
  - `tests/test_mc_anchors.py` — Pepperstone + OANDA pins
  - `dd_protection.py` — `DD_TRIGGER = 0.015`, `DD_SCALE = 0.40` (unchanged)
- MC harness: `portfolio_mc.py` (panel-paths + allocs only; no logic change)
- Forward-trigger instrumentation: `analysis/time_to_pass.py` (`--regime-check` mode, established 2026-05-08)

---

## Verification

```
# 1. MC anchor reproduces
$ python portfolio_mc.py --panel pepperstone
# Expected (tail): Pass: 98.78% / Bust: 0.12% / p99 DD: 4.17% / median 21

$ python portfolio_mc.py --panel oanda
# Expected (tail): Pass: 96.33% / Bust: 0.40% / p99 DD: 4.73% / median 26

# 2. Test pins pass
$ python -m pytest tests/test_mc_anchors.py -v
# Expected: 8 passed

# 3. Full test suite green
$ python -m pytest -q
# Expected: all green (170+ passed, 1 skipped, no failures)

# 4. Manifest integrity
$ python scripts/check_data_manifests.py
# Expected: no output (silent success)

# 5. CLAUDE.md / README / regime_robustness_gate.md / repo_context.md headline anchor consistency
$ grep -l "98.78" CLAUDE.md README.md docs/methodology/regime_robustness_gate.md docs/notion/repo_context.md
# Expected: all four files
```
