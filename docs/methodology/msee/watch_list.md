# MSEE — Watch list (Part VII operationalization)

**Established:** 2026-04-27
**Cadence:** Weekly (aligned with `cli.py update` weekly multiplier cycle).
**Generator:** [`scripts/msee_watchlist.py`](../../../scripts/msee_watchlist.py)
**Output:** `analysis/msee/watch_{date}.md` (most recent retained).
**Source:** Part VII of the MSEE source report + load-bearing observations from Phases 1–7.

## Indicator catalog

Indicators are grouped by load-bearing concern. Each has a current value (filled in by the weekly digest), a threshold, and a routing action when the threshold is crossed.

### Portfolio-level (highest priority)

| Indicator | Threshold | Routing on crossing |
|-----------|-----------|---------------------|
| **Joint-loss day count (any 3-strategy day with all R<0)** | First occurrence in panel ≥ 1 → auto-Forward regime-shift Q | Open Q-MSEE-portfolio.1; do NOT auto-Action; live-PnL-gap rule must fire separately |
| **G/A stress-conditional correlation** | Rises above +0.30 (point estimate) on a sliding 6-month stress slice | Open Q-MSEE-6c.1 follow-up; Pepperstone re-fit prerequisite for Action |
| **Portfolio realized max DD (current quarter)** | > 4.0% | Soft-warn; review next planned `cli.py update` window |
| **Portfolio realized max DD (current quarter)** | > 4.5% | Hard-warn; escalate to re-MC trigger evaluation under operational-rules.md |

### Guardian Gold v5.5

| Indicator | Threshold | Routing |
|-----------|-----------|---------|
| Realized max DD (rolling 6-month) on Guardian-only portfolio at locked 0.34% | > 4.6% (current panel max) | Investigate; no Action |
| Realized max DD on Guardian-only at locked 0.34% | > 4.8% | Hard-warn; only ~0.2pp from 5% ruin |
| Mean R-of-winners (rolling 50-trade) | Drops by > 25% from H10 baseline | Capacity-erosion (prey-shrink) signal |
| Trade rate per month (count) | Drops by > 30% from 4yr median | Niche contraction signal |

### Striker DJ30 v4.4

| Indicator | Threshold | Routing |
|-----------|-----------|---------|
| Win rate (rolling 50-trade) | Drops below 0.60 (from current ~0.66 in rolling window) | Density-rise senescence signal |
| Pyramid-leg P&L decomposition (when computed) | Leg 2/3 contribution as fraction of total drops > 30% | Herd-thinning signal (load-bearing per source report Part V.5.2) |
| Long negative-Sharpe segment (changepoint H5) | New segment > 90d with mean Sharpe < −1 | Recurrence of Dec-2022→Sep-2023 episode |

### Aegis-Reversion v4.3

| Indicator | Threshold | Routing |
|-----------|-----------|---------|
| Win rate (rolling 50-trade) | Drops below 0.34 (from current ~0.36 trend) | Density-rise continuation; reach extinction-rescue precedent |
| USDJPY 15m Hurst exponent (rolling 90d) | Persistently > 0.55 | Niche destruction (mean-reversion regime shift toward trending) |
| BOJ policy-decision events | Major policy change (rate hike, YCC removal) | Punctuated-equilibrium event for JPY mean-reversion structure |

### Regime under-sampling (information-value indicator)

| Indicator | Threshold | Routing |
|-----------|-----------|---------|
| Cluster 2 (XAU crash / risk-off) day count this quarter | ≥ 1 day | Most informative new data — log for next H2/H6 re-run |
| Stress-slice (top-5% |max-index-move|) day count this quarter | ≥ 5 days | Refresh H6c stress correlations |

## Threshold derivation

- **Joint-loss day = 1**: Under independence of ~5% per-strategy loss-day rates, joint probability ~0.0125%. A single occurrence rejects independence at p < 0.0001 — high-confidence regime signature even on small n.
- **G/A stress correlation > 0.30**: This is the same threshold used by the H6c auto-Forward trigger. Justified by ecological literature (limiting-similarity penalty kicks in above 0.30 cross-correlation in niche overlap).
- **Guardian DD > 4.6%**: Current panel realized max from H6 condition (3). Crossing this means the strategy is exceeding its 4yr panel envelope.
- **Striker WR < 0.60**: Per CLAUDE.md headline "WR 71.18%" and source report Part V.5.2 ("herd-amplification signature; if the herd thins, win rate falls toward 50%"). The 0.60 threshold is halfway to 50%.
- **Aegis Hurst > 0.55 persistently**: Source report Part V.5.3 ("if it drifts above 0.55 persistent, the niche is shrinking").

## Routing discipline (hard rule)

**No watch-list crossing alone is an Action trigger.** Every crossing routes to:

1. Closed (with one-paragraph archive note in `findings/`) if the trigger is a stale or already-known condition.
2. Forward (open a new `Q-MSEE-watch.N` question) for the cheapest follow-up falsification.
3. Action only if Rule 0 / overlay-discipline live-PnL gap / a documented re-MC trigger ALSO fires.

## Cross-references

- `framework.md` — operational synthesis
- `open_questions.md` — Forward question registry
- `findings/` — dated routing memos (Phase 1–7 results live here)
- `observation_routing.md` (parent methodology) — three-bucket gate
