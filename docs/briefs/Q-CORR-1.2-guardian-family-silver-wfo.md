# Q-CORR-1.2 — Guardian-family Silver (XAGUSD) WFO admission (Pre-Q)

**Status:** LOCKED  
**Lock date:** 2026-05-13  
**Date:** 2026-05-13  
**Parent:** Q-CORR-1.1 (correlation gate methodology; X lock and zero-fill semantic)  
**Loop:** Inquire-phase Pre-Q — binary admission for a viable Guardian-family parameter zone on Silver; **not** portfolio lock or 5-strategy re-MC.  
**Artifact path:** flat brief at [`docs/briefs/Q-CORR-1.2-guardian-family-silver-wfo.md`](Q-CORR-1.2-guardian-family-silver-wfo.md) (subdir convention not adopted for this Pre-Q).

**LOCK amendment:** §11–§19 appended 2026-05-13. After this revision, §4 hypothesis, §6 gates, and the parameter grid are frozen per §5 forbidden moves. Mid-run amendments are forbidden; methodology-layer changes require a new Pre-Q.

---

## §0 Rule-0 reads (production + load-bearing artifacts)

Read before treating any numeric claim or gate as authoritative:

- [`firm_rules.py`](../../firm_rules.py), [`accounts.py`](../../accounts.py), [`dd_protection.py`](../../dd_protection.py) — operational risk layer (context only; no strategy parameter edits).
- [`docs/rule_0.md`](../rule_0.md) — audit-first discipline.
- [`docs/methodology/regime_robustness_gate.md`](../methodology/regime_robustness_gate.md) — regime-robustness bootstrap pattern (adapted for OOS-stitched daily Net P&L in this Pre-Q).
- [`docs/spec/wfo-runner-v0.md`](../spec/wfo-runner-v0.md) with `STATUS=READY` for Path B subset (orchestration shell only; Python re-implementation modules out of scope for Q-CORR-1.2).
- [`docs/spec/wfo-runner-v0-phase1-path-analysis.md`](../spec/wfo-runner-v0-phase1-path-analysis.md) (CC Phase 1 analysis, DONE_WITH_CONCERNS, 2026-05-13). Phase 1 path decision: (Coarse, Path B) accepted by Joshua 2026-05-13.
- `data/tv_exports/pepperstone/SHA256SUMS` must include the `_13fad` Guardian Gold comparator row (`Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-12_13fad.csv`). **Pinned digest:** `e38e8fe80419a286666898e8cae41a3be796277844367b7f1dfdcc3a0feba124`. Verify with:

  ```bash
  grep e38e8fe8 data/tv_exports/pepperstone/SHA256SUMS
  ```

  PowerShell equivalent:

  ```powershell
  Select-String -Path "data/tv_exports/pepperstone/SHA256SUMS" -Pattern "e38e8fe8"
  ```

- [`lib/correlation.py`](../../lib/correlation.py) (canonical location; refactored from [`archive/analysis/eurusd_lnyo/correlation.py`](../../archive/analysis/eurusd_lnyo/correlation.py)) with `join='inner'` replaced by **zero-fill on the aligned date range**, per Q-CORR-1.1 amendment §7 semantic.

**At LOCK (2026-05-13), §0 infrastructure status:**

- Path B orchestration shell: present under `scripts/wfo/` (see [`docs/spec/wfo-runner-v0.md`](../spec/wfo-runner-v0.md)).
- `_13fad` comparator CSV + `SHA256SUMS` line: **on disk** (`Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-12_13fad.csv`); manifest regenerated. Run manifests must still set `comparator_csv_sha256` to the **full 64-hex** line at `init-run`.
- `lib/correlation.py` / `lib/regime_bootstrap.py`: landed; correlation semantic is zero-fill `bdate_range` alignment (full span between min/max exit dates).

---

## §1 Context

Q-CORR-1.2 asks whether a **Guardian-family** strategy configuration on **Silver (XAGUSD)** can pass a pre-registered admission battery: walk-forward (Path B — TradingView-native coarse grid), correlation gate vs locked Guardian Gold daily Net P&L comparator, and regime-robustness on stitched OOS daily P&L. Instrument differs from Gold; gates are calibrated not to silently import Gold’s parameter surface as if it were optimal for Silver.

