# Lock Decision: <Strategy> <Version>

**Date locked:** YYYY-MM-DD
**Author:** Joshua

---

## Verification preamble (Rule 0)

Before any number below was written, the following production files were `view`'d and the relevant blocks pasted literally — no paraphrase, no memory recall.

### Strategy file

`strategies/<strategy_filename>.pine`, lines `<X–Y>`:

```pine
// PASTE LITERAL PINE BLOCK COVERING ALL LOCKED PARAMETERS HERE.
// e.g. risk_pct, SL/TP multipliers, session windows, blocks, EOM rule.
```

### Risk-control file (if change in scope)

`<dd_protection.py | accounts.json | other>`, lines `<X–Y>`:

```python
# PASTE LITERAL PRODUCTION BLOCK HERE.
```

### Calibration script identity assertions

The script that produced the performance numbers below begins with:

```python
from lib.mvd import assert_symbol, assert_broker, assert_version, assert_window

assert_version(strategy_version, "<X.Y>")
assert_symbol(df['symbol'].iloc[0], "<USDJPY_X | XAU_USD | US30USD | ...>")
assert_broker(broker, "<Pepperstone | Alchemy | OANDA>")
assert_window(first_ts, last_ts, expected_min_days=<N>, label="<panel>")
```

---

## Locked parameters

| Param | Value | Source line |
|-------|-------|-------------|
|       |       |             |

## Performance numbers (canonical panel)

| Metric | Value | Producing script |
|--------|-------|------------------|
| PF     |       |                  |
| RF     |       |                  |
| Trade count |  |                  |
| WR     |       |                  |
| Net $  |       |                  |
| Static DD |   |                  |

## MC results

- Bust prob: `X%`
- Pass prob: `Y%`
- p99 DD: `Z%`
- Producing script: `portfolio_mc.py`
- `assert_no_fallback` confirmed clean: ☐ Yes (paste line count from log)

## Allocation

- Risk per trade: `X%`
- Lots / contracts: `...`
- Daily DD cap: `X%`

## Re-MC trigger conditions

(Per standing rule: 6mo live OR version bump OR allocation outside safe band OR any `dd_protection` constant change.)

---

## MVD-attest

For each cited number above, the producing script's first ~5 lines include identity assertions verifying symbol, broker, version, and window. ☐ **Confirmed.**

If any number above is sourced from a script that does not have identity assertions in its first ~5 lines, either harden that script or remove the number from this brief before it is cited downstream.

## References

- ADR: `docs/adr/2026-04-24-mvd-discipline.md`
- Methodology: `docs/methodology/mvd.md`
- Prior lock (if applicable): `<link>`
- CHANGELOG entry: `<link>`
