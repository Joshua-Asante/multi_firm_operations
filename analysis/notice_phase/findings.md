# Notice Phase — Bar-Data High-Leverage Drill-Down

**Scope.** Observation-only deep-dive on the three findings ranked top in
`analysis/bar_data_high_leverage.md`. No recommendations, no re-MC runs, no
overlay proposals, no strategy changes. Each thread surfaces structure; new
high-leverage questions are logged at the end as Open Questions for the
Inquire phase.

**Panel.** XAUUSD / US30 / USDJPY 15-min UTC bars, NY-tz daily aggregation.
Span 2022-01-02 → 2026-04-19, ~52 months. Bar counts (this load):
XAUUSD 101,461 / US30 101,245 / USDJPY 106,820 — match the initial-analysis
report. Zero NaNs. Daily counts: XAU 1,336 / US30 1,338 / JPY 1,342. See
`rule0_sanity.json` for the audit dump.

**Reuse.** Loader/daily aggregation copied from `analysis/bar_analysis.py`.
Thread C bootstrap mechanics mirror `portfolio_mc.build_week_blocks`
(`portfolio_mc.py:127`) and `run_seed`'s sampling
(`portfolio_mc.py:187`): Mon-anchored 5-day non-overlapping blocks of the
business-day-reindexed daily panel, sampled with replacement.

---

## Thread A — XAUUSD regime: WHEN and HOW

### A1. Inflection date

Rolling annualized vol on XAUUSD daily log returns. The "first date where
rolling vol crossed 20% and never returned below 15%" — verified across
three windows (file: [`A1_inflection.json`](A1_inflection.json), figure:
[`figures/A1_rolling_vol.png`](figures/A1_rolling_vol.png)):

| Window | Crossover date | Vol at crossover | Post-crossover min vol |
|---|---|---:|---:|
| 20-day | **2026-01-20** | 22.2% | 15.5% (held > 15%) |
| 30-day | **2026-01-22** | 21.5% | 20.1% (never returned < 20%) |
| 60-day | **2025-11-12** | 20.4% | 16.7% (held > 15%) |

The 60-day inflection precedes the 20/30-day by ~9 weeks: the rolling-60
window was already absorbing rising vol from late October before the
shorter windows registered. All three converge on the late-Nov-2025 →
late-Jan-2026 window as the regime onset. The 30-day rolling vol has *not*
returned below 20% since 2026-01-22 (n = 60 trading days post-crossover),
which is the strongest stability signal of the three.

### A2. Drift attribution within 2026 YTD

#### A2a. Session-time decomposition

Mean |15-min log return|, bp, by NY session window (file:
[`A2a_session_decomp.csv`](A2a_session_decomp.csv), ratios:
[`A2a_session_ratios.json`](A2a_session_ratios.json)):

| Session | 2022-2025 (n bars) | 2026 YTD (n bars) | 2026/prior ratio |
|---|---:|---:|---:|
| Asia 00-08 EST | 5.91 (33,014) | 13.24 (2,400) | **2.24×** |
| NY 08-16 EST | 8.25 (32,805) | 17.25 (2,388) | **2.09×** |
| Late 16-24 EST | 5.03 (28,753) | 15.69 (2,100) | **3.12×** |

The vol elevation is pervasive across the 24-hour cycle, not NY-session-
concentrated. The Late session (16-24 EST, post-NY-close into Asia open)
shows the largest relative jump (3.12×). NY hours scaled the least (2.09×),
though they remain the absolute-largest session in both eras.

#### A2b. Sign-symmetry — QQ plot

2026 YTD daily returns vs 2022-2025 pooled (n = 92 vs 1,243; figure:
[`figures/A2b_qq_plot.png`](figures/A2b_qq_plot.png), data:
[`A2b_sign_symmetry.json`](A2b_sign_symmetry.json)):

| Metric | 2022-2025 | 2026 YTD |
|---|---:|---:|
| p01 (lower tail, bp) | -239.3 | **-632.9** |
| p99 (upper tail, bp) | +244.3 | **+551.8** |
| |p01| / p99 ratio | 0.98 | **1.15** |
| Skew | -0.23 | -0.40 |
| Excess kurtosis | 3.14 | 1.64 |

Both tails widened ~2.3× vs prior. The 2026 distribution is mildly more
left-skewed (skew -0.40 vs -0.23, |p01|/p99 = 1.15 vs 0.98) — large
down-days exceed large up-days by ~15% in magnitude at the 1% tail.
Excess kurtosis is *lower* in 2026 (1.64) than in 2022-2025 (3.14):
the wider tails are part of a broader-shouldered distribution, not extreme
isolated outliers.

