# Q-CORR-1.3 — Guardian-family Silver (XAGUSD) Pepperstone-TV feed substitution (Pre-Q DRAFT)

**Status:** `OPEN — DRAFT (pre-lock)`
**Draft date:** 2026-05-13
**Parent:** Q-CORR-1.2 (Silver WFO admission gate; halted per its §15 fail-rule)
**Predecessor disposition:** Q-CORR-1.2 transitions to `SUPERSEDED` at Q-CORR-1.3 LOCK (see OPEN ITEM I for closure record convention).
**Loop:** Inquire-phase Pre-Q — binary methodology decision about feed substitution + revision tuple under doctrine constraints. **Not** a strategy admission run; **not** portfolio lock; **not** a re-MC.
**Artifact path:** flat brief at [`docs/briefs/Q-CORR-1.3-guardian-family-silver-pepperstone-feed-substitution.md`](Q-CORR-1.3-guardian-family-silver-pepperstone-feed-substitution.md) (subdir convention to be confirmed at lock — see OPEN ITEM I).

---

## §0 Rule-0 reads (production + load-bearing artifacts)

**Authoring note:** this DRAFT was authored in a web-Claude session without filesystem access. Every path below is marked `[§0-pending — read in Claude Code session before lock]`. The parent `multi_firm_operations` session MUST `view` each path with `git log --follow -n 1 -- <path>` confirming commit/timestamp and re-paste anchors into this section BEFORE LOCK. Per brief-authoring SKILL.md Rule 0 sub-rule: §0 without verification anchors decays to ceremony — do not lock without populating them.

Paths to read at lock-time Phase 0:

