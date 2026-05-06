# Sentinel USDCHF H4 — gate result (REJECTED, H2_KILL)

**Loop:** Sentinel build/no-build gate (parent brief 2026-05-03)
**Question (parent brief §4, single conjunction):** Across the full Pepperstone
USDCHF H4 panel 2022-01-04 → 2026-04-20, does a short-only Donchian(20)
breakdown + EMA(50) trend filter — with NO regime overlay — simultaneously
clear (a) N≥80, (b) PF≥2.0, (c) max DD<3.0%, AND (d) permutation p<0.05?
**Outcome:** **NO.** Three of four criteria fail. Verdict: **H2_KILL** —
entries are statistically indistinguishable from random placement within the
(session × weekday) candidate pool.
**Date closed:** 2026-05-03

## Single-page result (parent brief §6)

| Criterion | Threshold | Measured | Pass? |
|---|---:|---:|:---:|
| (a) N | ≥ 80 | **84** | ✅ |
| (b) PF | ≥ 2.0 | **1.026** | ❌ |
| (c) max DD | < 3.0% | **4.252%** | ❌ |
| (d) permutation p | < 0.05 | **0.944** | ❌ |

**Daily P&L correlation vs G/S/A** (1,120 business-day overlap):

| Strategy | r | Park-trigger? |
|---|---:|:---:|
| Guardian | +0.062 | no |
| Striker  | +0.001 | no |
| Aegis    | −0.020 | no |

All three correlations sit far below the 0.30 H3 park threshold, but this is
moot — PF/DD/perm-p failures dominate.

## What the permutation null says

Pool: 2,913 candidate H4 bars in (session 0800–1700 UTC × Mon–Fri × indicators
non-NaN), with 18 right-censored entries excluded. 1,000 shuffles; per shuffle,
N=84 timestamps drawn without replacement, simulated forward with same SL/TP
semantics, PF computed.

| Statistic | Value |
|---|---:|
| Observed PF | 1.026 |
| Null PF p05 / p50 / p95 | 0.724 / **1.076** / 1.504 |
| p (two-sided) | **0.944** |

Observed PF sits *below* the null median (1.026 vs 1.076). Random short entries
within the same mask would, on average, slightly out-perform the rule. There
is no within-mask edge to detect.

## ATR-quartile post-hoc diagnostic

Per Q2 decision: regime tag retained as diagnostic, never a filter. Quartiles
computed over panel-wide ATR(14) post-warmup.

| ATR quartile | n | win rate | PF | gross_profit_R | gross_loss_R |
|---|---:|---:|---:|---:|---:|
| Q1 (lowest vol)  | 19 | 0.368 | 0.755 | 9.21  | 12.20 |
| Q2               | 21 | 0.429 | 0.976 | 11.87 | 12.17 |
| Q3               | 17 | 0.235 | **0.401** | 5.28  | 13.16 |
| Q4 (highest vol) | 27 | 0.630 | **2.231** | 22.52 | 10.10 |

Q4 superficially clears the headline PF=2.0 — but: (i) n=27 is only 2 above
the Rule-1 small-cell threshold, (ii) acting on this would be the
explicitly-forbidden Pre-Q-D test "keep only trades that fit the CHF thesis"
applied via post-hoc volatility filtering. The brief's gate is
**unconditional**; this column is a diagnostic, not a rescue path. Memory
discipline: PF spike is *not* denominator-driven (gross_loss_R=10.10 from 10
losses ≈ -1.01R each, normal cost-adjusted SL distribution), so the issue is
genuine high win-rate concentration in high-vol regime — interesting *as a
forward observation* (see §"Notice-routed observation"), not as a rescue of
this gate.

## Verdict mechanics (parent brief §8)

Three independent kill criteria fired:

- **(b) PF** — observed 1.026 against required 2.0; no parameter retune in the
  same framework can lift this from 1.0× to 2.0× without re-introducing the
  v1.0 vol gate, which the brief deletes by construction.
- **(c) max DD** — equity drawdown reached -4.252% on 2026-04-02. Even if PF
  cleared, this fails portfolio-level dd_protection screening.
- **(d) permutation p** — 0.944. Entries are random within the mask. Memory
  discipline (state-readable observable bottleneck): this is the strongest
  evidence-of-absence of the four — positive evidence of randomness, not just
  insufficient signal.

Per §8 decision tree: PF fail OR perm-p fail → kill. Both fired. **H2_KILL.**

## Strategy parameters tested (parent brief §6, frozen)

