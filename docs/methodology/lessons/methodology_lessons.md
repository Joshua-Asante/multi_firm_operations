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

## Versioning & change-log

- **2026-05-08:** Registry seeded. Format spec authored. M-7 added as
  CANDIDATE on the 2026-05-07 Guardian late-fill anchor. M-1..M-6 remain in
  Notion / memory pending first-cite migration.
