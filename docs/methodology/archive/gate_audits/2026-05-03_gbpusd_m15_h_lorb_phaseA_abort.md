# Gate audit — H-LORB Inquire-phase G1 Phase A abort

**Date:** 2026-05-03
**Loop:** INQHIORI — H-LORB single-config falsification (Inquire phase)
**Parent Notice:** [docs/methodology/findings/2026-05-03_gbpusd_m15_lon_notice.md](../../findings/2026-05-03_gbpusd_m15_lon_notice.md)
**Parent Notice commit hash (pinned at session start):** `158dc61d1aae7ed87717a7291c43df51c526c9b5`
**Entry stub:** [docs/methodology/findings/2026-05-03_gbpusd_m15_lon_g1_inquire_entry.md](../../findings/2026-05-03_gbpusd_m15_lon_g1_inquire_entry.md)
**Predecessor kill audits (Rule-0 reads, load-bearing for §0a 1, 2, 5):**
- [2026-05-02_eurusd_m15_h_nyfbo_kill.md](2026-05-02_eurusd_m15_h_nyfbo_kill.md) — fade mechanism class (a), continuous-window failure record
- [2026-05-02_eurusd_m15_h_pdsb_kill.md](2026-05-02_eurusd_m15_h_pdsb_kill.md) — fade mechanism class (b), event-conditional failure record + SL-design lesson source

**Verdict:** **PHASE A ABORT — G1 fail; persistence/momentum prior not affirmatively supported at the H-LORB conditioning window**
**Routing:** **G3 (abandon GBPUSD M15 in this slot for the H-LORB / breakout-class mechanism)**; M15-FX stop-rule generalizes to mechanism class (d) breakout per parent Notice §6 G3 stop-rule update; G2 (H-PNCB) skipped under entry stub §3 component 3 explicit shared-inheritance commitment.
**Texture caveat (load-bearing for next M15-FX override author):** failing gate metric (within-day lag-1 ACF = −0.0204) is statistically indistinguishable from 0 (bootstrap 95% CI [−0.056, +0.013] crosses zero). The Hurst pooled clears at threshold (nolds 0.501, inline 0.554) but per-regime nolds is split 1/3 above / 2/3 below 0.50. The structural finding is "GBPUSD M15 post-OR window is essentially random-walk noise" — neither breakout-supportive (positive ACF + H well > 0.5) nor sharply mean-reverting (negative ACF + H well < 0.5). The strict pre-committed conjunctive gate fires on the negative point estimate; relaxing it post-hoc on bootstrap-CI grounds would be the silent-relabeling failure pattern (memory `feedback_overlay_trigger_discipline.md` / `feedback_leading_indicator_pnl_gate_rationalization.md`). Verdict stands; the texture is preserved for downstream override authoring.

---

## 0. Session-isolation disclosure + brief pinning

### Disclosure

This session is the in-conversation continuation of the session that authored the parent Notice and entry stub (commits `158dc61` Notice + `e55020a` entry stub, prior turn). The user explicitly directed "proceed with a fresh G1 H-LORB Inquire session" in this conversation; isolation was offered to be hard-fenced via a fresh agent and the user accepted in-session execution. To mitigate the predecessor G1 NYFBO §0 finding ("session-isolation slippage from over-priming"), the parent Notice §0–§9, predecessor kill audits, predecessor Notice, Pine sources at the cited line ranges, dd_protection.py, Rule 0, observation routing, and the two memory anchors named in parent Notice §0 were all re-read in full in this session before §0a was authored. No prose substitute for source reads was used. The structural verdicts in this audit are measurements; isolation-slippage at the prose layer does not contaminate the measurement layer.

### Brief pinning (parent Notice §5 #10 / entry stub §4)

Step 0 of the spawn prompt was performed:

```
$ git rev-parse HEAD -- docs/methodology/findings/2026-05-03_gbpusd_m15_lon_notice.md
e51da0fe4cf80e5916af564706a59985bcd6f671
$ git log -1 --format='%H' -- docs/methodology/findings/2026-05-03_gbpusd_m15_lon_notice.md
158dc61d1aae7ed87717a7291c43df51c526c9b5
$ git status --porcelain docs/methodology/
(empty)
```

