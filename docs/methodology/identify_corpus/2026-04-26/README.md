# Identify-phase corpus — 2026-04-26 (OANDA proxy)

> **2026-04-28 update — Action gate lifted.** OANDA findings can now route to
> Action proposals; Joshua validates in TradingView against Pepperstone bars
> before any code/lock change. CLAUDE.md headline MC numbers stay
> Pepperstone-anchored (lock-decision artifacts). Data-provenance discipline
> (tag the source feed, never silently substitute) is unchanged. See
> [`AMENDMENT_oanda_rescope.md`](AMENDMENT_oanda_rescope.md) supersession note.
>
> *Original banner (historical):* All findings in this corpus are OANDA-proxy;
> Pepperstone re-fit was previously a hard prerequisite for Action.

## Banner — corpus identity

| Field | Value |
|---|---|
| Brief | Identify-phase brief for 15min bar-data corpus (in conversation, 2026-04-26) |
| Amendment | [`AMENDMENT_oanda_rescope.md`](AMENDMENT_oanda_rescope.md) — OANDA re-scope authorized 2026-04-26 |
| Feed | OANDA |
| Bar panel window | 2022-01-02 → 2026-04-19 |
| Canonical status | PROXY (not Pepperstone) |
| Strategy versions | Guardian v5.5 / Striker v4.4 / Aegis v4.3 (locked) |
| INQHIORI loop position | Identify (first I). Next phase: Notice scan via observation routing gate. |

---

## Phase 0 — verification log

All Phase 0 checks PASSED on the OANDA paths. Detailed results in [`phase0_log.json`](phase0_log.json).

| Step | Result |
|---|---|
| TV identity (Guardian) | PASS — Guardian/Gold/v5.5/OANDA/XAUUSD |
| TV identity (Striker) | PASS — Striker/DJ30/v4.4/OANDA/US30USD |
| TV identity (Aegis) | PASS — Aegis/USDJPY/v4.3/OANDA/USDJPY |
| Bar verify (XAUUSD) | PASS — n=101,461 rows, span 2022-01-02..2026-04-19 |
| Bar verify (US30USD) | PASS — n=101,245 rows, span 2022-01-02..2026-04-19 |
| Bar verify (USDJPY) | PASS — n=106,820 rows, span 2022-01-02..2026-04-19 |
| TZ reconciliation (Guardian) | PASS — best EST (1.81 px diff) vs UTC (4.07) — chart-TZ NY |
| TZ reconciliation (Striker) | PASS — best EDT (0.20 px diff) vs UTC (239.7) — chart-TZ NY (decisive) |
| TZ reconciliation (Aegis) | PASS — best EDT (0.084 px diff) vs UTC (0.31) — chart-TZ NY |

**Resolved chart-TZ:** all three strategies use `America/New_York` (auto EST/EDT). Persisted in [`resolved_tz.json`](resolved_tz.json).

---

## Inventory

### Phase 0 outputs

- [`phase0_log.json`](phase0_log.json) — verification log
- [`resolved_tz.json`](resolved_tz.json) — per-strategy chart-TZ resolution

### O1 — Counterfactual rejected-trade simulation

| File | Cohort size | Notes |
|---|---|---|
| [`O1_rejected_trades_guardian.csv`](O1_rejected_trades_guardian.csv) | 2,979 sims | mean sim_R=+0.85; 90% stop, 9% TP, 2% stale |
| [`O1_rejected_trades_striker.csv`](O1_rejected_trades_striker.csv) | 7,224 sims | mean sim_R=−0.08; 87% BE, 13% stop, 0.1% TP — **base-leg only (no pyramid; understates Striker edge)** |
| [`O1_rejected_trades_aegis.csv`](O1_rejected_trades_aegis.csv) | 7,840 sims | mean sim_R=−0.07; 84% BE, 16% stop, 0.1% TP |

**Per-gate cohort sizes (smallest):** Guardian `block_MonH12` n=25, Aegis `block_TueH10` n=105. All ≥10; Rule-1 thin-cohort threshold not tripped at the gate level.

### O2 — Intra-trade MFE/MAE paths

| File | Trades |
|---|---|
| [`O2_trade_paths_guardian.csv`](O2_trade_paths_guardian.csv) | 200 |
| [`O2_trade_paths_striker.csv`](O2_trade_paths_striker.csv) | 233 |
| [`O2_trade_paths_aegis.csv`](O2_trade_paths_aegis.csv) | 123 |

