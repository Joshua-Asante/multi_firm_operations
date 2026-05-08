# USOIL Phase 2 — Pepperstone visual validation (vol-gated verdict)

**Verdict:** SURVIVES (overlap 2/3, PASS per pre-registered criterion)

**Loop:** USOIL 15min behavioral characterization (2026-05-02), Notice/Identify phase
**Plan:** `~/.claude/plans/usoil-15min-behavioral-composed-tower.md` (Stage D)
**Phase 1 brief:** `2026-05-02_usoil_15min_characterization.md`
**Indicator:** `archive/analysis/usoil/indicators/usoil_phase2_validation.pine`

## 1. Pre-registered pass criterion (set BEFORE Pine authored)

Per plan §Stage D step 13:

> **vol-gated** → passes if top-3 ATR-percentile bins on Pepperstone overlap ≥2 of 3
> with top-3 OANDA bins, evaluated by 15min bin-of-day index.

OANDA reference (from Phase 1 result brief): `[47, 48, 49]` = NY 11:45 / 12:00 / 12:15.

## 2. Pepperstone observed top-3 (Joshua, TradingView)

| Rank | Bin | NY clock | Mean ATR(14) |
|---:|---:|---|---:|
| 1 | 47 | 11:45 | 0.3440 |
| 2 | 46 | 11:30 | 0.3433 |
| 3 | 48 | 12:00 | 0.3423 |

Source: `archive/analysis/usoil/indicators/usoil_phase2_validation.pine` loaded on Pepperstone USOIL 15min chart, broker-connected via TradingView.

(NB: the indicator's first-render rendered clocks as "12:45 / 12:30 / 12:00" due to a
Pine `int / int` returning float bug in `bin_to_clock`. The bin-index comparison —
which is the load-bearing logic — was unaffected because it operates on raw integer
indices, not the formatted clock string. Bug fixed in-place; PASS verdict stands.
See §5.)

## 3. Overlap calculation

| Pepperstone bin | In OANDA `[47, 48, 49]`? |
|---:|:---:|
| 47 | ✓ |
| 46 | ✗ |
| 48 | ✓ |

**Overlap: 2 of 3. Criterion ≥2/3 → PASS.**

## 4. Verdict and routing

The Phase 1 vol-gated verdict on USOIL M15 **survives** Pepperstone visual validation.
Both feeds independently identify the same intraday vol concentration window
(11:30–12:15 ET) — the rank ordering differs slightly (Pepperstone has 11:30 in #2,
OANDA has 12:15 in #3, both miss each other's third bin) but the contiguous
late-morning vol cluster is feed-invariant.

**Routing per `docs/methodology/observation_routing.md`:** Forward — USOIL vol-gated
characterization becomes the seed for an Inquire-phase Q. Specifically Q-USOIL-3
from the Phase 1 brief §7:

> Q-USOIL-3: Conditional on USOIL 15min volatility-gated structure (ACF|r|>0.10,
> intraday concentration), separate the vol-gate from the underlying directional
> edge. What direction (if any) does USOIL exhibit conditional on entering a top-3
> ATR-percentile bin?

This is a **separate** loop with its own pre-Q gate. It is NOT executed in this
characterization loop.

## 5. Bug audit (Pine `int / int` clock-display bug)

Surfaced when Joshua reported the table contents: bin 47 (which should map to
NY 11:45) was rendered as "12:45". Investigation:

- Pine v6 evaluates `/` on integer operands as **float** division, not integer.
  `47 / 4 = 11.75`, not `11`.
- `str.format("{0,number,00}", 11.75)` rounds to nearest integer with the `00`
  pattern, giving `"12"`.
- Bin 48 displayed correctly because `48 / 4 = 12.0` exactly.

**Fix applied:** `bin_to_clock` now uses `math.floor(b / 4)` to lock integer
division behaviour.

**Why this did NOT affect the verdict:** the overlap test in the indicator is
implemented as `array.get(oanda_top, kk) == b` — comparing raw integer bin
indices, not formatted clock strings. The `bin_to_clock` output is purely
display. The PASS computation was correct from the start.

**Audit-hook check:** does this bug fire any of the plan §Audit-hooks conditions?
- (1) Forbidden D-test: no.
- (2) Extreme T1 stat (load bug): no — Phase 1 stats are unaffected.
- (3) Verdict contradicts plot evidence: no.
- (4) Stage 0 fails: no.
- (5) Phase 2 contradicts Phase 1: **no** — the bug was display-only; the underlying
  bin-overlap test passed cleanly.
- (6) Wall-clock > 1 working day: no.
- (7) Second instrument places Pine in `indicators/<instrument>/`: not applicable
  (this is the first).

No audit file is written. The bug is logged here for the next characterization
loop's pattern library.

## 6. Cross-references

- Plan: `~/.claude/plans/usoil-15min-behavioral-composed-tower.md`
- Stage 0 reconciliation: `2026-05-02_usoil_feed_reconciliation.md` (PASS)
- Phase 1 result brief: `2026-05-02_usoil_15min_characterization.md` (verdict: vol-gated)
- Pine indicator: `archive/analysis/usoil/indicators/usoil_phase2_validation.pine`
- Phase 1 results JSON: `2026-05-02_usoil_phase1_results.json`
- Observation routing: `docs/methodology/observation_routing.md`
