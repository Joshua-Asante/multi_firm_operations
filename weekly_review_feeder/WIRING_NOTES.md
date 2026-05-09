# Wiring notes — `weekly_review_feeder` mc/dd wrappers

**Wired:** 2026-05-09
**Branch:** `claude/bold-khorana-996336`
**Handoff:** `cc-handoff-wire-weekly-review-feeder-zesty-pascal` (2026-05-09)

## Summary

| Wrapper       | Status              | Pattern                                                              |
|---------------|---------------------|----------------------------------------------------------------------|
| `mc_wrapper`  | WIRED               | Composed Pattern A (helper composition) — see §mc-wrapper below     |
| `dd_wrapper`  | BLOCKED per §8      | dd_protection.py is a state machine, not an event log               |

**SHAs at wiring time:**
- `portfolio_mc.py` → `8ad8921`
- `dd_protection.py` → `0a10844`

## §0 Rule-0 read findings — three premise failures in the handoff

### Premise 1 (FAILED): Package exists in this worktree

The `weekly_review_feeder/` package was untracked in the **main** worktree only. Never committed to any branch. This worktree (`bold-khorana-996336`) did not contain it. Resolved by importing the package as a scaffolding commit (`chore(feeder): import weekly_review_feeder package scaffolding from main worktree`) before wiring.

### Premise 2 (FAILED): `portfolio_mc.py` has Pattern A (callable) or Pattern B (CLI with week-range flags)

Verified by reading `portfolio_mc.py` end-to-end:

- **Public callables**: `load_trades`, `implied_1r`, `build_daily_panel`, `build_week_blocks`, `_simulate_path`, `run_seed`, `compute_default_config`, `report_default`, `mode_default`, `mode_historical`, `mode_sensitivity`. **No** `weekly_band(week_start, week_end)` or any week-range function.
- **CLI flags**: `--dd-trigger`, `--dd-scale`, `--no-protection`, `--historical`, `--sensitivity`, `--guardian-risk`, `--panel {pepperstone,oanda}`, `--parallel`. **No** `--week-start`/`--week-end`/`--mode json`.
- **Output**: plain-text printout. No JSON mode.
- **Output granularity**: full-history aggregates only — pass/bust rates, p50/p95/p99 DD percentiles, bust attribution. **No weekly P&L percentile output.**
- **Bootstrap dimension**: `run_seed` resamples Mon-anchored 5-day blocks **uniformly from the whole panel** (`portfolio_mc.py:241`). No calendar-week conditioning.

Resolution: composed Pattern A — see `mc_wrapper` section below.

### Premise 3 (FAILED): `dd_protection.py` writes an event log

Verified by reading `dd_protection.py` end-to-end:

- Single state file at `dd_protection.py.parent / "dd_protection_state.json"`. **Not** JSONL. **Not** Python `logging` text. **Not** a per-event append log.
- Content shape: one JSON object with `starting_equity`, `peak_equity`, `last_equity`, and a `history: []` array of **equity-update snapshots** (each: `timestamp`, `equity`, `peak`, `dd_from_peak`, `multiplier`).
- **No event taxonomy**: the strings `tier_change`, `risk_multiplier_change`, `FIRE-alert` named in the handoff appear nowhere in the source. There is no `event` field.
- **State file does not exist yet** — created on first equity update via `python dd_protection.py <equity>`.
- CLI has only: show status, log new equity, `--history`, `--reset`. No `--events --since --until`.

This is exactly the §8 named escalation case. Resolution: BLOCKED — see `dd_wrapper §8` section below.

## `mc_wrapper` — composed Pattern A

### Composition path

```
load_trades(panel_csv) per Pepperstone strategy   # 4 strategies
    -> build_daily_panel(trades_by_strat, ALLOCATIONS)
    -> build_week_blocks(panel)                   # (n_blocks, 5, n_strats)
    -> blocks.sum(axis=(1, 2))                    # weekly P&L vector
    -> np.percentile([10, 50, 90])
    -> {"p10": float, "p50": float, "p90": float}
```

### Why panel-wide (week_start/week_end accepted but unused)

The locked MC anchor is calibrated against the 52-month Pepperstone panel (~220 Mon-anchored 5-day blocks). Per-week conditioning would require same-week-of-year subsetting, which yields ~4 blocks per calendar week — too thin for stable percentiles. The `(week_start, week_end)` signature is preserved for forward compatibility (per-week conditioning + provenance); the current implementation ignores them.

`tests/test_mc_wrapper.py` pins this contract via a stability check: calling `get_mc_band_for_week` with two different week ranges must return identical bands. If a future refactor introduces filtering, the test fails loudly.

### 1R-fallback guard

Mirrors `compute_default_config`'s assertion at `portfolio_mc.py:358-362`. If any strategy's `implied_1r` falls back to median-loss (n<5 full stops), the band is silently miscalibrated by ~10pp (per user memory `portfolio_mc_1r_fallback_trap.md`). The wrapper raises rather than returning a miscalibrated band.