### Phase 1 path decision

Phase 1 path-decision analysis completed 2026-05-13 (CC walk-away). Accepted recommendation: **(Coarse, Path B)**. Rationale: 3.25–5.25 dev-days vs Path A’s 7.5–14; comparable wall-clock under Joshua’s bandwidth constraint; native Pine execution on Pepperstone eliminates translation risk; sufficient for Q-CORR-1.2’s binary admission gate. Sequenced (Wide, Path A) optimization deferred to a possible **Q-CORR-1.3** if and only if Q-CORR-1.2 **RESOLVED** — the optimization question is post-admission and not part of this Pre-Q.

Note: this Pre-Q’s binary admission scope means “RESOLVED” identifies a **viable** Guardian-family parameter zone for Silver, not the globally optimal one. Promotion of Silver to the locked portfolio requires a **separate** lock decision brief and re-MC at the new 5-strategy composition, per §5 forbidden moves.

---

## §2 Question

Does any candidate in the pre-registered **Coarse** grid satisfy §6 gate criteria under Path B procedural discipline — including OOS-stitched correlation ≤ X′ vs the locked Gold comparator and regime-robustness on stitched OOS daily Net P&L — without breaching §5 forbidden moves?

---

## §3 Scope / non-goals

- **In scope:** Path B TV-native WFO shell, deterministic grid/manifest hashing, OOS aggregation metrics, correlation + regime gates per §6, audit hooks per §10.
- **Out of scope for Q-CORR-1.2:** Full Python Pine re-implementation; Path A wide optimization; portfolio-level MC at 5 strategies; any change to locked strategy parameters on Gold/DJ30/NAS/Aegis production code.

---

## §4 Falsifiable hypothesis

**H1 (architecture-core):** There exists at least one parameter vector in the pre-registered Coarse grid such that, under Path B discipline, stitched OOS performance clears §6 floors and **OOS-stitched** correlation with Guardian Gold v5.5 daily Net P&L (comparator CSV per §0) is ≤ **X′** (§4.1), and regime-robustness bootstrap criteria pass on the same stitched OOS daily series.

**¬H1:** No grid point clears §6 simultaneously; correlation or regime gate fails for all admissible selections; or Path B procedural discipline is violated (§6 / §10).

### §4.1 — X′ lock (correlation gate threshold)

**X′ = 0.10**

Rationale: X = 0.1229 (ρ_DJNAS = 0.022891 + 0.10 buffer, Q-CORR-1.1 §6 amendment) was calibrated against locked DJ30/NAS strategies (not swept). Q-CORR-1.2 admits parameter freedom within Guardian-family on Silver, which introduces selection-bias residual even under WFO discipline. **X′ = 0.10 (= X − 0.023)** adds buffer to absorb that residual.

Computed identically to Q-CORR-1.1’s correlation method:

- Daily Net P&L Pearson on aligned window.
- Zero-fill non-trade days on the **full business-day span** between the global min and max exit dates (`pd.bdate_range`, not inner-join on trade-only dates — see §0 Rule-0 reads for `lib/correlation.py`).
- Exit-date attribution.
- Comparator: Gold v5.5 daily Net P&L from the `_13fad` Pepperstone TV-export CSV (`Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-12_13fad.csv`; SHA256 `e38e8fe80419a286666898e8cae41a3be796277844367b7f1dfdcc3a0feba124` in `SHA256SUMS`).

**X′ is locked here**, NOT subject to mid-run adjustment per §5 forbidden moves.

---

## §5 Forbidden moves

- Mid-run adjustment of **X′**, fold boundaries, comparator CSV identity, or grid definition after `grid_hash` is committed to the run manifest.
- Claiming **RESOLVED** on partial folds without completing the pre-registered fold plan committed at run start (unless the Pre-Q explicitly closes early with a documented falsifier).
- Conflating this Pre-Q’s admission with **portfolio lock** or automatic inclusion in `portfolio_mc.py` without a separate lock brief and re-MC.

---

## §6 Gate criteria

**LOCK (2026-05-13):** authoritative numeric and procedural gates are consolidated in **§14**. The bullets below remain as conceptual scaffolding; **§14 wins** on any wording conflict.

