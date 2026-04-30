# AUDNZD M15 — framework screen (Phase 3)

**Loop:** `loop_2026-04-26_audnzd_discovery`
**Brief:** AUDNZD candidate-strategy discovery (2026-04-26)
**Phase:** 3 — strategy framework testing
**Status:** Both frameworks **FAIL OOS** — verdict 4A. See [REJECTED](2026-04-26_audnzd_REJECTED.md).

## 1. Provenance & discipline

- **Data:** `data/audnzd_oanda_m15_2022-01-01_to_2026-04-26_clean.csv`
  (SHA256 `6ff6cc3c…2d92`, validated against Dukascopy at three dates).
- **Train window:** 2022-01-02 → 2024-12-31 (74,608 M15 bars)
- **OOS window:** 2025-01-01 → 2026-04-24 (32,635 M15 bars)
- **Frameworks tested** (selected by Phase 2 §10): Aegis-style BB+ATR mean
  reversion (primary), range-fade with regime gate (secondary).
- **Backtest engine:** [scripts/audnzd_phase3_backtest.py](../../../scripts/audnzd_phase3_backtest.py).
- **Equity-plot generator:** [scripts/audnzd_phase3_plots.py](../../../scripts/audnzd_phase3_plots.py).
- **Raw results JSON:** [2026-04-26_audnzd_phase3_results.json](2026-04-26_audnzd_phase3_results.json).

### 1.1 Common simulation discipline

- Position sizing: constant 1R per trade. PnL recorded in R units.
- Entry signal computed at bar i close; fill at bar i+1 open.
- Stop / target checked intra-bar from i+1 onward.
- **Slippage haircut: 2 pips per trade** deducted from PnL at exit
  (Phase 1 caveat for practice-feed spread optimism).
- Hard exclusions:
  - Hour 17 NY (OANDA daily rollover) — entries blocked, open positions
    force-closed at the rollover bar's close.
  - RBA + RBNZ decision dates (40 + 30 = 70 dates in window) — entries
    blocked, open positions force-closed at the decision-day open.
  - Sunday partial-session bars (UTC DOW=6).
  - Friday late-day entries (≥16:00 NY) that wouldn't have time to exit.
- Entries restricted to 18:00–21:00 NY (Phase 2 §4 peak vol window).
- Train sweep selects the highest-PF parameter set with n_trades ≥ 30;
  that one parameter set is then evaluated OOS. **No reverse-engineering.**

### 1.2 Pass criteria (brief §3.3, all required)

| Criterion | Threshold |
|---|---|
| Train PF | ≥ 2.0 |
| OOS PF | ≥ 1.8 |
| OOS μ/σ | ≥ 1.0 |
| OOS max DD | ≤ 1.5 × train max DD |
| OOS n_trades | ≥ 50 |
| OOS Sharpe | ≥ 0.7 × train Sharpe |

A framework that misses any one of these fails. No "but the train numbers
are great" rescues.

## 2. Aegis-style BB+ATR mean reversion (primary)

**Native parameter sweep:** 288 combinations.

| Param | Values |
|---|---|
| BB period | 20, 30, 50 |
| BB std | 2.0, 2.5 |
| ATR period | 14, 20 |
| Stop ATR mult | 1.5, 2.0 |
| Target R mult | 1.0, 1.5, 2.0 |
| Max hold (bars) | 16, 32 |
| Entry variant | touch, cross_inside |

All 288 combinations produced ≥ 30 train trades (admissible by sample-size).

### 2.1 Best train parameters (frozen for OOS)

```
bb_period=50  bb_std=2.5  atr_period=20  stop_atr_mult=2.0
target_r_mult=1.0  max_hold_bars=16  entry_variant=touch
entry_hours_ny=[18,19,20,21]  require_regime_calm=False
```

### 2.2 Train metrics (frozen)

