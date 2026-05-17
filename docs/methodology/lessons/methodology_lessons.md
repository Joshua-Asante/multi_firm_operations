# Methodology Lessons Registry

This file is the canonical anchor for **methodology** lessons (M-class) — the
counterpart to [`live_journal/references/execution_lessons.md`](../../../live_journal/references/execution_lessons.md)
which holds **execution** lessons (E-class). Both registries follow the same
shape; the distinction is which layer the lesson lives at:

- **E-class — execution layer.** Lessons about live trading behavior (skips,
  decompositions, sizing deviations). Anchored to a specific dated trade with
  a P&L counterfactual or execution gap in dollars. Watch-points fire from
  `live_journal/scripts/journal_review.py`.
- **M-class — methodology layer.** Lessons about how Claude Code (or Joshua)
  authors briefs, runs §0 reads, applies pre-Q gates, classifies observations,
  or routes findings. Anchored to a specific dated decision artefact with an
  audit-instance cost (mis-stated production fact, wrong verdict, wrong
  routing) — usually instance count rather than dollars, but dollars where the
  methodology failure caused a measurable P&L mistake. Watch-points fire from
  brief-authoring discipline (Rule-0 reads, pre-Q gate audit, regime-robustness
  gate, etc.) rather than from a runtime script.
- **F-class — fixture-caught defect.** Counterfactual lessons: a defect that
  *would have* corrupted brief evidence had a fixture test not pinned the
  anchor invariant. Introduced 2026-05-16 alongside
  `docs/adr/2026-05-16-fixture-test-requirement.md`. Anchored to a specific
  dated investigation; cost is the counterfactual brief that would have been
  corrupted (dollar estimate when P&L-acting, audit-instance count
  otherwise). Watch-point fires during §0 of brief authoring when an analysis
  script is listed as a production read.

Both registries are durable canon. Memory entries that overlap with a
registered lesson exist only as compact pointers; the lesson itself lives here.

---

## Format spec

Each lesson is a self-contained section keyed `## M-N — short title`. Every
lesson must carry these fields, in this order:

1. **Status** — one of `CANDIDATE` / `PROMOTED` / `DEMOTED` (rare). With date.
2. **Anchor incident** — the specific dated event that surfaced the lesson.
   Cite a brief, ADR, gate audit, finding, or commit; quote the line that
   shows the failure.
