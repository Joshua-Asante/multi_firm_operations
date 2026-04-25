# Changelog

**Scope:** repo, methodology, and tooling changes only. Per-strategy version history lives in `strategies/<name>/<name>_CHANGELOG.md` (e.g. `strategies/aegis/aegis_CHANGELOG.md`).

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
