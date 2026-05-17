# ADR 2026-05-16 — Fixture-test requirement for analysis scripts producing brief evidence

**Status:** LOCKED 2026-05-16
**Authored:** 2026-05-16
**Author:** claude.ai (Tech Advisor)
**Lock owner:** Joshua

## §0 Rule 0 reads

Production files verified before authoring (verification timestamp: 2026-05-16):

- `tv_mt5_pnl_reconciliation.py` — pilot/anchor; defines `compute_pnl` (line 54),
  `compute_pnl_tv_buggy` (line 76; encodes the JPY 153× defect by omitting the
  exit-price divide on <30-day holds), `is_tv_short_horizon` (line 49),
  `USDJPY_CONTRACT_SIZE = 100_000` (line 20),
  `TV_SHORT_HORIZON_MAX_DAYS = 30` (line 22). Last
  `git log -1 -- tv_mt5_pnl_reconciliation.py`
  = `8e2a2d6 2026-05-16 23:25:25 -0400`.
- `tests/test_tv_mt5_pnl_reconciliation.py` — pilot test structure being
  templated for retrofit; three tests (parametrized fixtures, 30-day boundary,
  deliberate-regression). Last
  `git log -1 -- tests/test_tv_mt5_pnl_reconciliation.py`
  = `8e2a2d6 2026-05-16 23:25:25 -0400`.
- `tests/fixtures/usdjpy_pnl_fixtures.csv` — pilot fixture format with
  `#`-prefixed derivation comments. Last
  `git log -1 -- tests/fixtures/usdjpy_pnl_fixtures.csv`
  = `8e2a2d6 2026-05-16 23:25:25 -0400`.
- `CLAUDE.md` line 91 — Rule 0 doctrine reference + pointer to canonical text.
  Last `git log -1 -- CLAUDE.md` = `51005fc 2026-05-10 17:02:32 -0400`.
- `docs/rule_0.md` — canonical Rule 0 text being extended by §2 of this ADR.
  Last `git log -1 -- docs/rule_0.md` = `8f84060 2026-05-07 16:31:57 -0400`.
- `docs/audits/2026-05-16-inqhiori-programme-audit.md` — load-bearing audit
  whose Gap 1 verdict gates this ADR. Last
  `git log -1 -- docs/audits/2026-05-16-inqhiori-programme-audit.md`
  = `746d083 2026-05-16 23:51:40 -0400`.
- `docs/methodology/lessons/methodology_lessons.md` — F-class extension and
  F-1 seed entry land in the same commit as this ADR.
- `programme-audit` SKILL — audit instrument; lives in the `anthropic-skills`
  marketplace plugin (not in local `~/.claude/skills/` tree), so no
  repo-`git log` anchor is available. Pinned by plugin version
  (2026-05-13 lock as referenced in the audit note).

## §1 Context

The 2026-05-16 INQHIORI programme audit
(`docs/audits/2026-05-16-inqhiori-programme-audit.md`, commit `746d083`)
returned a split verdict on a proposed methodology extension. Gap 1 — fixture
tests for analysis scripts whose output enters a brief — cleared as
engineering hygiene on the Q-MT5-TV defect anchor (TV <30-day JPY ~153× P&L
inflation; specific anchor sufficient under the audit's hygiene-not-methodology
framing). Gap 2 — executable verdict assertions as INQHIORI methodology —
did not clear the pre-registered 3-of-6 falsifier (2-of-6,
ambiguous-leaning-rejected).

This ADR locks Gap 1 only. Methodology layer (INQHIORI SKILL.md) is not
modified.

Connects to: Rule 0 (production reads before brief authoring), CLAUDE.md
audit-first discipline, code-defect-debugging skill (JPY 153× canonical
anchor), brief-authoring §0 discipline check, F-1 lesson-registry entry
(retroactive seed for the JPY 153× defect).

## §2 Decision

Any analysis script whose output is cited as evidence in a brief's §3 or §4
must have at least one fixture test in `tests/` asserting an anchor
invariant. Pytest is the tooling. Strict scope: only scripts whose output
enters a brief, not all of `multi_firm_operations/`. Retrofit-first for
scripts already producing brief evidence; author-time gate going forward.

**Rule 0 extension (sub-clause):** When §0 of a brief lists a script as a
production read, the brief author verifies that script has a fixture test
against its anchor invariant. If absent, the brief is blocked until the test
is authored. This extends Rule 0 from "production code read" to "production
code read AND fixture-tested where output is load-bearing." The mechanical
check is `scripts/check_brief_evidence_coverage.py`.

## §3 Consequences

**Positive.** A defect of the JPY 153× class produces a failing test before
its corrupted output enters a brief. Brief §3/§4 evidence has a mechanical
correctness anchor independent of authorial judgment. §10 audit hooks gain a
runnable check (grep for cited scripts, verify each has ≥1 fixture test).
F-class lesson registry accumulates dated counterfactual entries; promotion
criteria mirror M-class.