**RESOLVED** only if all hold on the **stitched OOS** evaluation path (per WFO spec Path B subset):

- OOS-aggregated correlation with Gold v5.5 daily Net P&L on aligned window **≤ X′ = 0.10** (locked per §4.1).
- Regime-robustness gate passes on OOS-stitched daily Net P&L (bootstrap + half-panel criteria per **§14**).
- PF / DD / WR / MFE–MAE floors per **§14**.
- Path B procedural discipline holds: TV export filename encodes parameter set verifiably; fold-window encoding is confirmable from CSV ingestion timestamp ordering relative to the run manifest; no OOS run is credited for a candidate that was not selected by train-fold ranking in that fold.

**FALSIFIED** if:

- Any §6 numeric gate fails on the stitched OOS path for the selected candidate(s), or
- Path B procedural discipline **catastrophic failure:** any OOS run is observed **before** its corresponding train-fold selection has been committed to the run manifest. This is a **discipline-falsifier**, not a parameter-falsifier; if it occurs, the affected fold’s evidence is invalid and the Pre-Q closes **FALSIFIED on discipline grounds**, not strategy grounds.

**Prior gate line superseded:** “WFO runner audit hooks fail (grid hash drift, OOS leakage detected, fold boundary changed mid-run)” is replaced by the Path B procedural discipline bullets above (structural OOS protection is Path A; Path B relies on manifest + audit discipline — see §10).

### §6.5 — Train-selection lock (recommended mechanical guard)

Path A’s `Window` abstraction provides structural OOS protection. Path B does not. Recommended mitigation **(b)** — **tighter mechanical guard** — marginal cost ~0.25–0.5 dev-day:

- After train-fold ranking, the runner emits a per-fold **train-selection lock** file containing the selected config hash (and fold id).
- The lock file is committed (or timestamp-persisted) **before** any OOS TV export for that fold.
- OOS CSV ingestion **refuses** any file whose filename-encoded config hash does not match the lock file for that fold.

This does not prevent a determined bypass of git history, but it blocks casual out-of-order OOS and makes the discipline story legible to external reviewers.

---

## §7 Acceptance (pointer)

Detailed acceptance steps live in [`docs/spec/wfo-runner-v0.md`](../spec/wfo-runner-v0.md) §7 Path B subset. At minimum:

- §7.2 simplified: CSV ingestion + aggregation reproduces Q-CORR-1.1 amendment §7 Silver reference metrics from the agreed v5.5-on-Silver XAGUSD TV-export (pending filename registration at lock).
- §7.4 selection-bias smoke: deliberate overfit on a single fold; OOS must reveal bias.
- §7.5 §10 audit hooks pass.

---

## §10 Audit hooks

```bash
# Verify _13fad CSV present and hash matches Q-CORR-1.2 §0 citation
grep "e38e8fe80419a286666898e8cae41a3be796277844367b7f1dfdcc3a0feba124" data/tv_exports/pepperstone/SHA256SUMS
# Expected: line match

# PowerShell:
# Select-String -Path "data/tv_exports/pepperstone/SHA256SUMS" -Pattern "e38e8fe80419a286666898e8cae41a3be796277844367b7f1dfdcc3a0feba124"

# Verify correlation.py refactored to canonical location with zero-fill semantic
# (Git Bash / WSL — requires grep; or read file and confirm manually on Windows)
grep -E "fillna\\(0|reindex" lib/correlation.py
test $(grep -c "join=.inner" lib/correlation.py || echo 0) -eq 0
# Expected: zero-fill / reindex present; no join='inner' in lib/correlation.py

# Verify ρ_DJNAS + X anchor from current correlation.py against locked Pepperstone DJ30/NAS CSVs
# Paths must match the filenames committed in SHA256SUMS (rotate if exports change).
python -c "from pathlib import Path; from lib.correlation import pearson_daily_pnl; \
  P = Path('data/tv_exports/pepperstone'); \
  dj = P / 'Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv'; \
  nas = P / 'Striker_NAS100_v1_PEPPERSTONE_NAS100_2026-05-05_7ca6f.csv'; \
  rho = pearson_daily_pnl(dj, nas); \
  assert abs(rho - 0.021704) < 0.001, f'DJ/NAS anchor drifted: {rho}'; \
  print(f'rho_DJNAS={rho:.6f} X=rho+0.10={rho+0.10:.6f}')"
# Expected: rho_DJNAS ~0.0217 on 2026-05-05 panel pair; X = rho + 0.10 (~0.122)

# Path B: verify run manifest fold-train-OOS ordering
python scripts/wfo/audit_path_b_ordering.py scripts/wfo/runs/<run_id>/run_manifest.json
# Expected: PASS — every OOS CSV ingestion timestamp postdates its fold's train-selection commit
```

