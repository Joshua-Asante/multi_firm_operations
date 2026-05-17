# Guardian Gold v5.5 — LOCK

**Strategy version:** v5.5
**Lock date:** 2026-04-23
**Instrument:** XAUUSD 15m
**Risk per trade:** 0.34% (cold-start base, post-2026-04-23 relock)
**Phase parity:** challenge = funded (unified 2026-04-17)

## Source blob hashes (git-canonical, line-ending-normalized)

These are git's `hash-object` blob SHA1s — the authoritative content hashes
for files tracked under `core.autocrlf=true`. Raw `sha1sum` will diverge by
EOL bytes; trust the values below.

- Strategy:     `d30af5146d1df25d12ed68ce22150a0a58136e58` — strategies/guardian/guardian_gold_v5.5.pine
- Indicator:    `5b5239a608f453a7de78998bc63102bfa72bf30d` — strategies/guardian/guardian_gold_v5.5_indicator.pine
                  (combined: emits both FIRE-class `longSignal` and anticipation-class
                   `strictApproach`/`approachZone` alertconditions plus matching
                   `alert()` push calls — see indicator file's 2026-05-07 patch header)
- Anticipation: combined into indicator file (see indicator blob above)

## Reference backtest (canonical 2026-05-17 — BT-OFF + static-equity)

- Pepperstone canonical: `data/tv_exports/pepperstone/Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-17_90bb1.csv`
  (TradingView export with Backtest mode OFF; SHA256 `10f00ef62dcd0c4589103a8b50de7a77847f2581c43c652b8d5e99a6b5495cff` pinned
  in `data/tv_exports/pepperstone/SHA256SUMS`; methodology change documented in
  `data/reconciles/2026-05-17_guardian_bt_off_static_canonical.md`)

**Static-equity recomputation** (per-trade Net P&L USD × (INITIAL /
equity_at_entry), no compounding — the FXIFY-correct measurement for live
execution at fixed initial capital; Pine sizing line `calcSize(stopDist) =>
risk = strategy.equity * (riskPerTrade / 100)` compounds in the TV export,
requiring this recomputation to surface the live-FXIFY-equivalent profile):

- Trade count:        **207** _(max Trade # in CSV)_
- Net P&L (static):   **$245,424** _(+122.71% on $200K static)_
- Net P&L (TV compounded): $452,478.70 _(retained for cross-reference; not the lock anchor)_
- PF (static):        **3.26**
- WR:                 **22.71%** _(47/207; count-based, identical under both conventions)_
- Max DD % (static):  **6.92%**
- Max DD $ (static):  **$16,013**
- RF (static):        **15.33**
- 1R (median loss):   **$689** _(1R methodology: docs/methodology/1r_estimation.md)_

### Prior anchor — ARCHIVED 2026-05-17 (BT-ON compounded, superseded)

Retained for historical reference; **not the lock-of-record**. Replaced under
the BT-OFF + static-equity canonical methodology change (see reconcile note
above).

- Pepperstone (BT-ON compounded): `data/tv_exports/pepperstone/Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-05_33781.csv`
- Trade count: 201 · Net P&L: $577,936.90 (+288.97% on $200K, compounded) ·
  Max DD: 4.56%

## Lock decision Notion anchor

`<await user supply>`

Source-of-truth Notion page (root): https://www.notion.so/346dc0b53c1181d1b8d5e12df4bd3810

## Locked config (transcribed from strategy file header, not memory)

```
EMA 385/25 | SL 1.55×ATR | TP 29×ATR | grace 1b/2.0×ATR
maxHold 850 | max 2/day | risk 0.34%
Mon/Tue/Thu | 0800–1600 UTC (NY Extended)
Blocks: Tue H08, Mon H08, Mon H09, H12 entry + H12 day-gate
```

## Notes

- Guardian re-locked from 0.30% → 0.34% on 2026-04-23 after Pepperstone-sourced
  panel showed available headroom (per CLAUDE.md).
- v5.5 vs v5.4 filter changes: blockMonH08 ON (new), blockThuH08 OFF (new
  input), blockMonH09 ON (re-enabled). All other parameters unchanged.
- Indicator file header documents a 2026-05-07 NON-STRATEGY PATCH that added
  `alert()` push calls for anticipation states; strategy logic untouched.
  See `docs/audits/2026-05-08-guardian-v55-indicator-strategy-diff.md` for
  the indicator-vs-strategy entry-condition audit.
