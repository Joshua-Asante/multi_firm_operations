# Q-CORR-1 — Programme Closure Note

**Status:** CLOSED — SNAG BUDGET SPENT
**Date:** 2026-05-14
**Trigger:** Programme Audit follow-up #1 (`docs/notes/audits/programme-audit/2026-05-14-meta-q-corr-1-audit.md`, §5.1). Operator decision: Q-CORR-1's SNAG budget is spent.
**Artifact path (intended):** `docs/briefs/Q-CORR-1-closure.md` (co-located with the Q-CORR-1.x briefs it dispositions)
**Authoring environment:** claude.ai (briefs/methodology/no-commits — authored, not committed)

---

## §0 — Reads

- `2026-05-14-meta-q-corr-1-audit.md` — the audit whose follow-up #1 this note executes.
- `docs/briefs/Q-CORR-1.1-guardian-silver-correlation.md` — disposition FALSIFIED, unchanged by this note.
- `Q-CORR-1_2-guardian-family-silver-wfo.md` — PRE-Q DRAFT, dispositioned below.
- `docs/briefs/Q-CORR-1.3-guardian-family-silver-pepperstone-feed-substitution.md` — CLOSED clean, unchanged by this note.
- `docs/rejected_candidates.md` — updated per §3.

---

## §1 — Decision and basis

Q-CORR-1 — "does a Guardian-family strategy on XAGUSD decorrelate from Guardian Gold at the strategy level, admissible as a 5th portfolio strategy" — is **closed**. Its SNAG budget is spent.

Basis (from the audit, not re-litigated here): Q-CORR-1.1 falsified the parameter-equivalence port; Q-CORR-1.2 was a loop spawned on evidence its own brief labels non-probative (the ρ=0.028 in-sample hint) and stalled pre-lock; Q-CORR-1.3 closed but only resolved feed plumbing; the parallel v1.5-sweep track yielded a single +2% tweak and was running in-sample. Belt grew across every step with one candidate prune and zero belt prunes. Per the Programme Audit Protocol, SNAG-budget exhaustion is the disciplined response to this pattern — not another loop. This is a Delete under The Algorithm: the programme should not continue to exist, so it is closed rather than optimized further.

This closure is **not** a falsification of the finding that opened Q-CORR-1 (see §4).

---

## §2 — Loop dispositions

| Loop | Prior state | Disposition at closure |
|---|---|---|
| Q-CORR-1.1 | FALSIFIED (2026-05-12) | **Unchanged** — FALSIFIED stands on its own evidence (DD 11.52% > 8.0%; WR 11.34% below band). |
| Q-CORR-1.2 | PRE-Q DRAFT (lock pending WFO infra) | **CLOSED — WITHDRAWN PRE-LOCK.** Never locked, never run; parent programme budget spent before lock. Not falsified (no run), not superseded (nothing replaced it), not ambiguous (no run to be ambiguous about). This disposition also resolves the lineage ambiguity flagged in audit §5.2: Q-CORR-1.2 is closed, not "SUPERSEDED," and not active. |
| Q-CORR-1.3 | CLOSED clean (2026-05-14) | **Unchanged** — CLOSED stands. It resolved a methodology question (feed substitution); a methodology finding outlives the object-investigation that prompted it. One asterisk carried to §5. |
| v1.5-sweep track (rounds 1) | Adjudicated quarantined-hint (this session) | **Unchanged** — stays a quarantined hint set, same shelf as the ρ=0.028 hint. Not evidence, not a baseline. `trendBufferAtr` 0.25 does not carry forward as anything. |

The Q-code-collision question (audit §5.2 — Q-CORR-1.2 §5 reserved the "Q-CORR-1.3" label for a different contingency than the 1.3 actually authored) is now historical-record-only. Worth one annotation in the lineage record; not worth a follow-up, since the programme is closed.

---

## §3 — rejected_candidates.md update

**Add / broaden the entry:** Guardian-family strategy on XAGUSD (Silver) as a portfolio candidate.

- Scope: the **direction** is rejected, not only the v5.5-parameter-equivalence port that Q-CORR-1.1 already recorded. Q-CORR-1 as a whole — equivalence port, parameter-freedom WFO, and the in-sample sweep track — did not produce an admissible candidate.
- Re-proposal bar: **new mechanism evidence**, same standard as every other entry on the list (AUDNZD, CHN50U, Sentinel USDCHF, ORATS short-vol strangles, Aegis SHORT v0.1, Guardian-on-USOIL). "New parameters" or "a wider sweep" is not new mechanism evidence — that is the move the audit closed.
- Reference: this closure note + the audit.

---

## §4 — What survives the closure

The closure dispositions a *candidate and its investigation*. It does not retract these:

