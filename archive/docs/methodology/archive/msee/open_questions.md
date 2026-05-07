# MSEE — Open Questions (Forward bucket)

**Established:** 2026-04-27
**Source:** *Market Ecology, the Storage Effect, and Evolutionary Dynamics*, Parts IV (P1–P10) and VIII (H1–H10) — external reference, removed from repo 2026-04-28.
**Routing rule:** [observation_routing.md](../observation_routing.md) — three-bucket gate; cheapest-falsification first.
**Gate audit:** Each H must pass the **D-S-A pre-Q gate** before Inquiry begins. Audit recorded inline.

## Scope and constraints

- **Corpus:** OANDA-proxy panels (TV exports + 15m bars). Per [AMENDMENT_oanda_rescope.md](../identify_corpus/2026-04-26/AMENDMENT_oanda_rescope.md) supersession (2026-04-28), MSEE findings **can** route to Action proposals; Joshua validates in TradingView against Pepperstone bars before any code/lock change. Source feed always tagged on the artefact.
- **Foundation:** [`analysis/msee/daily_strategy_returns.py`](../../../analysis/msee/daily_strategy_returns.py) (Phase 0 — built 2026-04-27, q14 reconcile worst |dR| = 3.55e-15). Every H below joins on this file unless noted.
- **Locks:** No edits to Pine, `dd_protection.py`, `firm_rules.py` allocations, or `portfolio_mc.py`. H1 / H9 use `mc_explore.py` (Phase 6, EXPLORATORY).

## Status legend

`OPEN` (gate audited, awaiting Inquiry) · `INQUIRY` (script being run) · `CLOSED-{POSITIVE,NEGATIVE,NEUTRAL}` (result archived; no Action) · `ACTION-ROUTED` (cleared four-rules gate; opened separate Action work-item) · `BLOCKED` (gate failure; reason recorded).

## Phase 0 — Foundation (2026-04-27)

| Item | Status | Outcome |
|------|--------|---------|
| Per-strategy daily R/USD/n_trades primitive | CLOSED-POSITIVE | 420 trade-dates over 2022-01-04→2026-04-20; q14 regression invariant within 1e-6 (worst 3.55e-15). Commit pending. |
| `framework.md` operational synthesis | CLOSED-POSITIVE | Posted. |
| This file | CLOSED-POSITIVE | Posted. |

## Phase 1 — Cheapest falsifications (pure computation on existing trades)

### Q-MSEE-3 — Geometric mean uplift (H3, P7) — `OPEN`
**Question:** Does `G_portfolio − ⅓·(G_G + G_S + G_A)` (compounded geometric means of daily R-multiples translated to dollar returns) produce the predicted positive uplift, and does it match `½·(Σwᵢ²σᵢ² − Var[Σwᵢrᵢ])`?
**Falsifier:** Uplift ≤ 0 → bet-hedging mechanism rejected for this portfolio.
**D-S-A audit:**
- D: Restricted to trade-dates in the foundational primitive. Did NOT delete any cohort by P&L sign.
- S: Daily-R aggregation already at right grain; no further compression.
- A: One pandas computation, O(seconds). Bounded.
**Script:** `analysis/msee/h3_geometric_uplift.py` (Phase 1).
**Routing on result:** Closed-POSITIVE if uplift > 0; Closed-NEGATIVE rejects MSEE claim 2.

