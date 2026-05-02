# OANDA Stage 1 - Guardian Gold v5.5 - 2026-05-02

**D-S-A domain:** data

**Pre-Q gate:**
  - **D:** Pepperstone CSVs deleted (scope test); pre-2022 bars deleted (temporal scope).
  - **S:** Per-bar predicate matrix (entry_signal, in_session, day_ok, every hour-block) cached once; trades collapsed to per-trade rows with signal-bar ATR (R-unit pin).
  - **A:** Bar timestamp index; per-filter eligibility mask cached once; H12 day-latch precomputed.

## Brief header

- Strategy: Guardian Gold v5.5 (locked 2026-04-23; risk re-locked 0.30% -> 0.34% same day)
- OANDA bar window: 101,461 15M bars
- OANDA trade CSV: `data/tv_exports/oanda/Guardian_Gold_v5.5_OANDA_XAUUSD_2026-04-25_9ae1f.csv`, N=200
- Cost model (per Pine `strategy(...)`): commission 0 (cash_per_order=0), slippage 3 ticks
- Chart TZ: America/New_York (DST-aware); CSV->bar median fill-open gap 0.0023%
- Entry-signal validation: **99.00%** (198/200) match against CSV with all v5.5 filters on (>=98% required)

## Blocked-setup findings

Population per filter = bars where the EMA-recovery signal is hot AND session/day filters pass AND every *other* locked filter passes. Synthetic R = (exit_px - entry_px) / (1.55 x ATR), with grace-stop bar-1 mechanic preserved. Permutation = 1000-shuffle relabeling within the population.

| Filter | N blocked | Mean R | p (1000 perm) | Verdict |
|---|---:|---:|---:|---|
| tue_h08 | 51 | +0.8207 | 0.350 | rejected - N<100 |
| mon_h08 | 38 | +0.1517 | 0.151 | rejected - N<100 |
| mon_h09 | 40 | +1.2203 | 0.674 | rejected - N<100 |
| mon_h12 | 0 | +nan | nan | rejected - insufficient pop (n=0) |
| tue_h12 | 0 | +nan | nan | rejected - insufficient pop (n=0) |
| thu_h12 | 0 | +nan | nan | rejected - insufficient pop (n=0) |
| h12_day_latch | 62 | +1.2667 | 0.677 | rejected - N<100 |
| day_wed | 286 | +0.4277 | 0.005 | candidate |
| day_fri | 215 | +1.3804 | 0.616 | rejected - p>=0.05 |

## Post-exit findings

Per CSV exit, MFE_50 / MAE_50 over the next 50 bars in long-direction. R-units use signal-bar ATR x 1.55. Null pool = 2000 random non-trade-window 50-bar windows, excursion R = mfe_px / panel-median R-unit (approximation since random anchors have no per-window signal-bar ATR).

| Exit reason | N | Mean MFE_50 (R) | p (1000 perm) | Verdict |
|---|---:|---:|---:|---|
| grace_sl | 1 | +nan | nan | rejected - insufficient pool (n=1) |
| sl | 155 | +2.523 | 0.229 | rejected - p>=0.05 |
| scratch | 0 | +nan | nan | rejected - insufficient pool (n=0) |
| trail_or_intra | 26 | +3.487 | 0.435 | rejected - N<100 |
| tp | 0 | +nan | nan | rejected - insufficient pool (n=0) |
| max_hold | 15 | +1.198 | 0.094 | rejected - N<100 |

## Gated candidates

### day_wed

- **Mechanism (one falsifiable sentence):** _author after candidate review._
- **Locked baseline:** see Pine source `strategies/guardian/guardian_gold_v5.5.pine`.
- **Proposed direction:** removal / loosening / tightening (case-by-case).
- **Position-gate interaction:** _flag if candidate change alters per-day eligibility (Guardian max 2/day cap interacts with hour-block removal)._
- **Range proposal:** _bounded post-Stage-2 - Stage 1 emits the candidate, not the parameter value._


## Rejected candidates

- **tue_h08** - N<100
- **mon_h08** - N<100
- **mon_h09** - N<100
- **mon_h12** - insufficient pop (n=0)
- **tue_h12** - insufficient pop (n=0)
- **thu_h12** - insufficient pop (n=0)
- **h12_day_latch** - N<100
- **day_fri** - p>=0.05
- **grace_sl** - insufficient pool (n=1)
- **sl** - p>=0.05
- **scratch** - insufficient pool (n=0)
- **trail_or_intra** - N<100
- **tp** - insufficient pool (n=0)
- **max_hold** - N<100

Stage 1 complete. Candidates require Pepperstone Stage 2 validation before any consideration of Pine work or version bump.