### O3 — Conversion funnel

Static + rolling 90-day per strategy:

- [`O3_conversion_funnel_{guardian,striker,aegis}.csv`](O3_conversion_funnel_guardian.csv) — stage counts and pass rates
- [`O3_conversion_rolling_{guardian,striker,aegis}.csv`](O3_conversion_rolling_guardian.csv) — daily rolling 90-day pass rates

### O4 — Cross-instrument bar correlation

| File | Notes |
|---|---|
| [`O4_bar_corr_static.csv`](O4_bar_corr_static.csv) | XAU-DJ30=+0.16, XAU-USDJPY=−0.31, DJ30-USDJPY≈0 (101,117 aligned bars) |
| [`O4_bar_corr_rolling.csv`](O4_bar_corr_rolling.csv) | 60-day rolling pairwise; 1,317 daily-end rows |
| [`O4_simultaneous_adverse_windows.csv`](O4_simultaneous_adverse_windows.csv) | 213 windows where all three instruments moved adversely (down) at ≥1σ in the same 15min bar |

### O5 — Filter forensics (18 filters)

All 18 cohorts have n≥795 and are flagged **STRUCT** (not idiosyncratic by the >50%-of-bars-in-top-5-dates heuristic).

Files: `O5_filter_forensics_<strategy>_block_<filter>.csv` — see directory listing for the full set.

### O6 — Regime features (per instrument, monthly)

- [`O6_regime_features_XAUUSD.csv`](O6_regime_features_XAUUSD.csv) — 52 months
- [`O6_regime_features_US30USD.csv`](O6_regime_features_US30USD.csv) — 52 months
- [`O6_regime_features_USDJPY.csv`](O6_regime_features_USDJPY.csv) — 52 months

### O7 — Slippage realism

| File | Legs | Thin cohorts (n<10) |
|---|---|---|
| [`O7_slippage_realism_guardian.csv`](O7_slippage_realism_guardian.csv) | 400 | entry/reopen_w n=2; exit/reopen_w n=3; exit/gap_minor n=2 |
| [`O7_slippage_realism_striker.csv`](O7_slippage_realism_striker.csv) | 466 | exit/reopen_w n=8 |
| [`O7_slippage_realism_aegis.csv`](O7_slippage_realism_aegis.csv) | 246 | none |

---

## Rule-1 thin-cohort flags

Per the parent brief, every artefact under O1 / O5 / O7 carries `thin_cohort` columns where applicable. Surfaced cells with n<10:

- **O7 Guardian:** weekly-reopen entry leg n=2; weekly-reopen exit leg n=3; minor-gap exit leg n=2. The reopen cohort is structurally small for a strategy that trades only NY-day-08-16 — Sunday-evening reopens land outside the trading window, so reopen-adjacent fills are rare. Do not interpret slippage moments on these cells without explicit small-N caveat.
- **O7 Striker:** weekly-reopen exit leg n=8. Same structural reason.
- **O7 Aegis:** no thin cells.
- **O5:** no thin cells (smallest cohort 795 bars).
- **O1:** no per-gate cohort below n=25.

---

## Forbidden-D-test discipline notes

### O1 declared simplifications

The O1 simulation deliberately omits some locked Pine logic to keep the counterfactual sim tractable. **These are declared simplifications, not silent deletions.** Each omission was considered against the §5 forbidden-D-test list and routed as a permitted scope/cardinality reduction, not a "doesn't fit my model" deletion:

- **Striker pyramid (1.29 ATR + 6 bars, 350% size):** omitted. The Pine header says pyramid "is the entire structural edge". The mean sim_R = −0.08 for the rejected Striker cohort therefore **substantially understates** the actual P&L the rejected trades would have produced. This is logged in the artefact metadata column `simulation_simplifications` on every row.
- **Striker trail (wide/tight) and day soft-stop (−2% init eq):** omitted. Trail omission removes a partial winner-protection mechanism; day-stop omission is sequential-state and outside per-bar simulation scope.
- **Guardian grace stop (2.0× until bar 1):** modelled.
- **Aegis BE (0.3 ATR + 0.15 pad):** modelled.
- **All sims:** assume entry fill at signal-bar close, matching Pine `process_orders_on_close=true` for Striker and the entry-on-bar-close convention for the others.

These simplifications mean **O1 is upper-bounded as descriptive evidence**: a positive sim_R cohort is suggestive (would warrant a Notice-phase question); a negative or zero sim_R cohort cannot be interpreted as "filter is working" without re-sim including the omitted edge components.

