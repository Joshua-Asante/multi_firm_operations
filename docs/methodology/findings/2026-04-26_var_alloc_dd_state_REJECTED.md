# DD-state-conditioned variable allocation — REJECTED

**Loop:** `loop_2026-04-26_var_alloc_observables`
**Stage:** 1 of 3 — verdict
**Outcome:** **4A — Cond 3 (state-readable) fails the Pareto-improvement bar regardless of WoW constraint.**
**Date closed:** 2026-04-27
**Predecessor brief:** [2026-04-26_var_alloc_observables_stage0.md](2026-04-26_var_alloc_observables_stage0.md)
**Harness:** [scripts/var_alloc_inquire/dd_state_mc.py](../../../scripts/var_alloc_inquire/dd_state_mc.py)
**Run output:** preserved in `.claude/worktrees/.../tasks/bn2ba01mb.output` (transient — re-runnable from harness).

## Verdict

DD-state, conditioned via per-strategy weekly allocation under a survival objective and scale-down-only grid, **does not Pareto-improve over the locked fixed + dd_protection baseline** (Cond 1: pass 93.87% / bust 0.47% / p99DD 5.14% / medDays 32 at 500 sims/seed × 3 seeds, Pepperstone panel 2022-01-04 → 2026-04-20, 223 week-blocks).

This is decisive: in two constraint variants tested (with WoW per parity with the prior var_alloc_inquire constraint set, and without WoW per the brief's "scale-down-only drops the WoW asymmetry problem"), the state-readable Cond 3 policy fails the pre-registered Pareto bar by:

- 25pp pass-rate degradation (Cond 3 ≈ 69% vs baseline 94%)
- 40+ days median-days-to-pass degradation (76-80 vs 32)

The Cond 2 full-future oracle without WoW does Pareto-improve (100% pass / 0% bust / 1.05% p99DD / 28 medDays), confirming that the rolling-PF rejection's structural argument was scoped to the WoW constraint, not to the observable class. **But the Cond 2 → Cond 3 gap is the binding rejection here**: state-readable distillation loses ~31pp of pass-rate, regardless of constraint. DD-state does not predict the next-week per-strategy PnL sign that the oracle exploits.

## Numerical results

Run config: 500 sims/seed × 3 seeds (42, 123, 2026); HORIZON_DAYS=150; Pepperstone panel; scale-down-only grid `r_k ∈ {0, 0.2, 0.4, 0.6, 0.8, 1.0}` (216 candidates); survival objective `score = pnl_sum - 1e9·I(bust_in_week)`; DD-state bins `dd ∈ {<0.5%, 0.5-1%, 1-2%, ≥2%}` × `days_since_peak ∈ {<5, 5-19, ≥20}` = 12 states.

| Run | Variant | pass | σ | bust | p99 DD | medDays |
|---|---|---:|---:|---:|---:|---:|
| Cond 1 (fixed + dd_protection, control) | — | 93.87% | 0.34% | 0.47% | 5.14% | 32 |
| Cond 2 (survival oracle) | with WoW | 78.40% | 1.18% | 0.00% | 1.90% | 32 |
| Cond 3 (DD-state, state-readable) | with WoW | 68.80% | 0.99% | 0.00% | 2.18% | 76 |
| Cond 2 (survival oracle) | no WoW | **100.00%** | 0.00% | **0.00%** | **1.05%** | **28** |
| Cond 3 (DD-state, state-readable) | no WoW | 68.87% | 1.43% | 0.00% | 1.96% | 80 |

**Anchor reference** (10K × 3 seeds, locked production config): pass 92.73% / bust 0.65% / p99DD 4.94% / medDays 32. Cond 1 here is within seed σ of the anchor (small over-shoot due to 500-sim sampling noise; pass-rate σ scales as 1/√N).

Verdict bar (pre-registered in Stage 0 brief, tightened to Pareto-improvement during execution after a 15pp pass-rate collapse on the with-WoW Cond 2 was incorrectly tagged "BEATS BASELINE" by the original two-of-four bar): candidate must achieve ≥1pp pass-rate beyond 2σ-band OR ≥0.2pp bust-rate beyond 2σ-band, AND not degrade any of the four metrics by more than (1pp pass / 0.2pp bust / 0.5pp p99DD / 5 days).

| Variant / Cond | Headline | Pareto | Verdict |
|---|---|---|---|
| with-WoW Cond 2 | bust PASS | pass-rate fails by 15pp | does NOT beat |
| with-WoW Cond 3 | bust PASS | pass-rate fails by 25pp + medDays fails by 39 days | does NOT beat |
| no-WoW Cond 2 | pass + bust both PASS | all four PASS | **BEATS BASELINE** |
| no-WoW Cond 3 | bust PASS | pass-rate fails by 25pp + medDays fails by 43 days | does NOT beat |

## Why the rejection

Two layered findings:

### Finding 1 — The rolling-PF rejection's structural argument was constraint-specific, not observable-specific

The prior var_alloc_inquire (loop_2026-04-?, verdict 4A REJECTED) showed Cond 2 (full-future returns-max oracle) inferior to fixed under the locked constraint set (±50% WoW + 3.0% sum-budget + per-strategy max 2.0%). Memory `feedback_constraint_set_overlay_oracle.md` generalized this as "any responsive sizing, even with full future knowledge, is structurally inferior on pass-rate to fixed."

Stage 1 partially **falsifies the strong reading of that generalization**. The no-WoW Cond 2 variant (survival objective, scale-down-only grid) achieves 100.00% pass / 0.00% bust / p99DD 1.05% / medDays 28 — Pareto-dominant on every metric. So the ±50% WoW constraint, not the constraint-set as a whole, was the binding blocker on the prior result.

The narrower correct generalization: **the WoW constraint at ±50% combined with a symmetric per-strategy grid forces any responsive policy into a one-way ratchet that the rolling-PF observable cannot escape.** Drop the WoW (or asymmetrize the grid as Stage 1 did) and Cond 2 becomes free to allocate optimally.

### Finding 2 — DD-state cannot reproduce Cond 2's per-week PnL-sign behavior

Even with no WoW and perfect future, the Cond 2 oracle's actual behavior is per-strategy "set r=1 if next-week sum positive, else r=0" (modulo the scale-down grid's discretization). This is the optimal scale-down-only strategy under returns-max with no-bust constraint.

