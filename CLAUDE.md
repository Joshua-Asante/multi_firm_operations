# Multi-Firm Operations

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
Most recent version locks: Guardian v5.5 (2026-04-23), Aegis v4.3 (2026-04-23), Striker DJ30 **v4.4 → v4.5** (2026-05-05), Striker NAS100 **v1** (locked 2026-05-05; operational integration 2026-05-07 after DXTrade contractValue=10 broker-verified). v4.4 archived to `archive/strategies/striker/`. See lock MC notes below the table.

| Strategy        | Instrument / TF | Risk/trade              | Version       | DXTrade contractValue                             |
|-----------------|-----------------|-------------------------|---------------|---------------------------------------------------|
| Guardian Gold   | XAUUSD 15m      | 0.34% (cold-start base) | v5.5 LOCKED   | 100                                               |
| Striker DJ30    | DJ30 15m        | 1.00%                   | v4.5 LOCKED   | **10** (critical — default of 1 gives ~7% risk)   |
| Aegis USDJPY    | USDJPY 15m      | 1.50%                   | v4.3 LOCKED   | default (1)                                       |
| Striker NAS100  | NAS100 15m      | 0.40%                   | v1 LOCKED     | 10                                                |

Operational tooling scope: `firm_rules.py`, `dd_protection.py`, `accounts.py`, and `cli.py lots` cover all four strategies (NAS100 added 2026-05-07 after DXTrade contractValue=10 broker-verified). `portfolio_mc.py` already covered NAS100 from the 2026-05-05 lock anchor.

2026-05-08 lock MC anchor (4-strategy + dd_protection C2, current canonical):
* Pepperstone 4-strategy (G 0.34% / DJ30 v4.5 1.00% / A 1.50% / NAS v1 0.40%, dd_protection 1.5%/0.40×, 10K × 3 seeds): **98.09% pass / 0.36% bust (0.00% daily + 0.36% static) / 1.55% timeout**, p99 DD 4.73%, median days-to-pass 22. **Bust attribution**: striker 44.4% / aegis 24.1% / guardian 21.3% / NAS 10.2%. NAS remains the lowest contributor consistent with the diversification thesis. Reproducible under `python portfolio_mc.py --panel pepperstone`. `tests/test_mc_anchors.py` pins these. Lock criteria (bust <1%, p99 DD <5%) — both pass with margin. Relocked 2026-05-08 from prior C0 (1.0%/0.40×) anchor 97.88/0.22/4.55 after `bust_attribution_flip` closed broker-feed-confirmed via same-date Pepperstone+OANDA TV re-export and Q-DDP-1 C2 was adopted (median days-to-pass 23 → 22; risk controls met). See `docs/briefs/Q-DDP-1/recommendation.md` override note + `docs/briefs/bust_attribution_flip.md` closure.
* OANDA pattern-spotting proxy at C2 (3-strategy, DJ30 still v4.4): **96.23% pass / 0.69% bust / p99 DD 4.91%**, median days-to-pass 25. Both lock criteria clear with thinner margin than Pepperstone, consistent with OANDA's pattern-spotting role. Reproducible under `python portfolio_mc.py --panel oanda`.

Prior anchors (historical):
* 2026-05-05 4-strategy at C0 (1.0%/0.40×): **97.88% pass / 0.22% bust / 4.55% p99 DD**, median days-to-pass 23. Bust attribution: DJ30 40.9% / G 25.8% / A 22.7% / NAS 10.6%. Re-anchored same day after Guardian Pepperstone re-export (87e73 → 33781, 209 → 201 trades; 04-26 export contained 8 phantom v5.5 signals — see `data/reconciles/2026-05-05_guardian_n_reconcile.md`). See `docs/briefs/striker_nas100_q_nas_3_mc_addition.md` for the addition decision audit.
* 2026-04-23 lock cohort (G 0.34% / S v4.4 1.00% / A v4.3 1.50%, Pepperstone 04-26 panel, C0): **93.78% pass / 0.58% bust / 4.92% p99 DD** — code-reproducible against pre-2026-05-05 portfolio_mc.py + v4.4 panel. Bust attribution at that lock: A 25.1% / S 43.4% / G 31.4%. The 2026-04-23 in-flight lock-decision used 92.73% pass / 0.65% bust / 4.94% p99 DD against an in-flight panel that was not committed.
* Alchemy reference (2026-04-20, Striker v4.4 + Aegis v4.2 era — pre-2026-04-23 lock): **99.21% pass / 0.03% bust**.

No active overlays. Guardian runs at its locked base risk. The Iran-Israel /
Hormuz conflict overlay was deactivated 2026-04-23 after revert triggers met;
`archive/docs/methodology/archive/overlays/guardian_conflict_risk.md` retains the historical record.

Strategy parameters (SL/TP/ATR/hour-blocks/session/BE/trail/pyramid/etc.) live in Pine Script
and are NOT duplicated here. See Key Principle.

Source of truth: https://www.notion.so/346dc0b53c1181d1b8d5e12df4bd3810

## Protection (single-tier, production-locked 2026-04-17; revalidated 2026-04-23; relocked C2 2026-05-08)

Single rule in `dd_protection.py`. `portfolio_mc` validates.

