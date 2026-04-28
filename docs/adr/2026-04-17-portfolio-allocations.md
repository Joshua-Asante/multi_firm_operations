# ADR: Portfolio allocations — G 0.30 / S 1.00 / A 1.50

**Date:** 2026-04-17
**Status:** Partially superseded by [2026-04-23-guardian-risk-relock-0.34.md](2026-04-23-guardian-risk-relock-0.34.md) (Guardian 0.30% → 0.34%). Striker 1.00% and Aegis 1.50% allocations remain in force from this ADR.
**Scope:** `firm_rules.py`, portfolio risk allocation

## Context

Prior portfolio allocations (G 0.30% / S 0.70% / A 0.75%) produced a 4yr net in the $200K+ range with acceptable MC pass rate, but risk budget was under-utilized. Striker and Aegis both had spare room under the FXIFY 5% daily DD cap that their per-strategy recovery factors justified filling.

Allocations needed to optimize net P&L across the 150-day challenge horizon subject to:
- FXIFY rules: 5% profit target, 5% daily loss, 5% static DD
- Portfolio-level bust rate constraint (target <5%)
- No strategy allocated above its own recovery-factor-implied ceiling

## Decision

Allocations finalized at Guardian 0.30% / Striker 1.00% / Aegis 1.50% per trade.

Allocation method: per-strategy recovery factor optimization. Each strategy's risk allocation is proportional to its recovery factor relative to the portfolio-level bust constraint.

## Alternatives considered

- **Prior allocations (0.30 / 0.70 / 0.75).** Validated but suboptimal. Under-uses risk budget on Striker and Aegis.
- **Equal-risk (0.75 / 0.75 / 0.75).** Rejected — ignores per-strategy recovery factor differences. Guardian's RF 22.04 vs Striker's 18.43 vs Aegis (highest μ/σ 1.63) argue for differential allocation, not flat.
- **Aggressive (G 0.50 / S 1.20 / A 2.00).** Rejected — MC bust rate exceeded 5% threshold. Aegis at 2.0% becomes the dominant bust driver past the tolerable range.

## Consequences

Positive:
- 4yr scaled net P&L lifts materially vs prior allocations.
- Recovery factor ordering (Guardian > Striker > Aegis when normalized) respected.
- Under single-tier DD 1.0%/0.40×, MC produces bust 1.55% / pass 93.00% / p99 DD ~4.9%.

Negative:
- Aegis at 1.50% is the dominant bust driver (~47% of bust attribution). This is an artifact of correct sizing toward highest-μ/σ strategy, not a miscalibration, but it means tail events in USDJPY mean-reversion drive portfolio outcomes more than either of the other two strategies.

Risks:
- BOJ April 28, 2026 meeting is a binary vol event that could shift USDJPY regime away from Aegis's edge window. If regime shift is confirmed post-meeting, allocation may need downward adjustment. Monitor, do not preemptively cut.
- ~~Guardian funded ramp (0.30 → 0.40 at $210K, 0.50 at $220K, 0.55 at $225K) changes the allocation profile as challenge clears. Each ramp step requires portfolio MC rerun before activation.~~ (Superseded same day, 2026-04-17, by the unified-allocation decision: challenge phase = funded phase, no re-sizing at pass. See `firm_rules.py` `RISK_TIERS` and `CLAUDE.md` Multiplier System.)

## Cross-references

- Notion: [dd_protection retune to 1.5%/0.40× — 2026-04-17](https://www.notion.so/346dc0b53c118124811bee0d77c1b1e1) (captures allocation rationale)
- Code: `firm_rules.py`
- Related: ADR 2026-04-17-dd-trigger-calibration, ADR 2026-04-17-equity-tier-deletion
