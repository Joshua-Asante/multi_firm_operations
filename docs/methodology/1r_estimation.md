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

Pine sizes positions off contemporaneous equity (`guardian_gold_v5.5.txt:192-194`):

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

**Resolution:** The 0.58% / 0.66% figure that previously sat in this doc was a fixed-$200K normalization artefact, not a sizing problem. Guardian sizes correctly at 0.34% of contemporaneous equity. Mean equity at entry across the panel was $388K (1.94× initial); final equity $865K (4.33× initial). Tight p25–p75 (0.3402–0.3407%) confirms the script hits its target risk on essentially every full-stop trade — the trace mean is fractionally above median because of a thin tail (max 0.6806%, ~2× designed) consistent with occasional weekend gap / slippage events on XAUUSD. Decomposing that tail is out of scope here; it is small, does not threaten MC calibration (`portfolio_mc.py` reads actual trade P&Ls, so realized losses including the tail are already in the simulation), and does not change any allocation or `dd_protection` constant.

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

#### Striker tail — Forward-bucket question for a future session

The 1R diagnosis above is Guardian-specific. The same panel-summary script
extended to Striker / Aegis (`analysis/correlated_day_check.py`) surfaced a
finding worth flagging — **not actioning** in this brief because
`dd_protection` constants are explicitly out-of-scope:

- Striker mean per-loss = **1.1715%** of equity at entry vs designed 1.00%
  (~17% inflation). Aegis mean per-loss = 0.4962% vs designed 1.50% (BE/partial
  exits soaking up; expected sub-1R behaviour for v4.3 architecture).
  Guardian mean per-loss = 0.3437% vs designed 0.34% (matches).
- Worst observed combined-day loss across G+S+A on the panel: **3.56%** of
  equity at entry, on 2025-02-07. Source: a single Striker trade (3.56% on one
  trade alone — ~3.5× designed; pyramid stack or gap event).
- Daily-total combined-loss distribution across 230 loss-days (4-year panel):
  p50 = 0.34%, p75 = 1.00%, p90 = 1.35%, p95 = 1.67%, p99 = 2.37%, max = 3.56%.
- **Zero 3-strategy correlated loss days** in the 4-year panel; 16 days had
  2-strategy losses (max 1.81%); the 3.56% worst day was 1-strategy.
- FXIFY daily floor is 5.00%. p99 daily combined sits 2.63 percentage points
  inside the floor; the max sits 1.44 percentage points inside. Worst day on
  this panel did not breach.

**Forward question (cheapest-falsification-first ordering):** Does Striker's
single-trade tail (max ~3.56% of equity at entry) plus a hypothetical
correlated G or A loss day produce a combined-day total within `dd_protection`'s
working envelope? Inputs: existing OANDA panel, no re-MC. Output: a single
table comparing observed correlated-day distribution against
`dd_protection`'s 1% trigger latency (the trigger fires for the *next* day,
not within-day). If the answer surfaces an envelope hole, it routes to an
**Action**-bucket dd_protection re-pressure-test under documented
re-MC trigger rules. If not, **Closed**.

This question is logged here rather than spawned as a separate workstream
because (a) it does not require new data, (b) it is not the brief's primary
ask, (c) the brief's MC calibration scope is explicitly off-limits, and (d) the
observation routing gate (`docs/methodology/observation_routing.md`) puts this
in Forward — a question gated downstream on its own logic, not pulled forward
into the current session.

Reproducible: `python analysis/correlated_day_check.py`.

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
- Code: `accounts.py` and `firm_rules.py` (live-sizing model verified inline above)
- Related: ADR 2026-04-17-dd-trigger-calibration (MC outputs used this methodology)
- Related: ADR 2026-04-17-portfolio-allocations (allocation decisions used this methodology)

## Update log

- **2026-04-25** — Equity-compounding clarification added for Guardian v5.5. The previous "0.58% / 0.66%" figure was a fixed-$200K normalization artefact; equity_at_entry-normalized median is 0.3405% (= designed 0.34%). MC calibration unchanged (it consumes raw trade P&Ls). Reproducible via `analysis/1r_diagnosis.py`.
- **2026-04-25 (follow-up)** — Live-sizing Rule 0 cross-check added: `accounts.calc_multiplier` is balance-compounding at weekly resolution, equivalent to Pine's per-trade compounding to within one week of P&L drift; intra-week DD covered by `dd_protection`'s 1% trigger. Striker single-trade tail (max ~3.56% of equity at entry on 2025-02-07) and combined daily loss distribution logged as a Forward-bucket question. Reproducible via `analysis/correlated_day_check.py`. Feed citation added — this analysis ran on OANDA; canonical lock-of-record MC ran on Pepperstone.
