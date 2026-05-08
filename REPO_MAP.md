# REPO_MAP — active classification

**Updated:** 2026-05-08 (post C2 relock + repo-map disposition pass)
**Convention:**
- `[A]` active hot-path (production code, locked strategies, active analyses, immutable record)
- `[U]` utility — runs on demand, not in CI hot path, retained as load-bearing tool
- `[X]` archived — superseded or closed workstream; provenance only
- `[?]` open question — classification pending Joshua decision

Re-classification candidates (flagged `***`) stay `[A]` until a future Simplify pass.

---

## Root
[A] CLAUDE.md
[A] README.md
[A] CHANGELOG.md
[A] pyproject.toml
[A] REPO_MAP.md (this file)

## Production code
[A] accounts.py
[A] cli.py
[A] csv_parser.py
[A] firm_rules.py
[A] dd_protection.py — LOCKED single-tier 1.5% / 0.40× (C2 relock 2026-05-08)
[A] portfolio_mc.py — canonical lock-decision MC
[A] mc_explore.py — exploratory; explicitly NOT for locks

## Library
[A] lib/mvd.py
[A] lib/nonlinear.py
[A] lib/oanda.py
[A] lib/oanda_creds.py
[A] lib/tearsheet.py

## Strategies (Pine v6, locked)
[A] strategies/guardian/guardian_gold_v5.5.pine — LOCKED 2026-04-23
[A] strategies/guardian/guardian_CHANGELOG.md
[A] strategies/striker/striker_dj30_v4.5.pine — LOCKED 2026-05-05
[A] strategies/striker/striker_nas100_v1.pine — LOCKED 2026-05-05
[A] strategies/striker/striker_CHANGELOG.md
[A] strategies/aegis/aegis_usdjpy_v4.3.pine — LOCKED 2026-04-22
[A] strategies/aegis/aegis_CHANGELOG.md

## Scripts
[A] scripts/build_us_releases.py
[U] scripts/dryrun_aegis_v4_3.py — end-to-end exercise of all 9 lib/mvd helpers; sanity gate (verdict 2026-05-07)
[A] scripts/fetch_oanda_bars.py — hard-codes USDJPY/XAUUSD/US30USD only; not a general fetcher
[A] scripts/lock_event_hook.py

## Live execution
[A] live_journal/scripts/journal_review.py — signal-vs-fill reconciliation pipeline
[A] live_journal/scripts/m7_anticipation_gap_backfill.py — M-7 Route A slippage backfill (sibling-imports journal_review)
[A] live_journal/references/execution_lessons.md — E1/E2 anchor registry (skill ↔ repo runtime mirror)
[U] live_journal/data/ — runtime DXTrade exports + journal outputs (gitignored except .gitkeep)

## Data — TV exports (canonical MC inputs)
[A] data/tv_exports/pepperstone/Guardian_Gold_v5.5_*.csv
[A] data/tv_exports/pepperstone/Striker_DJ30_v4.5_*.csv
[A] data/tv_exports/pepperstone/Striker_NAS100_v1_*.csv
[A] data/tv_exports/pepperstone/Aegis_USDJPY_v4.3_*.csv
[A] data/tv_exports/pepperstone/SHA256SUMS — pinned panel hashes
[A] data/tv_exports/oanda/*.csv — secondary, validates Pepperstone

## Data — bars / external / reconciles
[A] data/bar_data/XAUUSD.csv, USDJPY.csv, US30USD.csv — active strategy bars
[A] data/bar_data/EURUSD_dukascopy_*, GBPUSD_dukascopy_*, USDCHF_pepperstone_h4_*, USOIL_oanda_m15_*_clean.csv, USOIL_oanda_m15_*_raw.csv — referenced by active findings docs (not duplicates of OANDA fetcher; vendor-specific panels)
[A] data/external/dxy.csv
[A] data/external/us_high_impact_0830et_2022_2026.csv
[A] data/reconciles/2026-05-05_guardian_n_reconcile.md
[A] data/*.sha256 — pinned hashes

## Tests
[A] tests/*.py — all CI-load-bearing

## Analysis
[A] analysis/oanda_stage1/ — findings in docs/methodology/findings/2026-05-02_oanda_stage1_*
[A] analysis/time_to_pass.py — re-MC reporting + --regime-check mode (quarterly review per ADR 2026-05-08-dd-trigger-c2-relock)

## Docs (active)
[A] docs/rule_0.md
[A] docs/operational_rules.md
[A] docs/methodology/*.md (active set: 1r_estimation, observation_routing, regime_robustness_gate)
[A] docs/methodology/findings/*.md
[A] docs/methodology/gate_audits/*.md
[A] docs/methodology/lessons/methodology_lessons.md — M-class lesson registry (format spec + M-7 CANDIDATE seeded 2026-05-08)
[A] docs/adr/*.md — IMMUTABLE record (latest: 2026-05-08-dd-trigger-c2-relock)
[A] docs/briefs/*.md — closed-with-override: Q-DDP-1 (C2 lock 2026-05-08); closed: Q-DJ30-3 (2026-05-06), bust_attribution_flip (2026-05-08); active: NAS100 (×2)
[A] docs/historical/*.md — IMMUTABLE record
[A] docs/templates/*.md
[A] docs/striker_nas100/q_nas_2_capture_plan.md — CLOSED 2026-05-08 (no forward capture; Q-NAS-1 hour×dow accepted as the answer)

## Archive (consolidated 2026-05-07, Approach D)
[X] archive/analysis/ — eurusd_lnyo, gbpusd_lon, usdchf_sentinel, usoil (incl. usoil/indicators/usoil_phase2_validation.pine moved 2026-05-07), striker_nas100/q_nas_1_pyramid_hypothesis.py (closed 2026-05-05), Q-DJ30-1/2/3 (closed 2026-05-06; archived 2026-05-08, cooldown overridden), dd_protection_trace.py (forensic tool moved with closed Q-DDP-1 cohort 2026-05-08)
[X] archive/docs/methodology/archive/ — full methodology archive (inner archive/ nesting preserved per README); + msee/_active_paths_2026-05-07/ (analysis_msee + msee_watchlist.py, archived 2026-05-07); + overlays/guardian_conflict_risk.md (deactivated 2026-04-23, archived 2026-05-07)
[X] archive/strategies/striker/striker_dj30_v4.4.pine — kept for OANDA-panel back-compat (open question: retire after OANDA mirror regenerated against v4.5)
[X] archive/strategies/striker/striker_nas100_v1_research.pine — post-lock research file (archived 2026-05-07; referenced by docs/striker_nas100/q_nas_2_capture_plan.md while Q-NAS-2 is open)
[X] archive/data/tv_exports/USOIL_pepperstone_m15_*.csv
[X] archive/scripts/run_v55_validation.py — Guardian v5.5 lock-validation harness, archived 2026-05-08 (one-shot; hardcoded v5.5/v5.4 expected metrics, future locks need own harness)

## Infrastructure
[A] .claude/commands/lock-check.md
[A] .claude/commands/mc-anchors.md
[A] .claude/commands/skew-audit.md
[A] .claude/settings.json
[A] .github/workflows/pylint.yml
[A] .github/workflows/tests.yml
[A] .gitignore
