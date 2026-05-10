# Parallel Doctrine — Cluster 001 Post-Mortem (TEMPLATE)

**Status**: TEMPLATE (unfilled). Fill after cluster closure.
**Cluster ID**: 001
**Cluster scope**: GH issues #54, #55, #56, #57 (ULP-precision `dd_protection` cluster)
**Doctrine under test**: `docs/specs/parallel_work_doctrine.md` (staged 2026-05-10)
**Cluster opened**: 2026-05-10
**Cluster closed**: <YYYY-MM-DD — fill on closure>
**Author**: <fill on closure>

---

## §0 — Cluster artifact lineage (Rule-0 anchor)

Confirm presence + paths + commit hashes before scoring. If any missing, post-mortem cannot complete; mark cluster `NOT_CLOSED` and re-run when artifacts land.

| Issue | Brief / artifact path | Surface (per doctrine) | Commit hash | Status |
|---|---|---|---|---|
| #54 | `docs/specs/issue_54_survey_brief.md` → `data/audits/issue_54_ulp_audit.json` | claude.ai author → CC walk-away execute | `<hash>` | RESOLVED / OPEN |
| #55 | `docs/specs/issue_55_remc_brief.md` → `data/audits/issue_55_mc_remc.json` | claude.ai author → CC walk-away execute | `<hash>` | RESOLVED / OPEN |
| #56 | `docs/specs/issue_56_replay_brief.md` → `data/audits/issue_56_state_replay.json` | claude.ai author → CC walk-away execute | `<hash>` | RESOLVED / OPEN |
| #57 | `docs/briefs/PreQ-MVD-epsilon.md` → ADR or close-as-no-change | claude.ai (Pre-Q) | `<hash>` | RESOLVED / OPEN |

Lineage grep (run from repo root):
```bash
git log --oneline --all | grep -E "^[a-f0-9]+ (spawn|cc-handoff|adversarial-review):"
```
Expected count after cluster: ≥3 (one per CC-handoff spawn at minimum). Actual count: `<int>`. If 0, doctrine was not exercised → §Promotion check (1) defaults FALSIFIED.

---

## §1 — Per-issue resolution log

For each issue, record:

### #54 — ULP-precision audit on risk-control comparison sites
- **Disposition outcome**: `<≥3-instance Pre-Q sweep | <3-instance fix-as-found | 0-instance close>`
- **Surface(s) used**: `<list>`
- **Brief authored at**: claude.ai
- **Executed at**: `<surface>`
- **Spec-compliance pass**: PASS / FAIL (failure notes if any)
- **Quality pass**: PASS / FAIL (failure notes if any)
- **Re-dispatches required**: `<int, with reasons>`
- **Notes**: `<freeform>`

### #55 — Re-run portfolio_mc.py against dd_protection ULP fix; verify C2 anchor stability
- **Anchor pre-fix**: `pass_rate=98.09 | dd=0.36 | ttp_med=4.73`
- **Anchor post-fix**: `pass_rate=<x> | dd=<y> | ttp_med=<z>`
- **Drift verdict**: WITHIN_TOLERANCE / RELOCK_REQUIRED / AMBIGUOUS
- **Surface(s) used**: `<list>`
- **Re-dispatches**: `<int>`
- **If RELOCK_REQUIRED**: ADR opened at `<path>`; bust attribution flip recorded.
- **Notes**: `<freeform>`

### #56 — Historical dd_protection_state replay under rounded comparison; flip list
- **Flip count**: `<int firings | int non-firings>`
- **Material flips identified**: `<int (those that would have changed live action)>`
- **Surface(s) used**: `<list>`
- **Re-dispatches**: `<int>`
- **Notes**: `<freeform>`

### #57 — MVD self-check epsilon (1e-4) tightening question
- **Pre-Q gate verdict**: PASS_TO_INQUIRE / GATE_OUT_AS_CEREMONIAL / DEFERRED
- **If PASS_TO_INQUIRE**: hypothesis stated; ADR or close-as-no-change emitted at `<path>`.
- **If GATE_OUT_AS_CEREMONIAL**: this is a §Promotion gate-relevant data point — pre-Q gate prevented a ceremonial INQHIORI loop.
- **Surface(s) used**: claude.ai only (methodology question).
- **Notes**: `<freeform>`

---

## §2 — Surface utilization scorecard

| Surface | Times used | Times CORRECTLY routed (per doctrine) | Times INCORRECTLY routed | Notes |
|---|---|---|---|---|
| claude.ai | `<int>` | `<int>` | `<int>` | |
| Cursor | `<int>` | `<int>` | `<int>` | |
| Claude Code (walk-away) | `<int>` | `<int>` | `<int>` | |
| Claude Code in Warp | `<int>` | `<int>` | `<int>` | |

