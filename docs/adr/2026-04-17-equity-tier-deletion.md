# ADR: Equity tier deletion from dd_protection

**Date:** 2026-04-17
**Status:** Accepted
**Scope:** `dd_protection.py`, portfolio risk architecture

## Context

Prior `dd_protection.py` implemented two-tier protection: a drawdown-from-peak trigger (DD tier) and an equity-level trigger (equity tier). Under the intended composition, both tiers fired independently and their scaling factors combined via `min(DD_SCALE, EQUITY_SCALE)` to produce the active risk multiplier.

Phase 1 audit surfaced the issue. Under `min()` semantics with the actual parameter values in use, the equity tier cannot fire without the DD tier having already fired first. The equity threshold (3.5% equity loss) is reached through drawdown from peak, which is exactly what the DD tier (1.5% DD) is already monitoring. The equity tier was behaviorally inert — mathematically dead code contributing nothing to the protection envelope.

This was verified by sweeping equity-tier parameters across plausible ranges and confirming zero behavioral difference in Monte Carlo outcomes.

## Decision

Delete the equity tier entirely. Single-tier protection: DD trigger 1.0% from peak with 0.40× risk scaling.

## Alternatives considered

- **3a. Keep both tiers, change combination from `min()` to `*=` (multiplicative).** Under multiplicative combination, the equity tier would provide behavioral contribution. MC at 2.0%/0.40× with multiplicative showed bust 1.66% vs 1.55% for the single-tier option. One extra line of semantic complexity for a worse result. Rejected.
- **3b. Delete equity, single-tier DD 1.0%/0.40×.** Chosen. Bust 1.55%, pass 93.00%, p99 DD ~4.9%.
- **Do nothing.** Keep dead code. Rejected — violates Delete step of The Algorithm, adds ongoing maintenance burden and reader confusion.

## Consequences

Positive:
- Reduces `dd_protection.py` complexity by removing an entire tier and its parameter surface.
- Improves MC bust rate from 8.72% (two-tier misconfiguration) to 1.55% (single-tier correctly specified).
- Eliminates a class of future bugs where someone might tune equity-tier parameters without realizing they have no effect.

Negative:
- Requires a follow-up ADR if future portfolio changes (fourth strategy, Aegis allocation above 1.5%, correlated tail additions) make a genuine equity-level floor useful. Revisit then, do not preemptively restore.

Risks:
- If backtest regime shifts produce fatter left tails than the 4yr window captured, single-tier may prove insufficient. Mitigated by MC bust attribution monitoring and the post-challenge retune proposal (DD 2.0%/0.50×) queued for after the challenge passes.

## Cross-references

- Notion: [dd_protection → single-tier (equity tier deleted, DD 1.0%/0.40×) — 2026-04-17 FINAL](https://www.notion.so/346dc0b53c11816085bbf2292be934cc)
- Notion: [dd_protection retune REVERSED — two-tier modeling correction — 2026-04-17](https://www.notion.so/346dc0b53c1181f39cd0f217aaefed37)
- Code: `dd_protection.py` (single-tier implementation post-commit `880f025`)
- Related: ADR 2026-04-17-dd-trigger-calibration
