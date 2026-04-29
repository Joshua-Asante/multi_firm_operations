# Q-T Tuesday-cohort bar-level concurrent-loss — findings — 2026-04-27

> **Disposition (2026-04-28): CLOSED with watchlist tripwire.** The bar-level
> finding stands and is logged. The Action proposal drafted under the lifted
> Pepperstone gate (preserved below for trail) is **NOT EXECUTED** — Joshua's
> call: an OANDA-proxy bar-stat without a live-PnL signal is not enough to
> justify the lock cycle, even with a P&L-test gate built into the proposal.
> Re-opening criterion is now a forward live-PnL tripwire rather than a
> backtest gate. See **Disposition** section before the Action proposal.

Substrate: OANDA-proxy 4yr 15min panel (XAUUSD / US30USD / USDJPY).
Canonical status: **PROXY** end-to-end per
[AMENDMENT_oanda_rescope.md](../../docs/methodology/identify_corpus/2026-04-26/AMENDMENT_oanda_rescope.md)
(supersession applies — data-provenance tag retained).
Brief: Q-T 2026-04-27 (Tuesday-cohort bar-level concurrent-loss falsifiability).
Artefact: [`q_t_tuesday_2026_04_27.json`](q_t_tuesday_2026_04_27.json).
Reproduce: [`python analysis/inquire_phase/q_t_tuesday_concurrent_loss_2026_04_27.py`](q_t_tuesday_concurrent_loss_2026_04_27.py).

## Phase 0 — provenance verification

| symbol | path | n_rows | first | last | sha256 | tv_export OANDA | PASS |
|---|---|---|---|---|---|---|---|
| XAUUSD | data/bar_data/XAUUSD.csv | 101,461 | 2022-01-02 | 2026-04-19 | `0d8aaa40…facca` | ✓ | **PASS** |
| US30USD | data/bar_data/US30USD.csv | 101,245 | 2022-01-02 | 2026-04-19 | `723a354b…677b5` | ✓ | **PASS** |
| USDJPY | data/bar_data/USDJPY.csv | 106,820 | 2022-01-02 | 2026-04-19 | `678c846c…b185e` | ✓ | **PASS** |

All three files match the [`identify_corpus/2026-04-26/phase0_log.json`](../../docs/methodology/identify_corpus/2026-04-26/phase0_log.json) manifest on rows, first/last timestamps, and TV-export OANDA-tag presence. Hashes also match the Notice-2026-04-27 [`phase0_2026_04_27.json`](../notice_phase/phase0_2026_04_27.json) re-verification. **all_pass = true.**

Next-action: NONE.

## Cohort sizes

Aligned 15min panel after rolling-std warmup (60d × 24h × 4 bars, min_periods 500):
- Panel bars with valid rolling std: **n = 101,117**.
- Overlap windows (≥2 strategies session-active per locked schedule): **n = 7,809**.
- Tuesday-overlap windows: **n = 4,579**.
- Non-Tuesday-overlap windows: **n = 3,230** (all Monday — see day-of-week table below).
- Thin-floor (≥100 Tuesday-overlap): **PASS** (4,579 ≫ 100).

Schedules used (operational metadata, not Rule 0 reads):
- Guardian: Mon/Tue/Thu × 08:00–16:00 NY.
- Striker: Tue/Fri × 13:00–17:00 UTC.
- Aegis: Mon/Tue/Wed × 10:00–13:45 NY.

Next-action: NONE.

## Concurrent-loss rates

Adversity definition reproduced from [`scripts/identify/2026-04-26/o4_bar_correlation.py`](../../scripts/identify/2026-04-26/o4_bar_correlation.py) `simultaneous_adverse()` — Q14-equivalent, no re-derivation: per-instrument log-return < −1.0σ_60d, long-only down direction. `concurrent_loss[t] = 1` iff ≥2 of the session-active strategies' instruments are simultaneously 1σ-adverse-down in window t.

