# WFO runner spec v0

**STATUS (2026-05-14):** RE-CLASSIFIED — general-purpose OOS infrastructure, **not Silver-specific**. Original target Q-CORR-1.2 closed pre-lock per [`docs/briefs/Q-CORR-1-closure.md`](../briefs/Q-CORR-1-closure.md) §5.2. Spec is parked at current state; decision (retain parked / carry to completion as standalone infra) deferred to the next strategy-admission investigation. Do NOT dispatch new CC handoffs against this spec citing Q-CORR-1.2 — that target is dead. Future use requires a fresh Pre-Q whose authoritative artifact names a live admission target.

**STATUS (prior):** READY — Path B subset (orchestration shell; Python Pine re-implementation explicitly out of scope for Q-CORR-1.2).

**Audience:** future strategy-admission investigations requiring deterministic walk-forward orchestration. The Q-CORR-1.2 audience tag is historical record only.

---

## §1 Purpose

Define a reproducible walk-forward **Path B** workflow: TradingView-native strategy execution, deterministic grid definition, manifest-backed fold assignment, OOS stitching, and report emission. Path B trades structural OOS isolation (Path A `Window` pattern) for procedural discipline enforced by manifests, timestamps, and optional train-selection lock files (see Pre-Q §6.5).

---

## §2 Definitions

- **Grid:** JSON file listing parameter dimensions; canonical sort + `json.dumps(..., sort_keys=True)` produces `grid_hash` (v0 uses JSON to avoid a PyYAML dependency).
- **Run manifest:** JSON declaring `run_id`, `grid_hash`, `fold_spec_hash`, `comparator_csv_hash`, `seed`, `bootstrap_seed`, `bootstrap_n_panels`, per-fold train selections, paths to ingested CSVs, and timestamps for audit.
- **Bootstrap convention (orchestration metadata, not gate definition):** `bootstrap_seed` and `bootstrap_n_panels` are pinned in the manifest at `init-run` and used by §14 Gate 9 (`lib.regime_bootstrap.regime_bootstrap_daily_pnl`) for reproducibility. Canonical defaults — `bootstrap_seed=42`, `bootstrap_n_panels=1000` — give noise-reduced `p05_pf` at the library's default `block_months=6`. The Gate 9 floor (`p05 PF ≥ 1.30`) is the gate; the seed/n_panels values are how it is mechanized, not part of the gate definition. Q-CORR-1.2 brief §15 acceptance reference for `p05 ≈ 1.05 ± 0.02` against the Q-CORR-1.1 v5.5 baseline reproduces only at `bootstrap_seed=7, bootstrap_n_panels=100` — that is a historical anchor, distinct from this disposition convention.
- **Train selection commit:** Event where the best train-fold config (per objective) is written to the manifest and `train_selection_lock.json` **before** OOS TV exports for that fold.

---

## §3 Algorithm (Path B subset)

1. Freeze `grid.json` → compute `grid_hash` (SHA-256 of canonical JSON bytes; see `scripts/wfo/grid_hash.py`).
2. Initialize `run_manifest.json` with fold plan (`fold_spec_hash`), comparator digest (`comparator_csv_sha256` from `SHA256SUMS` line), RNG `seed`, and bootstrap convention (`bootstrap_seed`, `bootstrap_n_panels`) for §14 Gate 9.
3. For each fold:
   - **Ingest** train TV exports: `python scripts/wfo/run_path_b.py ingest --run-dir <run> --csv <path>` (§16 `Silver_*_train.csv` naming; schema via `pair_tv_export_dataframe`; rows appended to manifest `ingests`).
   - **Select** train winner: `python scripts/wfo/run_path_b.py select --run-dir <run> --fold-id 1` (§16 ladder → `train_selection_lock.json` + manifest `folds[]` timestamps).
   - After lock timestamp: **ingest** OOS CSV only for the locked basename (`assert_oos_matches_lock` runs inside `ingest` for `*_oos.csv`).
4. Stitch OOS daily Net P&L across folds (concatenate in calendar order; non-overlapping windows by construction).
5. Evaluate §6 gates: correlation via `lib.correlation.pearson_daily_pnl` vs comparator; regime via `lib.regime_bootstrap`; PF/WR/DD per registered floors.
6. Emit `report.md` + `report.json` under `scripts/wfo/runs/<run_id>/` (`python scripts/wfo/run_path_b.py emit-reports --run-dir ...`).

---

## §6 Reporting

Each run directory contains:

- `run_manifest.json` — authoritative ordering and hashes.
- `report.md` — human summary: grid point selected per fold, metrics tables, gate pass/fail.
- `report.json` — machine-readable duplicate for CI.

---

## §7 Acceptance (Path B subset)

### §7.2 Comparator / ingestion sanity

CSV ingestion + daily Net P&L aggregation reproduces Q-CORR-1.1 amendment §7 Silver reference metrics from the agreed **v5.5-on-Silver XAGUSD** TV-export (exact filename + `SHA256SUMS` line registered at Pre-Q lock). Until lock: optional skip-if-missing in CI.

### §7.4 Selection-bias smoke

Deliberately overfit a toy grid on a single train fold; confirm stitched OOS degrades relative to train (bias visible).

### §7.5 Audit hooks

All commands in [`docs/briefs/Q-CORR-1.2-guardian-family-silver-wfo.md`](../briefs/Q-CORR-1.2-guardian-family-silver-wfo.md) §10 must pass for a claimed RESOLVED run.

### §7.6 Adversarial discipline tests (pre-flight)

Before TV operation, execute the scenarios in [`wfo-runner-v0-adversarial-tests.md`](wfo-runner-v0-adversarial-tests.md) and record outcomes in that file’s log table.

---

## Out of scope (v0)

- Path A Python `Window` runner.
- Automatic TradingView execution (human exports CSVs; runner ingests artifacts).