- [`firm_rules.py`](../../firm_rules.py), [`accounts.py`](../../accounts.py), [`dd_protection.py`](../../dd_protection.py) — operational risk layer (context only; Silver admission is orthogonal; no edits proposed). **[§0-pending]**
- [`docs/rule_0.md`](../rule_0.md) — audit-first discipline. **[§0-pending]**
- [`docs/methodology/regime_robustness_gate.md`](../methodology/regime_robustness_gate.md) — bootstrap pattern; gate inheritance from Q-CORR-1.2 §14 carries forward modulo OPEN ITEM D recalibration. **[§0-pending]**
- [`docs/briefs/Q-CORR-1.2-guardian-family-silver-wfo.md`](Q-CORR-1.2-guardian-family-silver-wfo.md) — parent Pre-Q; LOCKED 2026-05-13. Quote §15 fail-rule, §14 gates, §6.5 train-selection lock semantic verbatim where this brief inherits or supersedes. **[§0-pending]**
- [`docs/spec/wfo-runner-v0.md`](../spec/wfo-runner-v0.md) — Path B orchestration shell; feed-agnostic at the shell level. **[§0-pending]**
- [`docs/spec/wfo-runner-v0-adversarial-tests.md`](../spec/wfo-runner-v0-adversarial-tests.md) — discipline-falsifier tests. Carry forward unchanged. **[§0-pending]**
- [`CLAUDE.md`](../../CLAUDE.md) — "Public-clone posture" section AND "Vendor-data integrity gate" section. **[§0-pending]**
- user memory `feedback_two_tier_canonical_pepperstone_oanda.md` — two-tier canonical rule semantic (lives outside the repo at user-auto-memory storage; in-repo citations recorded in §1 doctrine #2). **[§0-pending — confirm file exists at user-memory path; record `stat`-style last-modified timestamp at lock-time Phase 0]**
- [`lib/correlation.py`](../../lib/correlation.py) — zero-fill semantic; feed-agnostic at function level. **[§0-pending]**
- [`lib/regime_bootstrap.py`](../../lib/regime_bootstrap.py) — bootstrap implementation; feed-agnostic. **[§0-pending]**
- [`data/tv_exports/pepperstone/SHA256SUMS`](../../data/tv_exports/pepperstone/SHA256SUMS) — confirm `_13fad` Gold comparator digest `e38e8fe80419a286666898e8cae41a3be796277844367b7f1dfdcc3a0feba124` still present. Required for OPEN ITEM B inheritance vs replacement decision. **[§0-pending]**
- [`strategies/MANIFEST.sha256`](../../strategies/MANIFEST.sha256) — Pine v5.5 source hash pin. **Reactivates as load-bearing if OPEN ITEM A resolves to A.ii (Path A);** non-blocking otherwise. **[§0-pending]**
- [`data/bar_data/XAGUSD.csv`](../../data/bar_data/XAGUSD.csv) — OANDA-pulled M15 bar witness `2022-01-02T23:00Z → 2026-04-19T23:45Z` (100,865 bars, no intra-week gaps in Q-CORR-1.2 fold window). **Not yet manifest-tracked.** If OPEN ITEM A resolves to A.ii, this file requires `scripts/check_data_manifests.py --regenerate` in the same commit per vendor-data integrity gate. **[§0-pending]**

**Surrounding-context sub-rule:** when citing a specific line from any of the above, the §0 reader at lock-time reads ±20 lines of surrounding context, not the line in isolation. Cross-ref grep before declaring anything cruft.

---

## §0.5 Phase 0 — Root-cause confirmation (pre-lock blocker)

**This section is a precondition for LOCK, not part of execution.** Q-CORR-1.3 cannot lock with the substitution decision until Phase 0 produces a determinate root cause for Pepperstone TV XAGUSD M15 bar-history insufficiency.

**Three candidate causes (Joshua's 2026-05-13 observation; not yet diagnosed):**

- **Cause-1 (most likely):** Pepperstone broker-side feed truncation on the TV connector. Non-transient.
- **Cause-2:** TV plan-tier mismatch vs the era when Q-CORR-1.1 ran. Transient (resolvable by plan change or wait).
- **Cause-3:** Pepperstone symbol-routing change (`XAGUSD` vs `XAGUSD.a` or similar). Potentially transient (resolvable by symbol selection on TV chart).

**Phase 0 reconnaissance steps** (Joshua-executed in TV; not Claude-executable):

1. On TV chart, set symbol `PEPPERSTONE:XAGUSD`, timeframe 15m; scroll to earliest visible bar; record earliest-bar date.
2. Try `PEPPERSTONE:XAGUSD.a` (if exposed by Pepperstone TV) — record earliest-bar date.
3. Cross-check `OANDA:XAGUSD`, `TVC:SILVER`, `FOREXCOM:XAGUSD` earliest-bar dates as availability witnesses.
4. Compare against Q-CORR-1.2 fold window start `2022-01-11`. If Pepperstone-TV earliest bar postdates that, Cause-1 confirmed unless ruled out by 2/3.

**Phase 0 verdict feeds OPEN ITEM A.** A determinate verdict is a hard precondition for LOCK; per §5 forbidden moves, no feed substitution may be pre-committed before Phase 0 completes.

---

## §1 Context

Q-CORR-1.2 (LOCKED 2026-05-13) is a Path B (TradingView-native) walk-forward admission gate for Guardian-family on Silver, with comparator-CSV semantics anchored to the Pepperstone TV export `Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-12_13fad.csv`. Its §15 pre-flight item "Spot-check Pepperstone TV: XAGUSD 15m availability **2022-01-11 → 2026-04-20** (or longer)" fired its falsifier on 2026-05-13: Pepperstone TV XAGUSD M15 visible-history is shorter than the locked fold window.

Q-CORR-1.2 §15 closing paragraph routes this exact situation:

> "If any item fails, halt. If the fix changes methodology (gates/grid), open Q-CORR-1.3 — do not amend Q-CORR-1.2 mid-flight."

Q-CORR-1.3 is that new Pre-Q. It does not propose to back-port any fix into Q-CORR-1.2 (forbidden by §5 below); it asks what doctrine-compliant path forward exists, surfaces the choice-points, and defers binding decisions to Joshua's LOCK pass after Phase 0 completes.

**Binding doctrine inherited from `multi_firm_operations`:**

1. **Rule 0** ([`docs/rule_0.md`](../rule_0.md)) — production reads before brief authorship.
2. **Two-tier canonical rule** (canonical: user memory `feedback_two_tier_canonical_pepperstone_oanda.md`; in-repo citations: `docs/adr/2026-05-03-sentinel-gate-decision.md:135`, `docs/briefs/bust_attribution_flip.md:86,122`, `docs/methodology/findings/2026-05-03_usdchf_h4_sentinel_gate.md:162`): *"OANDA findings can route Action; Joshua validates in TradingView before code/lock change. CLAUDE.md headline MC stays Pepperstone-anchored."* Implication for this Pre-Q: an OANDA-only execution path **cannot directly produce a portfolio-promotion lock verdict**. Q-CORR-1.3's output must route to Pepperstone-TV-native confirmation before any Silver lock decision; this shapes OPEN ITEM A and Gate 3 below.
3. **Public-clone posture** (CLAUDE.md) — Pine v5.5 source is gitignored, hash-pinned in `strategies/MANIFEST.sha256`. Path A re-implementation needs source bytes; Q-CORR-1.2 §6 closed this concern only because Path B was chosen. If OPEN ITEM A resolves to A.ii, the concern reactivates as a load-bearing constraint on how source is provided to the implementation environment.
4. **Regime-robustness gate** ([`docs/methodology/regime_robustness_gate.md`](../methodology/regime_robustness_gate.md)) — 6mo block bootstrap + half-panel split. Q-CORR-1.3 inherits Q-CORR-1.2 §14 Gates 9/10 in principle; numerical anchors may recalibrate per OPEN ITEM D.
5. **Vendor-data integrity gate** (CLAUDE.md) — any new comparator CSV or third-party bar file requires `scripts/check_data_manifests.py --regenerate` in the same commit as the bytes. Binds OPEN ITEMS A.ii and B.

---

## §2 Question

What feed substitution (if any) and methodology revisions preserve Q-CORR-1.2's admission-gate intent for Guardian-family on Silver, given Pepperstone TV XAGUSD M15 bar-history is insufficient for the locked fold window, **without** violating the two-tier canonical rule, public-clone posture, vendor-data integrity gate, or regime-robustness methodology?

(Pre-Q gate test, per brief-authoring SKILL.md §35 check #5: the question names the symptom — Pepperstone TV bar-history insufficiency, doctrine constraint — not a specific fix. "Feed substitution (if any)" is the question domain, not a pre-committed decision.)

---

## §3 Scope / non-goals

- **In scope:** Phase 0 root-cause classification; feed-substitution choice (A.i/A.ii/A.iii); methodology-revision tuple (X′, comparator identity, §14 floor portability, fold spec window); Q-CORR-1.2 closure record convention; pre-registered downstream gate execution under the chosen substitution.
- **Out of scope for Q-CORR-1.3:**
  - Any modification to Q-CORR-1.2 in place (forbidden by its §15 + this brief's §5).
  - Changes to locked Gold v5.5 / DJ30 v4.5 / Aegis v4.3 / NAS100 v1 strategy code or parameters.
  - Portfolio-MC anchor or `dd_protection` constant changes — Silver admission is upstream and orthogonal.
  - Path A wide optimization (a successor Q-CORR-1.4 if and only if Q-CORR-1.3 RESOLVED via H1-substitute).
  - Q-CORR-1.1 re-litigation — the X = ρ + 0.10 methodology and zero-fill correlation semantic are doctrine-layer and carried forward unchanged.

---

## §4 Falsifiable hypothesis

**H1 (parameterized over Phase 0 outcome and feed choice):** There exists a doctrine-compliant path forward from the operational fact (Pepperstone TV XAGUSD M15 bar-history insufficient for the Q-CORR-1.2 locked fold window `2022-01-11 → 2026-04-20`). The path is one of:

- **H1-resume:** Phase 0 identifies a transient cause (Cause-2: TV plan-tier; Cause-3: symbol-routing variant exposes deeper history). Fixing the cause restores Pepperstone TV bar-history sufficient for the locked fold window. Q-CORR-1.3 closes; Q-CORR-1.2 resumes unchanged (no substitution needed).
- **H1-substitute:** Phase 0 identifies a non-transient cause (most likely Cause-1: Pepperstone broker-side TV truncation). A feed substitution `F ∈ {A.i, A.ii, A.iii}` and methodology revision tuple `R_F = (X′_F, comparator_F, §14_floors_F, fold_spec_F)` is registered that (a) is policy-compliant under the two-tier canonical rule, (b) preserves Q-CORR-1.2's admission-gate intent (PF/WR/DD/MFE-MAE/correlation gate concepts), and (c) when executed downstream on the substituted substrate, produces at least one Coarse-grid configuration clearing all F-anchored §14 gates.

**¬H1 (FALSIFIED):** Phase 0 yields no determinate cause within the reconnaissance scope above; OR Phase 0 yields a non-transient cause AND no doctrine-compliant `(F, R_F)` exists; OR a chosen `(F, R_F)` is executed downstream and **no** Coarse-grid configuration clears the F-anchored §14 gates AND no two-tier-compliant fallback (e.g., A.iii two-phase confirmation) exists.

---

## §5 Forbidden moves

These are moves the author genuinely considered or was tempted by — they are not strawmen. The check (per brief-authoring SKILL.md trap #4): removing each item below would change behavior, so each is load-bearing.

1. **Mid-flight amendment of Q-CORR-1.2** to back-port the feed fix. Explicitly forbidden by Q-CORR-1.2 §15 closing paragraph: *"If the fix changes methodology (gates/grid), open Q-CORR-1.3 — do not amend Q-CORR-1.2 mid-flight."* Q-CORR-1.3 supersedes; Q-CORR-1.2 transitions to `SUPERSEDED` per OPEN ITEM I.
2. **Pre-committing to A.i, A.ii, or A.iii before Phase 0 produces a determinate root cause.** A.i/A.iii are policy-compliant only conditional on Phase 0 identifying a non-transient Cause-1; A.ii reactivates the public-clone posture concern; A.iii is only required if doctrine #2 (two-tier canonical rule) forces a screening/confirmation split.
3. **Silent X′ inheritance from Q-CORR-1.2.** Q-CORR-1.2 §4.1 set X′ = 0.10 = X − 0.023 = (ρ_DJNAS + 0.10) − 0.023 against the **Pepperstone DJ30/NAS pair**. If feed changes, the ρ_DJNAS baseline may shift on the new feed; X′ may require re-derivation. Inheriting X′ unchanged is permitted only if accompanied by an explicit "feed-change ρ-stability" justification recorded in §11/§14 at LOCK.
4. **Comparator-CSV identity change without re-pin in manifest.** OPEN ITEM B forces a binary B.i (keep `_13fad` Pepperstone Gold) vs B.ii (re-export Gold on matching feed; re-pin SHA). Whichever is chosen, the new run manifest's `comparator_csv_sha256` field must carry the full 64-hex digest from the corresponding `SHA256SUMS` line; truncation is a §14 Gate 3 falsifier in Q-CORR-1.2 lineage and carries forward.
5. **Declaring a Lock-class verdict on an OANDA-only (or any non-Pepperstone-TV) execution path.** Doctrine #2 prohibits this. The maximum verdict-class achievable on a non-Pepperstone-TV execution is **Action-class** (screening); Lock-class requires a Pepperstone-TV confirmation phase, which is the A.iii structure. If A.i is chosen (TV-native non-Pepperstone feed), A.iii's two-phase wrapper is the policy-compliant containment.
6. **Relaxing §14 floors** (PF ≥1.50, WR ≥15%, DD ≤8%, p05 PF ≥1.30, MFE/MAE >2.0) without an explicit "why this floor moves on the new feed" justification per OPEN ITEM D. Floors are presumptively portable; the burden of proof is on the relaxation.
7. **Inlining Pine source** in any artifact eligible for the public-clone path. Reactivated as load-bearing if A.ii. Pine bytes must reach the implementation environment via a scoped private workspace; no paste into briefs, ADRs, commit messages, or CC handoffs that may be cloned.
8. **Manifesting `data/bar_data/XAGUSD.csv` (OANDA bars) without `scripts/check_data_manifests.py --regenerate` in the same commit as any introduction into a run manifest.** Vendor-data integrity gate. Currently the file is parked but not manifest-tracked; promotion to manifest-tracked status is a separate commit hygiene step that A.ii would force.
9. **Treating the OANDA-pulled bar witness (100,865 weekday M15 bars) as Lock-class evidence in itself.** It establishes third-party availability of bar coverage for the fold window; it does not establish Pepperstone-TV bar-quality equivalence. A.i/A.iii may use it as a screening-substrate ground truth; Lock-class verdicts still require Pepperstone-TV.
10. **Multi-question creep.** Q-CORR-1.3 has one parent question (§2). OPEN ITEMS A–J are sub-decisions Joshua resolves at LOCK; they do not justify spawning parallel Pre-Qs (per brief-authoring SKILL.md trap #11, parent-Q convention applies).

---

## §6 Gate criteria

**LOCK-time scaffolding note:** §6 is in pre-lock form. At LOCK, Joshua selects from OPEN ITEMS A–J and the gates below resolve to concrete pinned values (paralleling Q-CORR-1.2's §11–§14 lock pass).

Gates are stratified into three classes; the overall verdict requires **all three classes** to pass simultaneously:

### §6.A — Phase 0 cause-identification gates (procedural)

- **Gate A.1 (RESOLVED requires):** Phase 0 reconnaissance produces a determinate root cause: **Cause-1**, **Cause-2**, **Cause-3**, OR a novel cause documented with reproducible reconnaissance steps. (`§0.5` steps 1–4 executed; results recorded.)
- **Gate A.2 (RESOLVED requires):** If Cause-2 or Cause-3, Joshua confirms by direct test (plan-tier change; alternate symbol selection on TV chart) whether Pepperstone-TV bar-history becomes sufficient. Binary: sufficient → H1-resume; insufficient → H1-substitute.
- **FALSIFIED if:** Phase 0 reconnaissance is inconclusive AND no determinate cause is named.

### §6.B — Substitution-decision gates (procedural; only fire if H1-substitute)

- **Gate B.1 (RESOLVED requires):** Chosen feed F is policy-compliant under the two-tier canonical rule. If F is Pepperstone-TV (impossible under H1-substitute by definition), trivial. If F is non-Pepperstone TV (A.i), the brief is structured as two-phase admission (A.iii wrapper) with the F-execution producing screening/Action-class and a deferred Pepperstone-TV confirmation phase producing Lock-class.
- **Gate B.2 (RESOLVED requires):** New run manifest declares the chosen feed identity explicitly (e.g., `chart_feed: "OANDA:XAGUSD"` field added to `run_manifest.json` schema), AND `comparator_csv_sha256` is full-64-hex per the OPEN ITEM B choice.
- **Gate B.3 (RESOLVED requires):** If A.ii, Pine source provision pathway is documented (private scoped workspace; no public-clone leakage).
- **Gate B.4 (RESOLVED requires):** X′ recalibration decision per OPEN ITEM C is recorded in §11/§14 with justification (recompute on new feed vs explicit inheritance with ρ-stability evidence).
- **Gate B.5 (RESOLVED requires):** §14 floor portability decision per OPEN ITEM D is recorded with justification (inheritance vs re-anchoring to new-feed Q-CORR-1.1-equivalent reference).
- **FALSIFIED if:** Any of B.1–B.5 cannot be satisfied within the chosen substitution.

### §6.C — Downstream execution gates (numerical; inherited from Q-CORR-1.2 §14, modulo OPEN ITEM D recalibration)

Inherited verbatim from Q-CORR-1.2 §14 except where OPEN ITEM D recalibrates floors. Subject to F-anchored recomputation per OPEN ITEM C (Gate C.6 below):

- **Gate C.1:** Run manifest `grid_hash` matches the LOCK-pinned value (TBD — see OPEN ITEM E; either inherited `a8fdd34e…` if grid unchanged, or new hash if grid resized).
- **Gate C.2:** Run manifest `fold_spec_hash` matches the LOCK-pinned value (TBD — likely inherited `5591f024…` if fold window is supported by the substituted feed, else re-derived).
- **Gate C.3:** Run manifest `comparator_csv_sha256` equals the full 64-hex of the OPEN-ITEM-B-selected comparator (`e38e8fe8…` if B.i, else new SHA after re-export and re-pin).
- **Gate C.4:** Path B procedural discipline: `scripts/wfo/audit_path_b_ordering.py` returns PASS. (Feed-agnostic; carries forward.)
- **Gate C.5:** `assert_oos_matches_lock` passes per OOS file. (Feed-agnostic.)
- **Gate C.6:** OOS **PF ≥ 1.50**, **WR ≥ 15%**, **DD ≤ 8%**, **p05 PF ≥ 1.30**, **MFE/MAE > 2.0** (Q-CORR-1.2 §14 Gates 6–11, presumptively portable per §5 forbidden move #6; reanchor only with OPEN ITEM D justification).
- **Gate C.7:** OOS daily Net P&L Pearson correlation with the OPEN-ITEM-B-selected comparator ≤ **X′_F** (the OPEN ITEM C value).

### Aggregate verdict

- **RESOLVED:** Either (H1-resume: §6.A Gate A.2 → sufficient) OR (H1-substitute: §6.A determinate cause + §6.B all pass + §6.C all pass on substituted substrate).
- **FALSIFIED:** §6.A inconclusive, OR §6.B cannot be satisfied, OR §6.C any standalone gate fails AND no two-tier-compliant fallback exists.
- **AMBIGUOUS:** Phase 0 produces a partial cause (e.g., Cause-1 + Cause-3 both partially apply); §6.C correlation gate falls in `(X′_F, X′_F + 0.05]` AND other §6.C gates pass; OR §6.B is satisfied but downstream execution surfaces a discipline failure (§14 Gates 4/5 fail catastrophically) → close AMBIGUOUS, no Lock-class verdict, document next-step decision.

---

## §7 Acceptance (pointer)

Acceptance procedures for the downstream execution (when H1-substitute is chosen) parallel Q-CORR-1.2 §7 with feed-substituted artifacts:

- §7.1: Phase 0 reconnaissance log committed to `docs/notes/Q-CORR-1.3-phase0-cause-id.md` (or similar) **before** LOCK.
- §7.2: If A.ii, a Silver-on-new-feed reference run reproducing Q-CORR-1.1 amendment §7's metric shape (i.e., a Silver Q-CORR-1.1-equivalent on the substituted feed). Anchor numbers TBD per OPEN ITEM D — likely **not** Pepperstone's `238 / 1.613 / 11.34% / 11.52%` (those are Pepperstone-anchored).
- §7.3: Selection-bias smoke test (Q-CORR-1.2 §7.4 carries forward).
- §7.4: §10 audit hooks pass.

---

## §10 Audit hooks

Runnable greps/commands. Final pinned values resolve at LOCK; the structure below is feed-agnostic.



```bash
# Verify chosen comparator CSV digest in SHA256SUMS (OPEN ITEM B)
# If B.i (inherit Pepperstone _13fad Gold):
grep "e38e8fe80419a286666898e8cae41a3be796277844367b7f1dfdcc3a0feba124" data/tv_exports/pepperstone/SHA256SUMS
# Expected: line match

# If B.ii (re-export Gold on substituted feed):
grep "<new-comparator-sha256>" data/tv_exports/<feed_dir>/SHA256SUMS
# Expected: line match (SHA TBD at LOCK)

# Verify run manifest declares chosen feed identity explicitly
python -c "import json; m = json.load(open('scripts/wfo/runs/<run_id>/run_manifest.json')); \
  assert 'chart_feed' in m and m['chart_feed'] != ''; print(m['chart_feed'])"
# Expected: matches OPEN ITEM A LOCK selection

# Verify grid_hash and fold_spec_hash (LOCK values per OPEN ITEM E)
python scripts/wfo/grid_hash.py scripts/wfo/examples/grid.json
# Expected: matches OPEN ITEM E LOCK value (a8fdd34e… if unchanged from Q-CORR-1.2)
python scripts/wfo/grid_hash.py scripts/wfo/examples/fold_spec.json
# Expected: matches OPEN ITEM E LOCK value (5591f024… if unchanged from Q-CORR-1.2)

# Verify Path B procedural discipline (feed-agnostic, carries forward from Q-CORR-1.2 §10)
python scripts/wfo/audit_path_b_ordering.py scripts/wfo/runs/<run_id>/run_manifest.json
# Expected: PASS

# Verify Q-CORR-1.2 closure record exists (OPEN ITEM I)
test -f docs/briefs/Q-CORR-1.2/closure.md || test -f docs/rejected_candidates.md
# Expected: at least one path exists with closure entry

# If A.ii, verify OANDA bar file is manifest-tracked
python scripts/check_data_manifests.py --check data/bar_data/XAGUSD.csv
# Expected: manifest entry present with SHA256
```





---

## §11+ — Lock scaffolding (populated at LOCK only)

DRAFT placeholder. At LOCK Joshua populates a Q-CORR-1.2-§11-style table with the resolved OPEN ITEMS:

| Item | Locked value | OPEN ITEM ref | Source |
|------|--------------|---------------|--------|
| Phase 0 root cause | TBD | A | `docs/notes/Q-CORR-1.3-phase0-cause-id.md` |
| Feed substitution F | TBD (resume / A.i / A.ii / A.iii) | A | §0.5 + Joshua decision |
| Comparator identity | TBD (B.i: `_13fad` / B.ii: new) | B | OPEN ITEM B |
| X′_F | TBD (inherit 0.10 / recompute) | C | OPEN ITEM C |
| §14 floors | TBD (inherit / re-anchor) | D | OPEN ITEM D |
| `grid_hash` | TBD (`a8fdd34e…` if unchanged) | E | OPEN ITEM E |
| `fold_spec_hash` | TBD (`5591f024…` if unchanged) | E | OPEN ITEM E |
| Pine source pathway | TBD (N/A unless A.ii) | H | OPEN ITEM H |

---

## Pre-Lock Checklist — OPEN ITEMS A–J

Joshua must resolve every box below before LOCK. Each item is a real fork the brief deliberately does NOT pre-decide:

- [ ] **A. Feed source.** Phase 0 verdict (Cause-1 / Cause-2 / Cause-3 / novel) drives feed choice:
  - [ ] **A.i** — TV-native deeper-history feed (e.g., `OANDA:XAGUSD`, `TVC:SILVER`, `FOREXCOM:XAGUSD`). Minimum methodology delta; comparator-CSV identity changes per OPEN ITEM B.
  - [ ] **A.ii** — Python re-impl on OANDA REST bars (Path A). Reactivates public-clone posture / Pine source access concern. Larger methodology delta.
  - [ ] **A.iii** — Two-phase admission: A.i drives screening (Action-class per doctrine #2); a Pepperstone-on-TV confirmation re-run drives Lock-class verdict when Pepperstone-TV bars become available. **Most policy-compliant given doctrine #2.**
  - [ ] **A.iv (resume)** — Phase 0 identifies a transient cause; substitution not needed.

- [ ] **B. Comparator series identity.**
  - [ ] **B.i** — Keep Pepperstone `_13fad` Gold comparator; accept feed-mismatch noise (cross-feed correlation confound).
  - [ ] **B.ii** — Re-export Gold v5.5 on the matching substituted feed; re-pin SHA in the new feed-specific `SHA256SUMS`; commit bytes + manifest regeneration in same commit per vendor-data integrity gate.

- [ ] **C. X′ recalibration.** Q-CORR-1.2 X′ = 0.10 was calibrated against the Pepperstone DJ30/NAS pair.
  - [ ] **C.recompute** — Re-derive ρ_DJNAS on substituted feed; X′_F = (ρ_DJNAS_F + 0.10) − 0.023.
  - [ ] **C.inherit** — Keep X′ = 0.10 with explicit ρ-stability justification (cross-feed ρ shift evidence).

- [ ] **D. §14 PF/WR/DD/p05 floor portability.** Q-CORR-1.2 §14 floors anchored to Pepperstone Q-CORR-1.1 reference numbers (238 / 1.613 / 11.34% / 11.52%) and `bootstrap_seed=7, n_panels=100, block_months=6` p05 anchor 1.05 ± 0.02.
  - [ ] **D.inherit** — Floors carry forward unchanged with "floors are presumptively feed-portable" rationale.
  - [ ] **D.reanchor** — Re-run a Q-CORR-1.1-equivalent reference on substituted feed; re-anchor floors to that reference; document drift.

- [ ] **E. Fold spec window.**
  - [ ] **E.inherit** — Keep `2022-01-11 → 2026-04-20` if substituted feed covers it (OANDA bar witness confirms this for the OANDA path).
  - [ ] **E.tighten** — Adjust window if substituted feed has narrower history; re-derive `fold_spec_hash` from new JSON.
  - [ ] **E.regrid** — If substituted feed shifts the parameter landscape enough that the §12 4-dim Cartesian is no longer mechanistically anchored (e.g., session-time semantics differ on a non-Pepperstone feed), re-freeze grid → new `grid_hash`. Otherwise carry forward `a8fdd34e…`.

- [ ] **F. Correlation comparator semantic.** Zero-fill on `bdate_range` between min/max exit dates (Q-CORR-1.1 amendment §7). Carry forward unchanged at the function level; flag re-validation on new feed for UTC-vs-NY exit-date attribution edge cases.

- [ ] **G. OOS protection.** §6.5 `train_selection_lock.json` + `audit_path_b_ordering.py` discipline is feed-agnostic. Carry forward unchanged.

- [ ] **H. Pine source access (only if A.ii).** Pine v5.5 source is gitignored; `MANIFEST.sha256` pins hashes only. A.ii requires source bytes for re-implementation. Specify provision pathway:
  - [ ] Private scoped workspace (named: TBD)
  - [ ] No paste into any public-clone-eligible artifact (briefs, commit messages, CC handoffs)
  - [ ] N/A — A.ii not selected.

- [ ] **I. Q-CORR-1.2 disposition.** Q-CORR-1.3 supersedes Q-CORR-1.2 at LOCK. Closure record destination:
  - [ ] `docs/briefs/Q-CORR-1.2/closure.md` (subdir convention)
  - [ ] `docs/rejected_candidates.md` (flat convention; Q-CORR-1.2 was not falsified on strategy grounds — flag this if used)
  - [ ] Inline addendum to Q-CORR-1.2 marking `Status: SUPERSEDED by Q-CORR-1.3` (preferred if Q-CORR-1.2's flat-brief convention is house style)
  - [ ] Confirm convention by checking lineage: `ls docs/briefs/Q-CORR-1.1*` and similar to see how prior supersession was handled.

- [ ] **J. Cause-#1 confirmation as Phase 0 (separate from §15-style pre-flight).** Phase 0 is a **pre-LOCK** blocker for Q-CORR-1.3; §15-style pre-flight (when applicable to the substituted execution) is a **pre-run** blocker after LOCK. These two checklists must not collapse into one.

---

## Items I could not verify (must be confirmed at §0 read pass)

The following claims in this DRAFT depend on filesystem reads I could not perform from web-Claude. Mark them as the parent session's §0 verification target before LOCK:

- That Q-CORR-1.2 §15 closing paragraph reads verbatim as quoted in §1 (handoff source; cross-check against the LOCKED file).
- That `data/tv_exports/pepperstone/SHA256SUMS` still contains the `_13fad` row with digest `e38e8fe8…` (no rotation since 2026-05-13 LOCK).
- That `lib/correlation.py` and `lib/regime_bootstrap.py` are at the paths cited (no refactor since 2026-05-13).
- That `data/bar_data/XAGUSD.csv` exists with the 100,865-bar OANDA-pull described in the handoff (and that it is not yet manifest-tracked).
- That CLAUDE.md `:99` "Public-clone posture" and `:114` "Vendor-data integrity gate" sections read as paraphrased in §1 doctrines #3 and #5.
- That the two-tier canonical rule's in-repo citations in §1 doctrine #2 (`docs/adr/2026-05-03-...md:135`, `docs/briefs/bust_attribution_flip.md:86,122`, `docs/methodology/findings/2026-05-03_usdchf_h4_sentinel_gate.md:162`) still resolve to the cited line numbers (verify with `grep -n "two-tier canonical"` after §0 read).
- That `strategies/MANIFEST.sha256` exists and pins Pine source hashes (relevant only if OPEN ITEM A resolves A.ii).

If any of these is inaccurate at §0 read time, this DRAFT needs revision before LOCK — flag and pause rather than silently correcting.

---

## Verification block (pre-LOCK)



```bash
# Discipline checks (mechanical)
python scripts/check_brief.py docs/briefs/Q-CORR-1.3-guardian-family-silver-pepperstone-feed-substitution.md --type inquire
# Expected: PASS on §0 populated, §4 falsifier, §5 forbidden moves, §6 binary gates, §10 audit hooks runnable.
# Known limitation: §0 verification anchors are pending until parent-session reads — check_brief may flag as
#   FAIL until §0 anchors are populated; that is the EXPECTED state for this DRAFT.

# Production-source verification (Rule 0 confirmation; parent-session executes pre-LOCK)
grep -n "SUPERSEDED\|LOCKED" docs/briefs/Q-CORR-1.2-guardian-family-silver-wfo.md
# Expected: LOCKED present; SUPERSEDED added only at Q-CORR-1.3 LOCK time.

grep "e38e8fe8" data/tv_exports/pepperstone/SHA256SUMS
# Expected: line match (confirms _13fad comparator still pinned).

git log --follow -n 1 -- lib/correlation.py
git log --follow -n 1 -- lib/regime_bootstrap.py
# Expected: commits postdating 2026-05-13 LOCK only if a refactor occurred; report timestamp into §0.

ls data/bar_data/XAGUSD.csv && wc -l data/bar_data/XAGUSD.csv
# Expected: file exists; row count consistent with 100,865 bars + header.

# Cross-reference verification (cited facts match canonical sources)
grep -n "two-tier canonical" \
  docs/adr/2026-05-03-sentinel-gate-decision.md \
  docs/briefs/bust_attribution_flip.md \
  docs/methodology/findings/2026-05-03_usdchf_h4_sentinel_gate.md
# Expected: matches at :135, :86, :122, and :162 respectively (line numbers per §1 doctrine #2).
```



Pre-Lock Checklist OPEN ITEMS A–J are not part of this verification block — they resolve at LOCK, not at DRAFT completion.

---

## Draft authorship notes (for Joshua's review pass)

- **Author scope:** web-Claude session; no filesystem reads; no tool execution against repo state. All paths cited are `[§0-pending]` until parent-session verification.
- **Lineage:** structure mirrors Q-CORR-1.2 §0–§10; §11+ scaffolding is placeholder (Q-CORR-1.2-style table to be filled at LOCK).
- **Decisions deferred to Joshua:** all of OPEN ITEMS A–J. The DRAFT enumerates the choices and surfaces trade-offs; it does not pre-commit.
- **Cuts I considered and did not make:** (i) collapsing OPEN ITEM A into "default to A.iii since most policy-compliant" — rejected because Phase 0 may produce a transient cause (A.iv resume) that makes the whole substitution unnecessary; (ii) folding §6.A and §6.B into a single procedural-gates block — rejected because Phase 0 is a pre-LOCK blocker while §6.B is a LOCK-time decision audit, and conflating them obscures the temporal ordering.
- **Brief-authoring discipline self-check:** §0 paths listed (anchors pending); §4 falsifier binary; §5 forbidden moves load-bearing; §6 gates produce binary verdicts per class; §2 names symptom not fix; §10 hooks runnable. Trap #11 (multi-question) addressed via parent-Q convention in §5 forbidden move #10.

---

## Revision log

- **Rev 1 (2026-05-13):** Doctrine attribution fix per parent A3 disposition.
  - §1 doctrine #2: removed false CLAUDE.md attribution; added user-memory canonical
    + three in-repo citations per parent session grep evidence.
  - §0 memory-file bullet: replaced "path within repo TBD" with parent A4 convention
    (basename + "user memory" qualifier).
  - "Items I could not verify" #5: split into separate CLAUDE.md and two-tier-rule items
    to prevent re-conflation at §0 read time.
  - No other changes. Status remains `OPEN — DRAFT (pre-lock)`.

- **Rev 2 (2026-05-13):** Residual doctrine-attribution surfaces closed per parent disposition.
  - Verification block: replaced CLAUDE.md grep with multi-path grep against the
    three in-repo citation files registered in §1 doctrine #2 by Rev 1.
  - §0 CLAUDE.md bullet: struck "(two-tier canonical rule)" parenthetical and
    "Strategy Reference" clause; bullet now cites only Public-clone posture (:99)
    and Vendor-data integrity gate (:114) — the two CLAUDE.md sections parent's
    grep evidence confirmed exist.
  - Notes appendix from Rev 1: removed (both flagged items closed; Revision log
    is the active audit trail going forward).
  - No other changes. Status remains `OPEN — DRAFT (pre-lock)`.