#### A2c. Time-clustering — top-N share of 2026 vol

n = 16 weeks, 92 trading days (file:
[`A2c_time_clustering.json`](A2c_time_clustering.json)):

| Metric | Share of 2026 squared-return total |
|---|---:|
| Top 5 weeks | **78.3%** |
| Top 5 days | 40.6% |
| Top 10 days | 62.5% |

Vol is heavily week-concentrated. The single largest week (2026-02-02,
contributing 0.0154 of the 0.0290 total YTD weekly variance) accounts for
~53% by itself. Top 10 weeks by contribution are all clustered in
Jan-Apr 2026 (contiguous). The week-concentration coexists with the
distribution-wide widening from A2b: the high-vol weeks are not headline-
spike artefacts — they are weeks where the *whole distribution* is
broader.

### A3. Guardian's actual input — 15-min 14-bar ATR (CRITICAL)

Pine-style `ta.atr(14)` on 15-min XAUUSD bars (RMA of true range, period 14;
implementation: `notice_phase.py` `rma()` — alpha = 1/14, SMA seed). Yearly
aggregates (n bars per year ≈ 23.6k for full years, 6,888 for 2026 YTD):

File: [`A3_yearly_atr.csv`](A3_yearly_atr.csv) /
[`A3_atr_summary.json`](A3_atr_summary.json) /
figure: [`figures/A3_atr_monthly.png`](figures/A3_atr_monthly.png).

| Year | mean ATR14 ($) | mean bar range ($) | ATR/range | RMA(14)/SMA(14) mean |
|---:|---:|---:|---:|---:|
| 2022 | 2.34 | 2.33 | 1.005 | 1.050 |
| 2023 | 2.07 | 2.06 | 1.004 | 1.061 |
| 2024 | 2.95 | 2.94 | 1.004 | 1.053 |
| 2025 | 5.67 | 5.66 | 1.003 | 1.033 |
| **2026 YTD** | **15.31** | **15.22** | **1.006** | **1.029** |

**Two findings.**

(1) 14-bar ATR has *not* lagged bar-range expansion. The ATR/mean-bar-range
ratio is essentially constant at 1.003-1.006 across all five years — the
RMA tracks the underlying range distribution to within 0.6% by year. This
is structurally expected (RMA is a smoothed mean and we are comparing means
over the year), but the empirical confirmation is non-trivial given the
~5× regime jump.

(2) RMA-vs-SMA contemporaneous lag (per-bar ratio of RMA(14) ÷ SMA(14)) is
in the 1.03-1.06 band across years, *falling slightly* in 2025 (1.033) and
2026 (1.029). The smoothed measure is closer to the contemporaneous mean in
the high-vol regime than in calm years — i.e., the lag did not widen during
the regime shift.

**Implied $-risk arithmetic.** Anchor lots at 2024 ATR (mean 2.949 $/bar),
ATR multiplier 1.55, contractValue $100/lot — implies lots = 1.49 for the
$680 (= 0.34% × $200K) target. *If* lots were held at that 2024 anchor
(counterfactual — Pine does not do this), then at 2025 ATR lots would
deliver $1,307/trade (1.92×) and at 2026 ATR $3,530/trade (5.19×). Pine
recomputes lots from the then-current ATR14 each entry, so the effective
forward $-risk is governed by ATR14-at-entry, which (per finding 1) is
within ~1% of the prevailing bar-range distribution. The auto-sizing
argument from the prior report appears intact at the bar-data level.

The remaining failure mode is *intra-trade*: ATR14 at entry estimates the
range at entry, but if vol expands further during the trade, the realized
SL distance (and therefore $-risk per stop-out) is whatever the post-entry
move dictates, not the at-entry estimate. Bar data alone cannot measure
this — it requires trade-level analysis on the locked Pine.

### A4. Trend persistence — run-length distribution by year

Consecutive same-sign daily run lengths on XAUUSD daily returns
(file: [`A4_run_lengths.csv`](A4_run_lengths.csv)):

| Year | n days | n runs | mean run | p95 run | max run | mean +run | mean -run | max +run | max -run |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 309 | 166 | 1.86 | 4.0 | 8 | 1.82 | 1.90 | 6 | 8 |
| 2023 | 309 | 142 | 2.18 | 5.0 | 12 | 2.30 | 2.06 | 5 | 12 |
| 2024 | 313 | 163 | 1.92 | 5.0 | 7 | 2.07 | 1.77 | 7 | 5 |
| 2025 | 312 | 152 | 2.05 | 5.0 | 8 | 2.38 | 1.72 | 8 | 5 |
| **2026 YTD** | 92 | 46 | 2.00 | 5.0 | 7 | 2.30 | 1.70 | 7 | 6 |

