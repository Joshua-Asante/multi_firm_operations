# Minimum Viable Defense (MVD) — methodology

**Status:** Active as of 2026-04-24.
**Authority:** [`docs/adr/2026-04-24-mvd-discipline.md`](../adr/2026-04-24-mvd-discipline.md).
**Purpose:** Prevent the recurring "result looked plausible so I shipped it" failure mode in load-bearing artifacts, with minimal friction.

## North star

Prevention with minimal friction. Defenses are inline assertions and template preambles in code-resident artifacts, not checklists or memory rules. Inline `assert` runs on every invocation regardless of attention state; checklists do not.

## Scope (5 mandatory triggers)

An artifact requires MVD if and only if it falls under one of:

1. **MC input panels** — anything `portfolio_mc.py` reads.
2. **Lock decision inputs** — every performance number cited in a lock brief.
3. **Risk-control production code** — `dd_protection.py`, Pine `risk_pct` / `dayStopPct` / SL / TP / session blocks.
4. **Allocation changes** — lot/risk per strategy in `accounts.json`; CLI `update`/`lots`.
5. **Specific numbers or named behavior cited in memory, ADR, or CHANGELOG.**

Out of scope: exploratory scripts, methodology drafts, ad-hoc charts, broker-feed comparisons not yet promoted, datasets on disk until used in scope.

## The library — 5 families

Implemented in [`lib/mvd.py`](../../lib/mvd.py).

### 1. Cardinality

Row counts, time-window span, page counts.

- `assert_min_rows(actual, minimum, label)` — fail if row count below floor.
- `assert_window(first_ts, last_ts, expected_min_days, label, tolerance_days)` — fail if time-span shorter than expected.

**Worked example.** OANDA fetch terminating after 2 pages: `len(df) ≈ 10K`, expected ≈ 100K. One line at end of fetch:
```python
assert_min_rows(len(df), 80_000, label="OANDA USDJPY 4yr")
```
would have raised on first run.

### 2. Identity

String identifiers (symbol, broker, version) verified at top of any script producing a load-bearing number. The most-leveraged single discipline: 70% of the audit-table instances are this class.

