# multi_firm_operations

Operational layer for Joshua's multi-firm prop trading. Account tracking,
multiplier lookup, DD protection, and portfolio-level challenge MC.

## Source of truth

This repo is the source of truth for locked parameters, risk controls, and
methodology. Notion is the operational and presentation surface (lock-decision
narratives, broker matrix, procedures). Per Rule 0 ([`docs/rule_0.md`](docs/rule_0.md)),
when prior docs or Notion pages disagree with the code, the code wins — flag
the skew and resync.

Start here:

- [`REPO_MAP.md`](REPO_MAP.md) — file tree with `[A]/[U]/[X]/[?]` classification
- [`CLAUDE.md`](CLAUDE.md) — architecture, CLI usage, Strategy Reference table,
  Protection spec, and the Key Principle (Pine Script is source of truth for
  strategy parameters)
- [`docs/adr/`](docs/adr/) — immutable architecture decision records
- [`docs/briefs/`](docs/briefs/) — open + closed decision briefs

Notion (operational, downstream of the repo):

- [Multi-Firm Operations Command Center](https://www.notion.so/32cdc0b53c1181b8a18cce1401a4f8e8)
- [📊 Portfolio MC Lock Details](https://www.notion.so/35cdc0b53c11813e82fdf5f09f36a459)
- [🔒 Strategy Lock Reference](https://www.notion.so/35cdc0b53c1181f2be51c8a8f0078046) — full Pine parameters (Pine source itself is private)
- [🏦 Per-Firm Broker Matrix](https://www.notion.so/35cdc0b53c11814d8985d778a92b640f) — DXTrade `contractValue` per instrument
- [📋 Operating Procedures](https://www.notion.so/35cdc0b53c11812dbdd1e84b7e37693f)

## Locked portfolio

Four strategies, all locked. Risk percentages and lock dates are the
canonical Pine-anchored values.

| Strategy        | Version | Risk  | Instrument   | Lock date  |
|-----------------|---------|-------|--------------|------------|
| Guardian Gold   | v5.5    | 0.34% | XAUUSD 15m   | 2026-04-23 |
| Striker DJ30    | v4.5    | 1.00% | DJ30 15m     | 2026-05-05 |
| Aegis-Reversion | v4.3    | 1.50% | USDJPY 15m   | 2026-04-22 |
| Striker NAS100  | v1      | 0.40% | NAS100 15m   | 2026-05-05 |

DD protection: **single-tier, 1.5% / 0.40×** — C2 relock 2026-05-08, see
[`docs/adr/2026-05-08-dd-trigger-c2-relock.md`](docs/adr/2026-05-08-dd-trigger-c2-relock.md).
Pepperstone MC anchor: **98.78 / 0.12 / 4.17** (pass / bust / p99 DD) on the
2026-05-14 allocation refresh, pinned by `tests/test_mc_anchors.py`. Bust
attribution: guardian 34.3% / aegis 28.6% / striker 25.7% / NAS 11.4%. Prior
2026-05-14 panel-refresh-only anchor (98.65 / 0.25 / 4.69 at DJ30 1.00%/pyr 350%,
NAS 0.40%) and 2026-05-08 C2 anchor (98.09 / 0.36 / 4.73) preserved in CLAUDE.md
"Prior anchors (historical)". The allocation refresh override of the
regime-robustness gate is documented in `docs/adr/2026-05-14-allocation-refresh.md`.
Revert trigger: rolling 6-month MC pass-rate < 95% across two consecutive windows
→ revert to C0 dd_protection / pre-refresh allocations; quarterly check via
`python analysis/time_to_pass.py --regime-check`.

## Portfolio MC

    python portfolio_mc.py                          # default run at locked allocations (Pepperstone)
    python portfolio_mc.py --historical             # deterministic backtest
    python portfolio_mc.py --sensitivity            # DD-tier grid
    python portfolio_mc.py --panel oanda            # pattern-spotting proxy panel
    python portfolio_mc.py --guardian-risk 0.0025   # what-if at reduced Guardian risk

TradingView exports live under `data/tv_exports/{pepperstone,oanda}/` with the
canonical filename
`<Strategy>_<Instrument>_<Version>_<Broker>_<Symbol>_<YYYY-MM-DD>_<hash>.csv`
(MVD identity gate in `portfolio_mc.py` enforces the seven-field shape).
The Pepperstone subdir is the lock-anchor source; OANDA is the proxy.

## Public-clone note

This repo's pipeline depends on two classes of files that are **not committed**:

- **Vendor-licensed data** — TradingView strategy-tester exports in `data/tv_exports/`,
  broker bar feeds in `data/bar_data/`, and reference series in `data/external/`.
  Pepperstone and OANDA terms permit personal export but not public redistribution.
  Per-directory `SHA256SUMS` manifests are tracked so any locally-acquired copy
  can be integrity-verified.
- **Pine strategy source** — `**/*.pine` files are held privately to protect the
  live trading edge. Per-file hashes pinned in
  [`strategies/MANIFEST.sha256`](strategies/MANIFEST.sha256).

Tests that depend on vendor data (`test_mc_anchors.py`, `test_tv_export_loader.py`)
skip cleanly when the CSVs are absent. The Python pipeline runs end-to-end as soon
as a valid `data/tv_exports/pepperstone/` is dropped in.