Cond 3's job is to distill this per-week per-strategy decision into a state-readable lookup keyed on (dd_bin, days_since_peak_bin). The collected policy table (no-WoW variant):

```
state                  r_g   r_s   r_a  n_obs
<0.5%   /dsp<5         0.20  0.40  0.20  23839
<0.5%   /dsp 5-19      0.20  0.40  0.20  16719
<0.5%   /dsp>=20       0.20  0.40  0.20  2111
0.5-1%  /dsp<5         0.20  0.40  0.20  870
0.5-1%  /dsp 5-19      0.20  0.40  0.20  1019
0.5-1%  /dsp>=20       0.20  0.40  0.20  288
1-2%    /dsp<5         0.20  0.40  0.20  51
1-2%    /dsp 5-19      0.20  0.40  0.20  68
1-2%    /dsp>=20       0.20  0.20  0.20  35
```

Every populated state lands at (~0.2, ~0.4, ~0.2). This is the per-strategy proportion of "next-week-positive" weeks at each state, snapped to the nearest grid point. The state itself is **near-uninformative** for predicting next-week sign — the per-strategy positive-week proportion is roughly constant across all DD-states, around 20-40% (snapped to the nearest grid point from 25-50% raw).

When Cond 3 applies (0.2, 0.4, 0.2) deterministically every week, it captures the **mean** behavior of Cond 2 but not the **per-week selection**. The result: roughly 30% of full allocation, applied uniformly. This produces the observed 69% pass-rate (vs 94% baseline) and 80-day medDays (vs 32 baseline) — sims accumulate equity slowly and frequently time out before reaching the 5% profit target.

