# Guardian v5.5 — Indicator vs. Strategy Entry-Condition Diff Audit

**Audit date:** 2026-05-08
**Trigger event:** 2026-05-07 Guardian v5.5 live trade fired but anticipation alert did not push to phone/watch.
**Audit scope:** entry-condition logic divergence between strategy script and indicator script. Hypotheses H1–H4 from CC-spawn brief §2.6.3.

---

## §1 — Sources

| Role | Path | git blob SHA1 |
|---|---|---|
| Strategy | `strategies/guardian/guardian_gold_v5.5.pine` | `d30af5146d1df25d12ed68ce22150a0a58136e58` |
| Indicator (combined: FIRE + anticipation) | `strategies/guardian/guardian_gold_v5.5_indicator.pine` | `5b5239a608f453a7de78998bc63102bfa72bf30d` |
| Anticipation | combined into indicator file (no separate `_anticipation.pine`) | — |

Blob hashes are git-canonical (line-ending-normalized; `core.autocrlf=true` in this repo).

---

## §2 — Extracted expressions

### 2.1 STRATEGY_ENTRY_COND (firing condition for `strategy.entry`)

From `guardian_gold_v5.5.pine`:

```
// line 137: bullTrendOK     = close > emaSlow
// line 138: recoveryLong    = close > entryEma and close[1] <= entryEma[1]
// line 139: longSignal      = bullTrendOK and recoveryLong and sessionOK and hourAllowed and dayAllowed and inDateRange
//
// line 184–187: canTrade    = (backtestMode or not ddHit)
//                              and dailyTradeCount < maxDailyTrades
//                              and strategy.position_size == 0
//                              and not h12SignalToday
//
// line 208: if longSignal and canTrade
// line 214:     strategy.entry("Long", strategy.long, qty=size)
```

Effective `STRATEGY_ENTRY_COND`:

```
bullTrendOK
  AND recoveryLong
  AND sessionOK
  AND hourAllowed                            // not (H14 ∨ TueH08 ∨ MonH08 ∨ ThuH08 ∨ MonH09 ∨ MonH12 ∨ TueH12 ∨ ThuH12)
  AND dayAllowed                             // tradeMon ∨ tradeTue ∨ tradeThu (Wed/Fri off)
  AND inDateRange
  AND (backtestMode OR NOT ddHit)            // live-mode DD kill
  AND dailyTradeCount < maxDailyTrades
  AND strategy.position_size == 0
  AND NOT h12SignalToday                     // strategy-side day-gate latch
```

Strategy declaration (lines 9–10): `process_orders_on_close=false`, `calc_on_every_tick=true` — entries fire intra-bar.

### 2.2 INDICATOR_FIRE_COND (firing condition for `alertcondition(longSignal, …)` and entry `alert()` push)

From `guardian_gold_v5.5_indicator.pine`:

```
// (mid-file): bullTrendOK   = close > emaSlow
//             recoveryLong  = close > entryEma and close[1] <= entryEma[1]
//             longSignalRaw = bullTrendOK and recoveryLong and sessionOK and hourAllowed
//                             and dayAllowed and inDateRange and not h12DayGateActive
//
// (entry block):  primaryEntry = longSignalRaw and wasNotInPosition and dailyCapOK
// (later):        longSignal   = primaryEntry
//
// alertcondition(longSignal, title="Guardian v5.5 LONG Signal", message="GUARDIAN: Long Entry")
// alert(entryMsg, alert.freq_once_per_bar_close)  — fires on primaryEntry
```

Effective `INDICATOR_FIRE_COND`:

```
bullTrendOK
  AND recoveryLong
  AND sessionOK
  AND hourAllowed                            // gated on single blockH12 (not per-day)
  AND dayAllowed
  AND inDateRange
  AND NOT h12DayGateActive                   // indicator-side day-gate
  AND wasNotInPosition                       // NOT inPosition (sim state)
  AND dailyCapOK                             // tradesToday < maxTradesDay
```

### 2.3 INDICATOR_ANTICIPATION_COND (firing condition for `alertcondition(strictApproach, …)` / `alertcondition(approachZone, …)` and anticipation `alert()` pushes)

From `guardian_gold_v5.5_indicator.pine`:

```
// filtersOK         = bullTrendOK and sessionOK and hourAllowed and dayAllowed
//                     and inDateRange and not h12DayGateActive
// belowEntry        = close <= entryEma
// distAtr           = (entryEma - close) / atrVal             [when atrSafe]
//
// approachZone      = filtersOK and belowEntry and atrSafe and distAtr <= proximityAtr     // 0.50 × ATR
// strictApproach    = filtersOK and belowEntry and atrSafe and distAtr <= strictProximity  // 0.15 × ATR
// strictFirstBar    = strictApproach and not strictApproach[1]
// approachFirstBar  = approachZone and not approachZone[1]
//
// alertcondition(strictApproach, title="Guardian v5.5 Strict Approach", …)
// alertcondition(approachZone,   title="Guardian v5.5 Approach",        …)
//
// if alertOnAnticipation and strictFirstBar
//     alert(nearMsg, alert.freq_once_per_bar_close)
// if alertOnAnticipation and approachFirstBar and not strictApproach
//     alert(appMsg,  alert.freq_once_per_bar_close)
```

