# AUDNZD M15 — structural characterization (Phase 2)

**Loop:** `loop_2026-04-26_audnzd_discovery`
**Brief:** AUDNZD candidate-strategy discovery (2026-04-26)
**Phase:** 2 — structural characterization (no strategy hypotheses tested)
**Status:** PASS — proceed to Phase 3 with the framework shortlist in §10

## 1. Provenance

- **Data:** `data/audnzd_oanda_m15_2022-01-01_to_2026-04-26_clean.csv`
- **SHA256:** `6ff6cc3ce9f3f7ac825b2bae8e1d0cd82295564ca909ba6698f523606fba2d92`
- **N bars:** 107,243
- **Window:** 2022-01-02 22:00 UTC → 2026-04-24 20:45 UTC
- **Source:** OANDA practice endpoint, externally validated against Dukascopy
  at three dates (max diff 0.250 pips). See
  [data_provenance/2026-04-26_audnzd_oanda_verification.md](../data_provenance/2026-04-26_audnzd_oanda_verification.md).
- **Numerical pipeline:** [scripts/audnzd_phase2_structural.py](../../../scripts/audnzd_phase2_structural.py).
- **Raw results JSON:** [2026-04-26_audnzd_structural_results.json](2026-04-26_audnzd_structural_results.json).

All measurements below operate on the mid-price `(bid+ask)/2` derived from
the BA-priced candles. Spread analysis uses `close_ask − close_bid`.

## 2. Hurst exponent (R/S of log returns)

R/S is applied to log-return increments, not log prices. (Applying R/S to
log-prices yields a spurious H≈1 because the cumsum of an integrated process
behaves like double-integration; that result is methodologically meaningless
and was caught and corrected before publication.)

| Horizon (M15 bars) | Time | H | 95% CI |
|---:|---:|---:|---:|
| 16 | 4 h | **0.570** | [0.566, 0.575] |
| 64 | 16 h | **0.531** | [0.525, 0.538] |
| 256 | 64 h | **0.517** | [0.514, 0.520] |

Plot: [2026-04-26_audnzd_hurst_rs.png](2026-04-26_audnzd_hurst_rs.png).

**Read:** H is monotonically convergent toward 0.5 with horizon. At long
horizons (64 h) AUDNZD M15 returns are operationally indistinguishable from
random walk increments. The mild >0.5 reading at 4 h is consistent with
volatility clustering inflating R/S without implying directional persistence
of signed returns (see §9.3 ACF lag-1 = −0.078 for the directional signal).

## 3. ADF stationarity

| Series | ADF stat | p-value | nlags |
|---|---:|---:|---:|
| close (price levels) | −0.13 | 0.946 | 13 |
| log returns | −91.95 | < 1e-300 | 12 |

Levels are non-stationary (cannot reject unit root). Log returns are very
strongly stationary (massive rejection). Both consistent with an FX cross
that follows a martingale-like price process at the M15 horizon.

## 4. Volatility profile by NY hour

Median ATR(14) on M15, grouped by NY-time hour:

Plot: [2026-04-26_audnzd_vol_by_hour.png](2026-04-26_audnzd_vol_by_hour.png).

Key numbers (median ATR(14) on mid, 1e-5 = 0.1 pip):

| Hour NY | Median ATR | Notes |
|---:|---:|---|
| 11 | 6.24e-4 | NY morning peak |
| 18 | 5.94e-4 | Asian open (Tokyo just opening) |
| **19** | **6.28e-4** | Asian session climbing |
| **20** | **6.31e-4** | Asian session peak |
| 21 | 5.73e-4 | Asian session continuing |
| 22 | 5.93e-4 | Asian session continuing |
| 14 | 4.07e-4 | NY lunch lull |
| 15 | 3.76e-4 | **Daily lull** |
| 16 | 3.74e-4 | Daily lull / pre-Asia open |

**Peak 3-hour window (NY time):** **18:00 → 21:00** = Tokyo open & early
Asian session. Summed median ATR over the window: 1.85e-3.

This matters because for an AUD/NZD cross both currencies are most actively
priced during APAC hours. The brief's strategy frameworks should respect
this — entries gated to 18:00–22:00 NY are entries during the regime where
the instrument actually trades.

## 5. Spread profile by NY hour

Plot: [2026-04-26_audnzd_spread_by_hour.png](2026-04-26_audnzd_spread_by_hour.png).

Median overall: **2.60 pips**. By hour, spreads are flat at 2.5–3.0 pips
across all 24 NY hours **with one exception**:

| Hour NY | Median spread (pips) |
|---:|---:|
| 17 | **10.20** |

Hour 17 NY (= 22:00 UTC) is the OANDA daily rollover hour: spread blowout
is a known broker artefact, not a real market wide-spread regime.

**Hours flagged as median > 2× overall median: [17]** — exactly the rollover
hour, exactly as expected. Any strategy framework on this instrument must
hard-exclude entries at hour 17 NY.

