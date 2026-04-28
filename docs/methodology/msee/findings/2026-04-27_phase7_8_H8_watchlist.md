# MSEE Phases 7–8 — H8 invasion-fitness + watch-list ops monitor

**Date:** 2026-04-27
**Corpus:** OANDA-proxy + bar_data
**Canonical status:** PROXY
**Routing rule:** [observation_routing.md](../../observation_routing.md)

## Q-MSEE-8 — Invasion-fitness battery (H8) → CLOSED-POSITIVE (battery validated)

`analysis/msee/h8_invasion_fitness.py` — reusable battery (`--candidate path/to/cand.csv` or `--demo`). Inputs: candidate daily R series + proposed allocation. Outputs: standalone fitness + correlation matrices to G/S/A in normal / stress / full slices + reject criterion check (stress correlation > 0.30 to any existing strategy).

### First test — synthetic stress-correlated demo

Demo candidate constructed to be stress-correlated to Striker (60% Striker copy on stress days + noise) but uncorrelated otherwise:

| Slice | vs guardian | vs striker | vs aegis |
|-------|-------------|------------|----------|
| calm  | +0.006 | −0.031 | −0.042 |
| stress | +0.235 | **+0.449** | +0.235 |
| full  | +0.026 | −0.017 | −0.033 |

Battery correctly flags `stress vs striker = +0.449 > 0.30` and **REJECTS** the candidate despite standalone Sharpe 3.36 / PF 1.71 / WR 0.59 — exactly the failure mode P9 predicts (a candidate that would pass naive normal-regime screens but fail under stress).

### AUDNZD candidate — already REJECTED upstream

The first real-world candidate referenced in the plan (AUDNZD) was REJECTED at the project's existing Phase-3 framework screen (`docs/methodology/findings/2026-04-26_audnzd_REJECTED.md`) with train PF = 0.72 (well below 2.0 threshold). No daily-R series produced for that candidate — H8 cannot be run on it without re-executing the backtest. The H8 battery is therefore **available for future candidates** that pass the project's existing standalone-fitness screen.

**Routes Closed-POSITIVE.** Battery validated on synthetic case; ready for production use on next candidate.

## Phase 8 — Watch-list operational monitor → CLOSED-POSITIVE

`scripts/msee_watchlist.py` + `docs/methodology/msee/watch_list.md`. Weekly digest at `analysis/msee/watch_{date}.md` + JSON sidecar.

### First run — 2026-04-27 baseline

Crossings: **1 INFO** (cluster_2_quarter_count: 6 |XAU| ≥ 4% days in last 90d, consistent with elevated 2026-Q1 XAU volatility per Iran/Hormuz overlay window). No HARD or SOFT crossings.

Indicator values:

| Indicator | Value | Status |
|-----------|-------|--------|
| joint_loss_days (panel) | 0 / 2 all-three-traded days | clean |
| G/A stress corr (rolling 6mo) | None (n<5 stress days) | insufficient stress data |
| Portfolio quarter max DD | 2.43% | < 4% soft, < 4.5% hard |
| Guardian rolling-50 WR / R-of-winners | 0.28 / 15.32R | normal |
| Striker rolling-50 WR / R-of-winners | 0.70 / 0.33R | matches CLAUDE.md ~71% headline |
| Aegis rolling-50 WR / R-of-winners | 0.38 / 0.11R | mild density-rise (per H10) |
| Aegis 15m USDJPY Hurst (rolling 90d) | 0.539 | below 0.55 threshold; 0.011 from crossing |
| Cluster-2 (|XAU|≥4%) days in quarter | 6 | INFO threshold crossed |

### Notable observations

- **Aegis Hurst 0.539 — 0.011 from threshold.** Closest single indicator to its threshold. If it crosses 0.55 persistently, that's the load-bearing Aegis-niche-shrinking signal from source report Part V.5.3. Worth weekly recheck.
- **G/A stress correlation cannot be evaluated this window** because only 4 stress days fell in the trailing 6mo. The +0.60 finding from H6c was on the full 4yr window (28 stress days). Quarterly evaluation will be unreliable until more stress days accumulate; longer window may be more diagnostic.
- **Cluster-2 INFO crossing**: 6 |XAU|≥4% days in 90d is high relative to 4yr rate (~25 days / 4yr ≈ 1.6/quarter). 4× normal rate this quarter. **Auto-Forward Q-MSEE-watch.1 opened**: characterize the 2026-Q1 XAU volatility regime — is it Iran/Hormuz residual, structural rate-environment shift, or a new regime not covered by historical clusters? Cheapest test: re-cluster on rolling window and check if a new cluster emerges.

**Routes Closed-POSITIVE.** Watch-list operational. Cadence: weekly with `cli.py update`. Auto-Forward Q-MSEE-watch.1 added to open_questions.md.

## Project completion summary

All 9 phases of the MSEE plan are complete. Artefact map:

- **Foundation:** `analysis/msee/daily_strategy_returns.py` → 420 trade-dates × 3 strategies, q14 reconcile to 3.55e-15
- **Cheapest falsifications (Phase 1):** H3 (POSITIVE — covariances negative as predicted), H10 (NEUTRAL with mild S/A density-rise), H4 (INCONCLUSIVE — no decay in panel)
- **Conditional correlations (Phase 2):** H6c — guardian/aegis stress correlation +0.60 (P2 partially supported on 28 stress days)
- **Punctuated equilibrium (Phase 3):** H5 — TRANSITIONAL at 90d; CONTINUOUS-DRIFT at 30d; window-dependent
- **Storage conditions (Phase 4):** H2 PARTIAL (best clusters distinct only at k≥5, perm p=0.074), H6 PARTIAL (cond 1 PARTIAL, cond 2 INSUFFICIENT DATA, cond 3 PASS)
- **OOS forecast (Phase 5):** H7 MIXED (regime forecast 75% > 54% chance; predicted-best test degenerate by Guardian-dominance)
- **MC perturbation (Phase 6):** mc_explore.py mirrors lock-MC; H1 reports portfolio-outcome sensitivity (lock-decision logic re-validated); H9 DEFERRED awaiting slippage model
- **Invasion fitness (Phase 7):** H8 battery validated on synthetic; ready for next real candidate
- **Watch-list (Phase 8):** weekly digest live; 1 INFO crossing on 2026-04-27 baseline

**Lock-path audit:** `portfolio_mc.py`, `dd_protection.py`, `firm_rules.py`, `accounts.py` UNCHANGED across all 9 phases.

**Forward questions added to open_questions.md:** Q-MSEE-6c.1 (Khandani-Lo G/A stress correlation), Q-MSEE-6.1 (Guardian-only re-MC at locked alloc with thin DD margin), Q-MSEE-7b (reformulate strategy-rotation framing), Q-MSEE-9.1 (strict capacity test when slippage model available), Q-MSEE-watch.1 (2026-Q1 XAU regime characterization).

**No Action triggered. No re-MC trigger fired. All findings remain PROXY-class until Pepperstone re-fit.**