---

## Items superseded at LOCK (2026-05-13)

Prior “DRAFT-to-LOCK gaps” are closed in **§11–§14** (fold spec, WR band, grid contents, config count, hashes). Do not treat the obsolete open-items list as active.

---

## Items closed (2026-05-13)

- Canonical Pine source access concern for Path A: non-blocking under Path B.
- Q-CORR-1.1 original Pre-Q backfill: documentation hygiene; convenience.
- XAGUSD feed equivalence / OANDA API dependency for this workstream: non-blocking; Path B runs natively on Pepperstone TV data.
- Comparator semantic: **zero-fill**; **X = ρ + 0.10** preserved at methodology level; **X′ = 0.10** locked in §4.1 for this admission gate.
- Comparator series: `_13fad` Guardian Gold export — committed + `SHA256SUMS` updated (`e38e8fe8…`).

---

## Mechanical implementation queue (repo)

1. ~~Commit `*_13fad.csv` + regenerate `SHA256SUMS`~~ **Done** — `Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-12_13fad.csv` + digest `e38e8fe80419a286666898e8cae41a3be796277844367b7f1dfdcc3a0feba124`. **Commit with CSV bytes + `SHA256SUMS` in one git commit** per vendor-integrity rules.
2. `lib/correlation.py` — zero-fill daily alignment; `pearson_daily_pnl`; tests.
3. `lib/regime_bootstrap.py` — cap-free block bootstrap for daily P&L series; tests (skip-if-missing Silver CSV where applicable).
4. `analysis/oanda_stage1/tv_export_loader.py` — `XAGUSD` price column mapping; tests.
5. `scripts/wfo/` — Path B orchestration subset: frozen `grid.json` / `fold_spec.json` → `grid_hash` / `fold_spec_hash`, manifest, ingestion hooks, aggregate metrics, reports.
6. Discipline guards + **§6.5** train-selection lock enforcement at OOS ingest.
7. Acceptance battery wiring per spec §7 Path B subset.

---

## §11 — Lock state summary

| Item | Locked value | Source |
|------|--------------|--------|
| Phase 1 path | (Coarse, Path B) | CC analysis 2026-05-13, Joshua accepted |
| Fold spec | `n_folds=1`, train 40mo / OOS 12mo (dates §13) | Joshua 2026-05-13 |
| Grid construction | 4-dim Cartesian, **250** configs | Joshua 2026-05-13 |
| **`grid_hash`** | **`a8fdd34e800f312e6c064a595ee9ae3565472d0da0a0990348e07d28076f85b1`** | SHA-256 of canonical JSON for [`scripts/wfo/examples/grid.json`](../../scripts/wfo/examples/grid.json) at LOCK commit |
| **`fold_spec_hash`** | **`5591f024515f422548bf9e60a7f23225e559a05346e8911e6397346acad6673e`** | SHA-256 of canonical JSON for [`scripts/wfo/examples/fold_spec.json`](../../scripts/wfo/examples/fold_spec.json) at LOCK commit |
| X′ (correlation gate) | 0.10 | §4.1 lock per prior DRAFT revision |
| WR gate | ≥15% floor only (no upper bound) | Joshua 2026-05-13 |
| Correlation method | zero-fill daily Net P&L Pearson, exit-date attribution; full `bdate_range` span | Q-CORR-1.1 amendment §7 semantic; [`lib/correlation.py`](../../lib/correlation.py) |
| Comparator series | Gold v5.5 `Guardian_*_2026-05-12_13fad.csv`; **SHA256** `e38e8fe80419a286666898e8cae41a3be796277844367b7f1dfdcc3a0feba124` (grep `e38e8fe8`); run `init-run` must set **full 64-hex** `comparator_csv_sha256` | On disk; commit with manifest per ops rules |
| OOS protection | mechanical via `train_selection_lock.py` + audit timestamps | §6.5 lock per prior DRAFT revision |

