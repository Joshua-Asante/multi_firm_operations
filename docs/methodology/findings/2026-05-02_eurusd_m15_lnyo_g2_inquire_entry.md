# EURUSD M15 LNYO — G2 (PDSB) Inquire-Phase Entry Handoff

**Status:** entry stub for a fresh G2 Inquire-phase session. G1 (NYFBO) closed 2026-05-02 — see kill audit linked in §2.
**Parent brief:** [2026-05-02_eurusd_m15_lnyo_notice.md](2026-05-02_eurusd_m15_lnyo_notice.md)
**G1 sibling stub (predecessor):** [2026-05-02_eurusd_m15_lnyo_inquire_entry.md](2026-05-02_eurusd_m15_lnyo_inquire_entry.md)
**G1 kill audit (load-bearing for §3):** [docs/methodology/archive/gate_audits/2026-05-02_eurusd_m15_h_nyfbo_kill.md](../archive/gate_audits/2026-05-02_eurusd_m15_h_nyfbo_kill.md)
**Why this file exists:** to enforce session isolation and to **avoid** the priming failure mode of the G1 stub. The G1 stub embedded a prose summary of parent brief §3–§8; that pre-loaded the spawn session with the authoring session's framing and weakened the §0 isolation guarantee (G1 audit §0 disclosed slippage). This stub directs the G2 session to read the brief in full, in its own session, before any data work — and gives no prose substitute.
**Out-of-scope reaffirmation:** parent brief §7 binds the G2 Inquire session in full. **Additionally: the parent brief itself is frozen for the duration of the G2 session** (see §4 brief-pinning protocol).
**Loop:** INQHIORI — falsifiable hypothesis (H-PDSB single-config), structural decision, gated promotion, conditional entry behind §3 §0a re-justification.

---

## 1. Spawn prompt for fresh G2 Inquire session

Open a fresh Claude Code session in this repo (worktree or main branch — Inquire reads code, does not modify it) and submit verbatim:

```
Run H-PDSB Inquire-phase falsification (G2 gate) per
docs/methodology/findings/2026-05-02_eurusd_m15_lnyo_notice.md.

Step 0 — version pinning (before any reads):
- Run: git rev-parse HEAD -- docs/methodology/findings/2026-05-02_eurusd_m15_lnyo_notice.md
- Run: git status --porcelain docs/methodology/
- If methodology dir is dirty, ABORT. Do not proceed on a moving brief.
- Record the brief commit hash; embed it in any audit-trail file you write.

Step 1 — read in full, do not skim:
- Parent brief §0–§12 (no shortcuts)
- G1 kill audit at docs/methodology/archive/gate_audits/2026-05-02_eurusd_m15_h_nyfbo_kill.md
- The G2 §0a re-justification requirements in §3 of THIS stub file
- docs/rule_0.md, docs/methodology/observation_routing.md
- All Rule-0 production sources named in parent brief §0; for each Pine
  source, read the FULL entry-condition block containing the dow filter
  (not just the dow line) and state the complete activation predicate
  in own words. Cross-check against the most recent backtest CSV trade
  days to confirm the filter is active in execution, not just coded.

Step 2 — write §0a entry re-justification (this stub §3) into the new
findings file BEFORE any data work. If §0a fails its own audit, abort
to G4. Do not proceed to backtest.

Step 3 — execute Inquire per parent brief §4 H-PDSB, §5 guardrails,
§6 G2 stage gate. All parameters, kill criteria, regime boundaries,
spread model, permutation count, and routing live in the parent brief.
Do not paraphrase them here. Re-derive from the brief in your session.

Out-of-scope (parent brief §7 plus this stub): no edits to Pine,
dd_protection.py, portfolio_mc.py, CLAUDE.md, OR the parent Notice
brief. The brief is frozen for the duration of this Inquire session.
```

---

## 2. Routing reference (parent brief §6 + this stub's stop-rule)

Decision object is the per-regime pass/fail matrix per parent brief §5 #2 (pooled stat is not the headline). Build it across `hike_2022 / hold_2023_24 / ease_2024_26` for kills #1–#6. **Any per-regime FAIL = G2 FAIL.** Pooled and partial passes are recorded for portfolio-merit input but never rescue the gate. Sub-tests (Friday-only Striker correlation, etc.) are diagnostic, not decision-bearing.

