# Methodology: 1R estimation for bimodal exit distributions

**Date established:** 2026-04-17
**Status:** Active — applies to any portfolio MC run that normalizes CSV backtest P&L to target risk allocations.

## Why this matters

Portfolio Monte Carlo (`portfolio_mc.py`) takes CSV backtest output from each strategy and normalizes P&L to a target risk allocation (e.g., scale Guardian's 0.55% backtest trades to 0.30% challenge allocation). The normalization requires a 1R estimator — the typical loss size in backtest-dollar terms — so that target allocation can be expressed as a simple multiplier on normalized P&L.

**If the 1R estimator is wrong, every MC number downstream is wrong.** Bust rate, pass rate, DD distribution, bust attribution — all distorted by the normalization error.

## The problem

Strategies with active exit management (breakeven, trailing stop, partial exits) produce **bimodal loss distributions**:
- **Full-stop losses:** trades that move against entry immediately and hit the initial SL. These are "1R" in the conventional sense.
- **BE-stopped or partial-stopped losses:** trades that moved favorably, triggered BE or a partial take, then retraced to close at BE or small profit/loss. These are typically much smaller losses than full-stops — or even small wins misclassified as "losses" if the trade exited at BE minus spread.

Using median loss as the 1R estimator conflates these two modes. The median of a bimodal distribution is a meaningless statistic for the purpose of sizing normalization — it depends on the ratio of the two modes, which varies across backtest windows and regimes.

## The correction

Apply per-strategy 1R estimation based on the strategy's exit architecture:

### Strategies with no exit management (unimodal loss distribution)

**Guardian v5.1** is the current example. No BE, no trail, no MFE-BE. All losses are full-stops. The loss distribution is unimodal and roughly symmetric around the mean stop size.

- **Estimator:** median loss is acceptable (mean ≈ median for unimodal symmetric).
- **Guardian v5.1 observed:** full-stop mean ≈ median ≈ 1.37% of account equity at backtest risk setting.
- **Implementation:** `median(abs(loss_pnl))` where `loss_pnl` is filtered to loss trades only.

### Strategies with active exit management (bimodal loss distribution)

**Striker v4.3** and **Aegis v4.1** both have BE and/or trail logic. The loss distribution has two modes.

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
- Code: `portfolio_mc.py` (normalization layer uses per-strategy 1R)
- Related: ADR 2026-04-17-dd-trigger-calibration (MC outputs used this methodology)
- Related: ADR 2026-04-17-portfolio-allocations (allocation decisions used this methodology)