**Negative.** Retrofit inventory (Hook 1 run at lock time, 2026-05-16):
5 distinct scripts cited across 3 briefs without fixture coverage —
`scripts/lock_event_hook.py`, `verify_lock_anchors.py`,
`scripts/fetch_oanda_bars.py`, `firm_rules.py`, `accounts.py`. Each retrofit
takes ~30–60 min (fixture design + test authoring + first-run verification).
One-time cost; ongoing cost is the author-time gate adding ~15 min per new
analysis script. Hook 1 exit status remains 1 until retrofit completes —
that exit code IS the canonical retrofit inventory.

**Methodology layer is NOT modified.** This ADR is engineering hygiene.
INQHIORI's hard core (falsifiable-H gate to investigation) remains textual
per the 2026-05-16 audit verdict. If Gap 2 re-test (target 2026-08-15 or
next methodology audit) clears the falsifier, a separate ADR will codify
executable verdict assertions.

## §4 Falsifiable claim

**Hypothesis.** Fixture tests on brief-evidence scripts catch ≥1 defect that
would have corrupted a brief before the brief is authored, within 6 months
of adoption.

**Falsified if.** 6 months pass (target: 2026-11-16), no fixture test has
failed and caught a real defect, AND no false-positive defects have been
caught by alternative means (CC code review, ad-hoc inspection) that the
fixture suite missed. In that case, the discipline is ceremony and the ADR
is revoked.

**Confirmed if.** ≥1 fixture test fails on a real defect within the window
(captured as F-N entry in the lessons registry), OR (weaker) the suite is
referenced in ≥3 brief §0 verifications and catches no defects only because
no defects occurred. The strong form is preferred.

## §5 Forbidden moves

Genuinely tempting alternatives that this ADR rules out:

- **Broad scope** — testing all of `multi_firm_operations/`. Tempting
  because it feels more thorough. Rejected: the audit verdict only licensed
  brief-evidence scripts. Scope creep would expand engineering work beyond
  what the falsifier justified.
- **Methodology codification** — adding fixture-test requirement to INQHIORI
  SKILL.md. Tempting because it elevates the rule. Rejected: this is
  engineering hygiene, not an epistemic move. The 2026-05-15 forward-asymmetry
  note (methodology refinement at 0.1pp scale while execution leakage runs
  ~50%) makes methodology expansion a degeneration risk.
- **Test-driven authoring** — requiring test before script. Tempting in
  principle. Rejected for retrofit phase: existing scripts get tests before
  next brief cites them, not pre-emptively. Going-forward author-time gate is
  the lighter discipline that earns its weight.
- **Skipping the pilot** — retrofitting all scripts in one CC spawn.
  Rejected: CC-handoff hygiene (2026-05-15 standing rule) requires dry-run on
  local snapshot for ≥3 mechanical edits in same family. Pilot establishes
  the pattern; retrofit follows.

## §6 Gate / closure criteria

This ADR is **REVOKED** if §4 falsification triggers (6mo, no caught defect,
no missed defects).
This ADR is **CONFIRMED** at 6mo review if §4 strong form holds (≥1 real
defect caught and entered in registry as F-N).
This ADR is **AMBIGUOUS** if 6mo passes with no fixture failures AND no
independent defect-catching evidence either way. Re-test condition: extend
window 6mo, document explicitly, do not let it drift to "we'll know more
later."

## §10 Audit hooks (runnable at next cycle)

```bash
# Hook 1: every .py path cited in any brief §0 block must have a fixture test.
# Form-agnostic — extracts paths from §0 sections regardless of citation form.
python scripts/check_brief_evidence_coverage.py

# Hook 2: fixture-test suite runs green.
pytest tests/ -v

# Hook 3: count fixture-caught defects via lessons registry (F-class).
# Note: F-N entries use H2 heading per registry format spec (matches M-N convention).
grep -c '^## F-' docs/methodology/lessons/methodology_lessons.md
```

Programme-audit §10 incorporates these hooks at next methodology cadence
(2026-08-15 or triggered).

## Verification block

- [x] §0 populated with specific paths + commit hashes
- [x] §4 falsifiable hypothesis stated with binary outcome
- [x] §5 forbidden moves are genuinely tempting, not strawmen
- [x] §6 gate criteria binary
- [x] §10 hooks runnable (Hook 1 lifted to versioned script per M-AHF; Hook 3 form-checked against H2 heading convention)
- [x] Connects to standing doctrine (Rule 0, code-defect-debugging skill, programme-audit verdict, F-1 lessons-registry seed)
- [x] No cross-layer contamination (methodology layer explicitly not modified)