- `assert_symbol(actual, expected)` — strict equality. `USDJPY` and `USDJPY_X` are different feeds.
- `assert_broker(actual, expected)` — strict equality.
- `assert_version(actual, expected)` — strict equality.
- `assert_tv_export(csv_path, expected_strategy, expected_version, expected_broker, expected_symbol)` — strict equality on all four fields parsed from the canonical OANDA filename pattern `<Strategy>_<Instrument>_<Version>_<Broker>_<Symbol>_<YYYY-MM-DD>_<hash>.csv`. Catches the "wrong CSV in load slot" class (e.g. a Striker CSV in Guardian's path, a v5.4 export when v5.5 is locked) at the consuming site.

**Worked example.** Aegis 14mo Alch calibration loaded a CSV labeled "USDJPY" and reported $117K — actual symbol was the spread-included USDJPY, not the USDJPY_X feed used elsewhere. Reproducing on USDJPY_X gave ~$93K. One line at top of the calibration script:
```python
assert_symbol(df['symbol'].iloc[0], "USDJPY_X")
```
would have raised before any number was computed.

### 3. Contract

Guards must fire; fallbacks must not; named computations produce what their name says.

- `assert_no_fallback(fallback_count, label)` — fail if a "should never fire" fallback path was taken.
- `assert_guard_fired(event_count, label)` — fail if a guard / stop / cap never fired across the panel.

**Worked examples.**

`portfolio_mc` 1R median-fallback: silent fallback path was firing on edge cases, biasing MC results. One line at end of 1R compute:
```python
assert_no_fallback(fallback_count, label="1R median compute")
```

Striker `dayStopPct = -3%` inert across 4yr panel — wasn't doing what its name implied. One line at end of Pine validation script:
```python
assert_guard_fired(day_stop_events, label="Striker dayStopPct -3%")
```
would have raised; we'd have known to lower to -2% before locking, not after.

### 4. Cross-source

TV-vs-Python, Pepperstone-vs-OANDA, prose-vs-Pine reconciliation gates.

- `assert_reconciled(actual, expected, tol_pct, label)` — fail if a value disagrees with an independent source by more than `tol_pct`.

**Worked example.** TV `<30-day` P&L distortion via JPY→USD conversion hook. CSV-derived P&L vs TV-displayed P&L diverged by >5% on short ranges. One line in any TV-ingest helper:
```python
assert_reconciled(tv_pnl, csv_pnl, tol_pct=0.05, label="TV vs CSV P&L")
```

### 5. Code-vs-doc

Briefs `view` and paste literal production lines. Brief templates at [`docs/templates/`](../templates/) enforce a verification-block preamble. "Primary X" claims require a generating script, not a sentence.

- `assert_file_contains(path, expected_text, label)` — fail if a file doesn't contain a literal text fragment, used to anchor doc claims to production code.

**Worked example.** Aegis EOM described in memory as "last 3 trading days"; Pine actually reads `dayofmonth >= 29` (calendar days, not trading days). One line in any methodology doc that would auto-validate the claim:
```python
assert_file_contains("strategies/aegis/aegis_usdjpy_v4.3.txt", "dayofmonth >= 29",
                     label="Aegis EOM rule")
```

**Meta-example (deployment-time, 2026-04-24).** This very ADR was originally drafted as `00XX-mvd-discipline.md` (numeric-prefix convention). Listing `docs/adr/` before authoring the destination path surfaced that the repo uses `YYYY-MM-DD-<slug>.md` instead — caught and corrected pre-commit. The general form: before authoring a path string or convention claim, read peer artifacts in the target directory.

## Producer-side rule

For any in-scope artifact: identity assertions appear within ~5 lines of identifier declaration. Cardinality and contract assertions appear at producing site, not consuming site (the author is the only one with full context to write them).

## Consumer-side promotion check

Any brief, ADR, memory entry, or CHANGELOG entry that cites specific numbers or named behavior must include:

> **MVD-attest:** For each cited number, the producing script's first ~5 lines include identity assertions.

If the check fails, the artifact is not promoted: either the producing script is hardened, or the citation is removed.

## Audit table — 10 instances driving the library

Pre-MVD failure cases. Each row's "MVD" column is the one-line defense that would have caught it.

| # | Date | Instance | MVD | Family | Identity? |
|---|------|----------|-----|--------|-----------|
| 1 | pre-04-17 | `portfolio_mc` 1R median-fallback firing silently | `assert_no_fallback(fallback_count, "1R compute")` | Contract | Y (broad) |
| 2 | 2026-04-24 | OANDA fetch terminating at ~10K rows instead of ~100K | `assert_min_rows(len(df), 80_000, "OANDA pull")` + `assert_window(...)` | Cardinality | N |
| 3 | 2026-04-17 | Production `dd_protection` rule vs memory drift (Rule 0 catalyst) | Brief preamble must `view` the production file and paste literal rule block | Code-vs-doc | Y (broad) |
| 4 | 2026-04-22 | Aegis $117K calibration on USDJPY mislabeled as USDJPY_X | `assert_symbol(df['symbol'].iloc[0], "USDJPY_X")` | **Identity** | Y (strict) |
| 5 | 2026-04-21 | Striker primary bust = pyramid-reversal (actual: solo gap-fill) | "Primary X" claim must be backed by event-count + $ attribution table generated by script | Code-vs-doc / cardinality | Y (broad) |
| 6 | 2026-04-21 | Striker `dayStopPct = -3%` inert across 4yr panel | `assert_guard_fired(day_stop_events, "Striker -3%")` | Contract | N |
| 7 | pre-04-22 | Aegis EOM "last 3 trading days" vs Pine `dayofmonth >= 29` | `assert_file_contains("strategies/aegis/aegis_usdjpy_v4.3.txt", "dayofmonth >= 29")` | Code-vs-doc | Y (strict) |
| 8 | 2026-04-23 | "4yr Alchemy panel" actually 14mo (no 2022 regime) | `assert_window(first, last, expected_min_days=4*365, "Alch panel")` | **Identity** + cardinality | Y (strict) |
| 9 | pre-04-22 | TV `<30-day` P&L distortion on JPY pairs | `assert_reconciled(tv_pnl, csv_pnl, 0.05, "TV vs CSV")` | Cross-source | N |
| 10 | 2026-04-25 | "DD" cited as 5.01% (intra-trade) on MVD page vs 3.76% (trade-close) in `aegis_CHANGELOG.md` — same metric name, different measurements | Use qualified labels in `assert_reconciled` (e.g. `"DD_intra vs canonical"`, never bare `"DD"`) — discipline at call site | **Identity** | Y (broad) |

**Summary.** 5 families. 7/10 instances are identity-class (strict or broad) — labels-as-verification is the dominant sub-pattern. 7/10 reduce to a single one-line assertion; 3 require template-level discipline (brief preamble, "primary X" backing requirement).

## Update protocol

Every new caught bug post-MVD-launch:

1. Adds a row to the audit table above.
2. If the catch reveals a new family or a new identity sub-pattern, adds a worked example to this doc and (if applicable) a new helper in `lib/mvd.py`.
3. Enforced as a step in any post-mortem or CHANGELOG entry that records the bug.

This is the defense against library decay (catching the previous war while current risk drifts un-covered).

## References

- ADR: [`docs/adr/2026-04-24-mvd-discipline.md`](../adr/2026-04-24-mvd-discipline.md)
- Library: [`lib/mvd.py`](../../lib/mvd.py)
- Templates: [`docs/templates/`](../templates/)
- Standing Rule 0 codification (precursor): 2026-04-17 (memory)
- OANDA bar dataset note (catalyst): Notion page `34ddc0b53c1181339eddf34db8978d8c`
- Conversation of record: 2026-04-24 (Identify → Notice → Question → Hypothesize → Investigate → Reflect)

---

**MVD-attest:** For each cited number above (e.g. "70%", "7/10", "10 instances"), the producing source is the audit table on this page. The audit table was assembled by manual review of the recent_updates section of the userMemories block on 2026-04-24 (instances 1–9) and extended on 2026-04-25 with instance #10 (DD label ambiguity, surfaced by [PR #2](https://github.com/Joshua-Asante/prop_firm_pipeline/pull/2)); numbers traced on first read.