(Caveat from Phase 1: practice-feed p99 spread is inflated to 17.5 pips
overall vs the 15.0-pip threshold the brief specified for live data. That
inflation is concentrated in the tail and largely co-located with hour 17
rollover; medians-by-hour outside hour 17 are clean.)

## 6. Day-of-week effects

Daily ATR (close-of-day high − low) and daily return (bps), by DOW
(0=Mon, 6=Sun):

| DOW | n | Mean daily return (bps) | Std (bps) | Mean daily range (pips) |
|---|---:|---:|---:|---:|
| Mon (0) | 225 | +1.66 | 25.1 | 47.6 |
| Tue (1) | 225 | +0.76 | 29.9 | 54.0 |
| **Wed (2)** | 225 | **+2.74** | **36.2** | **59.7** |
| Thu (3) | 225 | +1.33 | 26.5 | 51.4 |
| Fri (4) | 225 | −2.10 | 29.6 | 49.5 |
| Sun (6) | 222 | +1.86 | 9.1 | 26.0 |

Plot: [2026-04-26_audnzd_dow.png](2026-04-26_audnzd_dow.png).

**Read:** Wednesday is the highest-vol weekday by a clear margin (60-pip
range vs 48-54 elsewhere). Sunday's sample is the partial-session bar
(market opens late Sunday NY); its 26-pip range and 9-bps std are not
comparable to weekday vol — Sunday should be excluded from any framework
that doesn't model partial sessions explicitly.

DOW return means (1.66 bps … 2.74 bps) are within ±0.1σ of zero relative
to their stds — no DOW shows a tradable directional bias.

## 7. Range vs trend day classification

Per daily bar, `dir = (close − open) / ATR14_daily`:

- n days analysed: **1,334**
- **Trend days |dir| > 1.0: 10.2%**
- **Range days |dir| < 0.3: 42.7%**
- Mid-direction days: 47.2%
- Mean |dir|: 0.467
- Median |dir|: 0.364

Plot: [2026-04-26_audnzd_range_trend.png](2026-04-26_audnzd_range_trend.png).

**Read:** AUDNZD is overwhelmingly range-biased at the daily resolution.
Only 1 in 10 days produces a clean directional move >1 daily ATR; over
4 in 10 days the close ends within 30% of the daily ATR of the open.
This is the strongest single regime signal in the fingerprint.

## 8. RBA + RBNZ decision-day vol expansion

Decision dates in the window (best-effort from public schedules; accuracy
sufficient for an aggregate-ratio test):

- RBA: n=40 dates 2022-02-01 → 2026-04-01
- RBNZ: n=30 dates 2022-02-23 → 2026-04-08

Comparison metric: daily summed true range (sum of M15 TRs over the UTC
day), restricted to actual market days.

| Cohort | n | Mean daily summed TR | Ratio to baseline |
|---|---:|---:|---:|
| Non-decision baseline | 1264 | 0.0380 | 1.00× |
| RBA decision day | 40 | 0.0639 | **1.68×** |
| RBNZ decision day | 30 | 0.0734 | **1.93×** |

**Read:** Both central-bank decision days exhibit ~70-90% ATR expansion
versus baseline. This is the AUDNZD analogue of the BOJ-Aegis pause rule:
a binary-event volatility regime that any candidate framework must either
explicitly pause around (recommended) or model with a live-event scaler.
It is not a strategy edge to chase.

The 1.68× / 1.93× ratios are large enough that decision days are
operationally pause-worthy regardless of which framework Phase 3 selects.

## 9. ACF of log returns

| Lag (M15 bars) | Time | ACF |
|---:|---:|---:|
| 1 | 15 min | **−0.0784** |
| 5 | 75 min | −0.0047 |
| 20 | 5 h | −0.0059 |
| 96 | 24 h | +0.0071 |

95% CI band ≈ ±0.0060 (1.96/√107243).

Plot: [2026-04-26_audnzd_acf.png](2026-04-26_audnzd_acf.png).

**Read:** A clean, statistically significant negative autocorrelation at
lag 1 (−0.078, ~13× CI). At lags 5, 20, 96, ACF is at or just outside the
95% noise band — no operationally tradable signal at those horizons.

The lag-1 mean-reversion is the primary directional structural feature of
this instrument at M15. It is consistent with:
- 42.7% range-day rate (§7)
- ADF strongly stationary returns (§3)
- Hurst convergent to 0.5 at long horizons (§2)

## 10. Synthesis — ranked framework candidates

| Rank | Framework | Rationale | Phase 3 inclusion |
|---|---|---|---|
| **1** | **Aegis-style BB+ATR mean reversion** | Range-biased daily structure (§7); negative lag-1 ACF (§9); strong session vol concentration for entry timing (§4); decision-day pause precedent in the existing portfolio (§8). The four pillars of Aegis-style trade selection — range, mean-reversion at the entry horizon, identifiable peak-vol session, binary-event filter — are all present and quantified. | **Yes (primary)** |
| **2** | **Range-fade with regime gate** | Same instrument-structure fit as Aegis-style but with a different exit philosophy. If Aegis-style fails OOS due to BB-vs-mean threshold sensitivity, range-fade is the second-best fit. | **Yes (secondary)** |