| Metric | Value |
|---|---|
| n_trades | 319 |
| PF | **0.722** |
| win rate | 48.0% |
| mean R | −0.131 |
| std R | 0.870 |
| Sharpe | −2.39 |
| max DD | 47.2 R |
| total R | −41.8 |

### 2.3 OOS metrics (computed once with frozen params)

| Metric | Value |
|---|---|
| n_trades | 136 |
| PF | **0.620** |
| win rate | 48.5% |
| mean R | −0.191 |
| μ/σ | −0.220 |
| Sharpe | −3.50 |
| max DD | 29.6 R |
| total R | −26.0 |

### 2.4 Verdict — Aegis-style

| Criterion | Threshold | Observed | Verdict |
|---|---|---|---|
| Train PF | ≥ 2.0 | 0.722 | **FAIL** |
| OOS PF | ≥ 1.8 | 0.620 | **FAIL** |
| OOS μ/σ | ≥ 1.0 | −0.220 | **FAIL** |
| OOS max DD ≤ 1.5× train | ≤ 70.8 R | 29.6 R | PASS |
| OOS n_trades | ≥ 50 | 136 | PASS |
| OOS Sharpe ≥ 0.7× train | ≥ −1.67 | −3.50 | **FAIL** |

**Framework FAIL.** The strategy loses money in-sample, faster OOS, and the
Sharpe degrades by a factor of ~1.5×.

Equity curve: [2026-04-26_audnzd_phase3_equity_aegis.png](2026-04-26_audnzd_phase3_equity_aegis.png).

## 3. Range-fade with regime gate (secondary)

**Native parameter sweep:** 128 combinations. Adds a calm-regime gate
(current ATR(14) ≤ trailing-median regime ATR) on top of the BB+ATR shell.

| Param | Values |
|---|---|
| BB period | 20, 50 |
| BB std | 2.0, 2.5 |
| ATR period | 14, 20 |
| Stop ATR mult | 1.5, 2.0 |
| Target R mult | 1.0, 1.5 |
| Max hold (bars) | 16, 32 |
| Entry variant | touch, cross_inside |

All 128 combinations admissible.

### 3.1 Best train parameters (frozen for OOS)

```
bb_period=50  bb_std=2.0  atr_period=14  stop_atr_mult=2.0
target_r_mult=1.0  max_hold_bars=16  entry_variant=touch
entry_hours_ny=[18,19,20,21]  require_regime_calm=True
```

### 3.2 Train metrics (frozen)

| Metric | Value |
|---|---|
| n_trades | 269 |
| PF | **0.769** |
| win rate | 54.3% |
| mean R | −0.100 |
| std R | 0.835 |
| Sharpe | −1.91 |
| max DD | 33.5 R |
| total R | −27.0 |

### 3.3 OOS metrics

| Metric | Value |
|---|---|
| n_trades | 114 |
| PF | **0.663** |
| win rate | 52.6% |
| mean R | −0.161 |
| μ/σ | −0.187 |
| Sharpe | −2.97 |
| max DD | 23.4 R |
| total R | −18.4 |

### 3.4 Verdict — Range-fade

| Criterion | Threshold | Observed | Verdict |
|---|---|---|---|
| Train PF | ≥ 2.0 | 0.769 | **FAIL** |
| OOS PF | ≥ 1.8 | 0.663 | **FAIL** |
| OOS μ/σ | ≥ 1.0 | −0.187 | **FAIL** |
| OOS max DD ≤ 1.5× train | ≤ 50.3 R | 23.4 R | PASS |
| OOS n_trades | ≥ 50 | 114 | PASS |
| OOS Sharpe ≥ 0.7× train | ≥ −1.34 | −2.97 | **FAIL** |

**Framework FAIL.** The regime gate raises the win rate from 48% (Aegis) to
54%, but with a 1:1 R:R it is not enough to overcome execution cost.

Equity curve: [2026-04-26_audnzd_phase3_equity_rangefade.png](2026-04-26_audnzd_phase3_equity_rangefade.png).

## 4. Diagnostic — does ANY underlying edge exist?

