# Guardian conflict risk overlay

**Status:** DEACTIVATED 2026-04-23 (historical record preserved below)
**Scope:** Guardian Gold strategy (XAUUSD 15min)
**Type:** Regime overlay — temporary risk adjustment, not a parameter change to the strategy itself

Guardian is currently running at its locked base risk (see `firm_rules.py` / `CLAUDE.md`).
No overlay active. This document is retained as the operational template for a
future overlay and as a record of the Iran-Israel / Hormuz regime episode.

## Final state (deactivation, 2026-04-23)

| Field | Value |
|---|---|
| Per-trade risk | Reverted to locked base (see `firm_rules.py`) |
| Strategy parameters | v5.1 locked, unchanged throughout |

## Historical state (while active, 2026-04-16 → 2026-04-23)

| Field | Baseline (at activation) | Under overlay |
|---|---|---|
| Per-trade risk | 0.55% (pre-v5.1 era) | 0.25% |
| Strategy parameters | pre-v5.1 → v5.1 locked 2026-04-17 (mid-overlay) | unchanged |

**Baseline timing note.** The overlay activated 2026-04-16 against the then-current 0.55% per-trade risk. The v5.1 lock the next day (2026-04-17) re-set the cold-start baseline to 0.30% (see `strategies/guardian/guardian_CHANGELOG.md` v5.1 entry); the overlay's reduced 0.25% level was held throughout. On 2026-04-23 the overlay deactivated and Guardian re-locked at 0.34% (see `docs/adr/2026-04-23-guardian-risk-relock-0.34.md`). The "0.55% baseline" in the table above is the pre-v5.1 figure as recorded at overlay activation, not the v5.1-era cold-start.

The overlay modifies the risk multiplier applied to Guardian position sizing. The Pine strategy itself is unchanged. All other strategy parameters (EMA, SL, TP, session, hour blocks, maxHold, grace stop) operate identically to the locked v5.1 specification.

## Trigger that activated the overlay

Iran-Israel conflict onset 2026-02-28. Strait of Hormuz closure 2026-03-02. GVZ (Gold volatility index) spiked above 25 and has remained elevated. Guardian drew down through its worst-ever losing streak Mar 2–30.

XAUUSD under conflict regime exhibits:
- Elevated realized vol that violates the ATR-based SL calibration's implicit assumptions
- Discontinuous gap risk on headline-driven moves
- Correlation breakdown between Guardian's trend signal and actual price action

The overlay cuts risk to 0.25% to reduce exposure while the regime is active. The strategy continues to run on its normal schedule.

## Revert conditions

Both conditions must hold, sustained for 5 sessions:

1. **GVZ closes below 25** (returning to non-crisis vol regime)
2. **Hormuz transit volume above 50% of pre-closure baseline** (physical flow normalization)

When both conditions are met and sustained, revert per-trade risk from 0.25% to 0.55%.

## Extension rule

If neither signal fires within 8–12 weeks of the overlay activation (2026-04-16), **extend the overlay; do not revert on calendar.** The overlay is tied to regime state, not to elapsed time. A calendar-based revert would reintroduce full risk into a regime where risk was reduced for measurable reasons — that's worse than leaving the overlay in place indefinitely.

## What this overlay does NOT do

- Does not change Guardian's Pine code
- Does not change Guardian's signal logic, session, or hour blocks
- Does not affect Striker or Aegis (they have separate regime exposures — Striker via equity-vol whipsaw from oil shock repricing, Aegis via BOJ/Fed divergence and yen safe-haven flows)
- Does not modify `dd_protection.py` thresholds

## Log of changes

| Date | Change |
|---|---|
| 2026-04-16 | Overlay activated. Risk reduced 0.55% → 0.25%. |
| 2026-04-23 | Overlay deactivated. Revert conditions met; Guardian returned to locked base risk. |

## Cross-references

- Notion: [Guardian conflict risk overlay — 2026-04-16](https://www.notion.so/344dc0b53c118152bf97eca9c931050b)
- Code: Guardian base parameters live in `strategies/guardian/guardian_gold_v5.5.txt` (overlay was applied to v5.1 at the time; successor v5.5 not modified by overlay). Overlay applied at risk-sizing layer only.
- Related: `docs/operational_rules.md` (hard rule: never override a valid signal based on macro volatility forecast)
