# Amendment 1 — OANDA re-scope of the 2026-04-26 Identify brief

**D-S-A domain:** data
**Authored:** 2026-04-26
**Authorized by:** Joshua (Phase 0 halt response, option 2)
**Parent brief:** Identify-phase brief for 15min bar-data corpus (2026-04-26, in conversation transcript).

---

## Why this amendment exists

Phase 0 of the parent brief halted: the brief specifies the Pepperstone feed as the canonical input (bar files at an unspecified Pepperstone path; trade CSVs at `data/tv_exports/pepperstone/{guardian,striker,aegis}.csv`). Neither the Pepperstone bar files nor the Pepperstone TV exports are present in the repo. The 2026-04-23 Aegis-on-Alchemy-mislabeled-as-Pepperstone failure is the binding prior — substituting OANDA silently would replay that failure.

The repo does have OANDA equivalents:

| Asset | Path |
|---|---|
| XAUUSD 15m bars | `data/bar_data/XAUUSD.csv` (parent repo, not git-tracked) |
| US30USD 15m bars | `data/bar_data/US30USD.csv` (parent repo, not git-tracked) |
| USDJPY 15m bars | `data/bar_data/USDJPY.csv` (parent repo, not git-tracked) |
| Guardian trades | `data/tv_exports/oanda/Guardian_Gold_v5.5_OANDA_XAUUSD_2026-04-25_9ae1f.csv` |
| Striker trades | `data/tv_exports/oanda/Striker_DJ30_v4.4_OANDA_US30USD_2026-04-25_86e9d.csv` |
| Aegis trades | `data/tv_exports/oanda/Aegis_USDJPY_v4.3_OANDA_USDJPY_2026-04-25_7ee6b.csv` |

This amendment re-scopes the Identify corpus to the OANDA feed, with explicit consequences below.

---

## D-S-A trace

This amendment operates in the **data** domain only. It does not change the framework, the strategies, the protections, or the loop ceremony.

- **D — Delete:** Drop "Pepperstone-canonical" status from every artefact this run produces. The corpus exists, but no finding it surfaces is eligible for lock-decision use without re-running on Pepperstone. Permitted D-test applied: "Is this a literal copy / encoding of something already retained?" — no, but the inverse: this corpus *is not* the canonical data the brief specified, so the canonical-status claim is the deletion target, not the data.
- **S — Simplify:** Accept the OANDA panel as-is. No attempt to source Pepperstone within this loop. The simpler representation is "OANDA proxy, label clearly".
- **A — Accelerate:** None. No index built; the corpus is small enough that re-runs are cheap.

---

## What changes vs. the parent brief

### Data sources

Wherever the parent brief says "Pepperstone", read "OANDA" for this run. Bar instrument naming changes: `DJ30` → `US30USD` (the OANDA symbol). The output artefact names retain `dj30` for consistency with strategy nomenclature.

Bar coverage: 2022-01-02 → 2026-04-19 (XAUUSD: 101,461 rows; US30USD: 101,245 rows; USDJPY: 106,820 rows). Two days earlier than the brief's target start, one day shorter at the end. Within tolerance for the seven extractions.

### Trade-CSV identity

`assert_tv_export()` from `lib/mvd.py` is called per CSV with `expected_broker="OANDA"`. If OANDA Aegis bars are pre-EOM-filter-era exports, that's flagged in Phase 0 and surfaced; not silently substituted.

### Output artefact metadata

Every CSV / JSON artefact produced under this amendment **must** include the columns / fields:

- `feed = "OANDA"` (not Pepperstone)
- `panel_window = "2022-01-02_2026-04-19"`
- `canonical_status = "PROXY"` (never `"CANONICAL"`)

The README at `docs/methodology/identify_corpus/2026-04-26/README.md` opens with a banner stating: *"All findings in this corpus are OANDA-proxy. No finding is eligible for lock-decision use until re-run against Pepperstone. Routes Notice-bound findings as 'OANDA-only patterns' per amendment."*

### Routing of findings

All findings from this corpus route to **Notice as OANDA-only patterns**. Per `docs/methodology/observation_routing.md`, this means:

