# STATE — multi_firm_operations

**Snapshot date:** 2026-05-15
**Branch:** `claude/kind-lumiere-f15df7` @ `b54c02a` (HEAD); `origin/main` @ `7967644`
**Working tree:** 11 modified + 1 new file (uncommitted 2026-05-14 allocation refresh — see "Pending commit" below)
**Divergence vs origin/main:** local 2 ahead / 4 behind. Local commits are the pre-existing pre-refresh batch (Guardian Silver pin `b54c02a`, Q-CORR-1.2 seam `7b71329`); the working-tree edits for the 2026-05-14 allocation refresh are not yet committed.

This is a *snapshot*, not a history. For history: `CHANGELOG.md`. For classification: `REPO_MAP.md`. For locked constants and MC anchors: `CLAUDE.md`.

---

## Locked surfaces

### Strategies (Pine v6, all locked)

| Strategy        | Instrument  | Risk     | Pine deltas (vs prior lock)          | Version    | Lock date    | DXTrade contractValue |
|-----------------|-------------|----------|--------------------------------------|------------|--------------|-----------------------|
| Guardian Gold   | XAUUSD 15m  | 0.34%    | unchanged                            | v5.5       | 2026-04-23   | 100                   |
| Striker DJ30    | DJ30 15m    | **0.75%**| **pyramid 350% → 500%**              | v4.5       | 2026-05-14*  | 10                    |
| Aegis USDJPY    | USDJPY 15m  | 1.50%    | unchanged                            | v4.3       | 2026-04-22   | default (1)           |
| Striker NAS100  | NAS100 15m  | **0.45%**| allocation only (variant CSV sized 0.475% raw, re-scaled via implied_1r) | v1 | 2026-05-14* | 10 |

*2026-05-14 allocation refresh — version designation question open (pyramid 350→500 is Pine-source change). See [docs/adr/2026-05-14-allocation-refresh.md](docs/adr/2026-05-14-allocation-refresh.md) §Open items #1/#2.

Unified challenge/funded allocations (2026-04-17 baseline; DJ30 + NAS re-allocated 2026-05-14). No overlays active.

### Risk control

`dd_protection.py` — single-tier, **C2 locked 2026-05-08** (unchanged through 2026-05-14 refresh):

- Trigger: `(equity − peak) / peak ≤ −0.015` → multiply day's sizing by 0.40×.
- Auto-clears on peak return.
- ULP rounding fix landed 2026-05-10 (`6c7fa54`).

### MC anchor (Pepperstone, 4-strategy at C2 + 2026-05-14 allocation refresh)

**98.78% pass / 0.12% bust (0.00% daily + 0.12% static) / 1.10% timeout**, p99 DD 4.17%, median 21 days-to-pass.
Bust attribution: guardian 34.3% / aegis 28.6% / striker 25.7% / NAS 11.4%.
Both lock gates (bust <1%, p99 DD <5%) pass with the **widest margin of any anchor on record**. Reproducible via `python portfolio_mc.py --panel pepperstone`; pinned in `tests/test_mc_anchors.py`.
Panel: 2022-05-23 → 2026-05-14 (1039 bdays / 207 week-blocks).

**Documented revert target** (if 2026-05-14 §Falsifier fires): 2026-05-14 panel-refresh-only anchor 98.65 / 0.25 / 4.69 at DJ30 1.00%/pyr 350%, NAS 0.40%.

OANDA secondary at C2 (3-strategy, DJ30 still v4.4, panel unchanged): 96.33 / 0.40 / 4.73, median 26 days — anchor reshapes through DJ30 risk reduction only (no NAS panel on OANDA).

### Quarterly C2→C0 revert gate

Run `python analysis/time_to_pass.py --regime-check` quarterly. **Next dates: 2026-08-08 → 2026-11-08 → 2027-02-08 → 2027-05-08.** Revert if rolling 6-month pass <95% for two consecutive windows. Q-DDP-1's regime-robustness gate failed for C2 (2026-05-08); the 2026-05-14 allocation refresh further overrides the gate explicitly per [docs/adr/2026-05-14-allocation-refresh.md](docs/adr/2026-05-14-allocation-refresh.md) §Override. Same quarterly cadence covers retrospective catch.

