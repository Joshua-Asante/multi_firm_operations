# Variable allocation conditioned on non-PF observables — Stage 0 brief

**Loop:** `loop_2026-04-26_var_alloc_observables`
**Stage:** 0 of 3 — methodology gate (no code, no MC runs)
**Date opened:** 2026-04-26
**Predecessor:** `loop_2026-04-?_var_alloc_inquire` — verdict 4A REJECTED (rolling-PF as conditioner). See worktree `elated-mcclintock-7ac85b/scripts/var_alloc_inquire/var_alloc_mc.py` for the harness; memory `feedback_constraint_set_overlay_oracle.md` for the structural finding.

## The question

Does any observable other than rolling profit-factor — specifically vol regime, drawdown state, time-of-day, or calendar — admit a per-strategy weekly allocation policy that beats fixed allocation under the locked constraint set, on the four-metric verdict bar (pass%, bust%, p99 DD, median days-to-pass)?

## Structural pre-Q gate (the Cond 2 generalization argument)

The prior var_alloc_inquire harness implemented a three-tier oracle test:

- **Cond 1 (control):** fixed locked allocation [1, 1, 1].
- **Cond 2 (full-future oracle):** at each week, picks the per-strategy ratio vector from a constrained grid that maximizes next-week portfolio PnL given perfect knowledge of the next-week PnL block.
- **Cond 3 (state-readable):** at each week, looks up a ratio vector from a policy table keyed on rolling-PF state observed at week start; the policy table is itself optimized from the Cond 2 traces by binning (PF state → mean optimal ratio).

Constraints: per-strategy `r_k * locked_k ≤ 2.0%`, sum `0.34*rg + 1.00*rs + 1.50*ra ≤ 3.0%`, week-over-week `|Δr|/r ≤ 0.5`. Objective in Cond 2: returns-max (`week_strat_sums · r`).

**The result:** Cond 2 was inferior to Cond 1 (fixed) on pass-rate. Cond 3 was strictly weaker than its Cond 2 generator.

**The generalization:** Cond 2 is observable-AGNOSTIC — it sees future PnL directly, not via any state observable. So the rolling-PF rejection was not really *about* rolling PF: it was about the constraint-set-plus-objective combination making a constrained-future oracle inferior to fixed. **No state-readable Cond 3 (whatever the observable) can outperform its own Cond 2 generator under the same constraint set + objective.** Ergo, no observable-conditioned policy beats fixed under those conditions.

The argument has exactly two escape hatches:

1. **Different objective.** If Cond 2 maximizes survival (e.g., bust-rate-min, p99-DD-min, or a survival-weighted composite) instead of returns, the inferior-to-fixed result no longer applies — that result was specific to the returns-max objective. Existence proof for survival-objective allocation conditioning working: `dd_protection.py` is in production, locked 2026-04-17, and was validated by 10K-sim MC at 92.73% pass / 0.65% bust. It is itself a one-bin DD-state-conditioned variable allocator.

2. **Asymmetric constraint shape.** A "scale-down only" policy grid (`r_k ∈ [0, 1]`) sidesteps the symmetric WoW-budget trap that the rolling-PF Cond 2 oracle fell into. The binding constraint becomes one-sided.

The Stage 1 question is whether DD-state, threading both escape hatches, can clear the verdict bar. Stage 0 must close the other three observables analytically — which it does below.

## Closures

### Closure 1: Time-of-day / day-of-week — Closed

ToD acts on trade gating, not allocation, and is already absorbed by locked Pine filters:

- **Guardian v5.5**: `blockMonH08`, `blockMonH09`, `blockH12` (all-days), `blockH12Day` latch.
- **Aegis v4.3**: session selection per [`docs/adr/2026-03-01-aegis-session-selection.md`](../../adr/2026-03-01-aegis-session-selection.md).

Re-introducing ToD at the allocation layer would double-count an already-locked filter: the Pine layer has already removed every signal the strategies don't want, so the allocation layer would be conditioning on what's already absent. There is no second layer to add.

If a future ToD pattern were discovered that the Pine filters miss, the correct path is a Pine-side filter update (which requires version-bump and re-MC), not an allocation overlay. **Closed; no Stage 1 entry.**

### Closure 2: Calendar / event-time (NFP, FOMC, RBA, ECB, etc.) — Closed

