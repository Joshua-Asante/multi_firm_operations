# Methodology: 1R estimation for bimodal exit distributions

**Date established:** 2026-04-17
**Status:** Active — applies to any portfolio MC run that normalizes CSV backtest P&L to target risk allocations.

## Why this matters

Portfolio Monte Carlo (`portfolio_mc.py`) takes CSV backtest output from each strategy and normalizes P&L to a target risk allocation. The normalization requires a 1R estimator — the typical loss size in backtest-dollar terms — so that target allocation can be expressed as a simple multiplier on normalized P&L.

**If the 1R estimator is wrong, every MC number downstream is wrong.** Bust rate, pass rate, DD distribution, bust attribution — all distorted by the normalization error.

## The problem

Strategies with active exit management (breakeven, trailing stop, partial exits) produce **bimodal loss distributions**:
- **Full-stop losses:** trades that move against entry immediately and hit the initial SL. These are "1R" in the conventional sense.
- **BE-stopped or partial-stopped losses:** trades that moved favorably, triggered BE or a partial take, then retraced to close at BE or small profit/loss. These are typically much smaller losses than full-stops — or even small wins misclassified as "losses" if the trade exited at BE minus spread.

Using median loss as the 1R estimator conflates these two modes. The median of a bimodal distribution is a meaningless statistic for the purpose of sizing normalization — it depends on the ratio of the two modes, which varies across backtest windows and regimes.

## The correction

Apply per-strategy 1R estimation based on the strategy's exit architecture:

### Strategies with no exit management (unimodal loss distribution)

**Guardian v5.5** is the current example. No BE, no trail, no MFE-BE. All losses are full-stops. The loss distribution is unimodal and tightly clustered around the configured 0.34% risk per trade — measured against contemporaneous equity, the per-trade denominator the Pine script actually uses.

- **Estimator:** median loss is acceptable (the unimodal full-stop distribution is tight).
- **Implementation:** `median(abs(loss_pnl))` where `loss_pnl` is filtered to loss trades only.

#### Equity-compounding normalization — required when reporting 1R as a percent

Pine sizes positions off contemporaneous equity (`guardian_gold_v5.5.pine:192-194`):

```pine
calcSize(stopDist) =>
    risk = strategy.equity * (riskPerTrade / 100)
    stopDist > 0 ? risk / stopDist : 0
```

So `qty` scales with equity. Realized $ losses scale with equity. Reporting a backtest's 1R as a percent **requires normalizing each trade's loss by the equity that was live when that trade was sized** — not by fixed initial capital. Normalizing to fixed initial capital inflates the realized % by the equity-growth factor (mean entry equity / initial), which over a multi-year compounding backtest can be 2× or more.

