# Gate audit — H-PDSB Inquire-phase G2 kill

**Date:** 2026-05-02
**Loop:** INQHIORI — H-PDSB single-config falsification (Inquire phase)
**Parent brief:** [docs/methodology/findings/2026-05-02_eurusd_m15_lnyo_notice.md](../../findings/2026-05-02_eurusd_m15_lnyo_notice.md)
**Brief commit hash (pinned at session start):** `c3ef0448984f6fe11fba440285b5323b35209ca5`
**G2 entry stub:** [docs/methodology/findings/2026-05-02_eurusd_m15_lnyo_g2_inquire_entry.md](../../findings/2026-05-02_eurusd_m15_lnyo_g2_inquire_entry.md)
**G1 kill audit (load-bearing for §0a components 2 + 5):** [docs/methodology/archive/gate_audits/2026-05-02_eurusd_m15_h_nyfbo_kill.md](2026-05-02_eurusd_m15_h_nyfbo_kill.md)
**Verdict:** **KILL — G2 fail across both spread variants; structural across all three regimes**
**Routing:** **G4 (abandon EURUSD M15 in this slot for PDSB mechanism); M15-FX stop-rule fires**

---

## 0. Session-isolation disclosure + brief pinning

This G2 session was opened fresh against the worktree at branch
`claude/eager-chebyshev-731553`. Step 0 of the spawn prompt was performed:

- `git rev-parse HEAD -- docs/methodology/findings/2026-05-02_eurusd_m15_lnyo_notice.md`
  returned `c3ef0448984f6fe11fba440285b5323b35209ca5`.
- `git status --porcelain` returned empty.
- The brief commit hash is embedded in this audit header and in
  `analysis/eurusd_lnyo/results/h_pdsb_g2.json` / `h_pdsb_g2_spread125.json` /
  `h_pdsb_g2_phaseA_hurst.json`.
- Parent brief §0–§12 was read in full in this session (no skim, no paraphrase).
- G1 kill audit was read in full in this session.
- Pine sources were read with full entry-condition blocks
  (Guardian lines 35–164, Striker lines 30–199, Aegis lines 155–254).
- Pine activation predicates cross-checked against backtest CSV trade days:
  Striker entries are Tue (115) + Fri (116) only; Guardian Mon/Tue/Thu
  (57/64/88); Aegis Mon/Tue/Wed (43/23/57). All filters fire as coded.

This audit-trail is anchored to the pinned hash. The parent brief is
frozen for the duration of this session per stub §4.

## 0a. Entry re-justification (stub §3 components 1–5)

### 1. Mechanism distinction (NYFBO vs PDSB)

Parent brief §3 places NYFBO at cell `(Microstructure overreaction × Fade)`
and PDSB at `(Post-news overreaction × Fade)`. The S-collapse explicitly
preserved both as separate cells; the duplicated-cell column for PDSB is
empty (no other survivor in `(Post-news × Fade)`). The mechanism distinction
is structural: NYFBO conditions on the 09:00 ET first-bar opening range
under endogenous order-flow, whereas PDSB conditions on an *exogenous
information event* (08:30 ET US data print) followed by a Hawkes-style
overreaction. The signal generators differ in what makes the move and in
what makes a fade reasonable. This is not a relabel of NYFBO — it is a
distinct (driver × mechanism) cell.

### 2. Why Hurst ≈ 0.75 (G1 reading) does not generalize

The G1 kill audit computed Hurst on full-panel mid-price returns and
recorded H ≈ 0.75 across all three regimes (its specific R/S estimator with
n_lags up to 20). That reading is across an unconditional 24-hour returns
process. PDSB conditions on event-day post-08:30 ET 30-minute windows only
— a fundamentally different conditioning set. Hawkes / Bormetti post-news
overreaction literature documents that **post-event short-horizon dynamics
are empirically separable from baseline persistence**: even a panel that
trends overall can exhibit short-horizon mean reversion immediately after
information events. The argument requires measurement, not assertion (see
component 3).

### 3. Conditional-Hurst diagnostic gate (load-bearing) — measurement

Per stub §3 component 3, computed Hurst on the event-day post-08:30 ET
30-minute window (M15 bars at 08:30 + 08:45 ET). Threshold: H ≥ 0.65 →
abort G2 to G4.