Calendar conditioning is deterministic on date — there is no observable state to learn; the rule reduces to a static date filter. Static date filters are properly Pine-side (alongside ToD blocks) for the same reason as Closure 1: they remove signals at the trade-gate layer, not the sizing layer. Calendar conditioning at the allocation layer collapses analytically to ToD (with a calendar-specific date mask), which Closure 1 already covers.

The methodology gate also fires here from a different direction: per `feedback_overlay_trigger_discipline.md`, allocation rules require a live-PnL gap vs MC. No such gap has been observed around macro-event dates in the live trading record. **Closed; no Stage 1 entry.**

### Closure 3: Volatility regime (ATR percentile, realized-vol bucket) — Closed (doubly determined)

Two independent paths close vol-regime as a standalone allocation conditioner:

**Path A — already absorbed.** Per [`analysis/notice_phase/findings.md` A3 (lines 21-32)](../../../analysis/notice_phase/findings.md):

> Pine-style `ta.atr(14)` on 15-min XAUUSD bars across 2022–2026 YTD shows the RMA-smoothed ATR(14) sat within 0.6% of the contemporaneous mean bar range in every year, including the ~5× regime jump from 2024 (mean ATR $2.95) to 2026 YTD (mean ATR $15.31). [...] Vol-regime overlay was already closed by ATR-based sizing locked in Guardian v5.5; A3 re-confirms the auto-sizing argument at the bar-data level.

The Pine strategies auto-resize per contemporaneous ATR. Vol-regime conditioning at the allocation layer would re-encode what the Pine layer already does — same double-counting failure mode as Closure 1.

**Path B — trigger-discipline rejection.** Vol regime is the canonical "physical-fact / bar-statistical" overlay pattern that `feedback_overlay_trigger_discipline.md` rejects without a live-PnL gap. The Iran/Hormuz overlay (deactivated 2026-04-23) is the worked example of this failure mode: a physical-regime story without a live-PnL gap produced a removable overlay. Closing vol-regime by the same generalization is consistent.

**Stage 2 carve-out:** vol-regime as an *additive* conditioner *jointly with DD-state* is not closed by either path above. Path A speaks to standalone vol-regime conditioning at the allocation layer; a joint DD×vol policy that uses vol only when DD-state has fired could in principle add information that the Pine ATR sizing does not capture (e.g., a high-vol week amplifies the dd-state response). Stage 2 is gated on Stage 1 finding alpha in DD-state alone; if Stage 1 closes, Stage 2 does not run.

**Closed as standalone; Stage 2 conditional on Stage 1 outcome.**

### Stage 1 candidate: Drawdown state — open, with escape hatches

DD-state is the only candidate that threads both escape hatches above:

1. **Survival-objective production analogue:** `dd_protection.py` (1% trigger × 0.40 scale, locked 2026-04-17, MC 92.73% pass / 0.65% bust at the locked allocation). DD-state-conditioned allocation under a survival objective IS in production and IS validated. Stage 1 asks the narrower question of whether a *finer* DD-state binning (current DD bucket × days-since-peak bucket, scale-down-only) beats the existing single-tier rule.

2. **Scale-down-only grid:** `r_k ∈ {0, 0.25, 0.40, 0.60, 0.80, 1.0}`. Never amplifies above locked. The WoW asymmetry that killed the rolling-PF Cond 2 oracle does not apply.

3. **Zero new infra:** `simulate_var_alloc` already computes `dd_from_peak` per day at `var_alloc_mc.py:100`. Days-since-peak is one running counter on top.

**Stage 1 verdict bar (pre-registered):**
- Cond 2 (survival oracle, scale-down-only grid) must beat **fixed + current dd_protection** (the existing 1% × 0.40 single-tier rule, NOT fixed alone) by:
  - ≥1pp pass-rate beyond seed σ-band, OR
  - ≥0.2pp bust-rate reduction beyond seed σ-band,
  - AND no degradation > 0.5σ on p99 DD or median days-to-pass.