**Two frameworks tested in Phase 3.** Three or more would be data dredging
across one instrument; one would leave Phase 3 with no fallback if the
primary fails OOS for parameter-sensitivity reasons.

## 11. Counter-synthesis — frameworks the structural fingerprint rejects

The brief's instruction is that this section matters more than §10. Each
rejection is grounded in a quantified structural feature, not in prior
belief about the instrument.

| Rejected framework | Why the structure rejects it |
|---|---|
| **EMA-cross trend (Guardian-style)** | 10.2% trend-day rate (§7) means an EMA-cross trend rider catches the wrong regime ~9 of 10 days. Convergent Hurst to 0.5 (§2) and lag-1 ACF = −0.078 (§9) both contradict trend persistence at any tested horizon. Including this even as a null check would burn Phase 3 budget on a foregone conclusion. |
| **Striker-style breakout + pyramid** | Pyramiding is doomed in a range-biased instrument. The 47.6%–59.7% mean daily range across weekdays sets a hard ceiling on follow-through magnitude that pyramid-add geometry assumes is unbounded. Wednesday's elevated range (§6) is not enough to compensate. |
| **ORB session breakout** | The peak-vol Asian session (§4) does host directional volatility, but only 10% of days produce true trend moves (§7); ORB breakouts in a range-biased product fail more than they succeed. The framework is admissible per the brief but would need a regime gate stronger than its own — at which point it becomes a worse-instrumented version of mean reversion. |
| **Donchian channel reversion** | Not rejected on structural grounds — it would fit the regime — but it is **redundant with Aegis-style BB+ATR**. Two mean-reversion frameworks differ only in how they parameterize the band; testing both is dimension-collapsing duplication of the same underlying hypothesis. Donchian is held in reserve for follow-up if Phase 3 produces 4A. |

The H slightly above 0.5 at short horizons (§2) is **not** evidence for
trend continuation. Reading H = 0.57 as "trending" is the forbidden D-test
shape — it would encode a strategy hypothesis (trend persistence) into
what is actually a vol-clustering artefact of R/S on returns. The lag-1
ACF (which measures directional persistence directly) is unambiguously
negative.

## 12. S preservation test (brief §2.3)

> If a reader of the synthesis cannot tell what regime AUDNZD exhibits, S
> has compressed away the signal. Revert and use a richer representation.

A reader who has read sections 2–9 can answer the regime question:

> AUDNZD M15 over 2022-01-02 → 2026-04-24 is a range-biased mean-reverting
> cross with negative lag-1 return autocorrelation, near-random-walk
> long-horizon Hurst, peak volatility 18:00–21:00 NY (Asian session),
> Wednesday-elevated range, and ~70–90% ATR expansion on RBA/RBNZ decision
> days that should be filtered out.

That is a structural answer with quantified supports for every adjective.
**S preservation: PASS.** Phase 3 may proceed.

## 13. Carryover caveats from Phase 1

- Practice-feed spread tail inflation: at the median-by-hour resolution
  (§5) only hour 17 NY (rollover) is materially affected. Tradable hours
  at the typical entry horizons (§4 peak window 18–21 NY) show clean
  median spreads of 2.6–3.0 pips. No re-mediation needed in Phase 3
  beyond the planned 2-pip slippage haircut on edge candidates.
- All Phase 4 verdicts will inherit the practice-vs-live generalization
  caveat per the data provenance file §8.

## 14. Cross-references

- Phase 1 provenance: [data_provenance/2026-04-26_audnzd_oanda_verification.md](../data_provenance/2026-04-26_audnzd_oanda_verification.md)
- Brief: AUDNZD candidate-strategy discovery (2026-04-26)
- 1R estimation methodology: [methodology/1r_estimation.md](../1r_estimation.md)
- Observation routing: [methodology/observation_routing.md](../observation_routing.md)
- INQHIORI ⊕ The Algorithm gate discipline: skill `inqhiori-algorithm`

## 15. Forbidden-D-test audit (gate discipline)

Per inqhiori-algorithm §5, the structural characterization step did not
encode any of the forbidden tests:

- ❌ "Does this bar fit a mean-reversion model?" — not asked. The
  mean-reversion finding falls out of independent measurements (lag-1 ACF
  and §7 range-day rate); it is observed, not assumed.
- ❌ "Is this period a known regime break?" — not asked. The full window
  is processed uniformly; no period-specific deletions or weightings.
- ❌ "Does Aegis methodology fork cleanly here?" — not asked at the data
  level. The decision in §10 to forward Aegis-style as the primary
  candidate is downstream of the structural fingerprint, not upstream of
  it.

One adjacent forbidden test was caught and corrected during execution:
the initial Hurst implementation applied R/S to log-prices (an integrated
process), yielding spurious H ≈ 1.0. This was caught at sanity-check
(H bounded by [0,1] structurally) and corrected to operate on log
returns. The corrected analysis is what is reported above. No silent
substitution: the bug + fix are documented here for audit.
