# CLAUDE.md catch-up — branch state note (2026-05-17)

**Status:** ADVISORY — no patch authored; explanation only

## What I expected to author

A standalone diff against `CLAUDE.md` patching the stale 2026-05-08-anchor allocation table (DJ30 1.00% / NAS 0.40%) up to the 2026-05-14 allocation refresh (DJ30 0.75% pyramid 500% / NAS 0.45%), so the document and `firm_rules.py` no longer disagree.

## What §0 reads actually surfaced

Verification anchors as of 2026-05-17:

```
$ git -C C:/Users/joshu/multi_firm_operations rev-parse main
8e2a2d696f4a2449ffe1b52982d2889ee644fdee
$ git -C C:/Users/joshu/multi_firm_operations rev-parse origin/main
8919b8c89ea29a76a9b0ba68901d523427c994c3
$ git -C C:/Users/joshu/multi_firm_operations show origin/main:firm_rules.py | grep _BASE_RISK
_BASE_RISK = {"guardian": 0.0034, "striker": 0.0075, "aegis": 0.0150, "striker_nas100": 0.0045}
$ git -C C:/Users/joshu/multi_firm_operations show origin/main:CLAUDE.md | grep "Striker DJ30.*DJ30 15m"
| Striker DJ30    | DJ30 15m        | **0.75%** (pyramid 500%) | v4.5 LOCKED   | ...
$ git -C C:/Users/joshu/multi_firm_operations log --oneline a16a36b -1
a16a36b feat(lock): 2026-05-14 allocation refresh — DJ30 0.75%/pyr 500%, NAS 0.45% (#83)
$ git -C C:/Users/joshu/multi_firm_operations show --name-status a16a36b | grep -E '^[AM]\s+(CLAUDE\.md|firm_rules\.py|portfolio_mc\.py|docs/adr)'
M  CLAUDE.md
A  docs/adr/2026-05-14-allocation-refresh.md
M  firm_rules.py
M  portfolio_mc.py
```

**`origin/main` is already current.** PR #83 (commit `a16a36b`, merged 2026-05-16 per the commit date — calendar-misalignment, real merge calendar-time is between 2026-05-14 allocation-refresh authoring and 2026-05-17 today) updated all four touchpoints in a single commit: `CLAUDE.md` allocation table + MC anchor block, `firm_rules.py` `_BASE_RISK` dict, `portfolio_mc.py` `ALLOCATIONS`, and added `docs/adr/2026-05-14-allocation-refresh.md` as the canonical ADR.

## What's actually stale

The local worktree branch `claude/gifted-ritchie-9da9da` was branched from `local main = 8e2a2d6`, which is **8+ commits behind `origin/main = 8919b8c`**. The "stale CLAUDE.md" I observed in the worktree is purely a branch-vintage artifact, not a doc drift on canonical main.

## Recommended action (pick one)

### Option A — Rebase the worktree branch onto origin/main (recommended)

```
$ git -C C:/Users/joshu/multi_firm_operations/.claude/worktrees/gifted-ritchie-9da9da fetch origin
$ git -C C:/Users/joshu/multi_firm_operations/.claude/worktrees/gifted-ritchie-9da9da rebase origin/main
```

After rebase, the worktree's `CLAUDE.md`, `firm_rules.py`, `portfolio_mc.py`, and `docs/adr/2026-05-14-allocation-refresh.md` automatically match `origin/main`. The two new artifacts authored this session (`docs/briefs/Q-GDN-DDcap.md`, `docs/briefs/cc_handoff_dj30_decomposition.md`, this note) replay cleanly on top — they touch only paths PR #83 did not modify.

### Option B — Fast-forward `local main` then create a fresh branch off `origin/main`

```
$ git -C C:/Users/joshu/multi_firm_operations fetch origin
$ git -C C:/Users/joshu/multi_firm_operations checkout main
$ git -C C:/Users/joshu/multi_firm_operations merge --ff-only origin/main
$ git -C C:/Users/joshu/multi_firm_operations checkout -b claude/Q-GDN-DDcap-2026-05-17
# Then copy the three new artifacts authored this session over.
```

### Option C — Author a standalone diff against the stale CLAUDE.md (only if rebase undesirable)

If for some reason the worktree branch must stay off the stale base, a CLAUDE.md catch-up patch can be derived by extracting the CLAUDE.md hunk from `a16a36b`:

```
$ git -C C:/Users/joshu/multi_firm_operations show a16a36b -- CLAUDE.md > /tmp/claudemd_2026-05-14_refresh.patch
$ git -C C:/Users/joshu/multi_firm_operations/.claude/worktrees/gifted-ritchie-9da9da apply --check /tmp/claudemd_2026-05-14_refresh.patch
```

This is **not recommended** — it duplicates work already committed on `origin/main` and risks a future merge conflict if the worktree branch is ever rebased.

## Rule 0 takeaway captured

This is a worked example of the brief-authoring §0 sub-rule "production reads BEFORE the brief, not as a Phase 1 check after." Had I authored the patch directly from the in-context CLAUDE.md (worktree state) without running `git show origin/main:CLAUDE.md`, the result would have been a redundant duplicate of work already on canonical main — exactly the kind of artifact the lesson registry warns against. The §0 read flipped the recommendation from "draft patch" to "rebase branch."

No memory entry needed (the lesson is already captured in `brief-authoring`'s SKILL.md §0 sub-rules and `feedback_brief_revision_verification` memory). This note exists as the audit trail for the catch-up task closure.
