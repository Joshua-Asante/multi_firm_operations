# Calibration Brief: <Strategy> <Version> on <Broker>

**Date:** YYYY-MM-DD
**Window:** YYYY-MM-DD → YYYY-MM-DD (`<N>` months)
**Author:** Joshua

---

## Verification preamble (Rule 0)

Identity verified before any number was computed. Calibration script begins with:

```python
from lib.mvd import assert_symbol, assert_broker, assert_version, assert_window

assert_version(strategy_version, "<X.Y>")
assert_symbol(df['symbol'].iloc[0], "<USDJPY_X | USDJPY | XAU_USD | US30USD>")
assert_broker(broker, "<Pepperstone | Alchemy | OANDA>")
assert_window(first_ts, last_ts, expected_min_days=<N>, label="<broker> <N>mo")
```

**Why this matters:** the Aegis $117K → ~$93K revision (audit instance #4) and the "4yr Alchemy panel" → 14mo revision (audit instance #8) both traced to identifier drift that an `assert_symbol` / `assert_window` would have caught at script-start.

---

## Trade-level results

| Metric | Value |
|--------|-------|
| Trade count |  |
| WR     |       |
| PF     |       |
| Net $  |       |
| Static DD |   |
| Peak DD |     |

## Signal-match analysis vs canonical feed

- Canonical reference: `<broker + window>`
- Match rate: `X%` (`Y / Z` trades by date+side)
- Divergent trades:
  - Date | side | canonical $ | this-feed $ | Δ$
  - ...

## Fill-divergence analysis (matched trades only)

- Net Δ on matched: `±$X`
- Decomposition: `(SL-flips: $A) + (entry slippage: $B) + (exit MFE-capture: $C) + (other: $D)`
- Dominant driver: ...

## Haircut

- This-feed / canonical ratio: `X%`
- Forward haircut: `(1 − X%) = Y%`
- Canonical → this-feed-eq: `$<canonical> × X% = $<eq>`
- DD amplification (this-feed / canonical): `Z×`

## Sweep (only if fill gap > 10%)

If gap ≤ 10%, no sweep — divergence priced into MC bootstrap.
If sweep ran, key variable + result table here.

---

## MVD-attest

For each cited number above, the producing script's first ~5 lines include identity assertions verifying symbol, broker, version, and window. ☐ **Confirmed.**

## References

- ADR: `docs/adr/2026-04-24-mvd-discipline.md`
- Methodology: `docs/methodology/mvd.md`
- Canonical feed reconciliation framework: `<link>`
- Prior calibration (if applicable): `<link>`
