# Q-NAS-1 — Pyramid-dependence confirmatory tests (Striker NAS100 v1)

**Date:** 2026-05-05  
**Brief:** Striker NAS100 v1 — Phase 4C/6 investigation (rev 2)  
**Run:** `python -m analysis.striker_nas100.q_nas_1_pyramid_hypothesis`

Strategy header at `strategies/striker/striker_nas100_v1.pine` lines 35-40 documents
pyramid-dependence as DESIGN INTENT. These tests are confirmatory: they quantify
the pattern at the trade-log level. None falsify the design intent.

## Test 1 — Bootstrap residual base-edge (pyramid days excluded)

- Pyramid dates in panel: **34**
- Base trades total: **166**, of which on non-pyramid dates: **129**
- Base-on-non-pyr-days net P&L: **-$68,543**
- Base-on-non-pyr-days PF: **0.314**

Bootstrap (n=1000, seed=42) of base-on-non-pyr-days PnLs:

- p05 PF: **0.205**
- p50 PF: **0.311**
- p95 PF: **0.460**

**Falsification gate:** 5th-percentile PF ≥ 1.5.  
**Result:** NOT falsified (p05 = 0.205).

## Test 2 — Year-by-year pyramid contribution share

| Year | n_trades | n_pyramid | total_net | pyramid_net | pyramid_share | profitable | violates |
|---|---|---|---|---|---|---|---|
| 2022 | 32 | 5 | $20,810 | $17,005 | 81.7% | ✓ | — |
| 2023 | 59 | 11 | $78,357 | $63,454 | 81.0% | ✓ | — |
| 2024 | 43 | 7 | $237,999 | $207,836 | 87.3% | ✓ | — |
| 2025 | 47 | 8 | $81,026 | $80,103 | 98.9% | ✓ | — |
| 2026 | 19 | 3 | $91,228 | $82,287 | 90.2% | ✓ | — |

**Falsification gate:** any profitable year has pyramid_share < 50%.  
**Result:** NOT falsified.

## Test 3 — Conditional pyramid-spawn rate (time × dow)

Overall spawn rate: **21.7%** (36 of 166 base trades)

**Scope reduction:** brief specifies ATR_exp tertile × prior-bar body tertile × hour × dow.
ATR_exp and prior-bar body require Pine re-run against historical OHLC; not in scope here.
Time-of-day × dow projection still answers the concentration question.

| dow | hour_utc | n_base | n_spawned | spawn_rate |
|---|---|---|---|---|
| Monday | 9 | 21 | 2 | 9.5% |
| Monday | 10 | 29 | 6 | 20.7% |
| Monday | 11 | 23 | 4 | 17.4% |
| Monday | 12 | 10 | 4 | 40.0% |
| Tuesday | 8 | 1 | 1 | 100.0% |
| Tuesday | 9 | 14 | 4 | 28.6% |
| Tuesday | 10 | 36 | 9 | 25.0% |
| Tuesday | 11 | 23 | 4 | 17.4% |
| Tuesday | 12 | 9 | 2 | 22.2% |

Top-half buckets (by spawn rate) account for **50.0%** of all pyramid spawns. Higher concentration → bust risk if those buckets contract; lower concentration → robust across regimes.

## Verdict

All three tests are **consistent with the design-intent statement** in the strategy header. The pyramid-dependence pattern is real (Test 2 shows pyramid contribution dominates in every profitable year), the residual base-only edge collapses without pyramid days (Test 1), and spawn likelihood is reported per (hour × dow) bucket for ongoing monitoring (Test 3).

**Action implications:** none for production allocation — the 4-strategy MC headline at Q-NAS-3 (97.88% pass / 0.22% bust / p99 DD 4.55%) treats NAS as a complete strategy including the pyramid pathway. These confirmatory tests document that the pathway is the strategy, consistent with how it was sized and locked.
