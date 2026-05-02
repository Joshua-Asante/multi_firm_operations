# OANDA Stage 1 — Aegis USDJPY v4.3 — 2026-05-02

**D-S-A domain:** data

**Pre-Q gate:**
  - **D:** Pepperstone CSVs deleted (scope test); pre-2022 bars deleted (temporal scope).
  - **S:** Bars indexed by UTC, signals collapsed to per-bar booleans, trades collapsed to per-trade rows with pre-computed signal-bar ATR (R-unit pin).
  - **A:** Bar timestamp index; per-filter eligible-population mask cached once per filter.

## Brief header

- Strategy: Aegis USDJPY v4.3 (locked 2026-04-23; sole change vs v4.2 = EOM days 29-31 block)
- OANDA bar window: 106,820 15M bars
- OANDA trade CSV: `data/tv_exports/oanda/Aegis_USDJPY_v4.3_OANDA_USDJPY_2026-04-25_7ee6b.csv`, N=123
- Cost model (per Pine `strategy(...)`): commission 0.003% per side, slippage 2 ticks (0.0020 JPY)
- Chart TZ: America/New_York (DST-aware); CSV->bar median fill-open gap 0.0008% over 10 trades
- Entry-signal validation: **100.00%** (123/123) match against CSV with all v4.3 filters on (≥98% required)

## Blocked-setup findings

Population per filter = bars where the BB-cross signal is hot AND the trading-session/day/vol filters pass AND every *other* locked filter passes. Within that population, 'blocked' bars = bars rejected by the filter under test. Synthetic R = (exit_px − entry_px) / (1.42 × ATR). Permutation = 1000-shuffle relabeling within the population.

| Filter | N blocked | Mean R | p (1000 perm) | Verdict |
|---|---:|---:|---:|---|
| eom | 24 | -0.2795 | 0.009 | rejected — N<100 |
| tue_h10 | 74 | 0.1394 | 0.383 | rejected — N<100 |
| h11_or_1045 | 121 | 0.0871 | 0.118 | rejected — p>=0.05 |

## Post-exit findings

Per CSV exit, MFE_50 and MAE_50 are taken from the next 50 bars of OANDA price history in the long-direction (continuation = up for long-only Aegis). Normalized to R-units using the signal-bar ATR × 1.42. Null pool = 2000 random non-trade-window 50-bar windows from the same bar history; excursion converted to R using the panel-median R-unit.

| Exit reason | N | Mean MFE_50 (R) | p (1000 perm) | Verdict |
|---|---:|---:|---:|---|
| sl | 7 | 1.626 | 0.289 | rejected — N<100 |
| be_or_scratch | 84 | 1.989 | 0.023 | rejected — N<100 |
| intra_band | 1 | nan | nan | rejected — insufficient pool (n=1) |
| tp | 28 | 2.267 | 0.527 | rejected — N<100 |
| max_hold | 3 | 0.764 | 0.135 | rejected — N<100 |

## Gated candidates

_None._ All tested filters and post-exit subsets failed Stage 1 gating (N≥100, p<0.05, |effect| above cost floor). This is the discipline working — see `feedback_overlay_trigger_discipline.md`: Stage 1 is hypothesis-generation, not action.

## Rejected candidates

- **eom** — N<100
- **tue_h10** — N<100
- **h11_or_1045** — p>=0.05
- **sl** — N<100
- **be_or_scratch** — N<100
- **intra_band** — insufficient pool (n=1)
- **tp** — N<100
- **max_hold** — N<100

Stage 1 complete. Candidates require Pepperstone Stage 2 validation before any consideration of Pine work or version bump.
