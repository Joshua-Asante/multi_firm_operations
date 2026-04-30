# MSEE H1–H10 individual hypothesis outputs — archived

The individual H1–H10 hypothesis runs concluded in their respective findings docs at `docs/methodology/msee/findings/2026-04-27_phase*.md`. None routed Action. The live MSEE component is the **watchlist** (`scripts/msee_watchlist.py` + `analysis/msee/watch_*.{md,json}`), which reads `analysis/msee/daily_strategy_returns.csv` only and does not depend on any of these archived outputs.

Restore from git history if a future watchlist crossing needs one of these as substrate; do not re-run blindly without re-reading the methodology context.

## Files archived 2026-04-28

`h1_community_matrix.*`, `h2_daily_clusters.csv`, `h2_regime_clusters.*`, `h3_geometric_uplift.*`, `h4_alpha_decay.*` + `h4_alpha_decay_rolling.csv`, `h5_changepoint.*` + `h5_rolling_sharpe.csv`, `h6_storage_conditions.*`, `h6c_conditional_correlations.*`, `h7_regime_forecast.*`, `h8_invasion_fitness.*`, `h9_capacity.py` + `h9_capacity_audit.json`, `h10_senescence.*` + `h10_senescence_rolling.csv`.

## Live (not archived)

`daily_strategy_returns.{py,csv,json}` — substrate for the watchlist.
`watch_*.{md,json}` — dated watchlist digests.
