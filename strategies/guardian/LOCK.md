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

## Reference backtest

- Pepperstone canonical: `data/tv_exports/pepperstone/Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-05_33781.csv`
  (post-reconcile panel; 8 phantom v5.5 signals removed; see
  `data/reconciles/2026-05-05_guardian_n_reconcile.md`)
- Trade count: **201** _(extracted from CSV: max Trade # = 201)_
- Net P&L:     **$577,936.90** _(extracted from CSV: final Cumulative P&L USD; +288.97% on $200K)_
- PF:          `<verify against backtest CSV>`
- WR:          `<verify against backtest CSV>`
- Max DD:      `<verify against backtest CSV>`
- 1R:          `<verify against backtest CSV>` _(1R methodology: docs/methodology/1r_estimation.md — equity-compounding normalization for Guardian-style equity-sized strategies)_

The four placeholder metrics require either a full CSV reduction (PF / WR / Max
DD over the cumulative-P&L curve) or applying the 1R-estimation methodology.
Filling them is variable cost deferred to a follow-up session — not a memory
copy. Do not source from CLAUDE.md, prior briefs, or chat memory.

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
