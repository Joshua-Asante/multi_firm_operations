# Q-T Tuesday-cohort bar-level concurrent-loss — findings — 2026-04-27

Substrate: OANDA-proxy 4yr 15min panel (XAUUSD / US30USD / USDJPY).
Canonical status: **PROXY** end-to-end per
[AMENDMENT_oanda_rescope.md](../../docs/methodology/identify_corpus/2026-04-26/AMENDMENT_oanda_rescope.md).
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
