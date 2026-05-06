# Q-DDP-1 Pre-A — Drag re-baseline under production semantics

**Date:** 2026-05-06
**Author:** Claude Code (auto mode)
**Gate purpose:** confirm whether realized drag of C0 vs no-protection on the locked Pepperstone panel under production's release semantics still motivates the Pareto question.

## Production semantics (the model the harness actually uses)

From [portfolio_mc.py:195-219](../../../portfolio_mc.py:195) `_simulate_path`:

- Per-day evaluation
- Trigger condition: `dd_from_peak <= -dd_trigger`, with `dd_from_peak = (eq - peak) / peak`
- Multiplier on day's PnL: `scale = dd_scale if active else 1.0`; applied as `strat_pnls = path[day] * scale`
- Peak update: `if eq > peak: peak = eq` (running maximum)
- **Release** is implicit: scale returns to 1.0 the moment `dd_from_peak > -dd_trigger`, i.e. equity recovers to within DD_TRIGGER of peak (≈$2,000 short of peak at $200K base, NOT all the way back to peak).

This contradicts the brief's chat-based prose which described "≥peak release". The chat-based prose is wrong; production releases on a much lower bar.

## Walk: 28-month sub-window 2024-01-01 → 2026-04-20 (601 bdays, n=424 trades)

Sub-window matches the brief's chat-based forward-walk window exactly (n=424 trades reconciles to brief context).

| Metric | Unprotected | C0 (1.0% / 0.40×) |
|---|---:|---:|
| Terminal equity | $716,172 | $590,159 |
| Cumulative PnL | +$516,172 | +$390,159 |
| Engagement-window starts | 0 (sanity) | 17 |
| Active days | 0 | 207 / 601 (34.4%) |

## Drag (production semantics, 28mo)

- **Terminal-equity drag (C0 − unprotected): −$126,013**
- **As percentage of unprotected PnL: −24.4%**

## Comparison with chat-based forward-walk

| Quantity | Chat-based | Production walk | Delta |
|---|---:|---:|---|
| Drag ($) | −$149,277 | −$126,013 | chat overstates by $23.3K (18%) |
| Drag (% of unprotected PnL) | 24% | 24.4% | essentially identical |
| Engagement windows | 14 | 17 | counting heuristic differs |
| Active fraction | 52% calendar days | 34.4% bdays (≈25% cal days) | chat overstates engagement ~2× |

## Interpretation

- **Drag percentage matches almost exactly** (24% vs 24.4%) despite the chat-based prose mis-describing the release condition. The "24% of unprotected profits" framing in the brief Context survives unchanged under production semantics.
- **Drag dollar amount is 18% smaller** under production semantics (−$126K vs −$149K). Material reduction but the order of magnitude survives.
- **Engagement characterization in chat-based prose was wrong** — 52% of calendar days assumed long ≥peak release windows. Production release on partial recovery roughly halves the active-day count to 34.4% of bdays (≈25% of calendar days). The window count went up (17 vs 14) because production releases more often, creating more (shorter) windows.

## Recommendation: **PROCEED to Pre-B**

The corrected drag (−$126K, 24.4% of unprotected PnL over 28 months) remains material — well above the ≥10% materiality threshold suggested in the plan. The Inquire-phase question (does 4-strategy diversification permit a Pareto-dominant relaxation?) retains its legitimate motivation.

**Caveats carried forward into the sweep:**

1. The chat-based engagement-window narrative ("14 windows / 52% of calendar days") is wrong and should not be cited in any downstream document. Production-walk numbers (17 windows / 34.4% of bdays) are authoritative.
2. The MC sweep itself (Steps 2-3) is internally consistent with production semantics regardless of this re-baseline — the harness uses the same `_simulate_path` code. The re-baseline only affects how the Inquire-phase **trigger** is described, not the sweep mechanics.
3. The drag-savings-floor criterion (10% reduction vs C0) in the brief's Acceptance section still applies, anchored to the production-walk C0 drag of $126K (not the chat-based $149K).

## Reproducibility

```python
from portfolio_mc import _load_all, ALLOCATIONS, STARTING_EQUITY
from dd_protection import DD_TRIGGER, DD_SCALE
import pandas as pd

trades_by_strat, panel, blocks, scale_info, panel_strats = _load_all(
    ALLOCATIONS, panel_name='pepperstone'
)
sub = panel.loc[panel.index >= pd.Timestamp('2024-01-01')]
path = sub.values

def walk(path, dd_trigger, dd_scale):
    eq = peak = float(STARTING_EQUITY)
    for day in range(len(path)):
        dd_from_peak = (eq - peak) / peak if peak > 0 else 0.0
        scale = dd_scale if dd_from_peak <= -dd_trigger else 1.0
        eq += float((path[day] * scale).sum())
        if eq > peak:
            peak = eq
    return eq

print(walk(path, DD_TRIGGER, DD_SCALE) - walk(path, 10.0, 1.0))
# -> -126013.36
```
