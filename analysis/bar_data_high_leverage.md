# Bar-Level High-Leverage Findings: XAUUSD / US30 / USDJPY 15min

**Panel:** 2022-01-02 → 2026-04-19, ~52 months, 15-min bars (UTC, converted to NY for session work).
**Bar counts:** XAUUSD 101,461 / US30 101,245 / USDJPY 106,820. Zero NaNs, zero duplicates.
**Strategies:** LOCKED. Findings feed re-MC, allocation, and overlay decisions only — no parameter-change route.
**Rule 0 verification:** CSV span matches 52-mo Pepperstone calibration window; price ranges (gold $1,615-$5,602, US30 28,574-50,541, USDJPY 113-162) consistent with 2022-2026.

---

## Executive summary — top 3 findings by decision impact

1. **XAUUSD has undergone a structural regime shift in 2026 YTD that is not visible in any single-instrument backtest.** Annualized vol has gone from a 2022-2025 mean of ~13% to 31-34% YTD 2026 (KS p=0.0018; Levene p<1e-21). The shift is distribution-wide, not outlier-driven: removing the top 5 absolute moves still leaves 2026 vol at 26.9% vs 13.4% prior. 15-min mean bar range went from $5.66 (2025) to **$15.22 (2026)** — a 2.7× scale-up that is fully invisible to a multi-year backtest's averaged metrics. Three of the top 10 worst weekly XAUUSD blocks in the entire 52-mo panel are in 2026 YTD (which is only 6.7% of the panel by week count).

2. **Joint pairwise correlation has shifted in 2026 YTD, but tail co-movement has not.** XAUUSD-US30 corr went from 0.10 (2024-25) to 0.31 (2026); US30-USDJPY flipped sign from +0.13 to −0.22. However, conditional correlation on high-vol days (175 such days, 13% of panel) is statistically identical to calm days. Joint-3-negative-by-1σ occurred 1 time in 1,335 days. The structural diversification thesis holds at the extreme tail; the level shift may be benign (everything moves together more) but warrants monitoring.

3. **Bootstrap underestimates sequential-bad-week probability for XAUUSD and US30 due to vol clustering.** ACF of |daily ret| at lag 5 — which crosses portfolio_mc.py's 5-day non-overlapping block boundaries — is 0.23 for gold and 0.17 for US30 (vs 0.08 for JPY, which is fine). The Mon-anchored block bootstrap preserves intra-week clustering but treats weeks as exchangeable. They aren't. The 5% static DD cap is most threatened by sequential cluster, not single-day shocks; the MC's bust % may be optimistic for clustered sequences in gold and US30.

**See `/home/claude/analysis/figures/00_gold_regime_shift.png` for the headline chart.**

---

## TIER 1 — Re-MC trigger candidates

### 1.1 XAUUSD regime shift in 2026 YTD

| Metric | 2022 | 2023 | 2024 | 2025 | **2026 YTD** |
|---|---:|---:|---:|---:|---:|
| Annualized vol % | 13.6 | 12.1 | 13.2 | 16.7 | **33.9** |
| Daily true range, mean % | 1.26 | 1.09 | 1.22 | 1.54 | **2.92** |
| Daily true range, p95 % | 2.38 | 2.24 | 2.34 | 3.23 | **7.31** |
| Daily IQR (25-75%) | 0.90 | 0.79 | 0.86 | 1.03 | **1.94** |
| Mean 15-min bar range $ | 2.33 | 2.06 | 2.94 | 5.66 | **15.22** |

KS test 2026 vs prior years pooled: D=0.20, **p=0.0018**. Levene's test on |returns|: p=2.6×10⁻²². Highly significant. Vol ratio 2.40×.

**Outlier-removed verification.** Drop top 5 |ret| in each cohort: 2026 still at 26.9%, prior at 13.4%. Shift is broad-based, not driven by a few headlines.