- **G2 PASS (all cells, both spread variants per §3 spread-sensitivity requirement):** PDSB becomes primary candidate for the EURUSD M15 slot (NYFBO is dead). Route to **Verify (paper-trade scoping)**. Flag operational concerns from parent brief §5 #7 (08:30 alert latency 2–10s on Alchemy/DXTrade) at Verify entry, not at G2.
- **G2 PASS at 1.0× spread but FAIL at 1.25× spread:** **Conditional pass — MT5 spread validation is a Verify-phase prerequisite.** Do not promote until validated.
- **G2 FAIL — generalizable structural** (event-conditional Hurst gate fired in §3-prescribed §0a diagnostic, OR Hawkes overreaction empirically absent on EURUSD post-data): write kill at `docs/methodology/archive/gate_audits/<YYYY-MM-DD>_eurusd_m15_h_pdsb_kill.md`. **M15-FX stop-rule fires** (below). Route to **G4** — two distinct fade mechanisms have failed structurally in this regime.
- **G2 FAIL — operational only** (kill #6 spread widening, or kill #2 single-trade > 1.5% with otherwise positive edge): write kill, route to **G3 (PDDB Inquire)** — PDDB exits at 08:29 ET pre-release, has no event-window spread exposure, so the operational failure mode does not generalize.
- **G2 FAIL — small-cell only** (kill #5 N < 60): trigger Rule 1 variance inflation per parent brief §5 #5/§4 H-PDSB kill #5 and re-evaluate; if still inconclusive, **defer**, do not fail.

**M15-FX stop-rule (new — applies if G2 FAILS regardless of mode):** the next M15 retail-FX candidate (G3 PDDB, or any successor on a different pair) requires a written brief explaining why the prior is **not** "M15 retail-FX is dead in this spread regime" — specific to whether the prior generalizes from continuous-window fades to (a) event-conditional fades, (b) anticipatory brackets, (c) other mechanism classes. **Default: the prior generalizes, candidate is rejected at the brief stage, no Q-cost spent.** Override requires positive evidence of mechanism-class separability. The G2 kill audit (if it fires) appends this stop-rule as a new sub-row to parent brief §6.

Each gate decision writes its own audit-trail file per parent brief §8 with the brief commit hash recorded.

---

## 3. §0a entry re-justification — required components

The G2 session must author §0a as the head of its findings/kill file **before any data work**. §0a must contain all five components below. If any component is hand-waved or fails its own audit, **abort G2 to G4** without burning Q-cost.

1. **Mechanism distinction (NYFBO vs PDSB).** Cite parent brief §3 cell separation — `(Microstructure overreaction × Fade)` for NYFBO vs `(Post-news × Fade)` for PDSB. The S-collapse already documented these as distinct (driver × mechanism) cells; restate why this distinction is structural and not a relabeling of the same fade mechanism. D-S-A discipline applies (see component 4).

2. **Why Hurst ≈ 0.75 doesn't generalize.** State explicitly: (a) the G1 reading is on an unconditional 24h returns process, (b) PDSB conditions on event-day post-08:30 ET 30-min windows only, (c) Hawkes/Bormetti post-news overreaction is empirically separable from baseline persistence in literature. This argument must hold *before* the diagnostic gate in component 3 is run.

3. **Diagnostic gate before backtest — measurement, not assertion.** Compute conditional Hurst on event-day post-08:30 ET 30-min windows specifically (event calendar from §3 of plan / parent brief §4 H-PDSB hypothesis: NFP, CPI, PCE, retail sales, GDP advance). Use log-returns per memory `feedback_hurst_rs_log_prices_trap.md`. **If event-conditional H ≥ 0.65, abort G2 to G4** — the persistence kill has generalized into the event-conditional window, the §0a justification has falsified itself, and no further H-PDSB work is warranted. Record the measurement and the abort/proceed decision in §0a regardless of outcome.

4. **D-S-A discipline check** per memory `feedback_d_vs_s_collapse_discipline.md`. Explicitly distinguish "different mechanism class" (S-separator — structural compression preserved one candidate per cell) from "should-have-been-deleted" (D-test). PDSB is a separate (driver × mechanism) cell, not a deletion candidate hiding behind a permitted-sounding D label. Reaching for a D framing here would replicate the Iran-Hormuz silent-relabeling pattern.

5. **M15-retail-FX base-rate confrontation.** Repo history is now AUDNZD 4A + H-NYFBO = 0/2 on M15 retail-FX edge surviving realistic spread. Address the prior "M15 retail-FX edge dies in this spread regime." Narrow form for PDSB: H-NYFBO failed on **mechanism (persistence), not on cost** (G1 kill audit §5 — gross edge negative pre-cost). State whether that prior generalizes to event-conditional fades (H-PDSB) or only to continuous-window fades. The §0a does not pass if this is hand-waved or skipped. If §0a cannot answer it positively, abort to G4.

---

## 4. Brief-pinning protocol (Rule 0 applied to the brief itself)

Production code is read from source per Rule 0 to prevent acting on stale memory. The same logic applies to the parent brief: a decision audit-trail anchored to a brief that drifts after the audit is written is no longer falsifiable against its own gate. Step 0 of the spawn prompt enforces this:

- `git rev-parse HEAD -- docs/methodology/findings/2026-05-02_eurusd_m15_lnyo_notice.md` → record the hash.
- `git status --porcelain docs/methodology/` → must be empty. **If dirty, ABORT.** A dirty methodology dir means the brief or a related doc may move during Inquire and the audit-trail loses its anchor.
- The brief commit hash is embedded in the header of any findings or kill-audit file written by the G2 session.
- The parent brief is added to parent brief §7's no-edit list **for the duration of the G2 session**. The brief is frozen — the G2 session may not add cross-links, fix typos, or amend §6 routing rows. Any brief revision is a separate session, separate hash.

Mirror artifact: the G1 kill audit §0 disclosed session-isolation slippage but did not pin the brief hash. Do not repeat that miss here.

---

## 5. Inquire-phase entry checklist (G2)

> G2 Inquire-phase execution is a separate session. Entry into the G2 session requires §1 Step 0 (brief pinning) and §1 Step 1 (parent brief §0 Rule-0 reads) be performed in that session, not inherited from this G2-stub-authoring session.

- [ ] Brief commit hash recorded; methodology dir clean (§4)
- [ ] Parent brief §0–§12 read in full, in-session (no skim, no paraphrase substitute)
- [ ] G1 kill audit read in full, in-session
- [ ] Pine sources read with full entry-condition blocks (regime conditional, EOM gate, session block) — not isolated dow lines; complete activation predicates stated in own words
- [ ] Pine activation predicates cross-checked against most recent backtest CSV trade-day list (filter active in execution, not just coded)
- [ ] §0a written into the new findings file with all five components (§3 of this stub) — abort to G4 if any component fails
- [ ] Spread model provenance section authored in findings file (calibration source, sample window, known divergence vs Pepperstone live, mandatory 1.25× sensitivity)
- [ ] Pepperstone session-conditional spread model loaded from `analysis/eurusd_lnyo/pepperstone_spread.py`
- [ ] Dukascopy M15 EURUSD bid+ask 2022-01-04 → 2026-04-20 loaded from `data/bar_data/EURUSD_dukascopy_m15_bidask_2022-01-04_to_2026-04-20.csv`
- [ ] DST tz-aware timestamps verified at March/November transition zones (IANA `America/New_York`)
- [ ] Three regime sub-periods isolated using **pre-committed** boundaries from parent brief §5 #2 (no Inquire-time tuning of cutpoints — researcher-DOF leakage)
- [ ] H-PDSB single-config falsification with literature-default parameters (parent brief §4 + §5 #9)
- [ ] H-PDSB run twice — at 1.0× and 1.25× spread — both verdicts reported
- [ ] DXY anti-correlation explicit check on Guardian-active days (Mon/Tue/Thu)
- [ ] Striker-active-day (Tue + Fri) conditional correlation check for H-PDSB kill #4; Friday-only sub-test recorded as diagnostic only (does not rescue gate)
- [ ] Aegis Mon/Tue/Wed conditional correlation check (do not pool across full panel)
- [ ] Per-regime decision matrix built across all 6 kill criteria (§2 of this stub) — pooled is reported but not gating; any per-regime FAIL = G2 FAIL
- [ ] Permutation test (≥ 1000 shuffles) gating any pass verdict (parent brief §5 #8)
- [ ] Rule 1 small-cell check: any regime sub-sample n < 25 → variance-inflated CIs (parent brief §5 #5 + §4 H-PDSB kill #5 N ≥ 60 floor)
- [ ] Audit trail file written with brief commit hash embedded; M15-FX stop-rule activation noted if structural fail

---

## 6. Cross-references

- Parent brief: [2026-05-02_eurusd_m15_lnyo_notice.md](2026-05-02_eurusd_m15_lnyo_notice.md) — §0 Rule-0 reads, §3 sub-corpus + S-collapse, §4 H-PDSB hypothesis + 6 kill criteria, §5 10 methodology guardrails, §6 stage gates, §7 out-of-scope, §8 audit-trail commitments
- G1 sibling stub: [2026-05-02_eurusd_m15_lnyo_inquire_entry.md](2026-05-02_eurusd_m15_lnyo_inquire_entry.md)
- G1 kill audit (load-bearing for §3 components 2 + 5): [docs/methodology/archive/gate_audits/2026-05-02_eurusd_m15_h_nyfbo_kill.md](../archive/gate_audits/2026-05-02_eurusd_m15_h_nyfbo_kill.md)
- Rule 0: [docs/rule_0.md](../../rule_0.md)
- D-S-A discipline memory: `feedback_d_vs_s_collapse_discipline.md`
- Hurst trap memory: `feedback_hurst_rs_log_prices_trap.md`
- Observation routing: [docs/methodology/observation_routing.md](../observation_routing.md)
- Loop selection canon: notion.so/34ddc0b53c1181479d7bdecc61f47078