* **DD tier**: if `(equity - peak) / peak <= -0.015`, multiply day's sizing by 0.40×.
* Clears automatically when equity returns to peak.
* MC at current 4-strategy config (G 0.34% / DJ30 v4.5 1.00% / A 1.50% / NAS v1 0.40%, dd_protection C2 1.5%/0.40×, Pepperstone 2022→2026, 223 week-blocks, 10K × 3 seeds):
  **98.09% pass / 0.36% bust (0.00% daily + 0.36% static) / 1.55% timeout**, p99 DD 4.73%, median days-to-pass 22. Both lock gates clear with margin.
* 2026-05-08 relock from C0 (1.0%/0.40×) → C2 (1.5%/0.40×). Override grounds: `bust_attribution_flip` resolved broker-feed-confirmed via same-date Pepperstone+OANDA TV re-export, and Q-DDP-1's C2 sweep showed risk-controls-met + median-pass-time benefit (23 → 22 days). Q-DDP-1's regime-robustness gate (criterion 5) failed for C2; the 2026-05-08 override accepts that risk on the broker-feed + median-pass-time grounds. See `docs/adr/2026-05-08-dd-trigger-c2-relock.md` (canonical ADR) and `docs/briefs/Q-DDP-1/recommendation.md` override note.
* **Forward revert trigger (quarterly review):** if rolling 6-month MC pass-rate falls below 95% for two consecutive 6-month windows, revert to C0. Run `python analysis/time_to_pass.py --regime-check` quarterly (next dates: 2026-08-08, 2026-11-08, 2027-02-08, 2027-05-08).
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
* **Regime-robustness gate** (mandatory before any LOCK CANDIDATE on a `dd_protection`-class risk constant; 6mo block bootstrap + half-panel split, both pinned to brief floor; Q-DDP-1 worked example 2026-05-06): [`docs/methodology/regime_robustness_gate.md`](docs/methodology/regime_robustness_gate.md).
* **Operational rules** (incl. doc/code skew audit trigger): [`docs/operational_rules.md`](docs/operational_rules.md).
* **Strategy-research-phase methodology archive** (INQHIORI ⊕ The Algorithm framework, Pre-Q gates, Case B audits, MVD framing — all retired 2026-04-29; 90-day review gate 2026-07-29): [`archive/docs/methodology/archive/README.md`](archive/docs/methodology/archive/README.md).

## Public-clone posture

This repo is public; two classes of files are gitignored:

* **Vendor-licensed CSVs** under `data/tv_exports/`, `data/bar_data/`,
  `data/external/` (Pepperstone/OANDA TOS — personal export OK, redistribution
  not). Per-directory `SHA256SUMS` manifests are tracked.
* **Pine strategy source** (`**/*.pine`) — held privately to protect the live
  edge. Per-file hashes pinned in [strategies/MANIFEST.sha256](strategies/MANIFEST.sha256).

Tests that depend on vendor CSVs skip-if-missing. Locally Joshua has both sets,
so the full 105-test suite passes; on a fresh public clone the data-dependent
tests skip and the rest still run. The Python pipeline is reproducible end-to-end
once a valid `data/tv_exports/pepperstone/` is dropped in.

### Vendor-data integrity gate

After re-exporting any panel CSV under `data/tv_exports/`, any broker bar file
under `data/bar_data/`, or any reference CSV under `data/external/`, run
`python scripts/check_data_manifests.py --regenerate --dry-run` first, then
`python scripts/check_data_manifests.py --regenerate`, and commit the
`SHA256SUMS` delta in the **same commit** as the data change.

All four manifest dirs (`data/tv_exports/pepperstone/`,
`data/tv_exports/oanda/`, `data/bar_data/`, `data/external/`) must be present
locally before commits that stage anything under `data/`. Restore missing dirs
via their canonical sources (e.g. `data/bar_data/` via
`scripts/fetch_oanda_bars.py`) before staging. `--no-verify` is not the
standing path.

The checker hashes **working-tree bytes** (`open(..., "rb")`). With
`core.autocrlf=true` (typical on Windows), that is CRLF as checked out—not the
git blob—matching what `sha256sum` sees on disk.

**Load-bearing gate:** install the git `pre-commit` hook once per clone so
commits touching those trees cannot land with a stale manifest:

* Bash (macOS / Linux / Git Bash): `bash scripts/install_hooks.sh`
* Windows cmd: `scripts\install_hooks.bat`

Supplementary: Claude Code `PostToolUse` hooks (e.g. `scripts/lock_event_hook.py`)
do not replace this; they solve a different class of edits.

**CI is format-only:** `.github/workflows/manifest-check.yml` validates
`SHA256SUMS` line shape and ensures no `data/tv_exports/**/*.csv` or
`data/bar_data/**/*.csv` is accidentally tracked. It cannot re-hash gitignored
bytes on GitHub runners. Escape hatch: `git commit --no-verify` skips the hook
when intentional.

See [`docs/adr/2026-05-10-manifest-integrity-gate.md`](docs/adr/2026-05-10-manifest-integrity-gate.md).

**M-9 (methodology):** Gitignored vendor-data manifests need a local pre-commit
hash gate. CI cannot replace it when the bytes aren't in the repo. Manual regen
drifts silently. [`docs/methodology/lessons/methodology_lessons.md`](docs/methodology/lessons/methodology_lessons.md)

## Key Principle

The portfolio and strategies are LOCKED. This pipeline manages the *operational layer* — it never touches strategy parameters.
