# Prop Firm Pipeline

## Purpose

Lookup tool for Joshua's multi-firm prop trading operation. Pine Script indicators output lot sizes for a $200K baseline account. This pipeline provides a **multiplier** per account so those indicator lots scale correctly to any account size/phase.

## Architecture

* **firm_rules.py** — Firm configs, risk tiers, and baseline reference ($200K challenge). Add new firms here.
* **accounts.py** — Account dataclass, multiplier calculation, JSON persistence.
* **csv_parser.py** — DXTrade CSV trade history parser. Normalizes to standard trade format.
* **cli.py** — CLI interface: `add`, `update`, `status`, `lots` commands.
* **data/accounts.json** — Persistent account state.

## CLI Usage

```bash
python cli.py add FXIFY-200K-01 FXIFY 200000
python cli.py add 5ers-400K-01 FXIFY 400000 --phase funded
python cli.py update FXIFY-200K-01 203500
python cli.py status
python cli.py lots          # multiplier reference card for all active accounts
```

## Multiplier System

Pine Script indicators handle ATR and lot sizing for the $200K baseline. The `lots` command outputs a multiplier per account per strategy:

```
multiplier = (account_balance * account_risk_pct) / (200,000 * baseline_risk_pct)
```

Baseline risk = current locked risk (Guardian 0.30%, Striker 1.00%, Aegis 1.50%). Challenge and funded tiers are unified as of 2026-04-17; the phase field is retained for flags/DD tracking but no longer adjusts risk.

Multipliers update weekly when balances update (via `python cli.py update`), not daily. Always rounded down (never round up on risk).

## Strategy Reference (LOCKED 2026-04-17 — do not modify)

Unified allocations: challenge phase = funded phase. No re-sizing at pass.

| Strategy      | Instrument / TF | Risk/trade              | Version       | DXTrade contractValue                             |
|---------------|-----------------|-------------------------|---------------|---------------------------------------------------|
| Guardian Gold | XAUUSD 15m      | 0.30% (cold-start base) | v5.1 LOCKED   | 100                                               |
| Striker DJ30  | DJ30 15m        | 1.00%                   | v4.3 LOCKED   | **10** (critical — default of 1 gives ~7% risk)   |
| Aegis USDJPY  | USDJPY 15m      | 1.50%                   | v4.1 LOCKED   | default (1)                                       |

Guardian conflict overlay: currently running at 0.25% (not 0.30%) due to Iran-Israel / Hormuz regime.
This is a live override, NOT a parameter change. Base stays 0.30% in config; overlay is applied via
`portfolio_mc --guardian-risk 0.0025`. Revert triggers (both, sustained 5 sessions): GVZ sub-25 AND
Hormuz transit > 50% baseline.

Strategy parameters (SL/TP/ATR/hour-blocks/session/BE/trail/pyramid/etc.) live in Pine Script
and are NOT duplicated here. See Key Principle.

Source of truth: https://www.notion.so/346dc0b53c1181d1b8d5e12df4bd3810

## Protection (single-tier, production-locked 2026-04-17)

Single rule in `dd_protection.py`. `portfolio_mc` validates.

* **DD tier**: if `(equity - peak) / peak <= -0.010`, multiply day's sizing by 0.40×.
* Clears automatically when equity returns to peak.
* MC at this config: **93.00% pass / 1.55% bust / ~5.45% timeout** (10K sims × 3 seeds).
* The prior equity tier was deleted on 2026-04-17 after it was proven to be dead code under the live `min()` combining semantics. Revert triggers for reintroducing a second tier are documented in the FINAL decision page.
* Constants frozen — do not change without re-running `portfolio_mc`.

FINAL decision: https://www.notion.so/346dc0b53c11816085bbf2292be934cc

## Firm Expansion

To add a firm: define its rules in firm_rules.py as config. Everything downstream adapts automatically.

## Key Principle

The portfolio and strategies are LOCKED. This pipeline manages the *operational layer* — it never touches strategy parameters.