2026 YTD run-length distribution is statistically indistinguishable from
2023-2025 (mean 2.00, p95 5.0, max 7). The trend-rider edge proxy (mean
positive-sign run length) is 2.30 in 2026 — sits in the same band as
2023-2025 (2.06-2.38). The vol regime shift has *not* been accompanied by a
visible change in directional persistence at the daily horizon. Note small
sample for 2026 (n = 92 days, 46 runs) — confidence interval is wide.

---

## Thread B — Joint correlation: WHEN and HOW

### B1. Rolling traces

30/60/120-day rolling pairwise correlations across all three pairs (figure:
[`figures/B1_rolling_corr.png`](figures/B1_rolling_corr.png)). Sustained
breaks (>= 30 consecutive days outside the full-panel 60-day-corr ±1σ band;
file: [`B1_inflections.json`](B1_inflections.json)):

| Pair | 60d corr full mean ± std | Sustained breaks (≥30d) |
|---|---:|---|
| XAU-US30 | +0.16 ± 0.27 | 5 prior episodes (2022-25); **no 2026 break** registered |
| XAU-USDJPY | -0.39 ± 0.19 | 4 episodes incl. 2025-10-30 → 2026-01-27 (89d, above-band) and 2026-02-06 → 2026-03-13 (35d, above-band) |
| US30-USDJPY | -0.05 ± 0.25 | 4 prior episodes (2022-25); **no 2026 break** registered |

The XAU-USDJPY pair shows the most explicit 2026 inflection — the
correlation has been less negative (closer to zero) for ~5 contiguous
months starting late October 2025, aligning with the A1 inflection (60-day
window crossover at 2025-11-12). XAU-US30 and US30-USDJPY do **not**
register sustained breaks in 2026, despite the absolute-mean shifts
documented in the initial report. This is because the full-panel ±1σ band
is wide (60d std 0.27 and 0.25 respectively); 2026 corrs of +0.31 and -0.22
sit inside [-0.11, +0.43] and [-0.30, +0.21] respectively.

In other words: at the 60d-rolling level, only XAU-USDJPY has an unusual
sustained corr regime in 2026; the other two pairs' shifts are within
historical noise.

### B2. Event-driven vs pervasive

2026 YTD pairwise daily-return correlations, full vs trimmed-by-top-10
|z|-day outliers (n = 92 → 82 after trim; calibration n = 625 days for
2024-25; file: [`B2_event_vs_pervasive.json`](B2_event_vs_pervasive.json)):

| Pair | 2024-25 calib | 2026 full | 2026 trim-10 |
|---|---:|---:|---:|
| XAU-US30 | +0.10 | +0.31 | **+0.43** |
| XAU-USDJPY | -0.28 | -0.24 | -0.25 |
| US30-USDJPY | +0.13 | -0.22 | **-0.40** |

Removing the 10 largest-|z| days *strengthens* the 2026 correlation drift
on both XAU-US30 (+0.31 → +0.43) and US30-USDJPY (-0.22 → -0.40). The
outlier days (10 of which are clustered in Jan 23 - Feb 10 plus 03-27,
2026) are correlation-attenuating, not correlation-driving — they pull the
sample correlation toward zero rather than away from it.

The 2026 correlation drift is therefore characterised as **pervasive**, not
event-driven. The base-rate co-movement structure of all three pairs has
shifted. The headline event-day cluster sits *across* this shifted base
rate but does not produce it.

### B3. Intraday vs daily structure

15-min log-return correlations (n = 6,876 bars 2026 YTD vs 94,241 bars
2022-2025; file: [`B3_intraday_vs_daily.json`](B3_intraday_vs_daily.json)):

| Pair | 15m 2022-2025 | 15m 2026 YTD | (Reference: daily 2022-25) | (Reference: daily 2026) |
|---|---:|---:|---:|---:|
| XAU-US30 | +0.13 | **+0.34** | +0.10 | +0.31 |
| XAU-USDJPY | -0.34 | -0.23 | -0.28 | -0.24 |
| US30-USDJPY | +0.003 | **-0.23** | +0.13 | -0.22 |