```
Direction:   short-only
Entry:       close < Donchian(20)_lower_prior20 AND close < EMA(50)
             AND hour in [08,17] UTC AND weekday Mon-Fri AND flat
SL / TP:     entry + 3.0 × ATR(14)  /  entry - 4.0 × ATR(14)
Hold:        until SL or TP (no trail, no max-hold)
Risk:        0.50% per trade
Cost:        1.0 pip RT (Pepperstone-Razor USDCHF H4 conservative estimate)
```

Indicators use Pine v6 conventions (Wilder RMA for ATR, ewm with adjust=False
for EMA, prior-window-shifted Donchian).

## Notice-routed forward observation

> **USDCHF H4 short-Donchian without overlay does not exhibit a tradeable edge
> on Pepperstone 2022–2026.** The strategy is statistically indistinguishable
> from random within the (session × weekday) candidate pool.

Specific re-evaluation triggers (none of which are scheduled work):

- USDCHF realized vol regime shifts such that the panel-wide ATR(14) p75
  rises by ≥ 2× (would change the quartile composition; current finding's
  Q4 PF=2.231 cohort is a forward-observation marker, not an authorized
  filter)
- A high-impact CHF macro narrative re-emerges that systematically biases
  USDCHF downside (e.g., SNB intervention regime shift, EUR/CHF floor
  re-instatement) — physical-fact regime, would not by itself authorize an
  overlay (memory: leading-indicator-with-PnL-gate is the rationalizing
  form; live-PnL tripwire required, not a modeled gate)
- A different timeframe screen (D1, H1) on USDCHF that produces materially
  different N — separate INQHIORI loop with its own pre-Q gate

If none of those fire, this gate result stands. **No follow-up loop, no
parameter retry, no broader framework search.** AUDNZD-style closure.

## What this verdict does NOT mean

- It does not mean USDCHF is uninteresting at any timeframe — H4 short
  Donchian is one (rule, instrument, timeframe) cell, not the universe.
- It does not authorize a re-test with different SL/TP multiples or a longer
  Donchian; doing so without a fresh pre-Q gate would be the parameter-retry
  failure mode AUDNZD's closure note explicitly forbids.
- It does not retire the name "Sentinel" from future use. Sentinel as
  *concept* (USDCHF safe-haven hedge) was scoped 2026-04-13; this result
  closes the *no-overlay short-Donchian* operationalization. A different
  operationalization (e.g., long-only on a paired-instrument signal) would
  be a different brief with a different pre-Q gate.

## Out of scope (confirmed unmoved)

- ❌ No Pine v6 implementation work (gate-stage Python harness only)
- ❌ No portfolio Monte Carlo run (no fourth strategy to add)
- ❌ No allocation discussion (G 0.34% / S 1.00% / A 1.50% remain locked)
- ❌ No dd_protection retuning
- ❌ No modification of locked production parameters

## Deliverables (parent brief §6)

- Bar panel: [data/bar_data/USDCHF_pepperstone_h4_2020-06-25_to_2026-05-03.csv](../../../data/bar_data/USDCHF_pepperstone_h4_2020-06-25_to_2026-05-03.csv)
- Simulator: [analysis/archive/usdchf_sentinel/sentinel_simulator.py](../../../analysis/archive/usdchf_sentinel/sentinel_simulator.py)
- Permutation harness: [analysis/archive/usdchf_sentinel/permutation.py](../../../analysis/archive/usdchf_sentinel/permutation.py)
- Orchestrator + decision tree: [analysis/archive/usdchf_sentinel/run_sentinel_gate.py](../../../analysis/archive/usdchf_sentinel/run_sentinel_gate.py)
- Machine-readable results: [analysis/archive/usdchf_sentinel/results/sentinel_gate.json](../../../analysis/archive/usdchf_sentinel/results/sentinel_gate.json)
- ADR: [docs/adr/2026-05-03-sentinel-gate-decision.md](../../adr/2026-05-03-sentinel-gate-decision.md)

## Cross-references

- Parent brief: 2026-05-03 (chat — Sentinel USDCHF build/no-build gate)
- AUDNZD precedent (closure-note shape): [2026-04-26_audnzd_REJECTED.md](../archive/findings/2026-04-26_audnzd_REJECTED.md)
- Iran-Hormuz overlay deactivation (no-overlay rule): [docs/overlays/guardian_conflict_risk.md](../../overlays/guardian_conflict_risk.md)
- Two-tier canonical (Pepperstone is lock anchor): [feedback memory](../../../../.claude/projects/C--Users-joshu-prop-firm-pipeline/memory/feedback_two_tier_canonical_pepperstone_oanda.md)
