# ADR: DD trigger calibration — 1.0% / 0.40×

**Date:** 2026-04-17
**Status:** Accepted
**Scope:** `dd_protection.py`, drawdown protection behavior

## Context

With the equity tier deleted (ADR 2026-04-17-equity-tier-deletion), the DD trigger is the sole protection mechanism. Two parameters to calibrate:

- **Trigger threshold:** drawdown from peak at which protection activates
- **Scale factor:** risk multiplier applied when active

Calibration objective: minimize portfolio bust rate across 150-day challenge horizon while preserving enough profit capture to clear the 5% FXIFY target at acceptable pass rate.

## Decision

DD trigger: 1.0% drawdown from peak.
Scale factor: 0.40× (i.e., active risk multiplied by 0.40 when triggered).

Under this configuration and the finalized allocations (G 0.30 / S 1.00 / A 1.50):
- Bust rate: 1.55%
- Pass rate: 93.00%
- p99 drawdown: ~4.9%
- Bust attribution: Aegis ~47% / Striker ~40% / Guardian ~12%

## Alternatives considered

MC sweep across trigger × scale grid. Key points tested:

- **1.5% / 0.40× (initial retune).** Bust rate higher than 1.0%/0.40× because the trigger fired too late to meaningfully protect the 5% static DD bound. Rejected.
- **2.0% / 0.40× with multiplicative two-tier (3a).** Bust 1.66% — worse than single-tier 1.0%/0.40× despite additional complexity. Rejected in favor of single-tier deletion.
- **2.0% / 0.50× (post-challenge retune proposal).** Bust rate acceptable but only under relaxed challenge constraints (no 5% static DD cap). Proposal is queued for post-challenge, NOT active. See Notion: "dd_protection recalibration to 2.0%/0.50× — post-challenge — 2026-04-17".
- **0.50× scale (looser protection).** Preserves more upside but crosses the 5% challenge threshold with higher probability. Rejected for the challenge phase.
- **0.30× scale (tighter protection).** Reduces bust rate marginally but compresses profit distribution enough to drop pass rate below 90%. Rejected.

## Consequences

Positive:
- 1.0% trigger is early enough to engage before the 5% static DD bound is threatened even under correlated-loss scenarios across all three strategies.
- 0.40× scale is aggressive enough to materially change risk behavior when active while leaving room for recovery.
- Single parameter pair, trivially auditable, no hidden interactions with an equity tier.

Negative:
- Early 1.0% trigger means the protection fires relatively often in backtest. Each activation is a drag on recovery if markets immediately reverse.
- 0.40× is lighter than typical two-tier configurations; under a regime with sustained correlated drawdowns across strategies, protection may prove insufficient.

Risks:
- Post-challenge, the constraint envelope changes (no 5% static DD cap on funded account). Retune to 2.0%/0.50× is queued precisely because the current calibration is challenge-optimized, not live-optimized.
- If live execution slippage materially exceeds backtest assumptions, effective DD on the account may drift from modeled DD, and the 1.0% trigger may not engage at the intended moment.

## Cross-references

- Notion: [dd_protection → single-tier (equity tier deleted, DD 1.0%/0.40×) — 2026-04-17 FINAL](https://www.notion.so/346dc0b53c11816085bbf2292be934cc)
- Notion: [dd_protection recalibration to 2.0%/0.50× — post-challenge — 2026-04-17](https://www.notion.so/345dc0b53c1181909fa8db077925124f) (queued, NOT active)
- Code: `dd_protection.py` (`DD_TRIGGER=0.010`, `DD_SCALE=0.40`)
- Related: ADR 2026-04-17-equity-tier-deletion, ADR 2026-04-17-portfolio-allocations
