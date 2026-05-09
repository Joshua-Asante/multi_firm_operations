"""W19 acceptance test — runs the feeder end-to-end on fixture data.

Run with:
    cd /home/claude/weekly_review_feeder
    python -m tests.test_w19
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

# Make package importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from weekly_review_feeder.config import Paths
from weekly_review_feeder.__main__ import run_feeder


FIXTURES = Path(__file__).parent / "fixtures"


def _make_paths() -> Paths:
    """Build a Paths instance pointing at the fixtures directory."""
    # Use a temp dir for runs/fills so we don't pollute fixtures
    tmpdir = tempfile.mkdtemp(prefix="wrf_test_")
    return Paths(
        fills_dir=str(FIXTURES),
        backtest_dir=str(FIXTURES),
        dd_log_path=os.path.join(tmpdir, "dd.log"),
        feeder_runs_dir=os.path.join(tmpdir, "runs"),
    )


def test_w19_acceptance():
    paths = _make_paths()
    fills_path = str(FIXTURES / "w19_dxtrade_fills.csv")

    payload = run_feeder(
        "2026-W19",
        date(2026, 5, 4),
        date(2026, 5, 8),
        paths,
        skip_notion=True,  # PTL had only Friday's pre-window-watch entry
        skip_mc=True,
        skip_dd=True,
        fills_csv_override=fills_path,
    )

    expected = json.loads((FIXTURES / "w19_expected.json").read_text())

    failures = []

    # Exact-match fields
    for key in [
        "week", "week_start", "week_end", "trading_days",
        "g_pnl", "dj30_pnl", "a_pnl", "nas_pnl",
        "signals_fired", "signals_taken", "skip_count", "dd_events",
        "edge_captured_ratio", "mc_placement",
    ]:
        if payload.get(key) != expected.get(key):
            failures.append(f"  {key}: got {payload.get(key)!r}, expected {expected.get(key)!r}")

    # Tolerance fields
    for key, tol in [
        ("realized_pnl", 0.50),
        ("backtest_equiv_pnl", 0.50),
    ]:
        diff = abs(payload[key] - expected[key])
        if diff > tol:
            failures.append(f"  {key}: got {payload[key]!r}, expected {expected[key]!r} (diff {diff:.2f} > tol {tol})")

    # Slippage range
    slip = payload["avg_slippage"]
    if not (expected["avg_slippage_min"] <= slip <= expected["avg_slippage_max"]):
        failures.append(
            f"  avg_slippage: got {slip!r}, "
            f"expected in [{expected['avg_slippage_min']}, {expected['avg_slippage_max']}]"
        )

    # Op-test detection
    op_count = len(payload["_provenance"]["op_test_trades"])
    if op_count != expected["_op_test_count_expected"]:
        failures.append(
            f"  op_test_count: got {op_count}, expected {expected['_op_test_count_expected']}"
        )

    # Output
    print("=== W19 PAYLOAD ===")
    print(json.dumps(payload, indent=2, default=str))
    print()
    if failures:
        print("=== FAILURES ===")
        for f in failures:
            print(f)
        return False
    print("=== ALL CHECKS PASSED ===")
    return True


if __name__ == "__main__":
    ok = test_w19_acceptance()
    sys.exit(0 if ok else 1)
