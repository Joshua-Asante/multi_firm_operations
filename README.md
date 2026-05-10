# multi_firm_operations

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
python portfolio_mc.py                 # default run at locked allocations (Pepperstone)
python portfolio_mc.py --historical    # deterministic backtest
python portfolio_mc.py --sensitivity   # DD-tier grid
python portfolio_mc.py --panel oanda   # pattern-spotting proxy panel
python portfolio_mc.py --guardian-risk 0.0025   # what-if at reduced Guardian risk
```

TradingView exports live under `data/tv_exports/{pepperstone,oanda}/` with the
canonical filename `<Strategy>_<Instrument>_<Version>_<Broker>_<Symbol>_<YYYY-MM-DD>_<hash>.csv`
(MVD identity gate in `portfolio_mc.py` enforces the seven-field shape). The
Pepperstone subdir is the lock-anchor source; OANDA is the proxy.

## Public-clone note

This repo's pipeline depends on two classes of files that are **not committed**:

* **Vendor-licensed data** — TradingView strategy-tester exports in `data/tv_exports/`,
  broker bar feeds in `data/bar_data/`, and reference series in `data/external/`.
  Pepperstone and OANDA terms permit personal export but not public redistribution.
  Per-directory `SHA256SUMS` manifests are tracked so any locally-acquired copy
  can be integrity-verified.
* **Pine strategy source** — `**/*.pine` files are held privately to protect the
  live trading edge. Per-file hashes pinned in [strategies/MANIFEST.sha256](strategies/MANIFEST.sha256).

Tests that depend on vendor data (`test_mc_anchors.py`, `test_tv_export_loader.py`)
skip cleanly when the CSVs are absent. The Python pipeline runs end-to-end as soon
as a valid `data/tv_exports/pepperstone/` is dropped in.
