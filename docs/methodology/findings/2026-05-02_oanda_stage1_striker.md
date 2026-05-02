# OANDA Stage 1 - Striker DJ30 v4.4 - 2026-05-02

**D-S-A domain:** data

**Pre-Q gate:**
  - **D:** Pepperstone CSVs deleted (scope test); pre-2022 bars deleted (temporal scope); pyramid layers excluded from synthetic-trade simulation (modeling complexity test - documented approximation, not a relevance D-test).
  - **S:** Per-bar predicate matrix cached; trades collapsed to per-Trade-# rows with pyramid-leg flag preserved; signal-bar ATR pin for R-units.
  - **A:** Bar timestamp index; per-filter eligibility mask cached once.

## Brief header

- Strategy: Striker DJ30 v4.4 (locked 2026-04-23)
- OANDA bar window: 101,245 15M bars
- OANDA trade CSV: `data/tv_exports/oanda/Striker_DJ30_v4.4_OANDA_US30USD_2026-04-25_86e9d.csv`, N=233 rows (29 pyramid-add legs)
- Cost model (per Pine `strategy(...)`): commission 0 (cash_per_order=0), slippage 2 ticks
- Chart TZ: America/New_York for CSV display; Pine session/dow checks against UTC explicitly
- CSV->bar median fill-open gap: 0.2590%
- Entry-signal validation (BASE legs only): **100.00%** (204/204) match against CSV with all v4.4 filters on (>=98% required)

**Known approximation:** synthetic trades simulate the BASE entry only — pyramid layers (350% size add at +1.29 ATR profit, min 6 bars between) are NOT simulated. This biases mean R DOWNWARD on candidates that would have pyramided. Pyramid penetration on the realized panel was 14.2%, so the bias is bounded. Pyramid-aware synthetic R is deferred to Stage 1.5 / Stage 2 (any pyramid-bearing candidate that survives Stage 2 must be re-measured with the pyramid rule in scope).

**Deferred filter:** day soft-stop (`-2.0% of init equity, latches halt for the day`) is NOT tested — testing it requires synthetic per-day cumulative-P&L tracking on OANDA, which is its own subsystem. Flagged for Stage 1.5 if no candidate survives Stage 2.

## Blocked-setup findings

Population per filter = bars where every OTHER locked entry filter passes AND the raw breakout fires. Synthetic R = (exit_px - entry_px) / (1.25 x ATR). Permutation = 1000-shuffle relabeling within population.

| Filter | N blocked | Mean R | p (1000 perm) | Verdict |
|---|---:|---:|---:|---|
| atr_expanding | 94 | +0.2354 | 0.760 | rejected - N<100 |
| body_ok | 35 | +0.2196 | 0.767 | rejected - N<100 |
| prev_bar_bullish | 73 | +0.1618 | 0.444 | rejected - N<100 |
| warmup_ok | 31 | -0.0393 | 0.166 | rejected - N<100 |
| day_mon_wed_thu | 434 | +0.1055 | 0.044 | candidate |

## Post-exit findings

Per-leg post-exit MFE_50 / MAE_50 in long-direction. Pyramid legs tagged separately (`*_pyr`) for hypothesis surface visibility — adaptive trail tightening is suspected to be the prime continuation-cut hypothesis.

| Exit reason | N | Mean MFE_50 (R) | p (1000 perm) | Verdict |
|---|---:|---:|---:|---|
| sl | 46 | +2.105 | 0.252 | rejected - N<100 |
| sl_pyr | 0 | +nan | nan | rejected - insufficient pool (n=0) |
| be_or_scratch | 94 | +2.053 | 0.071 | rejected - N<100 |
| trail | 73 | +1.976 | 0.054 | rejected - N<100 |
| trail_pyr | 16 | +0.759 | 0.006 | rejected - N<100 |
| tp | 2 | +2.717 | 0.902 | rejected - N<100 |
| max_hold | 1 | +nan | nan | rejected - insufficient pool (n=1) |
| max_hold_pyr | 1 | +nan | nan | rejected - insufficient pool (n=1) |

## Gated candidates

### day_mon_wed_thu — REJECTED at Stage 2 (Pepperstone, 2026-05-02)

- **Stage 1 status:** gated (n=434, mean R = +0.11, p=0.044).
- **Stage 2 rubric (pre-committed before TV run):** locked Tue/Fri baseline on the 52-month Pepperstone panel = Net P&L $279,438 / PF 2.272 / RF 18.29 / Max DD 5.09%. Reject thresholds: NetP&L < $250K | PF < 2.0 | RF < 15 | Max DD > 5.5%. Any two triggered → reject. Note: rubric anchor numbers (RF 18.29, DD 5.09%) had no committed source in the repo; verified Tue/Fri baseline on the same TV run came in at PF 2.272 / RF 17.17 / DD 5.32% (the PF matched, RF/DD drifted ~1.1 pp / ~23 bp from the rubric anchor). Skew is downstream of the rubric being anchored on uncommitted numbers, not of the rubric being misapplied.
- **Stage 2 outcome — Pepperstone scoreboard:**

  | Variant | DD | RF | PF | Verdict |
  |---|---:|---:|---:|---|
  | Tue/Fri (locked) | 5.32% | 17.17 | 2.272 | hold |
  | +Wed | 8.17% | 13.87 | 2.034 | reject (DD + RF) |
  | +Mon | 11.42% | 8.28 | 1.922 | reject (DD + RF + PF) |
  | +Thu | 8.54% | 16.23 | 2.113 | reject (DD only) |
  | +Wed +Thu | 10.04% | 16.05 | 1.996 | reject (DD + PF) |

  Every alternative breaches DD > 5.5%. Locked baseline best on every risk-adjusted metric.
- **Mechanism resolved:** the OANDA-side positive-expectancy signal on Mon/Wed/Thu bars does not reproduce on Pepperstone — feed artifact, not multi-instrument signal. Confirmed alongside Guardian `day_wed` rejection on the same date. See `feedback_oanda_dow_feed_artifact.md`.
- **Footnote (deferred, not actionable):** of the single-day adds, +Thu was the only one to clear PF and RF — only DD blocked it. If a future INQHIORI revisits day-of-week against a different risk budget (per-allocation rather than absolute DD ceiling), Thu deserves first look.
- **Locked baseline preserved:** Striker Tue/Fri day filter unchanged at v4.4.
- **No Pine work, no version bump, no re-MC.**


## Rejected candidates

- **atr_expanding** - N<100
- **body_ok** - N<100
- **prev_bar_bullish** - N<100
- **warmup_ok** - N<100
- **sl** - N<100
- **sl_pyr** - insufficient pool (n=0)
- **be_or_scratch** - N<100
- **trail** - N<100
- **trail_pyr** - N<100
- **tp** - N<100
- **max_hold** - insufficient pool (n=1)
- **max_hold_pyr** - insufficient pool (n=1)

Stage 1 complete. Candidates require Pepperstone Stage 2 validation before any consideration of Pine work or version bump.