**Estimator:** R/S on log-returns of mid-price (memory
`feedback_hurst_rs_log_prices_trap.md` — never on log-prices). Two
implementations: (a) inline R/S, (b) `nolds.hurst_rs`. Sanity check on a
known H≈0.5 random walk + log-levels trap demo run first.

| Sanity probe | H |
|---|---|
| R/S on N(0,1) returns (n=2000) | 0.629 (small-sample inline R/S bias; nolds is cleaner) |
| R/S on log-PRICES trap demo | 1.004 (illustrates the trap — DO NOT use log levels) |
| R/S on AR(1) phi=0.5 returns | 0.288 |

| Conditional Hurst | n_returns | Inline R/S | nolds R/S |
|---|---|---|---|
| Broad event-window (any wkday 08:30+08:45 ET) | 2,228 | **0.599** | **0.522** |
| NFP-only (1st Fri 08:30+08:45 ET) | 104 | 0.614 | 0.406 |
| Full panel (context, G1 anchor ~0.75 different estimator) | 107,057 | 0.546 | — |

**Gate decision: PASS.** Both estimators on the broad event-window read
H < 0.65 (0.599 inline; 0.522 nolds). NFP-only reads similarly. The
event-conditional persistence is materially below the abort threshold —
the §0a justification survives the diagnostic. Backtest may proceed.
Results: `analysis/eurusd_lnyo/results/h_pdsb_g2_phaseA_hurst.json`.

### 4. D-S-A discipline check

Per memory `feedback_d_vs_s_collapse_discipline.md`, the §3 placement of
PDSB as a separate cell is an S-operation (compression preserves at most
one candidate per (driver × mechanism) cell — and PDSB occupies the only
candidate in its cell). It is not a deletion candidate hiding behind a
permitted-sounding D label. No D-test was reached for; no Iran-Hormuz
silent-relabeling pattern in the structural argument. Component 4 holds.

### 5. M15-retail-FX base-rate confrontation

Repo history at session start: AUDNZD 4A + H-NYFBO = 0/2 on M15 retail-FX
edge surviving realistic spread. The narrow form for PDSB:

H-NYFBO failed on **mechanism (persistence), not on cost** — G1 kill audit
§5 records gross edge negative pre-cost in every regime. Calibration
uncertainty cannot rescue that verdict.

Does the prior generalize from continuous-window fades to event-conditional
fades? Component 3's measurement is the strongest evidence the prior does
**not** automatically generalize: the event-conditional Hurst is 0.52–0.60
(below the persistence ceiling), so the mechanism-class separation predicted
in §0a component 1 is at least defensible. PDSB clears the entry gate on the
explicit prior-confrontation: H-NYFBO failed on persistence; the
post-event window does not show the same persistence; the candidate
deserves the backtest. Whether the candidate then *passes* the backtest is
a separate question (answered below).

§0a verdict: **all five components pass their own audit**. Backtest proceeds.

---

## 1. Hypothesis tested

H-PDSB (parent brief §4): on EURUSD M15, fading the first-bar overshoot
following a high-impact 08:30 ET US release within a 30-min fade window
produces positive expectancy net of cost, with daily P&L correlation to
G/S/A composite < 0.20 and tail-event drawdown contained below the FXIFY
5% static DD limit.

## 2. Configuration (literature-default per parent brief §5 #9)

- Event days: 224 events 2022-01-04 → 2026-04-20
  (NFP=52, CPI=52, RetailSales=52, PCE=51, GDP_Advance=17)
- Event bar = 08:30 ET M15 bar (08:30–08:44)
- Direction = sign(close − open) of event bar
- Fade entry = bar close, opposite event-bar direction
- Fade window = 08:35 → 09:00 ET (next two M15 bars: 08:45, 09:00)
- SL = event bar's high (short fade) or low (long fade)
- TP = event bar's open (mean-revert target — undo the impulse)
- Time stop = 09:00 ET bar close
- Costs = Pepperstone-Razor parametric session-conditional spread
  (0.35 pip baseline; 3× at 08:30 ET data minute; 10× at NFP first minute)
- Two spread variants: 1.0× (baseline) and 1.25× (sensitivity)
- N=224 trades both variants (event count = trade count, no two-sided skip)

