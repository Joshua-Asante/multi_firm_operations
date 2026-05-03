# EURUSD M15 Notice-Phase Brief — London–NY Overlap Variant

**D-S-A domain:** data (pre-Q gate over candidate-archetype corpus)
**Date authored:** 2026-05-02
**Loop:** INQHIORI — Notice complete, Inquire pending
**Predecessor:** external web report 2026-05-02 (London-prime variant, LOR-VEB / LFLSR survivors) — not committed to this repo; see §1
**Path:** `docs/methodology/findings/2026-05-02_eurusd_m15_lnyo_notice.md`
**Slot under investigation:** EURUSD M15, fourth portfolio slot, correlation-diversity objective, edge-first scoping

---

## 0. Pre-loop gate (Rule 0)

Before Inquire phase begins, read these production sources directly. Not memory. Not this brief. Source.

- [strategies/aegis/aegis_usdjpy_v4.3.pine](strategies/aegis/aegis_usdjpy_v4.3.pine) — verify session 10:00–13:45 chart TZ (lines 161–164), `min_atr_val = 0.07` (line 159), Tue H10 block (line 196), EOM block day≥29 (line 201), dow Mon/Tue/Wed (line 190), entry direction (line 240). Header reads "CANDIDATE LOCK 2026-04-22"; CLAUDE.md treats v4.3 as production-locked — tracking inconsistency, not a contradiction.
- [strategies/striker/striker_dj30_v4.4.pine](strategies/striker/striker_dj30_v4.4.pine) — verify session 13–17 UTC (lines 105–106; **= 08:00–13:00 ET in winter / 09:00–13:00 ET in summer**), **dow Tuesday + Friday only** (line 109), breakout `close > highestHigh[1]` (line 142), ATR-expansion gate (line 125), BE 0.15 / trail 0.15–0.9 (lines 69, 77–79), dayStopPct −2.00% (line 37), max 3/day (line 35). Memory-derived afternoon-session claims about Striker do not match the source — read the file before quoting.
- [strategies/guardian/guardian_gold_v5.5.pine](strategies/guardian/guardian_gold_v5.5.pine) — verify EMA 385/25 (lines 47–48), dow Mon/Tue/Thu (lines 78–82), Tue H08 block (line 63), Mon H08 + Mon H09 blocks (lines 64, 66), Mon/Tue/Thu H12 blocks (lines 67, 69, 71), H12 day-latch (line 73), risk 0.34% (line 39), session NY Extended 0800–1600 chart TZ (lines 103, 110).
- [dd_protection.py](dd_protection.py) — single-tier 1.0% / 0.40× (`DD_TRIGGER = 0.010`, `DD_SCALE = 0.40`, lines 38–39); `BASE_RISK` Guardian 0.0034 / Striker 0.0100 / Aegis 0.0150 (lines 42–46); MVD spec-pin (lines 142–151) hard-fails on constant drift.
- [CLAUDE.md](CLAUDE.md) — Strategy Reference table (locked), Protection section, Pepperstone MC anchor block (92.73% pass / 0.65% bust at current G/S/A; current 04-26 panel reproduces 93.78 / 0.58 / 4.92 within drift). Headline MC is Pepperstone-anchored; OANDA findings can route Action but TradingView validation precedes any code/lock change.

Rule-0 violation if Inquire begins without these reads in the same session. The brief is suspect even if its conclusions are right — it was authored without ground truth in scope.

---

## 1. Context

### Predecessor (external, not committed)

The predecessor "web Notice-phase report 2026-05-02 (London-prime variant, LOR-VEB / LFLSR)" is an external artifact only — not committed to this repo. The load-bearing carry-over is the operational-deletion of the awake-window archetypes; that decision is reproduced in the "Operational constraint pivot" subsection below and does not require the predecessor to be re-read.

The predecessor ranked two London-prime survivors:
- **LOR-VEB** — London Opening-Range Volatility-Expansion Break, 02:00–05:00 ET
- **LFLSR** — London Fakeout / Liquidity-Sweep Reversal, 02:30–08:00 ET

Both were ranked specifically for **temporal decorrelation** with G/S/A. Neither Guardian, Striker, nor Aegis has any exposure 02:00–07:00 ET, so any EURUSD daily P&L in that window would be structurally low-correlation with the existing portfolio by construction.

### Operational constraint pivot

