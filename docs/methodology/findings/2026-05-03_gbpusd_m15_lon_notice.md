# GBPUSD M15 LON — Notice-phase brief

**D-S-A domain:** data (pre-Q gate over GBPUSD M15 London-session-conditional mechanism corpus)
**Date authored:** 2026-05-03
**Loop:** INQHIORI — Notice phase
**Target slot:** fourth strategy/instrument; same slot vacated by EURUSD M15 LNYO abandonment 2026-05-02
**Status:** Notice authored against active M15-FX stop-rule; §1 carries the override burden
**Predecessor:** [docs/methodology/findings/2026-05-02_eurusd_m15_lnyo_notice.md](2026-05-02_eurusd_m15_lnyo_notice.md) — abandoned via G4 routing 2026-05-02

---

## 0. Rule-0 reads (required for Inquire session at session start)

The Inquire session must read each of the following in full and state each one's load-bearing fact in its own words before any data work. Sources are pinned by hash at session start.

- This brief in full (all sections).
- [docs/methodology/archive/gate_audits/2026-05-02_eurusd_m15_h_nyfbo_kill.md](../archive/gate_audits/2026-05-02_eurusd_m15_h_nyfbo_kill.md) — G1 kill, mechanism class (a) failure record.
- [docs/methodology/archive/gate_audits/2026-05-02_eurusd_m15_h_pdsb_kill.md](../archive/gate_audits/2026-05-02_eurusd_m15_h_pdsb_kill.md) — G2 kill, mechanism class (b) failure record + PDSB-derived SL-design lesson.
- [docs/methodology/findings/2026-05-02_eurusd_m15_lnyo_notice.md](2026-05-02_eurusd_m15_lnyo_notice.md) — predecessor brief; the methodology guardrails carry forward unless this brief explicitly amends.
- Pine sources (full entry-condition blocks, not line citations):
  - [strategies/guardian/guardian_gold_v5.5.pine](../../../strategies/guardian/guardian_gold_v5.5.pine) (lines 35–164)
  - [strategies/striker/striker_dj30_v4.4.pine](../../../strategies/striker/striker_dj30_v4.4.pine) (lines 30–199)
  - [strategies/aegis/aegis_usdjpy_v4.3.pine](../../../strategies/aegis/aegis_usdjpy_v4.3.pine) (lines 155–254)

  The Inquire session must state each strategy's full activation predicate (dow filter + session block + EOM gate where applicable) and cross-check against most recent backtest CSV trade days that the filters fire as coded.
- [dd_protection.py](../../../dd_protection.py) — single-tier 1.0% / 0.40× scaling; load-bearing for any post-G1 portfolio-merit discussion.
- [CLAUDE.md](../../../CLAUDE.md) — operational rules.
- Memory files: `feedback_hurst_rs_log_prices_trap.md` (Hurst on log returns, never log prices); `feedback_d_vs_s_collapse_discipline.md` (D vs S operations).

---

## 1. Stop-rule override (load-bearing — clears the gate to author this Notice)

M15-FX stop-rule status: **ACTIVE** per PDSB G2 audit §7.

Track record at brief authoring: AUDNZD 4A (2026-04-29) + EURUSD NYFBO (2026-05-02) + EURUSD PDSB (2026-05-02) = **0/3** for "M15 retail-FX edge survives realistic spread."

Stop-rule prior in narrow form: "M15 retail-FX edge dies in this spread regime" generalizes empirically to mechanism classes (a) continuous-window fade [NYFBO] and (b) event-conditional fade [PDSB], both of which bet on mean reversion of an impulse on EURUSD M15 with bar-extreme SL placement.

### Override argument

#### 1.1 Mechanism-class separability: breakout ≠ fade

Both failed candidates implement **fade signal generators** — short the impulse, target reversion. H-LORB (London Opening Range Breakout) implements a **breakout signal generator** — long the directional break, target continuation. The trades these two mechanism families would take are not merely opposite-signed on the same setup; they are gated on different conditional structures of the price process. Specifically:

- Fade strategies require **anti-persistent / mean-reverting dynamics** at the conditioning horizon (Hurst < 0.5 favors fade; PDSB measured 0.52–0.60 in the event-conditional window — borderline).
- Breakout strategies require **persistent dynamics / momentum continuation** at the conditioning horizon (Hurst > 0.5 favors breakout).