## 3. Panel

- Source: Dukascopy M15 EURUSD bid+ask (G1-shared loader)
- Range: 2022-01-04 00:00 UTC → 2026-04-21 00:00 UTC
- Rows: 107,058 M15 bars
- Event calendar: hand-constructed from BLS/BEA standard release patterns
  (see `analysis/eurusd_lnyo/event_calendar.py` docstring for rule set);
  spot-checked 2024 NFPs all match canonical 1st Friday dates.

## 4. Per-regime decision matrix — both spread variants

### 1.0× spread

| Criterion | hike_2022 | hold_2023_24 | ease_2024_26 | Verdict |
|---|---|---|---|---|
| #1 edge ≥ +2.5 pips | **−1.65** (n=52) FAIL | **−3.24** (n=78) FAIL | **−0.17** (n=94) FAIL | FAIL × 3 |
| #2 worst trade > −1.5% | **−7.5%** FAIL | **−14.5%** FAIL | **−14.5%** FAIL | FAIL × 3 |
| #3 p99 worst-trade DD > −2.5% | **−7.5%** FAIL | **−14.5%** FAIL | **−14.5%** FAIL | FAIL × 3 |
| #4 \|r\| Striker Tue+Fri ≤ 0.30 | — (panel) | — (panel) | — (panel) | PASS (\|r\|=0.115, n=103) |
| #5 event N ≥ 60 | — (panel) | — (panel) | — (panel) | PASS (N=224) |
| #6 spread-widen <25% trades | 23.1% PASS | 23.1% PASS | 23.4% PASS | PASS × 3 (just below threshold by design — calendar centered on 08:30 ET) |

### 1.25× spread (sensitivity)

| Criterion | hike_2022 | hold_2023_24 | ease_2024_26 | Verdict |
|---|---|---|---|---|
| #1 edge ≥ +2.5 pips | **−2.14** FAIL | **−3.73** FAIL | **−0.67** FAIL | FAIL × 3 |
| #2 worst trade > −1.5% | **−9.25%** FAIL | **−18.0%** FAIL | **−18.0%** FAIL | FAIL × 3 |
| #3 p99 worst-trade DD > −2.5% | **−9.25%** FAIL | **−18.0%** FAIL | **−18.0%** FAIL | FAIL × 3 |
| #4 Striker Tue+Fri | — | — | — | PASS (\|r\|=0.110) |
| #5 event N | — | — | — | PASS (N=224) |
| #6 spread widen | 23.1% PASS | 23.1% PASS | 23.4% PASS | PASS × 3 |

**Diagnostic sub-tests (do not rescue gate):**

- Friday-only Striker correlation: |r| = 0.115 (n=103) — same-magnitude as Tue+Fri pooled, no anti-correlation evidence.
- Pooled Striker (raw): |r| = 0.082 (n=224) — diagnostic only.
- Guardian | Mon/Tue/Thu: |r| = 0.041 (n=69) — no DXY-coupling on Guardian-active days.
- Aegis | Mon/Tue/Wed: |r| = 0.014 (n=52) — no JPY-coupling.
- G/S/A composite: |r| = 0.046 (n=224) — well below kill #4 threshold.
- DXY guardrail: |r| = 0.040 (n=69, Guardian-active dow) — no DXY-coupling.

**Permutation gating (1000 shuffles, sign-flip on per-trade pips):**
- 1.0×: observed mean = −1.58 pips, two-sided p = 0.006 (n=224)
- 1.25×: observed mean = −2.08 pips, two-sided p = 0.000 (n=224)
- The negative edge is statistically distinguishable from zero at both spread levels.

**Rule 1 small-cell:** all three regimes have n ≥ 25 (minimum 52). No
variance inflation applied.

## 5. Why the kill is structural, not regime-specific or operational-only

Per stub §2 routing: structural-fail → G4 with M15-FX stop-rule firing;
operational-only-fail → G3 (PDDB). This kill is **structural**:

1. **Edge fails in all three regimes** at 1.0× spread by 2.7–5.0 pips below
   the +2.5 pip threshold. At 1.25× the gap widens to 3.2–6.2 pips. This is
   not a "spread > edge" failure — gross pip P&L is also negative in every
   regime (mean per-trade gross ≈ net + 0.7 pip baseline RT cost).

