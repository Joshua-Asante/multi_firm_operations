# Changelog

**Scope:** repo, methodology, and tooling changes only. Per-strategy version history lives in `strategies/<name>/<name>_CHANGELOG.md` (e.g. `strategies/aegis/aegis_CHANGELOG.md`).

## 2026-04-28

- Stale-artifact sweep across the main checkout: Guardian Pine header risk-comment refreshed `0.30%` → `0.34%` (`strategies/guardian/guardian_gold_v5.5.txt`); Striker `stopAtr` tooltip refreshed `LOCKED: 1.35` → `LOCKED: 1.25` with v4.3→v4.4 derivation note (`strategies/striker/striker_dj30_v4.4.txt`); 2026-04-17 portfolio-allocations ADR's funded-ramp risk bullet marked superseded by the same-day unified-allocation decision; Guardian conflict overlay's "0.55% baseline" annotated as pre-v5.1-era to resolve the timing mismatch with v5.1's 0.30% cold-start; Aegis CHANGELOG's "post-v4.3 portfolio MC re-run" Unreleased item moved into the v4.3 entry as completed (Aegis bust attribution 47% → 27.6% at canonical 92.73% pass / 0.65% bust config).
- Notice-phase compression cleanup: deleted closed-bucket standing JSON outputs per `docs/methodology/observation_routing.md` rule (`o1`/`o3`/`o4`/`o5`/`o6`/`phase0_2026_04_27.json`, `rule0_sanity.json`, `B3_intraday_vs_daily.json`). Retained B1/B2 (Forward) plus `figures/B1_rolling_corr.png`. All deleted outputs are regenerable from the sibling `.py` scripts.
- v5.5 validation halt (`docs/historical/v5_5_validation_halt_2026-04-21.md`) annotated with resolution pointer to the 2026-04-23 lock; `run_v55_validation.py` moved out of `docs/historical/` into `scripts/`. Repo-root markdown stray and `data/bar_data/` corpus tracked.

## 2026-04-27

- `notice: 2026-04-27 OANDA-proxy bar-corpus scan` — second Notice run on the 2026-04-26 OANDA-proxy Identify corpus. Phase 0 PASS, five extractions (O1–O6) with `canonical_status = "PROXY"` end-to-end (Action routing forbidden on this corpus per the OANDA rescope amendment). Findings doc: `analysis/notice_phase/findings_2026-04-27.md`. Closed-bucket standing outputs from this run were removed in the 2026-04-28 sweep.

## 2026-04-26

- **Identify-corpus 2026-04-26 (OANDA-proxy)** — full INQHIORI loop iteration on the OANDA-proxy bar corpus (XAUUSD/US30/USDJPY 15m, 2022→2026). Materials under `docs/methodology/identify_corpus/2026-04-26/` including `README.md`, `phase0_log.json`, and `AMENDMENT_oanda_rescope.md` (formalizes the two-tier canonical: Pepperstone authoritative, OANDA proxy; D-test forbidden on proxy alone).
- **Inquire-phase findings (var-alloc, AUDNZD)** — `docs/methodology/findings/2026-04-26_var_alloc_observables_stage0.md`, `2026-04-26_var_alloc_dd_state_REJECTED.md`, `2026-04-26_audnzd_REJECTED.md`. Both verdicts 4A REJECTED.

## 2026-04-25 (methodology compression)

- Added `docs/methodology/observation_routing.md` — three-bucket gate (Closed/Action/Forward) replacing the prior Notice/Inquire two-phase framework. Algorithm-driven simplification (Question / Delete / Simplify) — Notice's protective benefit was redundant once Rule 0, Iran/Hormuz overlay-trigger discipline, and documented re-MC triggers were in place. Standing closed-bucket JSON/figure/CSV outputs deleted in the same compression; B-series (Forward) retained.
- Updated `docs/methodology/1r_estimation.md` — five follow-ups in the same day: equity-compounding clarification on Guardian v5.5 1R (median = 0.3405%, hits designed 0.34% to 4dp); live-sizing Rule 0 cross-check via `accounts.calc_multiplier`; Striker pyramid decomposition (corrects the 17%-inflation framing — initial entries +2.9%, pyramid layers +76.6%); pyramid 3.50× multiplier verified directly from layer-1/layer-2 qty pairs; pre-staged Forward question on within-day per-trade hard-cap vs leave-and-monitor-live for the 2025-02-07 fresh-peak single-trade outlier.
- Q5 break-window P&L analysis: ESCALATE Q3 (positive-tail co-movement, dd_protection rule persists at canonical config).