"Incorrectly routed" = work that ended up at a surface other than the doctrine's prescribed assignment, AND where the doctrine had a clear assignment. If doctrine was silent on the case, count it under §Promotion check (2) AMBIGUOUS instead.

---

## §3 — Promotion gate test (binary verdicts per doctrine §Promotion)

### Check 1 — Routing prevented at least one observed defect or rework instance vs no-doctrine counterfactual

**Verdict**: RESOLVED / FALSIFIED

**Evidence required**: cite at least one specific instance where the doctrine prevented a defect that the no-doctrine counterfactual would have produced. Examples acceptable:
- Doctrine routed #X audit to walk-away CC; default impulse was Cursor; doctrine prevented load-bearing-module mis-routing.
- Doctrine forced spawn brief authoring at claude.ai before CC dispatch; surfaced ambiguity that would have caused re-dispatch otherwise.
- Doctrine flagged Warp escalation when falsifiable H emerged; prevented OODA-surface INQHIORI drift.
- Doctrine's §protocol-3 (one load-bearing module per branch) prevented merge conflict on `dd_protection.py`.

**Counter-evidence (if FALSIFIED)**: state explicitly that the cluster was completed without any routing decision actually exercised, OR that the routing decisions made would have been made anyway under no-doctrine ad-hoc judgment.

**Filled instance(s)**:
1. `<instance description>` — `<which doctrine rule>` — `<no-doctrine counterfactual>`
2. ...

### Check 2 — Every encountered case routable without surface ambiguity

**Verdict**: RESOLVED / AMBIGUOUS

**Test**: count cases where doctrine had no rule for the situation OR the rule was unclear. ≥1 silent or unclear case → AMBIGUOUS.

**Silent cases encountered**:
1. `<case description>` — `<what doctrine should have said>`
2. ...

(If empty: RESOLVED.)

### Check 3 — No rule proved over-restrictive

**Verdict**: RESOLVED / FALSIFIED

**Test**: list any workarounds undertaken to comply with doctrine that themselves violated doctrine intent, OR any rules that forced clearly-wrong routing.

**Workarounds (if any)**:
1. `<workaround description>` — `<which rule>` — `<why over-restrictive>`
2. ...

(If empty: RESOLVED.)

---

## §4 — Outcome decision

**Doctrine status post-cluster**: PROMOTE / REVISE_AND_RESTAGE / DELETE

Selection logic (per doctrine §Promotion):
- (1) RESOLVED + (2) RESOLVED + (3) RESOLVED → **PROMOTE** to `docs/adr/2026-MM-DD-parallel-work-doctrine.md`. Stage doc remains as lineage.
- (1) FALSIFIED → **DELETE**. Capture lesson per §6 below.
- (3) FALSIFIED → **REVISE_AND_RESTAGE** with specified amendments before next cluster.
- (2) AMBIGUOUS → **REVISE_AND_RESTAGE** to cover silent cases.

**Selected**: `<one>`

**Justification**: `<freeform 2-4 sentences>`

**Next cluster (if REVISE_AND_RESTAGE)**: `<target cluster description>`

---

## §5 — Doctrine amendments (if REVISE_AND_RESTAGE)

For each amendment:
- **Target section**: `<doctrine §X>`
- **Current text**: `<verbatim>`
- **Proposed text**: `<verbatim>`
- **Reason**: `<which check failed and how this addresses it>`

---

## §6 — Lessons captured

For each lesson, follow lesson-capture discipline (dated anchor + dollar/counterfactual cost):

- **Lesson**: `<one sentence>`
  - **Anchor**: `<dated incident in this cluster>`
  - **Cost / counterfactual**: `<dollar figure OR "X happened that wouldn't have without doctrine">`
  - **Promotion candidate**: yes / no (graduates if anchor + cost both present, AND threshold met per E1/E2: single-incident >$3K OR three firings across separate windows)
  - **Routes to**: `<lesson registry entry, methodology audit, or memory edit>`

---

## §7 — Open follow-ups

- `<follow-up #1>` — owner, target date.
- `<follow-up #2>`
- ...

---

## §8 — Audit hooks (post-mortem self-check)

- **File presence**: this file at `docs/methodology_audit/parallel_doctrine_cluster_001.md` triggers §Promotion gate review.
- **Cross-reference**: cite this post-mortem from doctrine doc's §Promotion section once filled.
- **Notion mirror**: link to this post-mortem from Command Center under Methodology section.
- **Quarterly review**: re-read on next methodology audit; if §6 lessons remain unintegrated into doctrine or memory, the post-mortem is decaying.