### X reference value note

X = 0.123 was originally calibrated on the **2026-05-06** DJ30/NAS pair at ρ_DJNAS = 0.022891. The canonical tree carries the **2026-05-05** pair which yields ρ_DJNAS = **0.021704** under identical method. The §10 audit hook anchors on the canonical tree value (**0.0217**). **X is a historical reference; X′ = 0.10 is the actual gate threshold.** The ~0.0012 ρ-drift between source CSVs is well within the X − X′ = 0.023 buffer and does not require X re-locking. Documented for audit-trail integrity.

---

## §12 — Parameter grid (frozen)

Canonical bytes: [`scripts/wfo/examples/grid.json`](../../scripts/wfo/examples/grid.json) (LOCK commit). **Do not edit after LOCK** without a new Pre-Q.

### 4-dim Cartesian: 250 configurations

5 × 5 × 5 × 2 = **250** (`expected_config_count` in JSON).

### Hint-zone-anchor justification

- `ema_slow_len = 395` is the v1.5 hint value; `385` is the v5.5 lock value (FALSIFIED on Silver in Q-CORR-1.1 — included as the architectural-equivalence reference point that the perturbation regions surround). Values 450/500/550 are the slower-trend perturbation region.
- `stop_atr = 1.4` is v1.5; `1.55` is v5.5; 1.75/2.0/2.25 are the wider-stop perturbation region.
- `tp_atr = 33` is v1.5; `29` is v5.5; 15/20/25 are the faster-TP perturbation region.
- `session = NY_Extended` is the v1.5/v5.5 lock; `London_NY_Overlap` is the alternative-session perturbation.

Other fixed parameters held at v1.5’s choice (see `fixed_parameters` in `grid.json`). This Pre-Q does not sweep those dimensions in Q-CORR-1.2.

### `grid_hash` anchor

```bash
python scripts/wfo/grid_hash.py scripts/wfo/examples/grid.json
# Expected: a8fdd34e800f312e6c064a595ee9ae3565472d0da0a0990348e07d28076f85b1
```

---

## §13 — Fold spec (frozen)

Canonical bytes: [`scripts/wfo/examples/fold_spec.json`](../../scripts/wfo/examples/fold_spec.json).

### Single split: train 40 months / OOS 12 months (nominal)

```json
{
  "n_folds": 1,
  "train_start": "2022-01-11",
  "train_end": "2025-05-10",
  "oos_start": "2025-05-11",
  "oos_end": "2026-04-20",
  "comment": "40-month train / 11.3-month OOS, using Q-CORR-1.1 disposition's Pepperstone XAGUSD trade-date span (2022-01-11 -> 2026-04-20). OOS truncated to actual data end; spec window is 12 months nominal."
}
```

If pre-flight TV verification reveals different XAGUSD data availability (longer history, fresher end date), **update `fold_spec.json` before run-start**, re-hash, and amend **only** via a **new Pre-Q** if methodology changes; mechanical date corrections pre-run are OK if documented in the run manifest notes.

### `fold_spec_hash` anchor

```bash
python scripts/wfo/grid_hash.py scripts/wfo/examples/fold_spec.json
# Expected: 5591f024515f422548bf9e60a7f23225e559a05346e8911e6397346acad6673e
```

### Wall-clock estimate

- Train sweep: 250 configs × ~4 min ≈ **~17 h** TV time → realistically **5–8 sessions** of 2–2.5 h each.
- Train selection + lock commit: ~30 min (orchestration post-processing).
- OOS run: 1 config (or top-N ties; deterministic tie-break in §16) × ~4 min.
- Disposition analysis: 0.5–1 dev-day.
- **Total wall-clock to disposition: ~2–3 weeks** (interleaved with live ops / NDR / proving cluster).

---

## §14 — §6 gate criteria (final, frozen)

**RESOLVED requires ALL of:**

