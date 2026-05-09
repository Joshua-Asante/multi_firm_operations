# Weekly Review Feeder

Auto-fill the Notion Weekly Review numeric block from existing data sources.
Cuts W20+ review time from ~45min to ~10min.

Implements the spec at `docs/specs/weekly_review_feeder.md` (v0.1).

## What it does

Reads:
1. DXTrade fills CSV for the week
2. Pre-Trade Log entries from Notion (filtered to week)
3. Per-strategy Pepperstone backtest CSVs (TradingView "List of trades" exports)
4. portfolio_mc.py output (via wrapper — needs wiring on your machine)
5. dd_protection.py log (via wrapper — needs wiring on your machine)

Computes the 17 numeric fields of the Weekly Review DB:
realized P&L, backtest-equiv P&L, edge-captured ratio, MC P10/50/90, MC placement,
per-strategy P&L (G/DJ30/A/NAS), signals fired/taken/skipped, avg slippage, dd events,
trading days, week start/end.

Outputs:
- JSON to stdout (paste into Notion), or
- Direct create/update of the Weekly Review row via Notion API.

Always logs a provenance block (input file SHA256s, query timestamps, op-test detections).

## Install

```bash
cd weekly_review_feeder
pip install -r requirements.txt
# Optional editable install:
pip install -e .
```

Python 3.10+ required.

## Configure

Set environment variables (or use `.env` with python-dotenv):

```bash
# Required for --mode notion or default Pre-Trade Log query
export NOTION_API_TOKEN="secret_..."

# Optional: override defaults
export WRF_FILLS_DIR="data/fills"
export WRF_BACKTEST_DIR="data/tv_exports/pepperstone"
export WRF_DD_LOG="data/dd_protection.log"
export WRF_RUNS_DIR="data/feeder_runs"
export NOTION_PTL_DB_ID="e375125c-8c60-42ec-80ce-6dcb33122831"
export NOTION_WEEKLY_REVIEW_DB_ID="903516488cde49099a159822c5916eee"
```

To get a Notion API token: https://www.notion.so/my-integrations → Create integration →
copy the secret. Then share the CTA Track-Record Habits page with the integration so
it can read PTL and create/update Weekly Review rows.

## Wire the local-script wrappers

Two modules are intentional STUBs — they need wiring to your local scripts:

### `mc_wrapper.py`

Replace `get_mc_band_for_week(...)` with either a subprocess call to your
`portfolio_mc.py` or a direct import. Required output:
`{"p10": float, "p50": float, "p90": float}`.

Two suggested patterns are documented in the module docstring. Pick whichever
matches your `portfolio_mc.py` CLI surface.

### `dd_wrapper.py`

Replace `count_dd_events_for_week(...)` to read your dd_protection log.
A "trigger event" is any tier change OR risk-multiplier change OR FIRE-alert
within the date range.

Until wired, run with `--skip-mc --skip-dd` to test without these:

```bash
python -m weekly_review_feeder --week 2026-W19 --skip-mc --skip-dd --mode json
```

## Usage

### Print JSON for the current week

```bash
python -m weekly_review_feeder --week 2026-W20 --mode json
```

### Auto-update Notion Weekly Review row

```bash
python -m weekly_review_feeder --week 2026-W20 --mode notion
```

Creates the row if absent; updates numeric fields if present.

### Override fills CSV path

```bash
python -m weekly_review_feeder \
  --week 2026-W20 \
  --fills-csv data/fills/dxtrade_2026-05-11_to_2026-05-15.csv \
  --mode json
```

### Custom date range

```bash
python -m weekly_review_feeder \
  --week-start 2026-05-04 --week-end 2026-05-08 \
  --mode json
```

### Skip stub wrappers (offline testing)

```bash
python -m weekly_review_feeder --week 2026-W19 \
  --skip-notion --skip-mc --skip-dd --mode json
```

## Acceptance test

W19 is the canonical regression fixture. To verify the feeder reproduces the
hand-computed W19 review:

```bash
python -m tests.test_w19
```

Should print `=== ALL CHECKS PASSED ===` and exit 0.

Expected W19 metrics:
- realized_pnl: −878.40 (Wed copier excluded as op-test, +$837.40 logged separately)
- backtest_equiv_pnl: −675.68
- edge_captured_ratio: null (loss-week, INT-2 convention)
- g_pnl: −878.40, others: 0.0
- signals_fired/taken/skipped: 1/1/0
- avg_slippage: 128.54
- 1 op-test round-trip detected

## Conventions encoded

These are baked in per the surfacing findings of the W19 dry run:

1. **INT-1 (PTL signal-type partition) — heuristic v0.1:** op-test detection uses
   "non-session day + no PTL Linked DXTrade ID match" as a conservative rule.
   When INT-1 lands a `signal_type` field on Pre-Trade Log, swap the heuristic
   for a direct field check.

2. **INT-2 (loss-week ratio sign-flip):** edge-captured ratio is set to `null`
   when backtest-equiv P&L is negative. Avg Slippage in dollars carries the
   leakage signal on loss-weeks.

3. **Trading week = Mon-Fri.** ISO week conversion picks Monday as start.

4. **DXTrade timestamp parsing:** tries `DD/MM/YY HH:MM` first, then `DD/MM/YYYY HH:MM`,
   then ISO. Verify against your actual export.

## Files

```
weekly_review_feeder/
├── __main__.py        # CLI entry, orchestration
├── config.py          # symbol→strategy mapping, IDs, week-range helpers
├── fills_parser.py    # DXTrade CSV → per-strategy P&L + op-test heuristic
├── backtest_parser.py # Pepperstone CSV → per-trade summary
├── ptl_client.py      # Notion Pre-Trade Log query
├── mc_wrapper.py      # STUB — wire to portfolio_mc.py
├── dd_wrapper.py      # STUB — wire to dd_protection.py
├── compute.py         # edge-captured, slippage, MC placement
├── notion_writer.py   # Weekly Review row create/update
└── provenance.py      # SHA256, audit trail
tests/
├── test_w19.py        # acceptance test
└── fixtures/          # W19 reference data
```

## Forbidden moves (per spec §6)

Encoded in code comments and code structure:
- No modification of `portfolio_mc.py` or `dd_protection.py` — wrap, don't edit.
- No bypass of op-test exclusion — even pre-INT-1, the heuristic is in place.
- No silent fallback on missing inputs — fail fast with explicit error.
- Single source of truth for SYMBOL_STRATEGY_MAP (config.py).
- No Notion mutation without `--mode notion` flag.

## Out of scope (v0.1)

Per spec §7. Candidates for v0.2+:
- Slippage decomposition (entry+exit; sizing variance vs pure slippage)
- BOJ/FOMC/NFP automatic calendar check
- Op-Risk Register delta detection
- Behavioral state aggregation
- Skip-pattern detection
