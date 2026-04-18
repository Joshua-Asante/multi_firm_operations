# FXIFY Portfolio Optimization Suite

## Purpose
Surgical refinement of a 3-strategy algorithmic portfolio (Guardian Gold / Striker DJ30 / Aegis-Reversion USDJPY) for maximizing FXIFY $200K challenge pass probability.

**Current baseline:** 97.9% pass rate, 14 median days, 3.56% max DD (10K Monte Carlo sims).

## Project Structure

```
fxify_analysis/
├── config.py                          # Strategy params, challenge rules, risk allocations
├── master_analysis.py                 # Data loader, shared utilities, validation framework
├── 01_challenge_equity_optimization.py # Adaptive risk scaling near target/DD limits
├── 02_losing_trade_patterns.py        # Multi-dimensional loser clustering
├── 03_cross_strategy_drawdown.py      # Tail correlation & conditional DD analysis
├── 04_exit_optimization.py            # TP/SL/trail/time-exit sweep
├── 05_session_time_filters.py         # Session window P&L decomposition
└── data/                              # Place backtest CSVs here
    ├── guardian_gold_v37.csv
    ├── striker_dj30_v41.csv
    └── aegis_reversion_v4.csv
```

## Setup

```bash
pip install pandas numpy matplotlib seaborn scipy scikit-learn
```

## CSV Format Expected
TradingView strategy tester export with columns:
- Trade #, Type, Signal, Date/Time, Price, Contracts, Profit, Cum. Profit, Run-up, Drawdown

If your CSVs have different column names, update the `COLUMN_MAP` in `config.py`.

## Claude Code Usage

Point Claude Code at this directory and ask it to:
1. Run `master_analysis.py` first to validate data loads correctly
2. Run individual modules (01-05) for specific analyses
3. Iterate on findings — each module prints actionable recommendations

### Key constraint to enforce with Claude Code:
**All proposed changes must be validated out-of-sample.** Train on 2021-2023, validate on 2024-2025. Any filter that doesn't hold OOS is curve-fitting.

### What NOT to change:
- Entry signals (locked and battle-tested)
- Core indicator parameters
- Strategy logic architecture
- Never add complexity (new indicators, ML models for entries)

### What CAN be refined:
- Risk allocation per strategy (within challenge DD budget)
- Session/time filters (removing provably bad windows)
- Exit management (partials, trails, time-based closes)
- Adaptive risk near challenge milestones
- Filtering losers that share identifiable non-edge patterns