- Cond 3 (state-readable lookup) must clear the same bar AND its outcome must exceed Cond 2 by less than 3σ-band (Cond 3 ≥ Cond 2 outcomes are sampling noise — the harness's one-step look-ahead has nothing to overfit at 10K × 3 seeds).
- Cond 3 policy table must be non-degenerate: must NOT trivially recover the existing (1% DD → 0.40, else 1.0) rule with rounding.

If Cond 2 fails the bar → DD-state is closed → all four observables become a generalized rejection. Stage 2 does not run. Memory update: extend `feedback_constraint_set_overlay_oracle.md` to cover survival-objective + scale-down-only, not just returns-max + symmetric WoW.

If Cond 2 passes but Cond 3 fails → there is alpha in DD-conditioning under survival objective, but it is not state-readable. Document the gap; treat any richer-observable extension (e.g., adding consecutive-loss streak) as a separate inquiry, not part of this loop.

If Cond 2 and Cond 3 both pass → Cond 3 policy becomes a *candidate* sizing rule. Production change requires a Notion FINAL decision page and Joshua's review per the locked-constants discipline (`dd_protection.py:113-116`). The harness output alone does not authorize a constants change.

## Stage 0 verdict — gate fires open

The Cond 2 generalization argument closes ToD, calendar, and vol-regime (standalone). DD-state passes the gate to Stage 1 because both escape hatches are defensible (production analogue + asymmetric grid) and the harness needs no new infra to run.

**Routing:** Stage 1 authorized. Closures 1–3 are committed independently of the Stage 1 outcome — even if Stage 1 unexpectedly resurrected a vol-regime question, the standalone vol-regime overlay is closed; only joint dd×vol (Stage 2) is downstream-conditional.

## What this verdict does NOT mean

- **It does not retroactively re-open the rolling-PF rejection.** Rolling PF was correctly rejected under returns-max + symmetric grid, and Stage 1 does not re-test it under different objectives. The rolling-PF rejection's load-bearing fact is the original Cond 2 result; that fact stands.
- **It does not authorize any code change to `dd_protection.py`.** Stage 1 produces a candidate proposal at most. The locked-constants discipline gates production changes.
- **It does not authorize any change to Pine strategies** (locked v5.5 / v4.4 / v4.3).
- **It does not generalize the closures to any future observable.** A novel observable not on the four-candidate list (e.g., consecutive-loss streak, cross-strategy-correlation regime, equity-curve smoothness) would need its own Stage 0 routing — it is not pre-closed by this brief.
- **It is not authorized by a live-PnL gap.** Per `feedback_overlay_trigger_discipline.md`, this entire inquiry is in *exploratory mapping* mode, not overlay-proposal mode. Even a Stage 1 pass produces only a candidate proposal, not a deployable change. A live-PnL gap would be required for production deployment beyond what dd_protection already covers.

## Out of scope (confirmed)

- ❌ No Pine Script implementation work
- ❌ No change to locked production parameters
- ❌ No change to `dd_protection.py` constants from Stage 1 alone
- ❌ No modification of the prior var_alloc_inquire artifact in worktree `elated-mcclintock-7ac85b`
- ❌ No allocation discussion outside the staged framework (G 0.34% / S 1.00% / A 1.50% remain locked)

## Cross-references

- Predecessor inquiry harness: `.claude/worktrees/elated-mcclintock-7ac85b/scripts/var_alloc_inquire/var_alloc_mc.py`
- Locked DD protection: [`dd_protection.py`](../../../dd_protection.py) (lines 1-7 lock notes, 145-154 MVD pin)
- Vol-regime A3 finding: [`analysis/notice_phase/findings.md:21-32`](../../../analysis/notice_phase/findings.md)
- Observation routing: [`docs/methodology/observation_routing.md`](../observation_routing.md) (three-bucket gate)
- Aegis ToD selection: [`docs/adr/2026-03-01-aegis-session-selection.md`](../../adr/2026-03-01-aegis-session-selection.md)
- Memory: `feedback_constraint_set_overlay_oracle.md` (rolling-PF rejection structural fact), `feedback_overlay_trigger_discipline.md` (live-PnL-gap requirement), `feedback_three_tier_oracle_test.md` (oracle test as standard instrument), `feedback_two_tier_canonical_pepperstone_oanda.md` (Pepperstone authoritative for verdict-bar MC)

## Stage transitions

- **Stage 0 → Stage 1:** authorized as of this brief (DD-state passes gate).
- **Stage 1 → Stage 2:** conditional on Cond 2 + Cond 3 both passing the verdict bar AND the Cond 3 policy being non-degenerate.
- **Stage 1 → REJECTED:** if Cond 2 fails the verdict bar against fixed+dd_protection.
- **Stage 1 → DOCUMENTED-GAP:** if Cond 2 passes but Cond 3 fails (alpha exists but is not state-readable from DD-state alone).

Verdict files for downstream stages will be siblings to this file: `2026-04-26_var_alloc_dd_state_*.md` and `2026-04-26_var_alloc_dd_vol_*.md`.