The two mechanism families are not just different parameter choices on the same trade type; they bet on opposite features of the price process. The empirical failure of fade on EURUSD M15 does not constitute evidence against breakout on the same instrument-timeframe — it is at most weakly informative (joint failure of both would imply random-walk-like dynamics, but neither has been measured for breakout).

#### 1.2 Time-of-day separability

PDSB conditioned on 08:30 ET (= 13:30 BST) US data releases. NYFBO conditioned on 09:00 ET (= 14:00 BST) NY first-bar microstructure. Both are NY-session-anchored.

H-LORB conditions on **08:00 BST London open** (= 03:00 ET) — a window that is pre-NY, low-news-density on the US calendar, dominated by London desk flow and EU-session price discovery. The participant mix is structurally distinct: NY market makers are not yet present; UK and EU institutional flow dominates; macro news risk is on a different calendar (UK 07:00 BST releases occur before the OR window, not during).

The conditioning set is mechanism-distinct from the failed candidates. The failure prior does not transit time-of-day automatically.

#### 1.3 SL-design lesson carry-forward (load-bearing PDSB output)

PDSB G2 audit §5.3 documented that bar-extreme SL on impulse-driven event bars produces 5–12× tail-budget violation: when the fade is wrong, the strategy takes the full bar range, which on NFP/CPI prints exceeds the per-trade risk budget by an order of magnitude. This is a mechanism-level lesson, not a pair-level lesson, and it generalizes to any future event-or-impulse-driven design on any pair/timeframe.

H-LORB inherits this lesson and pre-commits to **ATR(14)-multiple SL, NOT bar-extreme or OR-extreme SL**. See §4 H-LORB single-config and §5 guardrail #11.

#### 1.4 Spread headwind acknowledgment

GBPUSD Pepperstone-Razor typical RT cost ~1.0 pip (0.4 pip raw + $7/lot commission ≈ 0.6 pip), vs EURUSD ~0.7 pip. The ~0.4 pip headwind raises the edge threshold required to clear cost. This is acknowledged and reflected in §4 kill #1 threshold (+2.5 pips, identical to EURUSD's threshold despite higher cost — i.e., implicit ~0.4 pip stricter on edge requirement). A separate cost-vs-gross-edge gate is added as kill #7 to prevent thin-edge-survives-by-luck patterns.

#### 1.5 Hurst gate, inverted (deferred to Inquire §0a)

PDSB used a Phase-A Hurst gate that aborted on H ≥ 0.65 (high persistence falsifies the fade prior). H-LORB uses an **inverted Phase-A gate**: abort on H < 0.50 OR lag-1 ACF < 0 in the 09:00–11:00 BST window (mean-reverting dynamics falsify the breakout prior). Pre-committed thresholds; estimator dual-implementation (`nolds.hurst_rs` canonical, inline R/S cross-check); see §6 stage gates and §9.

#### 1.6 What the override does NOT claim

- It does **not** claim M15 retail-FX edge generally survives. It claims one specific mechanism class on one specific pair-timeframe-window has not been falsified and is worth the Q-cost of one Inquire session.
- It does **not** claim breakout > fade as a category. It claims breakout has not been tested on M15 retail-FX in this repo.
- If H-LORB G1 fails on edge or tail criteria, the M15-FX stop-rule generalizes to mechanism class (d) breakout, and the next M15-FX Notice requires an even narrower override. If H-LORB G1 passes, the prior is updated; conditioning still required for any new mechanism.

**Override verdict:** the prior does not generalize to breakout mechanism class on a structurally distinct conditioning window. Notice is authored.

---

## 2. Loop selection

INQHIORI — falsifiable hypothesis, structural decision, gated promotion. Tactical decisions about backtest configuration that are recoverable within session do not promote to OODA; the gate criteria are pre-committed and cannot be relaxed mid-session.

---

## 3. Corpus + S-collapse