The daily-level shifts are mirrored at the 15-min level, both in direction
and approximate magnitude. XAU-US30: +0.13 → +0.34 at 15m (vs +0.10 →
+0.31 daily); US30-USDJPY: +0.003 → -0.23 at 15m (vs +0.13 → -0.22
daily); XAU-USDJPY: -0.34 → -0.23 at 15m (vs -0.28 → -0.24 daily).
This rules out the daily-aggregation-artefact explanation. The shift is a
true bar-level co-movement regime change.

---

## Thread C — Vol clustering vs portfolio_mc bootstrap mechanics

XAUUSD only. The bootstrap experiment mirrors `portfolio_mc.py`'s 5-day
Mon-anchored non-overlapping block sampling exactly (mechanics confirmed
against `portfolio_mc.py:127` `build_week_blocks` and `:187` `rng.integers`
sampling). Built 224 Mon-anchored weekly returns from the business-day-
reindexed XAU daily panel (matches `build_week_blocks` count semantics).
Share of weeks with negative cumulative return: **41.5%**
([`C1_empirical_max_runs.json`](C1_empirical_max_runs.json)).

**This is a methodology-mechanic experiment, not a portfolio MC. No
pass/bust output. No allocation involved.**

### C1. Empirical max-consecutive-negative-weeks distribution

Sliding 32-week window over the 224-week panel. n = 193 windows
(file: [`C1_empirical_max_runs.json`](C1_empirical_max_runs.json)):

| Stat | Value |
|---|---:|
| Mean | 3.43 |
| p50 | 3 |
| p75 | 5 |
| p90 | 5 |
| p95 | 5 |
| p99 | 5 |
| Max | **5** |

The 224-week panel never produced a strict-negative streak longer than 5
weeks anywhere. Adjacent sliding-windows are highly correlated (overlap
31/32 weeks), so the distribution has effectively very few independent
samples — the "5 max" is the binding constraint imposed by the empirical
panel itself.

### C2. Bootstrap-replicated distribution

Same 5-day Mon-anchored block bootstrap as `portfolio_mc.py`, sampling
32 blocks with replacement, summing each block to a weekly log return,
recording max consecutive negative weeks per path. n = 3,000 paths
(3 seeds × 1,000) (file:
[`C2_bootstrap_max_runs.json`](C2_bootstrap_max_runs.json)):

| Stat | Value |
|---|---:|
| Mean | 3.51 |
| p50 | 3 |
| p75 | 4 |
| p90 | 5 |
| p95 | 6 |
| p99 | 8 |
| Max | **11** |

### C3. Comparison

Overlay: [`figures/C3_max_runs_overlay.png`](figures/C3_max_runs_overlay.png).
Delta = empirical − bootstrap (file:
[`C3_comparison.json`](C3_comparison.json)):

| Quantile | Empirical | Bootstrap | Delta (emp - boot) |
|---|---:|---:|---:|
| Mean | 3.43 | 3.51 | -0.08 |
| p50 | 3 | 3 | 0 |
| p90 | 5 | 5 | 0 |
| p95 | 5 | 6 | **-1** |
| p99 | 5 | 8 | **-3** |
| Max | 5 | 11 | **-6** |

**Direction is opposite to the prior-report hypothesis.** The original
report speculated that vol clustering should make empirical sequential bad
streaks heavier-tailed than the i.i.d.-week bootstrap. For the specific
metric of "max consecutive strictly-negative weeks in a 32-week horizon",
the bootstrap produces *longer* tails than the empirical panel:
bootstrap p99 = 8 weeks vs empirical p99 = 5 weeks; bootstrap max = 11 vs
empirical max = 5.

**Two non-mutually-exclusive descriptive interpretations.**

(a) The empirical distribution is bounded above by the historical max
streak (5 weeks anywhere in 224 weeks). The 193 sliding windows are not
independent samples — they share 31/32 weeks of overlap with their
neighbours — so the empirical p99 has effectively ~6 independent
realisations. The empirical sample cannot express tails longer than the
historical max, regardless of true population tail shape.

(b) The bootstrap, by sampling weeks with replacement, can recombine bad
weeks from disjoint historical periods into longer streaks than ever
historically occurred. For *this metric*, that recombination produces a
heavier tail than the empirical realisation.

For this particular tail measure (max-consec-neg-weeks in 32w), the
bootstrap is therefore *more* pessimistic than the empirical record, not
less. This does not refute the lag-5 ACF concern in the original report —
which is about within-block-sequence clustering, not strict-negative-run
length — but it does constrain how that ACF concern manifests in tail
measures.

### C4. GARCH(1,1) descriptive fit