### Permitted vs forbidden D-tests applied during extraction

- **Permitted (cardinality):** O5 small cohorts (n<10) flagged via `thin_cohort=1` rather than dropped. None deleted.
- **Permitted (scope):** O4 simultaneous-adverse window detection requires `min_periods=500` for rolling std — early-panel bars dropped because they have no rolling-std reference, not because of any signal-property test.
- **Forbidden — caught and surfaced:** none triggered during this run. The OANDA-substitution risk at the brief level was caught at Phase 0 and surfaced via [`AMENDMENT_oanda_rescope.md`](AMENDMENT_oanda_rescope.md) rather than silently substituted. Per the skill's §5 example, this is the gate working as intended.

---

## Notice-bound observations seeded by this run

These are observations surfaced *during corpus production*. They are not Notice-phase findings yet — Notice is the next loop phase. Routing each through `docs/methodology/observation_routing.md` is Notice's job, not Identify's.

1. **Doc/code TZ skew on Guardian.** [CLAUDE.md](../../../CLAUDE.md) describes Guardian session as "0800–1600 UTC (NY Extended)". Phase 0 empirically resolves Guardian chart-TZ to `America/New_York` (EST 1.81 px diff vs UTC 4.07). Pine `time(period, "0800-1600:23456")` uses chart-TZ unless an explicit TZ is passed; combined with a NY chart, the actual session is 08-16 NY = 13-21 UTC (EST) / 12-20 UTC (EDT), **not** 08-16 UTC. Same observation may apply to other doc claims. **Forward-class candidate for Notice scan; do not action without doc/code skew audit per `docs/operational_rules.md`.**
2. **Striker rejected-cohort BE-dominance signature (87% BE).** Even with the explicit pyramid omission, the BE-dominant exit profile of the rejected universe matches the actual Striker character. Suggests the filters are blocking trades whose BE-or-stop noise resembles the population, not selectively blocking the worst tail. Closed-class candidate (filters not deleting tail-risk cells preferentially).
3. **Aegis EOM cohort (n=795 bars, 53 distinct dates) is structurally large and STRUCT-flagged** — the 2026-04-22 EOM lock was on Pepperstone evidence; this OANDA cohort independently has the structural mass needed to characterize. Forward-class candidate: re-run O5 EOM forensics on Pepperstone to verify the structural signature transfers (separate loop per amendment).
4. **XAU-USDJPY 15min bar correlation = −0.31** (static). Daily-level analyses already in the codebase; 15min level surfaces an inverse correlation tighter than the daily aggregate. Forward-class candidate, gated on Pepperstone re-run before any MC-input revision (per amendment).
5. **O4 simultaneous-adverse 1σ windows: 213 events over 4yr.** ~50 per year. Concentration analysis (clustering by month / week / regime) not performed in this run. Forward-class candidate.

These five observations are the candidate Notice-input list. Notice will route each through the three-bucket gate.

---

## Acceptance verification

Per parent brief §"Acceptance criteria":

- [x] Phase 0 reconciliation passes for all three TV CSVs and all three bar files.
- [x] All seven O-artefacts produced under `docs/methodology/identify_corpus/2026-04-26/`.
- [x] README.md exists, reports Phase 0 results, lists thin-cohort and forbidden-D-test discipline notes.
- [x] No file under `prop_firm_pipeline/`, no Pine file, and no Notion page modified by this run. (Worktree-only writes.)
- [x] No new entry written to `dd_protection.py` config, `accounts.json`, or any production-execution path.

---

## Cross-references

- Amendment: [`AMENDMENT_oanda_rescope.md`](AMENDMENT_oanda_rescope.md)
- Methodology: [`../../observation_routing.md`](../../observation_routing.md)
- 1R: [`../../1r_estimation.md`](../../1r_estimation.md)
- Operational rules: [`../../../operational_rules.md`](../../../operational_rules.md)
- MVD asserts (used by Phase 0): [`../../../../lib/mvd.py`](../../../../lib/mvd.py)
- Two-tier canonical rule: user memory `feedback_two_tier_canonical_pepperstone_oanda.md`
- INQHIORI ⊕ The Algorithm: skill `anthropic-skills:inqhiori-algorithm` (Notion `34ddc0b53c1181479d7bdecc61f47078`)
- Scripts: [`../../../../scripts/identify/2026-04-26/`](../../../../scripts/identify/2026-04-26/)
