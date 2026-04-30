# Prop Firm Pipeline

## Purpose

Lookup tool for Joshua's multi-firm prop trading operation. Pine Script indicators output lot sizes for a $200K baseline account. This pipeline provides a **multiplier** per account so those indicator lots scale correctly to any account size/phase.

## Architecture

* **firm_rules.py** — Firm configs, risk tiers, and baseline reference ($200K challenge). Add new firms here.
* **accounts.py** — Account dataclass, multiplier calculation, JSON persistence.
* **csv_parser.py** — DXTrade CSV trade history parser. Normalizes to standard trade format.
* **cli.py** — CLI interface: `add`, `update`, `status`, `lots`, `tearsheet` commands.
* **data/accounts.json** — Persistent account state.

## CLI Usage

```bash
python cli.py add FXIFY-200K-01 FXIFY 200000
python cli.py add 5ers-400K-01 FXIFY 400000 --phase funded
python cli.py update FXIFY-200K-01 203500
python cli.py status
python cli.py lots          # multiplier reference card for all active accounts
python cli.py tearsheet trades.csv   # quantstats HTML tearsheet from a DXTrade CSV
```

## Multiplier System

Pine Script indicators handle ATR and lot sizing for the $200K baseline. The `lots` command outputs a multiplier per account per strategy:

```
multiplier = (account_balance * account_risk_pct) / (200,000 * baseline_risk_pct)
```

Baseline risk = current locked risk (Guardian 0.34%, Striker 1.00%, Aegis 1.50%). Challenge and funded tiers are unified as of 2026-04-17; Guardian re-locked 0.30% → 0.34% on 2026-04-23 after Pepperstone-sourced panel showed available headroom. The phase field is retained for flags/DD tracking but no longer adjusts risk.

Multipliers update weekly when balances update (via `python cli.py update`), not daily. Always rounded down (never round up on risk).

## Strategy Reference (LOCKED — do not modify)

Unified allocations (locked 2026-04-17): challenge phase = funded phase. No re-sizing at pass.
Strategy versions most recently re-locked 2026-04-23 (Guardian v5.4 → v5.5, Striker v4.3 → v4.4, Aegis v4.1 → v4.3). Guardian risk re-locked 0.30% → 0.34% same day. See lock MC notes below the table.

| Strategy      | Instrument / TF | Risk/trade              | Version       | DXTrade contractValue                             |
|---------------|-----------------|-------------------------|---------------|---------------------------------------------------|
| Guardian Gold | XAUUSD 15m      | 0.34% (cold-start base) | v5.5 LOCKED   | 100                                               |
| Striker DJ30  | DJ30 15m        | 1.00%                   | v4.4 LOCKED   | **10** (critical — default of 1 gives ~7% risk)   |
| Aegis USDJPY  | USDJPY 15m      | 1.50%                   | v4.3 LOCKED   | default (1)                                       |

2026-04-23 lock MC anchors:
* Alchemy reference (2026-04-20, Striker v4.4 + Aegis v4.2 era — pre-2026-04-23 lock): **99.21% pass / 0.03% bust**.
* Pepperstone directional (2026-04-23, all three at candidate versions, 10K × 3 seeds): **88.45% pass / 4.68% bust** raw; **84.37% pass / 1.03% bust** after correcting Aegis 1R for the n=1 full-stop thin-cohort artifact (median fallback inflates Aegis scale 4.4×). Bust gate passes under corrected 1R; pass-rate gap vs Alchemy attributed to feed-level drag + v5.5 added filters (blockMonH08, blockMonH09, blockH12 all-days, blockH12Day latch). Locked under brief-authorized directional read, not anchor-grade MC. Re-MC with v5.4 Pepperstone pending (would isolate feed effect from version effect).
* Post-Guardian-risk-relock MC (G 0.34% / S 1.00% / A 1.50%, same panel): **92.73% pass / 0.65% bust / 6.62% timeout**, p99 DD 4.94%. Lock criteria: bust <1%, p99 DD <5%. Current 04-26 Pepperstone panel (the one committed to the repo) reproduces **93.78% pass / 0.58% bust / 4.92% p99 DD** under `python portfolio_mc.py --panel pepperstone` — drift within lock criteria, no re-MC triggered. `tests/test_mc_anchors.py` pins 93.78/0.58/4.92 as the code-reproducible anchor; 92.73/0.65/4.94 retained here as the 04-23 lock-decision artifact. **Bust-attribution split** also drifted: 04-23 ADR cites A 27.6% / S 39.3% / G 33.2%; 04-26 Pepperstone reproduces A 25.1% / S 43.4% / G 31.4% — Striker still the marginal contributor, ranking S > G > A preserved. Full breakdown pending in `docs/briefs/bust_attribution_flip.md`. See Protection section below.