---

## Pending commit (2026-05-15 working tree)

Uncommitted 2026-05-14 allocation refresh — 11 modified + 1 new file:

| File | Change |
|---|---|
| `docs/adr/2026-05-14-allocation-refresh.md` (**NEW**) | Lock decision ADR — §Override of regime-robustness gate (7/7 brief discipline checks pass) |
| `portfolio_mc.py` | `ALLOCATIONS` striker 0.0100→0.0075, striker_nas100 0.0040→0.0045; `PEPPERSTONE_PANELS` swapped to e4dd7 + da880; `assert_window` tolerance 60d→100d |
| `tests/test_mc_anchors.py` | Pepperstone 0.9878/0.0012/0.0417 + OANDA 0.9633/0.0040/0.0473 pins; docstrings reflect refresh |
| `firm_rules.py` | `_BASE_RISK` constants — load-bearing for `cli.py lots` multiplier formula |
| `live_journal/scripts/journal_review.py` | `STRATEGIES.risk_pct` (was 1.00 / 0.40 → 0.75 / 0.45) |
| `CLAUDE.md` | Strategy Reference table + MC anchor block + Protection MC line + baseline-risk note |
| `README.md` | Headline anchor 98.65/0.25/4.69 → 98.78/0.12/4.17 + bust attribution |
| `analysis/time_to_pass.py` | Baseline pass-rate references (3 lines) |
| `docs/methodology/regime_robustness_gate.md` | Production-pinned MC anchor line |
| `docs/notion/repo_context.md` | Anchor pinned-by + MVD-gates line |
| `.claude/commands/mc-anchors.md` | Skill command template generalized |
| `data/tv_exports/pepperstone/SHA256SUMS` | +2 variant entries (e4dd7, da880) — manifest now 13 rows |

**Test gate:** 170 passed, 1 skipped, 4 warnings, no failures.
**Manifest check:** silent success in both worktree and main repo (parity confirmed by `diff`).
**Discipline check:** 7/7 PASS on the ADR (`scripts/check_brief.py --type adr`).

The 2026-05-14 panel refresh (which produced the 98.65/0.25/4.69 panel-refresh-only intermediate anchor) and the 2026-05-14 allocation refresh (which produced the 98.78/0.12/4.17 current canonical) are bundled in this single uncommitted change set — both updates flow from the same 2026-05-14 Pepperstone re-export event.

---

## Active investigations

### Q-CORR-1.2 — Guardian-family Silver (XAGUSD) WFO admission

**Status:** LOCKED 2026-05-13. Path B (TradingView-native coarse grid) admission gate.
**Brief:** [docs/briefs/Q-CORR-1.2-guardian-family-silver-wfo.md](docs/briefs/Q-CORR-1.2-guardian-family-silver-wfo.md).
**Comparator:** Guardian Gold v5.5 Pepperstone XAGUSD `_13fad` (digest `e38e8fe8…`).
**Scope:** binary admission for a viable Guardian-family parameter zone on Silver. *Not* portfolio lock or 5-strategy re-MC; promotion requires a separate lock decision brief.
**Currently blocked on:** Phase 0 root-cause confirmation for Pepperstone TV XAGUSD M15 bar-history insufficiency (Q-CORR-1.3 verdict 2026-05-13). Joshua-side TV reconnaissance pending.

### Q-CORR-1.3 — Silver feed substitution (CLOSED-RESOLVED, H1-resume)

**Status:** CLOSED-RESOLVED 2026-05-13. Q-CORR-1.2 resumes unchanged.
**Brief:** [docs/briefs/Q-CORR-1.3-guardian-family-silver-pepperstone-feed-substitution.md](docs/briefs/Q-CORR-1.3-guardian-family-silver-pepperstone-feed-substitution.md).
**Verdict:** the §15 pre-flight tested the wrong capacity surface (TV chart-display depth, not strategy-tester depth). Strategy-tester depth is intact, so Q-CORR-1.2 does not need feed substitution. OPEN ITEMS B–J moot; A collapses to A.iv (resume).

### Q-CORR-1.2 §16 seam scaffolding (landed)