- **Correct denominator:** `equity_at_entry_i = initial_capital + sum(P&L_j for j < i)`. Equivalent to `200_000 + Cumulative P&L USD` from the prior trade row in a TradingView export.
- **Acceptable approximation:** `equity_at_close` (off by one trade's P&L; differs from entry-equity 1R by < 0.001 percentage points on the Guardian panel).
- **Wrong denominator:** fixed `initial_capital`. Produces an inflated number that does not reflect actual per-trade risk-taking.

#### Guardian v5.5 — measured 1R, three normalizations (n=158, OANDA 2022-01-11 → 2026-04-20)

**Feed:** OANDA XAUUSD via `Guardian_Gold_v5.5_OANDA_XAUUSD_2026-04-25_9ae1f.csv`.
The canonical lock-of-record portfolio MC was calibrated on the **Pepperstone**
2022→2026 panel (per CLAUDE.md Protection section). The OANDA panel is used here
because it is the only on-disk artefact with the matching v5.5-locked snapshot
and a clean equity-progression column. The result (median realized loss / equity
at entry ≈ designed risk) is structural to compounding percent-risk sizing and
is feed-independent in expectation, but the exact percentiles below are
OANDA-specific. The Pepperstone-vs-OANDA reconciliation is a separate question;
this update does not assert that Pepperstone numbers match the table below to
4 decimal places — only that the equity-compounding artefact is the correct
explanation in either feed.

Reproducible via `python analysis/1r_diagnosis.py` against
`data/tv_exports/oanda/Guardian_Gold_v5.5_OANDA_XAUUSD_2026-04-25_9ae1f.csv`.

| Normalization                          | Median   | Mean     | p25      | p75      | Notes |
|----------------------------------------|----------|----------|----------|----------|-------|
| `loss / fixed $200K`                   | 0.5787%  | 0.6582%  | 0.3925%  | 0.8104%  | Equity-compounding artefact — do not use |
| `loss / equity_at_entry` **(canonical)** | **0.3405%** | **0.3437%** | **0.3402%** | **0.3407%** | Matches designed 0.34% to 4dp |
| `loss / equity_at_close`               | 0.3417%  | 0.3449%  | 0.3414%  | 0.3419%  | ≈ entry-equity, off by 1 trade's P&L |

**Resolution:** The 0.58% / 0.66% figure that previously sat in this doc was a fixed-$200K normalization artefact, not a sizing problem. Guardian sizes correctly at 0.34% of contemporaneous equity. Mean equity at entry across the panel was $388K (1.94× initial); final equity $865K (4.33× initial). Tight p25–p75 (0.3402–0.3407%) confirms the script hits its target risk on essentially every full-stop trade — the trace mean is fractionally above median because of a thin upper tail (max 0.6806% = **2.000× designed, exactly**) attributable to the grace-stop mechanism by design: `graceStopMult=2.0` widens the stop to `2.0 × 1.55 × ATR` for the first `minBarsBeforeStop=1` bar after entry (`Guardian_Gold_v5.5_Strategy.pine:49,195-197`); trades that exit during the grace window realize 2× the normal stop loss as a structural feature, not as slippage. The tail is small, does not threaten MC calibration (`portfolio_mc.py` reads actual trade P&Ls, so realized losses including the grace-stop trades are already in the simulation), and does not change any allocation or `dd_protection` constant. Earlier version of this paragraph attributed the tail to weekend gap / slippage events; that attribution was incorrect and is corrected here.

#### Live calibration — Rule 0 cross-check on `accounts.calc_multiplier`

Sizing equivalence between the backtest and live operations is not assumed; it
is checked. `accounts.calc_multiplier` (`accounts.py:67-87`) computes
`floor((balance × tier_pct) / (200K × baseline_pct) × 100) / 100`. With
challenge-tier and funded-tier risk percentages unified at the baseline values
(`firm_rules.py:25-28` — `RISK_TIERS["challenge"]` and `["funded"]` both equal
`BASELINE_RISK`), this collapses to `multiplier = floor(balance / 200K, 2dp)`.
A Pine indicator's lot output is for a $200K baseline; live lots = indicator
lots × multiplier; therefore `live $-at-risk per trade ≈ balance × baseline_pct`
— a balance-compounding sizing model.

The live model is therefore equivalent to Pine's `strategy.equity` per-trade
compounding **at weekly resolution**, not per-trade resolution: per CLAUDE.md
the multiplier "updates weekly when balances update (via `python cli.py update`),
not daily." Within-week balance drift is not captured by the multiplier.
Within-week drawdown drift, however, *is* captured by `dd_protection.py`'s 1%
peak-drawdown trigger which cuts the day's sizing by 0.40× the moment equity
drops 1% below peak. So the live system is balance-compounding at weekly
resolution with intra-week DD coverage from `dd_protection`. The 1R diagnosis
holds for live to first order, with the remaining gap (intra-week
positive-drift) being a second-order under-sizing during winning weeks — a
conservative direction that does not threaten DD calibration.

**Verdict:** live calibration confirmed. The "system sizes correctly at 0.34%
of contemporaneous equity" statement applies to the live pipeline, with
intra-week balance drift bounded by `dd_protection`'s 1% trigger.

#### Striker — pyramid decomposition (corrects an initial misframing)

The 1R diagnosis above is Guardian-specific. Extending the same equity-
normalized loss measurement to Striker and Aegis surfaced a 17% mean
inflation on Striker (1.1715% per-loss vs designed 1.00%). An initial
reading framed this as "Striker tail-of-loss event" — that framing was
wrong. Pyramid decomposition (`analysis/striker_pyramid_decomposition.py`)
shows the 17% is primarily an artefact of treating each pyramid layer as
an independent Trade-# in the per-Trade mean, not a system-wide
overshoot.

Per-signal-class loss decomposition (n=62 losses, OANDA panel):

| Bucket                            | n  | mean loss% | median | max     | inflation vs 1.00% designed |
|-----------------------------------|----|------------|--------|---------|----------------------------:|
| Initial entries (`Long`/`Short`)  | 50 | **1.0289%**| 1.0062%| 3.5611% | **+2.9%** (= sized correctly) |
| Pyramid layers (`*_Add`)          | 12 | **1.7658%**| 1.9129%| 2.5261% | **+76.6%** (against pyramid-layer equity) |
| Combined per-Trade-#              | 62 | 1.1715%    | 1.0058%| 3.5611% | +17.2% (= the 17% headline)   |

Pyramid penetration: 29 of 204 initial entries extended (14.2%), of which
22 wins and 7 losses on the trade-group level. The pyramid sizing
multiplier in the panel is **3.50× initial qty** verified directly from
the raw `Size (qty)` columns of all 29 layer-1 / layer-2 pairs:
`min(layer2_qty / layer1_qty) = 3.499865`,
`max = 3.501093`, spread `0.001229` — entirely consistent with 4dp qty
rounding in the CSV (no implementation drift). Multiple pairs (e.g.
2022-08-12, 2026-01-06) are exact to 4dp. Every pair also entered with
positive layer-2-vs-layer-1 entry-price delta, confirming the pyramid
trigger is gated on favorable layer-1 movement.

Trade-group decomposition (initial + same-bar pyramid exits collapsed,
sum of P&L per group / equity at first-entry of group):

| Group size | n   | wins | losses | BE | mean loss% | max group-loss% |
|------------|-----|------|--------|----|------------|----------------:|
| 1-leg      | 175 | 125  | 50     | 0  | 1.0289%    | **3.5611%**     |
| 2-leg      |  29 |  22  |  7     | 0  | 0.8021%    | 2.0092%         |
| 3-leg+     |   0 |   —  |  —     | —  | —          | —               |

**Corrected framing.**

1. **Striker initial entries are sized correctly.** Mean +2.9% vs designed,
   median 1.0062%. The system hits 1R on essentially every full-stop
   single-leg trade.
2. **The 17% headline inflation is a measurement artefact** of counting
   each pyramid leg as an equal-weight observation in the per-Trade-# mean.
   Pyramid layers run at 3.50× initial qty and stop out at ~1.77% of
   pyramid-layer equity, which by construction is larger than initial-
   layer equity at the moment the pyramid was added.
3. **Trade-group risk is *better* than non-pyramided would be**, not worse.
   2-leg groups (initial + pyramid that both close together) have mean
   group-loss 0.8021% — *smaller* than 1-leg's 1.0289%. Mechanism: the
   pyramid only triggers after the initial moves favorably; on reversal,
   the initial closes near or above breakeven while the pyramid takes
   the SL hit. The layer-1 cushion absorbs.
4. **The 3.56% worst-observed combined day** (2025-02-07, the figure that
   prompted the original tail concern) was a **1-leg initial entry**, not
   a pyramid event. It is a regular gap/slippage outlier on DJ30 — the
   real fat-tail signal is on the initial-entry distribution at its
   max, not on pyramid mechanics.

**Re-cal-trigger candidacy.** The original Forward-bucket framing flagged
this for re-cal candidacy on the assumption that Striker was systematically
under-risk-stated. After decomposition, that framing is weaker:

- The pyramid-layer-only +76.6% inflation is real but **already baked into
  MC calibration** because `portfolio_mc.py` consumes raw trade P&Ls per
  Trade-# (including pyramid-leg rows) — the simulator sees the actual
  realized losses.
- The initial-entry +2.9% inflation is within measurement noise of zero.
- The 3.56% one-event outlier is a fat tail on the initial-entry
  distribution, not a structural mis-sizing.

The Forward question therefore narrows: **does the initial-entry
distribution's max (3.56%) plus realistic correlated-day pairings
challenge `dd_protection`'s working envelope?** This is decidable from the
existing panel + the existing simulator output without re-MC and without
new data. **Tag: re-cal-trigger candidate** — flag this for the next MC
pre-flight reconciliation so it surfaces immediately rather than being
re-discovered. The trigger does not fire today (no version bump, no 6mo
live data, no allocation change, no `dd_protection` constant change), but
it is the kind of structural finding that justifies an early MC pass if
the inflation factor *grows* in live data.

**Empirical answer to the narrowed question (combined-account simulator,
`archive/analysis/dd_protection_trace.py`):** of the three branches (a) trigger
fired beforehand and live max < 3.56%, (b) trigger never engaged and the
outlier passed through untouched, (c) trigger engaged but post-cut residual
was still material — **branch (b)** holds for the 2025-02-07 day in this
panel. Combined-account state at morning check on 2025-02-07: equity at
fresh peak ($601,461), DD-from-peak 0.000%, multiplier 1.00×. The Striker
-3.561% loss passed through at full risk; daily DD floor consumed = 71.2%
of the 5.00% FXIFY budget on a single trade. The trigger engaged the *next*
trade-day (2025-02-11, DD-from-peak now 3.561%) and stayed engaged for
roughly two weeks of recovery. The largest DD-from-peak in the entire
4-year combined panel was 3.561% on 2025-02-11 — that one trade produced
the worst observed DD across the whole window. Trigger frequency across
the panel: 188 of 419 trade-days = **44.9%**. The rule is doing real work,
but its work is post-event sizing reduction, not within-day single-trade
protection.

**Mechanism note (limits the rule's protective scope, design-intentional):**
`dd_protection.py` is a morning pre-market tool that fires once per day at
the start-of-day check. It cannot reduce a single-trade tail event that
happens on a day starting at peak — by construction. The 4-year panel
contains exactly one day with any strategy losing > 2.00% in a day
(2025-02-07 itself); not a recurring pattern, but the envelope margin on
that single observation was 1.44 percentage points. This narrows what the
re-cal-trigger-candidate tag should look for in live: a *second*
single-trade outlier within the budget-consumption window of a first one,
not the steady-state tail of routine losses.

**Confirmation: canonical MC metrics are net-of-rule.** `portfolio_mc.py`
applies `dd_protection` in-loop (`portfolio_mc.py:148-150`: `scale =
dd_scale if dd_from_peak <= -dd_trigger else 1.0`); the scaled P&L feeds
both the bust checks (lines 154-157) and the peak tracking (line 161). So
the locked headline figures (92.73% pass / 0.65% bust / p99 DD 4.94% under
the 3-strategy lock; re-anchored 2026-05-05 to 97.88% / 0.22% / 4.55% under
the 4-strategy lock — see `strategies/striker/striker_CHANGELOG.md` v4.5
entry) are **already attenuated by the rule** — `dd_protection` is part of the
calibrated system, not a detachable post-hoc overlay. The 44.9% panel
trigger frequency from the trace above is therefore a property of the same
system whose pass/bust numbers are anchored.

**Pre-staged Forward question — category-gap fix vs live-monitor.** The
2025-02-07 result is a structural category gap, not a configuration miss:
`dd_protection`'s daily cadence cannot, by construction, attenuate a
fresh-peak single-trade outlier. Two structurally distinct responses are
on the table; do not decide now (`dd_protection` constants are
out-of-scope for this brief), but pre-stage the choice so the next
allocation review or 6-month live reconciliation walks into a known
question, not a fresh one:

  1. **Within-day per-trade hard-cap** — a separate tripwire layered on
     top of the existing daily-cadence rule, capping any single trade's
     realized loss at e.g. 2.0% of equity at entry. Closes the category
     gap by construction. Cost: adds operational surface area, requires
     re-MC to confirm the cap value does not over-attenuate Striker's
     pyramid-driven PF (94% of historical Striker profit sits above the
     cap-clip threshold for the largest pyramid stacks).
  2. **Leave the rule and observe live** — accept that the gap is real
     but the base rate of fresh-peak single-trade outliers is, in the
     panel, exactly one event in four years. With n=1, the conditional
     probability of a *second* outlier inside the budget-consumption
     window of a first is unestimable from history (you would be fitting
     a Poisson on n=1). The honest framing is that this question may be
     decidable **only from live data** — meaning the gap cannot be closed
     pre-launch and has to be monitored live with a tripwire (e.g., an
     alert that fires when any single trade exceeds 2.0% of equity at
     entry, even if `dd_protection` itself does not engage).

The choice is between closing-by-construction (option 1) and
closing-by-observation (option 2 with a live tripwire). Option 2 is
cheaper today and falsifiable in 6 months from live data; option 1 is
permanent insurance whose price (potential PF drag on pyramid extensions)
is currently unquantified. Tagged Forward, gated downstream on either
allocation review or 6-month live reconciliation, whichever fires first.

#### Live ↔ backtest pyramid divergence (one-liner caveat)

The live-calibration equivalence stated above is **first-order, initial-
entry only.** Pyramid sizing has a tracked divergence:

- **Backtest:** layer-2 sizes off `strategy.equity`, which credits
  layer-1's open profit at the moment layer-2 enters. So backtest layer-2
  qty reflects the favorable mid-trade equity position.
- **Live:** layer-2 sizes off the same weekly balance snapshot as
  layer-1; no open-profit credit. Layer-2 qty is undersized relative to
  backtest.

Asymmetric impact: live undersizes layer-2 in winning extensions (drag on
PF since 94% of Striker profit historically comes from pyramid extensions
per the v4.3-pyramid ADR) and undersizes in losing extensions (modest
benefit on the rare reversal-at-pyramid case). Net direction: live PF on
Striker tracks below backtest PF; magnitude scales with how favorable
layer-1 was at the moment layer-2 fires. Quantification requires per-trade
open-profit data, which the current CSV panel does not directly expose.
Routed Forward as part of the same re-cal-trigger-candidate question.

> **Forward signpost for the 6-month live reconciliation:** 94% of historical
> Striker profit is pyramid-driven; live undersizing on layer-2 (no
> open-profit credit on the weekly-balance multiplier) is therefore the
> dominant expected live-vs-backtest PF gap on Striker, magnitude TBD.
> The reconciliation should be looking for this specific divergence — not
> discovering it as a surprise.

#### Quantization bias in `calc_multiplier` (sub-1% sizing drag, not actioned)

`accounts.calc_multiplier` returns `floor((balance × tier_pct) /
(200K × baseline_pct) × 100) / 100` — i.e., the multiplier is rounded
down to 2 decimal places, equivalent to a 1% balance step (every $2K of
balance change). At $201,999 the multiplier is `floor(1.00999, 2dp) = 1.00`
(sized for $200K equivalent); at $202,000 it steps to 1.01.

Combined with the weekly update cadence, mid-week growth is systematically
under-weighted. This is a sub-1% sizing drag — small at current scale,
asymmetrically helpful on the DD side (under-compounded after positive
weeks = smaller loss exposure if next-week reverses) and unhelpful on the
upside compounding. Direction is conservative; not worth fixing now;
documenting that it exists.

#### Striker correlated-day pressure test (panel reference)

The original observed-pressure-test results are unchanged by the
decomposition above; logged here for traceability:

- Worst observed combined-day loss across G+S+A: **3.56%** of equity at
  entry, on 2025-02-07. Single-strategy (Striker), single-trade, 1-leg
  initial entry.
- Daily-total combined-loss distribution across 230 loss-days (4-year
  panel): p50 0.34%, p75 1.00%, p90 1.35%, p95 1.67%, p99 2.37%, max 3.56%.
- **Zero 3-strategy correlated loss days** across the 4-year panel; 16
  days had 2-strategy losses (max 1.81%); the 3.56% worst day was
  1-strategy.
- FXIFY 5.00% daily floor not breached on observed history; p99 daily
  combined sits 2.63 percentage points inside the floor; max sits 1.44
  percentage points inside.

Reproducible: `python analysis/correlated_day_check.py` and
`python analysis/striker_pyramid_decomposition.py`.

#### Trade-count reconciliation vs canonical 201 / 20.40% WR

The canonical Guardian v5.5 figure cited in CLAUDE.md and prior briefs is 201 trades / 20.40% WR (≈41W / 160L). The OANDA panel above shows 200 / 21.00% WR (42W / 158L). The OANDA file is fully closed — Trade #200 exits 2026-04-20 18:00, no open positions at the panel boundary. The 1-trade / 2-loss / 1-win delta is therefore between snapshots (different feed window or pre-2026-04-23-lock backtest), not an exclusion bug in the panel. The delta does not move the equity-normalized result: median over n=158 vs n=160 is 0.34% in either case because the entry-equity distribution is degenerate (p25–p75 spread = 0.0005pp).

### Strategies with active exit management (bimodal loss distribution)

- **Estimator:** filter the CSV to **full-stop losses only** (losses that exited at or very near the initial SL, not at BE). Use the mean of that filtered subset as 1R.
- **Identification:** a full-stop loss is defined as `abs(loss_pct - sl_size_pct) < tolerance` where `sl_size_pct` is the configured stop in the Pine strategy and `tolerance` is a small slippage allowance (e.g., 10% of SL size).
- **Alternative estimator:** MAE-based 1R. Use maximum adverse excursion distribution of winning trades as a proxy for what "stop size" means for the strategy's actual behavior. Useful when the CSV does not cleanly label exit reason.

## Reproducibility requirement

Any future portfolio MC run must:

1. State which 1R estimator it used per strategy
2. Produce the estimator values in the run log (not just the final bust/pass numbers)
3. Reference this methodology doc

A run that does not log per-strategy 1R is not reproducible. Do not accept its numbers into portfolio decisions.

## Relationship to the April 17 decisions

The final portfolio MC on 2026-04-17 (bust 1.55%, pass 93.00%, p99 DD ~4.9%, bust attribution Aegis ~47% / Striker ~40% / Guardian ~12%) was produced using this methodology. The first-pass MC that session used median loss for all three strategies, which produced artifically favorable bust numbers on Striker and Aegis because median loss under BE/trail architecture is smaller than full-stop loss — normalization under-allocated risk, and MC understated true bust probability.

The revised MC is the accepted result. Do not revert to median-loss 1R without explicit reasoning logged in a dated decision record.

## Cross-references

- Notion: [Methodology: 1R estimation for bimodal exit distributions — 2026-04-17](https://www.notion.so/345dc0b53c1181b49e1adf485d17846c)
- Notion: [Portfolio sim 4yr — findings log — 2026-04-17](https://www.notion.so/345dc0b53c11813fb7a6c7c76384414f)
- Notion: [Claude Code brief — 1R diagnosis + Open Questions reorder + Notice phase compression — 2026-04-25](https://www.notion.so/34ddc0b53c1181199976c9b1b4effb17)
- Code: `portfolio_mc.py` (normalization layer uses per-strategy 1R)
- Code: `analysis/1r_diagnosis.py` (Guardian equity-normalized 1R recompute, reproduces the table above)
- Code: `analysis/correlated_day_check.py` (G+S+A correlated-day pressure test referenced in the Striker tail subsection)
- Code: `analysis/striker_pyramid_decomposition.py` (signal-class and trade-group decomposition that corrects the initial Striker-tail framing)
- Code: `archive/analysis/dd_protection_trace.py` (combined-account simulator that resolved the Branch (a/b/c) question for the 2025-02-07 day)
- Code: `accounts.py` and `firm_rules.py` (live-sizing model verified inline above)
- Related: ADR 2026-04-17-dd-trigger-calibration (MC outputs used this methodology)
- Related: ADR 2026-04-17-portfolio-allocations (allocation decisions used this methodology)

## Update log

- **2026-04-25** — Equity-compounding clarification added for Guardian v5.5. The previous "0.58% / 0.66%" figure was a fixed-$200K normalization artefact; equity_at_entry-normalized median is 0.3405% (= designed 0.34%). MC calibration unchanged (it consumes raw trade P&Ls). Reproducible via `analysis/1r_diagnosis.py`.
- **2026-04-25 (follow-up)** — Live-sizing Rule 0 cross-check added: `accounts.calc_multiplier` is balance-compounding at weekly resolution, equivalent to Pine's per-trade compounding to within one week of P&L drift; intra-week DD covered by `dd_protection`'s 1% trigger. Striker single-trade tail (max ~3.56% of equity at entry on 2025-02-07) and combined daily loss distribution logged as a Forward-bucket question. Reproducible via `analysis/correlated_day_check.py`. Feed citation added — this analysis ran on OANDA; canonical lock-of-record MC ran on Pepperstone.
- **2026-04-25 (second follow-up)** — Striker decomposition corrects the initial 17%-inflation framing. Initial entries +2.9% vs designed (sized correctly); pyramid layers +76.6% (against own larger equity at entry, expected for 350% pyramid sizing); 2-leg trade-groups average smaller losses than 1-leg (0.80% vs 1.03%). The 3.56% worst day is a 1-leg gap event, not a pyramid event. Forward question tagged **re-cal-trigger candidate** for surface in next MC pre-flight. Live↔backtest pyramid divergence (layer-2 backtest credits open profit, live does not) noted as first-order-only equivalence caveat. Quantization bias in `floor(balance/200K, 2dp)` documented as known sub-1% conservative sizing drag, not fixed. Reproducible via `analysis/striker_pyramid_decomposition.py`.
- **2026-04-25 (third follow-up)** — Pyramid 3.50× multiplier verified directly from raw layer-1 / layer-2 qty pairs across all 29 events (min 3.499865, max 3.501093 — spread consistent with 4dp qty rounding); implementation-drift hypothesis refuted, finding locked. Pyramid PF gap one-liner added in Forward bucket so the 6-month live reconciliation knows what to look for. dd_protection trace on 2025-02-07 resolves to **Branch (b)**: account at peak going into the day, trigger did not engage, the -3.561% Striker loss consumed 71.2% of the 5.00% daily DD budget on a single trade. Trigger fires 44.9% of trade-days across the panel — design-intentional daily cadence; cannot prevent within-day single-trade tails by construction. Reproducible via `archive/analysis/dd_protection_trace.py`.
- **2026-04-25 (fourth follow-up)** — Confirmed canonical MC metrics are net-of-rule (`portfolio_mc.py:148-150` applies `dd_protection` in-loop). Pre-staged Forward question on the category-gap fix: **within-day per-trade hard-cap** (closes by construction; cost: re-MC + potential PF drag on pyramid extensions) vs **leave-and-monitor-live** (cheaper today; gap may be decidable only from live data given n=1 panel base rate). Decision deferred; staged for next allocation review or 6-month live reconciliation, whichever fires first.
- **2026-04-25 (fifth follow-up — Q1 pre-Q gate test)** — Q1 (Guardian 1R reconciliation) re-run as the first conscious application of the unified INQHIORI ⊕ The Algorithm framework with the D-S-A pre-Q gate (Notion: [unified framework](https://www.notion.so/34ddc0b53c1181479d7bdecc61f47078); [Q1 brief](https://www.notion.so/34ddc0b53c118107a21fd7b282ef3598)). Three substantive results from this pass: (i) Pine sizing block re-read verbatim (lines 171-173, `risk = strategy.equity * (riskPerTrade / 100)`) confirms no vol-conditional, no ATR-floor, no regime-variable logic — bar-data D-test (instrument-scope #3) validated. (ii) The Pine input field's *default* is 0.30%, not the post-2026-04-23 locked 0.34%; the OANDA backtest itself ran at 0.34% (median equity-normalized 1R = 0.3417% nails the locked value), so the input was overridden at backtest time. The Pine file's `input.float(0.30, …)` and the comment-block `risk 0.30%` are post-relock-stale on the source-file side and worth a separate Pine refresh. (iii) Tail-attribution corrected: the 2× upper tail is grace-stop firing by design (graceStopMult=2.0 over the first minBarsBeforeStop=1 bar), not weekend gap / slippage — fix applied to the resolution paragraph above. Gate audit: clean. D was permitted (instrument-scope), S was unused (per-trade frame already at the right grain), A was bounded (`equity_at_close = $200K + cumulative P&L` is one column division), A.4 did not need to fire. Time on gate-step (D-test articulation + bar-data D validation in A.1) was small relative to I/N work (Pine read + CSV compute + 1R reconciliation).