```
Pre-Q gate:
  D: Fade-mechanism candidates (cells 2, 4, 6) deleted (stop-rule
     scope test: M15-FX stop-rule active for fade mechanism class;
     override in §1 is breakout-scoped only). UK-event-conditional
     breakout (cell 5) deferred (separate-override test).
  S: H-LORB and H-PNCB preserved as separate (driver × mechanism)
     cells under per-cell uniqueness; both breakout, but
     conditioning-driver-distinct (microstructure vs liquidity-shift).
  A: (driver × mechanism) cell index over London-session-conditional
     window 08:00–13:00 BST.
```

### 3.1 Corpus (London-session-conditional GBPUSD M15 mechanisms)

Pre-collapse candidates considered:

| Cell | Driver | Mechanism | Candidate | Status |
|---|---|---|---|---|
| 1 | Microstructure | Breakout | London Opening Range Breakout (LORB) | **Survivor — H-LORB** |
| 2 | Microstructure | Fade | London Open Range Fade | Excluded — fade mechanism class, falls under M15-FX stop-rule active scope |
| 3 | Liquidity-shift | Breakout | Pre-NY consolidation breakout (11:00–13:00 BST consolidation, break before NY open) | **Survivor — H-PNCB (G2 candidate)** |
| 4 | Liquidity-shift | Fade | Asian-range fade at London open | Excluded — fade mechanism class |
| 5 | Event-conditional | Breakout | UK CPI/jobs 07:00 BST breakout | Deferred — anticipatory bracket adjacent; separate Notice if H-LORB fails on cost-not-mechanism |
| 6 | Event-conditional | Fade | UK 07:00 BST fade | Excluded — fade mechanism class |

### 3.2 S-collapse rationale