### Defensive behaviors (verified)

- Module-load: triggers `dd_protection._validate_protection_rule()` which pins `DD_TRIGGER == 0.015 / DD_SCALE == 0.40`. Constant drift fails import.
- `load_trades`: triggers MVD `assert_min_rows` (≥100 rows) and `assert_window` (≥4yr panel) per CSV.
- Missing panel CSV: raises `FileNotFoundError` with full path. Verified by temporarily renaming `Striker_NAS100_v1_PEPPERSTONE_NAS100_2026-05-05_7ca6f.csv` and re-running the live smoke (§3.2 below) — got `FileNotFoundError: [Errno 2] No such file or directory: ...Striker_NAS100_v1_PEPPERSTONE_NAS100_2026-05-05_7ca6f.csv`.

## `dd_wrapper` — §8 BLOCKED

### Structural finding

`dd_protection.py` is a state machine. It does not emit a discrete event stream. Instead:

- `dd_protection_state.json` is the single persistence target (next to `dd_protection.py`).
- The file holds one JSON object: `{starting_equity, peak_equity, last_equity, history: []}`.
- The `history` array is appended on each `python dd_protection.py <equity>` invocation.
- Each history entry is a **snapshot** (`timestamp`, `equity`, `peak`, `dd_from_peak`, `multiplier`), not an event.
- The strings `tier_change`, `risk_multiplier_change`, `FIRE-alert` (named in the handoff §2) do not appear anywhere in `dd_protection.py`.
- The state file does not exist on a fresh checkout.

### Heuristic considered and rejected per §8

A "multiplier-transition counter" could be derived from the snapshot history: walk `state["history"]`, count entries where `multiplier` differs from the prior entry, filter to the week range. This was considered and **rejected** because:

1. Handoff §8 covers this exact case ("dd_protection.py doesn't log events at all and only writes state snapshots") and instructs: **DO NOT improvise**.
2. The handoff §2 contract requires a "per existing dd_protection convention" event definition. No such convention exists. Inventing one violates the contract and locks future readers into a definition that wasn't reviewed by the upstream.
3. A multiplier-transition heuristic would equate "DD activated/cleared on day X" with "trigger event" — a semantic narrowing the wrapper has no authority to make.

### Recommended upstream follow-ups

Pick one for the next pass:

1. **Extend `dd_protection.py`** with a real event-log emit path: write a JSONL event line whenever `multiplier` changes, alongside the existing state-file write. Wrapper then becomes Shape 1 (parse JSONL).
2. **Redefine the wrapper contract** explicitly: rename `count_dd_events_for_week` to `count_multiplier_transitions_for_week` and document that the heuristic is derived (transitions in snapshot history), not pulled from a per-existing convention. Then implement that.
3. **Accept that `dd_events` is unsupported** until either (1) or (2) lands. The orchestration layer's existing `try/except NotImplementedError` path already records `dd_snapshot = "STUB-not-wired"` and the `--skip-dd` flag works — so this is operationally fine for the current Notion Weekly Review use case if `dd_events` is non-critical.

## Verification — outputs

### §3.1 W19 regression (skip-mode)

```
$ cd weekly_review_feeder && python -m tests.test_w19
...
=== ALL CHECKS PASSED ===
```

Full payload from skip-mode test (relevant fields):

```
mc_p10        : 0.0
mc_p50        : 0.0
mc_p90        : 0.0
mc_invocation : "skipped"
dd_events     : 0
dd_log_snapshot_at : "skipped"
warnings      : ["PTL query skipped (--skip-notion)",
                 "No PTL entries for week; signals_taken inferred from fills.",
                 "MC band skipped (--skip-mc); P10/50/90 set to 0.0",
                 "DD log skipped (--skip-dd); dd_events set to 0"]
```

### §3.2 Live wiring smoke (mc real, dd skipped per §8)

```
$ PYTHONPATH=weekly_review_feeder \
  WRF_BACKTEST_DIR=weekly_review_feeder/tests/fixtures \
  python -m weekly_review_feeder \
    --week 2026-W19 \
    --fills-csv weekly_review_feeder/tests/fixtures/w19_dxtrade_fills.csv \
    --no-log --skip-dd --skip-notion --mode json
```

Payload (verbatim):

