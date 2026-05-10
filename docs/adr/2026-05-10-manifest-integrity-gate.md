# ADR: Vendor manifest integrity gate (pre-commit + format CI)

**Date:** 2026-05-10  
**Status:** Accepted  
**Issue:** [GH #62](https://github.com/Joshua-Asante/multi_firm_operations/issues/62)  
**Phase A anchor:** [`docs/briefs/2026-05-10-pr59-manifest-drift-rca.md`](../briefs/2026-05-10-pr59-manifest-drift-rca.md)

## Context

PR [#59](https://github.com/Joshua-Asante/multi_firm_operations/pull/59) established the public-clone posture: vendor CSVs under `data/tv_exports/`, `data/bar_data/`, and `data/external/` stay gitignored; per-directory `SHA256SUMS` files are tracked. Phase A (RCA above) found manifest vs on-disk skew in a narrow time window and concluded **H2** — on-disk rewrites between commit and later verification — with NAS100USD.csv as the conclusive missing-file case.

**Phase A H2 hypothesis (verbatim from RCA §1):**

> **H2 — on-disk rewrites in window.** Manifest correct at b71e4a4 11:12 EDT; on-disk CSVs were modified between 11:12 EDT and the spawn pre-flight ~12:10 EDT (or the sync at 12:21 EDT).

Phase A aggregate verdict (RCA §3) adopts H2 as the operational explanation for the drift pattern, with NAS100USD as decisive.

There was **no** manifest-generation script in `scripts/` at Phase A; Phase B **creates** the reproducible check/regenerate tool and wires it into git + CI at the format boundary.

## Decision

1. Add [`scripts/check_data_manifests.py`](../../scripts/check_data_manifests.py) (stdlib only): `--check` (default), `--regenerate`, `--regenerate --dry-run`, walking the four directories that hold tracked `SHA256SUMS`.
2. Add a **git-native** `pre-commit` hook (tracked template at [`scripts/githooks/pre-commit`](../../scripts/githooks/pre-commit)) installed per clone via [`scripts/install_hooks.sh`](../../scripts/install_hooks.sh) or [`scripts/install_hooks.bat`](../../scripts/install_hooks.bat). The hook runs `--check` when any staged path is under `data/tv_exports/`, `data/bar_data/`, or `data/external/`. `git commit --no-verify` remains the explicit escape hatch.
3. Add [`.github/workflows/manifest-check.yml`](../../.github/workflows/manifest-check.yml): **format-only** validation of `SHA256SUMS` lines plus enforcement that no `data/tv_exports/**/*.csv` or `data/bar_data/**/*.csv` is **tracked**. Hash equality against bytes is **local-only** — CI does not have gitignored CSVs.
4. Document the standing regen-with-data workflow in [`CLAUDE.md`](../../CLAUDE.md) and classify new paths in [`REPO_MAP.md`](../../REPO_MAP.md).
5. Graduate methodology lesson **M-9** in [`docs/methodology/lessons/methodology_lessons.md`](../methodology/lessons/methodology_lessons.md).

## Trade-offs

| Approach | Outcome |
|----------|---------|
| Hash validation in GitHub Actions | **Rejected** — vendor bytes are not in the repo; runners cannot recompute ground truth. |
| Ungitignore CSVs | **Rejected** — violates PR #59 / public-prep contract (redistribution). |
| `pre-commit` framework / husky / lefthook | **Rejected this round** — single-developer overhead; separate ADR if the project outgrows shell hooks. |
| Runtime verification in `portfolio_mc.py` / TV loaders | **Rejected** — too late, repeats work every run; integrity belongs at commit boundary. |
| Backfill “historical correct” manifest at `b71e4a4` | **Rejected** — bytes unrecoverable; reconstruction error risk. |

**Windows note:** `core.autocrlf=true` (confirmed on the authoring machine) means the checker must hash **working-tree** bytes read via `open(..., "rb")`, not git blobs — consistent with GNU `sha256sum` on the same checkout.

## Consequences

- Any normal commit that stages vendor-tree paths must pass `check_data_manifests.py --check` or the commit aborts.
- After deliberate re-exports, the operator runs `--regenerate` (dry-run first) and commits manifest updates **with** the data change.
- CI catches malformed manifest lines and accidental `git add -f` of vendor CSVs; it does **not** replace the hook.

## GH #62 closing comment (template)

Paste when merging / closing the issue:

---

**Verdict:** Phase A **H2** — manifest correct at b71e4a4 11:12 EDT; on-disk CSVs modified between 11:12 EDT and the spawn pre-flight ~12:10 EDT (RCA §1). Phase B closes the loop with a load-bearing **git pre-commit** gate + **format-only** CI.

**ADR:** [`docs/adr/2026-05-10-manifest-integrity-gate.md`](docs/adr/2026-05-10-manifest-integrity-gate.md)

**Lesson:** **M-9** — Gitignored vendor-data manifests need a local pre-commit hash gate. CI cannot replace it when the bytes aren't in the repo. Manual regen drifts silently. [`docs/methodology/lessons/methodology_lessons.md`](../methodology/lessons/methodology_lessons.md)

**NAS100USD.csv:** Tracking-only case already resolved by **93865f8** (manifest entry dropped). No further code action; if `fetch_oanda_bars.py` is run later, `--regenerate` picks up the new file.

---

## §7 Audit hooks

### Repository state at verification

```
$ git rev-parse HEAD
3965cc8424f13ed8614808798cc61f1ca8f683c2
$ python --version
Python 3.14.3
$ git config --get core.autocrlf
true
```

(Replace `HEAD` in this section with the Phase B merge commit after this ADR lands.)

### Files added or materially changed by Phase B

- `scripts/check_data_manifests.py`
- `scripts/githooks/pre-commit`
- `scripts/install_hooks.sh`
- `scripts/install_hooks.bat`
- `.github/workflows/manifest-check.yml`
- `CLAUDE.md`
- `REPO_MAP.md`
- `docs/adr/2026-05-10-manifest-integrity-gate.md` (this file)
- `docs/methodology/lessons/methodology_lessons.md` (M-9 + changelog)
- `docs/briefs/2026-05-10-pr59-manifest-drift-rca.md` (Phase A RCA committed for anchor)

### Validator output — `--check` (partial vendor tree)

This workspace has Pepperstone + OANDA panel CSVs but not `data/bar_data/*.csv` or `data/external/*.csv`. **MISSING** lines are expected until those files exist locally. On a full Joshua machine with all vendor files present, exit code is **0**.

```
$ python scripts/check_data_manifests.py
MISSING data/bar_data/US30USD.csv
MISSING data/bar_data/USDJPY.csv
MISSING data/bar_data/XAUUSD.csv
MISSING data/external/dxy.csv
MISSING data/external/us_high_impact_0830et_2022_2026.csv
Run: python scripts/check_data_manifests.py --regenerate
```
*(exit code 1)*

### Validator output — **MISMATCH** (one-byte truncate; Aegis Pepperstone)

```
$ python scripts/check_data_manifests.py
MISMATCH data/tv_exports/pepperstone/Aegis_USDJPY_v4.3_PEPPERSTONE_USDJPY_2026-04-26_0bf1b.csv manifest=1706e69f... ondisk=acf83c4b...
MISSING data/bar_data/US30USD.csv
MISSING data/bar_data/USDJPY.csv
MISSING data/bar_data/XAUUSD.csv
MISSING data/external/dxy.csv
MISSING data/external/us_high_impact_0830et_2022_2026.csv
Run: python scripts/check_data_manifests.py --regenerate
```
*(exit code 1; file restored immediately after capture)*

### Validator output — **EXTRA** (temporary duplicate CSV in `pepperstone/`)

```
$ python scripts/check_data_manifests.py
EXTRA data/tv_exports/pepperstone/_EXTRA_TEST_aegis_copy.csv
MISSING data/bar_data/US30USD.csv
MISSING data/bar_data/USDJPY.csv
MISSING data/bar_data/XAUUSD.csv
MISSING data/external/dxy.csv
MISSING data/external/us_high_impact_0830et_2022_2026.csv
Run: python scripts/check_data_manifests.py --regenerate
```
*(exit code 1; copy removed after capture)*

### Validator output — **MISSING** (OANDA Aegis CSV renamed aside)

```
$ python scripts/check_data_manifests.py
MISSING data/tv_exports/oanda/Aegis_USDJPY_v4.3_OANDA_USDJPY_2026-04-25_7ee6b.csv
MISSING data/bar_data/US30USD.csv
MISSING data/bar_data/USDJPY.csv
MISSING data/bar_data/XAUUSD.csv
MISSING data/external/dxy.csv
MISSING data/external/us_high_impact_0830et_2022_2026.csv
Run: python scripts/check_data_manifests.py --regenerate
```
*(exit code 1; file renamed back after capture)*

### `--regenerate --dry-run` (excerpt)

```
$ python scripts/check_data_manifests.py --regenerate --dry-run
--- data/tv_exports/pepperstone/SHA256SUMS (proposed) ---
1706e69fa01807741d8087c9effa704748c0ee44a87c696532f957db13acce3b *Aegis_USDJPY_v4.3_PEPPERSTONE_USDJPY_2026-04-26_0bf1b.csv
2eda8be54d4d2e4bc5a91946ab39a393b94af9877c6026cf4609d71df4d8def1 *Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-05_33781.csv
61399c52d6dc704999fe36b2d02d21b4d4e31590ddc1ba72707b2ae6f2552642 *Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv
20d71a8db9e5d613ccf585bb0c21406f5d0987832abee8dae3845d10f38b0ed3 *Striker_NAS100_v1_PEPPERSTONE_NAS100_2026-05-05_7ca6f.csv
--- data/tv_exports/oanda/SHA256SUMS (proposed) ---
[...]
--- data/bar_data/SHA256SUMS (proposed) ---
--- data/external/SHA256SUMS (proposed) ---
```
*(exit code 0; no files written)*

### Pre-commit hook smoke

With `.git/hooks/pre-commit` installed from `scripts/githooks/pre-commit`, `git add -f` on a **truncated** Pepperstone panel CSV followed by `git commit` printed the same **MISMATCH** / **MISSING** / regen hint bundle and exited **1** (commit blocked). CSV was restored to manifest hash after the test.

### Suite regression

`python -m pytest tests/ -q` — **105 passed** (2026-05-10, ~75s on authoring machine).

### CI spot-check (operator)

Per spawn §5: open a **draft PR** with a deliberately malformed `SHA256SUMS` line; confirm the `format` job fails; close the draft without merging.
