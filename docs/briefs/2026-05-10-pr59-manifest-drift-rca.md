# Phase A RCA — PR #59 manifest drift

**Anchor:** GH [#62](https://github.com/Joshua-Asante/multi_firm_operations/issues/62) (op-risk).
PR [#59](https://github.com/Joshua-Asante/multi_firm_operations/pull/59) at b71e4a4 introduced SHA256SUMS tracking; Q-MCFP-1 §2.1 pre-flight at ~12:10 EDT on 2026-05-10 found 5/8 files mismatched; sync commit 93865f8 at 12:21 EDT updated manifests to current on-disk reality.

**Phase A scope:** read-only investigation. Verdict per drifted file + aggregate. No CSV modifications, no SHA256SUMS modifications, no script modifications. Phase B handles audit-hook installation; this brief feeds its scoping.

---

## §0 Rule-0 reads (production, verified 2026-05-10)

| Path | git anchor | Notes |
|---|---|---|
| `data/tv_exports/pepperstone/SHA256SUMS` | last touched 93865f8 (sync) | 4 entries, current canonical |
| `data/tv_exports/oanda/SHA256SUMS` | last touched 93865f8 (sync) | 4 entries, current canonical |
| `data/bar_data/SHA256SUMS` | last touched 93865f8 (sync) | 3 entries (NAS100USD removed by sync) |
| `data/external/SHA256SUMS` | last touched a6bd9848/b71e4a4 | 2 entries, no drift, no further touches |
| `scripts/lock_event_hook.py` | b9... (pre-existing) | NOT a manifest-gen script — fires `verify_lock_anchors.py` on locked-file edits only |
| `scripts/fetch_oanda_bars.py` | post-f1bdc50 | Only code-level consumer of `data/bar_data/NAS100USD.csv` |

**Manifest-generation script: NONE FOUND.** `scripts/` contains no `*manifest*`, `*sha256*`, or `*hash*` filename. PR #59's SHA256SUMS files were authored by hand or ad-hoc shell (e.g., `sha256sum *.csv > SHA256SUMS`). No reproducible artifact in the repo encodes the manifest-creation procedure. This is itself evidence about the defect surface — Phase B cannot patch a script that doesn't exist; it must create one.

**Pre-flight (§6 verbatim):**
- `git status` clean ✓
- HEAD: `3965cc8424f13ed8614808798cc61f1ca8f683c2`
- `git rev-parse b71e4a4` → `b71e4a40ba4c7ecaba7a0610c0c64cd6bc2efdb7` ✓

**Drift table from GH #62 (verbatim):**

| Panel | File | Main repo hash | Worktree manifest | Status |
|---|---|---|---|---|
| Pepperstone | Aegis_USDJPY_v4.3 | `1706e69f` | `1706e69f` | match |
| Pepperstone | Guardian_Gold_v5.5 | `2eda8be5` | `e38e8fe8` | **drift** |
| Pepperstone | Striker_DJ30_v4.5 | `61399c52` | `d83a81d8` | **drift** |
| Pepperstone | Striker_NAS100_v1 | `20d71a8d` | `05eb6ae8` | **drift** |
| OANDA | Aegis_USDJPY_v4.3 | `8ab0809c` | `8ab0809c` | match |
| OANDA | Guardian_Gold_v5.5 | `a25f2663` | `a25f2663` | match |
| OANDA | Striker_DJ30_v4.4 | `395ac324` | `395ac324` | match |
| OANDA | Striker_NAS100_v1 | `65bbc31a` | `a347143e` | **drift** |
| bar_data | US30USD | `723a354b` | `723a354b` | match |
| bar_data | USDJPY | `678c846c` | `678c846c` | match |
| bar_data | XAUUSD | `0d8aaa40` | `0d8aaa40` | match |
| bar_data | NAS100USD | **(missing)** | `c9611b33` | **missing** |

---

## §1 Falsifiable hypotheses (recap)

- **H1 — script bug.** Manifest at b71e4a4 disagreed with on-disk reality at b71e4a4 (e.g., generated against a different tree, copy-pasted from a stale source).
- **H2 — on-disk rewrites in window.** Manifest correct at b71e4a4 11:12 EDT; on-disk CSVs were modified between 11:12 EDT and the spawn pre-flight ~12:10 EDT (or the sync at 12:21 EDT).
- **H3 — both.**

---

## §2 Per-file forensic table

CSV files are gitignored (PR #59 contract). Bytes at b71e4a4 are NOT in git history; the only ground truth is (a) the manifest committed at b71e4a4, (b) the manifest committed at 93865f8/HEAD, (c) current on-disk hashes (recomputed, this run), (d) git log for the manifest itself, (e) the unique case of `data/bar_data/NAS100USD.csv` which WAS tracked at f1bdc50 then untracked at b71e4a4 via `git rm --cached`.

Times in this brief are EDT (commit timestamps recorded as `-0400`); the "12:10Z" in #62 is read as 12:10 local (EDT), placing it between PR #59 (11:12 EDT) and sync (12:21 EDT).

| File | Manifest @ b71e4a4 | Manifest @ HEAD | Recomputed on-disk now | mtime (EDT) | Verdict |
|---|---|---|---|---|---|
| Pepperstone Guardian_Gold_v5.5_..._33781.csv | `e38e8fe8...` | `2eda8be5...` | `2eda8be5...` ✓ | 2026-05-10 15:25:35 | H2-leaning |
| Pepperstone Striker_DJ30_v4.5_..._12175.csv | `d83a81d8...` | `61399c52...` | `61399c52...` ✓ | 2026-05-10 15:25:35 | H2-leaning |
| Pepperstone Striker_NAS100_v1_..._7ca6f.csv | `05eb6ae8...` | `20d71a8d...` | `20d71a8d...` ✓ | 2026-05-10 15:25:35 | H2-leaning |
| OANDA Striker_NAS100_v1_..._74d8e.csv | `a347143e...` | `65bbc31a...` | `65bbc31a...` ✓ | 2026-05-10 15:23:43 | H2-leaning |
| bar_data NAS100USD.csv | `c9611b33...` | (entry removed by sync) | (file MISSING) | n/a | **H2 confirmed** |
| Pepperstone Aegis_..._0bf1b.csv (control) | `1706e69f...` | `1706e69f...` | `1706e69f...` ✓ | 2026-05-10 15:25:34 | no drift |
| OANDA Aegis_..._7ee6b.csv (control) | `8ab0809c...` | `8ab0809c...` | `8ab0809c...` ✓ | 2026-05-10 15:25:34 | no drift |
| OANDA Guardian_..._9ae1f.csv (control) | `a25f2663...` | `a25f2663...` | `a25f2663...` ✓ | 2026-05-10 15:25:34 | no drift |
| OANDA DJ30_v4.4_..._86e9d.csv (control) | `395ac324...` | `395ac324...` | `395ac324...` ✓ | 2026-05-10 15:25:34 | no drift |

### NAS100USD.csv — H2 confirmed (the decisive case)

- **f1bdc50** (2026-05-08 17:11 EDT) added `data/bar_data/NAS100USD.csv` to git (blob hash `d6062452...`, 6,854,765 bytes LF). On-disk with `core.autocrlf=true` it would have been CRLF (different SHA256 than the blob).
- **32c0c86** (2026-05-08 17:23 EDT) "closed-investigation data file cleanup" did NOT delete NAS100USD.csv (file list checked: USOIL, audnzd, EURUSD H-PDSB, GBPUSD H-LORB, USDCHF only).
- **b71e4a4** (2026-05-10 11:12 EDT) untracked NAS100USD.csv via `git rm --cached`; file preserved on disk. Manifest captured `c9611b33...` — necessarily computed from a real on-disk file at that moment.
- **93865f8** (2026-05-10 12:21 EDT) removed the NAS100USD entry from `data/bar_data/SHA256SUMS` (commit diff: 1 line removed) because the file was no longer on disk by then.
- **Now**: file missing, no entry in manifest.

The file existed at b71e4a4 → was deleted before the sync 1h09min later. **H2** for this file is conclusive.

### Four panel CSVs — H2-leaning, AMBIGUOUS

The on-disk bytes at b71e4a4 are unrecoverable (not in git, no backup). Two arguments narrow the verdict toward H2 without closing it:

1. **Pattern.** All four drifted entries are recent locks (Guardian v5.5 Pep, DJ30 v4.5 Pep, NAS v1 Pep, NAS v1 OANDA). All four non-drifted files are older (Aegis v4.3 Pep 04-26; Aegis v4.3 / Guardian v5.5 / DJ30 v4.4 OANDA all 04-25). Drift correlates with "recently locked / actively iterated panel," not with broker or with file naming. This is the pattern of a re-export campaign that updated the recently-locked strategies and skipped the older ones.
2. **Workflow inference.** With no manifest script in the repo, the natural authoring workflow is `sha256sum data/<dir>/*.csv > data/<dir>/SHA256SUMS && git add ... && git commit`. Under that workflow, the manifest at commit time = on-disk reality at commit time. To overturn that null, we'd need affirmative evidence that the manifest was generated from a different tree (a different worktree, a stale paste, etc.). No such evidence found.
3. **a6bd9848 → b71e4a4 stability.** The two same-day public-prep commits (11:08 → 11:12 EDT) carry identical Pepperstone and OANDA manifests. No re-exports happened in that 4-minute window. This narrows the "rewrite window" to 11:12 EDT (PR #59) → 12:21 EDT (sync), a ~69-minute span. The matching 09206ebe-style "re-export + manifest regenerate" pattern is established Joshua workflow (see commit 2026-05-05 21:43 EDT for Guardian Pepperstone 209→201 reconcile).

What would shift this to H1: TradingView re-exports producing non-deterministic bytes for unchanged data (so 15:25 EDT touches would have differed from 12:21 EDT bytes), OR evidence Joshua had two checkouts that day. Neither is in evidence; the 15:25 EDT mtime-update on ALL Pepperstone CSVs (including non-drifted Aegis whose hash didn't change) suggests TV exports are deterministic for unchanged data. That cuts against H1.

### Manifest-script status

No script exists. `scripts/` listing: `build_us_releases.py`, `dryrun_aegis_v4_3.py`, `fetch_oanda_bars.py`, `lock_event_hook.py`, `replay_state_h5.py`. `lock_event_hook.py` (read above) is a PostToolUse hook that triggers `verify_lock_anchors.py` on edits to `firm_rules.py` / `dd_protection.py`. It does NOT touch SHA256SUMS.

There is therefore no script to re-run at b71e4a4 to test H1 directly. The brief's §2 step 5 ("Re-run script at b71e4a4") returned the absence of an artifact; that absence is itself the answer.

---

## §3 Aggregate verdict — H2 (on-disk re-exports between PR #59 and the spawn pre-flight)

**Verdict: H2.** With the caveat that for the four panel CSVs the verdict is H2-leaning rather than conclusive (bytes at b71e4a4 unrecoverable). NAS100USD.csv is conclusive H2 (file deletion in window). The pattern across all five drifts, plus the absence of a script that could plausibly mis-fire, plus the established re-export-with-regenerated-manifest workflow Joshua had used five days earlier, all point in the same direction.

**Trigger for downgrade to AMBIGUOUS:** if Phase B finds evidence of a second checkout / stale-paste / Joshua confirms he did NOT re-export in that window, then the four panel CSVs flip to H1. NAS100USD.csv stays H2 regardless.

---

## §4 Phase B recommendation feed

**Audit hook is necessary AND sufficient.** A pre-commit hook (and/or CI check) that validates SHA256SUMS against on-disk for `data/tv_exports/**` and `data/bar_data/**` catches BOTH directions of failure:
- Manifest-was-correct, on-disk-rewritten-without-re-running (the H2 mode that surfaced here).
- Manifest-was-wrong, manifest-doesn't-match-disk-at-all (the H1 mode, hypothetically).

**Phase B work — creation, not surgery:**

1. **Create `scripts/check_data_manifests.py`.** Two modes:
   - `--check` (default): exit non-zero if any tracked SHA256SUMS file disagrees with the recomputed hashes of files in its directory. Diff format human-readable. This is the validator.
   - `--regenerate`: regenerate SHA256SUMS files from current on-disk reality. Used after deliberate re-exports.
   - Walks `data/tv_exports/pepperstone/`, `data/tv_exports/oanda/`, `data/bar_data/`, `data/external/`. (Joshua to confirm directory list — these four are the ones with tracked SHA256SUMS at HEAD.)
   - Skip-if-missing semantics: a file present in manifest but absent on disk should fail loud (this would have caught NAS100USD.csv); a file present on disk but absent from manifest should also fail loud (catches "added a file but forgot to manifest it").

2. **Wire `--check` into pre-commit hook** in `.git/hooks/pre-commit` (or settings.json hook for the Claude Code workflow), filtered to runs that touch `data/tv_exports/**` or `data/bar_data/**`. Can also wire to GitHub Actions for cross-platform validation.

3. **Doc the regen workflow** in CLAUDE.md or REPO_MAP.md: "After re-exporting any panel CSV, run `python scripts/check_data_manifests.py --regenerate` and commit the manifest delta in the same commit." This makes the 09206ebe-style "Pep SHA256SUMS regenerated" inline note the standing convention.

**No script-bug surgery required** because no script exists to fix.

**Forbidden moves Phase B should NOT take** without a separate brief:
- Changing the gitignore contract for vendor data. PR #59's posture (gitignore CSVs, track manifests) is correct and not on the table.
- Adding hash verification inside `portfolio_mc.py` or `tv_export_loader.py`. The validator runs at commit time, not at MC time. MC time is too late and adds runtime cost.
- Backfilling a "historical correct" manifest at b71e4a4. The bytes are unrecoverable; attempting to reconstruct them invites reconstruction-of-reconstruction errors.

**Tracking-only NAS100USD.csv check (per spawn brief §5):** confirmed. Code-level consumers of `data/bar_data/NAS100USD.csv`:

```
$ rg -l 'NAS100USD' --type py
scripts/fetch_oanda_bars.py        # writes the file
```

Doc references (`CHANGELOG.md`, `REPO_MAP.md`, `strategies/nas/striker_nas100_CHANGELOG.md`, `docs/briefs/Q-MCFP-1/closure.md`) do not consume the file at runtime. `portfolio_mc.py` does NOT import `data/bar_data/NAS100USD.csv`. `data/tv_exports/oanda/SHA256SUMS` reference is a different file (TV-export panel, not bar-data feed).

**Action: tracking-only, deferred.** Re-running `python scripts/fetch_oanda_bars.py` would restore the file (it's a deterministic fetch from OANDA). Joshua may choose to (a) re-fetch and let Phase B's regenerator update the manifest, or (b) accept the file's absence and let the validator continue to omit it. Phase B's validator should treat the manifest as truth — if the entry is in the manifest, the file must exist; if Joshua deletes the file deliberately, he runs `--regenerate` to drop the entry. Either path is consistent.

---

## §5 Forbidden moves (this brief)

This brief was authored under §4 of the spawn brief:
- Did not modify any file in `data/tv_exports/**` or `data/bar_data/**` ✓
- Did not modify any committed SHA256SUMS ✓
- Did not modify the manifest-gen script (none exists) ✓
- Read-only against history ✓ — no worktree at b71e4a4 created (decided against because CSVs are gitignored, so a worktree at b71e4a4 would not contain them; the verification it would have performed is unrecoverable for the same reason)
- No commits ✓

---

## §6 Verdict gate

| Question | Answer |
|---|---|
| Did manifest-gen script exist at PR #59 author time? | No. `scripts/` had no manifest tool. |
| Did the manifest at b71e4a4 reflect on-disk reality at b71e4a4? | NAS100USD.csv: yes (at the time of capture). 4 panel CSVs: H2-leaning yes-then-rewritten. |
| Is the drift compatible with a partial re-export between 11:12 EDT and 12:21 EDT? | Yes. Pattern (recent locks only), workflow inference (no script means manual sha256sum), and Joshua's prior 09206ebe-style "re-export + regenerate manifest" pattern all converge. |
| Phase B fix shape | **Hook install + CREATE `scripts/check_data_manifests.py`** (validator + regenerator). No script-fix surgery (no script exists). |
| Tracking-only NAS100USD.csv: defer? | Yes. Only `scripts/fetch_oanda_bars.py` writes it; nothing consumes at runtime. |

---

## §7 Audit hooks (verbatim outputs captured this run)

Platform / Python:
```
$ python -V
Python 3.14.3
$ uname -a
MINGW64_NT-10.0-26200 SOELaboratory 3.6.3-086201ea.x86_64 2025-06-05 13:51 UTC x86_64 Msys
```

Git anchors:
```
$ git rev-parse HEAD
3965cc8424f13ed8614808798cc61f1ca8f683c2
$ git rev-parse b71e4a4
b71e4a40ba4c7ecaba7a0610c0c64cd6bc2efdb7
$ git status --short
(clean)
```

SHA256SUMS commit timeline (paths as listed):
```
$ git log --all --pretty=format:'%H %aI %s' -- data/tv_exports/pepperstone/SHA256SUMS data/tv_exports/oanda/SHA256SUMS data/bar_data/SHA256SUMS
54d228585256aea993735f828c4c4ba38ecae7d0 2026-05-10T12:58:04-04:00 Q-MCFP-1: MC precision treatment + mc_explore DELETE + boundary tests + Rule 0-T compliance (#63)
93865f86493a52de850879a2dde591c8d44eddec 2026-05-10T12:21:06-04:00 chore(data): sync SHA256 manifests to current on-disk panel files
b71e4a40ba4c7ecaba7a0610c0c64cd6bc2efdb7 2026-05-10T11:12:33-04:00 chore(public-prep): gitignore vendor data + Pine source; track SHA256 manifests (#59)
a6bd9848d2d3055f19634414da679dcfe5ee7517 2026-05-10T11:08:08-04:00 chore(public-prep): gitignore vendor data + Pine source; track SHA256 manifests
09206ebe62de35fe7d12df1659d297b23285b915 2026-05-05T21:43:52-04:00 Guardian Pepperstone re-export: 209 → 201 trades; 4-strategy MC re-anchor 97.88/0.22/4.55
4c65d296827001adf00aeaf97e52efe6a01ac7bd 2026-05-05T17:02:50-04:00 Striker NAS100 v1 add (0.40%) + DJ30 v4.4 → v4.5 migration; 4-strategy MC anchor 98.13/0.22/4.49
be7d4d12912b10d0ca76ee00f17c2b08dfb7683f 2026-04-27T18:33:31-04:00 inquire: var-alloc observables (DD-state, vol, ToD, calendar) — verdict 4A REJECTED
05297c2516e84fd7f70be047a161ff96b7f3bff7 2026-04-26T22:10:43-04:00 inquire: variable risk allocation — verdict 4A REJECTED
```

Manifest contents at b71e4a4 (unmodified copy from `git show b71e4a4:...`):
```
# pepperstone
1706e69fa01807741d8087c9effa704748c0ee44a87c696532f957db13acce3b *Aegis_USDJPY_v4.3_PEPPERSTONE_USDJPY_2026-04-26_0bf1b.csv
e38e8fe80419a286666898e8cae41a3be796277844367b7f1dfdcc3a0feba124 *Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-05_33781.csv
d83a81d81187958dc2e90006af995605d928a074369341155519cce69ccdf415 *Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv
05eb6ae8e7fded582b0e4ddcb489117ba98266b6fe7a767f7216282c51236c45 *Striker_NAS100_v1_PEPPERSTONE_NAS100_2026-05-05_7ca6f.csv

# oanda
8ab0809c7352017a055cbee22bf4d79d3fc77b02f7aa3b9740e83c05614cf4a1 *Aegis_USDJPY_v4.3_OANDA_USDJPY_2026-04-25_7ee6b.csv
a25f266312bc1c01f10f7b8ceefcbf2a0d334882403874bb573ae46ecdb96f7c *Guardian_Gold_v5.5_OANDA_XAUUSD_2026-04-25_9ae1f.csv
395ac324a99be3f693a2653cf652e483009ccf071412aaba0b2a43860415adfe *Striker_DJ30_v4.4_OANDA_US30USD_2026-04-25_86e9d.csv
a347143e3f485e5ebe92f1317c65c745bab8b81ed5b617dbb16c5326dae4464a *Striker_NAS100_v1_OANDA_NAS100USD_2026-05-08_74d8e.csv

# bar_data
c9611b3387cf36523b3fc1c72c9766213784a7cc59145f22286ee23760a231c0 *NAS100USD.csv
723a354b1b874e000b025c9537a55f57d810da684e29fce808e1148f0ee677b5 *US30USD.csv
678c846c483139e537b43a5ad9950c5fbff4d99733dc735bd564a7fd83db185e *USDJPY.csv
0d8aaa4077892805d0ecaf00f172dfb122284e104db2c0203cd2117c420facca *XAUUSD.csv
```

Recomputed on-disk hashes (this run, 2026-05-10):
```
$ sha256sum data/tv_exports/pepperstone/Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-05_33781.csv
2eda8be54d4d2e4bc5a91946ab39a393b94af9877c6026cf4609d71df4d8def1
$ sha256sum data/tv_exports/pepperstone/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv
61399c52d6dc704999fe36b2d02d21b4d4e31590ddc1ba72707b2ae6f2552642
$ sha256sum data/tv_exports/pepperstone/Striker_NAS100_v1_PEPPERSTONE_NAS100_2026-05-05_7ca6f.csv
20d71a8db9e5d613ccf585bb0c21406f5d0987832abee8dae3845d10f38b0ed3
$ sha256sum data/tv_exports/oanda/Striker_NAS100_v1_OANDA_NAS100USD_2026-05-08_74d8e.csv
65bbc31a9df6fda3097098e57b65c16ae8d7f81bc47e95686dc1573e4787f97c

# Controls (no drift, recompute confirms manifest at HEAD = on-disk):
$ sha256sum data/tv_exports/pepperstone/Aegis_USDJPY_v4.3_PEPPERSTONE_USDJPY_2026-04-26_0bf1b.csv
1706e69fa01807741d8087c9effa704748c0ee44a87c696532f957db13acce3b
$ sha256sum data/tv_exports/oanda/Aegis_USDJPY_v4.3_OANDA_USDJPY_2026-04-25_7ee6b.csv
8ab0809c7352017a055cbee22bf4d79d3fc77b02f7aa3b9740e83c05614cf4a1
$ sha256sum data/tv_exports/oanda/Guardian_Gold_v5.5_OANDA_XAUUSD_2026-04-25_9ae1f.csv
a25f266312bc1c01f10f7b8ceefcbf2a0d334882403874bb573ae46ecdb96f7c
$ sha256sum data/tv_exports/oanda/Striker_DJ30_v4.4_OANDA_US30USD_2026-04-25_86e9d.csv
395ac324a99be3f693a2653cf652e483009ccf071412aaba0b2a43860415adfe

$ stat -c '%y %s %n' data/tv_exports/pepperstone/*.csv data/tv_exports/oanda/*.csv
2026-05-10 15:25:34.882110400 -0400 29787 .../pepperstone/Aegis_USDJPY_v4.3_..._0bf1b.csv
2026-05-10 15:25:35.145010300 -0400 47714 .../pepperstone/Guardian_Gold_v5.5_..._33781.csv
2026-05-10 15:25:35.404975000 -0400 52862 .../pepperstone/Striker_DJ30_v4.5_..._12175.csv
2026-05-10 15:25:35.666384100 -0400 47104 .../pepperstone/Striker_NAS100_v1_..._7ca6f.csv
2026-05-10 15:25:34.057762800 -0400 29813 .../oanda/Aegis_USDJPY_v4.3_..._7ee6b.csv
2026-05-10 15:25:34.351518300 -0400 48823 .../oanda/Guardian_Gold_v5.5_..._9ae1f.csv
2026-05-10 15:25:34.617836100 -0400 56670 .../oanda/Striker_DJ30_v4.4_..._86e9d.csv
2026-05-10 15:23:43.082289900 -0400 49715 .../oanda/Striker_NAS100_v1_..._74d8e.csv
```

NAS100USD.csv git history (the decisive case):
```
$ git log --all --pretty=format:'%H %aI %s' -- data/bar_data/NAS100USD.csv
b71e4a40ba4c7ecaba7a0610c0c64cd6bc2efdb7 2026-05-10T11:12:33-04:00 chore(public-prep): gitignore vendor data + Pine source; track SHA256 manifests (#59)
a6bd9848d2d3055f19634414da679dcfe5ee7517 2026-05-10T11:08:08-04:00 chore(public-prep): gitignore vendor data + Pine source; track SHA256 manifests
f1bdc50bda6e3f341bce7a0757a0e1531a7bd8f1 2026-05-08T17:11:14-04:00 feat(nas100): split to strategies/nas/ + OANDA bar/panel coverage + changelogs

$ git rev-parse "f1bdc50:data/bar_data/NAS100USD.csv"  # blob hash, not on-disk SHA256
d60624523c7a45342771b6bc43fa803262d93d2b
$ git cat-file -s d6062452          # blob size in git (LF line endings)
6854765
$ git config --get core.autocrlf
true
```

Phase B audit-hook query (re-runnable later):
```
# After Phase B installs scripts/check_data_manifests.py:
$ python scripts/check_data_manifests.py --check
# Expected: zero diffs, exit 0
$ python scripts/check_data_manifests.py --regenerate --dry-run
# Expected: no changes proposed unless on-disk has drifted from manifest
```

---

## Epilogue — Phase B close-out (2026-05-10)

- **Phase B commit on `main`:** `51005fc` (rebased onto `7452e77` after `b22efab`; contains manifest gate + M-9 + ADR + RCA + CLAUDE/REPO_MAP updates). This epilogue landed in a subsequent docs-only commit on `main`.
- **Format-CI smoke (draft PR):** https://github.com/Joshua-Asante/multi_firm_operations/pull/68 — closed without merge. Deliberate-break commit: `f1f5180`. **Format job** (non-zero): https://github.com/Joshua-Asante/multi_firm_operations/actions/runs/25639640550
- **Primary clone — `pre-commit` install:** `-rwxr-xr-x 1 joshu 197609 397 May 10 17:02 /c/Users/joshu/multi_firm_operations/.git/hooks/pre-commit`
- **GH #62 — §5 verification comment:** https://github.com/Joshua-Asante/multi_firm_operations/issues/62#issuecomment-4416341978
- **Other active clones / worktrees:** single clone for hook install in this session; repeat `bash scripts/install_hooks.sh` elsewhere as needed.
