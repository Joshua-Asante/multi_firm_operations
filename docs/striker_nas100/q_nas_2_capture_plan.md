# Q-NAS-2 — 4-week forward gate-state capture plan (Striker NAS100 v1)

**Date authored:** 2026-05-05
**Indicator file:** [strategies/striker/striker_nas100_v1_research.pine](../../strategies/striker/striker_nas100_v1_research.pine)
**Brief:** Striker NAS100 v1 — Phase 4C/6 investigation (rev 2)

## Why this capture exists

The taken-trades log answers "what happened on entries that fired", not "what would today's filtered bar (e.g. ATR_exp −9%, Dist-to-Res ABOVE, body 65.5%) have looked like as a pyramid-spawn candidate." Q-NAS-2 needs the gate state for **every** in-session candidate bar — taken or filtered — so we can compute conditional spawn rates against features only knowable at filter-evaluation time.

Q-NAS-1 Test 3 in this session was scope-reduced to (hour × dow) only because ATR_exp, prior-bar body, and Dist-to-Res are not in the trade CSV. The forward capture from this indicator backfills those features for the next 4 weeks of NAS100 M15 bars, enabling the full conditional-spawn analysis to run on the post-2026-05-05 cohort.

## Capture mechanism

The research indicator emits per-bar plot() series for in-session, in-date bars only. Each plot is exposed via TradingView's "Data Window" (right-click chart → Data Window) and exportable via "Export Chart Data" → Excel/CSV.

Series captured:
- Filter pass/fail flags (8 binary): `is_session_ok`, `is_warmup_ok`, `is_dow_ok`, `is_atr_expanding`, `is_body_ok`, `is_prev_bar_bull`, `is_raw_breakout`, `is_signal`
- First-blocking-filter code: `filter_reason_code` (0 = signal would-fire; 1-8 = first failing filter)
- Numeric features: `atr_val`, `atr_ma`, `atr_exp_ratio`, `body_ratio`, `dist_to_res_atr`, `resistance_lvl`
- Lookback 15-bar OHLC window: `look15_high`, `look15_low`, `look15_range`

For any candidate bar at time T, the **forward** 15-bar window (T..T+15) is reconstructed in pandas by date-shifting `look15_high/low/range` back by 15 bars (i.e., the value emitted at T+15 covers the window ending at T+15, which is bars T..T+15 since the lookback is 16 bars inclusive).

## Operating procedure

1. **Load indicator on NAS100 M15 chart** (TradingView, broker = Pepperstone for parity with the canonical panel).
2. **Confirm dashboard reads** `LOCKED v1.0` defaults — body 0.38, ATR exp 0.28, lookback 15, ATR length 11, ATR MA 85, Mon+Tue allowed (Wed/Thu/Fri blocked).
3. **Set start date** to 2026-05-05 (today) via the "DATE RANGE" input. End date can stay at the 2027-12-31 default.
4. **Run forward** for at least 4 weeks (20 trading days × 4 in-session hours × 4 bars/hour ≈ 320 in-session bars; ~80 of those will be Mon/Tue locked-DOW set; ~60 after warmup ≈ usable candidate-bar count). Larger samples are better — 8 weeks ideal.
5. **Daily hygiene**: glance at the dashboard each session close to confirm the indicator is still running and capturing. If the chart is closed or the indicator is removed, capture stops.

## Export procedure (end of capture)

1. Right-click chart → **"Export Chart Data"** → format CSV.
2. The output includes one column per `plot()` series. Bars where `emit` is false (out of session) carry `na` and can be dropped during ingest.
3. **File naming**: `Striker_NAS100_v1research_PEPPERSTONE_NAS100_<YYYY-MM-DD>_<hash>.csv` — match the TV-export convention so [tv_export_loader.py](../../analysis/oanda_stage1/tv_export_loader.py) MVD-identity gates extend cleanly. (Note `v1research` not `v1` — keeps the research-mode capture distinct from the production trade log.)
4. Place the file under `data/tv_exports/pepperstone/` and add its SHA256 to `SHA256SUMS`.

## Downstream analysis (after 4-week capture)

Author `analysis/striker_nas100/q_nas_2_conditional_spawn.py`. For each row in the export:
- Drop `na` rows (out-of-session bars)
- Bin features: `atr_exp_ratio` tertile × `body_ratio` tertile × `entry_hour_utc` (4 buckets in 13-17 UTC) × `entry_dow` (Mon/Tue locked)
- Define `spawned`: a base-trade bar where `is_signal == 1` AND a subsequent bar within 15 produced a pyramid leg (cross-reference against the TV strategy export from the same period)
- Compute P(spawned | bucket) and the variance-explained share of the partition
- Falsify if spawn rate concentrates in <3 of the buckets (per Q-NAS-1 test 3 spec)

## Sample sizing & re-run cadence

- 4-week minimum: ~60 usable candidate bars in the locked DOW set, possibly ~10-20 of which are pyramid spawners. Tight but interpretable for top-bucket effects.
- 8-week target: roughly doubles the sample; reduces bin-cell sparseness and gives bootstrap CIs that don't blow up.
- After Q-NAS-2 closure: indicator can stay loaded as a passive monitoring tool. New regime shifts (e.g. NAS100 volatility-cluster changes) become detectable from the rolling spawn-rate plot.

## Out of scope

- This indicator does NOT place orders. No equity management, no allocation logic. Strategy-side execution stays at the locked v1.0 file.
- This indicator does NOT mirror BE / trail / pyramid post-entry logic — only entry-gate state matters for Q-NAS-2.
- No backtest replay against pre-2026 data is intended. Forward capture only — historical bars wouldn't add the conditional information that's missing from the trade log (we already have what fired from history).

## Cross-references

- Production strategy (gate-logic source of truth): [strategies/striker/striker_nas100_v1.pine](../../strategies/striker/striker_nas100_v1.pine), entry filter chain at line 197.
- Q-NAS-1 confirmatory analyses (the partial answer this capture extends): [docs/briefs/striker_nas100_q_nas_1_results.md](../briefs/striker_nas100_q_nas_1_results.md).
- TV-export loader (will need a small extension when the research CSV format lands): [analysis/oanda_stage1/tv_export_loader.py](../../analysis/oanda_stage1/tv_export_loader.py).
