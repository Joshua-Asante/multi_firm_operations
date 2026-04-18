# prop_firm_pipeline

Operational layer for Joshua's multi-firm prop trading. Account tracking,
multiplier lookup, DD protection, and portfolio-level challenge MC.

## Parameter source of truth

All locked parameters (risk%, versions, contractValue, protection constants)
are authoritative in Notion, not in this repo:

* Main brief: https://www.notion.so/346dc0b53c1181d1b8d5e12df4bd3810
* Protection FINAL decision (single-tier, DD 1.0%/0.40×):
  https://www.notion.so/346dc0b53c11816085bbf2292be934cc

If the code and Notion disagree, Notion is right and the code is stale —
open an issue and resync via the brief's Phase 2 procedure.

## Quick reference

See [CLAUDE.md](CLAUDE.md) for architecture, CLI usage, the Strategy
Reference table, the Protection spec, and the Key Principle about
Pine Script being the source of truth for strategy parameters.

## Portfolio MC

```bash
python -m prop_firm_pipeline.portfolio_mc                 # default two-tier run
python -m prop_firm_pipeline.portfolio_mc --historical    # deterministic backtest
python -m prop_firm_pipeline.portfolio_mc --sensitivity   # DD-tier grid
python -m prop_firm_pipeline.portfolio_mc --guardian-risk 0.0025   # overlay sim
```

TradingView exports belong at `data/tv_exports/{guardian,striker,aegis}.csv`.
