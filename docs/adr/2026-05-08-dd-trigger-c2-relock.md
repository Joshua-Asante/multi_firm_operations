# ADR: dd_protection C2 relock — 1.0% / 0.40× → 1.5% / 0.40×

**Date:** 2026-05-08
**Status:** Accepted (with documented dissent)
**Scope:** `dd_protection.py`, `tests/test_mc_anchors.py`, `tests/test_mvd_selfchecks.py`, `CLAUDE.md`, `mc_explore.py`
**Supersedes:** 2026-04-17-dd-trigger-calibration — `DD_TRIGGER` only. `DD_SCALE = 0.40` unchanged.

## Context

Two converging events created the conditions for this re-lock:

1. **bust_attribution_flip resolution.** The 2026-04-26 portfolio_mc canonical-OANDA migration surfaced a mirror-symmetric Aegis ↔ Guardian attribution swap between the OANDA and Pepperstone panels (~+14pp Guardian / ~−14pp Aegis), confounded between two candidate drivers (broker-feed effect vs. version-relock effect). The brief at [docs/briefs/bust_attribution_flip.md](../briefs/bust_attribution_flip.md) was held Forward pending three gating preconditions including a same-date TradingView Pepperstone+OANDA re-export. On 2026-05-08 those preconditions cleared, and the same-date re-export resolved the flip as **broker-feed-confirmed**: OANDA mis-represents the Aegis-vs-Guardian attribution split relative to Pepperstone. Pepperstone is canonical for attribution; OANDA continues as the secondary pattern-spotting surface.

2. **Q-DDP-1 sweep verdict re-evaluation.** The Q-DDP-1 Pareto-relaxation sweep (2026-05-06, [docs/briefs/Q-DDP-1/recommendation.md](../briefs/Q-DDP-1/recommendation.md)) tested 5 candidate dd_protection configs against 5 acceptance criteria. C2 (1.5% / 0.40×) was the sole config to pass criteria 1–4 strictly on the full 4-strategy Pepperstone panel:
   - Pass 98.09% (vs C0 97.88%)
   - Bust 0.36% (under 0.50% ceiling, vs C0 0.22%)
   - p99 DD 4.73% (under 5.00% ceiling, vs C0 4.55%)
   - Drag savings 25% (vs C0 baseline)
   - **Median days-to-pass 22 (vs C0 23)**

   C2 **failed criterion 5 (regime-robustness gate)** decisively: bootstrap 5th-percentile pass-rate 90.82% (vs 97.5% floor), H1 (2022-01 → 2024-04) sub-panel pass-rate 86.78% (vs 97.5% floor); H2 (2024-05 → 2026-04) sub-panel passes at 99.67%. The 12.9pp half-panel pass-rate spread was decisive and the recommendation was AMBIGUOUS / default HOLD.

The combined re-evaluation: with broker-feed differential isolated and OANDA's role re-affirmed as pattern-spotting (not lock-decision substrate), the H1↔H2 partition asymmetry that drove the regime-robustness failure is partially confounded by the same broker-feed differential the same-date re-export was designed to control. The dissent on regime fragility is preserved — H1's 86.78% characterization is not erased — but the operational benefit of C2 (median days-to-pass 23 → 22, 25% drag savings, both lock criteria still cleared with margin) is concrete and broker-feed-validated.

## Decision

Re-lock dd_protection at **C2 (DD_TRIGGER = 0.015, DD_SCALE = 0.40)**. Override of the Q-DDP-1 HOLD recommendation, on the explicit grounds that:

1. **Risk controls clear.** Bust 0.36% < 1.00% lock criterion; p99 DD 4.73% < 5.00% lock criterion. Both gates pass with margin on the full 4-strategy Pepperstone panel.
2. **Median pass-time benefit.** 23 → 22 days. Operational, concrete, measured.
3. **Broker-feed resolution.** The bust_attribution_flip closure validates that broker-feed differential affects attribution; C2's H1↔H2 spread is partially read through the same lens. Not a complete invalidation of the regime-robustness signal — a partial reframe.
4. **OANDA pattern-spotting reliability preserved.** OANDA C2 anchor (96.23% / 0.69% / 4.91%) clears the same lock criteria on the secondary panel.

### Locked MC numbers (canonical reference)

Config: G 0.34% / DJ30 v4.5 1.00% / A v4.3 1.50% / NAS v1 0.40%, dd_protection C2 1.5% / 0.40× single-tier, Pepperstone panel 2022-01-04 → 2026-04-20, 10,000 sims × 3 seeds.

- **Pass: 98.09%** (sigma 0.04%)
- **Bust: 0.36%** (0.00% daily + 0.36% static, sigma 0.03%)
- **Timeout: 1.55%**
- **Median days to pass: 22**
- **p50 DD: 1.37% / p95 DD: 3.74% / p99 DD: 4.73%**
- **Bust attribution:** striker 44.4% / aegis 24.1% / guardian 21.3% / NAS 10.2%

OANDA C2 anchor (3-strategy, DJ30 still v4.4): 96.23% pass / 0.69% bust / p99 DD 4.91% / median 25 days. Both lock criteria clear with thinner margin than Pepperstone, consistent with OANDA's pattern-spotting role.

Pinned by `tests/test_mc_anchors.py` and `tests/test_mvd_selfchecks.py`.

## Alternatives considered