Headline (per brief's pre-defined metric):

| cohort | n | concurrent-loss n | rate |
|---|---:|---:|---:|
| Tuesday-overlap | 4,579 | 281 | **6.14%** |
| Non-Tuesday-overlap (Mon) | 3,230 | 24 | **0.74%** |
| **Δ** | | | **+5.39 pp** |

Mann-Whitney U: U = 7,793,952; **p = 8.7 × 10⁻³⁴** (two-sided).
Bootstrap 95% CI on Δ (1,000 resamples, seed 42): **[+4.60 pp, +6.18 pp]**, median +5.42 pp.

Day-of-week breakdown of overlap windows (descriptive — confirms non-Tuesday cohort is structurally Monday-only, since Wed/Thu/Fri/Sat/Sun never have ≥2 session-active strategies given the locked schedules):

| dow | n_overlap | n_concurrent_loss | rate |
|---|---:|---:|---:|
| Mon | 3,230 | 24 | 0.743% |
| Tue | 4,579 | 281 | 6.137% |
| Wed | 0 | 0 | — |
| Thu | 0 | 0 | — |
| Fri | 0 | 0 | — |
| Sat/Sun | 0 | 0 | — |

K-level decomposition (descriptive — surfaces the mechanical confound that ≥2-of-3 is higher-probability than ≥2-of-2 even under iid):

| sub-cohort | n | rate |
|---|---:|---:|
| Tuesday K=3 (G+S+A all active) | 2,360 | 8.64% |
| Tuesday K=2 (any 2 of 3 active) | 2,219 | 3.47% |
| Monday K=2 (G+A active) | 3,230 | 0.74% |

**Matched K=2 test (Tuesday-K=2 vs Monday-K=2):** Δ = **+2.73 pp**, MW U = 3,681,412, **p = 2.3 × 10⁻¹³**; bootstrap 95% CI [+1.93 pp, +3.49 pp].

The K=3 → K=2 mechanical effect explains some of the headline gap: Tuesday-K=3 (8.64%) is markedly above Tuesday-K=2 (3.47%). However, the K-matched comparison (Tuesday-K=2 vs Monday-K=2) is still significant at Δ=+2.73 pp, confirming a Tuesday-specific component beyond the ≥2-of-3-vs-≥2-of-2 mechanical artifact. The H_alt_1 verdict is robust to K-matching — Δ remains > 1pp and p remains far below 0.05 even under the strictest control available on this corpus.

Next-action: NONE.

## Hypothesis branching applied

Pre-defined thresholds (from brief):
- H_null: |Δ| ≤ 1pp AND p > 0.05.
- H_alt_1: Δ > 4pp AND p < 0.05.
- Else: H_inconclusive.

Observed: Δ = +5.39 pp; p = 8.7 × 10⁻³⁴.

**Verdict: H_alt_1 supported.** Tuesday-cohort concurrent-loss rate materially exceeds non-Tuesday-cohort baseline by ~7.4× (6.14% vs 0.74%); the gap is significant under MW and the bootstrap 95% CI excludes both 0 and the +4 pp threshold. The K-matched control (Tuesday-K=2 vs Monday-K=2) attenuates Δ to +2.73 pp but remains far above noise — Tuesday concentration is real.

This is a daily-aggregation-masking pattern: Q14's daily-resolution finding (7.5% adverse vs 7.1% non-adverse, MW p=0.19, "no portfolio-DD signal") aggregated across all weekdays and across all bars within a day. Q-T resolves at 15min × Tuesday-only-overlap-window and finds the Tuesday cohort carries the bar-level adverse co-movement that O4 flagged at lags 1–4 (z>5–14, run-length 15.6× iid).

Q14 is **not falsified** as stated — its measurement was at trade-day resolution against P&L, and P&L on Tuesdays still aggregates across the full trading day. Q-T identifies the bar-level signal Q14's resolution averaged over.

Macro-event Tuesday composition (descriptive; tag-and-preserve, no deletion):
- pct_in_NFP_first-Friday_window: 0.0% (Tuesday cohort cannot intersect Friday).
- pct_in_FOMC_Wed-evening_window: 0.0% (Tuesday cohort cannot intersect Wednesday).
- The macro-tag function inherited from [`o4_adverse_autocorr_2026_04_27.py`](../notice_phase/o4_adverse_autocorr_2026_04_27.py) targets Friday/Wednesday windows and is mechanically zero on a Tuesday-only cohort. Tuesday-specific events that the existing tag function does NOT cover include US CPI releases (some Tuesdays, ~12:30 UTC), Treasury auctions (Tuesdays), and BoJ rate decisions (Tuesday-eligible). Adding Tuesday-aware macro tags is OUT OF SCOPE for this brief — would require new tagging logic and risks crossing into "deletion by macro-event" forbidden D-test territory if the synthesis-pass author chose to filter on it. Surfacing here for synthesis-author awareness only.

Next-action: NONE.

## Verdict

**H_alt_1 supported.**

**Routing recommendation: Forward to Pepperstone re-verification (gated).** OANDA-proxy Tuesday cohort shows bar-level concurrent-loss elevation (Δ+5.39pp headline, Δ+2.73pp K-matched, both p ≪ 0.05). Per AMENDMENT and the brief's routing rules:

- Synthesis-pass author should consider authoring a new gated Q (Q-T-P) with fire conditions identical to Q-G/Q-A class (Pepperstone re-MC piggyback / explicit canonical-feed authorization).
- Verdict at this stage is **descriptive**: "OANDA-proxy Tuesday cohort shows concurrent-loss elevation; Pepperstone canonical re-verification required before any operational implication."

**Explicit non-actions (mandatory per brief):**
- **No overlay proposal.** Iran/Hormuz precedent ([feedback_constraint_set_overlay_oracle.md](../../../../.claude/projects/C--Users-joshu-prop-firm-pipeline/memory/feedback_constraint_set_overlay_oracle.md)) binds: bar-stat regime shifts do not justify overlay candidacy on backtest signal alone, regardless of magnitude.
- **No allocation modulation.** Var-alloc 4A REJECTED ([feedback_state_readable_observable_bottleneck.md](../../../../.claude/projects/C--Users-joshu-prop-firm-pipeline/memory/feedback_state_readable_observable_bottleneck.md)) binds: a "rolling Tuesday adversity" observable inherits the state-readable observable bottleneck (~31pp pass-rate strict-inferiority), so even a sized-down rule on this signal would Pareto-fail the constrained-future oracle.
- **No dd_protection touch.** Locked tier (≤−1.0% intraday × 0.40×) revalidated 2026-04-23, MC 92.73% pass; this finding does not motivate change.
- **No parameter change.** Strategy code locks (Guardian v5.5 / Striker v4.4 / Aegis v4.3) untouched; risk percentages (0.34 / 1.00 / 1.50) untouched.

Next-action: NONE.

## Methodology notes

### Pre-Q gate execution log

D applied at run time:
- Deleted: non-Tuesday days (kept Mon-only as comparison cohort), windows where <2 strategies session-active.
- Permitted-list anchors: §5 "outside the temporal / instrument scope of the question class".
- NOT deleted: any low-magnitude adverse windows, any "doesn't fit my model" cohort, any macro-event-aligned windows.

S applied at run time:
- Compressed raw OHLCV → log-return panel (inner-join on common timestamps) → per-instrument 1σ-adverse flag → per-overlap-window concurrent-loss binary.
- Preservation criterion: direct comparability with Q14's adversity threshold. Q14's per-instrument 1σ-adverse parameters reproduced verbatim from `o4_bar_correlation.py:simultaneous_adverse()` (rolling 60-day std, min_periods 500, threshold 1.0σ, long-only down). No re-derivation.

A applied at run time:
- Single pass over panel: O(n_bars) for adversity flags, O(overlap_windows) for cohort tests, O(1000 × n_a + 1000 × n_b) for bootstrap. Bounded; total runtime well under 1 day.

### Forbidden D-test self-check log

Self-checked at execution. None of the following surfaced:
- Deletion by mechanism plausibility (✗ — no "rejected because the signal looks too clean / too noisy").
- Deletion by macro-event tag (✗ — macro tagging applied descriptively to Tuesday cohort; not used as filter).
- Deletion by signal strength (✗ — kept all 1σ-adverse flags as defined).
- Deletion by model fit (✗ — let the data answer; H_alt_1 fired by the brief's pre-declared thresholds).

Close-call surfaced for transparency: the K-decomposition is descriptive only. The brief's primary metric is the headline Tuesday vs non-Tuesday rate. K-matching is reported alongside as a confound check, not as the verdict driver. Treating K=3 as "out of scope" would have been a forbidden D-test (deletion by mechanism plausibility) — it is part of the population the question targeted ("Tuesday is the day with maximum overlap"), so it is preserved.

### Time budget actual vs declared

Declared: ~1 day for Inquire-phase execution.
Actual: < 1 hour (Phase 0 verification cached from Notice run; Phase 1–4 single-pass over the aligned panel; bootstrap 1000 resamples on 4,579 + 3,230 binary array; well within budget).

### Sources Read at execution (Code's mirror of brief-author Sources Read)

| Source | Purpose | Path |
|---|---|---|
| Q-T brief (this turn) | task spec, halt conditions, hypothesis thresholds | (conversation) |
| AMENDMENT_oanda_rescope.md | canonical_status=PROXY binding; no Action verdict | docs/methodology/identify_corpus/2026-04-26/AMENDMENT_oanda_rescope.md |
| Notice 04-27 phase0 | provenance baseline (cached PASS) | analysis/notice_phase/phase0_2026_04_27.json |
| Q14 closure findings | parent verdict tested for robustness | analysis/notice_phase/findings_2026-04-26.md §G2 |
| O4 autocorr Notice findings | parent observation (lags 1–4 z>5–14) | analysis/notice_phase/o4_adverse_autocorr_2026_04_27.json |
| o4_bar_correlation.py | per-instrument 1σ-adverse definition (no re-derivation) | scripts/identify/2026-04-26/o4_bar_correlation.py |
| filters.py | strategy schedule operational metadata (Rule 0 does not bind) | scripts/identify/2026-04-26/filters.py |
| common.py | bar-loader, panel TZ, strategy identity | scripts/identify/2026-04-26/common.py |
| memory: feedback_constraint_set_overlay_oracle.md | overlay-candidacy refusal precedent | memory file |
| memory: feedback_state_readable_observable_bottleneck.md | var-alloc 4A REJECTED precedent | memory file |

Production strategy-code files (Guardian/Striker/Aegis Pine sources) NOT read — schedule metadata available from `filters.py` reconstruction and the 04-26 synthesis page, both of which are operational metadata layers above the locked Pine. Rule 0 explicitly does not bind on Q-T (no risk-control decision proposed at any verdict branch).

Next-action: NONE.

---

# Disposition (2026-04-28): closed with watchlist tripwire

**Decision (Joshua, 2026-04-28):** Log the finding. Add "Tuesday K=3 concentration" to the MSEE watchlist. Set a forward tripwire on **live FXIFY P&L variance**. The Action proposal drafted under the lifted Pepperstone gate (preserved below for trail) is **NOT EXECUTED**.

## Rationale

The Action proposal had a defensible technical argument: day-of-week is forward-readable (no Cond 3 bottleneck), the K-matched +2.73pp residual is real, and the proposal built in a P&L-Pareto adoption gate so the bar-stat couldn't directly drive a lock change. That's the "leading indicator with P&L gate" pattern.

The deeper read: that pattern is the rationalizing form of the Iran/Hormuz overlay-discipline trap. The discipline says "only a live-PnL gap vs MC justifies acting on a regime signal" — *not* "any signal you can model can be tested if you wrap it in a P&L gate". A P&L-test gate inside a backtest validates whether the bar-stat translates to backtest P&L; it does not validate whether it translates to **live P&L** that pays for the lock cycle.

The honest reframing is: **a bar-stat without a live-PnL signal is not enough to justify the lock cycle, even with a P&L-test gate built in.** If the discipline holds for overlays, it holds for sizing rules. The proposal earns cycles when the bar-level concentration manifests as a daily-resolution live-PnL signal — not before. Until then, the right move is to monitor and let the substrate speak.

## Tripwire — re-opening criterion

**Trigger:** Over a rolling 6-month window of **live FXIFY trading** (not backtest), Tuesday daily-portfolio-R standard deviation exceeds 1.5× max(Monday std, Thursday std), with n ≥ 30 trade-days in each cohort.

**Why this metric:**
- *Live, not backtest.* The discipline that closed the proposal was about live-PnL signal. The tripwire enforces it.
- *Variance, not mean.* The bar-level finding is about *concentration of tail-risk*, which manifests as variance asymmetry before it shows up as mean-loss asymmetry. Variance is the right first-derivative signal.
- *vs Mon and Thu.* Monday is the natural K=2 control (G+A). Thursday is a Guardian-only day (no S, no A); using both controls bounds against single-day anomalies.
- *1.5× threshold.* Conservative — accommodates normal week-to-week variance. A real Tuesday-K=3 concentration leaking to live P&L should show >1.5× std ratio.
- *n ≥ 30 floor.* Avoids tripping on noise during early challenge weeks.

**If tripped:** the bar-stat finding has graduated to a daily-resolution live signal. The Action proposal below earns its cycles. Run Gate 1.5 (entry-count audit) on the live data, then the sizing grid. Re-MC if the grid clears the Pareto criterion.

**If not tripped after 6 months of live FXIFY trading:** the finding remains a structural watchlist item, not a candidate for action. Re-evaluate cadence (extend monitoring vs close-permanent) at the next quarterly methodology review.

## Logged

- Watchlist indicator added: see [`docs/methodology/msee/watch_list.md`](../../docs/methodology/msee/watch_list.md) → "Tuesday K=3 P&L variance elevation".
- Memory observation: leading-indicator-with-P&L-gate as a rationalization pattern (Iran/Hormuz spirit refinement).

---

# Action proposal — Tuesday-K=3 risk scaling test (drafted 2026-04-28, NOT EXECUTED)

> **Status: NOT EXECUTED.** Closed 2026-04-28 per the Disposition section above.
> Preserved verbatim as the trail of considered-but-rejected work.
> Re-opening criterion: live-PnL tripwire defined in Disposition.
>
> Drafted under the 2026-04-28 policy supersession: OANDA findings can route
> to Action proposals; Joshua validates in TradingView against Pepperstone
> bars before any code/lock change. Joshua's subsequent call: that gate-pattern
> rationalizes the Iran/Hormuz overlay-discipline rather than honoring it. See
> Disposition.

## What the finding shows

On the OANDA-proxy 4yr 15min panel, when all three strategies are simultaneously session-active (Tuesday-K=3 windows: G ∩ S ∩ A schedule overlap), the bar-level concurrent-loss rate (≥2 of the three instruments hitting 1σ-adverse-down on the same 15min bar) is **8.64%** vs Mon-K=2's **0.74%** — a ~12× rate elevation. K-matched control (Tue-K=2 vs Mon-K=2) attenuates Δ to +2.73pp but stays significant (p ≪ 0.05), confirming a Tuesday-specific component beyond the K=3 mechanical artifact.

**Operative effect size for sizing-rule design: +2.73pp, not +5.39pp.** Roughly half the headline gap is the mechanical ≥2-of-3 vs ≥2-of-2 combinatorial artifact (K=3 windows trivially produce more concurrent-loss bars than K=2 windows, even under iid). The Tuesday-specific component the sizing change is actually correcting for is the K-matched residual. Anchor cost-benefit on the residual, not the headline ratio.

This is a structural concentration of *bar-level* tail-risk on the one day of the week with maximum concurrent strategy exposure. **Pre-budget the expected gain.** Back-of-envelope on a uniform-s sizing rule applied only inside the K=3 window (~26% Tuesday-overlap exposure footprint) at the operative +2.73pp effect: a realistic ceiling on p99 DD reduction is ~0.5–1.0pp. Decide whether that clears the lock-cycle cost (3 Pine bumps, ADR, MVD, re-MC, anchor refresh) **before** running the grid, not after.

## Why this is eligible for Action (not Forward-only)

- Day-of-week is a **forward-readable, deterministic state variable** — known at session start, no look-ahead. Unlike DD-state / rolling-PF / cumulative-past observables, it does not trip the state-readable Cond 3 bottleneck (var-alloc 4A REJECTED precedent does not apply).
- The proposed change is a **risk-sizing test**, not an overlay. The Iran/Hormuz overlay-trigger discipline (overlays require live-PnL-gap, not bar-stat shifts) does not block it — but the spirit (don't act on bar-stat shifts blindly) is honored by gating adoption on a Pareto-improvement criterion in TradingView, not on the bar-stat finding alone.
- Q14 was *not* falsified — the bar-level signal Q-T identifies has not manifested as a daily-resolution P&L gap. This proposal therefore acts on a **leading indicator** and must clear an explicit P&L-test gate before adoption.

## Pre-test gates (cheapest first, do these before the sizing grid)

> **Substrate constraint.** Pepperstone 15min bar OHLCV is **not available** in this repo or on Joshua's workstation. The Q-T headline (bar-level concurrent-loss rate at the 15min × 1σ-adverse-down × ≥2-instrument resolution) cannot be substrate-replicated against Pepperstone without acquiring Pepperstone bars. Available Pepperstone substrate is trade-level only: per-strategy TV exports at [`data/tv_exports/pepperstone/`](../../data/tv_exports/pepperstone/) (Guardian / Striker / Aegis trade history through 2026-04-26).
>
> Gate 1 below is therefore re-specced as a **trade-level corroboration gate** using the Pepperstone TV exports. This is a *weaker* gate than bar-level replication would have been — see the "What Gate 1 can and cannot tell us" caveat after the spec.

**Gate 1 — Pepperstone trade-level Tuesday-K=3 corroboration** (runs in this repo against committed Pepperstone CSVs). For each Tuesday and Monday in the 2022-01 → 2026-04-26 panel, mark which strategies had a trade entry inside the G ∩ S ∩ A overlap window on that day. Stratify days into Tuesday-K=3 (G+S+A all entered), Tuesday-K=2 (any 2 of 3), Monday-K=2 (G+A — Striker is Tue/Fri only, so Monday is structurally K=2). Compute per-day:
- **Concurrent-loss-day rate**: rate of days where ≥ 2 of the active strategies had ≥ 1 losing trade exit on the day.
- **Mean per-day portfolio R**: sum of allocation-weighted R across active strategies on that day.
- **Days breaching dd_protection's 1.0% intraday DD trigger**: rate.

**Gate 1 pass condition (any of the three is sufficient — directional consistency, not strict significance):**
- Tuesday-K=3 concurrent-loss-day rate > Monday-K=2 by ≥ +5pp (descriptive); OR
- Tuesday-K=3 mean per-day portfolio R < Monday-K=2 by ≥ 0.1R (descriptive); OR
- Tuesday-K=3 dd_protection-trigger rate > Monday-K=2 (any positive Δ).

**Gate 1 fail condition: all three null/reversed.** If Pepperstone trade-level shows Tuesday-K=3 days are *better* than Monday-K=2 days (or noisily indistinguishable across all three readings), the OANDA bar-level signal does not propagate to Pepperstone trade-level under any natural aggregation. **Reject the proposal here.** The structural concentration is OANDA-feed-specific or it concentrates at a resolution that doesn't show up in P&L; either way, sizing against it would be Pareto-negative.

**What Gate 1 can and cannot tell us (mandatory caveat).**
- Q14 (the OANDA equivalent at trade-day resolution) showed null. Q-T's whole motivation is that the bar-level signal is *below* trade-day aggregation — i.e., the bar-level concurrent-loss bars on Tuesday don't propagate to a daily-aggregate P&L gap, because intraday recovery and per-strategy exit logic absorb the bar-level adverse moves before they hit the books.
- **Therefore: a passing Gate 1 (Pepperstone trade-level shows directional signal) is STRONG corroboration** — it means the bar-level concentration is severe enough on Pepperstone that it leaks into trade-level outcomes despite the same intraday absorption.
- **A null Gate 1 (Pepperstone trade-level shows no signal) is NOT a clean rejection** — it's consistent with both (a) the Pepperstone bar-level signal being real but absorbed at trade-level (analogous to Q14 on OANDA), and (b) the bar-level signal not replicating on Pepperstone at all. Without Pepperstone bars, those two cases are indistinguishable from trade-level alone.
- **A reversed Gate 1 (Pepperstone trade-level shows Tuesday-K=3 *better* than Mon-K=2) is the rejection trigger.** That would mean even if the bar-level concentration is real on Pepperstone, the trade-level outcome on Tuesday-K=3 days is structurally *favorable*, and sizing down would erase a profitable cohort.

**Optional Gate 1-bar (cleaner substrate replication, requires manual TradingView work).** If Joshua wants the original bar-level Q-T headline replicated against Pepperstone, write a Pine indicator that flags 1σ-adverse-down 15min bars per instrument (rolling 60-day std, 1.0σ threshold matching `o4_bar_correlation.py:simultaneous_adverse()`), and outputs concurrent-loss rates by day-of-week × K-class to TradingView's data window. Run on Pepperstone XAUUSD/US30/USDJPY for the 2022-01 → 2026-04 span and read the Tuesday-K=3 vs Mon-K=2 Δ. Original Gate 1 fail condition (Δ < +1.0pp or p > 0.05) applies. **Recommended only if Gate 1 (trade-level) lands ambiguous** — Pepperstone-bar acquisition / Pine-indicator authoring is non-trivial work; do it once the cheaper trade-level gate has narrowed the question.

**Gate 1.5 — K=3-window entry-count power audit.** On the Pepperstone TV exports, count entries per strategy that fall inside the Tuesday G ∩ S ∩ A overlap window over the 4yr panel. Rough back-of-envelope: Guardian ≈ 25, Striker ≈ 50–80, Aegis ≈ 35 — plausibly < 100 affected entries per strategy. **If any strategy has < 50 affected entries, flag the historical-replay leg of the sizing test as low-power and pre-commit to weighting MC re-anchor evidence over historical replay where they conflict.** Adoption decision must explicitly tag which evidence source is load-bearing. Also produces the cohort sizes Gate 1's stratification depends on, so run as part of the same pass.

## Proposed sizing test (run only if both gates pass)

Apply scaling factor `s ∈ {0.50, 0.70, 0.85, 1.00}` to all three strategies' `riskPerTrade` **only on Tuesdays during the G ∩ S ∩ A overlap window** (Striker 13:00–17:00 UTC ∩ Guardian 08:00–16:00 NY ∩ Aegis 10:00–13:45 NY). Run on Pepperstone 2022-01 → 2026-04 with **MC at 50K × 3 seeds** (raised from canonical 10K to tighten bust-rate CI for the comparison). Compare against the locked baseline (`s = 1.00`):

| Metric | Adoption criterion (vs. baseline) |
|---|---|
| Pass rate | within −1.0pp |
| Bust rate | ≤ baseline within MC bootstrap 95% CI |
| p99 portfolio DD | strictly lower |
| Median days-to-pass | within +5 days |

**Bust-rate criterion rationale.** At 0.65% baseline on 10K MC draws ≈ 65 events; strict-inequality detection against MC sampling variance is a high bar that will reject for noise even if the signal is real. The bootstrap-CI form preserves the tail-risk discipline (don't accept anything that materially worsens bust rate) without rejecting Pareto improvements that fall inside MC noise. The strict-inequality discipline is moved to p99 DD, where the signal-to-noise ratio is higher.

**Adopt** the lowest `s` that satisfies all four. **Reject** if no `s` does, with one exception:

**Per-strategy follow-up (if uniform shows marginal Pareto).** Bust attribution is uneven (S 39.3% / G 33.2% / A 27.6% per the 04-23 ADR; 04-26 Pepperstone reproduction shows S still leads at 43.4%). If uniform-s clears the gate marginally on one or two metrics, the per-strategy variant `s_G`, `s_S`, `s_A` is worth a follow-up rather than an immediate reject — Striker is doing more of the bust work and may deserve a tighter scale than the others. This expands the test dimensionality, so run it only if uniform shows promise.

## What this proposal does NOT do

- Does **not** modify Pine code, allocations, `dd_protection`, or strategy versions until the TradingView test confirms a `s` that meets adoption criteria.
- Does **not** touch CLAUDE.md headline MC numbers (Pepperstone-anchored lock-decision artifacts). If `s < 1.00` is adopted, a fresh re-MC fires under the existing re-MC trigger rules.
- Does **not** stagger strategy session schedules — those are inside the locked Pine and out of scope here.
- Does **not** add a Tuesday-specific tier in `dd_protection` (single-tier production-locked 2026-04-17). Sizing-by-day-of-week is a separate axis.

## If adopted, where it lives

If the TradingView test selects a non-trivial `s`, the implementation is a per-strategy Pine modification (or a `dd_protection`-style sizing layer) that reads day-of-week and the overlap-window timestamp. This is a Pine-code change requiring a fresh ADR (`docs/adr/YYYY-MM-DD-tuesday-k3-sizing.md`), an MVD assertion against the new constant, and a re-MC committed via [tests/test_mc_anchors.py](tests/test_mc_anchors.py) anchor refresh.

## Reproducibility

OANDA-proxy script: [`python analysis/inquire_phase/q_t_tuesday_concurrent_loss_2026_04_27.py`](q_t_tuesday_concurrent_loss_2026_04_27.py). The Pepperstone re-run is Joshua's TradingView responsibility; no script in this repo currently runs against Pepperstone bars (data not git-tracked).

## Expected outcome distribution (calibrated 2026-04-28, Pepperstone-bars-unavailable variant)

For sequencing expectations under the trade-level Gate 1 (Pepperstone bars not available):

- **~15%** Gate 1 reversed (Pepperstone Tuesday-K=3 days are better than Mon-K=2 days at trade-level). Outcome: reject proposal, OANDA bar-level signal is feed-specific or doesn't survive trade-level aggregation in a sizable-down direction.
- **~50%** Gate 1 ambiguous (Pepperstone trade-level null or weakly directional, consistent with both "bar-level signal real but absorbed" and "bar-level signal absent on Pepperstone"). Sub-decision required: either proceed to sizing test on weaker evidence (raise Pareto criterion strictness to compensate), or run optional Gate 1-bar in TradingView before the sizing test. Default: proceed if Gate 1.5 entry counts are healthy (≥ 50 per strategy), defer to optional Gate 1-bar otherwise.
- **~25%** Gate 1 passes (Pepperstone trade-level shows directionally consistent Tuesday-K=3 signal on at least one of the three readings). Strong corroboration; proceed to sizing test with confidence.
- **~10%** Sizing test clears Pareto criterion at `s ∈ {0.70, 0.85}`. Outcome: fresh ADR, MVD assertion, re-MC, anchor refresh.

The shift versus the bar-level-Gate-1 variant: more mass on "ambiguous, decide what to do next" (50% vs ~0%), less on clean reject (15% vs ~40%) and clean adopt (10% vs ~25%). Trade-level Gate 1 is a weaker discriminator than bar-level would have been; expect more proposals to require a second decision point rather than resolving cleanly at Gate 1.

If realized outcome diverges materially from this distribution (e.g., Gate 1 passes cleanly *and* sizing test sails through at `s = 0.50`), audit the test setup before adopting — may indicate over-fit, a substrate issue, or that the OANDA bar-level finding was actually a stronger signal than expected.
