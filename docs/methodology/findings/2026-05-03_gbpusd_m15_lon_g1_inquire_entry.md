# GBPUSD M15 LON — G1 (H-LORB) Inquire-Phase Entry Handoff

**Status:** entry stub for a fresh G1 Inquire-phase session. Notice authored 2026-05-03 — see parent brief in §6.
**Parent brief:** [2026-05-03_gbpusd_m15_lon_notice.md](2026-05-03_gbpusd_m15_lon_notice.md)
**Parent brief commit hash (record-of-pinning):** `158dc61d1aae7ed87717a7291c43df51c526c9b5` — embed in any audit-trail file written by the G1 session. The session must independently re-derive this with `git rev-parse HEAD -- docs/methodology/findings/2026-05-03_gbpusd_m15_lon_notice.md` and confirm match before any data work.
**Predecessor template (structural mirror for this stub):** [2026-05-02_eurusd_m15_lnyo_g2_inquire_entry.md](2026-05-02_eurusd_m15_lnyo_g2_inquire_entry.md)
**Predecessor kill audits (Rule-0 reads, load-bearing for §3 §0a components 1, 2, 5):**
- [docs/methodology/archive/gate_audits/2026-05-02_eurusd_m15_h_nyfbo_kill.md](../archive/gate_audits/2026-05-02_eurusd_m15_h_nyfbo_kill.md) — fade mechanism class (a) failure record.
- [docs/methodology/archive/gate_audits/2026-05-02_eurusd_m15_h_pdsb_kill.md](../archive/gate_audits/2026-05-02_eurusd_m15_h_pdsb_kill.md) — fade mechanism class (b) failure record + SL-design lesson source.

**Why this file exists:** to enforce session isolation and to repeat the discipline of the G2 PDSB stub — the spawn session must read the parent Notice in full, in its own session, before any data work, and gives no prose substitute. The Notice is the structural commit; this stub is the operational handoff.

**Out-of-scope reaffirmation:** parent Notice §7 binds the G1 Inquire session in full. **Additionally: the parent Notice itself is frozen for the duration of the G1 session** (see §4 brief-pinning protocol).

**Loop:** INQHIORI — falsifiable hypothesis (H-LORB single-config), structural decision, gated promotion, conditional entry behind §3 §0a re-justification.

---

## 1. Spawn prompt for fresh G1 Inquire session

Open a fresh Claude Code session in this repo (worktree or main branch — Inquire reads code, does not modify it) and submit verbatim:

```
Run H-LORB Inquire-phase falsification (G1 gate) per
docs/methodology/findings/2026-05-03_gbpusd_m15_lon_notice.md.

Step 0 — version pinning (before any reads):
- Run: git rev-parse HEAD -- docs/methodology/findings/2026-05-03_gbpusd_m15_lon_notice.md
- Expected hash: 158dc61d1aae7ed87717a7291c43df51c526c9b5
  (recorded in entry stub header). If divergent, ABORT — brief moved
  since stub authoring; restart only after reconciling.
- Run: git status --porcelain docs/methodology/
- If methodology dir is dirty, ABORT. Do not proceed on a moving brief.
- Record the brief commit hash; embed it in any audit-trail file you write.

Step 1 — read in full, do not skim:
- Parent Notice §0–§9 (no shortcuts)
- Predecessor kill audits at
    docs/methodology/archive/gate_audits/2026-05-02_eurusd_m15_h_nyfbo_kill.md
    docs/methodology/archive/gate_audits/2026-05-02_eurusd_m15_h_pdsb_kill.md
  in full (load-bearing for §0a components 1, 2, 5)
- Predecessor Notice at docs/methodology/findings/2026-05-02_eurusd_m15_lnyo_notice.md
  (load-bearing — methodology guardrails carry forward unless parent Notice
  explicitly amends)
- The G1 §0a re-justification requirements in §3 of THIS stub file
- docs/rule_0.md, docs/methodology/observation_routing.md
- All Rule-0 production sources named in parent Notice §0; for each Pine
  source, read the FULL entry-condition block containing the dow filter
  (not just the dow line) and state the complete activation predicate
  in own words. Cross-check against the most recent backtest CSV trade
  days to confirm the filter is active in execution, not just coded.
- dd_protection.py at repo root (single-tier 1.0% / 0.40× scaling)
- Memory anchors: feedback_hurst_rs_log_prices_trap.md
                  feedback_d_vs_s_collapse_discipline.md

Step 2 — write §0a entry re-justification (this stub §3) into the new
findings file BEFORE any data work. If §0a fails its own audit on any
of the 5 components, abort to G3 (skip G2 — see §2 routing). Do not
proceed to backtest. Do not proceed to Phase A diagnostic.

Step 3 — execute Inquire per parent Notice §4 H-LORB single-config,
§5 guardrails (all 13 items), §6 G1 stage gate (Phase A diagnostic →
Phase B backtest). All parameters, kill criteria, regime cutpoints,
spread model, permutation count, and routing live in the parent
Notice. Do not paraphrase them here. Re-derive from the brief in
your session.

Out-of-scope (parent Notice §7 plus this stub): no edits to Pine,
dd_protection.py, portfolio_mc.py, CLAUDE.md, the parent Notice,
the predecessor EURUSD Notice or its audit trail, OR this stub.
The parent Notice is frozen for the duration of this Inquire
session.
```