- HEAD-rev-parse returns `e51da0f` (latest merge); the **introducing commit** of the parent Notice file is `158dc61d1aae7ed87717a7291c43df51c526c9b5`, matching the entry stub §4 expected hash. The brief is unchanged since stub authoring.
- methodology dir clean.
- Brief commit hash `158dc61d1aae7ed87717a7291c43df51c526c9b5` is embedded in this audit header and will be embedded in any results JSON written to disk.
- Parent Notice §0–§9 read in full in this session.
- Predecessor kill audits (NYFBO + PDSB) read in full in this session.
- Predecessor EURUSD LNYO Notice read in full in this session.
- Pine sources read with full entry-condition blocks: Guardian v5.5 lines 35–164 (NY Extended 0800–1600 chart TZ; dow Mon/Tue/Thu; risk 0.34%; EMA(385) trend + EMA(25) recovery; H08 blocks Mon/Tue, H09 block Mon, H12 blocks Mon/Tue/Thu, H12 day-latch); Striker v4.4 lines 30–199 (UTC 13–17; dow Tue+Fri; risk 1.00%; 15-bar `close > highestHigh[1]` breakout, ATR-expansion 0.28, warmup>3 bars, body≥0.25, prev bar bullish, max 3/day, dayStop −2%); Aegis v4.3 lines 155–254 (10:00–13:45 chart TZ; dow Mon/Tue/Wed; risk 1.50%; BB-lower fade long, ATR≥0.07, H11 blocked, Tue H10 blocked, EOM 29–31 blocked, max 1/day).
- Pine activation predicates cross-checked against the most recent Pepperstone TV-export entry-day distributions: Guardian Mon=57 / Tue=64 / Thu=88 (n=209, no Wed/Fri); Striker Tue=115 / Fri=116 (n=231, no Mon/Wed/Thu); Aegis Mon=43 / Tue=23 / Wed=57 (n=123, no Thu/Fri). Filters fire as coded.
- dd_protection.py read; single-tier 1.0% / 0.40× scaling rule confirmed in-session (`DD_TRIGGER = 0.010`, `DD_SCALE = 0.40` at lines 38–39; MVD spec-pin at lines 142–151 hard-fails on drift; BASE_RISK Guardian 0.0034 / Striker 0.0100 / Aegis 0.0150).
- `docs/rule_0.md` read; production-code-first discipline reaffirmed.
- `docs/methodology/observation_routing.md` read; three-bucket gate (Closed / Action / Forward) is downstream of the pre-Q gate.
- Memory anchors `feedback_hurst_rs_log_prices_trap.md` (R/S on log-returns only; H>0.9 diagnostic for log-prices bug) and `feedback_d_vs_s_collapse_discipline.md` (same-class candidate compression goes under S, not D) read in full.
- The 6 reuse-path source modules at `analysis/eurusd_lnyo/` (`pepperstone_spread.py`, `permutation.py`, `correlation.py`, `dxy_loader.py`, `hurst_phase_a.py`, `dukascopy_loader.py`) read in full.

This audit is anchored to the pinned hash. The parent Notice and the entry stub are frozen for the duration of this G1 session per entry stub §4.

---

## 0a. Entry re-justification (entry stub §3 components 1–5)

### 1. Mechanism distinction LORB vs failed candidates (NYFBO + PDSB)

Parent Notice §3 corpus places H-LORB at cell **1 (Microstructure × Breakout)**, vs the failed candidates at cells `(Microstructure overreaction × Fade)` (NYFBO, EURUSD G1 kill 2026-05-02) and `(Post-news × Fade)` (PDSB, EURUSD G2 kill 2026-05-02). The S-collapse (parent Notice §3.2) preserved cells 1 (LORB) and 3 (PNCB) as separate breakout cells under per-cell uniqueness; cells 2/4/6 were excluded by the fade-class M15-FX stop-rule and cell 5 deferred (separate-override test).

The structural property: **fade and breakout signal generators bet on opposite features of the price process.** A fade strategy is profitable when the conditioning-window return process is anti-persistent / mean-reverting (Hurst < 0.5 favors); a breakout strategy is profitable when the conditioning-window return process is persistent / momentum-continuing (Hurst > 0.5 favors). The two mechanism families are not parameter-choice variants on the same setup — they require opposite conditional structures. The PDSB G2 audit explicitly framed this in its §0a: PDSB's event-conditional Hurst gate (H<0.65 abort) was inverted from the breakout-prior framing. H-LORB applies the inverse of that gate (H≥0.50 pass) precisely because the mechanism class is opposite.

