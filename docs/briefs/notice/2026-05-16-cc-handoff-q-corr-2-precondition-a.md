# CC Handoff — Q-CORR-2 pre-condition A: portfolio_mc joint-day sampling read

**Date:** 2026-05-16
**Parent:** `2026-05-16-notice-q-corr-2-pyramid-conditional-correlation.md` (§6 pre-condition A)
**Route:** Walk-away (single-shot, sealed inputs, no mid-session ping)
**Scope:** Read-only. Zero code changes. Zero commits. Single written report back.
**Expected duration:** 1 session, < 30 minutes execution.

---

## §1 Context

Q-CORR-2 is a Notice-phase observation asking whether DJ30 × NAS100 strategy-level correlation differs materially under pyramid-active conditioning. The Notice cannot transition to Pre-Q until the MC's current joint-day correlation assumption is named in writing, because the falsifier threshold depends on which branch (A1 / A2 / A3 from the Notice) the MC actually implements.

This handoff resolves exactly that: locate the joint-day sampling code in `portfolio_mc`, name the assumption, and report. Nothing else.

---

## §0 Required production reads (Rule 0)

Before §2 execution, the spawn must read and report `git log -1 -- <path>` anchor for each of:

1. **`portfolio_mc/` module root** — identify the entry point and the module containing joint return / joint-day generation.
2. **The specific function(s) that produce per-day or per-trade P&L draws across the four strategies.** Name is unknown; candidates include any of: `simulate.py`, `joint_returns.py`, `bootstrap.py`, `resample.py`, `correlation.py`, or inline logic inside the main simulator.
3. **Any config file or constants module** that names a correlation matrix, a covariance, or "independence" / "iid" flags. Candidates: `config.py`, `constants.py`, JSON/YAML files in `portfolio_mc/`.
4. **STATE.md** (repo root or `docs/`) — to confirm whether the joint-sampling design is already documented anywhere as standing methodology.

If any of the above cannot be located after `find . -name "*.py" | xargs grep -l "correlation\|covariance\|joint\|bootstrap\|resample"`, halt and return `NEEDS_CONTEXT` per §6.

---

## §0.5 Clarifying questions (halt before §2 if any are material-and-unresolved)

The spawn must read §0 first, then evaluate each of these. For any that are **material** (block the report) and **unresolved by §0 reads**, halt and return `NEEDS_CONTEXT`. For non-material or §0-resolved ones, proceed and note in the report.

