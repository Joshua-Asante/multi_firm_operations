# Gate audit — H-NYFBO Inquire-phase G1 kill

**Date:** 2026-05-02
**Loop:** INQHIORI — H-NYFBO single-config falsification (Inquire phase)
**Parent brief:** [docs/methodology/findings/2026-05-02_eurusd_m15_lnyo_notice.md](../../findings/2026-05-02_eurusd_m15_lnyo_notice.md)
**Inquire-entry handoff:** [docs/methodology/findings/2026-05-02_eurusd_m15_lnyo_inquire_entry.md](../../findings/2026-05-02_eurusd_m15_lnyo_inquire_entry.md)
**Verdict:** **KILL — G1 fail; structural across all three regimes**
**Routing:** **G4 (abandon EURUSD M15 in this slot for NYFBO mechanism)**; G2/PDSB open as conditional next candidate (different signal source) but with degraded prior — see §5.

---

## 0. Session-isolation disclosure

Per parent brief §0, the Inquire session is meant to perform its own Rule-0 reads. This Inquire phase was executed inside the same Claude Code session that authored this audit-trail's planning brief (user chose "continue here" at plan ExitPlanMode); Rule-0 production sources were re-read live in this session, but the parent brief itself was loaded into context during planning. This weakens the session-isolation guarantee. Mitigation: Pine line numbers and DOW filters were independently re-grepped at the start of Phase A; the load-bearing facts in §0 were stated in own words from the source files, not from the brief. The structural verdict (negative edge in all three regimes) is robust to session-isolation slippage because it is a measurement, not an interpretation.

## 1. Hypothesis tested

H-NYFBO (parent brief §4): On EURUSD M15, fading a failed breakout of the NY-open first-bar range during 09:00–10:30 ET, with ATR-regime filter, produces positive expectancy net of Pepperstone-Razor session-conditional cost, with daily P&L correlation to G/S/A composite below 0.20 over regime-stratified 2022-01-04 → 2026-04-20 panel.

## 2. Configuration (literature-default, parent brief §5 #9)

- Opening range = 09:00 ET 15-min bar (09:00–09:14 ET)
- Failed-breakout signal = price breaks range high or low intrabar, then closes back inside the range within fade window 09:15 → 10:30 ET
- Fade entry = at the close of the bar that closes back inside range
- SL = breakout extreme (range_high for short fade, range_low for long fade)
- TP = range midpoint (first touch)
- Time stop = 10:30 ET
- ATR filter = ATR(14) on M15 percentile-rank gate, threshold = 25th percentile (literature default)
- Costs = Pepperstone-Razor parametric session-conditional spread (0.35 pip/fill baseline; 3× at 08:30 ET data minute; 10× at NFP first minute)
- Two-sided breakouts within the fade window were skipped (ambiguous direction)

## 3. Panel

- Source: Dukascopy M15 EURUSD bid+ask via `dukascopy-python` v4.0.1
- Range: 2022-01-04 00:00 UTC → 2026-04-21 00:00 UTC
- Rows: 107,058 M15 bars
- bid ≤ ask invariant: 100.00%
- DST sanity: 09:00 ET = 13:00 UTC pre-Mar transition + post-Mar transition; 09:00 ET = 14:00 UTC post-Nov transition. All 8 transition spot-checks consistent with IANA `America/New_York` zoneinfo handling.

## 4. Per-criterion measurements vs G1 thresholds

| # | Criterion | Threshold | Measured | Verdict |
|---|---|---|---|---|
| 1 | Net edge per trade in `hike_2022` | ≥ +1.5 pips | **−2.70 pips** (n=159) | **FAIL** |
| 1 | Net edge per trade in `hold_2023_24` | ≥ +1.5 pips | **−1.78 pips** (n=228) | **FAIL** |
| 1 | Net edge per trade in `ease_2024_26` | ≥ +1.5 pips | **−1.65 pips** (n=281) | **FAIL** |
| 2 | \|r\| daily P&L vs G/S/A composite \| weekdays | ≤ 0.30 | 0.061 (n=668) | PASS |
| 3 | \|r\| daily P&L vs Striker \| Tue+Fri | ≤ 0.20 | 0.070 (n=277) | PASS |
| 3 | \|r\| Friday-only sub-test | ≤ 0.20 | 0.123 (n=144) | PASS |
| 4 | Trade-day concentration | ≤ 75% | top 42.7% positive days hold 75% of (negative) edge | PASS |
| 5 | Recency 2024-07-01 → 2026-04-20 share | ≥ 25% of total edge | total edge negative; share computation moot | FAIL (logical-NA, not load-bearing) |
| 6 | N ≥ 100 AND permutation p < 0.05 | per brief | N=668, p=0.0000 | PASS |
| §5#6 | DXY \| Guardian-active dow | ≤ 0.30 | −0.033 (n=387) | PASS |

**Permutation gating:** 1000-shuffle sign-permutation. Observed mean = −1.94 pips/trade. Two-sided p = 0.0000. The negative edge is statistically distinguishable from zero — this is not noise.

**Rule 1 small-cell:** All three regimes have n ≥ 25 (minimum 159). No variance inflation applied.

**Hurst sanity (log-returns per memory `feedback_hurst_rs_log_prices_trap.md`):**
- hike_2022: H=0.751
- hold_2023_24: H=0.754
- ease_2024_26: H=0.757

Reading interpretation: H ≈ 0.75 across all regimes (R/S, n_lags up to 20). Consistent with persistent (trending) behavior in EURUSD M15 returns over this panel. **The simple R/S estimator is known to bias high under volatility clustering**; the magnitude is suspect but the cross-regime stability of the reading is meaningful — whatever EURUSD M15 is doing, it's doing it consistently across the panel. The reading is corroborative of the structural kill (a fade strategy in a trending regime should fail), not a load-bearing input.