### Q-MSEE-10 — Senescence decomposition (H10) — `OPEN`
**Question:** Per strategy, do rolling R-multiples-of-winners and rolling win-rate trend over 2022→2026? Mode classification: prey-shrink (R declines, WR steady) vs density-rise (WR declines, R steady) vs both vs neither.
**Falsifier:** No interpretable trend in either component (consistent with stationary edge so far — strengthens framework's "lifecycle 3–7yr" claim by null result; not a true falsifier).
**D-S-A audit:**
- D: Per-trade frame from foundation primitive (entries closed in panel only).
- S: Rolling 6-month windows on trade index (not calendar) to keep cohort size stable.
- A: Three rolling computations, O(seconds).
**Script:** `analysis/msee/h10_senescence.py` (Phase 1).

### Q-MSEE-4 — Alpha-decay form (H4, P4) — `OPEN`
**Question:** Does rolling 6-month profit factor per strategy fit hyperbolic α(t)=K/(1+λt), exponential α(t)=K·exp(−λt), or linear better (by AIC)? Hyperbolic indicates frequency-dependent crowding (Lee 2025); exponential indicates non-adaptive drift.
**Falsifier (for MSEE claim 3):** All three strategies prefer exponential or linear decisively over hyperbolic.
**D-S-A audit:**
- D: Restricted to rolling windows with ≥ 30 trades (avoids early-cohort noise).
- S: 6-month rolling PF on trade-indexed window; one fit per strategy per model.
- A: scipy.optimize.curve_fit, O(seconds).
**Script:** `analysis/msee/h4_alpha_decay_fit.py` (Phase 1).

## Phase 2 — Conditional correlations (P2, H6 partial)

### Q-MSEE-6c — Stress-conditional correlations (P2) — `OPEN`
**Question:** On the worst 5% of market days (top |index move| or broker-spread proxy), do pairwise (G,S), (G,A), (S,A) correlations of daily R rise above their baseline near-zero? Khandani-Lo unwind signature would push them positive.
**Falsifier:** Stress correlations remain near zero (storage effect holds under stress).
**Auto-Action trigger:** If any pair > 0.3 in stress, an automatic Forward question on Khandani-Lo crowded-unwind risk opens. Action proposals from this trigger route through TradingView/Pepperstone validation (post-2026-04-28 policy) and the four-rules gate; auto-Action remains forbidden.
**D-S-A audit:**
- D: Restricted to 420 trade-dates joined to bar-derived stress flags.
- S: Single-day stress proxy from XAU/US30/USDJPY |daily ret|; alternatives logged.
- A: Bootstrap CIs on Pearson; O(seconds).
**Script:** `analysis/msee/h6c_conditional_correlations.py` (Phase 2).

## Phase 3 — Punctuated equilibrium (H5, P5)

### Q-MSEE-5 — Changepoint analysis (H5) — `OPEN`
**Question:** Does PELT (or BOCPD) on rolling 30-day Sharpe of each strategy find < 5 discrete breaks per 4yr (punctuated signature) rather than continuous drift?
**Falsifier:** > 10 breaks (continuous-drift signature) or 0 breaks (frozen-edge signature).
**Cross-check:** Predicted breaks should align with known events (2022 inflation regime, 2024 election, Mar-2020 COVID — pre-panel, but 2022+ events covered).
**D-S-A audit:**
- D: Rolling Sharpe restricted to days with ≥ 1 trade in the strategy.
- S: 30-day calendar window; alternatives (60d, trade-indexed) noted as follow-up.
- A: `ruptures` library, O(seconds).
**Script:** `analysis/msee/h5_changepoint.py` (Phase 3). Dep: `pip install ruptures`.

## Phase 4 — Regime classification + storage-condition synthesis (H2, H6, P3)

### Q-MSEE-2 — Regime cluster decomposition (H2, P3) — `OPEN` (gated on Phase 1+2 closing)
**Question:** k-means (k=4 default) on daily features from 15m bars (XAU/US30/USDJPY daily ret, realized vol, range %, bar-count); does each strategy's PF differ significantly across clusters, with non-overlapping "best-day" cluster?
**Falsifier:** Clusters do not separate strategy PFs; rank-ordering of strategies across clusters is unstable.
**D-S-A audit:**
- D: Bar-feature universe restricted to dates in the foundation primitive.
- S: k=4 anchored to "trend / chop / event / quiet" prior; sensitivity to k logged.
- A: sklearn k-means, O(seconds); reproducible seed.
**Script:** `analysis/msee/h2_regime_clusters.py` (Phase 4).

### Q-MSEE-6 — Storage-effect three-condition formal test (H6) — `OPEN` (depends on Q-MSEE-2)
**Question:** Does the portfolio satisfy Chesson's three conditions formally?
1. Species-specific environmental response (significance test on H2 cluster × strategy interaction).
2. Environment-competition covariance (capacity-erosion proxy via slippage trend in good regimes; uses `analysis/notice_phase/o7_slippage_realism.py` scaffold).
3. Buffered growth (max DD vs ruin threshold per [dd_protection.py](../../../dd_protection.py)).
**Falsifier:** Any one of the three conditions returns False.
**D-S-A audit:** Inherits Q-MSEE-2's gate. Condition (3) is a one-line read against locked DD_TRIGGER. Condition (2) introduces a slippage-trend regression bounded by panel size.
**Script:** `analysis/msee/h6_storage_conditions.py` (Phase 4).

## Phase 5 — Out-of-sample regime forecast (H7)

### Q-MSEE-7 — Lagged-feature regime forecast (H7) — `OPEN` (depends on Q-MSEE-2)
**Question:** Using week t-1 features, can we predict week t cluster better than chance? And does the predicted cluster's predicted-best strategy outperform the others OOS?
**Falsifier:** OOS hit-rate is at or below chance (binomial CI).
**D-S-A audit:**
- D: Rolling-origin OOS split (no peeking).
- S: Lag-1 only initially; longer lags are follow-up.
- A: Logistic regression / gradient boosting baselines, O(seconds-minutes).
**Script:** `analysis/msee/h7_regime_forecast.py` (Phase 5).

## Phase 6 — Community matrix + capacity (H1, H9, P1)

### Q-MSEE-1 — Community matrix Aᵢⱼ (H1, P1) — `OPEN` (depends on `mc_explore.py`)
**Question:** Perturbing capital allocations ±10% per strategy, what is the empirical 3×3 matrix Aᵢⱼ = ∂rᵢ/∂wⱼ? Predicted: off-diagonals near zero (with possibly small negative S–A entry), diagonals strongly negative.
**Falsifier:** Off-diagonals are large positive (mutualism) or large negative (predation); diagonals near zero (no own-density effect).
**Constraint:** Uses `mc_explore.py` only. Lock-decision `portfolio_mc.py` baseline must produce identical numbers before/after this work (audited at end of Phase 6).
**D-S-A audit:**
- D: Perturbation grid restricted to ±10% (single-step linearization sufficient for sign of Aᵢⱼ).
- S: Three perturbation runs per strategy (baseline + ±10%); 9 runs total.
- A: Reuses `portfolio_mc` block-bootstrap; minutes.
**Script:** `analysis/msee/h1_community_matrix.py` (Phase 6).

### Q-MSEE-9 — Capacity per strategy (H9) — `OPEN` (depends on `mc_explore.py` + slippage scaffold)
**Question:** Progressively scale lot sizes (with slippage model from [o7_slippage_realism.py](../../../analysis/notice_phase/o7_slippage_realism.py)) until slippage-adjusted PF falls 20%; report carrying-capacity K per strategy.
**Falsifier (for prediction):** K ordering is not Aegis > Guardian > Striker.
**D-S-A audit:**
- D: Slippage model restricted to currently-locked instruments; doesn't extrapolate.
- S: Lot-scaling grid (1×, 2×, 5×, 10×, 20× baseline) — coarse first pass; refine if K is in interior.
- A: Bounded by grid size × MC sims.
**Script:** `analysis/msee/h9_capacity.py` (Phase 6).

## Phase 7 — Invasion fitness (H8, P9)

### Q-MSEE-8 — Invasion-fitness battery (H8, P9) — `OPEN` (depends on Phases 2 + 4)
**Question:** For new-strategy candidates: (a) standalone Sharpe, (b) normal-regime correlation matrix to G/S/A, (c) stress-regime correlation matrix. Reject candidates with stress-corr > 0.3 even if normal-regime corr is near zero.
**First test case:** AUDNZD candidate from `scripts/audnzd_phase3_*.py` (already REJECTED on prior screen — re-test under MSEE battery and confirm).
**D-S-A audit:**
- D: Restricted to candidates that already passed Phase 0 verification in the AUDNZD discovery pipeline.
- S: Three correlation matrices (standalone, normal, stress).
- A: Direct computation, O(seconds).
**Script:** `analysis/msee/h8_invasion_fitness.py` (Phase 7).

## Phase 8 — Watch-list operationalization

Part VII early-warning indicators from the source report become a weekly
ops monitor — see `watch_list.md` (Phase 8). Thresholds calibrated from
data accumulated through Phases 1–6.

## Routing summary

| Result class | Routes to | Action gate |
|--------------|-----------|-------------|
| Hypothesis confirmed (positive) | CLOSED-POSITIVE | None — strengthens framework, no policy change. |
| Hypothesis falsified (negative) | CLOSED-NEGATIVE | None — rejects mechanism, framework restated. |
| Stress correlation > 0.3 | CLOSED + auto-Forward (Khandani-Lo Q) | TradingView/Pepperstone validation + four-rules. |
| Capacity K below current capital allocation | CLOSED + auto-Forward (allocation review Q) | TradingView/Pepperstone validation + four-rules + re-MC trigger. |
| First all-three-loss day in panel | CLOSED + auto-Forward (regime-shift Q) | Live-PnL gap rule + TradingView/Pepperstone validation. |

A MSEE result can support an Action proposal; the proposal is validated by Joshua in TradingView against Pepperstone bars before any code/lock change (2026-04-28 policy update).