**Worst weekly XAUUSD blocks** (Mon-anchored 5-day, matches `portfolio_mc.py` methodology):

| Rank | Week | Return | Year |
|---:|---|---:|---:|
| 1 | 2026-03-16 | **−13.27%** | 2026 |
| 2 | 2026-01-26 | −7.70% | 2026 |
| 3 | 2026-03-02 | −4.94% | 2026 |
| 4 | 2025-10-20 | −4.57% | 2025 |
| 5 | 2023-12-04 | −4.26% | 2023 |

**3 of top 10 worst weeks are in 2026 YTD** despite 2026 being only 6.7% of panel weight. The single worst week (-13.27%) is 1.7× the second-worst.

**Implication for `portfolio_mc.py`.** The week-block bootstrap samples weeks uniformly across the 224-week panel. In a 32-week challenge horizon, expected 2026-style weeks drawn ≈ 2.1. The lock baseline (92.73% pass / 0.65% bust / p99 DD 4.94%) is a panel average. If the 2026 regime persists rather than mean-reverts, the live forward distribution will be materially worse than the locked anchor. This is *not* a strategy-failure signal — Guardian's ATR-based sizing already auto-scales position down with rising ATR (1.55×ATR×lots = $680 SL distance is dynamically held). It is a *calibration-anchor-validity* signal.

**Decision routing.** Does **not** formally trigger re-MC by documented rules: no version bump, allocation in 0.30-0.34% safe band, no `dd_protection` change, <6 months live data accumulated. **However**, recommend a **discretionary regime-sub-panel MC** restricted to 2025-2026 only, to bound where pass/bust would shift if the 2026 regime persists. Output is a sensitivity check, not a re-lock. The locked metrics remain the operational baseline.

### 1.2 Joint pairwise correlation drift in 2026 YTD

| Pair | Full panel | 2024-25 calib mid | **2026 YTD** |
|---|---:|---:|---:|
| XAUUSD-US30 | +0.155 | +0.100 | **+0.313** |
| XAUUSD-USDJPY | −0.348 | −0.277 | −0.240 |
| US30-USDJPY | −0.040 | +0.133 | **−0.216** |

XAUUSD-US30 correlation has tripled in 2026 (gold and equities now move together more — a "everything's a risk asset" signature consistent with macro stress regimes). US30-USDJPY has flipped sign (−0.22).

**Counter-evidence: tail correlation is stable.** Conditioned on at-least-one-instrument moving |z|>2 daily (n=175 days), pairwise correlations are essentially identical to calm-day correlations:

| Pair | Big-move days | Calm days |
|---|---:|---:|
| XAUUSD-US30 | +0.170 | +0.137 |
| XAUUSD-USDJPY | −0.358 | −0.342 |
| US30-USDJPY | −0.021 | −0.073 |

Joint-3-negative days: 101 of 1,335 (7.6%). All-3-negative-by-1σ: **1** in 1,335 (0.07%). Two-or-more-negative-by-1σ: 54 (4.0%). The structural diversification thesis from prior regime analysis holds at the extreme tail.

**Decision routing.** Flag and monitor. Not by itself a re-MC trigger — the level shift could be transient (regime-driven), and the tail behavior that actually drives portfolio bust is unchanged.

---

## TIER 2 — MC assumption violations (methodology, not strategy)

### 2.1 Vol clustering exceeds bootstrap-block independence assumption

ACF of absolute daily returns:

| Symbol | n | lag-1 | lag-5 | lag-10 |
|---|---:|---:|---:|---:|
| XAUUSD | 1,335 | **0.279** | **0.228** | 0.086 |
| US30 | 1,337 | **0.249** | 0.168 | 0.140 |
| USDJPY | 1,341 | 0.123 | 0.081 | 0.051 |

ACF of squared returns is even stronger for gold (lag-1 = 0.483).