---

## 2. Routing reference (parent Notice §6 + Phase-A gate + post-G1 stop-rule)

The G1 gate runs in two phases. **Phase A is a measurement gate that runs before any backtest work**; if it aborts, no Phase B is attempted.

### Phase A gate (pre-backtest)

Per parent Notice §1.5 + §6, the Phase-A persistence diagnostic is **conjunctive across three conditions**, all measured on the post-OR window 09:00–11:00 BST log-returns (NOT log-prices, per memory `feedback_hurst_rs_log_prices_trap.md`):

| Condition | Threshold |
|---|---|
| `nolds.hurst_rs` Hurst ≥ 0.50 | canonical estimator |
| inline R/S Hurst ≥ 0.50 | cross-check estimator (dual-implementation per parent Notice §5 #12) |
| lag-1 ACF ≥ 0 | parent Notice §1.5 explicit additional gate |

**Any single condition failing → Phase A ABORT.** Write `<YYYY-MM-DD>_gbpusd_m15_h_lorb_phaseA_abort.md` audit at `docs/methodology/archive/gate_audits/`, embedding parent Notice commit hash. Route to **G2 entry decision** per parent Notice §6 ("Either failing → abort to G2 entry decision (do not run backtest)"). The breakout-class persistence prior has been falsified at the conditioning window; further H-LORB work is not warranted at this configuration.

Record measurement values and abort/proceed decision in §0a regardless of outcome.

### Phase B decision matrix (backtest)

If Phase A passes, run H-LORB single-config per parent Notice §4.2 across the per-regime × per-spread-variant grid:

- Regimes: `hike_2022_23` (2022-01-04 → 2023-08-31), `hold_2023_24` (2023-09-01 → 2024-07-31), `cut_2024_26` (2024-08-01 → 2026-04-20). **Pre-committed BoE-anchored cutpoints — no Inquire-time tuning** per parent Notice §5 #3.
- Spread variants: 1.0× baseline + 1.25× sensitivity (mandatory per parent Notice §4.2 + §5 #1).

Decision object is the per-regime pass/fail matrix across all 8 kill criteria from parent Notice §4.3 (kills #1–#7 + #8 N-floor). **Any per-regime FAIL = G1 FAIL.** Pooled stat is reported but never decision-bearing. Sub-tests (Friday-only Striker correlation, etc.) are diagnostic, not decision-bearing.

### Routing outcomes

- **G1 PASS (all 8 kills × all 3 regimes × both spread variants):** H-LORB becomes primary candidate for the GBPUSD M15 LON slot. Route to **portfolio-merit Inquire** (correlation, allocation sizing, MC re-calibration scope). H-PNCB G2 stub is not authored. Pine implementation remains a post-portfolio-merit deliverable per parent Notice §7.
- **G1 FAIL — generalizable structural** (kill #1 fails all 3 regimes OR kill #7 fails all 3 regimes): write kill audit at `docs/methodology/archive/gate_audits/<YYYY-MM-DD>_gbpusd_m15_h_lorb_kill.md`. **G2 SKIPPED** — H-PNCB inherits the same structural failure (both are post-news-low-density breakout strategies on the same instrument-timeframe; kill criteria #1/#7 are mechanism-class metrics). Route to **G3 (abandon GBPUSD M15)**. **M15-FX stop-rule generalizes** to mechanism class (d) breakout (parent Notice §6 "Stop-rule update on G3"). Track record becomes 0/4 spanning fade × 2 + breakout × 2. The next M15 retail-FX candidate's override surface narrows materially.
- **G1 FAIL — non-structural** (tail #2/#3 OR correlation #4/#5 OR mixed-regime, with edge surviving in at least one regime): write kill audit, route to **G2 (H-PNCB Inquire)**. The breakout mechanism class is not falsified; the OR-anchored implementation is suboptimal. Author H-PNCB G2 entry stub at `docs/methodology/findings/<YYYY-MM-DD>_gbpusd_m15_lon_g2_inquire_entry.md` mirroring this stub's structure.
- **G1 FAIL — small-cell only** (kill #8 N < 60 or per-regime n < 25): trigger Rule 1 variance inflation per parent Notice §5 #8 / §4.3 kill #8 and re-evaluate. If still inconclusive, **defer**, do not fail.

### G1 single-knob escalation (pre-committed per parent Notice §6)

If kill #1 fails on **edge concentration in the late-OR window** — specifically, trades that hit the 11:00 BST time-stop cluster as profitable while trades exiting earlier are net negative — the single permitted post-falsification knob iteration is: **extend time-stop from 11:00 BST to 14:00 BST + Thursday-noon-BST BoE Bank Rate decision-day blackout**. This is a one-knob iteration permitted by parent Notice §5 #9, NOT a G1 grid search. Pre-committing it here means it is not reached for as a face-saving rescue if G1 marginally fails for unrelated reasons (tail, correlation, mixed regime). Any other knob (OR length, SL multiple, RR, DOW filter) is **out of scope** for G1's single-knob escalation.

### Audit-trail file pattern (parent Notice §8)

- G1 PASS: `docs/methodology/archive/gate_audits/<YYYY-MM-DD>_gbpusd_m15_h_lorb_pass.md`
- G1 FAIL: `docs/methodology/archive/gate_audits/<YYYY-MM-DD>_gbpusd_m15_h_lorb_kill.md`
- Phase A abort: `docs/methodology/archive/gate_audits/<YYYY-MM-DD>_gbpusd_m15_h_lorb_phaseA_abort.md`

Each audit must embed the parent Notice commit hash, embed the Phase-A diagnostic results JSON path (when run), reference the parent Notice by relative path, state load-bearing facts of all Rule-0 reads in own words, and reaffirm out-of-scope per parent Notice §7.

---

## 3. §0a entry re-justification — required components

The G1 session must author §0a as the head of its findings/kill file **before any data work** (and before Phase A measurement). §0a must contain all five components below. If any component is hand-waved or fails its own audit, **abort G1 to G3** without burning Q-cost. (G2 is skipped on §0a abort because the §0a falsification — particularly components 1, 2, 5 — is mechanism-class-level and would block H-PNCB equally.)

1. **Mechanism distinction LORB vs failed candidates (NYFBO + PDSB).** Cite parent Notice §3 cell separation: H-LORB is cell 1 `(Microstructure × Breakout)` vs NYFBO `(Microstructure overreaction × Fade)` and PDSB `(Post-news × Fade)`. Restate the structural property: fade requires anti-persistent dynamics (H<0.5 favors); breakout requires persistent dynamics (H>0.5 favors). The two mechanism families bet on opposite features of the price process — they are not opposite-signed parameter choices on the same setup, they are gated on different conditional structures. The S-collapse (parent Notice §3.2) preserved cells 1 and 3 as separate breakout cells per per-cell uniqueness; this distinction is structural and not a relabeling. D-S-A discipline applies (component 4).

2. **Why prior does not generalize from fade to breakout.** Restate parent Notice §1.1–§1.6 as in-session re-derivation:
   - **Mechanism-class separability (§1.1):** empirical failure of fade on EURUSD M15 does not constitute evidence against breakout on the same instrument-timeframe. Joint failure of both would imply random-walk-like dynamics, but breakout has not been measured.
   - **Time-of-day separability (§1.2):** 08:00 BST London open is mechanism-distinct from PDSB 08:30 ET event-window (= 13:30 BST) and NYFBO 09:00 ET (= 14:00 BST). Participant mix (UK/EU institutional flow vs NY market makers) and macro-news calendar (UK 07:00 BST releases occur **before** the OR window, not during) are structurally different.
   - **SL-design lesson carry-forward (§1.3):** bar-extreme SL ban inherited from PDSB G2 audit §5.3 (5–12× tail-budget violation on impulse-driven event bars). H-LORB pre-commits to ATR(14)-multiple SL, NOT bar-extreme or OR-extreme SL.
   - **Spread headwind acknowledged (§1.4):** GBPUSD ~1.0 pip RT vs EURUSD ~0.7 pip; ~0.4 pip stricter implicit edge requirement at kill #1 +2.5-pip threshold (identical numeric threshold despite higher cost). Kill #7 (cost-as-fraction-of-gross-edge ≤ 50%) added vs EURUSD precedent to prevent thin-edge-survives-by-luck patterns.
   - **Negative claim (§1.6) explicitly stated:** this does NOT claim M15 retail-FX edge generally survives, nor breakout > fade as a category. It claims one specific mechanism class on one specific pair-timeframe-window has not been falsified and is worth the Q-cost of one Inquire session.

3. **Phase-A persistence diagnostic measurement gate (not assertion).** Compute Hurst on the post-OR window 09:00–11:00 BST returns:
   - **log-returns only** per memory `feedback_hurst_rs_log_prices_trap.md` (R/S on log-prices yields spurious H≈1; H>0.9 is a diagnostic for this bug).
   - **Dual estimator:** `nolds.hurst_rs` canonical + inline R/S cross-check (parent Notice §5 #12 dual-implementation requirement).
   - **Lag-1 ACF on the same returns series** (parent Notice §1.5 explicit additional gate).
   - **Conjunctive abort condition:** if `nolds` H < 0.50 OR inline R/S H < 0.50 OR lag-1 ACF < 0 → **abort G1 to G3.** Persistence kill has falsified the breakout prior; further H-LORB work is not warranted. (G2 also skipped — H-PNCB is breakout-class on the same instrument-timeframe and would inherit the same persistence-prior falsification.)
   - Record measurement values (3 numeric estimates) and abort/proceed decision in §0a regardless of outcome.

4. **D-S-A discipline check** per memory `feedback_d_vs_s_collapse_discipline.md`. Explicitly distinguish:
   - **S-separator:** cells 1 (LORB) and 3 (PNCB) preserved as breakout-class candidates under per-cell uniqueness; cells 2, 4, 6 deleted as fade-class under stop-rule active scope; cell 5 deferred (separate-override test). Parent Notice §3 corpus + §3.2 S-collapse rationale.
   - **NOT a disguised D-test:** LORB is a breakout-class candidate that survives the S-pass; reaching for a D framing (e.g., "delete LORB as redundant with PNCB") would replicate the Iran-Hormuz silent-relabeling pattern — same-class candidate compression goes under S, not D. Parent Notice §3.2 explicitly preserved both cells under conditioning-driver-distinct grounds (microstructure vs liquidity-shift), not class deletion.

5. **M15-retail-FX base-rate confrontation.** Repo history at G1 entry: AUDNZD 4A (2026-04-29) + EURUSD NYFBO (2026-05-02) + EURUSD PDSB (2026-05-02) = **0/3** on M15 retail-FX edge surviving realistic spread, **all three fade-class**. Address whether the prior generalizes to breakout:
   - **Narrow form:** prior is fade-class-internal (3/3 fade failures); breakout is mechanism-distinct (component 1) and conditioning-window-distinct (component 2); Phase-A measurement (component 3) is the in-session falsifier.
   - **Wider form acknowledged:** if H-LORB G1 fails structurally, the M15-FX stop-rule generalizes to mechanism class (d) breakout, and the next M15-FX Notice's override surface narrows materially (parent Notice §1.6 + §6 stop-rule update).
   - If §0a cannot answer the base-rate confrontation positively (i.e., cannot articulate why this candidate has not already been refuted by the 0/3 priors), abort to G3.

---

## 4. Brief-pinning protocol (Rule 0 applied to the brief itself)

Production code is read from source per Rule 0 to prevent acting on stale memory. The same logic applies to the parent Notice: a decision audit-trail anchored to a brief that drifts after the audit is written is no longer falsifiable against its own gate. Step 0 of the spawn prompt enforces this:

- `git rev-parse HEAD -- docs/methodology/findings/2026-05-03_gbpusd_m15_lon_notice.md` → record the hash. Expected: `158dc61d1aae7ed87717a7291c43df51c526c9b5`. If divergent, **ABORT** — brief moved since this stub was authored.
- `git status --porcelain docs/methodology/` → must be empty. **If dirty, ABORT.** A dirty methodology dir means the brief or a related doc may move during Inquire and the audit-trail loses its anchor.
- The brief commit hash is embedded in the header of any findings or kill-audit file written by the G1 session.
- The parent Notice is added to parent Notice §7's no-edit list **for the duration of the G1 session**. The brief is frozen — the G1 session may not add cross-links, fix typos, or amend §6 routing rows. Any brief revision is a separate session, separate hash.
- This stub itself is also frozen for the duration of the G1 session (no in-session edits to handoff scaffolding).

**Mirror artifact:** the predecessor G1 NYFBO kill audit §0 disclosed session-isolation slippage from over-priming (the G1 NYFBO stub embedded a prose summary of the parent brief). The G2 PDSB stub corrected this by giving no prose substitute; this stub continues that discipline.

---

## 5. Inquire-phase entry checklist (G1)

> G1 Inquire-phase execution is a separate session. Entry into the G1 session requires §1 Step 0 (brief pinning) and §1 Step 1 (parent Notice §0 Rule-0 reads) be performed in that session, not inherited from this stub-authoring session.

- [ ] Brief commit hash recorded (expected `158dc61d1aae7ed87717a7291c43df51c526c9b5`); methodology dir clean (§4)
- [ ] Parent Notice §0–§9 read in full, in-session (no skim, no paraphrase substitute)
- [ ] Predecessor kill audits (NYFBO + PDSB) read in full, in-session
- [ ] Predecessor Notice (EURUSD M15 LNYO) read in full, in-session — methodology guardrails inheritance check
- [ ] Pine sources read with full entry-condition blocks (regime conditional, EOM gate where applicable, session block) — not isolated dow lines; complete activation predicates stated in own words
- [ ] Pine activation predicates cross-checked against most recent backtest CSV trade-day list (filter active in execution, not just coded)
- [ ] [dd_protection.py](../../../dd_protection.py) read; single-tier 1.0% / 0.40× scaling rule confirmed in-session
- [ ] §0a written into the new findings file with all 5 components (§3 of this stub) — abort to G3 if any component fails
- [ ] **Phase A diagnostic gate run** (post-OR window 09:00–11:00 BST log-returns): `nolds` Hurst + inline R/S Hurst + lag-1 ACF; conjunctive verdict recorded; **abort to G3 if any single condition fails** (write `<date>_gbpusd_m15_h_lorb_phaseA_abort.md`)
- [ ] Spread model provenance section authored in findings file: GBPUSD calibration source, sample window, known divergence vs Pepperstone live, UK-release multiplier rationale, mandatory 1.25× sensitivity
- [ ] **Reuse path executed** per parent Notice §5 #13 — port the 6 modules from `analysis/eurusd_lnyo/` to `analysis/gbpusd_lon/` with the swaps below; no greenfield. Each port is a separate file in the new dir. Source files (read-only, must NOT be edited):
  - [analysis/eurusd_lnyo/pepperstone_spread.py](../../../analysis/eurusd_lnyo/pepperstone_spread.py): port + swap baseline `PEPPERSTONE_RAZOR_BASELINE_PIPS = 0.35` → `0.5` per fill (parent Notice §1.4 / §5 #13) + add UK-release multiplier (UK 07:00 BST data calendar; multiplier magnitude calibrated and documented in port docstring with sample-window evidence per parent Notice §5 #2) + add `Europe/London` `BST` `ZoneInfo` alongside the existing `America/New_York` `ET`
  - [analysis/eurusd_lnyo/permutation.py](../../../analysis/eurusd_lnyo/permutation.py): port unchanged. Update docstring header from "H-NYFBO falsification" to "H-LORB falsification"
  - [analysis/eurusd_lnyo/correlation.py](../../../analysis/eurusd_lnyo/correlation.py): port unchanged. DOW masks `STRIKER_DOW = {1, 4}`, `GUARDIAN_DOW = {0, 1, 3}`, `AEGIS_DOW = {0, 1, 2}` carry over (strategy-side, pair-agnostic per parent Notice §5 #6). Hardcoded Pepperstone CSV panel paths (`Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-04-26_*.csv`, `Striker_DJ30_v4.4_PEPPERSTONE_US30_2026-04-26_*.csv`, `Aegis_USDJPY_v4.3_PEPPERSTONE_USDJPY_2026-04-26_*.csv`) stay unchanged — strategy-side panels, not pair-side
  - [analysis/eurusd_lnyo/dxy_loader.py](../../../analysis/eurusd_lnyo/dxy_loader.py): port unchanged. DXY symbol `DX-Y.NYB` correct for GBPUSD anti-correlation check (parent Notice §5 #7); shared output path `data/external/dxy.csv` acceptable
  - [analysis/eurusd_lnyo/hurst_phase_a.py](../../../analysis/eurusd_lnyo/hurst_phase_a.py): port + **invert threshold direction** (`< 0.65 PASS` → `≥ 0.50 PASS`) + add **lag-1 ACF on log-returns ≥ 0 conjunctive condition** (parent Notice §1.5) + swap `DATA` path to GBPUSD M15 file + swap measurement window from event-day post-08:30 ET 30-min windows to **post-OR window 09:00–11:00 BST returns** (Phase A's measurement is on the breakout-window persistence, not event-window persistence)
  - [analysis/eurusd_lnyo/dukascopy_loader.py](../../../analysis/eurusd_lnyo/dukascopy_loader.py): port + symbol swap `EUR/USD` → `GBP/USD` + update `OUT_PATH` filename to `GBPUSD_dukascopy_m15_bidask_2022-01-04_to_2026-04-20.csv`. Output dir `data/bar_data/` unchanged
- [ ] Dukascopy M15 GBPUSD bid+ask 2022-01-04 → 2026-04-20 loaded; tz-aware timestamps verified at all DST transition zones (`Europe/London` BST/GMT for OR window; `America/New_York` for cross-strategy DOW masks)
- [ ] **Data-quality audit** (parent Notice §5 #5): missing-bar count, suspect-spread-bar count (criterion: spread > 5× session median), holiday/half-day handling, NFP/UK-data-spike artifact treatment
- [ ] **UK-release-day OR-window spread distribution** reported (sensitivity, not headline): OR-formation spread conditional on release-day vs non-release-day per parent Notice §5 #2 (BoE / ONS calendar over the panel)
- [ ] Three regime sub-periods isolated using **pre-committed BoE-anchored cutpoints** from parent Notice §5 #3 (no Inquire-time tuning of cutpoints — researcher-DOF leakage)
- [ ] H-LORB single-config falsification per parent Notice §4.2 with literature-default parameters (60-min OR 08:00–08:59 BST, 1.0× ATR(14) SL, 1:2 RR, 11:00 BST time stop, no DOW filter at single-config baseline). ATR(14) computed on M15 series ending at 08:59 BST and held constant intraday
- [ ] H-LORB run twice — at 1.0× and 1.25× spread — both verdicts reported
- [ ] DXY anti-correlation explicit check on Guardian-active days (Mon/Tue/Thu) and pooled (parent Notice §5 #7)
- [ ] Striker-active-day (Tue + Fri) conditional correlation check per kill #4; Friday-only sub-test recorded as diagnostic only (does not rescue gate)
- [ ] Guardian (Mon/Tue/Thu) and Aegis (Mon/Tue/Wed; Tue H10 blocked, EOM 29–31 blocked) conditional correlations for kill #5 G/S/A composite; pooled correlation diagnostic only
- [ ] Per-regime decision matrix built across all 8 kill criteria (§2 of this stub) — pooled is reported but not gating; **any per-regime FAIL = G1 FAIL**
- [ ] Permutation test (≥ 1000 sign-flip shuffles per spread variant per regime) gating any pass verdict (parent Notice §5 #8)
- [ ] Rule 1 small-cell check: any regime sub-sample n < 25 → variance-inflated CIs (parent Notice §5 #5 + §4.3 kill #8 N ≥ 60 floor, per-regime n ≥ 20)
- [ ] **Cost-as-fraction-of-gross-edge** computed per regime per spread variant (kill #7 ≤ 50%); narrow-band binding noted (binds in 3.5–5.0 pip gross-edge band; dominated by kill #1 outside that band)
- [ ] Audit-trail file written with brief commit hash embedded; appropriate filename per parent Notice §8 routing (`pass` / `kill` / `phaseA_abort`); M15-FX stop-rule generalization to breakout class noted if structural fail

---

## 6. Cross-references

- **Parent Notice:** [2026-05-03_gbpusd_m15_lon_notice.md](2026-05-03_gbpusd_m15_lon_notice.md) — §0 Rule-0 reads, §1 stop-rule override (load-bearing for §0a components 1, 2, 5), §3 corpus + S-collapse, §4 H-LORB hypothesis + 8 kill criteria, §5 13 methodology guardrails, §6 stage gates + single-knob escalation pre-commit, §7 out-of-scope, §8 audit-trail commitments, §9 entry stub deferral
- **Predecessor structural-mirror template:** [2026-05-02_eurusd_m15_lnyo_g2_inquire_entry.md](2026-05-02_eurusd_m15_lnyo_g2_inquire_entry.md)
- **Predecessor kill audits** (load-bearing for §3 components 1, 2, 5):
  - [2026-05-02_eurusd_m15_h_nyfbo_kill.md](../archive/gate_audits/2026-05-02_eurusd_m15_h_nyfbo_kill.md)
  - [2026-05-02_eurusd_m15_h_pdsb_kill.md](../archive/gate_audits/2026-05-02_eurusd_m15_h_pdsb_kill.md)
- **Predecessor Notice** (methodology guardrails inheritance): [2026-05-02_eurusd_m15_lnyo_notice.md](2026-05-02_eurusd_m15_lnyo_notice.md)
- **Rule 0:** [docs/rule_0.md](../../rule_0.md)
- **Observation routing:** [docs/methodology/observation_routing.md](../observation_routing.md)
- **Memory anchors:**
  - `feedback_d_vs_s_collapse_discipline.md` — same-class candidate compression goes under S, not D
  - `feedback_hurst_rs_log_prices_trap.md` — R/S on log-returns only (increments), not log-prices; H>0.9 diagnostic for the bug
  - `feedback_loop_selection_inqhiori_ooda.md` — INQHIORI selection rule for structural / low-reversibility / hypothesis-bearing decisions
- **Loop-selection canon:** notion.so/34ddc0b53c1181479d7bdecc61f47078