`scripts/wfo/` Path B orchestration shell (PR #79, local + upstream):

- `train_selection_lock.py` — extended lock schema (constraint_floors, tie_break_applied, candidate_count, grid_hash, fold_spec_hash, selection_status); `assert_oos_matches_lock` refuses NO_CANDIDATE locks.
- `operations.py` — tie-break ladder (pf_tie / dd_tie / wr_distance_tie / alpha_id); NO_CANDIDATE writes lock before raising; OOS ingest populates `folds[i].oos_csv_paths`.
- `run_path_b.py` — batch ingest (file or directory); `cmd_select` returns non-zero on NO_CANDIDATE.
- `report.py` — §14 disposition evaluator (RESOLVED / FALSIFIED / AMBIGUOUS); §5.8 hygiene (verdict in CLI stdout only, never in `report.json`/`report.md`).
- `closure_note.py` — skeleton generator with `<DISPOSITION>` placeholder; three §17 branches for hand-curation.

Tests: **157 pass / 14 skip** at PR #79 landing; **170 pass / 1 skip** in this worktree after 2026-05-14 allocation refresh (skip count drops as worktree has vendor CSVs).

---

## Recently closed / archived (working memory)

| Item                       | Closed       | Disposition                          | Trail                                                              |
|----------------------------|--------------|--------------------------------------|--------------------------------------------------------------------|
| **2026-05-14 allocation refresh** | **2026-05-14** (pending commit) | **DJ30 0.75% / pyr 500% + NAS 0.45%; gate override** | **`docs/adr/2026-05-14-allocation-refresh.md`** |
| 2026-05-14 panel refresh   | 2026-05-14   | Subsumed by allocation refresh (98.65→98.78 intermediate; documented revert target) | bundled in same commit set |
| Q-DDP-1 (dd_trigger sweep) | 2026-05-08   | C0→C2 with override                  | `docs/briefs/Q-DDP-1/recommendation.md`, ADR 2026-05-08            |
| `bust_attribution_flip`    | 2026-05-08   | Broker-feed confirmed                | `docs/briefs/bust_attribution_flip.md`                             |
| Q-MCFP-1 (MC precision)    | 2026-05-10   | mc_explore.py DELETED                | `docs/briefs/Q-MCFP-1/closure.md`                                  |
| GH #62 manifest gate       | 2026-05-10   | Phase B done; pre-commit hook live   | ADR 2026-05-10-manifest-integrity-gate                             |
| GH #54 ULP audit v2        | 2026-05-10   | DONE_WITH_CONCERNS (M-8 candidate)   | `docs/adr/2026-05-10-dd-protection-ulp-rounding.md`                |
| Q-DJ30-1 / -2 / -3         | 2026-05-06   | CLOSE/null + AMBIGUOUS/HOLD; archived 2026-05-08 | `archive/analysis/Q-DJ30-{1,2,3}/`                  |
| Q-NAS-2 capture plan       | 2026-05-08   | Closed; archived same day            | `archive/docs/striker_nas100/q_nas_2_capture_plan.md`              |

---

## Infrastructure

### Public-clone posture (2026-05-10)

This repo is public; two classes gitignored:

- **Vendor CSVs** under `data/tv_exports/`, `data/bar_data/`, `data/external/` — `SHA256SUMS` tracked.
- **Pine strategy source** (`**/*.pine`) — per-file hashes in `strategies/MANIFEST.sha256`.

Local clone has both sets; on a fresh public clone, data-dependent tests skip and the Python pipeline is reproducible once `data/tv_exports/pepperstone/` is dropped in.

### Vendor-data integrity gate (load-bearing)

- Local `pre-commit` hook required. Install via `bash scripts/install_hooks.sh` (POSIX) or `scripts\install_hooks.bat` (Windows).
- After re-exporting any panel CSV / bar file / reference CSV: `python scripts/check_data_manifests.py --regenerate --dry-run` → `--regenerate` → commit the `SHA256SUMS` delta in the **same commit**.
- CI (`.github/workflows/manifest-check.yml`) is **format-only**: validates `SHA256SUMS` line shape + no tracked vendor CSVs. Cannot re-hash gitignored bytes on runners. The local hook is the only byte-validation gate.
- See ADR 2026-05-10-manifest-integrity-gate + M-9 lesson.

### MVD `assert_window` tolerance (2026-05-14)

Loosened 60d → 100d in `portfolio_mc.py:load_trades` to accept Aegis's 1367-day span on the strict 4yr (2022-05-14 → 2026-05-14) Pepperstone re-export — filter warm-up delays first signal by ~2 months. The 1400d floor still rejects ≥3-month coverage gaps (would still have caught the aborted 681d Aegis _05549 export). Inline justification at the call site; documented in `docs/adr/2026-05-14-allocation-refresh.md` (carried from panel refresh).

### Repo rename (2026-05-08)

`prop_firm_pipeline` → `multi_firm_operations`. Working tree at `C:\Users\joshu\multi_firm_operations\`; remote `https://github.com/Joshua-Asante/multi_firm_operations.git`; package name `multi-firm-operations` in `pyproject.toml`. Historical doc/code refs swept; ADR + brief URLs untouched (GitHub auto-redirects).

---

## Methodology layer (post-2026-04-29 minimal set)

Strategy-research-phase methodology (INQHIORI ⊕ The Algorithm, Pre-Q gates, Case B audits, MVD framing) **retired 2026-04-29** to `archive/docs/methodology/archive/`; 90-day review gate **2026-07-29**.

Active rules (only what earned its place via execution-phase failure):

- **Rule 0** — audit-first (`docs/rule_0.md`). Cross-phase track record 2026-04-17 / 2026-04-27 / 2026-05-14 (the allocation-refresh ADR's 29-anchor §0 is the latest worked example).
- **The Algorithm** — default problem-solving framework (Notion: 34ddc0b53c11811eb6a0d9192b63d252).
- **Observation routing** — three-bucket gate Closed / Action / Forward (`docs/methodology/observation_routing.md`).
- **1R estimation** — per-strategy 1R, equity-compounding normalization (`docs/methodology/1r_estimation.md`).
- **Regime-robustness gate** — 6mo block bootstrap + half-panel split; pinned to brief floor; mandatory before any LOCK CANDIDATE on a `dd_protection`-class constant. Overridden twice on record (2026-05-08 C2 relock, 2026-05-14 allocation refresh) — both with explicit grounds and forward retrospective catch via quarterly `time_to_pass.py --regime-check` cadence. (`docs/methodology/regime_robustness_gate.md`).
- **Operational rules** — incl. doc/code skew audit trigger (`docs/operational_rules.md`).

INQHIORI vs OODA loop selection (reactivated 2026-05-01): INQHIORI for structural / low-reversibility / hypothesis-bearing; OODA for tactical / recoverable / tempo-bound. Tiebreaker: cannot articulate the falsifiable hypothesis in one sentence → OODA. Rebound check **2026-07-29**.

---

## Open questions / queued

- **DJ30 version designation (2026-05-14 ADR §Open items #1):** pyramid 350% → 500% is a Pine-source parameter change. Filename retains `v4.5`. Two coherent resolutions: (a) bump to v4.6 + Pine version-lock ADR; (b) re-document v4.5 as "production parameters: risk 0.75%, pyramid 500%". Defer to next session.
- **NAS100 variant `da880` pyramid behavior (ADR §Open items #2):** +22% Net at identical trade selection suggests Pine pyramid edit alongside sizing change. v1 designation may need version-bump.
- **OANDA re-export (ADR §Open items #3):** OANDA panel stayed at 2026-04-25 / 2026-05-08 vintage on 2026-05-14. Closes the panel-vintage parity gap if re-exported under new allocations.
- **Phase 0 (Q-CORR-1.2 dependency):** Joshua-side TV reconnaissance to confirm strategy-tester depth on Pepperstone XAGUSD M15 covers fold window `2022-01-11 → 2026-04-20`. Q-CORR-1.2 cannot resume sweep execution until determinate.
- **OANDA panel migration** (open question, no deadline): `archive/strategies/striker/striker_dj30_v4.4.pine` retained for OANDA-panel back-compat; potential retire after OANDA mirror regenerated against v4.5.
- **C2→C0 revert trigger**: first quarterly check 2026-08-08 (~12 weeks out). Now covers both the 2026-05-08 dd_protection override and the 2026-05-14 allocation-refresh override (same cadence, same instrumentation).
