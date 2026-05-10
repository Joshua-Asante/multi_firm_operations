# Issue #54 — ULP-Precision Comparison Audit (CC Walk-away Spawn Brief)

**Status**: AUTHORED — ready for spawn.
**Date**: 2026-05-10
**Author**: claude.ai
**Target surface**: Claude Code (walk-away CLI). NOT Cursor (no production code edits in scope).
**Methodology**: INQHIORI-gated mechanical analysis, schema-locked output.
**Parent issue**: [GH #54](https://github.com/Joshua-Asante/multi_firm_operations/issues/54)
**Cluster**: doctrine proving cluster (#54–57). First artifact authored under parallel-work doctrine.
**Connects to**: PR #53 (canonical ULP fix at `dd_protection.py:90`); ADR `docs/adr/2026-05-10-dd-protection-ulp-rounding.md`; PR #52 (fxify_rule_validator.py, already-rounded, OUT of scope).

---

## §0 — Rule-0 production reads (Phase 0; halt on failure)

The spawn MUST execute these reads BEFORE Phase 1 analysis. Memory recall is forbidden as substitute.

For each file below: run `git log -1 --format="%h %ci" -- <path>` and record the hash + timestamp in §0 of the output. If any file is missing, return `BLOCKED (context-problem)`.

| File | Why it's read | Read directive |
|---|---|---|
| `dd_protection.py` | Canonical fix site (PR #53). Establishes the corrected pattern. | Read fully; locate the `round(dd_from_peak, 6)` site that was line 90 pre-fix. |
| `docs/adr/2026-05-10-dd-protection-ulp-rounding.md` | Decision rationale. Defines variable-scale precision rule (cents→2dp, ratios→6dp). | Read fully; quote the precision rule verbatim in §0 output. |
| `accounts.py` | Survey target #1 (named in #54 scope). | Read fully; index every `<float> >= <threshold>` and `<float> <= <threshold>` site. |
| `firm_rules.py` | Survey target #2. Constants AND consumers. | Read constants block and any importer in scope. |
| `portfolio_mc.py` | Survey target #3, dd_protection simulation path explicitly flagged in #54. | Read fully; particular attention to dd-related comparison logic. |
| `analysis/` (all `.py`) | Survey target #4 — "if any equity/drawdown comparisons exist." | Read each `.py`; if no equity/dd comparisons, record null finding. |
| `weekly_review_feeder/` (all `.py`) | Survey target #5 — same conditional. | Same as above. |
| `fxify_rule_validator.py` | OUT-of-scope per #54 (PR #52 already rounds money math). | DO NOT survey. Confirm exclusion in §0 output (paste line: "fxify_rule_validator.py confirmed out of scope per #54"). |

Verification anchor format for §0 output (one line per file):
```
<path>  <git-hash>  <iso-8601-timestamp>  [READ | OUT-OF-SCOPE]
```

---

## §0.5 — Pre-execution clarifications

Before Phase 1, spawn surfaces ambiguities by halting and returning `NEEDS_CONTEXT` with the specific question. Do NOT default-assume on any of these.

1. **Are there comparison sites I should ignore?** E.g., `if x >= 0:` zero-sentinels, `if i >= len(arr):` index bounds, type-tagged comparisons that are not risk-control. The expected answer: ignore non-risk-control comparisons (zero/sentinel/bound checks, loop guards, length checks). If unsure on a specific site, classify as `unclear` in the output, do NOT skip silently.
2. **Is `firm_rules.py` "constants and consumers" scope-limited to the multi_firm_operations repo, or does it extend to other repos that import from it?** Expected answer: this repo only. Cross-repo imports are out of scope.
3. **Should the survey include test files (`test_*.py`, `tests/`)?** Expected answer: no — test files don't gate live behavior. If a test asserts on a comparison expression, that is informational only, not a survey target.
4. **What constitutes a "comparison site" when the comparison is composed (e.g., `if a >= b and c <= d:`)?** Expected answer: each operator instance is one site (so the example yields 2 sites). This matters for the ≥3 threshold.

If any of (1)–(4) feel underspecified after spawn reads §0–§4, halt and ask before Phase 1.

---

## §1 — Context

PR #53 fixed an IEEE-754 ULP-noise edge case at `dd_protection.py:90`: a raw float `>=` against `DD_TRIGGER = 0.015` could fire (or fail to fire) on rounding noise alone at the boundary. Fix: `round(dd_from_peak, 6) >= DD_TRIGGER`.

The defect pattern is generic: any `<float> >= <threshold>` or `<float> <= <threshold>` where the LHS is computed from arithmetic that may introduce ULP-scale noise. #54 asks whether other sites in the repo carry the same defect.

Disposition is conditional on instance count:
- **≥3 instances** → Pre-Q gates a sweep with the variable-scale precision rule from PR #53 ADR (cents→2dp, ratios→6dp).
- **<3 instances** → fix-as-found in their respective change windows.

This brief produces the survey output that drives the disposition decision. Disposition itself is parent (claude.ai) responsibility, NOT spawn responsibility. Spawn does not propose fixes.

---

## §2 — Scope (what spawn does)

1. **Phase 0**: Execute §0 reads. Emit §0 output block.
2. **Phase 1**: Survey each in-scope file. For every `<float> >= <threshold>`, `<float> <= <threshold>`, `<float> > <threshold>`, `<float> < <threshold>` site — where LHS is computed (not literal) and RHS is a risk-control threshold — emit one row of the §8 output schema.
3. **Phase 2**: Aggregate. Total instance count. Bucket by variable type.
4. **Phase 3**: Emit §8 artifact (JSON primary + markdown table secondary). Emit §6 status return.

**Scope-creep boundary** (§7 spec-compliance check): spawn does NOT propose fixes; does NOT modify any production code; does NOT decide disposition; does NOT amend the comparison-detection rule mid-survey. If spawn finds a site that doesn't fit the rule cleanly (e.g., float vs int compare, integer thresholds, etc.), classify as `unclear` and emit; do NOT silently include or exclude.

---

## §3 — Falsifiable hypothesis

**H**: The ULP-defect pattern from `dd_protection.py:90` exists at ≥3 other risk-control comparison sites across the in-scope files.

**RESOLVED-true**: ≥3 instances counted, schema-conformant rows emitted → Pre-Q sweep is justified.
**RESOLVED-false**: 0–2 instances counted, schema-conformant rows emitted → fix-as-found is justified.
**FALSIFIED**: 0 instances and the survey was complete (all §0 files read, all bucketed) → defect is isolated to PR #53 site; close #54 with no further action.

---

## §4 — Methodology (how spawn executes)

**Phase 1 detection rule**: a site qualifies if and only if:
- The comparison operator is `>=`, `<=`, `>`, or `<`.
- LHS is a Python expression that evaluates to `float` (or `numpy.float64`) at runtime.
- LHS contains arithmetic (subtraction, division, multiplication, accumulator update) — pure variable references like `if x <= y` where both are literal-assigned floats are excluded UNLESS one was previously computed.
- RHS is a constant threshold OR a constant-like config value (a value that does not change within a single comparison frame).
- The comparison gates a risk-control decision: equity check, drawdown check, position size check, MVD check, account-state transition, etc. Loop bounds, sentinel-zero checks, and length comparisons are excluded.

**Variable-type classification** (§8 schema, `var_type` field):
- `money` → cents/dollars; recommend 2 dp.
- `ratio` → drawdown fractions, allocation fractions, percentage as float; recommend 6 dp.
- `time` → seconds, durations, timestamps; precision per use-case (note in `notes` field).
- `count` → integer-typed but in float arithmetic.
- `other` → does not fit cleanly; explain in `notes`.

**Variable-type → recommended treatment** (informational only; spawn does NOT apply):
- `money` → `round(x, 2)` per ADR `2026-05-10-dd-protection-ulp-rounding.md`.
- `ratio` → `round(x, 6)` per same ADR.
- `time` / `count` / `other` → `unclear`; flag for parent (claude.ai) decision.

**ULP-vulnerable classification** (§8 schema, `ulp_vulnerable` field):
- `yes` → LHS arithmetic includes subtraction at near-equal magnitudes (catastrophic cancellation), accumulator drift, or division producing values near a representational boundary.
- `no` → LHS arithmetic is order-preserving and bounded away from threshold by structure (rare).
- `unclear` → cannot determine without runtime context.

Default to `unclear` if uncertain. Do not over-claim `yes` or `no`.

---

## §5 — Forbidden moves

These are genuinely tempting; doctrine forbids them:

1. **Proposing patches.** Tempting because the fix pattern is obvious from PR #53. Forbidden: spawn output is survey-only; patches are Cursor's surface, gated by disposition.
2. **Modifying any production code.** Including "trivial" reformatting, import sorting, comment fixes encountered while reading. Spawn is read-only on the repo except for emitting the output artifact.
3. **Deciding disposition (≥3 vs <3) inline.** The disposition rule is parent (claude.ai) responsibility. Spawn emits the count; claude.ai applies the rule.
4. **Skipping `unclear` sites silently.** Tempting to keep the count clean. Every found site emits a row, even if classification is `unclear`.
5. **Including out-of-scope files** (e.g., `fxify_rule_validator.py`, test files) "for completeness." Out of scope means no rows emitted.
6. **Re-defining the comparison-detection rule mid-survey** to capture or exclude edge cases. If the rule is wrong, halt with `NEEDS_CONTEXT`; do not amend in flight.
7. **Reading from memory or prior CC sessions.** Every read is fresh per §0. No "I remember this file from a prior session" shortcuts.

---

## §6 — Gates and status return

Spawn returns one of:

- **`DONE`** — all §0 reads completed with anchors recorded; all in-scope files surveyed; §8 artifact emitted and schema-conformant; instance count and bucket totals included; no concerns flagged.
- **`DONE_WITH_CONCERNS`** — survey complete and artifact emitted, but spawn flagged ≥1 finding the parent should resolve before accepting (e.g., a comparison site that doesn't fit the §4 rule cleanly; a file where the read succeeded but the structure suggests the survey rule may be incomplete; a discovered import from an out-of-scope module that may itself contain risk-control logic).
- **`NEEDS_CONTEXT`** — spawn halted because §0.5 ambiguity surfaced and no default is safe. Specify which question, what context is needed, and what the spawn would do given each plausible answer.
- **`BLOCKED`** — spawn cannot complete. Sub-case required:
  - `BLOCKED (context-problem)` — file missing, repo state inconsistent, ADR not at expected path. Re-dispatch with corrected paths.
  - `BLOCKED (capability-problem)` — task exceeds spawn's analysis depth (unlikely for a syntactic survey, but reserved). Escalate to claude.ai with stronger model or human review.
  - `BLOCKED (scope-problem)` — survey scope is too large for one session (target files have ≥10× expected comparison density). Decompose by directory; re-dispatch as N smaller surveys.
  - `BLOCKED (plan-itself-wrong)` — the §4 detection rule produces nonsensical results (e.g., zero matches in `dd_protection.py` itself). Escalate to parent.

---

## §7 — Parent-session review (claude.ai, post-spawn)

When spawn returns, parent runs TWO independent review passes per brief-authoring skill discipline:

**Pass 1 — Spec compliance** (does spawn output match §1/§2/§8 EXACTLY?):
- [ ] §0 anchors recorded for every file in the scope table.
- [ ] OUT-OF-SCOPE confirmation present for `fxify_rule_validator.py`.
- [ ] No production code modified (verify via `git diff` on spawn branch).
- [ ] No fixes proposed inline.
- [ ] No disposition decision attempted by spawn.
- [ ] All schema-conformant rows.
- [ ] Bucket totals match row counts.

**Pass 2 — Quality** (is what spawn produced methodologically sound?):
- [ ] §4 detection rule applied consistently — sample 3 random rows; re-derive classification by hand; check agreement.
- [ ] `unclear` flags are genuine uncertainty, not lazy classification.
- [ ] No false negatives in spot-check: open one in-scope file not yet flagged in spawn output, confirm no obvious risk-control comparison was missed.
- [ ] Variable-type buckets are well-formed (e.g., no `money` typed as `ratio`).

Both passes pass → apply disposition (§9). Either fails → re-dispatch with correction notes; do NOT accept partial output.

---

## §8 — Output schema (locked, no post-hoc renegotiation)

Primary output: JSON file at `data/audits/issue_54_ulp_audit.json`. Secondary output: markdown table at `data/audits/issue_54_ulp_audit.md`.

JSON schema:

```json
{
  "rule0_reads": [
    {"path": "<file>", "git_hash": "<7-char>", "timestamp_iso": "<YYYY-MM-DDTHH:MM:SS>", "status": "READ | OUT-OF-SCOPE"}
  ],
  "adr_precision_rule_quote": "<verbatim quote from ADR>",
  "findings": [
    {
      "file": "<relative path>",
      "line": <int>,
      "expression": "<verbatim source line, stripped>",
      "lhs_var": "<identifier or expression>",
      "operator": ">= | <= | > | <",
      "rhs": "<threshold expression>",
      "var_type": "money | ratio | time | count | other",
      "current_treatment": "raw_float | round(x,N) | abs_diff_eps | other",
      "ulp_vulnerable": "yes | no | unclear",
      "recommended_treatment": "<from §4 mapping or 'unclear'>",
      "notes": "<optional human-read context>"
    }
  ],
  "totals": {
    "instance_count": <int>,
    "by_var_type": {"money": <int>, "ratio": <int>, "time": <int>, "count": <int>, "other": <int>},
    "by_ulp_vulnerable": {"yes": <int>, "no": <int>, "unclear": <int>}
  },
  "status_return": "DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED",
  "concerns": ["<one per concern, empty array if DONE>"],
  "blocked_subcase": "context | capability | scope | plan-wrong | null",
  "blocked_detail": "<empty if not BLOCKED>"
}
```

Markdown table is human-readable mirror, same fields (one row per finding), plus the `totals` and `status_return` blocks at top.

---

## §9 — Disposition (parent applies, post-review)

Per #54 disposition rule:
- `totals.instance_count >= 3` → claude.ai opens Pre-Q (Inquire-phase brief) at `docs/briefs/PreQ-ULP-sweep.md` to gate the sweep with PR #53 ADR's variable-scale precision rule.
- `totals.instance_count in {0, 1, 2}` → claude.ai opens fix-as-found Cursor briefs (one per site) at `docs/briefs/fix_<file>_<line>_ulp.md`.

Disposition decision recorded in #54 closure comment with link to follow-up artifact(s).

---

## §10 — Audit hooks

- **Artifact presence**: `ls data/audits/issue_54_ulp_audit.json` after spawn close. Missing = spawn did not complete; promotion gate check (1) cannot evaluate.
- **Lineage commit**: spawn commit prefix `cc-handoff: #54 ULP audit survey` per parallel-work doctrine §protocol-8. Verify with `git log --oneline | grep "cc-handoff: #54"`.
- **Schema conformance check**: parent runs `python -c "import json; json.load(open('data/audits/issue_54_ulp_audit.json'))"` and validates against §8 schema before disposition.
- **Spec-compliance + quality pass logs**: parent (claude.ai) records both review pass results in #54 thread before applying disposition.
- **Cluster post-mortem reference**: this brief and its outcome become entry #1 in `docs/methodology_audit/parallel_doctrine_cluster_001.md`.

---

## §11 — Spawn invocation

When ready, spawn with:

```
You are executing a ULP-precision audit per docs/spec/issue_54_survey_brief.md.

1. Read §0 reads in full. Record anchors as specified.
2. Surface §0.5 ambiguities if any. Halt with NEEDS_CONTEXT if so.
3. Execute §2 phases.
4. Emit artifacts at data/audits/issue_54_ulp_audit.{json,md}.
5. Return §6 status with §8 schema fields populated.

Forbidden moves: §5. Read brief in full before Phase 0.
```

(claude.ai issues this invocation; CC walk-away executes.)
