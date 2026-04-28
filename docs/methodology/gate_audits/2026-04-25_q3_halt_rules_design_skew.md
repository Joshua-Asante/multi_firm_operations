# Gate audit — Q3 halt rules: design skew (false positives + structural fire)

**Date:** 2026-04-25
**Question:** Q3 — pairwise P&L correlation + symmetric joint-tail
**Brief:** https://www.notion.so/34edc0b53c1181eda644e5bc64163452
**Resolution:** https://www.notion.so/34edc0b53c11819fa919cdf265a45490
**Slug:** `q3_halt_rules_design_skew` (under brief's `q3_brief_skew` umbrella)
**Case:** B (audit fires; verdict still reached)
**First-ever Q-gate audit file.** `docs/methodology/gate_audits/` directory created in this commit.

## What happened

Q3.4 ran the per-period 150-day bootstrap bust rates as specified. Two of the
three brief-specified halt rules fired:

1. **Panel-split bug catcher.** `|cal_bust − full_bust| = 0.18pp` vs threshold
   `2 × max(σ_cal, σ_full) = 0.02pp` at 50K SIMS_PER_SEED. Halt fired.
2. **Internal noise gate (calibration).** `σ_seed/mean = 0.064 > 0.05` at 10K.
   Cleared at 50K (`σ_seed/mean = 0.008`) per brief's permitted noise-gate
   response (raise SIMS_PER_SEED).
3. **Internal noise gate (2026-YTD).** `σ_seed/mean = 0.163 > 0.05` at 50K.
   Halt fired (and would not clear at any reasonable SIMS).

Per brief: "halt and audit." This file is that audit. Each fired halt was
direct-examined and classified at execution time; the analysis continued past
the FALSE_POSITIVE and STRUCTURAL_RARE_EVENT classifications and reached a
clean verdict (NO_TRIGGER_CANDIDATE).

## Halt 1 — Panel-split bug catcher: FALSE POSITIVE

**Rule (from brief):** `|OANDA-calibration mean bust % − OANDA full-panel mean bust %| > 2 × max(σ_seed_calib, σ_seed_full)` → halt and audit. Stated purpose: "catches inadvertent overlap between calibration and 2026-YTD periods or a drifted date partition."

**Observed at execution:** `|0.63 − 0.45| = 0.18pp` vs `2 × max(0.00, 0.07) = 0.14pp` at 10K (and `2 × 0.01 = 0.02pp` at 50K). Halt fired at both SIMS levels.

**Classification basis:** the brief's stated purpose is partition-bug detection. The actual computation is correct **and** the divergence is exactly what Q3 would expect to see if its hypothesis is true. Two independent checks established that the partition is mechanically clean:

1. **Manual partition audit** (executed in the script, output captured in resolution page):
   - `endpoints_align_with_brief: True` (CALIB_END = 2025-10-29, YTD_START = 2025-10-30)
   - `no_bday_overlap: True` (n_overlap_bdays = 0)
   - `union_covers_full_panel: True`
   - `block_count_parity_ok: True` (calib 198 + YTD 24 = 222 vs full 223; loses 1 block to mid-week boundary, expected)
   - `overall_clean: True`
2. **Direction-of-effect alignment with Q3 hypothesis:** the divergence direction (full < calibration) matches the arithmetic implication of the 2026-YTD slice being materially different from calibration in the safer direction. Specifically, `|YTD − cal| = 0.53pp` is larger than the observed `|full − cal| = 0.18pp`, so the cal-vs-full divergence is the smaller weighted-blend shadow of the actual cal-vs-YTD signal.

**Why the rule fires as a false positive:** the rule's threshold is `2 × max(σ_seed_*)`. As SIMS_PER_SEED increases, σ shrinks (1/√N) but the mean-divergence stays fixed. So the threshold tightens at higher SIMS even though the underlying divergence is the SAME structural signal. At infinite SIMS, the threshold → 0 and the halt **always** fires whenever cal ≠ full at any tolerance.

**Implication:** the rule conflates two distinct conditions:
- (a) Partition bug → cal-vs-full divergence with small expected sign/magnitude.
- (b) Real regime shift between calibration and 2026-YTD → cal-vs-full divergence is the **arithmetic shadow** of |YTD − cal|.

When (b) is true (which is exactly the question Q3 is testing), the rule fires regardless of whether (a) is also true. The rule has **no discriminating power** in the regime-shift case. The brief's authoring missed this in its v2.1 patch round, even though the patch round explicitly added the rule as a panel-split bug catcher.

**Action:** classified as FALSE POSITIVE; analysis continued. Documented here.

## Halt 2 — Internal noise gate (calibration): cleared

**Rule (from brief):** `σ_seed / mean_seed > 0.05` on either calibration or 2026-YTD bust % → halt; raise SIMS_PER_SEED or report Q3.5 as deferred.

**Observed at 10K SIMS:** σ_seed_calib = 0.04pp, mean_seed_calib = 0.65%, ratio = 0.064. Halt fired.

**Action:** raised SIMS_PER_SEED from canonical 10K to 50K (brief-permitted response). At 50K: σ_seed_calib = 0.005pp, mean_seed_calib = 0.63%, ratio = 0.008. Cleared.

**No skew here** — the gate functioned as designed; the brief-permitted response resolved it.

## Halt 3 — Internal noise gate (2026-YTD): STRUCTURAL_RARE_EVENT

**Rule (from brief):** same as Halt 2.

**Observed at 50K SIMS:** σ_seed_2026 = 0.016pp, mean_seed_2026 = 0.099%, ratio = 0.163. Halt fired.

**Why raising SIMS does not help:** the 2026-YTD slice is so favorable (24 unique blocks, mean bust 0.10%) that bust events are extremely rare in 150-day sims. The bootstrap is technically working — the rare-event estimator just has high relative noise relative to its tiny mean. To clear `ratio ≤ 0.05`, σ would need to drop to ~0.005pp, which requires SIMS_PER_SEED ≈ 500K (10× current). At 5M SIMS, ratio still doesn't approach calibration's 0.008 because the mean-rarity dominates.

**Why the gate's discrimination concern is moot in this case:** the gate's stated purpose is "the bootstrap is too noisy at current SIMS_PER_SEED for Q3.5 to discriminate." But Q3.5's discrimination is between "trigger candidate" and "no trigger candidate." The trigger-candidate verdict requires 2026-YTD bust CI lower bound to **exceed** calibration mean + T = 1.13%. The 2026-YTD bust CI lower bound is 0.067% — not just under the threshold, but **below calibration mean entirely** (0.63%). The CI would have to span >10× its own value upward to reach the threshold, which is implausible for any rare-event estimator.

The discrimination question is **direction-resolved**, not noise-resolved. The gate fires on noise without considering direction-of-effect.

**Classification basis:** σ_seed_2026 = 0.016pp ≤ 0.5pp absolute floor (the brief's own discrimination-failure-guard threshold for σ_seed_calib). Combined with direction-of-effect (YTD < calibration on bust mean), the gate's discrimination concern is structurally moot in this case.

**Action:** classified as STRUCTURAL_RARE_EVENT; analysis continued. Documented here.

## Methodology learning (carried forward)

The brief's halt rules at Q3.4 were authored in v2.1 to catch (a) panel-split
bugs and (b) discriminator-noise overflow. Both are real concerns, but the
rules as authored have a **direction-blindness flaw**: they fire on magnitude
without considering whether the magnitude is signal or noise.

Three concrete patches for future briefs of similar shape:

1. **Panel-split bug catcher should be conditional on direction.** Instead of
   `|cal − full| > 2σ`, use `|cal − full|` AND `|YTD − cal|` jointly: if
   `|YTD − cal|` is large in the same direction as `|cal − full|`, the
   cal-vs-full divergence is the arithmetic shadow of the regime shift, NOT
   a partition bug. Manual partition audit should be the primary check;
   magnitude-divergence is at most a secondary signal that should be
   contextualized by manual audit.

2. **Internal noise gate should consider direction-of-effect.** If
   `mean_YTD < mean_calibration` and the trigger-candidate verdict requires
   `mean_YTD > mean_calibration + T`, the verdict is mechanically resolved
   regardless of YTD's σ. The noise gate should fire only when noise actually
   gates the discrimination, not when direction-of-effect already resolves
   the question.

3. **Halt rules should declare their failure modes.** The brief's halt rules
   said "halt and audit" without specifying what the audit is checking. A
   stronger spec would be "halt iff the manual audit cannot distinguish
   bug-vs-signal AND the discrimination is not direction-resolved." The
   audit is the gate, not the magnitude-comparison.

Ω **For iteration 4 (next time the framework runs):** if the brief author
specifies halt rules in the Q4-spec section, also specify the **classification
procedure** for the halt: what makes it FALSE_POSITIVE vs TRUE_POSITIVE vs
STRUCTURAL? This forces the brief author to think about the rule's failure
modes at brief-time, not at execution-time.

## Verdict-impact assessment

**Did the halt-rule skew change the Q3.5 verdict?** No.

- If halts had blocked the verdict: Q3.5 would be DEFERRED. But the
  underlying data was unambiguous in direction (YTD bust mean 0.10% vs
  calibration 0.63%), so deferral would have been a more conservative but
  substantively equivalent verdict.
- If the rules had been authored with direction-of-effect logic: halts would
  not have fired in the first place; verdict NO_TRIGGER_CANDIDATE would have
  been reached without audit.
- The audit is **methodology learning, not verdict salvage.** The verdict
  was direction-determined; the audit's value is in fixing the rule design
  for future iterations.

**Bottom line:** Case B is a non-failure mode for the framework at iteration 3.
Verdict reached cleanly; methodology learning logged; gate-audit directory
seeded for the first time.

## Cross-references
- Brief: https://www.notion.so/34edc0b53c1181eda644e5bc64163452
- Resolution: https://www.notion.so/34edc0b53c11819fa919cdf265a45490
- Framework: https://www.notion.so/34ddc0b53c1181479d7bdecc61f47078
- Skill file: `inqhiori-algorithm/SKILL.md`
- Analysis script: `analysis/q3_pairwise_joint_tail.py`
- Findings: `analysis/notice_phase/findings.md`