- **C0 = (1.0%, 0.40×) — prior lock.** Pass 97.88% / bust 0.22% / p99 DD 4.55% / median 23. Pareto-undominated under the full Q-DDP-1 criteria set (1–5). Forgoes the median-pass-time benefit and 25% drag savings. **Rejected** in favor of C2 once broker-feed-resolution shifted the load on criterion 5.
- **C1 = (1.0%, 0.50×).** Bust 0.54% — exceeds the 0.50% ceiling. **Rejected** on Q-DDP-1 criterion 2.
- **C3 = (1.5%, 0.50×).** Bust 0.74% — exceeds the 0.50% ceiling. **Rejected** on Q-DDP-1 criterion 2.
- **C4 = (2.0%, 0.50×).** Bust 1.03%, p99 DD 5.06% — fails both the bust ceiling AND the static DD ceiling. **Rejected** on Q-DDP-1 criteria 2 + 3.

The full sweep audit lives at [docs/briefs/Q-DDP-1/sweep_results.csv](../briefs/Q-DDP-1/sweep_results.csv); per-config rejection itemization at [docs/briefs/Q-DDP-1/recommendation.md](../briefs/Q-DDP-1/recommendation.md).

## Consequences

Positive:
- Median days-to-pass shortens from 23 to 22 on Pepperstone.
- Drag savings of 25% on the unprotected-PnL substrate (per Q-DDP-1 sweep).
- Bust attribution rebalances under the new trigger: striker 40.9% → 44.4%, guardian 25.8% → 21.3%, aegis 22.7% → 24.1%, NAS 10.6% → 10.2%. NAS remains the lowest contributor consistent with the diversification thesis.
- Both lock criteria (bust < 1%, p99 DD < 5%) continue to clear on Pepperstone and OANDA.

Negative / watched:
- **Regime-robustness dissent.** H1 sub-panel pass-rate of 86.78% under C2 remains a real characterization of the strategy under early-panel (2022-01 → 2024-04) market conditions. The 12.9pp half-panel spread is on record. If forward live-PnL or future panel updates show H1-like underperformance, **C2's regime-fragility risk has materialized** — the documented fallback is to revert to C0.
- **Reduced p99 DD headroom under the 5% static cap.** 4.55% → 4.73% (45 bp → 27 bp of headroom). Still clear, but tighter than C0.
- **Striker concentration in bust attribution.** DJ30 share grew 40.9% → 44.4%. Q-DJ30-3 closed exhausted on the SNAG-tail anchor (2025-02-07 / −5.94R) on 2026-05-06; under C2 the DJ30 path now carries marginally more bust budget. Forward live-PnL on DJ30 warrants the most attention.

### Forward revert trigger (load-bearing)

Per the OVERRIDE section in [docs/briefs/Q-DDP-1/recommendation.md](../briefs/Q-DDP-1/recommendation.md):

> If rolling 6-month MC pass-rate on the live-extended Pepperstone panel falls below 95% for two consecutive 6-month windows after this override, treat as evidence the regime-fragility risk has materialized and re-open the C0/C2 question with the new panel data.

**Operationalization (2026-05-08):** quarterly cadence; the rolling 6-month MC pass-rate check is implemented in `analysis/time_to_pass.py` (`--regime-check` mode) and reported during the next four quarter-end reviews (2026-08-08, 2026-11-08, 2027-02-08, 2027-05-08 minimum).

## Cross-references

- Notion FINAL decision page (single-tier dd_protection): https://www.notion.so/346dc0b53c11816085bbf2292be934cc
- Q-DDP-1 brief: [docs/briefs/Q-DDP-1/recommendation.md](../briefs/Q-DDP-1/recommendation.md) (OVERRIDE section + original AMBIGUOUS / default HOLD verdict preserved below)
- bust_attribution_flip closure: [docs/briefs/bust_attribution_flip.md](../briefs/bust_attribution_flip.md)
- Regime-robustness gate doc (worked example + override postscript): [docs/methodology/regime_robustness_gate.md](../methodology/regime_robustness_gate.md)
- Related ADRs:
  - 2026-04-17-dd-trigger-calibration (original C0 lock; superseded for `DD_TRIGGER` only)
  - 2026-04-17-equity-tier-deletion (single-tier basis)
  - 2026-04-23-guardian-risk-relock-0.34 (concurrent risk-control work)
  - 2026-04-24-mvd-discipline (constant-change MVD gate that fired correctly on this relock)
  - 2026-04-25-mvd-retrofit (MVD self-check at import; constants pinned at two layers)
- Code: `dd_protection.py` (`DD_TRIGGER = 0.015`, `DD_SCALE = 0.40`); `tests/test_mc_anchors.py` (Pepperstone 0.9809/0.0036/0.0473, OANDA 0.9623/0.0069/0.0491); `tests/test_mvd_selfchecks.py` (duplicated pin)
- MC harness: `portfolio_mc.py` (no source change; constants imported from `dd_protection`)
- Forward-trigger instrumentation: `analysis/time_to_pass.py` (`--regime-check` mode added 2026-05-08)

---

## Addendum — 2026-05-10

- `mc_explore.py` deleted in Q-MCFP-1 (PR #63, merge 54d22858 on main).
- C2 anchor 98.09 / 0.36 / 4.73 empirically reconfirmed post-precision-fix
  (Run A identical to baseline at abs=1e-4).
- Reference: [docs/briefs/Q-MCFP-1/closure.md](https://github.com/Joshua-Asante/multi_firm_operations/blob/main/docs/briefs/Q-MCFP-1/closure.md)