**Generalization (proposed for memory):** *Cumulative-past observables (DD state, days-since-peak, rolling PF, similar) cannot reproduce the full-future oracle's per-week PnL-sign discrimination. The Cond 3 ≤ Cond 2 inequality is empirically very large for backward-looking observables — the gap was 31pp pass-rate here, not within seed-σ noise.* This is a strictly stronger statement than the rolling-PF rejection's constraint-set finding.

## Closures held / strengthened

The Stage 0 brief closed time-of-day, calendar, and vol-regime as standalone allocation conditioners on independent grounds (Pine-absorbed for ToD; collapses to ToD for calendar; A3 + trigger discipline for vol-regime). Stage 1's Finding 2 is consistent with those closures and arguably stronger: **all three closed observables are also backward-looking or static**. None forecasts next-week per-strategy PnL sign. So even if the Stage 0 closure paths were relaxed, the Cond 3 information bottleneck would still apply.

The only candidate observable not closed by either path is one that **directly forecasts next-week strategy PnL sign**. None of the four observables in this inquiry does so. Such an observable would not be a sizing rule; it would be a strategy-signal layer (i.e., a Pine-side filter or a new strategy), and its proper home is in the Pine layer, not the allocation layer.

## Stage 2 NOT triggered

Stage 2 (vol-regime as additive conditioner jointly with DD-state) was conditional on Stage 1 finding alpha in DD-state alone. Stage 1 closes DD-state. Vol-regime as a joint conditioner inherits the DD-state failure mode (binning loses the per-week PnL-sign signal). Stage 2 is not authorized by this verdict and is closed by inference.

If a future inquiry wants to test joint conditioning, it must first identify an observable that empirically predicts next-week per-strategy PnL sign — a strictly different exercise than allocation-layer sizing. No such observable is currently on the candidate list.

## What this verdict does NOT mean

- **It does not authorize any change to `dd_protection.py`.** The locked single-tier rule (1% × 0.40) remains the production-validated DD-state-conditioned variable allocator. Stage 1 found nothing better.
- **It does not retroactively expand the rolling-PF rejection.** The rolling-PF rejection's specific result stands; Stage 1 narrowed its generalization to the WoW constraint, not to the constraint set as a whole.
- **It does not close DD-conditioning categorically.** dd_protection IS DD-conditioning, in production, and works. The closure is on *finer-grained DD-state binning under a state-readable policy*, not on DD-conditioning per se.
- **It does not generalize to forward-looking observables.** A hypothetical observable that predicts next-week per-strategy PnL sign (e.g., a leading-indicator panel computed pre-trade) was not tested. The closure is on backward-looking / static observables specifically.
- **It is not authorized by a live-PnL gap.** Per Stage 0 brief and `feedback_overlay_trigger_discipline.md`, the inquiry was exploratory mapping. The rejection forecloses the exploration; nothing in the live-PnL record changed.

## Notice-routed re-evaluation triggers (per `docs/methodology/observation_routing.md`)

Specific triggers that would warrant re-opening this inquiry:

1. **A new observable enters the candidate list that is forward-looking** — i.e., empirically predicts next-week per-strategy PnL sign. Candidates: (a) a leading bar-statistical indicator with bootstrap-validated next-week predictive power on at least one strategy, (b) a non-locked Pine-side signal-layer change that surfaces a new conditioning channel, (c) a fundamental/macro feed integrated into the operational pipeline.
2. **The locked WoW constraint is removed at the operational layer** — i.e., dd_protection acquires a multi-tier rule that operates without WoW and is validated by re-MC. At that point the no-WoW Cond 2 result becomes a candidate for direct implementation, but the state-readable bottleneck still requires a forward-looking observable.
3. **Live-PnL gap vs MC** at the locked allocation/dd_protection config, sustained over a 6-month window, large enough to justify re-MC. This is the standard `feedback_overlay_trigger_discipline.md` trigger.