`portfolio_mc.py` uses Mon-anchored 5-day non-overlapping blocks, sampled with replacement. This preserves intra-week clustering (lag-1 to lag-4 within a block) but **treats weeks as exchangeable** (lag-5 effectively zero in the bootstrap).

The lag-5 ACF for gold (0.23) and US30 (0.17) is materially > the 95% CI bound (~1.96/√n ≈ 0.054) and matters because the 5% static DD cap is most threatened by sequential cluster, not single-day shock. A bad week followed by another bad week in the empirical data is more likely than the bootstrap reproduces.

**Quantitative impact: unknown without comparison run.** Recommend a methodology-sensitivity run with a **stationary bootstrap** (Politis & Romano 1994; preserves long-range dependency through random block lengths) and compare bust % delta against the current fixed-block result. If delta is <5 bp, current methodology is fine. If >25 bp, methodology revision is justified.

**Decision routing.** Flag for next MC methodology review. Strategies are not in scope.

---

## TIER 3 — Operational findings

### 3.1 DJ30 weekend gap structure (Striker is intraday — confirms design)

| Day-of-week (open) | n | mean % | p95 |abs| | p99 |abs| | max |abs| |
|---|---:|---:|---:|---:|---:|
| Sun open (post-weekend) | 220 | −0.045 | **0.78** | **1.41** | **3.89** |
| Mon | 224 | +0.005 | 0.006 | 0.090 | 0.608 |
| Tue | 224 | 0.000 | 0.006 | 0.009 | 0.012 |
| Wed | 224 | 0.001 | 0.006 | 0.012 | 0.127 |
| Thu | 224 | 0.001 | 0.007 | 0.019 | 0.065 |
| Fri | 221 | −0.001 | 0.006 | 0.013 | 0.120 |

Striker trades Tue/Fri intraday, so weekend gaps don't apply to held positions. Weekday open gaps are negligible (max 1.2 bp on Tue, the relevant Striker day). **Confirms: intraday-only Striker design correctly avoids the only material US30 gap regime in the data.**

### 3.2 DJ30 intraday-range distribution and Striker −2% day-stop calibration

US30 days with intraday range > 2.0%: **175 of 1,338 (13.1%).** By year:

| 2022 | 2023 | 2024 | 2025 | 2026 YTD |
|---:|---:|---:|---:|---:|
| 95 | 14 | 17 | 33 | 16 |

The −2% day-stop is well-calibrated against the 2022 cascade pattern (95 high-range days). In 2025 (33 days, ~13% of trading days) and 2026 YTD (16/93 ≈ 17%), the activation rate is in line with the long-run average. **Stop-rule coverage is regime-stable.**

### 3.3 Session-edge maps — alignment is broad, hour-blocks are not bar-validatable

Session boundaries (NY hours) align well with the realized vol distribution per symbol — Guardian/Striker/Aegis all open near intraday vol peaks (NY equity open + late London) and end during lunchtime cooling-off. See `figures/04_session_maps.png`.

**However: specific hour-blocks (Mon H08, Mon H09, H11, Tue H10, etc.) cannot be validated or invalidated by bar data alone.** Bar character at blocked hours is statistically similar to neighboring unblocked hours.

Example — Aegis 15-min granular bar character (USDJPY, Mon/Tue/Wed):

| Bar | n | mean abs ret bp | p95 |abs| bp |
|---|---:|---:|---:|
| 10:00 | 667 | 8.13 | 29.4 |
| 10:15 | 667 | 5.46 | 15.2 |
| 10:30 | 666 | 5.35 | 15.4 |
| **10:45 (BLOCKED)** | 666 | 5.29 | 14.9 |
| **11:00 (BLOCKED)** | 666 | 5.00 | 13.4 |
| 11:15 | 666 | 4.35 | 11.3 |

The 10:45 block has bar character indistinguishable from 10:30 (which is allowed). The H11 hour is mildly elevated vs H12 but not pathologically so. **These blocks are strategy-signal-conditional, not bar-conditional** — they reflect the BB+ATR+session interaction, not raw bar character.