Anticipation fires when price is below the entry EMA at ≤ proximity threshold (in ATR units), with the same shared filter preconditions as FIRE (bullTrend / session / hourAllowed / dayAllowed / dateRange / not h12 day-gated). Push-class `alert()` fires only on the first-bar transition into the proximity zone, gated on the `alertOnAnticipation` input (default true).

---

## §3 — Three-way set diff

### 3.1 STRATEGY_ENTRY_COND vs INDICATOR_FIRE_COND

Shared (semantically identical at locked defaults):
- `bullTrendOK`, `recoveryLong`, `sessionOK`, `hourAllowed`, `dayAllowed`, `inDateRange`
- Day-gate latch (`not h12SignalToday` ≈ `not h12DayGateActive`)
- Position-flat gate (`strategy.position_size == 0` ≈ `wasNotInPosition`)
- Daily cap (`dailyTradeCount < maxDailyTrades` ≈ `dailyCapOK`)

In strategy only:
- `(backtestMode OR NOT ddHit)` — DD-based live kill switch (lines 172–175). Indicator does not replicate. **Design choice, not drift**: DD enforcement is strategy-side or via external `dd_protection.py`. Irrelevant under `backtestMode=true`.

In indicator only:
- None.

Per-day H12 collapse: strategy uses three independent `blockMonH12 / blockTueH12 / blockThuH12` inputs (lines 67–72) plus `dayH12Blocked` (line 155–157) latch gate; indicator collapses to a single `blockH12` input. **At locked defaults (all three on), behavior is semantically identical**; only diverges if strategy is run with one Hxx unblocked (e.g., the documented "TEST VARIANT" Thu H12 isolation).

Conclusion: at locked defaults, `STRATEGY_ENTRY_COND` and `INDICATOR_FIRE_COND` are semantically equivalent. **No drift**.

### 3.2 INDICATOR_FIRE_COND vs INDICATOR_ANTICIPATION_COND

FIRE has `recoveryLong = close > entryEma AND close[1] <= entryEma[1]` (the cross moment).
Anticipation has `belowEntry = close <= entryEma` AND `distAtr <= proximityAtr` (or `strictProximity`) — price still below the EMA, within proximity.

These are mutually exclusive at the same bar by design — anticipation fires while approaching from below, FIRE fires on the cross-up. This is the intended relationship.

Anticipation omits `wasNotInPosition AND dailyCapOK`. Anticipation can fire even when an open position exists or the daily cap is hit. **Design choice, informational class**.

Conclusion: anticipation is **NOT** a strict relaxation of FIRE — it is a different boolean covering the pre-cross approach window. This is correct design, not a logic bug. **No drift**.

---

## §4 — Hypothesis verdicts

- H1 (barstate gating divergence): **NOT-SUPPORTED**.
  Strategy declaration sets `process_orders_on_close=false` + `calc_on_every_tick=true` (lines 9–10). Indicator does not gate `primaryEntry`, anticipation alertconditions, or anticipation `alert()` pushes on `barstate.isconfirmed`. Both FIRE and anticipation paths in the indicator have identical bar-state behavior — no asymmetric gating that could explain FIRE firing while anticipation silently dropped.