1. **The belt finding that opened Q-CORR-1 stands.** Instrument-level correlation is not a reliable proxy for strategy-level correlation (the NAS100/DJ30 strategy-level decorrelation despite tight instrument correlation). Q-CORR-1 tested whether *Guardian-on-Silver specifically* could exploit that. It could not. The general finding is independent of this result and remains in the portfolio-construction belt.
2. **A 5th strategy is not foreclosed.** What is closed is this candidate via this investigation. A 5th strategy on a different instrument, or on Silver with genuinely new mechanism evidence, remains open — at the same intake bar as any candidate.
3. **Q-CORR-1.3's feed-substitution finding** is retained as a general methodology finding, reusable by any future investigation that needs the Pepperstone/TV feed question settled.
4. **Candidate lesson (pinned, below graduation threshold):** "An in-sample sweep track running parallel to a gated OOS Pre-Q leaks toward baseline status unless physically walled." Fired once, cleanly, inside a now-closed programme. Counterfactual anchor: a max-Net sweep would have shipped the $597,784 curve-fit combo. Pin for re-firing detection on the next parallel-track situation; graduates at a second firing or a single >$3K incident.

---

## §5 — Operational loose ends

These need action; the closure is not complete until they are resolved.

1. **In-flight Q-CORR-1.2 §16 train sweep — cancel or recall.** `b889ba59` shows the §16 train sweep was resumed and a CC handoff authored (`cc-handoff-2026-05-13-q-corr-1-2-seam-1-pre-sweep-impl.md`). If that handoff has been dispatched to a CC session, recall it; if not, cancel it. It points at a closed target. **This is the one time-sensitive item.** *Owner: Joshua. Now.*
2. **WFO-runner infrastructure — re-classify, do not orphan.** `wfo-runner-v0.md` spec and its Seam #1 / adversarial-OOS-guard CC handoffs were in progress toward Q-CORR-1.2. The runner is general-purpose OOS infrastructure, not Silver-specific. Decide explicitly: retain it parked at current state as general WFO capability, or carry it to completion as standalone infra. Either is fine — what is not fine is leaving it in-progress toward a dead target. *Owner: Joshua. No deadline; before next strategy-admission investigation.*
3. **Q-CORR-1.3 "14.99%" verification (carried from audit §5.4).** Q-CORR-1.3 closed "clean"; confirm the "DD-convention amendment / §15 acceptance battery → 14.99%" did not move a falsifier line. A closed-clean artifact should not silently carry convention drift. Single grep/diff against locked values. *Owner: Joshua. Low priority; before the 1.3 feed-substitution finding is cited by any future investigation.*
4. **Notion + memory.** If Q-CORR-1 is tracked in the Notion Command Center, mark it closed. Claude's memory still carries Guardian Silver as an active 5th-strategy candidate — stale as of this note; flagged to Joshua for a memory edit if he wants the closure recorded there.

Audit follow-ups #3 (structural in-sample/OOS guard) and #4 (WR band→floor drift) were scoped to Q-CORR-1.2's §4 grid and §6 thresholds; with Q-CORR-1.2 closed, the strategy-specific versions are moot. The general principle behind #3 survives as the §4.4 candidate lesson.

---

## §10 — Audit hooks (verify the closure stuck)

```bash
# 1. Q-CORR-1.2 not silently resurrected — status reads CLOSED, no new run activity
grep -iE "status" docs/briefs/Q-CORR-1.2-guardian-family-silver-wfo.md
git log --oneline --since=2026-05-14 -- scripts/wfo/runs/
# Expected: status CLOSED — WITHDRAWN PRE-LOCK; zero new run dirs

# 2. rejected_candidates.md carries the broadened Guardian-on-XAGUSD entry
grep -n "XAGUSD\|Guardian.*Silver" docs/rejected_candidates.md
# Expected: direction-level entry present, re-proposal bar = new mechanism evidence

# 3. No §16 / train-sweep commits after closure
git log --oneline --since=2026-05-14 --all -- docs/briefs/handoffs/ | grep -i "q-corr-1.2\|train sweep\|seam"
# Expected: empty (handoff cancelled/recalled, not executed)

# 4. The surviving belt finding is still in the portfolio-construction belt, not deleted with the candidate
grep -rn "instrument.*correlation\|strategy-level correlation" docs/
# Expected: the NAS100/DJ30 belt finding intact and independent of Q-CORR-1

# 5. v1.5 sweep artifacts remain quarantined hints, never cited as evidence/baseline
grep -rn "0.25\|v1.5 sweep" docs/briefs/ docs/notes/
# Expected: hint-log context only
```

---

## Discipline check

```
[x] Decision recorded in writing with basis (audit follow-up #1 executed)
[x] Every loop dispositioned (1.1 unchanged / 1.2 CLOSED-WITHDRAWN-PRE-LOCK / 1.3 unchanged / sweep quarantined)
[x] rejected_candidates.md update specified with scope + re-proposal bar
[x] What survives the closure stated explicitly (closure does not over-claim)
[x] Operational loose ends named with owner; the time-sensitive one flagged
[x] §10 hooks verify the closure cannot be silently un-made
```
