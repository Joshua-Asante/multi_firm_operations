# Historical `dd_protection_state.json` re-evaluation — closure of #56

**Date:** 2026-05-10
**Issue:** [#56](https://github.com/Joshua-Asante/multi_firm_operations/issues/56)
**ADR anchor:** [docs/adr/2026-05-10-dd-protection-ulp-rounding.md](../adr/2026-05-10-dd-protection-ulp-rounding.md)
**Disposition:** RESOLVED — vacuous zero (no historical entries on disk)
**Author:** Claude Code (worktree `suspicious-cray-59ad14`)

---

## §0 — Rule 0 production reads

Read before authoring this brief. Paths absolute to the worktree at HEAD `3965cc8` (7 commits past PR #53 merge `6c7fa54`).

### Files read

| File | sha256 | Why |
|---|---|---|
| `dd_protection.py` | `75b3e68116412ca9aa397d73d39e39032996a7bda02faca2671c60770839e33a` | Patch site, write-time rounding, schema, state-file path resolution |
| `.gitignore` | (lines 1–5 reproduced below) | Confirm state-file tracking posture |

### Production-code anchors (verified at `3965cc8`)

- **State-file path resolver** — `dd_protection.py:61`:
  ```python
  STATE_FILE = Path(__file__).parent / "dd_protection_state.json"
  ```
  Resolves to repo-root `dd_protection_state.json`, **not** `data/dd_protection_state.json` as the issue brief assumed. Path discrepancy logged in §7.

- **Patch site (PR #53)** — `dd_protection.py:92`:
  ```python
  dd_triggered = round(dd_from_peak, 6) >= DD_TRIGGER
  ```

- **Write-time rounding** — `dd_protection.py:305` (issue brief said line 303; actual line 305):
  ```python
  "dd_from_peak": round(result["dd_from_peak"], 6),
  ```

- **Persisted schema** — `dd_protection.py:301-307`:
  ```python
  state["history"].append({
      "timestamp": datetime.now().isoformat(),
      "equity": equity,
      "peak": state["peak_equity"],
      "dd_from_peak": round(result["dd_from_peak"], 6),
      "multiplier": result["multiplier"],
  })
  ```
  Five fields per entry: `timestamp, equity, peak, dd_from_peak, multiplier`. Issue brief expected four (`equity, peak, dd_from_peak, timestamp`); `multiplier` is the additional one. Confirmed but immaterial — recompute uses raw `equity` + `peak` only and discards the logged `dd_from_peak`.

- **`DD_TRIGGER` constant** — `dd_protection.py:49` = `0.015` (current C2-relock value, 2026-05-08).

### Gitignore posture (`.gitignore:1-5`)

```
# Live trading data — never commit
accounts.json
dd_protection_state.json
data/live/*.csv
*.json.bak
```

`dd_protection_state.json` is gitignored. `git log --all --oneline -- dd_protection_state.json` returns empty — the file has never been committed in any branch or worktree.

### Existence check (recursive)

```
PS> Test-Path 'C:\Users\joshu\multi_firm_operations\dd_protection_state.json'
False

PS> Get-ChildItem -Path 'C:\Users\joshu\multi_firm_operations\' -Filter 'dd_protection_state*' -Recurse
(no output)

PS> Get-ChildItem -Path 'C:\Users\joshu\multi_firm_operations\' -Filter '*.bak' -Recurse
(no output)

PS> Test-Path 'C:\Users\joshu\multi_firm_operations\backups'
False

PS> Test-Path 'C:\Users\joshu\multi_firm_operations\data\backups'
False
```

No `dd_protection_state.json` exists anywhere under the repo tree — neither in the worktree, the main checkout, nor any sibling worktree. No `.bak` siblings. No `backups/` or `data/backups/` directories.

### Pre-flight checks (per §6 of issue spec)

| Check | Status |
|---|---|
| `git status` clean | ✓ |
| HEAD at or past PR #53 merge | ✓ — HEAD `3965cc8` is 7 commits past `6c7fa54` |
| State-file path confirmed | ✓ — repo-root, not `data/` |
| Backups enumerated | ✓ — none exist |
| First 3 entries printed | N/A — file has zero entries (file does not exist) |

---

## §1 — Falsifiable hypothesis (echoed verbatim from issue spec)

> ZERO history entries flip firing-decision under post-fix rounded comparison.
>
> Falsifier: ≥1 entry where `(peak - equity) / peak >= 0.015` differs from `round((peak - equity) / peak, 6) >= 0.015`. The flip window is `raw_dd ∈ [0.0149995, 0.015)` — a 5e-7-wide band. Prior expectation: 0.

Sanity-check of flip window (Python 3.14.3, raw float64):

```
raw=0.0149990000  round6=0.0149990000  pre=False  post=False  flip=False
raw=0.0149994000  round6=0.0149990000  pre=False  post=False  flip=False
raw=0.0149995000  round6=0.0150000000  pre=False  post=True   flip=True
raw=0.0149999000  round6=0.0150000000  pre=False  post=True   flip=True
raw=0.0150000000  round6=0.0150000000  pre=True   post=True   flip=False
raw=0.0150004000  round6=0.0150000000  pre=True   post=True   flip=False
raw=0.0150006000  round6=0.0150010000  pre=True   post=True   flip=False
```

Confirms unidirectional flip band `[0.0149995, 0.015)`, width 5e-7. Post-fix is strictly more conservative; no `pre=True, post=False` flips exist (verified — zero width on that side under round-to-nearest-even at 6 dp).

---

## §2 — Method (recompute formula echoed verbatim)

For each entry across `dd_protection_state.json` + every backup enumerated:

1. Read raw `equity` and `peak`. Do NOT use the logged `dd_from_peak` — it's already rounded at line 305 and would mask the very flip we're testing for.
2. `raw_dd = (peak - equity) / peak` in float64 to match the production code path.
3. `pre_fire = raw_dd >= 0.015`
4. `post_fire = round(raw_dd, 6) >= 0.015`
5. Flag if `pre_fire != post_fire`.

---

## §3 — Inputs, environment, and recompute results

### Environment

| Item | Value |
|---|---|
| Python | 3.14.3 |
| numpy | 2.4.4 |
| HEAD | `3965cc8424f13ed8614808798cc61f1ca8f683c2` |
| Branch | `claude/suspicious-cray-59ad14` |
| Working tree | clean |

### Input files inspected (read-only)

| Path | sha256 | Entries |
|---|---|---|
| `dd_protection_state.json` | (file does not exist) | 0 |
| `dd_protection_state.json.bak` | (file does not exist) | 0 |
| `data/dd_protection_state.json` (issue-brief path; verified absent) | (file does not exist) | 0 |
| `backups/` (directory) | (does not exist) | 0 |
| `data/backups/` (directory) | (does not exist) | 0 |

### Per-file recompute totals

| File | Total entries | Flip count |
|---|---|---|
| `dd_protection_state.json` | 0 | 0 |
| (no backups exist) | 0 | 0 |
| **Total** | **0** | **0** |

### Per-flip table

(empty — no entries to evaluate)

| timestamp | equity | peak | raw_dd | pre_fire | post_fire |
|---|---|---|---|---|---|

---

## §4 — Result

**Flip count: 0** (vacuous — no historical state on disk).

The state file is gitignored and uncommitted. No `*.bak` sibling exists. No `backups/` directory exists. No prior-commit copy is reachable (the file has never been tracked). The only equity-snapshot artifact in the codebase (`dd_protection_state.json`) was never persisted in this clone or has been removed since last write.

The hypothesis "ZERO history entries flip firing-decision under post-fix rounded comparison" holds **vacuously**. The falsifier requires ≥1 entry; the input set has zero entries; the falsifier cannot fire.

---

## §5 — Gate / disposition (§5 language quoted verbatim from issue spec)

> Zero flips → close #56 with methodology lesson: "ULP fix had no historical retroactive effect on this state." Lesson registry entry.

This is the disposition. Quoted verbatim into the GH closing comment per §7 audit-hook directive.

The dual-lesson arm (≥1 flip → capture flips + Pre-Q on upstream-of-decision) is **not triggered** — flip count is 0.

The closure is informed-null, not procedural-null:

- The recompute itself is well-defined (formula in §2, environment in §3) but operates on an empty input.
- The empty input is not an oversight — it is the production posture: `dd_protection_state.json` is observability, gitignored by design (`.gitignore:3`), and either has never been generated by the operator or has been wiped since the last write.
- This means the ULP fix (PR #53) had no retroactive effect on any persisted decision-trace. The fix is purely forward-binding.

---

## §6 — Methodology lesson (registry entry)

**Lesson:** *"ULP fix had no historical retroactive effect on this state."*

**Anchor:** [#56](https://github.com/Joshua-Asante/multi_firm_operations/issues/56), 2026-05-10. Recompute over `dd_protection_state.json` + backups returned 0 entries. Hypothesis held vacuously.

**Why it's load-bearing:** `dd_protection_state.json` is a logging artifact, not a decision-binding source. The binding decision substrate for the C2 lock is `portfolio_mc.py`'s MC anchor — see [#55](https://github.com/Joshua-Asante/multi_firm_operations/issues/55), already resolved per the post-merge addendum to the ULP-rounding ADR (`portfolio_mc.py` shares the comparison logic; C2 anchor 98.09 / 0.36 / 4.73 holds at `abs=1e-4` after the fix). Historical state-file entries, even if they had flipped, would have been informational — they do not retroactively re-bind any locked decision.

**Generalization:** When auditing the historical effect of a precision-class fix to a risk-control comparison, the question to answer first is "is the artifact decision-binding or observability?" before designing the recompute. For `dd_protection_state.json` specifically: observability. For `portfolio_mc.py`'s MC anchor: decision-binding (and that's what [#55](https://github.com/Joshua-Asante/multi_firm_operations/issues/55) covered).

**Status:** CANDIDATE. Single-incident lesson with no dollar anchor (vacuous-true outcomes have no avoided-cost magnitude). Promotion to load-bearing requires either (a) recurrence on a separate risk-control fix where the same artifact-class distinction matters, or (b) a future fix where the artifact *was* decision-binding and a parallel re-evaluation moves a real dollar number.

---

## §7 — Discrepancies flagged (issue-brief vs production)

Two specifics in the issue-brief diverged from the production code at `3965cc8`. Logged for the parent's awareness; neither alters the disposition.

1. **State-file path.** Issue brief: `data/dd_protection_state.json`. Production (`dd_protection.py:61`): repo-root `dd_protection_state.json`. The issue brief's "verify actual path before assuming" sub-clause caught this — verified, corrected, both paths checked for completeness.

2. **Write-time rounding line number.** Issue brief: line 303. Production: line 305. The line numbers in this brief reference the production file at HEAD `3965cc8` (sha256 `75b3e681…`); two-line drift is consistent with the post-merge update (#60) that landed the addendum block in the file header.

Neither discrepancy was brief-precision-exceeds-grounding (Rule 0 sub-rule §1, brief-authoring trap #13) — both were resolved by the §0 read protocol exactly as written.

---

## §8 — Audit hooks

```
# Rerun this re-evaluation against any future-generated state:
$ python -c "
import json, hashlib, os, sys
from pathlib import Path
DD_TRIGGER = 0.015
state_path = Path('dd_protection_state.json')
if not state_path.exists():
    print(f'{state_path}: does not exist; vacuous-zero closure remains valid')
    sys.exit(0)
state = json.loads(state_path.read_text())
hist = state.get('history', [])
flips = []
for e in hist:
    raw = (e['peak'] - e['equity']) / e['peak'] if e['equity'] < e['peak'] else 0.0
    pre = raw >= DD_TRIGGER
    post = round(raw, 6) >= DD_TRIGGER
    if pre != post:
        flips.append((e['timestamp'], e['equity'], e['peak'], raw, pre, post))
print(f'Total entries: {len(hist)}; flips: {len(flips)}')
for f in flips: print(f)
"

# Reconfirm the gitignore posture (state file should remain uncommitted):
$ git check-ignore -v dd_protection_state.json
# Expected: .gitignore:3:dd_protection_state.json    dd_protection_state.json

# Reconfirm no backups have appeared:
$ git ls-files | grep dd_protection_state
# Expected: empty
```

---

## §9 — GH closing comment (verbatim, for paste into #56)

> **RESOLVED — vacuous zero.** Closing per §5 first-arm gate language quoted verbatim from the issue spec:
>
> > "Zero flips → close #56 with methodology lesson: 'ULP fix had no historical retroactive effect on this state.' Lesson registry entry."
>
> Recompute brief: [`docs/briefs/2026-05-10-historical-dd-reeval.md`](../briefs/2026-05-10-historical-dd-reeval.md).
>
> **Result:** Flip count 0 / 0 entries. The state file (`dd_protection_state.json`) is gitignored at `.gitignore:3`, has never been committed (`git log --all --oneline -- dd_protection_state.json` returns empty), and does not exist on disk anywhere under the repo tree (recursive `Get-ChildItem` confirmed). No `.bak` siblings. No `backups/` or `data/backups/` directories.
>
> **Disposition:** ULP fix (PR [#53](https://github.com/Joshua-Asante/multi_firm_operations/pull/53)) had no historical retroactive effect on `dd_protection_state.json`. The fix is forward-binding only.
>
> **Material falsifier note:** The decision-binding falsifier on the ULP fix is the C2 MC anchor — issue [#55](https://github.com/Joshua-Asante/multi_firm_operations/issues/55), already resolved per the [2026-05-10 post-merge addendum to the ULP-rounding ADR](../adr/2026-05-10-dd-protection-ulp-rounding.md) (anchor holds at `abs=1e-4`). The historical-state recompute closed here is informational, not decision-binding.
>
> **Path/line discrepancies** (logged in brief §7, neither alters the disposition): issue brief said `data/dd_protection_state.json`; production resolves to repo-root. Issue brief said write-time rounding at line 303; actual is line 305 (two-line drift consistent with post-merge addendum landing).

---

## §10 — Discipline checklist

- [x] §0 Rule 0 reads populated with file paths + sha256 + verification anchor (`HEAD = 3965cc8`)
- [x] §0 reads scoped per context-scope sub-rules (surrounding ±20 lines around line 92, 305; cross-ref grep on state-file existence; gitignore confirmed)
- [x] Falsifiable hypothesis stated in §1 (echoed verbatim from issue spec)
- [x] Forbidden moves preserved by adherence (no edits to `dd_protection.py` or any production state file; no use of logged `dd_from_peak`; no deletion or rewrite of history entries; no commit beyond this brief)
- [x] Gate criteria binary in §5 (zero-flip arm explicitly invoked; ≥1-flip arm explicitly not-triggered with reason)
- [x] Question names symptom (does the ULP fix retroactively change any persisted decision-trace?)
- [x] Audit hooks runnable (§8 contains executable Python + git commands)
- [x] Brief connects to standing doctrine (ADR `2026-05-10-dd-protection-ulp-rounding.md`, issue #55 cross-reference, gitignore posture)
- [x] Specifics grounded — every line number and constant traces to a §0 read against `dd_protection.py` sha256 `75b3e681…`
- [x] §5 gate language quoted verbatim into §9 GH closing comment
