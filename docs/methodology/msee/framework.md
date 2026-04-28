# MSEE — Market Storage-Effect Ecology framework

**Established:** 2026-04-27
**Status:** Active research track. Operational/measurement layer only.
**Source:** [Market Ecology, the Storage Effect, and Evolutionary Dynamics.md](../../../Market%20Ecology%2C%20the%20Storage%20Effect%2C%20and%20Evolutionary%20Dynamics.md)

## What MSEE is

A hybrid biological framework for the locked G/S/A portfolio: Farmer's
market-ecology substrate + Chesson's storage-effect coexistence theory +
Lo's AMH evolutionary engine extended with bet-hedging. The framework
maps near-zero cross-strategy correlations, zero all-three-down days, and
the debate-to-election countercyclicality onto a three-dimensional
niche-partitioned coexistence (instrument × signal-mechanism × regime-
response axes), and predicts when that coexistence breaks down.

The source report produces 10 falsifiable predictions (P1–P10) and 10
directly testable hypotheses (H1–H10). Each H becomes a numbered
question on the Open Questions list — see [open_questions.md](open_questions.md).
Part VII early-warning signals become the watch-list (`watch_list.md`,
Phase 8).

## Where MSEE sits

MSEE lives **entirely in the operational/measurement layer**. Per the
Key Principle (CLAUDE.md), the portfolio and strategies are LOCKED — this
framework never touches strategy parameters. Concretely:

- No edits to Pine strategy files (Guardian v5.5, Striker v4.4, Aegis v4.3).
- No edits to `dd_protection.py` (DD trigger 1%, scale 0.40, locked 2026-04-17).
- No edits to allocations in `firm_rules.py` (G 0.34% / S 1.00% / A 1.50%).
- No edits to `portfolio_mc.py` — the lock-decision MC is read-only here.

For hypotheses that need MC perturbation or daily-curve retention (H1
community matrix, H9 capacity), a parallel `mc_explore.py` is introduced
(Phase 6) that mirrors `portfolio_mc`'s block-bootstrap with explicit
`EXPLORATORY` banner. Outputs carry `canonical_status = "EXPLORATORY"`.

## Governance posture

Every MSEE finding routes through the existing three-bucket gate
(Closed / Action / Forward) per [observation_routing.md](../observation_routing.md).
By construction:

- Most findings route **Closed** (the framework moves no policy by itself).
- Findings that would suggest a code change must additionally clear
  Rule 0, the overlay-discipline live-PnL-gap rule, or a documented
  re-MC trigger before reaching **Action**.
- Open hypotheses are **Forward** questions, ordered cheapest-falsification
  first per `open_questions.md`. Each must pass the **D-S-A pre-Q gate**
  before Inquiry begins.

OANDA-proxy discipline applies: per [AMENDMENT_oanda_rescope.md](../identify_corpus/2026-04-26/AMENDMENT_oanda_rescope.md),
findings produced on the OANDA panel cannot authorize Action. Pepperstone
re-fit gates Action on any MSEE result. Pepperstone bar-corpus acquisition
is itself a separate Forward question and is **out of scope** for this
research track.

## What MSEE claims (testable)

Three core claims, each with a defined falsifier:

1. **Niche-partitioned coexistence.** G/S/A occupy different niches along
   instrument, signal-mechanism, and regime-response axes; their daily-R
   covariance matrix has near-zero off-diagonals in normal regimes.
   *Falsifier:* H6 fails on condition (1) — no significant strategy ×
   regime-cluster interaction.

2. **Storage-effect buffering.** Strategy-specific responses + drawdown
   caps + capital persistence (Cohen 1966 / Slatkin 1974 geometric-mean
   fitness) produce a portfolio whose compound geometric growth exceeds
   the average of individual geometric growths.
   *Falsifier:* H3 returns ≤ 0 (no diversification uplift).

3. **Punctuated, not gradual, alpha decay.** Strategy edge declines via
   discrete regime breaks (Eldredge & Gould 1972) and frequency-dependent
   crowding (hyperbolic α(t)=K/(1+λt), Lee 2025), not via smooth Sharpe
   drift.
   *Falsifier:* H4 prefers exponential or linear over hyperbolic
   decisively *and* H5 finds continuous drift instead of discrete breaks.

If all three claims survive their tests, MSEE is the operational lens.
If any one fails, the framework's specific mechanism for that claim is
rejected — the lens is not used to defend the failed mechanism.

## What MSEE does NOT claim

- Markets are organisms (the report is explicit on this — it is a
  generator of testable predictions, not a metaphysical position).
- Strategies "evolve" without a designer (selection here is Lamarckian /
  artificial; the user is the selecting environment).
- Backtested track records are evolutionary fitness (4yr live data is
  closer to fitness than backtest, but not identical).
- Central-bank intervention is Darwinian (it is not — regulatory shocks
  are exogenous and the framework needs separate priors for them).

## Cross-references

- Source report: `Market Ecology, the Storage Effect, and Evolutionary Dynamics.md`
- Operational gate: `docs/methodology/observation_routing.md`
- Risk normalization: `docs/methodology/1r_estimation.md`
- MVD discipline: `docs/methodology/mvd.md`, `lib/mvd.py`
- Lock decisions: CLAUDE.md "Strategy Reference (LOCKED)" + linked Notion
- D-S-A pre-Q gate: anthropic-skills:inqhiori-algorithm
- Open questions: [open_questions.md](open_questions.md)
- Watch-list: `watch_list.md` (Phase 8)
- Foundation primitive: [`analysis/msee/daily_strategy_returns.py`](../../../analysis/msee/daily_strategy_returns.py)