## 5. Why the kill is structural, not regime-specific

The §6 routing rule: regime-specific failure → G2 (PDSB); structural failure → G4 (abandon EURUSD M15).

This kill is **structural for the NYFBO mechanism**:
- All three regimes fail kill #1 with similar magnitude (−1.6 to −2.7 pips)
- Permutation p=0.0000 shows the negative edge is real, not noise
- Mean negative edge is much larger than the parametric-spread cost (0.7 pip RT) — this is not a "spread > edge" failure where better calibration could rescue it. **Gross edge is also negative**: net = raw − cost, so raw ≈ −1.0 to −2.0 pips before cost.
- Hurst ≈ 0.75 across all three regimes corroborates a structural reason the fade mechanism fails: EURUSD M15 returns are persistent over this panel, so "failed" breakouts often resume in the breakout direction rather than mean-revert.

Calibration uncertainty disclosure (parent brief §9 + plan ExitPlanMode): the Pepperstone-Razor spread model is parametric (literature defaults), not validated against an MT5 export. Per plan §"Calibration uncertainty disclosure", a kill on cost grounds is robust only if edge fails by a wide margin. **Here, gross edge (raw_pips, before cost) is negative in every regime by ≥1 pip** — calibration uncertainty cannot rescue this verdict. Even at zero cost, NYFBO at literature-default parameters has negative gross edge.

## 6. Routing decision

**G4 — abandon EURUSD M15 for the NYFBO mechanism.**

Per parent brief §6 and §7, the routing options on G4 are:
1. (a) GBPUSD M15 same archetype set (~0.4 pip higher cost) — separate Notice phase
2. (b) EURUSD M30/H1 (different timeframe family) — separate Notice phase
3. (c) hold the slot empty until a new Notice phase

PDSB and PDDB remain conditional candidates per parent brief §6 (G2/G3). Parent brief §4 H-PDSB conditional entry rule:

> PDSB only enters Inquire if NYFBO clears its gates **and** PDSB is needed as a decorrelated complement, **or** if NYFBO fails for reasons not generalizable to PDSB.

The NYFBO failure mode (negative gross edge from fading microstructure overreactions in a trending intraday regime) does NOT directly generalize to PDSB (post-news fade on US data prints) — the signal generators are different. PDSB *could* pass. However:
- The Hurst-driven concern (M15 trending behavior) generalizes to any M15 fade mechanism on EURUSD, weakening the prior on PDSB
- PDSB has a higher kill threshold (2.5 pips edge floor; severe slippage around data prints)
- Parent brief §10 #3 already flags 2024-2026 sub-sample size for event-day count
- Parent brief §7: Iran-Hormuz overlay-deactivation lessons hold — do not weaken kill criteria to keep candidates alive

**Recommended next step:** abandon EURUSD M15 (route (c) — hold the slot empty until a new Notice phase). PDSB is open per the conditional rule but with degraded prior; user judgment needed before opening G2.

## 7. Lesson (one line for the regime-marker accumulator)

EURUSD M15 fade-the-failed-breakout has structurally negative gross edge across all three regimes (2022-01-04 → 2026-04-20), corroborated by Hurst ≈ 0.75 — M15 EURUSD trends rather than mean-reverts on the NY-open horizon, and the literature-default NYFBO trade pattern is on the wrong side of that drift.

## 8. Reproducibility

- Pipeline orchestrator: [analysis/eurusd_lnyo/run_h_nyfbo.py](../../../../analysis/eurusd_lnyo/run_h_nyfbo.py)
- Results JSON: [analysis/eurusd_lnyo/results/h_nyfbo_g1.json](../../../../analysis/eurusd_lnyo/results/h_nyfbo_g1.json)
- Dukascopy panel: `data/bar_data/EURUSD_dukascopy_m15_bidask_2022-01-04_to_2026-04-20.csv` (107,058 rows)
- DXY panel: `data/external/dxy.csv` (1079 rows, yfinance `DX-Y.NYB`)
- Per-strategy modules:
  - [analysis/eurusd_lnyo/dukascopy_loader.py](../../../../analysis/eurusd_lnyo/dukascopy_loader.py)
  - [analysis/eurusd_lnyo/pepperstone_spread.py](../../../../analysis/eurusd_lnyo/pepperstone_spread.py)
  - [analysis/eurusd_lnyo/nyfbo_simulator.py](../../../../analysis/eurusd_lnyo/nyfbo_simulator.py)
  - [analysis/eurusd_lnyo/correlation.py](../../../../analysis/eurusd_lnyo/correlation.py)
  - [analysis/eurusd_lnyo/permutation.py](../../../../analysis/eurusd_lnyo/permutation.py)
  - [analysis/eurusd_lnyo/dxy_loader.py](../../../../analysis/eurusd_lnyo/dxy_loader.py)
- Reproduction:
  ```
  python -m analysis.eurusd_lnyo.dukascopy_loader --fetch
  python -m analysis.eurusd_lnyo.dxy_loader --fetch
  python -m analysis.eurusd_lnyo.run_h_nyfbo
  ```

## 9. Out-of-scope reaffirmation (parent brief §7)

No edits made to: Pine strategies (G v5.5 / S v4.4 / A v4.3), `dd_protection.py`, `portfolio_mc.py`, `CLAUDE.md`. No grid search; literature-default single-config only. No allocation, MC re-run, overlay reintroduction, or new strategy code.
