# ADR: Guardian risk re-lock — 0.30% → 0.34%

**Date:** 2026-04-23
**Status:** Accepted
**Scope:** `firm_rules.py`, `dd_protection.py`, `portfolio_mc.py`, `CLAUDE.md`
**Supersedes:** (partially) 2026-04-17-portfolio-allocations — Guardian allocation only.
  Striker 1.00% / Aegis 1.50% unchanged.

## Context

Two things changed since the 2026-04-17 allocation lock:

1. **Data expansion.** Guardian/Striker/Aegis backtest CSVs were re-sourced from
   Pepperstone, giving a 2022-01-04 → 2026-04-20 panel (1,120 business days, 223
   Mon-anchored week-blocks). The prior Alchemy-sourced panel only reached back
   to Feb 2025 — roughly 14 months vs. 52 months of regime coverage. Re-running
   portfolio MC on the expanded panel at the original 0.30% / 1.00% / 1.50%
   allocation produces bust 0.52% / pass 92.47% / p99 DD 4.91%, a substantially
   wider margin under the 5% static DD cap than the 2026-04-17 MC (1.55%).

2. **Deliberate headroom test.** A Guardian-risk sweep from 0.35% to 0.50% was
   run against a v5.5 CSV (identical 201 trades, sized natively at 0.5% risk to
   honestly capture any size-dependent Pine behavior). The sweep gave:

   | Guardian | Bust  | p99 DD |
   | ---      | ---   | ---    |
   | 0.30%    | 0.52% | 4.91%  |
   | 0.34%    | 0.65% | 4.94%  |
   | 0.35%    | 0.84% | 5.00%  |
   | 0.40%    | 1.12% | 5.19%  |
   | 0.50%    | 1.93% | 5.55%  |

Two caps bite in the same neighborhood: the 1% bust target (crossed between
0.35% and 0.40%) and the 5% static DD cap (p99 DD reaches it at 0.35%).
0.34% sits just under both with preserved headroom.

## Decision

Re-lock Guardian at **0.34%** per-trade risk. Striker and Aegis unchanged.

| Strategy | Before | After | Change |
| ---      | ---    | ---   | ---    |
| Guardian | 0.30%  | 0.34% | +4 bp  |
| Striker  | 1.00%  | 1.00% | —      |
| Aegis    | 1.50%  | 1.50% | —      |

### Locked MC numbers (canonical reference)

Config: G 0.34% / S 1.00% / A 1.50%, DD 1.0% / 0.40× single-tier,
Pepperstone panel 2022-01-04 → 2026-04-20, 10,000 sims × 3 seeds.

- **Pass: 92.73%** (sigma 0.11%)
- **Bust: 0.65%** (0.00% daily + 0.65% static, sigma 0.08%)
- **Timeout: 6.62%**
- **Median days to pass: 32**
- **p50 DD: 1.63% / p95 DD: 3.99% / p99 DD: 4.94%**
- **Bust attribution:** Aegis 27.6% / Striker 39.3% / Guardian 33.2%

## Alternatives considered

- **0.30% (prior lock).** Bust 0.52%, p99 DD 4.91%. Safest but under-utilizes
  risk budget. On the expanded Pepperstone panel the 2026-04-17 numbers
  (1.55% / 93.00%) no longer apply — the real margin under the caps is wider
  than previously believed, which motivated reopening the lock.
- **0.35%.** Bust 0.84%, p99 DD exactly 5.00%. Zero headroom under the static
  DD cap. Rejected: any modest MC re-estimation error pushes 1-in-100 sims
  into bust.
- **0.40%.** Bust 1.12%, p99 DD 5.19%. Fails both the 1% bust target and the
  5% static DD cap. Rejected.
- **Proportional bump to 0.50%.** Bust 1.93%. Rejected — ~3× the bust target
  for marginal pass-rate gain (pass is flat at ~92.3–92.5% across the whole
  range; extra Guardian risk converts timeouts into busts, not passes).

## Consequences

Positive:
- Slightly higher expected P&L from Guardian at no cost to pass rate.
- Bust attribution rebalances toward a more even distribution across the
  three strategies (Guardian share 27% → 33%).
- MC is revalidated on 4yr+ of regime data rather than 14mo.

Negative / watched:
- p99 DD headroom under the 5% static cap shrinks from 9 bp (at 0.30%) to
  6 bp (at 0.34%). Still clear, but tighter.
- Conflict overlay was deactivated in a concurrent change on 2026-04-23
  (revert triggers met). Guardian now runs at the 0.34% locked base
  unqualified. See `docs/overlays/guardian_conflict_risk.md` for the
  deactivation record.

## Cross-references

- Notion source of truth: https://www.notion.so/346dc0b53c1181d1b8d5e12df4bd3810
- Related: ADR 2026-04-17-portfolio-allocations (original lock), ADR
  2026-04-17-dd-trigger-calibration, ADR 2026-04-17-equity-tier-deletion
- Code: `firm_rules.py`, `portfolio_mc.py` (ALLOCATIONS), `dd_protection.py` (BASE_RISK)
- Data: `data/tv_exports/{guardian,striker,aegis}.csv` (Pepperstone-sourced 2022→2026)