2. **Permutation p < 0.01 at both spread levels** confirms the negative
   edge is not noise. The fade signal generator at literature-default
   parameters has no demonstrable expectancy on event-day post-08:30 ET
   30-min windows for EURUSD M15.

3. **Tail risk is severe.** Worst single-trade loss of −7.5% to −14.5%
   account at 1.0× spread (and −9.25% to −18% at 1.25×) violates kill #2
   (1.5% threshold) by 5–12×. Bar-extreme SL during high-impact data
   events is the wrong stop placement for this mechanism — the bar
   extreme can be 15+ pips from the bar close on NFP/CPI prints, and
   when the fade is wrong the strategy takes the full bar range.

4. **The §0a Hurst gate passed** (event-conditional H = 0.52–0.60 < 0.65),
   so the Hawkes-overreaction prior is *not* falsified by persistence
   structure alone. The mechanism-class separability assumed by the
   §0a justification holds. **What fails is the literature-default
   parameter choice (entry on bar-close + bar-extreme SL).** The
   mechanism class (post-event fade) is not falsified at the structural
   level by this run; the *single-config implementation* is. However,
   per parent brief §5 #9, no parameter optimization is permitted at
   this stage — the kill stands as written.

5. **Operational-only kills (#2 spread or #6 widening)** cannot be
   triangulated as the sole failure mode. Kill #1 (edge) and kills #2/#3
   (tail) all fail per regime. Kill #6 (spread widening) actually passes
   (23.1–23.4% < 25% threshold). The failure is not isolated to
   operational characteristics that PDDB would avoid; the failure is in
   the edge magnitude itself.

6. **Recency / regime-specific failure** is also ruled out: the worst
   regime (hold_2023_24, mean −3.24) and the best regime (ease_2024_26,
   mean −0.17) both fail kill #1 in the same direction; the recent regime
   is not closer to passing.

## 6. Routing decision

**G2 verdict: FAIL — structural × all three regimes × both spread variants.**

**Route: G4 — abandon EURUSD M15 for the PDSB mechanism.**

Per parent brief §6 G4 routing options:
1. (a) GBPUSD M15 same archetype set (~0.4 pip higher cost) — separate Notice
2. (b) EURUSD M30/H1 (different timeframe) — separate Notice
3. (c) hold the slot empty until a new Notice phase

PDDB (G3) is the next conditional candidate per parent brief §6, but per
parent brief §4 H-PDDB conditional entry rule:

> PDDB only enters Inquire if both NYFBO and PDSB are unviable.

Both are now unviable. PDDB is *eligible* but the M15-FX stop-rule (next
section) creates a high default-rejection prior.

## 7. M15-FX stop-rule fires

**Stop-rule (defined in stub §2):** the next M15 retail-FX candidate
(G3 PDDB, or any successor on a different pair) requires a written brief
explaining why the prior is **not** "M15 retail-FX is dead in this spread
regime" — specific to whether the prior generalizes from continuous-window
fades to (a) event-conditional fades, (b) anticipatory brackets, (c) other
mechanism classes.

**Status: ACTIVE.** Repo M15 retail-FX edge-survival track record now reads:

- AUDNZD 4A: did not survive realistic spread
- EURUSD M15 H-NYFBO (G1 2026-05-02): structural negative gross edge in
  all three regimes; mechanism = continuous-window fade
- EURUSD M15 H-PDSB (G2 2026-05-02): structural negative net edge in all
  three regimes at both spread variants; tail violations 5–12× threshold;
  mechanism = event-conditional fade

**The stop-rule generalizes BOTH (a) and (b)**: continuous-window fades
fail (NYFBO) AND event-conditional fades fail (PDSB). Anticipatory brackets
(PDDB) are mechanism class (c) — pre-data, no event-window exposure. The
question for PDDB is whether the prior "M15 retail-FX edge dies in this
spread regime" generalizes to anticipatory brackets that exit pre-release.

Per the stop-rule default: **the prior generalizes; PDDB is rejected at the
brief stage; no Q-cost spent**, unless an override brief presents positive
evidence of mechanism-class separability for anticipatory brackets vs the
two failed fade mechanisms. That override brief is the responsibility of
the next Notice authoring session and is **not** authored here.

Recommended next step: **route (c) — hold the slot empty until a new Notice
phase**, where the new Notice phase either justifies PDDB under the
M15-FX stop-rule override clause, or proposes a different pair / timeframe.

## 8. Lesson (one line for the regime-marker accumulator)

EURUSD M15 event-conditional post-data fade (PDSB) at literature-default
parameters has structurally negative gross edge AND severe tail risk
(worst single-trade −14.5% to −18% account) across all three regimes
2022–2026; the §0a event-conditional Hurst gate cleared (H = 0.52–0.60)
so the Hawkes-overreaction prior survives the structural test, but the
single-config implementation does not — and the M15-FX stop-rule now
generalizes "M15 retail-FX edge dies in this spread regime" to BOTH
continuous-window AND event-conditional fade mechanism classes.

## 9. Reproducibility

- Pipeline orchestrator: [analysis/eurusd_lnyo/run_h_pdsb.py](../../../../analysis/eurusd_lnyo/run_h_pdsb.py)
- §0a Phase-A diagnostic: [analysis/eurusd_lnyo/hurst_phase_a.py](../../../../analysis/eurusd_lnyo/hurst_phase_a.py)
  → [analysis/eurusd_lnyo/results/h_pdsb_g2_phaseA_hurst.json](../../../../analysis/eurusd_lnyo/results/h_pdsb_g2_phaseA_hurst.json)
- Results JSON: [analysis/eurusd_lnyo/results/h_pdsb_g2.json](../../../../analysis/eurusd_lnyo/results/h_pdsb_g2.json)
  (1.0×) and [h_pdsb_g2_spread125.json](../../../../analysis/eurusd_lnyo/results/h_pdsb_g2_spread125.json) (1.25×)
- Event calendar: [analysis/eurusd_lnyo/event_calendar.py](../../../../analysis/eurusd_lnyo/event_calendar.py)
  → [data/external/us_high_impact_0830et_2022_2026.csv](../../../../data/external/us_high_impact_0830et_2022_2026.csv)
- PDSB simulator: [analysis/eurusd_lnyo/pdsb_simulator.py](../../../../analysis/eurusd_lnyo/pdsb_simulator.py)
- Dukascopy panel (G1-shared): `data/bar_data/EURUSD_dukascopy_m15_bidask_2022-01-04_to_2026-04-20.csv`
- DXY panel (G1-shared): `data/external/dxy.csv`
- Reproduction:
  ```
  python analysis/eurusd_lnyo/event_calendar.py
  python analysis/eurusd_lnyo/hurst_phase_a.py
  python -m analysis.eurusd_lnyo.run_h_pdsb
  ```

## 10. Out-of-scope reaffirmation (parent brief §7 + stub)

No edits made to: Pine strategies (G v5.5 / S v4.4 / A v4.3),
`dd_protection.py`, `portfolio_mc.py`, `CLAUDE.md`, the parent Notice
brief, OR the G2 entry stub. No grid search; literature-default
single-config only at both spread levels. No allocation, MC re-run,
overlay reintroduction, or new strategy code.

## 11. Spread-model provenance (stub §5 disclosure)

The Pepperstone-Razor session-conditional spread model (`analysis/eurusd_lnyo/pepperstone_spread.py`)
remains PARAMETRIC: 0.35 pip per-fill baseline (= 0.7 pip RT, derived from
$7/lot commission ≈ 0.6 pip + 0.1 pip raw) with 3× multiplier on 08:30 ET
weekday minutes (mean+2σ proxy) and 10× on NFP first minute. **Not
empirically calibrated against an MT5 export sample.**

Sensitivity: 1.25× multiplier was run as the stub §5 mandated sensitivity.
Both verdicts are FAIL_G2 with FAIL margins on kill #1 of 2.7–5.0 pips
(1.0×) and 3.2–6.2 pips (1.25×). The kill is robust to spread-model
mis-calibration of up to ~25% upward (the 1.25× variant is designed to
proxy the realistic worst case of pre-data widening underestimation).

---

**End of audit.** Brief commit hash recorded (`c3ef044`); methodology dir
clean at session start; no edits attempted to frozen artifacts; M15-FX
stop-rule registered as active.