**Null finding.** Bar data does not tell us whether the hour-blocks are robust or overfit. That requires trade-level analysis on the locked Pine, which is out-of-scope for this exercise (strategies LOCKED).

---

## Null findings (saved you from a false signal)

- **Tail correlation breakdown: not present.** High-vol-day pair correlations ≈ calm-day. Diversification thesis intact.
- **All-three-down-by-1σ days: 1 in 1,335 (0.07%).** Empirical joint tail is extremely thin.
- **US30 and USDJPY 2026 vs prior pooled returns: not significantly different** (KS p=0.29 / p=0.27). Regime drift signal is concentrated in gold.
- **USDJPY vol clustering: weak** (lag-1 ACF 0.12, lag-5 0.08). The Aegis i.i.d.-week assumption holds well enough on USDJPY specifically.
- **Hour-block validation by bar data: inconclusive.** Bar character does not separate blocked from unblocked hours cleanly.

---

## Overlay candidates — and the INQHIORI hurdle

The locked stance is no overlays: strategies are inherently regime-adaptive via EMA slope (Guardian), breakout-distance thresholds (Striker), and BB+ATR gates (Aegis). **Bar data does not contradict that.**

The Guardian 1.55×ATR SL with `calcSize` lot sizing means that as ATR rises 7× (the 2023→2026 scale-up), Pine automatically writes 1/7 the lot size for the same $-risk. The vol regime shift is *partially handled by base logic*. Whether it is *fully* handled is an empirical question only live data can answer.

**Candidate (gated by INQHIORI, not a recommendation):** A vol-regime gate on Guardian risk (e.g., reduce 0.34% → 0.25% when XAUUSD 30-day annualized vol exceeds a threshold). This is bar-data-driven, not headline-driven, so it survives the Iran-Hormuz lesson. It would still need to clear:

- Q: Does the gate solve a problem the base logic cannot? (Unknown until live.)
- D: Can the gate be removed? Yes, no strategy code change.
- S: Simpler alternative — just trust the ATR-driven sizing. Already implemented.
- O/A/A: Premature without live evidence.

**Verdict: park as concept, no action.** Live the locked allocation through the new regime; gather data; if Guardian PF degrades materially live, re-open the question with INQHIORI.

---

## Re-MC trigger evaluation against documented rules

| Documented trigger | Status |
|---|---|
| 6 months live data accumulated | Not yet |
| Strategy version bump | None pending |
| Allocation outside Guardian 0.30-0.34% safe band | No |
| `dd_protection` constant change | No |

**No documented trigger fires.** Locked baseline (Pass 92.73% / Bust 0.65% / p99 DD 4.94%) remains operational.

**Discretionary recommendation:** Run a **regime-sub-panel MC** sensitivity sweep before the next 6mo re-MC, restricted to 2025-2026 panel only. Purpose: bound the worst-case anchor drift if the current regime persists. Output is informational, not a re-lock. If sub-panel MC shows pass <88% or bust >1.5%, that triggers an early INQHIORI on the locked allocation; otherwise, hold the lock and wait for the formal 6mo trigger.

---

## Reproducibility

- Script: `/home/claude/analysis/bar_analysis.py`
- Outputs: `/home/claude/analysis/*.csv` (regime, KS, joint correlations, tails, vol clustering, gaps, sessions, hour-blocks)
- Figures: `/home/claude/analysis/figures/00_gold_regime_shift.png`, `01_annual_vol.png`, `02_rolling_corr.png`, `03_vol_acf.png`, `04_session_maps.png`
- Stack: pandas, numpy, scipy.stats, statsmodels, matplotlib. No new dependencies.
- Sample sizes and significance levels stated for every numeric finding. Multiple-comparison risk: report uses uncorrected p-values; the headline gold finding is significant enough (Levene p ~10⁻²²) to survive any reasonable correction.