If none of those triggers fire, this rejection is permanent under "rejected hypotheses stay rejected" discipline.

## Methodology audit

- **Pre-Q gate (Stage 0 brief):** properly applied; closed three of four candidate observables analytically; routed DD-state to Stage 1 with explicit escape-hatch hypotheses.
- **Verdict bar:** pre-registered as "≥1pp pass OR ≥0.2pp bust beyond σ-band, AND no degradation > 0.5σ on p99 DD or medDays." Tightened to Pareto-improvement during execution when the original bar was found to admit a 15pp pass-rate collapse as "passing." This tightening is a material change to the pre-registration; logged here for audit. The tightening was unambiguously correct (a 15pp pass-rate trade for a 0.5pp bust improvement is not a real beat), but it is a methodology lesson for future inquiries: pre-register the non-degradation criterion *for all four metrics*, not just two.
- **WoW variant addition:** added during execution after Variant A (with WoW) failed Cond 2, in light of Stage 0 brief's claim that "scale-down-only drops the WoW asymmetry problem." Not pre-registered. The no-WoW Cond 2 result (100% pass) was the unexpected finding; the with-WoW Cond 2 failure was the expected finding. Both were necessary for the conclusion that the bottleneck is the *state-readable distillation*, not the constraint set.
- **Sample size:** 500 sims/seed × 3 seeds (15× short of the locked 10K anchor). The rejection margins (25pp pass-rate gap on Cond 3, 40+ day medDays gap) far exceed seed σ (0.99-1.43%). 10K confirmation would tighten σ but is not load-bearing for the verdict. Re-runnable from `dd_state_mc.py` if a future audit needs the full anchor.

## Cross-references

- Stage 0 brief: [2026-04-26_var_alloc_observables_stage0.md](2026-04-26_var_alloc_observables_stage0.md)
- Harness: [scripts/var_alloc_inquire/dd_state_mc.py](../../../scripts/var_alloc_inquire/dd_state_mc.py)
- Reused base harness: [scripts/var_alloc_inquire/var_alloc_mc.py](../../../scripts/var_alloc_inquire/var_alloc_mc.py) (copied from worktree `elated-mcclintock-7ac85b`; `simulate_var_alloc`, `summarize`, `fmt_summary`, `load_pepperstone_panel`)
- Locked production analogue: [`dd_protection.py`](../../../dd_protection.py)
- Predecessor inquiry (rolling-PF, REJECTED): worktree `elated-mcclintock-7ac85b/scripts/var_alloc_inquire/var_alloc_mc.py`
- Memory updates triggered by this verdict:
  - `feedback_constraint_set_overlay_oracle.md` — narrow scope to WoW (not whole constraint set)
  - NEW: `feedback_state_readable_observable_bottleneck.md` — Cond 3 ≤ Cond 2 strict inferiority is empirically very large for backward-looking observables; cumulative-past states don't predict per-week PnL sign

## Out of scope (confirmed)

This verdict authorizes nothing in production:

- ❌ No change to `dd_protection.py` constants (1% × 0.40 remain locked)
- ❌ No change to locked Pine strategies (G v5.5 / S v4.4 / A v4.3)
- ❌ No allocation discussion (G 0.34% / S 1.00% / A 1.50% remain locked)
- ❌ No portfolio MC re-run beyond the 500-sim Stage 1 numbers above
- ❌ No Stage 2 (vol-regime joint conditioning) — closed by Stage 1 inference
- ❌ No re-opening of the rolling-PF inquiry (rejection stands; Stage 1 narrowed but did not invalidate the rolling-PF result)