1. Run manifest `grid_hash` matches **§11** (`a8fdd34e…`) at run-start.
2. Run manifest `fold_spec_hash` matches **§11** (`5591f024…`) at run-start.
3. Run manifest `comparator_csv_sha256` equals the **full 64-character** SHA256 from `SHA256SUMS` for the `_13fad` Gold comparator row (`e38e8fe80419a286666898e8cae41a3be796277844367b7f1dfdcc3a0feba124` at last regen; the manifest field must not truncate).
4. Path B procedural discipline: `audit_path_b_ordering.py` returns **PASS** — every OOS CSV `mtime` postdates `train_selection_committed_utc` recorded for that fold (see `train_selection_lock.json` + manifest).
5. `assert_oos_matches_lock` validation passes for each OOS run (basename matches lock file).
6. OOS **PF ≥ 1.50**
7. OOS **WR ≥ 15.0%** (no upper bound)
8. OOS **DD ≤ 8.0%** (max underwater vs notional per disposition convention — register implementation in report JSON)
9. OOS 6mo-block bootstrap **p05 PF ≥ 1.30** via [`lib/regime_bootstrap.py`](../../lib/regime_bootstrap.py)
10. OOS half-panel split: **PF ratio (H1/H2) ∈ [0.7, 1.3]**
11. OOS **MFE/MAE asymmetry ratio > 2.0** (long-only structural support)
12. OOS daily Net P&L Pearson correlation with Gold v5.5 (zero-fill aligned window) **≤ 0.10** (i.e. **≤ X′**)

**FALSIFIED if ANY of:**

- Audit hooks **1–5** fail.
- Standalone gate **6, 7, 8, 9,** or **10** fails.
- Correlation gate **12** fails (ρ **>** 0.10).
- MFE/MAE asymmetry falsifies long-only **and** no short-mirror dispositioned.
- Catastrophic Path B procedural failure: OOS run observed **before** `train_selection_committed_utc`.

**AMBIGUOUS if:**

- Correlation gate in **(0.10, 0.15]** AND all standalone gates pass.
- Pre-flight infrastructure issue mid-run compromises OOS integrity → close **AMBIGUOUS**, fix infra, **new Pre-Q** if methodology must change.

---

## §15 — Pre-flight checklist (before TV operation)

LOCK is a methodology event. Infrastructure readiness is separate. Complete **after** LOCK commit and **before** train TV sessions:

### Mechanical Cursor items

- [x] Commit `Guardian_*_13fad*.csv` (Gold v5.5 comparator) to `data/tv_exports/pepperstone/`
- [x] Run `python scripts/check_data_manifests.py --regenerate` in same commit as CSV bytes
- [x] Verify `grep e38e8fe8 data/tv_exports/pepperstone/SHA256SUMS` matches
- [x] Populate `scripts/wfo/examples/grid.json` with §12 (LOCK commit)
- [x] Populate `scripts/wfo/examples/fold_spec.json` with §13 (LOCK commit)
- [x] Record `grid_hash` = `a8fdd34e800f312e6c064a595ee9ae3565472d0da0a0990348e07d28076f85b1` in §11
- [x] Record `fold_spec_hash` = `5591f024515f422548bf9e60a7f23225e559a05346e8911e6397346acad6673e` in §11
- [ ] Verify `python scripts/wfo/run_path_b.py init-run ...` produces valid `run_manifest.json` referencing these hashes

### Adversarial OOS-guard tests (~30 min)

Execute and record outcomes in [`docs/spec/wfo-runner-v0-adversarial-tests.md`](../spec/wfo-runner-v0-adversarial-tests.md).

- [ ] Scenario 1: wrong OOS basename → `assert_oos_matches_lock` raises
- [ ] Scenario 2: OOS `mtime` predates commit → `audit_path_b_ordering.py` FAIL
- [ ] Scenario 3: post-hoc lock recreation → distinguishable FAIL mode

### Conceptual sanity

- [ ] §12 grid: v1.5 hint at **(ema_slow=395, stop_atr=1.4, tp_atr=33, session=NY_Extended)** appears in Cartesian product
- [ ] v5.5 reference at **(385, 1.55, 29, NY_Extended)** appears in product
- [ ] §13 OOS starts **2025-05-11** — confirm no live Silver execution contaminates this **pure backtest** window
- [ ] Spot-check Pepperstone TV: XAGUSD 15m availability **2022-01-11 → 2026-04-20** (or longer)