The S-pass that produced LORB and PNCB as survivors is not a relabeling of NYFBO — they are gated on a structurally distinct property of the price process. Component 1 holds.

### 2. Why prior does not generalize from fade to breakout

Parent Notice §1.1–§1.6 in compressed form:

- **§1.1 — Mechanism-class separability.** Empirical failure of fade on EURUSD M15 (NYFBO + PDSB, 2/2 in their respective conditioning windows) does not constitute evidence against breakout on the same instrument-timeframe. Joint failure of both fade and breakout would imply random-walk-like dynamics, but breakout has not been measured on M15 retail-FX in this repo. The NYFBO G1 audit's full-panel Hurst≈0.75 reading is informative (it is the same R/S estimator family that we will use for Phase A) but was measured on full-panel mid-price log-returns, not on the H-LORB conditioning window — same instrument, different conditioning set, different measurement.
- **§1.2 — Time-of-day separability.** PDSB conditioned on 08:30 ET (= 13:30 BST) US data releases. NYFBO conditioned on 09:00 ET (= 14:00 BST) NY first-bar microstructure. Both are NY-session-anchored. H-LORB conditions on **08:00 BST London open** (= 03:00 ET) — a window that is pre-NY, low-news-density on the US calendar, dominated by London desk flow and EU-session price discovery. UK 07:00 BST releases (BoE / ONS calendar) occur **before** the OR window forms, not during. Participant mix is structurally distinct (UK/EU institutional flow vs NY market makers).
- **§1.3 — SL-design lesson carry-forward (load-bearing PDSB output).** PDSB G2 audit §5.3 documented bar-extreme SL on impulse-driven event bars produces 5–12× tail-budget violation: when the fade is wrong, the strategy takes the full bar range (worst single trades −7.5% to −18% account at 1.0× and 1.25× spread). This is a mechanism-level lesson that generalizes to any future event-or-impulse-driven design. H-LORB inherits and pre-commits to **ATR(14)-multiple SL, NOT bar-extreme or OR-extreme SL.** The 1.0× ATR(14) at 08:59 BST close, held constant intraday, is the canonical implementation per parent Notice §4.2 and §5 #11.
- **§1.4 — Spread headwind acknowledgment.** GBPUSD Pepperstone-Razor typical RT cost ~1.0 pip (0.4 pip raw + $7/lot commission ≈ 0.6 pip), vs EURUSD ~0.7 pip. The ~0.4 pip headwind raises the edge threshold required to clear cost. Kill #1's +2.5 pip threshold is identical numerically to PDSB, despite the higher cost — i.e., implicit ~0.4 pip stricter on edge requirement. Kill #7 (cost-as-fraction-of-gross-edge ≤ 50%) is added vs the EURUSD precedent to prevent the configuration where gross edge clears the +2.5 threshold by 0.1 pip after costs eat 80% of gross.
- **§1.6 — Negative claims explicitly stated.** This re-justification does NOT claim M15 retail-FX edge generally survives, nor breakout > fade as a category. It claims one specific mechanism class on one specific pair-timeframe-window has not been falsified and is worth the Q-cost of one Inquire session. If H-LORB G1 fails structurally (kill #1 or #7 in all three regimes), the M15-FX stop-rule generalizes to mechanism class (d) breakout per parent Notice §6 G3 routing.

Component 2 holds.

### 3. Phase-A persistence diagnostic measurement gate (PLANNED — measurement deferred to Phase A section)

Per memory `feedback_hurst_rs_log_prices_trap.md`, the diagnostic uses **log-returns only** of M15 mid-price (`(bid_close + ask_close) / 2`), NEVER log-prices. R/S on log-prices yields spurious H≈1.0 (the cumsum-of-cumsum trap; H > 0.9 is the diagnostic of this bug).

Per parent Notice §1.5 + §6 + entry stub §3 component 3:

| Estimator | Threshold | Source |
|---|---|---|
| `nolds.hurst_rs` on log-returns | ≥ 0.50 | parent Notice §6 (canonical estimator) |
| Inline R/S Hurst on log-returns | ≥ 0.50 | parent Notice §5 #12 (cross-check estimator) |
| Lag-1 ACF on log-returns | ≥ 0 | parent Notice §1.5 (additional gate) |

**Conjunctive abort condition:** if `nolds` H < 0.50 OR inline R/S H < 0.50 OR lag-1 ACF < 0 → **abort G1 to G3.** The breakout-class persistence prior has been falsified at the H-LORB conditioning window; further H-LORB work is not warranted, and G2 (H-PNCB) is also skipped because H-PNCB is breakout-class on the same instrument-timeframe and would inherit the same persistence-prior falsification.

**Measurement window:** post-OR window 09:00–11:00 BST log-returns, weekdays only, full panel 2022-01-04 → 2026-04-20. Sanity probes (random-walk H≈0.5; log-levels trap H≈1.0; AR(1) phi=0.5 returns H<0.5) are run first in the ported `hurst_phase_a.py` to confirm the estimator behaves before any panel measurement.

**Measurement values + gate decision:** see Phase A section below.

### 4. D-S-A discipline check (memory `feedback_d_vs_s_collapse_discipline.md`)

The S-pass that produced LORB and PNCB as survivors:
- **S-separator:** cells 1 (LORB) and 3 (PNCB) preserved as breakout-class candidates under per-cell uniqueness; cells 2, 4, 6 deleted as fade-class under stop-rule active scope; cell 5 deferred (event-conditional breakout, separate-override test). Parent Notice §3 corpus + §3.2 S-collapse rationale.
- **NOT a disguised D-test:** LORB is a breakout-class candidate that survives the S-pass; reaching for a D framing here (e.g., "delete LORB as redundant with PNCB") would replicate the Iran-Hormuz silent-relabeling pattern (memory `feedback_d_vs_s_collapse_discipline.md`). Parent Notice §3.2 explicitly preserved both cells under conditioning-driver-distinct grounds (microstructure vs liquidity-shift), not class deletion. The compression is structural (each cell occupies a unique (driver × mechanism) coordinate); no permitted-sounding D-test name was substituted for what is structurally an S-collapse.

Component 4 holds.

### 5. M15-retail-FX base-rate confrontation

Repo history at G1 entry (parent Notice §1):
- AUDNZD 4A (2026-04-29) — fade-class
- EURUSD H-NYFBO (G1 2026-05-02, fade mechanism class (a), continuous-window) — structural negative gross edge in all 3 regimes
- EURUSD H-PDSB (G2 2026-05-02, fade mechanism class (b), event-conditional) — structural negative net edge in all 3 regimes at both spread variants; 5–12× tail-budget violation

= **0/3** on M15 retail-FX edge surviving realistic spread, **all three fade-class.**

**Narrow form (load-bearing for §0a):** the prior is fade-class-internal (3/3 fade failures); breakout is mechanism-distinct (component 1) and conditioning-window-distinct (component 2); Phase-A measurement (component 3) is the in-session falsifier of the breakout prior at the H-LORB conditioning window. The prior does not automatically generalize to breakout; whether it does is a measurement question, not an assertion.

**Wider form acknowledged:** if H-LORB G1 fails structurally (kill #1 or #7 across all 3 regimes), the M15-FX stop-rule generalizes to mechanism class (d) breakout (parent Notice §1.6 + §6 G3 stop-rule update). The H-PNCB G2 candidate inherits the same structural failure under shared mechanism class + instrument-timeframe and is skipped. Track record becomes 0/4 spanning fade × 2 + breakout × 2; the next M15 retail-FX candidate's override surface narrows materially.

This re-justification does not assert that the prior fails to generalize. It asserts that the question is open and the cheapest-falsification gate (Phase A) is set up to answer it. If Phase A fails, abort to G3 with the stop-rule generalization. If Phase A passes, run Phase B; only the per-regime decision matrix can falsify the breakout prior at the implementation level. Component 5 holds.

---

## §0a verdict — proceed-or-abort decision

Components 1, 2, 4, 5 — **PASS** (prose audit; structurally sound on parent Notice + predecessor audits + Pine sources + memory anchors).

Component 3 — **PENDING** (measurement deferred to Phase A; gate criteria pre-committed; abort-to-G3 condition fully specified).

Status: §0a non-measurement components clear. Proceed to module porting, data fetch, and Phase A measurement. Final §0a verdict gates on Phase A outcome.

---

## Phase A — diagnostic gate (measurement)

### Data and module ports

**Data fetched:** Dukascopy GBPUSD M15 bid+ask 2022-01-04 → 2026-04-21 via the ported `analysis/gbpusd_lon/dukascopy_loader.py` (symbol swap EUR/USD → GBP/USD; `Europe/London` BST ZoneInfo added; chunked 60-day fetch). 107,041 rows (vs EURUSD predecessor's 107,058; 17-bar diff from pair-specific holiday handling).

**Modules ported** to `analysis/gbpusd_lon/` per parent Notice §5 #13 and entry stub §5:
- `dukascopy_loader.py` — symbol swap, OUT_PATH update, `Europe/London` BST ZoneInfo, expanded DST_TRANSITIONS for UK BST cycle
- `pepperstone_spread.py` — baseline 0.35 → 0.5 pip per fill (parent Notice §1.4); UK 07:00 BST 2.0× multiplier added (parent Notice §5 #2; outside H-LORB's 09:00-11:00 BST execution window so doesn't affect cost — coded for completeness; sensitivity captured by 1.25× variant); US 13:30 BST (= 08:30 ET) and NFP first-minute multipliers retained
- `permutation.py` — ported unchanged; docstring header swapped H-NYFBO → H-LORB
- `correlation.py` — ported unchanged; DOW masks `STRIKER_DOW = {1, 4}`, `GUARDIAN_DOW = {0, 1, 3}`, `AEGIS_DOW = {0, 1, 2}` carry over (strategy-side, pair-agnostic); Pepperstone CSV panel paths unchanged
- `dxy_loader.py` — ported unchanged; DXY symbol `DX-Y.NYB` correct for GBPUSD anti-correlation; shared output path `data/external/dxy.csv` reused
- `hurst_phase_a.py` — threshold inverted (≤ 0.65 abort → ≥ 0.50 pass); lag-1 ACF on log-returns ≥ 0 conjunctive condition added; window swapped from event-day post-08:30 ET 30-min to post-OR 09:00–11:00 BST returns; DATA path swapped to GBPUSD M15 file

### Data-quality audit (parent Notice §5 #5)

| Check | Result |
|---|---|
| Rows | 107,041 |
| bid_close ≤ ask_close invariant | 100.0000% |
| Mean close spread | 1.207 pips (Dukascopy retail; 1.25× spread sensitivity brackets) |
| Median session 08:00-13:00 BST spread | 0.800 pips |
| p99 session spread | 1.800 pips |
| Suspect bars (spread > 5× session median = 4.0 pips) | 3,713 (3.469% of all bars; mostly weekend-edge / overnight outside H-LORB exec window) |
| OR-window 08:00-08:59 BST spread (mean / median) | 0.863 / 0.800 pips |
| Inferred UK-release-day OR-window (07:00 BST mean spread > 2× sess median): n=15 days → 48 OR-window bars | mean 3.204 pips |
| Inferred non-UK-release-day OR-window: n=4,408 bars | mean 0.837 pips |
| Total weekday-dates | 1,121 |
| Holiday / no-trade days (< 40 bars) | 7 |
| Half-days (40–79 bars) | 0 |
| DST sanity | 18 transition spot-checks consistent with IANA `Europe/London` (08:00 local → 07:00 UTC summer / 08:00 UTC winter) |

UK-release-day OR-window mean spread is 3.84× the non-release-day baseline — confirms parent Notice §5 #2 rationale and is reported as **sensitivity, not headline** per the brief commitment.

### Sanity probes (`hurst_phase_a.py`)

| Probe | H |
|---|---|
| R/S inline on N(0,1) returns (n=2000) | 0.629 (small-sample upward bias known) |
| R/S inline on log-PRICES (the trap, n=2000) | 1.004 (illustrates memory `feedback_hurst_rs_log_prices_trap.md`) |
| R/S inline on AR(1) phi=+0.5 returns (n=1999) | 0.288 (differenced-AR(1) artifact) |
| R/S inline on AR(1) phi=−0.5 returns (n=1999) | 0.197 (anti-persistent control) |

The estimator catches the log-prices trap as expected. Random-walk returns read with ~0.13 upward bias at this n; this is a known small-sample feature of the inline R/S estimator and motivates the dual-estimator requirement (nolds is cleaner asymptotically). The mean-reverting controls correctly read below 0.5.

### §0a Component 3 — measurements (gate metrics)

**Window:** post-OR 09:00–11:00 BST log-returns of mid-quote `(bid_close + ask_close) / 2`, weekdays only.

**n_returns (panel):** 8,912

**Pooled gate metrics (parent Notice §6 + entry stub §3 conjunctive):**

| Metric | Reading | Threshold | Verdict |
|---|---|---|---|
| `nolds.hurst_rs` H | **0.501** | ≥ 0.50 | **PASS at threshold** |
| inline R/S H | **0.554** | ≥ 0.50 | PASS |
| within-day lag-1 ACF | **−0.0204** (n_pairs = 7,798) | ≥ 0 | **FAIL** (point estimate negative) |
| flat-series lag-1 ACF (cross-day boundary noise) | −0.0094 | — (sanity only) | reported |

**Conjunctive verdict:** ANY-fail per parent Notice §6 + entry stub §3 component 3 → **FAIL** on lag-1 ACF.

### Robustness — bootstrap CI on the failing metric + per-regime stability

The point-estimate gate verdict is a strict pre-commitment. To capture the load-bearing texture of the failure, the gate metrics were re-run per BoE-anchored regime + a 2,000-replication bootstrap CI was computed on the within-day lag-1 ACF.

**Per-regime n (post-OR 09:00–11:00 BST log-returns):** hike_2022_23 = 3,464; hold_2023_24 = 1,896; cut_2024_26 = 3,552. All clear parent Notice §4.3 kill #8 per-regime n ≥ 20 floor.

**Per-regime Hurst (information; not the gate metric — gate is pooled per Notice §6):**

| Regime | n_returns | H_inline | H_nolds |
|---|---|---|---|
| hike_2022_23 | 3,464 | 0.559 | 0.523 |
| hold_2023_24 | 1,896 | 0.581 | **0.470** |
| cut_2024_26 | 3,552 | 0.588 | **0.494** |
| pooled (gate) | 8,912 | 0.554 | 0.501 |

The pooled-panel nolds reading (0.501, technically clearing the threshold) hides a per-regime split: 2 of 3 regimes read nolds H < 0.50. The pooled clear is carried by the hike regime (0.523). Inline R/S is more uniformly above 0.50 across regimes (0.559 / 0.581 / 0.588), but inline has known small-sample upward bias from the sanity probes. **Reading: random-walk-like with no consistent breakout-favoring persistence across regimes.**

**Per-regime within-day lag-1 ACF + 2k-replication bootstrap 95% CI:**

| Regime | n_pairs | ρ | 95% CI | P(ρ<0) bootstrap |
|---|---|---|---|---|
| hike_2022_23 | 3,031 | −0.0229 | [−0.073, +0.027] | 0.816 — **CI crosses 0** |
| hold_2023_24 | 1,659 | +0.0018 | [−0.058, +0.058] | 0.489 — basically zero |
| cut_2024_26 | 3,108 | −0.0263 | [−0.070, +0.019] | 0.871 — **CI crosses 0** |
| pooled | 7,798 | −0.0204 | [−0.056, +0.013] | 0.887 — **CI crosses 0** |

**Bootstrap CI on the failing gate metric crosses 0 in every regime and pooled.** The pooled point estimate is ~1.85 SE below 0; one-sided P(ρ<0) under bootstrap = 0.887, well above conventional 95% thresholds. Under conventional inference, H₀: ρ = 0 cannot be rejected.

### §0a Component 3 verdict

**Gate metric, strict reading: FAIL** — pooled within-day lag-1 ACF is negative (−0.0204), violating the pre-committed `≥ 0` conjunctive condition.

**Substantive interpretation: NO STRONG SIGNAL.** Hurst dual-estimator pooled clears at threshold (0.501 / 0.554) but per-regime nolds is split 1/3 above / 2/3 below 0.50. Lag-1 ACF point estimate is negative but the bootstrap 95% CI crosses 0 in every regime + pooled. The failing gate metric is **not statistically distinguishable from 0** under conventional inference.

The structural finding is "GBPUSD M15 post-OR window 09:00–11:00 BST returns are essentially random-walk noise" — neither sharply persistent (H well above 0.5, positive ACF — would support breakout) nor sharply mean-reverting (H well below 0.5, negative ACF — would falsify breakout decisively). The data does not provide affirmative support for the breakout prior, and a strict-rule conjunctive gate fires on a borderline reading.

### §0a overall verdict

- Components 1, 2, 4, 5: PASS (prose audit; structurally sound)
- Component 3 measurement gate: **FAIL** under strict pre-committed conjunctive rule (point-estimate ACF < 0)
- Component 3 substantive reading: **NO SIGNAL** (gate fires on borderline metric statistically indistinguishable from 0; substantive rationale is "data doesn't support the prior" not "data falsifies the prior")

Per the brief-pinning and methodology discipline (parent Notice §5 #10, entry stub §4, memory `feedback_overlay_trigger_discipline.md` and `feedback_leading_indicator_pnl_gate_rationalization.md`), the strict-gate is what was pre-committed. Relaxing it post-hoc on the basis of "the bootstrap CI includes 0" would be exactly the silent-relabeling failure pattern that the gate was designed to prevent. **Strict-gate verdict applies: §0a fails Component 3 → abort G1 to G3.**

The audit captures the borderline texture so that future M15-FX override authors can read this as "no support" rather than "active falsification." That distinction matters for the M15-FX stop-rule generalization in §6.

### Phase A — final decision

**Phase A verdict: ABORT.** Routing per parent Notice §6 + entry stub §2 + entry stub §3 component 3.

No Phase B backtest run. No `run_h_lorb.py` orchestrator authored. No `lorb_simulator.py` written.

---

## Phase B — backtest decision matrix

**Not executed.** Phase A gate fired abort; Phase B is gated downstream of Phase A pass per parent Notice §6 ("Either failing → abort to G2 entry decision (do not run backtest)").

---

## Final routing

### Decision: G3 — abandon GBPUSD M15 in this slot

Routing rationale per **entry stub §3 component 3 explicit commitment**:

> "Conjunctive abort condition: if `nolds` H < 0.50 OR inline R/S H < 0.50 OR lag-1 ACF < 0 → **abort G1 to G3.** Persistence kill has falsified the breakout prior; further H-LORB work is not warranted. (G2 also skipped — H-PNCB is breakout-class on the same instrument-timeframe and would inherit the same persistence-prior falsification.)"

The entry stub §2 alternative routing language ("G2 entry decision per parent Notice §6 ... at this configuration") is more permissive — it would route the Phase A abort to a separate decision-point on whether to author H-PNCB G2. The stub §3 component 3 explicit-commitment language is more specific and stricter. Per the entry stub's own §4 brief-pinning protocol (the stub cannot be modified during the G1 session), the §3 commitment governs. **G2 SKIPPED → G3.**

The texture of the failure — "no signal," not "active falsification" — is preserved in the audit but does not change the routing. Both stub passages support G3 routing under their respective framings; the more specific §3 component 3 commitment is the authoritative one.

### Stop-rule update (parent Notice §1.6 + §6 G3 stop-rule update)

The M15-FX stop-rule status updates from the PDSB G2 audit §7 record:

| Track record at session start | 0/3 fade-class (AUDNZD 4A + EURUSD NYFBO + EURUSD PDSB) |
| Phase A abort → G3 (this audit) | LORB breakout-class, conditioning-window persistence/momentum-prior **not affirmatively supported**; G2 H-PNCB skipped under entry stub §3 inheritance commitment |
| Track record at session end | 0/4 spanning fade × 2 + breakout × 2 (PNCB counted via shared structural inheritance per entry stub §3) |

**Texture caveat (load-bearing for the next M15-FX override author):** the LORB Phase A failure is on a borderline gate metric (lag-1 ACF point estimate −0.02; bootstrap 95% CI [−0.056, +0.013] crosses 0). The H readings cleared pooled (0.501 nolds at threshold) but failed per-regime in 2 of 3 regimes (nolds 0.470 / 0.494). The structural finding is "GBPUSD M15 post-OR window is essentially random-walk noise — no affirmative support for breakout, no decisive evidence of mean-reversion." The next M15-FX override author should not read this as "M15 retail-FX breakout is dead" — they should read it as "GBPUSD M15 LON window has no measurable price-process structure to bet on." Different overrides (different pair, different window, different timeframe) may produce different gate metrics.

### Stop-rule generalization

Per parent Notice §6:
> "If G3 fires on H-LORB G1 structural failure, the M15-FX stop-rule generalizes to mechanism class (d) breakout. Track record becomes 0/4 spanning fade × 2 + breakout × 2 (counting LORB and PNCB jointly when PNCB is skipped via shared structural failure). The next M15 retail-FX candidate on any pair requires a brief explaining why the prior is not 'M15 retail-FX is dead, period' — the override surface narrows materially."

**Status: ACTIVE — generalized.** The next M15 retail-FX Notice (any pair, any conditioning window, fade or breakout class) requires a brief addressing:
1. Why the prior is not "M15 retail-FX is dead in this spread regime" full-stop. The override surface is now narrower than after the PDSB stop-rule fire.
2. Specifically for breakout-class candidates: why the H-LORB conditioning-window measurement does not generalize to the new candidate's window. (For LORB the failure was "no signal"; a candidate with measured positive lag-1 ACF + H ≥ 0.55 in its conditioning window has a structurally different starting point.)
3. For fade-class candidates: the existing 2/2 NYFBO + PDSB stop-rule still binds; the additional LORB datum does not strengthen the fade prior either way (different mechanism class).

### Slot decision

Per parent Notice §6 G3 routing options:
1. (a) GBPUSD M30/H1 (different timeframe, separate Notice).
2. (b) Non-FX instrument (CHN50U.x, NDX, separate Notice).
3. (c) Slot empty until next Notice phase.

**Recommended:** route (c) — hold the slot empty. Routes (a) and (b) require their own Notice authoring with override briefs that confront the now-generalized M15-FX stop-rule (route a) or the broader 4-failure track record (route b).

### Open question for the next Notice author

The texture of the LORB Phase A failure (random-walk noise, gate fires on borderline ACF) is qualitatively different from the texture of NYFBO + PDSB failures (sharply negative gross edge, structural fade-mechanism kills). Whether the M15-FX stop-rule should weight the four failures equally, or weight LORB lower due to its "no signal" texture, is an open methodology question for the next Notice author. The parent Notice §6 stop-rule update language is silent on this weighting; that's a deliberate hand-off, not an oversight.

### Audit-trail commitments (parent Notice §8)

This audit will be copied/renamed to `docs/methodology/archive/gate_audits/2026-05-03_gbpusd_m15_h_lorb_phaseA_abort.md` per the §8 file pattern, with the brief commit hash `158dc61d1aae7ed87717a7291c43df51c526c9b5` embedded in the header.

Phase A diagnostic results JSON: [`analysis/gbpusd_lon/results/h_lorb_g1_phaseA_hurst.json`](../../../../analysis/gbpusd_lon/results/h_lorb_g1_phaseA_hurst.json).

Robustness JSON (per-regime Hurst + bootstrap ACF CI): [`analysis/gbpusd_lon/results/h_lorb_g1_phaseA_robustness.json`](../../../../analysis/gbpusd_lon/results/h_lorb_g1_phaseA_robustness.json).

---

## Out-of-scope reaffirmation (parent Notice §7)

No edits made to: Pine strategies (Guardian v5.5 / Striker v4.4 / Aegis v4.3 — locked), `dd_protection.py`, `portfolio_mc.py`, `CLAUDE.md`, the parent Notice, the entry stub, the predecessor EURUSD Notice or its audit trail. No grid search; literature-default single-config H-LORB was specified in the Notice but Phase B was never executed because Phase A aborted. No allocation, MC re-run, overlay reintroduction, or new strategy code.

The 6 ports under `analysis/gbpusd_lon/` are new code at the analysis layer (not strategy/protection/MC layer) and are governed by parent Notice §5 #13 reuse-path commitment + entry stub §5 checklist explicit authorization.

---

**End of audit.** Brief commit hash recorded (`158dc61`); methodology dir clean at session start; no edits attempted to frozen artifacts; M15-FX stop-rule registered as active and generalized to mechanism class (d) breakout per parent Notice §6.