- **Q1 [material]:** Does `portfolio_mc` produce P&L on a per-day basis (panel-aligned daily bars across the four strategies) or per-trade basis (each strategy's trades drawn independently from its own panel)? The "joint-day correlation" framing assumes the former. If it's the latter, "joint-day sampling" may not literally exist as a step, and the report should describe what cross-strategy coupling (if any) the per-trade draw introduces.
- **Q2 [material]:** Is there ONE simulator path or MULTIPLE (e.g., separate code paths for C0/C1/C2 dd_protection scenarios, or for different challenge phases)? If multiple, the assumption may differ across them. Report the assumption for the path that produced the **2026-05-15 FXIFY-correct lock** (99.88 / 0.12 / 4.21).
- **Q3 [non-material; proceed and note]:** If the assumption is empirical (branch A1: historical resample / bootstrap from joint panel), is the joint panel the union of dated bars across all four strategies, or strategy-by-strategy with date alignment imposed at sample time? Either is defensible; just report which.
- **Q4 [non-material; proceed and note]:** If the assumption is parametric (branch A3: copula or stress correlation), report the parameter values verbatim (e.g., correlation matrix entries, copula family name, stress multiplier).

---

## §2 Execution steps

### Step 2.1 — Locate the joint-sampling code

```
cd <repo root>
find . -path ./node_modules -prune -o -name "*.py" -print | xargs grep -l "portfolio_mc\|joint\|correlation\|covariance\|resample\|bootstrap" 2>/dev/null
```

Identify the function(s) responsible for producing per-day or per-trade P&L draws across the four strategies in a single simulated trajectory. Report:
- File path and line range
- `git log -1 -- <path>` output for each file read

### Step 2.2 — Name the assumption

Read the joint-sampling code and classify it into exactly one of three branches (or `OTHER` with explanation):

- **A1 — Empirical joint resample.** The simulator draws joint days/trades from historical panel data, preserving observed correlations by construction. Look for: `np.random.choice`, `pd.DataFrame.sample`, block bootstrap, panel-aligned date sampling.
- **A2 — Independence / iid.** The simulator draws each strategy's P&L independently from its marginal distribution. Look for: separate per-strategy random draws with no shared random index, no correlation matrix, no joint panel.
- **A3 — Parametric joint.** The simulator uses a correlation matrix, covariance, copula, or stress-correlation parameter. Look for: `np.random.multivariate_normal`, copula library imports, correlation matrix construction.

If the code combines branches (e.g., empirical marginals + parametric coupling), classify as `OTHER` and describe verbatim what's happening.

**Quote the relevant code lines in the report.** Not paraphrased — copy the actual function signature and the joint-sampling line(s) inline.

### Step 2.3 — Report empirical figures (conditional)

- **If branch A1:** report the date range of the joint panel, the resample unit (day / block / trade), and any block size if block bootstrap is in use. **Do not compute conditional correlations** — that is Inquire-phase work, out of scope here.
- **If branch A2:** confirm independence by grepping for any correlation-related variable in the simulator path; report any near-miss findings (e.g., "found a correlation matrix in `legacy_sim.py` but it's not called by the current simulator").
- **If branch A3:** report the correlation matrix or copula parameters verbatim, with file path and line number.
- **If `OTHER`:** describe.

### Step 2.4 — Sanity-check against the 2026-05-15 lock

The 2026-05-15 FXIFY-correct lock is 99.88 / 0.12 / 4.21 / days 21/99/156. The report should confirm (one line) that the joint-sampling code path identified in §2.1 is the one that produced this lock — by either checking that a recent commit referencing the lock touched this code, or that the simulator entry point used in the lock workflow reaches this function.

If the lock came from a different code path than the one read, that is a material finding and the report should state it clearly: which path is canonical for current MC, and which path was read.

---

## §3 Deliverable

A single markdown file: `docs/briefs/notice/q-corr-2-precondition-a-report.md`

Structure:
```
# Q-CORR-2 pre-condition A — portfolio_mc joint-day sampling report
Date: 2026-05-16
Spawn: <CC session id>
Parent: 2026-05-16-notice-q-corr-2-pyramid-conditional-correlation.md

## §1 Files read (with git anchors)
## §2 Assumption branch (A1 / A2 / A3 / OTHER)
## §3 Code excerpt (verbatim)
## §4 Empirical figures (conditional on branch)
## §5 Sanity check against 2026-05-15 lock
## §6 Status (DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED)
## §7 Concerns (if DONE_WITH_CONCERNS) or sub-case (if BLOCKED)
```

No commit yet — write the file, leave uncommitted, return status. Parent session decides whether to commit after review.

---

## §4 Forbidden moves (genuinely tempting; not strawmen)

1. **Computing conditional correlations.** That is Inquire-phase work. The Notice has not transitioned to Pre-Q. If the spawn computes anything beyond what's already in the panel, the §0.5 ambiguity about subset definition (pyramid-active B1/B2/B3/B4 from the Notice) gets pre-empted by whichever choice the spawn makes silently. Out of scope. Hard line.
2. **Proposing what the Pre-Q falsifier should look like.** Same reason. Parent-session work.
3. **Refactoring "while I'm in here."** If the joint-sampling code is messy, ugly, or has TODOs, do not touch it. Report what's there, not what it could be.
4. **Suggesting MC re-runs or sensitivity analyses.** Out of scope. The report names the current assumption; downstream sensitivity work is Inquire-phase.
5. **Editing the parent Notice.** If a §0.5 ambiguity surfaces that the Notice didn't anticipate, surface it in the report's §7 Concerns — do not edit `2026-05-16-notice-q-corr-2-pyramid-conditional-correlation.md`. Notice edits are parent-session work.

---

## §5 Falsifiable hypothesis

N/A — this is a read-only reporting task, not an Inquire-phase investigation. The Pre-Q drafted **after** this report is the artifact that will carry the falsifier.

---

## §6 Reporting taxonomy

Return one of:

- **DONE** — joint-sampling code located, assumption named, report file written. Pre-condition A resolved.
- **DONE_WITH_CONCERNS** — report written but one or more of: §0.5 Q1 or Q2 resolved in a way the parent should know about (e.g., multiple simulator paths with conflicting assumptions), Step 2.4 sanity check failed (read code path is not the one that produced the lock), assumption is `OTHER` and ambiguous. List concerns in §7 of the report.
- **NEEDS_CONTEXT** — §0 reads cannot complete because:
  - **context sub-case:** missing file pointers, ambiguous module structure, or repo state unclear. Re-dispatch viable with more pointers from parent.
  - **capability sub-case:** code requires interactive exploration beyond static read (e.g., need to run the simulator to trace which path executes). Re-dispatch with stronger model or human pairing.
- **BLOCKED** — one of:
  - **context-problem:** as above but more severe — fundamental missing context that the parent must supply before any read is possible.
  - **scope-problem:** the joint-sampling code is too entangled with the rest of the simulator to be reported in isolation. Decompose: parent should split into "read the entry point" / "read the per-strategy marginal sampling" / "read the cross-strategy coupling" as separate handoffs.
  - **plan-itself-wrong:** the framing in this handoff (A1/A2/A3 branching) does not match what `portfolio_mc` actually does. Escalate to parent for re-framing.

Status verdict is mandatory. No "FAILED" / "COMPLETE" — use the four-state taxonomy.

---

## §7 Parent-session review (spec-compliance + quality, two passes)

Parent (claude.ai or Joshua) reviews the returned report in two distinct passes:

**Pass 1 — spec compliance (claude.ai or Joshua):**
- Did the spawn read EXACTLY the files §0 requested, plus those needed to resolve §0.5? No "while-I-was-in-there" reads?
- Did the spawn compute anything beyond Step 2.3? (Forbidden move #1 / #2 audit.)
- Did the spawn edit anything? (Read-only check: `git status` should be clean except for the new report file.)
- Did the spawn refactor or propose changes to existing code? (Forbidden move #3.)

**Pass 2 — quality (claude.ai or Joshua):**
- Is the assumption-branch classification correct given the quoted code?
- Is the §2.4 sanity check honest — did the spawn verify the read path is the one that produced the lock, or punt?
- Are the §7 concerns (if any) load-bearing or ceremonial?

**Final consolidated read:** N/A. §2 has only one functional step (the others are read/quote/classify supports). No multi-step integration to check.

---

## §8 Audit hooks (mechanical)

- After the spawn returns: `git status` → should show one new untracked file at `docs/briefs/notice/q-corr-2-precondition-a-report.md`. Any other change is a forbidden-move violation.
- `grep -n "Q-CORR-2" docs/briefs/notice/q-corr-2-precondition-a-report.md` → should reference the parent Notice.
- After parent review, if `DONE`: the parent Notice's §6 pre-condition A becomes resolved, and Pre-Q drafting can begin.

---

## §9 Disposition

| Item | Status |
|---|---|
| §0 reads identified | YES (4 candidate read targets) |
| §0.5 ambiguities surfaced | YES (4 questions, 2 material) |
| §2 steps specified | YES (4 steps, narrow scope) |
| §5 forbidden moves explicit | YES (5 genuinely tempting moves) |
| §6 reporting taxonomy applied | YES (4-state, with BLOCKED sub-cases) |
| §7 spec-compliance pass distinct from quality | YES |
| Final consolidated read required | N/A (single-step task) |

**Spawn instruction:** begin at §0. Read all four targets, surface `git log -1` anchors, then evaluate §0.5 before any §2 execution.