```json
{
  "week": "2026-W19",
  "week_start": "2026-05-04",
  "week_end": "2026-05-08",
  "trading_days": 5,
  "realized_pnl": -878.4,
  "backtest_equiv_pnl": -675.68,
  "edge_captured_ratio": null,
  "mc_p10": -2095.09,
  "mc_p50": 40.84,
  "mc_p90": 11980.21,
  "mc_placement": "P10-P50",
  "g_pnl": -878.4,
  "dj30_pnl": 0.0,
  "a_pnl": 0.0,
  "nas_pnl": 0.0,
  "signals_fired": 1,
  "signals_taken": 1,
  "skip_count": 0,
  "avg_slippage": 128.54,
  "dd_events": 0,
  "_provenance": {
    "generated_at": "2026-05-09T09:51:14+00:00",
    "fills_csv_path": "weekly_review_feeder/tests/fixtures/w19_dxtrade_fills.csv",
    "fills_csv_sha256": "81935a9c427ae575fa7c82b7ad2163e42a7bf83749e4d217a175915fd574dc77",
    "backtest_csvs": {
      "G":    {"path": "weekly_review_feeder/tests/fixtures\\guardian_gold_v5_5.csv", "sha256": "14014bacccb4338924ddfbfede707e49af1cc6fbfbeaca6771a744f3dff8160e"},
      "DJ30": {"path": "weekly_review_feeder/tests/fixtures\\striker_dj30_v4_5.csv",   "sha256": "1680f93df850bf31ea6cd59fe3a128bd745ea1756128d8bda4371ce0b0318af1"},
      "A":    {"path": "weekly_review_feeder/tests/fixtures\\aegis_v4_3.csv",           "sha256": "1680f93df850bf31ea6cd59fe3a128bd745ea1756128d8bda4371ce0b0318af1"},
      "NAS":  {"path": "weekly_review_feeder/tests/fixtures\\striker_nas100_v1.csv",    "sha256": "1680f93df850bf31ea6cd59fe3a128bd745ea1756128d8bda4371ce0b0318af1"}
    },
    "ptl_query_timestamp": "skipped",
    "mc_invocation": "portfolio_mc.py",
    "dd_log_snapshot_at": "skipped",
    "op_test_trades": [
      {
        "symbol": "XAUUSD.XX",
        "date": "2026-05-06",
        "first_timestamp": "2026-05-06T15:17:00",
        "order_ids": ["73433943", "73515958"],
        "n_opens": 1,
        "n_closes": 1,
        "net_pnl": 837.4,
        "reason": "non-session day + no PTL link"
      }
    ],
    "warnings": [
      "PTL query skipped (--skip-notion)",
      "No PTL entries for week; signals_taken inferred from fills.",
      "DD log skipped (--skip-dd); dd_events set to 0"
    ]
  }
}
```

Audit checks against §3.2 expectations:

| Check                                          | Expected                          | Actual                              | Pass |
|------------------------------------------------|-----------------------------------|-------------------------------------|------|
| `mc_p10/p50/p90` are non-zero floats           | yes                               | -2095.09 / 40.84 / 11980.21         | ✓    |
| `_provenance.mc_invocation` not `STUB-not-wired` | yes                             | `"portfolio_mc.py"`                 | ✓    |
| `dd_events` is real int                        | yes (0 expected, dd skipped)      | 0 (via `--skip-dd`)                 | partial — dd intentionally skipped per §8 |
| `_provenance.dd_log_snapshot_at` not `STUB-not-wired` | yes                        | `"skipped"`                         | partial — dd intentionally skipped per §8 |
| `_provenance.warnings` has no `STUB:` strings  | yes                               | no `STUB:` strings present          | ✓    |

The dd-side partial-pass is the intended audit signal of §8 escalation, not a silent breakage.

### §3.3 mc_wrapper unit test

```
$ cd weekly_review_feeder && python -m tests.test_mc_wrapper
=== MC WRAPPER BAND ===
p10:    -2,095.09
p50:        40.84
p90:    11,980.21

=== ALL CHECKS PASSED ===
```

### §3.4 Performance

Live smoke completed in <5s on Windows / Python 3.14. Well under the 30s budget.

### §3.5 Fail-fast

Verified by temporarily renaming `data/tv_exports/pepperstone/Striker_NAS100_v1_PEPPERSTONE_NAS100_2026-05-05_7ca6f.csv`. Live smoke raised `FileNotFoundError` with the full missing-path. CSV restored after verification.

The dd-side fail-fast verification is **not applicable** — the wrapper raises `NotImplementedError` unconditionally per §8, so there is no missing-input failure mode to verify.

## Files modified

Wiring commit (`feat(feeder): wire mc_wrapper to portfolio_mc; escalate dd_wrapper per §8`):

- `weekly_review_feeder/weekly_review_feeder/mc_wrapper.py` — wired (composed Pattern A).
- `weekly_review_feeder/weekly_review_feeder/dd_wrapper.py` — docstring update + NotImplementedError message points to this file's §8 block. Function bodies unchanged in behavior.
- `weekly_review_feeder/tests/test_mc_wrapper.py` — new file.
- `weekly_review_feeder/tests/fixtures/README.md` — new file.
- `weekly_review_feeder/WIRING_NOTES.md` — this file.

**Not modified** (per §4 forbidden moves):
- `portfolio_mc.py`
- `dd_protection.py`
- `__main__.py`, `config.py`, `fills_parser.py`, `backtest_parser.py`, `compute.py`, `notion_writer.py`, `provenance.py`, `ptl_client.py`
- Notion DB schema