NDR sales role 2–11pm ET Tue–Sat → sleep window covers 02:00–07:00 ET. London-prime archetypes are **operationally unfit** regardless of statistical edge. They cannot be monitored, cannot be discretionarily overridden, and a daily-DD-buster at 04:00 ET is not discovered until ~14:00 ET when Joshua logs in — at which point dd_protection has already done its work, but the operational flight-without-instruments is unacceptable as a portfolio addition.

Both London-prime survivors are **deleted from the corpus** by the permitted temporal-scope test (temporal scope = trader-awake hours).

### New firing-window constraint

**08:00–12:00 ET** (London–NY overlap into early NY morning). Joshua is awake, market liquidity is at peak, and **G/S/A are also active** in this window — but on a day-of-week-conditional schedule that significantly reframes the correlation analysis vs. the predecessor brief:

- **Guardian:** session NY Extended 08:00–16:00 chart TZ; dow **Mon/Tue/Thu**; XAU EMA 385/25 trend; with day-specific H08/H09/H12 blocks.
- **Striker:** 13–17 UTC = **08:00–13:00 ET (winter) / 09:00–13:00 ET (summer)**; dow **Tuesday + Friday only**; DJ30 long-only breakout-pyramid; max 3/day; dayStop −2%.
- **Aegis:** 10:00–13:45 chart TZ; dow **Mon/Tue/Wed**; USDJPY mean-revert long; ATR/EOM-gated; Tue H10 block + EOM block.

The temporal-decorrelation guarantee is **gone**. Decorrelation must now come from **mechanism** (different signal logic), **direction** (opposite to existing exposures), or **day-of-week** (different active-DOW set), not from time-of-day.

### Day-of-week intersection in candidate window 08:00–12:00 ET

| Day | Guardian | Striker | Aegis | NYFBO collision profile |
|-----|----------|---------|-------|--------------------------|
| Mon | YES (H10/H11 only after Mon H08+H09+H12 blocks) | NO | YES | G + A possible; no S |
| Tue | YES (H09–H11 after Tue H08+H12 blocks) | YES | YES (Tue H10 blocked) | All three possible — worst-case collision day |
| Wed | NO | NO | YES | A only |
| Thu | YES (H08–H11 after Thu H12 block) | NO | NO | G only |
| Fri | NO | YES | NO | S only — cleanest test of NYFBO vs Striker anti-correlation |