No active overlays. Guardian runs at its locked base risk. The Iran-Israel /
Hormuz conflict overlay was deactivated 2026-04-23 after revert triggers met;
`docs/overlays/guardian_conflict_risk.md` retains the historical record.

Strategy parameters (SL/TP/ATR/hour-blocks/session/BE/trail/pyramid/etc.) live in Pine Script
and are NOT duplicated here. See Key Principle.

Source of truth: https://www.notion.so/346dc0b53c1181d1b8d5e12df4bd3810

## Protection (single-tier, production-locked 2026-04-17; revalidated 2026-04-23)

Single rule in `dd_protection.py`. `portfolio_mc` validates.

* **DD tier**: if `(equity - peak) / peak <= -0.010`, multiply day's sizing by 0.40×.
* Clears automatically when equity returns to peak.
* MC at current config (G 0.34% / S 1.00% / A 1.50%, Pepperstone 2022→2026, 223 week-blocks, 10K × 3 seeds):
  **92.73% pass / 0.65% bust (0.00% daily + 0.65% static) / 6.62% timeout**, p99 DD 4.94%, median days-to-pass 32.
* The prior equity tier was deleted on 2026-04-17 after it was proven to be dead code under the live `min()` combining semantics. Revert triggers for reintroducing a second tier are documented in the FINAL decision page.
* Constants frozen — do not change without re-running `portfolio_mc`.

FINAL decision: https://www.notion.so/346dc0b53c11816085bbf2292be934cc

## Firm Expansion

To add a firm: define its rules in firm_rules.py as config. Everything downstream adapts automatically.

## Methodology references

* **Rule 0 — audit-first** (only methodology rule that survived the 2026-04-29 archive; cross-phase track record 2026-04-17 / 2026-04-27): [`docs/rule_0.md`](docs/rule_0.md). Read production code first when authoring decision briefs or implementation steps touching risk controls.
* **The Algorithm** (default problem-solving framework — Question / Delete / Simplify / Accelerate / Automate, strict order): https://www.notion.so/34ddc0b53c11811eb6a0d9192b63d252 (permanent reference page).
* **Observation routing** (three-bucket gate Closed / Action / Forward, replaces the prior Notice/Inquire framework): [`docs/methodology/observation_routing.md`](docs/methodology/observation_routing.md).
* **1R estimation** (per-strategy 1R, equity-compounding normalization for Guardian-style equity-sized strategies): [`docs/methodology/1r_estimation.md`](docs/methodology/1r_estimation.md).
* **Operational rules** (incl. doc/code skew audit trigger): [`docs/operational_rules.md`](docs/operational_rules.md).
* **Strategy-research-phase methodology archive** (INQHIORI ⊕ The Algorithm framework, Pre-Q gates, Case B audits, MVD framing — all retired 2026-04-29; 90-day review gate 2026-07-29): [`docs/methodology/archive/README.md`](docs/methodology/archive/README.md).

## Key Principle

The portfolio and strategies are LOCKED. This pipeline manages the *operational layer* — it never touches strategy parameters.