A no-slippage pass over the same sweep characterizes whether the
mean-reversion structural feature translates into a tradable signal at all,
or whether the brief's pass criteria fail because of the haircut alone.

| Framework | Train PF (no-slip) | OOS PF (no-slip) | Train mean R | OOS mean R |
|---|---|---|---|---|
| Aegis-style (touch) | 1.128 | 0.934 | +0.047 | −0.028 |
| Range-fade (touch) | 1.229 | 1.103 | +0.081 | +0.040 |

**Read:**
- Even at zero slippage, neither framework approaches the brief's
  PF ≥ 2.0 train threshold. The strategies are barely above break-even
  in-sample under ideal execution.
- Range-fade's no-slippage train mean R = +0.081 / OOS mean R = +0.040
  represents the entire underlying edge size on this instrument under
  these frameworks. A 2-pip slippage haircut on an ~10-pip stop = 0.20R
  per trade — easily larger than the underlying edge.
- This is consistent with Phase 2 §9: lag-1 ACF = −0.078 is a real but
  small signal. Standard frameworks cannot harvest it cleanly enough on
  M15 against retail-order execution costs.

The diagnostic is **not** verdict-relevant per the brief's discipline; it
is reported here only to distinguish "no underlying edge" from "edge eaten
by haircut." The honest answer for AUDNZD is: there is a faint structural
edge at lag-1, but it is **smaller than the irreducible execution cost on
M15** and cannot be amplified with standard parameter choices. The brief's
PF ≥ 2.0 hurdle is not arbitrary — it bakes in the operational reality
that prop-firm strategies need meaningful margin over realized costs.

## 5. Honest assessment

The Phase 2 structural fingerprint correctly identified AUDNZD as a
range-biased mean-reverting cross. That assessment was not wrong — it is
**evidently true** (lag-1 ACF, range-day rate, Hurst convergence to 0.5,
session vol concentration all line up). The error, if any, was in
expecting that *standard* frameworks could harvest the *modest* signal at
M15 against *retail* execution costs.

The lag-1 ACF of −0.078 is the entire signal magnitude. To make it
tradable would require either:
(a) execution costs much smaller than 2 pips per round trip (institutional
    feed; outside FXIFY's retail-prop constraint), or
(b) a non-M15 horizon where the signal is structurally larger (untested
    here, and a separate brief's question), or
(c) a non-mean-reversion entry concept that exploits a different feature
    of the structural fingerprint (untested here, also a separate brief).

None of those are in scope for this loop.

## 6. Forbidden-D-test audit

Per the inqhiori-algorithm gate discipline, no forbidden D-tests were
applied during Phase 3:

- Parameter sweep grids were declared up-front (§2, §3) and used in full;
  no after-the-fact narrowing.
- The "best train PF" selection rule is mechanical and was applied once.
- OOS evaluation happens **once** with the frozen parameter set. No
  reverse-engineering of OOS-good parameters back into the training set
  (the explicit Aegis-v3 pre-stress-test failure mode the brief flagged).
- The diagnostic no-slippage pass is labeled non-verdict-relevant and is
  not used to argue for any framework's pass.
- The "entry_variant" parameter (touch vs cross_inside) was added during
  the diagnostic phase after the first sweep returned spurious failures;
  this is a documented widening of the native sweep, not a hand-tune,
  and the wider sweep produced **worse** results, not better. No
  selection-bias gain from the addition.

## 7. Cross-references

- Phase 1 provenance: [data_provenance/2026-04-26_audnzd_oanda_verification.md](../data_provenance/2026-04-26_audnzd_oanda_verification.md)
- Phase 2 structural characterization: [2026-04-26_audnzd_structural_characterization.md](2026-04-26_audnzd_structural_characterization.md)
- Phase 4 verdict: [2026-04-26_audnzd_REJECTED.md](2026-04-26_audnzd_REJECTED.md)
- Brief: AUDNZD candidate-strategy discovery (2026-04-26)