3. **Cost** — the load-bearing measure that earns this lesson its slot.
   Choose ONE form:
    - **Dollar cost** if a live-PnL or P&L-counterfactual figure isolates
      cleanly to the methodology failure.
    - **Audit-instance count** for production-vs-doc mismatches (e.g. the
      Rule-0 catalyst was instance #3 of dd_protection misstatement).
    - **Wrong-verdict count** for cases where applying the lesson would have
      flipped a verdict (e.g. PROMOTE → HOLD).
4. **Rule** — imperative, single sentence. "Always X." / "Never Y." / "Before
   Z, do W."
5. **Mechanism (why this fails)** — the underlying generator that the rule
   guards against. Without this, the rule is a cargo-cult prescription.
6. **Connection to standing doctrine** — cross-reference to Rule 0 sub-rules
   (`docs/notion/repo_context.md` §7), observation routing, regime-robustness
   gate, or another locked methodology document.
7. **Watch-point** — where the lesson fires. For M-class lessons, this is
   typically "during §0 of brief authoring", "during pre-Q gate construction",
   or "before declaring a verdict CLOSED". Be specific.
8. **Output trigger** — what to do when the watch-point fires. Reference the
   lesson by name + cost; do not re-derive the rule each time.

Optional fields (use when load-bearing for the lesson):

- **Forbidden moves** — explicit list of patterns the lesson rules out. Use
  for lessons that name a tempting failure shape (e.g. silent relabeling,
  goalpost-moving).
- **Reproducer / worked example** — link to the gate audit, finding, or brief
  that documents the failure being avoided.
- **Sibling lessons** — other M-class or E-class lessons that interlock with
  this one.

### Promotion criteria

A pattern graduates from CANDIDATE to PROMOTED when EITHER:
- (a) a single audit-instance with cost ≥ promotion threshold surfaces, OR
- (b) the same pattern fires across three separate brief / decision windows.

Promotion thresholds (per cost form):

| Cost form | Threshold |
|---|---|
| Dollar cost | ≥ $3,000 (matches E-class) |
| Audit-instance count | ≥ 3 instances of the same production-vs-doc class |
| Wrong-verdict count | ≥ 1 verdict flip (a wrong-verdict is itself load-bearing) |

### Demotion criteria

A PROMOTED lesson demotes to DEMOTED if 6+ months pass without the
watch-point firing AND the structural condition that produced the lesson no
longer exists (e.g., methodology framework changed in a way that eliminates
the failure shape). Demotion is rare; lessons mostly accumulate.

DEMOTED lessons stay in this file (history-preserving) — they are not deleted.

### Versioning & change-log

Maintained at the bottom of this file. Each entry: date + lesson IDs added /
promoted / demoted + one-line rationale. Mirrors execution_lessons.md
versioning.

### File ownership and sync

This file is the **durable canon** for M-class lessons. The `brief-authoring`
skill bundle's SKILL.md may reference these lessons; the skill is downstream.
New M-entry workflow: edit this file, propagate to skill bundle on next
session install. Mirrors the [§7 sub-rule sync clause](../../notion/repo_context.md)
(Notion §7 ↔ SKILL.md) — repo wins.

---

## Migration plan (M-1..M-6)

**Decision (2026-05-08):** the lesson-registry on-disk format spec above is
confirmed. M-1..M-6 (currently in user memory entries + Notion lesson page)
migrate to this file when next a brief or §0 cites them and the format
mismatch surfaces. Until then, the Notion / memory pointers remain
authoritative for those six and this file holds only newly-authored or newly-
PROMOTED methodology lessons (M-7 onward).

This is a deliberate "grow on evidence" choice: porting six lessons cold is
cheap-but-ceremonial; porting on first cite is load-bearing. The migration
order will be the order in which they are next cited.

If a future brief authors a fresh M-class lesson before any of M-1..M-6 are
cited, that fresh lesson lands here directly under its own M-N tag (using the
next free integer above the highest currently-pointed-to in memory; check
both Notion and `~/.claude/projects/.../memory/` before claiming a number).

---

## M-7 — Anticipation-alert audit before lock declaration

**Status:** CANDIDATE 2026-05-08 (~$103 single-incident anchor on the
2026-05-07 Guardian late fill; Route A backfill scheduled 2026-05-11 morning
will measure cumulative cost across the 2026-04-22 → 2026-05-07 union
exposure window and decide promotion).

**Anchor incident:** 2026-05-07 Guardian XAUUSD entry late-filled because
the indicator was emitting via `alertcondition()` only (no `alert()` call),
so TradingView fired the alert one bar later than the strategy logic
expected. Patched same day across Guardian, DJ30, NAS100; Aegis was patched
2026-04-27 already.

**Cost:** ~$103 entry slippage on the single 2026-05-07 Guardian fill.
Cumulative cost across the union exposure window (Aegis 5d / Guardian 14d /
DJ30 2d / NAS100 2d bugged) is to be measured by
[live_journal/scripts/m7_anticipation_gap_backfill.py](../../../live_journal/scripts/m7_anticipation_gap_backfill.py)
on 2026-05-11. Promotion threshold (≥$3K cumulative) clears the backfill
gate.

**Rule:** Before declaring a Pine strategy LOCK complete, audit the alert
plumbing: every signal-emitting condition MUST have a paired `alert()` call
(not just `alertcondition()`), and the active-window guard must wrap both.
The lock checklist (§7 sub-rule #5: "operational-tooling integration phase")
extends with an "anticipation alerts wired" item.

**Mechanism (why this fails):** `alertcondition()` declares an alert template
that the user must manually wire in TV's UI. `alert()` fires immediately at
bar close. A strategy locked with only `alertcondition()` requires manual UI
wiring per chart — easy to forget on a fresh chart load, and silent when
forgotten (no error; just no fill until the trader notices). The
slippage-vs-signal-bar accumulates per missed bar.

**Connection to standing doctrine:** Reinforces §7 sub-rule #5 (lock
procedures need an operational-tooling integration phase). Pine + manifest +
MC ≠ live; alert plumbing is part of "live", not part of "Pine". Also
reinforces Rule 0 audit-first discipline at lock time: read the actual
`alert(...)` call in the locked Pine source, not the docstring claim that
alerts are wired.

**Watch-point:** During lock-event hook (`scripts/lock_event_hook.py`) and
during §0 of any "lock complete" brief — grep the locked Pine source for
`alert(` calls and confirm one fires inside each entry-condition branch.

**Output trigger:** When the watch-point catches missing `alert()` plumbing,
halt the lock, patch in same-session, and update this lesson's Cost section
with the audit-instance count (third firing → cumulative-firing route to
PROMOTED).

**Forbidden moves:**
- Do NOT declare a lock complete on the strength of an `alertcondition()`-
  only audit. The `alert()` call is the load-bearing surface; the
  `alertcondition()` is decoration.
- Do NOT defer alert-plumbing fixes "to next lock cycle"; same-session patch
  preserves the audit window cleanly.

**Reproducer / worked example:** Backfill script at
[live_journal/scripts/m7_anticipation_gap_backfill.py](../../../live_journal/scripts/m7_anticipation_gap_backfill.py).
Per-strategy patch dates documented in the script's `PATCH_DATES`.

**Sibling lessons:** §7 sub-rule #5 (operational-tooling integration phase);
E1 (Trust the design through macro) — both reinforce that lock declarations
are load-bearing only against the live execution surface.

---

## M-8 — Mechanical thresholds need a qualitative override channel

**Status:** CANDIDATE 2026-05-10 (single near-miss anchor on GH #54 ULP audit;
DONE_WITH_CONCERNS taxonomy caught the gap before any wrong verdict landed —
no flip incurred, but the brief's §2.3 *would* have prescribed ceremonial work
under strict mechanical reading).

**Anchor incident:** GH [#54](https://github.com/Joshua-Asante/multi_firm_operations/issues/54)
ULP-precision audit on risk-control comparison sites (CC walk-away spawn,
2026-05-10). Brief §2.3 disposition rule: *"Count instances where current
treatment = NONE AND risk ≥ MED ... If count ≥ 3 → recommend opening
Q-DDP-PRECISION-SWEEP Pre-Q."* Spawn returned 5 hits — **all** in
`analysis/oanda_stage1/` (archived research code per CLAUDE.md 2026-04-29
archive; 90-day review gate 2026-07-29). Zero hits in production
risk-control sites: `dd_protection.py:92` was patched by PR
[#53](https://github.com/Joshua-Asante/multi_firm_operations/pull/53), all 6
`portfolio_mc.py` decision sites already on the precision-by-scale rule, and
`accounts.py` ratio/dollar comparisons fed by `round(_, 2)` properties.

**Cost:** Wrong-verdict count = 0 (verdict flip *prevented* by
DONE_WITH_CONCERNS surfacing; not an actual flip). Counterfactual cost if the
brief had been read mechanically: ~1 session of Pre-Q authoring + closure
overhead, $0 P&L impact, reinforcement of the ceremonial-artifact failure
mode the parallel-work doctrine is trying to suppress. Tracked as a
near-miss; promotion gated on second occurrence (a future brief whose
mechanical threshold prescribes ceremony under qualitative re-read).

**Rule:** Brief authoring must pair count-only disposition thresholds with at
least one qualitative gate (e.g., *"≥ 3 production risk-control sites"*
rather than *"≥ 3 sites"*), OR explicitly flag the threshold as
mechanical-only and rely on the spawn's `DONE_WITH_CONCERNS` channel to
surface the qualitative gap for parent-review override.

**Mechanism (why this fails):** A pure count threshold is shape-blind — it
treats live-risk-control sites and archived-research backtest filters as
equally weighted. The defect generator is a brief author writing
"sites" / "instances" / "hits" without scoping the count to the
production surface that motivated the audit in the first place. Under
mechanical reading, the threshold trips on shape-mismatched evidence and
prescribes ceremony. The cost is small per incident but compounds: each
ceremonial Pre-Q normalises the artifact-without-target pattern.

**Connection to standing doctrine:** Reinforces the brief-authoring discipline
already encoded in `brief-authoring` SKILL.md (falsifiable §4 hypothesis,
§5 forbidden moves, §6 named gate). The qualitative-gate refinement extends
§6 — gate construction must specify *what kind of evidence* the count is
counting, not just the count itself. Also reinforces the four-state status
taxonomy (DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED) as the
load-bearing recovery channel when a brief turns out to be over-restrictive
in flight.

**Watch-point:** During §6 of brief authoring, when writing any disposition
rule of the form *"if count ≥ N → action X"*. Read the rule back asking:
*"Could 5 hits in archived / dormant / out-of-spirit code trip this without
a single hit in the actual target surface?"* If yes, scope the count
qualitatively or flag mechanical-only.

**Output trigger:** When the watch-point fires, either (a) rewrite the
threshold to scope the count to the audit's intended surface (e.g.,
"production risk-control sites" not "sites"), or (b) leave the count
mechanical and add an explicit §6 line: *"Threshold is mechanical;
DONE_WITH_CONCERNS expected if hits cluster outside the audit's target
surface — parent-session override decides."* Update this lesson's Cost
section with the new instance.

**Forbidden moves:**
- Do NOT bake unscoped count thresholds into a brief's disposition rule
  without checking the qualitative re-read.
- Do NOT treat `DONE_WITH_CONCERNS` as a brief-authoring failure mode — it
  is the recovery channel that earned this near-miss its non-cost. The
  failure mode is the brief that *forces* a wrong verdict by leaving the
  spawn no concerns-channel to use.

**Reproducer / worked example:** GH [#54](https://github.com/Joshua-Asante/multi_firm_operations/issues/54)
spawn return (transcript 2026-05-10): mechanical count = 5, qualitative
re-read = 0 production hits, status = `DONE_WITH_CONCERNS`, parent disposition
= CLOSE without opening Pre-Q. The full spawn-return survey table and
disposition reasoning are in the issue's closing comment.

**Sibling lessons:** None yet at M-class. Cross-feeds the parallel-work
doctrine post-mortem (2026-05-XX) as one datapoint for the brief-authoring
skill v-next refinement (discipline check #4: "qualitative gate alongside
count thresholds").

---

## M-9 — Gitignored vendor-data manifests need a local pre-commit hash gate

**Status:** PROMOTED 2026-05-10 (GH [#62](https://github.com/Joshua-Asante/multi_firm_operations/issues/62)
Phase B — manifest drift between PR #59 and sync 93865f8; NAS100USD missing-on-disk
caught by manifest vs reality mismatch).

**Anchor incident:** Phase A RCA
[`docs/briefs/2026-05-10-pr59-manifest-drift-rca.md`](../briefs/2026-05-10-pr59-manifest-drift-rca.md)
§3 verdict **H2** — *"Manifest correct at b71e4a4 11:12 EDT; on-disk CSVs were
modified between 11:12 EDT and the spawn pre-flight ~12:10 EDT (or the sync at
12:21 EDT)."* (quoted from §1 H2 hypothesis as adopted in the aggregate verdict.)

**Cost:** Audit-instance count — silent manifest vs on-disk skew across five
vendor files in one session; one conclusive missing-file case (NAS100USD.csv)
that a commit-time **MISSING** check would have surfaced immediately.

**Rule:** Gitignored vendor-data manifests need a local pre-commit hash gate.
CI cannot replace it when the bytes aren't in the repo. Manual regen drifts
silently.

**Mechanism (why this fails):** Tracked manifests without an automated
validator only reflect whatever bytes existed the last time someone ran
`sha256sum`. Re-exports, CRLF normalization, and file deletes happen on disk;
CI on GitHub never sees the bytes, so **hash validation in CI is infeasible**
under the public-clone vendor-data contract. Without a local hook, drift
stays silent until a human runs a manual reconcile.

**Connection to standing doctrine:** Reinforces Rule 0 (read production +
on-disk reality before verdicts) and the public-clone posture in `CLAUDE.md`.
Complements E-class execution lessons: this is methodology-layer **data
integrity**, not fill quality.

**Watch-point:** Any PR touching `data/**/SHA256SUMS`, any spawn brief
mentioning vendor panels, or any "re-export" workflow — confirm hook installed
and regen landed in the same commit as the CSV change.

**Output trigger:** Run `python scripts/check_data_manifests.py --check`;
if it fails, run `--regenerate --dry-run` then `--regenerate`. Reference this
lesson + [`docs/adr/2026-05-10-manifest-integrity-gate.md`](../../adr/2026-05-10-manifest-integrity-gate.md).

**Forbidden moves:**
- Do NOT treat `.github/workflows/manifest-check.yml` as byte-level integrity
  coverage — it is format + tracked-path enforcement only.
- Do NOT `git commit --no-verify` for routine vendor-data work; reserve for
  exceptional bypass with explicit rationale.

**Reproducer / worked example:** Phase A drift table and NAS100USD timeline in
[`docs/briefs/2026-05-10-pr59-manifest-drift-rca.md`](../briefs/2026-05-10-pr59-manifest-drift-rca.md)
§2–§3.

**Sibling lessons:** None yet at M-class.

---

## M-10 — FXIFY ops integration: validator routing beats parallel display layers

**Status:** PROMOTED 2026-05-10 (multi-layer FXIFY integration review before merge;
pytest green did not catch display-layer contradictions).

**Anchor incident:** FXIFY challenge tooling shipped as a **parallel layer**: simplified
`dd_remaining_pct` / `target_remaining` remained on `status`, `cmd_update`, and
`Account.flags` alongside `fxify_rule_validator`, plus `prior_eod_equity =
initial_balance` on `add_account`, defeating skip semantics; `phase_complete`
surfaced only as a volatile flag string with no persisted audit timestamp.

**Cost:** Audit-instance cluster — five contradiction surfaces (flag merge,
status table adjacency, `cmd_update` duplicate metrics, silent daily-loss
reference, phase-complete persistence ambiguity); instance count over dollars.

**Rule:** For firm-specific rule validators, **route display and failure through the
validator exclusively** for that firm; keep simplified accounting properties only
for firms that do not use the validator. Never default fake inputs that defeat
explicit skip paths. Persist audit-worthy completion (`phase_completed_at` per-phase
dict of ISO timestamps) when adopting completion semantics.

**Mechanism (why tests missed it):** Integration tests exercised validator math;
they did not assert **single-truth UI** (no adjacent contradictory columns) or
**serialization of persisted audit fields** (`to_dict` drift vs in-memory set).

**Connection to standing doctrine:** Reinforces Rule 0 (read production paths end-to-end)
and The Algorithm (**Delete/Simplify** cross-wiring before layering features).

**Watch-point:** Any PR touching `accounts.py` FXIFY branches, `cli.py status/update`,
or `accounts.json` schema — confirm one routing path per firm and JSON round-trip
for new persisted fields.

**Output trigger:** Human review checklist for validator/display coupling; optional
UX snapshot test for FXIFY row shape.

**Forbidden moves:**
- Do not ship parallel DD semantics for the same firm on `status` / `flags` /
  `update` without explicit operator doctrine.
- Do not default `prior_eod_equity` to synthetic values that replace explicit skip.

**Reproducer / worked example:** Pre-fix `python cli.py status` showed DD Left %
next to FXIFY column; `cmd_update` printed simplified DD lines above validator
lines for FXIFY.

**Sibling lessons:** Complements M-9 (integrity drift); same theme — green tests
≠ aligned operator truth.

---

## M-AHF — Audit hooks check storage form, not human-readable property

**Status:** PROMOTED 2026-05-10 (third instance auto-graduation per registry rule *"auto-graduates on third instance regardless of dollar cost"*)
**Domain:** brief-authoring · ADR authoring · methodology audit
**Sibling lessons:** M-EC (Execution Commit) · Rule 0 (audit-first) · Rule 0-T (test-call-graph)

### Pattern

Mechanical audit hooks (grep regexes, count assertions, presence checks) are repeatedly authored against the **author's mental form** of the value being inspected, rather than against the **storage form** in the artifact under audit. The hook tests *"is this string present in the form I'm thinking of"* when it should test *"is this property held in whichever form the artifact uses."*

Mental form ≠ storage form. The hook author imagines the value as it reads in conversation or specification; the artifact stores it in whichever form the storage convention dictates. When the two diverge, the hook silently passes or fails on the wrong property.

### Anchors (three instances, all 2026-05-10)

| # | Round | Hook intent | Author's mental form | Storage form | Failure mode |
|---|---|---|---|---|---|
| 1 | GH #55 ratification, round 1 (commit `50664cd` predecessor) | Verify ADR content stability across commits | *"Commit hasn't been amended"* | File contents at commit ref | Commit metadata used as proxy for content; missed actual content drift |
| 2 | GH #55 ratification, round 2 (commit `50664cd`) | Verify MC anchor pins in test file | `98.09% / 0.36% / 4.73%` (percent form) | `0.9809 / 0.0036 / 0.0473` (decimal form) | Hook matched zero pins; required round-trip correction |
| 3 | PR #73 hook 4 (CC handoff for feed-equivalence-brief-commit) | Verify trashed Notion page ID doesn't leak outside §Lock metadata | `notion.so/358dc0b53c11818085d0cc36692e0185` (URL form) | `358dc0b53c11818085d0cc36692e0185` (bare page ID) | CC correctly used bare-ID grep to verify the property; surfaced hook over-scoping as a defect rather than a content failure |

Instance 3 differs from 1 and 2 in cost: CC's autonomy absorbed the form-fidelity gap by interpreting the hook's *intent* (property: page ID does not leak) rather than its *expression* (form: URL string present). No round-trip, no dollar cost. The pattern still fired — CC's report flagged the discrepancy explicitly as a handoff-authoring defect.

### Counter-measure

When authoring an audit hook, before committing the regex or assertion:

1. **State the property in plain language**, not as a grep expression. *"Page ID does not leak outside §Lock metadata"* is the property. `grep 'notion.so/358dc0b...'` is one mechanization. Many other mechanizations exist; pick whichever covers the property.
2. **`cat` the target file** (or echo its expected content) and confirm the regex matches the literal storage form. If the property could be held in alternate forms (URL vs bare ID; percent vs decimal; commit metadata vs file content), cover all forms or restate the property to make form irrelevant.
3. **Prefer property assertions over form matches** when storage form is variable or under author control. Example: instead of `grep 'notion.so/PAGE_ID' <file>`, use a form-agnostic ID match scoped to the section that should/shouldn't contain it:
   ```bash
   # Property: bare page ID appears exactly once, inside §Lock metadata
   awk '/^## §Lock metadata/,/^## /' <file> | grep -c '358dc0b53c11818085d0cc36692e0185'  # expect 1
   grep -c '358dc0b53c11818085d0cc36692e0185' <file>                                       # expect 1 (total)
   ```
   Two assertions, one property, form-irrelevant.

### Promotion provenance

- **Round 1** (GH #55, 2026-05-10): single instance, candidate registry, log-entry status.
- **Round 2** (GH #55, 2026-05-10): second instance same day, sharper two-layer formulation, log-entry status. Pre-registered rule: *"third instance auto-graduates regardless of dollar cost."*
- **Round 3** (PR #73, 2026-05-10): third instance. CC correctly interpreted intent, surfaced over-scoping. Auto-promotion triggered per the pre-registered rule.

The rule is what fired the promotion, not a fresh judgement. If the rule hadn't existed, instance 3 would have stayed log-entry status because CC absorbed the cost — and the lesson would have been understated. Pre-registration is what made the third instance count.

### Related candidates (not promoted)

- **Count-expectation pinned at authoring time before final artifact existed.** PR #73 hook 3 (`prop_firm_pipeline` count expected 1, brief retained 2 — second retention is operationally legitimate). First instance. Stays log-entry status; re-check on next instance.

### Cross-reference

- **Rule 0** (audit-first) reads production state before authoring decisions. M-AHF extends Rule 0 to authoring time of the audit hooks themselves.
- **Rule 0-T** (test-call-graph) verifies that a test reaches the changed path. M-AHF is the sibling for audit hooks: verifies that a hook matches the stored form. Both attack indirection; Rule 0 against doc indirection, Rule 0-T against test-coverage indirection, M-AHF against form-mismatch indirection.
- **M-EC** (Execution Commit) is the *result* discipline — forward-binding the lock to a live signal. M-AHF is the *audit-mechanization* discipline — forward-binding the hook to the storage form. Both belong to the brief-authoring discipline-checks bundle.

---

## F-1 — TradingView <30-day JPY P&L inflation (~153× at USDJPY ~150)

**Status:** CANDIDATE 2026-05-16 (retroactive seed; defect predates F-class infrastructure)
**Domain:** brief-evidence integrity · analysis-script output validation
**Sibling lessons:** M-AHF (audit hooks check storage form) · Rule 0 (audit-first) · code-defect-debugging skill (canonical anchor)

### Pattern

TradingView reports JPY-quoted instrument P&L in raw JPY (not USD) on holds
strictly under 30 calendar days, while reporting USD on longer holds. The
short-horizon JPY figure looks like a plausible USD value at first read but
is inflated by the quote rate (~153× at USDJPY ~150). Any brief that cited
TV-reported P&L on a sub-30-day USDJPY trade as USD evidence would silently
overstate by two orders of magnitude.

### Anchor incident

- **Investigation:** Q-MT5-TV equivalence.
- **Defect surface:** TV display layer; JPY→USD conversion omitted on
  short-horizon JPY-quoted holds.
- **Discovery path:** noticed manually during equivalence cross-check; not
  caught by any fixture suite (none existed at the time).
- **Canonical fix:** `tv_mt5_pnl_reconciliation.py` (commit `8e2a2d6`,
  2026-05-16) encodes the independent USD formula and a `compute_pnl_tv_buggy`
  regression helper that reproduces the defect. Fixture suite at
  `tests/test_tv_mt5_pnl_reconciliation.py` pins the canonical, inverse, and
  30-day boundary cases against independently derived expected values.

### Cost

**Audit-instance count: 1** (retroactive seed). The Q-MT5-TV equivalence work
was diagnostic rather than P&L-acting, so the counterfactual is
re-investigation cost (~1 session) rather than direct dollar loss. The lesson
seeds the registry; future fixture-caught defects accumulate alongside.

### Rule

Before citing an analysis-script output as brief evidence, confirm the script
has a fixture test under `tests/test_<basename>.py` pinning its anchor
invariant against an independently derived expected value, and that
`pytest tests/test_<basename>.py -v` returns green.

### Mechanism (why this fails)

Order-of-magnitude defects in numeric output escape eyeballing when the
incorrect magnitude is *plausible at first glance*. The TV JPY figure on a
sub-30-day USDJPY hold reads as a reasonable percentage; only the
side-by-side comparison against an independently derived USD value reveals
the ~153× inflation. Fixture tests with expected values derived by hand (not
by the same code path) catch this class because the comparison is between
two independent derivations, not a self-check.

### Connection to standing doctrine

- `docs/adr/2026-05-16-fixture-test-requirement.md` — codifying ADR;
  extends Rule 0 from "production code read" to "production code read AND
  fixture-tested where output is load-bearing."
- `docs/rule_0.md` — canonical Rule 0 text being extended.
- `code-defect-debugging` skill — canonical JPY 153× anchor (TV <30-day JPY
  ~153× P&L inflation) lives in the skill's defect catalogue.

### Watch-point

During §0 of brief authoring, when listing an analysis script as a production
read. The check fires at the brief-authoring time, not at script-edit time.

### Output trigger

If the cited script lacks `tests/test_<basename>.py` OR its fixture suite is
red, block brief authoring until fixture test lands and pytest is green. The
ADR's Hook 1 (`scripts/check_brief_evidence_coverage.py`) provides the
mechanical check across all committed briefs and ADRs.

### Promotion criteria for F-class

Same shape as M-class:
- (a) single instance with dollar cost ≥ $3,000 OR
- (b) three separate fixture-caught defects across the registry.

F-1 stays CANDIDATE as a retroactive seed; PROMOTION fires on the second
genuinely fixture-caught defect (i.e. one where the fixture suite, not
manual inspection, surfaced the defect first).

---

## Versioning & change-log

- **2026-05-08:** Registry seeded. Format spec authored. M-7 added as
  CANDIDATE on the 2026-05-07 Guardian late-fill anchor. M-1..M-6 remain in
  Notion / memory pending first-cite migration.
- **2026-05-10:** M-8 added as CANDIDATE on the GH #54 ULP-audit near-miss
  anchor. No wrong-verdict flip occurred (DONE_WITH_CONCERNS taxonomy caught
  the gap); promotion gated on second occurrence.
- **2026-05-10:** M-9 added as PROMOTED on GH #62 Phase B / PR #59 manifest
  drift RCA (H2 verdict); encodes local pre-commit hash gate + format-only CI.
- **2026-05-10:** M-10 added as PROMOTED on FXIFY validator/display routing review
  (parallel-layer contradiction cluster + `phase_completed_at` persistence).
- **2026-05-10:** M-AHF added as PROMOTED on third-instance auto-graduation per
  registry rule (audit hooks check storage form, not human-readable property;
  three same-day instances: GH #55 round 1, GH #55 round 2, PR #73 hook 4).
- **2026-05-16:** F-class introduced (fixture-caught defect). F-1 added as
  CANDIDATE on the Q-MT5-TV JPY ~153× anchor (retroactive seed; defect
  predates F-class infrastructure). F-class definition added to registry intro.
  Codifying ADR: `docs/adr/2026-05-16-fixture-test-requirement.md`.
