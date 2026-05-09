"""CLI entry: python -m weekly_review_feeder --week 2026-W19 --mode json."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

from . import __version__
from .backtest_parser import all_strategies_backtest
from .compute import (
    avg_slippage,
    compute_edge_captured,
    compute_mc_placement,
    reconcile_fills_to_backtest,
)
from .config import (
    INTERNAL_STRATEGY_KEYS,
    Paths,
    date_to_iso_week,
    iso_week_to_range,
    trading_days_in_range,
)
from .fills_parser import (
    detect_op_test_order_ids,
    filter_to_week as filter_fills_to_week,
    op_test_summary,
    parse_dxtrade_csv,
    per_strategy_pnl,
    realized_pnl_total,
)
from .provenance import assemble_provenance, log_feeder_run, now_utc_iso
from .ptl_client import (
    get_token,
    query_ptl_for_week,
    signals_skipped,
    signals_taken,
)


def _resolve_week(args: argparse.Namespace) -> tuple[str, date, date]:
    """Resolve week label + date range from CLI args."""
    if args.week:
        start, end = iso_week_to_range(args.week)
        return args.week, start, end
    if args.week_start and args.week_end:
        start = date.fromisoformat(args.week_start)
        end = date.fromisoformat(args.week_end)
        return date_to_iso_week(start), start, end
    raise SystemExit("Provide --week YYYY-Www OR both --week-start and --week-end.")


def run_feeder(
    week_label: str,
    week_start: date,
    week_end: date,
    paths: Paths,
    *,
    skip_notion: bool = False,
    skip_mc: bool = False,
    skip_dd: bool = False,
    fills_csv_override: str | None = None,
) -> dict[str, Any]:
    """Run the full feeder pipeline. Returns the JSON payload (dict)."""
    warnings: list[str] = []

    # ---- 1. Fills CSV ----
    fills_csv_path = fills_csv_override or _default_fills_path(paths, week_start, week_end)
    fills_df = parse_dxtrade_csv(fills_csv_path)
    fills_df = filter_fills_to_week(fills_df, week_start, week_end)

    # ---- 2. Pre-Trade Log entries ----
    if skip_notion:
        ptl_entries: list[dict[str, Any]] = []
        ptl_query_ts = "skipped"
        warnings.append("PTL query skipped (--skip-notion)")
    else:
        token = get_token()
        ptl_entries = query_ptl_for_week(token, week_start, week_end)
        ptl_query_ts = now_utc_iso()

    # ---- 3. Op-test detection (heuristic, pre-INT-1) ----
    op_test_ids = detect_op_test_order_ids(fills_df, ptl_entries)
    op_tests = op_test_summary(fills_df, op_test_ids)

    # ---- 4. Per-strategy P&L (excluding op-tests) ----
    strat_pnl = per_strategy_pnl(fills_df, exclude_op_tests=True, op_test_order_ids=op_test_ids)
    total_realized = realized_pnl_total(fills_df, op_test_order_ids=op_test_ids)

    # ---- 5. Backtest-equiv per strategy ----
    backtest_per_strat = all_strategies_backtest(paths, week_start, week_end)
    backtest_total = sum(info["pnl"] for info in backtest_per_strat.values())
    signals_fired_count = sum(info["signals_fired"] for info in backtest_per_strat.values())
    for k, info in backtest_per_strat.items():
        if "_warning" in info:
            warnings.append(f"{k}: {info['_warning']}")

    # ---- 6. PTL-based counts ----
    taken_count = signals_taken(ptl_entries)
    skipped_count = signals_skipped(ptl_entries)
    # If PTL is sparse for the week (e.g. log just started), fall back to backtest count
    # for signals_fired and live-fills count for signals_taken.
    if signals_fired_count == 0 and taken_count == 0:
        # No signals at all — week was inactive
        pass

    # signals_taken via fills: count distinct order_ids that have a Closing fill
    fills_taken_count = (
        fills_df[
            (fills_df["effect"].str.lower() == "closing")
            & (~fills_df["order_id"].isin(op_test_ids))
        ]["order_id"].nunique()
    )
    # If PTL is the source of truth (entries exist), use PTL count; else fall back.
    if ptl_entries:
        taken_final = taken_count
    else:
        taken_final = int(fills_taken_count)
        warnings.append("No PTL entries for week; signals_taken inferred from fills.")

    skip_count_final = max(0, signals_fired_count - taken_final)

    # ---- 7. MC band ----
    if skip_mc:
        mc = {"p10": 0.0, "p50": 0.0, "p90": 0.0}
        mc_invocation = "skipped"
        warnings.append("MC band skipped (--skip-mc); P10/50/90 set to 0.0")
    else:
        from .mc_wrapper import get_mc_band_for_week
        try:
            mc = get_mc_band_for_week(week_start, week_end)
            mc_invocation = "portfolio_mc.py"
        except NotImplementedError as e:
            warnings.append(f"MC wrapper STUB: {e}")
            mc = {"p10": 0.0, "p50": 0.0, "p90": 0.0}
            mc_invocation = "STUB-not-wired"

    # ---- 8. DD events ----
    if skip_dd:
        dd_events = 0
        dd_snapshot = "skipped"
        warnings.append("DD log skipped (--skip-dd); dd_events set to 0")
    else:
        from .dd_wrapper import count_dd_events_for_week
        try:
            dd_events = count_dd_events_for_week(paths.dd_log_path, week_start, week_end)
            dd_snapshot = now_utc_iso()
        except NotImplementedError as e:
            warnings.append(f"DD wrapper STUB: {e}")
            dd_events = 0
            dd_snapshot = "STUB-not-wired"

    # ---- 9. Slippage ----
    pairs = reconcile_fills_to_backtest(fills_df, backtest_per_strat, op_test_order_ids=op_test_ids)
    slippage = avg_slippage(pairs)

    # ---- 10. Edge-captured ratio + MC placement ----
    edge_ratio = compute_edge_captured(total_realized, backtest_total)
    placement = compute_mc_placement(total_realized, mc["p10"], mc["p50"], mc["p90"])

    # ---- 11. Assemble payload ----
    payload: dict[str, Any] = {
        "week": week_label,
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "trading_days": trading_days_in_range(week_start, week_end),
        "realized_pnl": round(total_realized, 2),
        "backtest_equiv_pnl": round(backtest_total, 2),
        "edge_captured_ratio": edge_ratio,
        "mc_p10": round(mc["p10"], 2),
        "mc_p50": round(mc["p50"], 2),
        "mc_p90": round(mc["p90"], 2),
        "mc_placement": placement,
        "g_pnl": round(strat_pnl["G"], 2),
        "dj30_pnl": round(strat_pnl["DJ30"], 2),
        "a_pnl": round(strat_pnl["A"], 2),
        "nas_pnl": round(strat_pnl["NAS"], 2),
        "signals_fired": signals_fired_count,
        "signals_taken": taken_final,
        "skip_count": skip_count_final,
        "avg_slippage": slippage,
        "dd_events": dd_events,
    }
    payload["_provenance"] = assemble_provenance(
        fills_csv_path=fills_csv_path,
        backtest_csv_paths={k: paths.backtest_csv(k) for k in INTERNAL_STRATEGY_KEYS},
        ptl_query_timestamp=ptl_query_ts,
        mc_invocation=mc_invocation,
        dd_log_snapshot_at=dd_snapshot,
        op_test_trades=op_tests,
        warnings=warnings,
    )
    return payload


def _default_fills_path(paths: Paths, week_start: date, week_end: date) -> str:
    """Convention: data/fills/dxtrade_YYYY-MM-DD_to_YYYY-MM-DD.csv."""
    fname = f"dxtrade_{week_start.isoformat()}_to_{week_end.isoformat()}.csv"
    return str(Path(paths.fills_dir) / fname)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="weekly_review_feeder",
        description="Auto-fill the Notion Weekly Review numeric block.",
    )
    g = p.add_mutually_exclusive_group()
    g.add_argument("--week", help="ISO week label, e.g. 2026-W19")
    p.add_argument("--week-start", help="Override week start date (YYYY-MM-DD)")
    p.add_argument("--week-end", help="Override week end date (YYYY-MM-DD)")
    p.add_argument(
        "--mode", choices=["json", "notion"], default="json",
        help="json: print to stdout. notion: also create/update the Weekly Review row.",
    )
    p.add_argument("--fills-csv", help="Override fills CSV path")
    p.add_argument("--skip-notion", action="store_true", help="Skip PTL Notion query (offline mode)")
    p.add_argument("--skip-mc", action="store_true", help="Skip portfolio_mc.py invocation")
    p.add_argument("--skip-dd", action="store_true", help="Skip dd_protection.py log read")
    p.add_argument("--no-log", action="store_true", help="Don't persist run to data/feeder_runs")
    p.add_argument("--version", action="version", version=__version__)

    args = p.parse_args(argv)

    week_label, ws, we = _resolve_week(args)
    paths = Paths()

    payload = run_feeder(
        week_label, ws, we, paths,
        skip_notion=args.skip_notion,
        skip_mc=args.skip_mc,
        skip_dd=args.skip_dd,
        fills_csv_override=args.fills_csv,
    )

    # Persist for audit
    if not args.no_log:
        try:
            log_feeder_run(paths.feeder_runs_dir, payload)
        except Exception as e:
            payload["_provenance"]["warnings"].append(f"Run log failed: {e}")

    # Notion update
    if args.mode == "notion":
        from .notion_writer import create_or_update_weekly_review
        token = get_token()
        result = create_or_update_weekly_review(token, payload)
        payload["_notion_result"] = result

    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