Cells 2, 4, 6 are excluded by stop-rule — the override in §1 is scoped to breakout, not fade. Cell 5 is deferred (would require its own override addressing event-conditional breakout vs PDSB's event-conditional fade — different argument). Cells 1 and 3 are both breakout-class, both London-session-conditional, but they condition on different liquidity dynamics (open-of-session vs mid-session-consolidation). They are preserved as separate (driver × mechanism) cells.

**Survivors:** H-LORB (cell 1, primary) and H-PNCB (cell 3, G2 conditional).

---

## 4. Hypothesis + kill criteria

### 4.1 H-LORB (primary)

**Statement:** On GBPUSD M15, a breakout of the 08:00–09:00 BST opening range (60-minute, 4 × M15 bars) entered on close of the breakout-confirming bar, with ATR(14)-multiple SL and 2× SL TP, time-stopped at 11:00 BST, produces positive expectancy net of cost across `hike_2022_23`, `hold_2023_24`, and `cut_2024_26` regimes, with daily P&L correlation to G/S/A composite < 0.20 and tail-event single-trade DD contained below FXIFY 5% static DD limit.

### 4.2 Single-config (literature-default per §5 guardrail #9)

- **Opening range:** 08:00:00–08:59:59 BST (4 × M15 bars: 08:00, 08:15, 08:30, 08:45)
- **OR high/low:** max/min of the four bars' highs/lows
- **Entry:** close of first M15 bar (≥ 09:00 BST) that closes outside the OR. Long if close > OR_high; short if close < OR_low. One trade per day max.
- **SL:** entry ± 1.0 × ATR(14, M15 bars at entry time). Not bar-extreme. Not OR-opposite-extreme. Carry-forward of PDSB lesson. (ATR(14) is computed on the M15 bar series ending at the OR-end bar close = 08:59 BST, and held constant for any subsequent breakout entry within the same trading day. This avoids ambiguity if breakout fires at, e.g., 10:30 BST after additional bars have updated the rolling ATR.)
- **TP:** entry ± 2.0 × (entry − SL distance) — i.e., 1:2 RR. No partial fills, no scaling out.
- **Time stop:** 11:00 BST (8 × M15 bars after OR end). Closes before 12:00 BST BoE windows.
- **Days:** Mon–Fri, all (no day-of-week filter at single-config baseline; conditional cross-strategy correlation tested in kills #4 and #5).
- **Cost:** GBPUSD parametric session-conditional spread model (see §5 guardrail #1).
- **Spread variants:** 1.0× baseline, 1.25× sensitivity (mandatory).
- **Position sizing:** fixed 1% account risk per trade.

### 4.3 Kill criteria (pre-committed; any single criterion firing in any single regime fails G1)

1. **Edge:** mean net pips per trade ≥ +2.5 in EACH of three regimes. (Identical threshold to EURUSD PDSB despite ~0.4 pip higher GBPUSD cost — implicit stricter edge requirement.)
2. **Worst single-trade loss:** > −1.5% account in EACH regime. Bar-range tail-risk failure mode pre-empted by ATR-multiple SL design.
3. **p99 worst-trade DD:** > −2.5% account in EACH regime.
4. **|r| daily P&L vs Striker** (Tue+Fri conditional): ≤ 0.30. Friday-only sub-test recorded but does not rescue.
5. **|r| daily P&L vs G/S/A composite:** ≤ 0.20.
6. **Profit factor:** ≥ 1.5 in EACH regime.
7. **Cost-as-fraction-of-gross-edge:** ≤ 50%. (NEW vs EURUSD PDSB — prevents the configuration where gross edge clears the +2.5 threshold by 0.1 pip after costs eat 80% of gross. A strategy with 50%+ of gross edge consumed by cost is too fragile to live spread-realization mismatch.)

   **Binding range:** kill #7 binds only in the narrow band where gross edge is 3.5–5.0 pips. At higher gross edge it is dominated by #1; at lower gross edge #1 fires first. Its purpose is to protect against post-G1 parameter configurations where gross edge degrades under sweep.

8. **Total N:** ≥ 60 trades; per-regime n ≥ 20 (Rule 1 inflation if any < 25). PRE-COMMITTED.

### 4.4 H-PNCB (G2 conditional — conditional on H-LORB failure mode)

Entered ONLY if H-LORB fails on a non-structural basis — i.e., one regime passes kills #1 and #6 but fails on tail (#2/#3) or correlation (#4/#5), suggesting the breakout mechanism class is not falsified but the OR-anchored implementation is suboptimal.

If H-LORB fails on edge in all regimes (kill #1 × 3) OR on cost-vs-edge (#7), H-PNCB inherits the same structural failure — both are post-news-low-density breakout strategies on the same instrument-timeframe — and G2 is skipped, route directly to G3.

**Statement (deferred specification):** mid-London consolidation breakout on GBPUSD M15, 11:00–13:00 BST consolidation window, breakout entered post-13:00 BST — full single-config to be specified in G2 entry stub if entered.

---

## 5. Methodology guardrails

1. **Spread model provenance.** GBPUSD-specific parametric Pepperstone-Razor model required. Calibration source must be stated explicitly: typical-spread reference, sample window, known divergence vs Pepperstone live quotes, news-minute multipliers (UK 07:00 BST, US 13:30 BST). Do not reuse EURUSD's parametric model. Sensitivity at 1.25× mandatory.

2. **UK 07:00 BST release residual:** spread can stay elevated 30–60 min post-release. The OR window 08:00–09:00 BST forms inside this residual on UK release days. Spread model must apply a UK-release-day OR-window multiplier (sensitivity, not headline). Track UK release dates (BoE / ONS calendar) over the panel and report OR-formation spread distribution conditional on release-day vs non-release-day.

3. **Regime stratification (pre-committed cutpoints, BoE-anchored).**

   - `hike_2022_23`: 2022-01-04 → 2023-08-31 (Bank Rate cycle: 0.25% → 5.25%, last hike Aug 2023).
   - `hold_2023_24`: 2023-09-01 → 2024-07-31 (rate held at 5.25%).
   - `cut_2024_26`: 2024-08-01 → 2026-04-20 (cut cycle commenced Aug 2024).

   The Inquire session may not tune these. Pooled stat is not the headline.

   The 08:00 BST OR window is dominated by London desk flow on the GBP-leg; BoE rate cycle is the load-bearing macro stratifier. Fed-anchored cutpoints would be appropriate for an NY-session GBPUSD strategy and are not used here.

   **Per-regime decision rule:** any regime fail = G1 fail. Partial passes recorded for portfolio-merit input but never rescue the gate. Pooled is diagnostic only.

4. **Data + tz handling.** Dukascopy M15 GBPUSD bid+ask 2022-01-04 → 2026-04-20 with IANA tz-aware timestamps (`Europe/London` for OR window, `America/New_York` for cross-checks against locked-strategy active days). BST/GMT transitions explicitly handled — OR window is anchored to local London 08:00, not fixed UTC offset.

5. **Data-quality audit (mandatory pre-test).** Inquire session must report: missing-bar count, suspect-spread-bar count (criterion: spread > 5× session median), holiday/half-day handling, NFP/UK-data-spike artifact treatment. Memory `audnzd_lag1_acf_was_below_floor` lesson applies.

6. **Cross-strategy correlation conditioning.** Striker (Tue+Fri); Guardian (Mon/Tue/Thu); Aegis (Mon/Tue/Wed, Tue H10 blocked, EOM 29–31 blocked). Conditional |r| computed on conditional-day intersection only. Pooled correlation diagnostic.

7. **DXY cross-check.** GBPUSD has stronger USD-leg sensitivity than EURUSD overlap; |r| GBPUSD-LORB-trade-pnl vs DXY computed pooled and on Guardian-active-day intersection.

8. **Permutation gating.** ≥ 1000 sign-flip shuffles per spread variant per regime. Two-sided p reported.

9. **Single-config first, no grid search at G1.** Literature-default parameters (60-min OR, 1.0× ATR SL, 1:2 RR, 11:00 BST time stop). Single-variable iteration permitted only after first-config falsification result is recorded.

10. **Brief immutability.** Inquire session must `git rev-parse HEAD` of this file at session start and embed in audit + results JSON. `git status --porcelain` must be empty on `docs/methodology/findings/`.

11. **SL design constraint (carry-forward from PDSB).** Bar-extreme SL is forbidden for any strategy in this candidate slot. ATR-multiple or fixed-pip SL only. Any deviation requires its own override brief addressing the tail-risk-mechanism lesson explicitly.

12. **Hurst on log returns, never log prices** (`feedback_hurst_rs_log_prices_trap.md`). Dual-estimator: `nolds.hurst_rs` canonical, inline R/S cross-check.

13. **Implementation reuse — port from `analysis/eurusd_lnyo/`.** No greenfield reimplementation. Direct ports with parameter swaps:

    | Source module | Reuse pattern |
    |---|---|
    | [pepperstone_spread.py](../../../analysis/eurusd_lnyo/pepperstone_spread.py) | Port to `analysis/gbpusd_lon/`. Swap baseline (0.35 pip → 0.5 pip per fill on GBPUSD) + add UK-release multiplier from §5 #1. |
    | [permutation.py](../../../analysis/eurusd_lnyo/permutation.py) | Port unchanged. |
    | [correlation.py](../../../analysis/eurusd_lnyo/correlation.py) | Port unchanged; DOW masks (Striker Tue+Fri, Guardian Mon/Tue/Thu, Aegis Mon/Tue/Wed) carry over. |
    | [dxy_loader.py](../../../analysis/eurusd_lnyo/dxy_loader.py) | Port unchanged; DXY cross-check applies identically. |
    | [hurst_phase_a.py](../../../analysis/eurusd_lnyo/hurst_phase_a.py) | Port with inverted threshold (≤0.65 abort → ≥0.50 pass; lag-1 ACF ≥ 0). |
    | [dukascopy_loader.py](../../../analysis/eurusd_lnyo/dukascopy_loader.py) | Port with symbol swap EUR/USD → GBP/USD. |

    Parameter swaps are documented in the Inquire entry stub (§9). Any deviation from this reuse path requires its own justification in the entry stub.

---

## 6. Stage gates + routing

### G1 — H-LORB Inquire (single-config + 1.25× spread sensitivity)

**Phase A (gate, pre-backtest):** Conditional persistence diagnostic on the post-OR window (09:00–11:00 BST returns).

- Lag-1 ACF on log-returns: must be ≥ 0.
- Hurst R/S on log-returns (dual-estimator): must be ≥ 0.50 on `nolds`.
- Either failing → **abort to G2 entry decision** (do not run backtest).

**Phase B (backtest):** All 8 kill criteria from §4.3 evaluated per regime per spread variant.

**Outcomes:**

- All criteria pass × all regimes × both spread variants → **G1 PASS** → route to portfolio-merit Inquire (correlation, allocation sizing, MC re-calibration scope).
- Any structural fail (edge × all regimes or cost-vs-edge × all regimes) → **G2 SKIPPED** → route to G3.
- Non-structural fail (tail OR correlation OR mixed regime) → route to **G2 (H-PNCB Inquire)**.

### G1 single-knob escalation (pre-committed)

If H-LORB G1 fails on edge concentration in the late-OR-window — specifically, trades that hit time-stop near 11:00 BST cluster as profitable / trades that exit early are net negative — the single-knob iteration is "extend time-stop to 14:00 BST with explicit BoE-day blackout filter" (Thursday noon BST BoE Bank Rate decision dates blacked out). This is a permitted one-knob iteration post-falsification per §5 #9, not a G1 grid search. Pre-committing it here means it is not reached for as a face-saving rescue if G1 marginally fails for unrelated reasons. Any other knob (OR length, SL multiple, RR) is out of scope for G1's single-knob escalation.

### G2 — H-PNCB Inquire (conditional)

Entry stub authored only if G1 fails non-structurally. Same methodology stack; PNCB single-config to be specified in stub.

### G3 — abandon GBPUSD M15

If both G1 and G2 fail, GBPUSD M15 abandoned for this slot. Routing options:

- (a) GBPUSD M30/H1 (different timeframe, separate Notice).
- (b) Non-FX instrument (CHN50U.x, NDX, separate Notice).
- (c) Slot empty until next Notice phase.

### Stop-rule update on G3

If G3 fires on H-LORB G1 structural failure, the M15-FX stop-rule generalizes to mechanism class (d) breakout. Track record becomes 0/4 spanning fade × 2 + breakout × 2 (counting LORB and PNCB jointly when PNCB is skipped via shared structural failure). The next M15 retail-FX candidate on any pair requires a brief explaining why the prior is not "M15 retail-FX is dead, period" — the override surface narrows materially.

If G3 fires on H-LORB G1 tail-only failure with a structural pass on edge, the lesson is "breakout edge exists but implementation tail risk un-tamed at M15" — different update.

---

## 7. Out-of-scope

The Inquire session may NOT:

- Modify Pine strategies (Guardian v5.5 / Striker v4.4 / Aegis v4.3 — locked).
- Modify [dd_protection.py](../../../dd_protection.py), [portfolio_mc.py](../../../portfolio_mc.py), [CLAUDE.md](../../../CLAUDE.md).
- Modify this Notice brief.
- Modify the predecessor EURUSD Notice or its audit trail.
- Re-run portfolio MC.
- Reintroduce overlays.
- Author Pine for H-LORB at G1 stage. (Pine implementation is a post-G1, post-portfolio-merit deliverable.)
- Grid-search at G1. Literature-default single-config only.
- Pursue fade variants on GBPUSD M15 — explicitly excluded by stop-rule.
- Pursue UK-event-conditional breakout (cell 5) without authoring a separate override brief.

---

## 8. Audit-trail file pattern

- G1 PASS: `docs/methodology/archive/gate_audits/<YYYY-MM-DD>_gbpusd_m15_h_lorb_pass.md`
- G1 FAIL: `docs/methodology/archive/gate_audits/<YYYY-MM-DD>_gbpusd_m15_h_lorb_kill.md`
- Phase A abort: `docs/methodology/archive/gate_audits/<YYYY-MM-DD>_gbpusd_m15_h_lorb_phaseA_abort.md`
- G2 audits follow same pattern with `h_pncb`.

Every audit must:

- Embed brief commit hash from §0/§5.10.
- Embed Phase-A diagnostic results JSON path (when run).
- Reference parent brief by relative path.
- State load-bearing facts of all Rule-0 reads in own words.
- Reaffirm out-of-scope per §7.

---

## 9. Inquire-phase entry stub (deferred)

A separate entry stub (`2026-05-03_gbpusd_m15_lon_g1_inquire_entry.md`) will be authored before spawning the Inquire session, mirroring the EURUSD G2 stub pattern: spawn prompt, §0a entry re-justification components (1: mechanism distinction LORB vs failed candidates; 2: why prior does not generalize; 3: Phase-A persistence diagnostic measurement gate; 4: D-S-A discipline check; 5: M15-FX base-rate confrontation), Phase-A diagnostic abort thresholds.

Entry stub is the operational handoff. This Notice is the structural commit.

---

End of Notice. Awaiting entry-stub authoring and spawn.