Constant-mean GARCH(1,1) on daily log returns × 100, normal innovations
(`arch` 8.0.0; file: [`C4_garch.json`](C4_garch.json)):

| Symbol | n | ω | α | β | α+β (persistence) | LL |
|---|---:|---:|---:|---:|---:|---:|
| XAUUSD | 1,335 | 0.0351 | 0.1021 | 0.8631 | **0.965** | -1755.5 |
| US30 | 1,337 | 0.0427 | 0.1194 | 0.8264 | 0.946 | -1619.6 |
| USDJPY | 1,341 | 0.0127 | 0.0694 | 0.8950 | **0.964** | -1127.9 |

XAUUSD and USDJPY both have α+β > 0.95 (the threshold the prep flagged for
"i.i.d. assumption is structurally wrong"). US30 is 0.946 — below the
threshold but only marginally. All three series exhibit substantial
GARCH-style conditional heteroskedasticity. USDJPY shows the highest β
(0.895) — its variance process is the most slowly mean-reverting of the
three; US30 has the highest α (0.119), i.e. the largest immediate
shock-to-variance pass-through. Descriptive only — model not used in any
downstream computation here.

---

## Open Questions for Inquire phase

- Has the 2026 XAUUSD regime shift produced a measurable change in
  Guardian's *realized* per-trade $-risk relative to the 0.34% account
  target, controlling for at-entry ATR? Bar data alone cannot answer this;
  requires trade-level reconciliation against the locked Pine.
- Does the empirical-vs-bootstrap inversion in Thread C (bootstrap longer-
  tailed than empirical for max-consec-neg-weeks) survive an alternative
  metric formulation — e.g., max cumulative weekly drawdown, longest
  losing-equity run by day, or max consecutive *strategy-P&L*-negative
  weeks under the locked allocation?
- Does the XAU-US30 correlation shift propagate to *strategy P&L*
  correlation under the locked allocation, or does the strategy-signal
  layer (EMA slope on Guardian, breakout-distance on Striker) decorrelate
  the joint exposure regardless of the underlying bar-level co-movement?
- Is the 60-day rolling correlation band ([B1] full-panel mean ± std) the
  right reference frame for declaring an "unusual" regime, given that
  XAU-US30 and US30-USDJPY 2026 shifts do not register as sustained breaks
  by that test despite being clearly unusual at the absolute-mean level?
- Does the 2025-10-30 → 2026-01-27 XAU-USDJPY sustained-break window
  ([B1]) coincide with any locked-strategy live PnL anomaly (Guardian or
  Aegis), or has the strategy-signal layer absorbed it?
- Given GARCH(1,1) persistence > 0.95 on XAU and USDJPY ([C4]), what
  fraction of `portfolio_mc.py`'s reported p99 DD is sensitive to the
  i.i.d.-week resampling assumption — measurable via a paired stationary-
  bootstrap vs fixed-block experiment, *if and when* a re-MC trigger fires
  by documented rules?
- Does the late-session (16-24 EST) 3.12× elevation in 2026 XAUUSD bar
  vol ([A2a]) coincide with the bar windows around any locked-strategy
  scheduled exit (Guardian end-of-session) or pyramid-add point? Bar data
  alone cannot answer.

---

## Reproducibility

- Script: [`notice_phase.py`](notice_phase.py) (single-file, self-contained
  except for input bar CSVs at `C:/Users/joshu/prop_firm_pipeline/data/bar_data/`).
- Outputs: all `*.json` and `*.csv` files in this directory.
- Figures: in [`figures/`](figures/).
- Stack: pandas, numpy, scipy.stats, statsmodels (acf), arch (GARCH),
  matplotlib. arch 8.0.0 added to local environment for this analysis;
  no other new dependencies.
- Sample sizes stated for every numeric claim. Significance levels cited
  where computed. No multiple-comparison correction applied — uncorrected
  p-values inherited from the original report (KS p=0.0018, Levene
  p=2.6e-22) remain the basis for the regime claim. None of the new
  numeric claims in this notice phase depend on a borderline p-value
  (0.01 < p < 0.05).
- Bootstrap mechanics in Thread C verified line-for-line against
  `portfolio_mc.build_week_blocks` (`portfolio_mc.py:127`) and
  `run_seed`'s `rng.integers(0, n_blocks, ...)` call (`portfolio_mc.py:187`).
- `portfolio_mc.py` was **not** executed during this work (per scope
  constraint). Thread C uses the same block-construction and sampling
  code but runs over single-asset XAU returns rather than the multi-
  strategy P&L panel.