### Acceptance battery

- [ ] `python -m pytest tests/ -q` — baseline preserved (140+ pass pattern)
- [ ] `python scripts/wfo/acceptance_silver.py` with `Q_CORR_SILVER_TV_CSV` set — §7.2 Silver refs (238 / 1.613 / 11.34% / 11.52%)
- [ ] `lib/correlation.py` anchor ρ_DJNAS ≈ **0.0217 ± 0.001** on canonical DJ30/NAS pair
- [ ] `lib/regime_bootstrap.py` Silver bootstrap p05 ≈ **1.05 ± 0.02** when Silver CSV supplied

If any item fails, halt. If the fix changes methodology (gates/grid), open **Q-CORR-1.3** — do not amend Q-CORR-1.2 mid-flight.

---

## §16 — TV operation workflow (Joshua reference)

1. **Train sweep (sessions):** set TV inputs per Cartesian row from §12; `startDate`/`endDate` = §13 train window; export CSV per naming convention (`Silver_e{ema}_sl{...}_tp{...}_{session}_train.csv`); ingest via planned `run_path_b.py ingest` (or batch).
2. **Train selection:** `run_path_b.py select --fold=1` (when implemented) → `train_selection_lock.json` + `train_selection_committed_utc`; objective: **max PF** s.t. **{DD ≤ 8%, WR ≥ 15%, trades ≥ 50}**; tie-break: lower DD → smaller |WR−20%| → alphabetical config id; **commit lock to git before OOS export.**
3. **OOS:** selected config only; OOS window §13; filename `..._oos.csv`; ingest with `assert_oos_matches_lock`.
4. **Disposition:** `emit-reports` + `audit_path_b_ordering.py`; apply **§14** → RESOLVED / FALSIFIED / AMBIGUOUS.

---

## §17 — Closure actions on disposition

**If RESOLVED:** belt update scoped to Gold/Silver pair only; separate lock brief for portfolio promotion; optional Q-CORR-1.3 for optimization; append hint note to `docs/notes/q-corr-1-hint-log.md` (create file on first entry if missing).

**If FALSIFIED:** append one-line row to `docs/rejected_candidates.md` (create on first entry if missing); do not open Q-CORR-1.3 for a new grid without new mechanism evidence; Q-CORR-1 instrument-tightness conclusion stands.

**If AMBIGUOUS:** document reasoning and next-step decision (often new Pre-Q or defer).

---

## §18 — Lock history

- **2026-05-12:** Pre-Q drafted.
- **2026-05-13:** Phase 1 path analysis; Joshua accepted (Coarse, Path B).
- **2026-05-13:** Path B shell + `lib/correlation` + `lib/regime_bootstrap` + tests landed in repo.
- **2026-05-13:** **LOCKED** — fold spec single split 40mo/12mo; 4-dim Cartesian **250** configs; WR ≥15% floor; X′ = 0.10; §14 gates frozen; `grid_hash` / `fold_spec_hash` pinned in §11.

---

## §19 — Verification at LOCK commit

```bash
git log --follow -n 5 -- docs/briefs/Q-CORR-1.2-guardian-family-silver-wfo.md

grep "LOCKED" docs/briefs/Q-CORR-1.2-guardian-family-silver-wfo.md

grep "a8fdd34e800f312e6c064a595ee9ae3565472d0da0a0990348e07d28076f85b1" docs/briefs/Q-CORR-1.2-guardian-family-silver-wfo.md

grep "5591f024515f422548bf9e60a7f23225e559a05346e8911e6397346acad6673e" docs/briefs/Q-CORR-1.2-guardian-family-silver-wfo.md

grep e38e8fe8 data/tv_exports/pepperstone/SHA256SUMS

python scripts/wfo/grid_hash.py scripts/wfo/examples/grid.json
python scripts/wfo/grid_hash.py scripts/wfo/examples/fold_spec.json
```

Pre-flight §15 items are **not** part of LOCK verification — they run between LOCK and run-start.