This table reframes §3, §4, and §10 substantially. Most NYFBO trade-days have zero or one G/S/A strategy active in the same window — only Tuesday is the worst-case three-strategy collision day. Friday is the cleanest test of the NYFBO-vs-Striker anti-correlation hypothesis (Striker-only). Striker-correlation kill measurement (§4 H-NYFBO kill #3) must be conditional on Tue + Fri NYFBO trade-days only; pooling across all panel days dilutes the test toward zero by construction.

### Sub-question this Notice phase answers

> Within the 08:00–12:00 ET window, with G/S/A active on a day-of-week-conditional schedule, does any EURUSD M15 archetype exist whose daily P&L is structurally decorrelated from the G/S/A composite, *despite* day-of-week and time-of-day overlap on collision days?

---

## 2. Pre-Q gate (data domain — mandatory header)

```
Pre-Q gate:
  D: London-prime archetypes deleted (temporal-scope test:
     window outside trader-awake hours)
  S: Same-DXY-driver candidates collapsed (NYORB, NYDXY, LNYO-VCB);
     Aegis-mechanism-class candidate collapsed (LMR);
     compression preserves at most one candidate per
     (driver class × mechanism class) cell
  A: Three-column index by (window | driver | mechanism)
```

### Pre-Q gate audit

- The temporal-scope D-test is on the permitted-test list (D-test discipline reference: [docs/methodology/archive/identify_corpus/2026-04-26/README.md](docs/methodology/archive/identify_corpus/2026-04-26/README.md)).
- The directional-driver and mechanism-distinctness filters that produce the §3 CUT verdicts are **S-operations, not D-operations**. They compress same-class candidates within a working enumeration; nothing is deleted from corpus on those grounds. Each §3 CUT row declares which (driver × mechanism) cell it duplicates — a structural fact — instead of which deletion test removed it.
- The S-reframe is deliberate: substituting a permitted-sounding D-test phrasing (e.g. "duplicated by a higher-fidelity source", "question-class extrapolation") for what is structurally an S-collapse would repeat the Iran-Hormuz failure pattern of silently relabeling. See user-memory `feedback_overlay_trigger_discipline.md` and `feedback_leading_indicator_pnl_gate_rationalization.md`.
- If any item compressed in S later turns out to be a non-duplicate that should have stayed in the corpus, gate audit fires per the [docs/methodology/archive/gate_audits/](docs/methodology/archive/gate_audits/) convention and the per-cell uniqueness rule is revised.
- D-S-A header convention follows the extant pattern in [docs/methodology/findings/2026-05-02_oanda_stage1_aegis.md](docs/methodology/findings/2026-05-02_oanda_stage1_aegis.md).

---

## 3. Sub-corpus after pre-Q gate

### Window-intersection enumeration (7 archetypes fire 08:00–12:00 ET)

| Tag | Archetype | Firing (ET) | Driver | Mechanism |
|---|---|---|---|---|
| **NYORB** | NY Opening-Range Break | 09:00–10:30 | DXY + NY institutional flow | Breakout (continuation) |
| **NYFBO** | NY-Open Failed-Breakout Fade | 09:00–10:30 | Microstructure overreaction | Fade (mean-revert against opening drive) |
| **PDDB** | Pre-Data Drift Bracket | 08:00–08:25 | Pre-announcement informed flow | Anticipatory bracket, exit pre-release |
| **PDSB** | Post-Data Snap-Back | 08:35–09:45 | Post-news overreaction (Hawkes / Bormetti) | Fade |
| **LNYO-VCB** | London–NY Volatility-Compression Break | 08:00–09:30 | Vol-clustering long memory | Breakout from compression |
| **LMR** | Lunch Mean-Revert | 11:00–13:00 | Range fade in low-info window | Mean-revert |
| **NYDXY** | NY-Open DXY Confluence | 09:00–10:30 | DXY (direct) | Breakout w/ confluence filter |

### S-collapse — CUT rows declare duplicated (driver × mechanism) cell

| Tag | Verdict | Duplicates cell (driver × mechanism) | Note |
|---|---|---|---|
| NYORB | **CUT (S)** | (DXY × Breakout) — same driver as Guardian (XAU long ≈ DXY short), same mechanism class as Striker (breakout-continuation) | Cell representative if Breakout slot ever needed |
| **NYFBO** | **PASS** | (Microstructure overreaction × Fade) — non-duplicate cell against G/S/A | Strongest residual after S-collapse |
| PDDB | **WEAK PASS** | (Pre-announcement × Anticipatory bracket) — non-duplicate cell | Conditional candidate (Rank 3) |
| **PDSB** | **PASS (high-risk)** | (Post-news × Fade) — non-duplicate cell, but tail-risk severe | Conditional candidate (Rank 2) |
| LNYO-VCB | **CUT (S)** | (DXY × Breakout) — duplicates NYORB | Collapsed; NYORB chosen as cell representative |
| LMR | **CUT (S)** | (Range × Mean-revert) — duplicates Aegis (USDJPY band-revert is the same mechanism class) | Collapsed into Aegis |
| NYDXY | **CUT (S)** | (DXY × Breakout) — duplicates NYORB by construction (anti-DXY ≡ Guardian XAU long) | Collapsed |

### Survivors

Three archetypes pass per-cell uniqueness:

1. **NYFBO** — NY-Open Failed-Breakout Fade — **Rank 1**
2. **PDSB** — Post-Data Snap-Back — **Rank 2 (high-risk, conditional on tail control)**
3. **PDDB** — Pre-Data Drift Bracket — **Rank 3 (conditional on Rank 1 & 2 failing)**

---

## 4. Falsifiable Inquire-phase hypotheses

### H-NYFBO (Rank 1)

**Hypothesis (1 sentence):**
*On EURUSD M15, fading a failed breakout of the NY-open first-bar range — defined as a return into the range within N bars after a break — during the 09:00–10:30 ET window, conditioned on an ATR-regime filter, produces a positive expectancy net of Pepperstone-Razor session-conditional cost, with daily-P&L correlation to the G/S/A composite below 0.20 over the regime-stratified 2022-01-04 → 2026-04-20 panel.*

**Kill criteria (any one fires → kill):**

1. Net per-trade edge < 1.5 pips in any of the three regimes (2022 hike / 2023–24 hold / 2024–26 ease).
2. **Daily-P&L correlation with G/S/A composite > 0.30 in any regime or pooled, measured as signed daily-P&L correlation conditional on G/S/A-active days only** (not pooled raw Pearson over all panel days; window containment will inflate raw pooled Pearson regardless of mechanism — that's measurement noise, not signal).
3. **Striker-specific signed daily-P&L correlation > 0.20, conditional on Striker-active days (Tue + Fri only)** (negates the anti-correlation hypothesis on the days where it must hold). Friday is the cleanest sub-test: Striker-only, no Guardian, no Aegis in window.
4. Trade-day concentration > 75% (under 5% daily DD, concentration is itself a tail-risk signature).
5. Edge concentrated such that 2024-07-01 → 2026-04-20 contributes < 25% of total edge (recency-failure).
6. **Two separate sample-size constraints, both must hold for promotion:**
   - **Permutation-power floor:** N (effective trade count, full panel) ≥ 100, with permutation gating mandatory (Q-A1 lesson 2026-04-29: N binding + perm p just above 0.05 ≠ promotion). Reference: [docs/methodology/archive/identify_corpus/2026-04-27/q_a_aegis_panel_mechanism_gated.md](docs/methodology/archive/identify_corpus/2026-04-27/q_a_aegis_panel_mechanism_gated.md).
   - **Rule 1 small-cell variance prior:** any regime sub-sample with n < 25 triggers Rule 1; tail statistics carry the small-cell prior and confidence intervals must be variance-inflated, not pooled to inflate N. Reference: [docs/methodology/findings/2026-05-02_usoil_15min_characterization.md](docs/methodology/findings/2026-05-02_usoil_15min_characterization.md).

**Q-cost prior:** ~3 hours of Inquire work to backtest single-config falsification on Dukascopy + Pepperstone spread model. If the falsification is not testable in that budget, the hypothesis is not falsifiable enough — refine before continuing.

### H-PDSB (Rank 2, conditional)

**Hypothesis:**
*On EURUSD M15, fading the first-bar overshoot following a high-impact 08:30 ET US release (NFP, CPI, PCE, retail sales, GDP advance) within a 30-minute fade window produces a positive expectancy net of cost, with daily-P&L correlation to the G/S/A composite below 0.20 and tail-event drawdown contained below the FXIFY 5% static DD limit on a Pepperstone-calibrated MC.*

**Kill criteria:**

1. Net per-trade edge < 2.5 pips (higher floor than NYFBO; event-driven slippage is severe).
2. Any single trade in the regime backtest exceeds 1.5% account loss → instant kill (proves the slippage assumption is wrong).
3. p99 single-trade DD on MC > 2.5% account.
4. **Daily-P&L correlation with Striker > 0.30, conditional on Striker-active days (Tue + Fri)** (Striker fires on the same data prints; correlation expected but capped — and only Tue/Fri data prints can produce the collision).
5. Event-day count < 60 over 4-year panel triggers Rule 1 small-cell prior.
6. Pre-announcement spread × 5+ widening on > 25% of event days (operational unreliability).

**Conditional entry rule:** PDSB only enters Inquire if NYFBO clears its gates **and** PDSB is needed as a decorrelated complement, **or** if NYFBO fails for reasons not generalizable to PDSB. Do not pursue PDSB as a hedge against NYFBO failure — it has higher tail risk and lower documented edge.

### H-PDDB (Rank 3, conditional)

**Hypothesis:**
*On EURUSD M15, a bracketed entry in the 08:00–08:25 ET pre-data window, exiting unconditionally at 08:29 ET, produces positive expectancy net of cost driven by documented pre-announcement drift (Lucca/Moench 2015; ECB WP1901), with no overnight or post-announcement exposure.*

**Kill criteria:**

1. Net edge per trade < 1.0 pip (drift literature is thin for FX; bar is set low but is not a free pass).
2. Pre-announcement drift documented in equities does not replicate on EURUSD M15 → no-drift falsification.
3. Pre-data-window entry correlation with Striker entries > 0.40 (conditional on Striker-active Tue + Fri days).
4. Event-days N < 60 triggers Rule 1 small-cell prior.

**Conditional entry rule:** PDDB only enters Inquire if both NYFBO and PDSB are unviable. It is the fallback, not a parallel candidate.

---

## 5. Methodology guardrails (must hold in Inquire phase)

1. **Spread model.** Pepperstone-Razor session-conditional spread (mean + 2σ widening at 08:30 ET data, 10× normal during NFP first 60 sec). Constant-spread backtests overstate NYFBO/PDSB edge by ~30–50%; do not use.
2. **Regime stratification — three sub-periods, reported individually:**
   - 2022-01-04 → 2022-12-30 (ECB/Fed tightening shock, parity break)
   - 2023-01-01 → 2024-06-30 (range-bound 1.05–1.12)
   - 2024-07-01 → 2026-04-20 (ECB cuts, USD-weak drift to 1.17–1.20)
   Pooled stat is misleading and is **not** the headline metric.
3. **Multiple-testing correction.** Three hypotheses → t-stat hurdle ≥ 2.5 (Harvey/Liu/Zhu 2016 baseline). Candidates with t-stat 2.0–2.5 are *interesting*, not *validated*.
4. **DST handling.** EURUSD is double-DST-sensitive (US and EU shift on different dates in March/November). Use IANA tz-aware bar timestamps. There are 2–4 weeks per year where naive offset breaks the session window.
5. **Rule 0 in Inquire.** Re-read production Pine for any G/S/A calibration claim referenced in the correlation analysis. Do not infer fire patterns from memory.
6. **DXY anti-correlation explicit check.** Before approving any survivor, run the cross-correlation: EURUSD long P&L day vs Guardian XAU long P&L day, in the same direction, **conditional on Guardian-active dow (Mon/Tue/Thu)**. If daily Pearson > 0.30 on Guardian-active days, the candidate is DXY-coupled and the hypothesis must be rejected even if standalone metrics look strong.
7. **Live operability.** Joshua must be at the screen during firing window. NYFBO 09:00–10:30 ET is fine. PDSB at 08:30 ET data release will produce alert latency 2–10 sec on Alchemy/DXTrade — flag at Verify, not at Inquire.
8. **Permutation gating.** N ≥ 100 trades and permutation p < 0.05 required for any "promote to Verify" decision (Q-A1 Aegis lesson, 2026-04-29: perm p just above 0.05 + N binding ≠ promotion).
9. **No premature parameter optimization.** Notice → first hypothesis falsification with literature-default parameters (NYFBO: range = first 15-min bar; fade entry = close back inside range; SL = bar high/low; TP = range midpoint at first pass). Grid search only after single-config falsification survives.
10. **Single-variable iteration.** If first-config falsification fails, change one knob, re-test, log. No multi-variable sweeps until the loop has stabilized.

---

## 6. Stage gates and decision points

| Gate | Trigger | Decision |
|---|---|---|
| **G1** | NYFBO Inquire complete | Pass all kill criteria → promote to Verify (paper-trade scoping). Fail → audit which criterion fired; route to PDSB if failure is regime-specific; route to abandon-EURUSD-M15 if failure is structural (e.g., spread > edge in all regimes). |
| **G2** | PDSB Inquire complete (only if NYFBO failed for non-generalizable reasons OR survived as primary and PDSB enters as decorrelated complement). G2 entry handoff: [2026-05-02_eurusd_m15_lnyo_g2_inquire_entry.md](2026-05-02_eurusd_m15_lnyo_g2_inquire_entry.md) — adds §0a entry re-justification gate, brief-pinning protocol, per-regime decision matrix, 1.25× spread sensitivity, M15-FX stop-rule. | Same gate logic. PDSB additional kill: tail-event single-trade > 1.5% account. |
| **G3** | PDDB Inquire complete (only if both NYFBO and PDSB are unviable) | Same. PDDB additional kill: drift effect not replicating on FX. |
| **G4** | All three Inquire-failed | **Abandon EURUSD M15 in this slot.** Do not weaken kill criteria to keep candidates alive. Routing options: (a) GBPUSD M15 same archetype set (wider edge-budget, ~0.4 pip higher all-in cost), (b) EURUSD M30/H1 (different timeframe family — separate Notice phase required), (c) hold the slot empty until a new Notice phase is launched on a different candidate. |

---

## 7. What this brief explicitly does not do

- **No Pine code.** Strategies locked at G v5.5 / S v4.4 / A v4.3. New strategy code is post-Verify only.
- **No parameter values.** First-bar window length, ATR floor, fade-entry rule, time-stop, TP/SL multiples — all literature defaults at first pass; grid search post-falsification.
- **No allocation decisions.** Allocation is post-MC, post-Verify. Guardian 0.30–0.34% safe band, dd_protection 1.0%/0.40×, re-MC triggers — all unchanged by this brief.
- **No dd_protection changes.** Single-tier 1.0% / 0.40× remains canonical (`DD_TRIGGER = 0.010`, `DD_SCALE = 0.40` in [dd_protection.py](dd_protection.py)).
- **No portfolio MC re-run.** New MC fires only after a strategy passes Verify and is added to the portfolio. Re-MC triggers from CLAUDE.md and user memory: 6mo live, version bump, allocation outside G safe band, any dd_protection constant change.
- **No overlay reintroduction.** Iran-Hormuz overlay-deactivation lessons hold ([docs/overlays/guardian_conflict_risk.md](docs/overlays/guardian_conflict_risk.md)). Any regime/macro overlay is a separate INQHIORI loop, not a sub-task here.
- **No new strategies in production.** Surviving archetypes flow Notice → Inquire → Verify → Promote. Claude Code may not skip Verify even if all kill criteria pass.

---

## 8. Audit-trail commitments

1. If any hypothesis is modified after data is touched, log as data-snooping and apply Bonferroni-equivalent t-stat hurdle bump.
2. If any candidate is killed, write a one-paragraph kill note in `docs/methodology/archive/gate_audits/YYYY-MM-DD_<slug>.md` (slug-based naming per existing convention; pattern reference: [docs/methodology/archive/gate_audits/2026-04-25_q3_halt_rules_design_skew.md](docs/methodology/archive/gate_audits/2026-04-25_q3_halt_rules_design_skew.md)).
3. If a forbidden D-test is detected post-hoc — for example, if the §3 S-collapse turns out to encode a hypothesis rather than a structural duplication observation — write a gate audit and revise this brief retroactively. **Do not silently amend.**
4. If the small-cell prior fires (Rule 1: any regime sub-sample n < 25), document and apply variance-inflated confidence intervals; do not pool across regimes to inflate N.

---

## 9. Inquire-phase entry checklist (Claude Code)

> Inquire-phase execution is a separate session. Entry into Inquire requires the §0 Rule-0 reads be performed in that session, not inherited from this Notice-authoring session. Spawn prompt and stage-gate routing live in the entry stub: [2026-05-02_eurusd_m15_lnyo_inquire_entry.md](2026-05-02_eurusd_m15_lnyo_inquire_entry.md).

- [ ] Rule 0 reads complete (§0)
- [ ] Pepperstone session-conditional spread model built and validated against 6-month MT5 export sample
- [ ] Dukascopy M15 EURUSD data 2022-01-04 → 2026-04-20 downloaded, bid+ask
- [ ] DST tz-aware timestamps verified at March/November transition zones (4 transitions in 2022–2026)
- [ ] Three regime sub-periods isolated; pooled stat is *not* the headline number
- [ ] H-NYFBO single-config falsification with literature-default parameters
- [ ] DXY anti-correlation explicit check on Guardian-active days (Mon/Tue/Thu)
- [ ] Striker-active-day (Tue + Fri) conditional correlation check for H-NYFBO kill #3; Friday-only sub-test recorded separately
- [ ] Aegis Mon/Tue/Wed conditional correlation check (do not pool across full panel)
- [ ] Hurst exponent on log returns (not log prices — `feedback_hurst_rs_log_prices_trap.md`) per regime; sanity-check vs prior of H ≈ 0.5
- [ ] G1 stage gate evaluated against §4 NYFBO kill criteria
- [ ] Permutation test (≥ 1000 shuffles) gating any pass verdict
- [ ] Rule 1 small-cell check: any regime sub-sample n < 25 → variance-inflated CIs
- [ ] Audit trail file written if any kill criterion fired

---

## 10. Open questions / known unknowns

1. **Aegis correlation on EUR-fade days.** Aegis fires Mon/Tue/Wed only ([strategies/aegis/aegis_usdjpy_v4.3.pine:190](strategies/aegis/aegis_usdjpy_v4.3.pine)). Thu/Fri NYFBO trade-days are zero-Aegis-exposure by construction, sharpening the H-NYFBO correlation null toward "Aegis correlation lives only on Mon/Tue/Wed; measure conditional, not pooled." Heuristic correlation low (different pair), but worth measuring directly in Inquire.
2. **Striker DJ30 vs EURUSD on big-data days — principal H-NYFBO failure mode.** Striker fires Tue + Fri only ([strategies/striker/striker_dj30_v4.4.pine:109](strategies/striker/striker_dj30_v4.4.pine)). The anti-correlation hypothesis (NYFBO fades what Striker pyramids) lives entirely on Tue and Fri NYFBO trade-days. **NYFBO 09:00–10:30 ET is fully contained inside Striker's 13–17 UTC window**, so they will co-fire on the highest-volatility Tue/Fri days, exactly when anti-correlation must hold. The conditional-on-Striker-active-day estimator (kill #3) is set up specifically to detect this. Friday is the cleanest sub-test: Striker-only in window, no Guardian, no Aegis.
3. **2024–2026 sub-sample size.** ~22 months at NYFBO frequency may yield insufficient regime-specific N. If NYFBO fails the recency-contribution test (§4 kill #5), check whether it's a recency *failure* or just a recency *sample* problem — Rule 1 small-cell prior may apply to the regime sub-sample independent of the full-panel permutation-power floor.
4. **Operational fallback if NYFBO requires intra-bar entry.** Pine bar-close vs intra-bar logic divergence on TradingView is a known issue. If the rule requires intra-bar entry, alert latency on Alchemy/DXTrade may matter — flag at Verify.
5. **EURUSD vs GBPUSD edge-budget tradeoff.** GBP responds more aggressively to NY open but pays ~0.4 pip more in cost. If NYFBO marginally fails on EURUSD it may pass on GBPUSD — but that is a separate Notice phase, not a fallback within this one.
6. **DST-week contamination magnitude.** Need to quantify how many trade observations fall in the 2–4 contaminated weeks per year. If material, treat as a separate regime; if not, document and fold into the main panel.

---

## 11. Cross-references

- **Predecessor Notice phase:** external web report 2026-05-02 (LOR-VEB / LFLSR — operationally killed by awake-window constraint; not committed to this repo)
- **Loop selection canon:** notion.so/34ddc0b53c1181479d7bdecc61f47078
- **Rule 0:** [docs/rule_0.md](docs/rule_0.md)
- **D-test discipline:** [docs/methodology/archive/identify_corpus/2026-04-26/README.md](docs/methodology/archive/identify_corpus/2026-04-26/README.md)
- **Observation routing (Closed / Action / Forward):** [docs/methodology/observation_routing.md](docs/methodology/observation_routing.md)
- **D-S-A pre-Q header convention (extant example):** [docs/methodology/findings/2026-05-02_oanda_stage1_aegis.md](docs/methodology/findings/2026-05-02_oanda_stage1_aegis.md)
- **Q-A1 Aegis closing brief (permutation-power lesson):** [docs/methodology/archive/identify_corpus/2026-04-27/q_a_aegis_panel_mechanism_gated.md](docs/methodology/archive/identify_corpus/2026-04-27/q_a_aegis_panel_mechanism_gated.md)
- **Operational rules:** [docs/operational_rules.md](docs/operational_rules.md)
- **1R estimation:** [docs/methodology/1r_estimation.md](docs/methodology/1r_estimation.md)
- **Strategy-research-phase methodology archive:** [docs/methodology/archive/README.md](docs/methodology/archive/README.md)
- **Overlay history (Iran-Hormuz, deactivated 2026-04-23):** [docs/overlays/guardian_conflict_risk.md](docs/overlays/guardian_conflict_risk.md)
- **dd_protection production source:** [dd_protection.py](dd_protection.py); MC anchors: [CLAUDE.md](CLAUDE.md), [portfolio_mc.py](portfolio_mc.py), [tests/test_mc_anchors.py](tests/test_mc_anchors.py)
- **OODA-loop sibling skill:** for tactical / live-trade decisions during the Inquire phase
- **fxify-challenge skill:** G/S/A operational facts, dd_protection, MC panel
- **pinescript-v6 skill:** post-Verify only
- **Notion Command Center:** notion.so/34bdc0b53c1181fe9dc3fd93eadf3e8e
- **Strategy decision FINAL:** notion.so/346dc0b53c11816085bbf2292be934cc

---

## 12. Single-line summary for index

> EURUSD M15, 4th slot, awake-window constraint deletes London-prime; three survivors after S-collapse to (driver × mechanism) cells (NYFBO Rank 1, PDSB Rank 2 conditional, PDDB Rank 3 conditional); single Inquire-phase falsification proceeds on H-NYFBO at literature-default parameters; G1 stage gate against §4 kill criteria with Striker correlation measured conditional on Tue/Fri active days only; abandon-EURUSD-M15 if all three fail.