- A finding can route **Closed** on its own (an OANDA-only pattern that fails to clear the four-rule overlay/policy gate is closed regardless of feed).
- A finding can route **Forward** as a question whose first dependency is "re-run on Pepperstone before this question becomes decidable".
- A finding **cannot** route **Action** on this corpus alone. Action requires the four rules — including the canonical-feed pre-condition for any rule grounded in MC calibration. The OANDA-canonical / Pepperstone-canonical two-tier rule binds.

### O4 / O6 / MC-relevant findings — explicit demotion

The parent brief flags O4 (cross-instrument bar correlation) and O6 (regime characterization) as the most plausible MC-input candidates. Under this amendment, both are **explicitly demoted to pattern-spotting status**:

- O4 simultaneous-adverse-window counts on OANDA do **not** authorize an MC re-run. They authorize a question on the Open Questions list whose first dependency is "verify on Pepperstone".
- O6 regime drift on OANDA is descriptive only. The 2026-04-23 lock MC anchored on Pepperstone remains the lock-decision MC; OANDA regime features are pattern-spotting input, not calibration input.

This is the "two-tier canonical: Pepperstone authoritative, OANDA proxy" rule binding at the Identify-output stage rather than only at the MC stage.

---

## What does NOT change

All scope guards from the parent brief stand verbatim:

- Strategy parameter changes: forbidden (locks: v5.5 / v4.4 / v4.3).
- Allocation changes: forbidden (G 0.34% / S 1.00% / A 1.50%).
- `dd_protection` changes: forbidden (single-tier 1.0% / 0.40×).
- MC re-runs: forbidden in this loop, even if O3 / O4 / O6 surface drift candidates.
- Overlay design or reintroduction: forbidden.
- BOJ / binary-event pause rules: out of scope.
- Pine code modification: forbidden.
- Cross-broker comparison (OANDA vs Pepperstone vs Alchemy): forbidden — this brief operates on OANDA only; the cross-broker question is its own loop.
- Anything on instruments outside the three locked symbols: forbidden.

Acceptance criteria (1)–(5) from the parent brief stand. Phase 0 must pass on OANDA paths before any extraction runs. No production-execution path is touched.

---

## Forbidden-D-test discipline note

Substituting OANDA for Pepperstone without surfacing it would have been a forbidden D-test in disguise — a "is this close enough?" model-fit substitution dressed as a permitted scope test. The skill (`anthropic-skills:inqhiori-algorithm`, §5) explicitly warns against silent substitution of a permitted-looking test for a forbidden one. This amendment is the surfacing: every OANDA finding carries the `canonical_status = "PROXY"` flag end-to-end.

If, during extraction, Claude Code finds itself implicitly applying a forbidden D-test (e.g., dropping a cohort because "OANDA noise is high here" or "this looks like a feed artefact"), surface it in the artefact metadata with a `forbidden_d_test_warning` field and proceed without the deletion. The next loop's Pre-Q gate decides.

---

## Phase 0 re-execution under this amendment

Phase 0 is re-run against OANDA paths. The Phase 0 script lives at `scripts/identify/2026-04-26/phase0_discovery.py` and applies MVD asserts:

- `assert_tv_export(broker="OANDA", version=...)` per strategy CSV
- `assert_min_rows` and `assert_window` per bar file
- Empirical timezone reconciliation: spot-check N entry timestamps against bar prices under chart-TZ-UTC and chart-TZ-NY hypotheses; record the resolved TZ per strategy in the README

Phase 0 result is logged to the README with PASS / FAIL per (1)–(3). On any FAIL, halt and report — the same halt criterion as the parent brief, against the OANDA-feed paths.

---

## Cross-references

- Parent brief: in conversation transcript, 2026-04-26.
- Two-tier canonical rule: user memory `feedback_two_tier_canonical_pepperstone_oanda.md`.
- Observation routing: `docs/methodology/observation_routing.md`.
- MVD asserts: `lib/mvd.py`.
- INQHIORI skill: `anthropic-skills:inqhiori-algorithm` (canonical Notion: `34ddc0b53c1181479d7bdecc61f47078`).