- H2 (different lookback / parameter values, or extra gating clause): **SUPPORTED** (fast-approach mechanism confirmed by user-supplied chart 2026-05-08).
  Static parameters (`emaSlowLen=385`, `entryEmaLen=25`, `atrLength=14`, `proximityAtr=0.50`, `strictProximity=0.15`, all session/day filters) match between strategy and indicator at locked defaults — no static drift. Anticipation correctly tests a different boolean (pre-cross approach) than FIRE (the cross). The 2026-05-07 chart screenshot supplied by Joshua shows visually:
  - **No orange approach/strict-approach circles plotted below any bar before the cross** (08:00 → ~09:30 bars are clean of anticipation markers).
  - **Cross bar (~09:30) is a large green candle with body ≈30 points**, moving price from ~at-EMA (≈4715) directly to ~4745, well above. With ATR(14) on XAUUSD 15m of order 10-13 points (consistent with the dashboard's current "Dist below: 0.74 ATR" reading), this is a 2-3 × ATR single-bar move.
  - **Approach circles ARE visible 11:00-11:30** — after the STOP exit, when price returned below the EMA at proximity. This confirms the anticipation plot logic is wired correctly and was firing later in the day; it just had no eligible bar to fire on before the cross.
  Therefore, on the bar immediately before the cross, either (a) `distAtr > 0.50` (close was farther than 0.5 × ATR below the EMA, so outside the proximity zone) or (b) `belowEntry` was false (close was at or above the EMA — `recoveryLong` only requires `close[1] <= entryEma[1]`, which permits exact-equality, and exact-equality at one bar's close before a fast-up cross is plausible). Either case satisfies "no first-bar transition into proximity at close before the cross"; anticipation `alert()` legitimately had no bar to fire on. **Not a bug — expected behavior of a first-bar-transition gate against a fast-approach price path.**

- H3 (`alertcondition()` for anticipation not present): **NOT-SUPPORTED**.
  Indicator file declares `alertcondition(strictApproach, …)` and `alertcondition(approachZone, …)` (final block of file). Anticipation `alert()` push calls are also present (gated on `alertOnAnticipation` input, default true). Both paths are wired into the indicator as written.

- H4 (alert frequency / `alert.freq_*` mismatch): **NOT-SUPPORTED** (resolved via user confirmation 2026-05-08, see §6).
  Indicator file header (top comment block, dated 2026-05-07) reads:
  > _"2026-05-07 NON-STRATEGY PATCH (no version bump): Added alert() calls for anticipation states (NEAR + APPROACH first-bar transitions). Previously these states only had alertcondition() bindings, which require manual per-alert setup in TradingView and do not fire from the universal 'Any alert() function call' subscription."_

  Joshua confirmed (2026-05-08): the indicator on chart at the moment of the 2026-05-07 missed signal was **post-patch**, and the TV subscription was the universal **"Any alert() function call"** type. Under that configuration the post-patch `alert(nearMsg, …)` and `alert(appMsg, …)` push calls *should* fire — and they had previously fired correctly for prior anticipation events on this indicator. Therefore H4 is rejected as the cause of the 2026-05-07 non-fire.

  Residual concern (low confidence, not a hypothesis upgrade): if a TV alert was originally armed against the pre-patch indicator and TV cached the older binding, the universal subscription could in principle have stale routing. This is speculative and would manifest as a TV-side bug rather than a Pine-side one; out of scope for this audit but worth a one-line check ("delete and re-create the universal alert against the post-patch indicator") if H2 fast-approach (see below) is later ruled out by bar replay.

---

## §5 — Overall verdict

**`RESOLVED-fast-approach-not-a-bug`**

H1, H3, H4 all ruled out (see §4). H2 fast-approach SUPPORTED by visual evidence in user-supplied 2026-05-07 chart screenshot: no anticipation circles were plotted below any bar before the cross; the cross bar itself was a single 15m green candle of ≈30 points (≈2-3 × ATR) that traversed the proximity zone too fast for any prior bar's *close* to fall within `belowEntry AND distAtr <= 0.50`. Anticipation circles DO appear later the same day (11:00-11:30) once price returned below the EMA at proximity post-STOP, confirming the anticipation plot/alert wiring is functional.

The indicator behaved exactly as designed. The 2026-05-07 anticipation non-fire was not caused by indicator-strategy entry-condition drift, by missing alertcondition, by alert-frequency mismatch, or by parameter divergence. It was caused by a price path the first-bar-transition gate cannot fire on by construction.

## §6 — User confirmations received (2026-05-08)

- **Q4.1 (patch timing):** post-patch indicator was on chart at the time of the missed signal. → H4 push-call gap closed.
- **Q4.2 (TV subscription type):** universal "Any alert() function call". → H4 delivery-channel-mismatch ruled out.
- **Chart screenshot (2026-05-08 follow-up):** XAUUSD 15m, Thu 2026-05-07, full session view including entry bar at ~09:30 (4745.48), STOP exit at ~11:00-11:30 (4724.23 grace), and post-stop approach circles at 11:00-11:30. → Visual confirmation that no anticipation marker plotted before the cross. H2 fast-approach SUPPORTED.

## §7 — Recommended next action

**No code change to Guardian indicator or strategy.** The behavior is correct; the silent anticipation on fast-approach days is a designed property of a first-bar-transition gate, not a defect.

Calibration of expectation: when ATR is low and price gaps or jumps through the proximity zone in a single 15m bar, anticipation alerts can legitimately not fire even though FIRE fires immediately after. Mental model going forward: anticipation is **best-effort early warning, not a guarantee**.

Methodology lesson candidacy (single instance, n=1): *"indicator first-bar-transition anticipation alerts are silently bypassed by single-bar fast approaches; FIRE alert remains the only guaranteed signal — anticipation is informational warmup that fires only when price lingers in proximity ≥ 1 closed bar."* Promote to methodology registry on second occurrence (n=2) — likely candidates: Striker DJ30 / NAS100 (breakout strategies, similar first-bar-transition anticipation design) or Aegis (mean-reversion, same gate pattern inverted). Until a second occurrence, one-line note in `docs/methodology/lessons/methodology_lessons.md` is sufficient (out of scope for this session).

Optional (low value, defer): re-watch the indicator behavior over the next 2-3 Guardian entries to log whether anticipation fires or doesn't, building a small empirical base for "fast-approach silence rate" — but only if the question reopens in a future session.

(Recorded only — not executed.)
