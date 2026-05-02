# USOIL feed reconciliation (OANDA <-> Pepperstone) — Stage 0

**Verdict:** PASS

**Loop:** USOIL 15min behavioral characterization (2026-05-02)
**Brief:** §3 Stage 0 (mandatory feed-equivalence pre-check)
**Plan:** `~/.claude/plans/usoil-15min-behavioral-composed-tower.md`

## Sources

- **OANDA:** WTICO_USD M15 via `lib.oanda.fetch_candles`
- **Pepperstone:** `data\tv_exports\pepperstone\USOIL_pepperstone_m15_2025-06-02_to_2026-05-01.csv`
- **OANDA pull window:** 2025-04-01T00:00:00Z -> 2026-04-20T00:00:00Z
- **Intersection of feed coverage:** 2025-06-01 22:00:00+00:00 -> 2026-04-19 23:45:00+00:00
- **Common bars (within intersection):** 20,751
  - OANDA bars in intersection: 20,764
  - Pepperstone bars in intersection: 20,751
  - OANDA-only bars within intersection: 13
  - Pepperstone-only bars within intersection: 0
  - OANDA bars OUTSIDE intersection (corpus envelope, informational): 3,938
  - Pepperstone bars OUTSIDE intersection (corpus envelope, informational): 912

## 1. Bar-timestamp alignment (within intersection of feed coverage)
- bar_drift_pct: 0.0313% (acceptable < 1%)
- alignment_pass: **True**

## 2. Return correlation per 15min bin (Spearman rho >= 0.95)
- bins_below_floor: 0 of 96 populated bins
- correlation_pass: **True**

## 3. Roll convention (proxy: single-bar |ret| > 5%)
- big_bar_jumps_oanda: 8
- big_bar_jumps_pepperstone: 7
- roll_convention_pass: **True**

## 4. Holiday calendar cross-tab
- days_oanda_only: 51
  - first 10: ['2025-04-01', '2025-04-02', '2025-04-03', '2025-04-04', '2025-04-06', '2025-04-07', '2025-04-08', '2025-04-09', '2025-04-10', '2025-04-11']
- days_pepperstone_only: 11
  - first 10: ['2026-04-20', '2026-04-21', '2026-04-22', '2026-04-23', '2026-04-24', '2026-04-26', '2026-04-27', '2026-04-28', '2026-04-29', '2026-04-30']

## 5. Bar-range profile by 15min bin (informational)

Used as a proxy for spread comparison since neither feed contains BA pricing.
Report only top-10 highest-divergence bins.

| bin | median_range_oanda | median_range_pepperstone | ratio (p/o) |
|---:|---:|---:|---:|
| 2 | 0.0700 | 0.0600 | 0.857 |
| 21 | 0.0800 | 0.0700 | 0.875 |
| 81 | 0.0910 | 0.0800 | 0.879 |
| 88 | 0.1250 | 0.1400 | 1.120 |
| 17 | 0.0680 | 0.0600 | 0.882 |
| 13 | 0.0900 | 0.0800 | 0.889 |
| 87 | 0.0900 | 0.0800 | 0.889 |
| 11 | 0.0900 | 0.0800 | 0.889 |
| 22 | 0.1100 | 0.1000 | 0.909 |
| 15 | 0.0660 | 0.0600 | 0.909 |

## Stop rule outcome

All three load-bearing diagnostics (alignment, correlation, roll convention) PASS.
Proceed to Stage B (Phase 1 fetch + clean + verify).