## 2026-04-25 (retrofit)

- Added `docs/adr/2026-04-25-mvd-retrofit.md` — ADR scoping the production-code retrofit: `portfolio_mc.py`, `dd_protection.py`, audit row #10.
- Updated `docs/methodology/mvd.md` — added audit row #10 (DD label ambiguity, Identity-class), refreshed summary stats `9 → 10 instances`, `67% → 70% identity`, `6/9 → 7/10 single-line`. Top-of-section "67%" reference at line 42 also updated. Bottom MVD-attest refreshed.
- `portfolio_mc.py` retrofit (separate commit): `implied_1r` returns `(r1, fell_back)`; canonical-config silent-fallback path now raises via `assert_no_fallback`. `load_trades` validates input panels via `assert_min_rows` + `assert_window`. Maps to methodology family **Contract** (audit instance #1) and **Cardinality** (audit instance #2).
- `dd_protection.py` retrofit (separate commit): module-load `_validate_protection_rule()` runs `assert_guard_fired` (just-above trigger) + `assert_no_fallback` (just-below trigger). Catches future drift in `DD_TRIGGER` / `DD_SCALE`. Maps to methodology family **Contract**.
- **MVD-attest:** numbers cited in the retrofit ADR (`~2 hrs`, `9→10`, `67%→70%`) trace to: time tracked on the retrofit conversation 2026-04-25; audit table at `docs/methodology/mvd.md` updated in this PR.

## 2026-04-25

- Added `scripts/dryrun_aegis_v4_3.py` — MVD helper sanity gate. Exercises all 9 helpers in `lib/mvd.py` against the canonical Pepperstone 52mo Aegis v4.3 CSV (123 trades, Jan 2022 → Apr 2026). All 5 canonical numbers reproduce: net $178,208.42, PF 4.186, WR 60.16%, intra-trade DD 5.01%, trade-close DD 3.82%.
- **Finding (Identity-class candidate, audit instance #11):** "DD" without a labeling qualifier is ambiguous. The MVD page cited 5.01% (intra-trade); `aegis_CHANGELOG.md` cited 3.76% (trade-close). Both are correct, just different metrics. Harness asserts each explicitly with the qualifier in the label string.
- **MVD-attest:** the harness output is the producing source for the canonical-reproduction claim; identity assertions are within the first 5 lines of `main()` (filename-parsed symbol/broker/version verified before any metric is computed).

## 2026-04-24

- Added `docs/adr/2026-04-24-mvd-discipline.md` — ADR formalizing the Minimum Viable Defense discipline for load-bearing artifacts crossing the live capital boundary.
- Added `docs/methodology/mvd.md` — methodology reference: 5 families, worked examples, 9-instance audit table, producer/consumer rules.
- Added `lib/mvd.py` — assertion library (9 helpers across 5 families: cardinality, identity, contract, cross-source, code-vs-doc).
- Added `docs/templates/lock_decision.md` — lock brief template with verification preamble and MVD-attest section.
- Added `docs/templates/calibration_brief.md` — calibration brief template with identity-assertion preamble.
- Added `docs/templates/bust_analysis.md` — bust analysis template requiring script-generated event-count + $ attribution.
- **MVD-attest:** the audit table in `docs/methodology/mvd.md` is the source for all numbers cited in the ADR (`67%`, `6/9`, `9 instances`, etc.); numbers traced on first read.
