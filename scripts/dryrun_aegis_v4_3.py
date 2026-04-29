"""
MVD helper dry-run: Aegis v4.3 on Pepperstone 52mo canonical panel.

Purpose: exercise all 9 helpers in lib/mvd.py against a known reference and
verify they reproduce the canonical performance numbers documented in
strategies/aegis/aegis_CHANGELOG.md and the Notion MVD page.

This is the sanity gate before any retrofit code lands in portfolio_mc.py,
dd_protection.py, or calibration scripts. If this dry-run passes, the
helpers' signatures and logic are validated end-to-end on real data.

Usage:
    AEGIS_CSV=/path/to/Aegis_USDJPY_v4.3_PEPPERSTONE_USDJPY_*.csv \\
        python scripts/dryrun_aegis_v4_3.py

If AEGIS_CSV is unset, the harness looks at data/tv_exports/aegis.csv
(repo-relative). The CSV is gitignored — fixture lives outside the tree.

Canonical reference (Pepperstone 52mo, 123t, locked 2026-04-23):
    Net P&L     : $178,208.42      (cumulative on trade #123)
    Profit Factor: 4.186
    Trade count : 123
    Max DD intra: 5.01%             (peak-to-MFE-trough, $10,017 / $200K)
    Max DD close: 3.76%             (peak-to-trough on closed-trade equity,
                                      labeled 'trade-close' in CHANGELOG)

Note on the DD reconciliation: '5.01%' (cited in MVD docs) and '3.76%'
(in aegis_CHANGELOG.md) are two valid measurements of different things.
The harness asserts both and labels each explicitly — the labeling
ambiguity itself is an Identity-class MVD case (audit instance candidate
#11: 'DD' treated as if verified to refer to its claimed measurement).
"""

from __future__ import annotations

import csv
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Allow running as `python scripts/dryrun_aegis_v4_3.py` from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.mvd import (
    assert_min_rows,
    assert_window,
    assert_symbol,
    assert_broker,
    assert_version,
    assert_no_fallback,
    assert_guard_fired,
    assert_reconciled,
    assert_file_contains,
)


# ----------------------------------------------------------------------
# Canonical reference values (Pepperstone 52mo, v4.3 lock 2026-04-23)
# ----------------------------------------------------------------------

EXPECTED_SYMBOL = "USDJPY"
EXPECTED_BROKER = "Pepperstone"
EXPECTED_VERSION = "v4.3"
EXPECTED_MIN_ROWS = 240          # 123 trades x 2 (entry+exit) = 246
EXPECTED_MIN_DAYS = 4 * 365      # 52mo panel
EXPECTED_TRADE_COUNT = 123
EXPECTED_NET_USD = 178_208.42
EXPECTED_PF = 4.186
EXPECTED_DD_INTRA_PCT = 5.01     # cited canonical, intra-trade
EXPECTED_DD_CLOSE_PCT = 3.76     # CHANGELOG, trade-close
START_EQUITY = 200_000.0         # $200K challenge baseline

# Filename convention from Pepperstone TV export:
# Aegis_USDJPY_v4.3_PEPPERSTONE_USDJPY_YYYY-MM-DD_HASH.csv
FILENAME_RE = re.compile(
    r"^Aegis_(?P<sym1>[A-Z_]+)_v(?P<ver>\d+\.\d+)_"
    r"(?P<broker>[A-Z]+)_(?P<sym2>[A-Z_]+)_\d{4}-\d{2}-\d{2}_[a-f0-9]+\.csv$"
)


# ----------------------------------------------------------------------
# Path resolution
# ----------------------------------------------------------------------

def resolve_csv_path() -> Path:
    env = os.environ.get("AEGIS_CSV")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "data" / "tv_exports" / "aegis.csv"


def resolve_pine_path() -> Path:
    env = os.environ.get("AEGIS_PINE")
    if env:
        return Path(env)
    return (
        Path(__file__).resolve().parent.parent
        / "strategies" / "aegis" / "aegis_usdjpy_v4.3.pine"
    )


# ----------------------------------------------------------------------
# CSV ingest + metric compute
# ----------------------------------------------------------------------

def parse_filename_identity(csv_path: Path) -> tuple[str, str, str]:
    """Return (symbol, broker, version) parsed from canonical filename."""
    m = FILENAME_RE.match(csv_path.name)
    if not m:
        # Fall back to env-var overrides for the standardized aegis.csv path
        sym = os.environ.get("AEGIS_SYMBOL", "")
        brk = os.environ.get("AEGIS_BROKER", "")
        ver = os.environ.get("AEGIS_VERSION", "")
        if not (sym and brk and ver):
            raise ValueError(
                f"Cannot parse identity from filename '{csv_path.name}' and "
                f"AEGIS_SYMBOL / AEGIS_BROKER / AEGIS_VERSION env vars unset. "
                f"Either rename to canonical Pepperstone export form or set vars."
            )
        return sym, brk, ver
    # Pepperstone exports BROKER as uppercase; normalize to title case for assert
    return m["sym1"], m["broker"].title(), f"v{m['ver']}"


def load_trades(csv_path: Path) -> tuple[int, list[dict]]:
    """Return (raw_row_count, exit_only_trades). Raw count is for cardinality."""
    raw_count = 0
    trades: list[dict] = []
    with csv_path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_count += 1
            if not row["Type"].startswith("Exit"):
                continue
            trades.append({
                "n": int(row["Trade #"]),
                "ts": datetime.strptime(row["Date and time"], "%Y-%m-%d %H:%M"),
                "pnl": float(row["Net P&L USD"]),
                "cum_pnl": float(row["Cumulative P&L USD"]),
                "adv_usd": float(row["Adverse excursion USD"]),
            })
    return raw_count, trades


def compute_metrics(trades: list[dict]) -> dict:
    fallback_count = 0  # by construction this compute path takes no fallback
    gross_win = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    gross_loss = sum(t["pnl"] for t in trades if t["pnl"] < 0)
    if gross_loss == 0:
        # Would be the silent-fallback class — flag rather than divide by zero
        fallback_count += 1
        pf = float("inf")
    else:
        pf = gross_win / abs(gross_loss)

    losing = sum(1 for t in trades if t["pnl"] < 0)

    # Trade-close DD on cum P&L $
    peak_close = trades[0]["cum_pnl"]
    max_dd_close = 0.0
    for t in trades:
        peak_close = max(peak_close, t["cum_pnl"])
        max_dd_close = max(max_dd_close, peak_close - t["cum_pnl"])

    # Intra-trade DD: equity floor during a trade = cum_at_entry + adverse_excursion
    peak_intra = 0.0
    max_dd_intra = 0.0
    for t in trades:
        cum_before = t["cum_pnl"] - t["pnl"]
        intra_trough = cum_before + t["adv_usd"]
        peak_intra = max(peak_intra, cum_before)
        max_dd_intra = max(max_dd_intra, peak_intra - intra_trough)
        peak_intra = max(peak_intra, t["cum_pnl"])

    return {
        "trade_count": len(trades),
        "net_usd": trades[-1]["cum_pnl"],
        "pf": pf,
        "win_rate": sum(1 for t in trades if t["pnl"] > 0) / len(trades),
        "losing_count": losing,
        "fallback_count": fallback_count,
        "max_dd_close_pct": max_dd_close / START_EQUITY * 100,
        "max_dd_intra_pct": max_dd_intra / START_EQUITY * 100,
        "first_ts": trades[0]["ts"],
        "last_ts": trades[-1]["ts"],
    }


# ----------------------------------------------------------------------
# Main dry-run
# ----------------------------------------------------------------------

def main() -> int:
    csv_path = resolve_csv_path()
    pine_path = resolve_pine_path()

    if not csv_path.exists():
        print(f"FAIL: CSV not found at {csv_path}", file=sys.stderr)
        print("Set AEGIS_CSV to point at the Pepperstone v4.3 export.", file=sys.stderr)
        return 2

    print(f"Aegis v4.3 dry-run — {csv_path.name}")
    print(f"  CSV  : {csv_path}")
    print(f"  Pine : {pine_path}")
    print()

    # --- Family 2: Identity (parsed from filename) ---
    sym, broker, version = parse_filename_identity(csv_path)
    assert_symbol(sym, EXPECTED_SYMBOL)
    assert_broker(broker, EXPECTED_BROKER)
    assert_version(version, EXPECTED_VERSION)
    print(f"  [Identity ] symbol={sym} broker={broker} version={version} OK")

    # --- Family 1: Cardinality ---
    raw_count, trades = load_trades(csv_path)
    assert_min_rows(raw_count, EXPECTED_MIN_ROWS, label="Aegis Pepperstone 52mo CSV")
    print(f"  [Cardinal ] raw rows={raw_count} (>= {EXPECTED_MIN_ROWS}) OK")

    metrics = compute_metrics(trades)
    assert_window(
        metrics["first_ts"],
        metrics["last_ts"],
        expected_min_days=EXPECTED_MIN_DAYS,
        label="Aegis 52mo panel",
        tolerance_days=60,
    )
    span_days = (metrics["last_ts"] - metrics["first_ts"]).days
    print(
        f"  [Window   ] {metrics['first_ts'].date()} -> {metrics['last_ts'].date()} "
        f"({span_days} days, >= {EXPECTED_MIN_DAYS - 60}) OK"
    )

    # --- Family 3: Contract ---
    assert_no_fallback(metrics["fallback_count"], label="Aegis P&L compute")
    print(f"  [Contract ] no_fallback (count={metrics['fallback_count']}) OK")

    assert_guard_fired(metrics["losing_count"], label="Aegis SL realized in panel")
    print(
        f"  [Contract ] guard_fired losing_trades={metrics['losing_count']} "
        f"(SL fires confirmed) OK"
    )

    # --- Family 4: Cross-source (canonical reconciliation) ---
    assert_reconciled(
        metrics["trade_count"], EXPECTED_TRADE_COUNT, tol_pct=0.0,
        label="Aegis trade count vs canonical",
    )
    assert_reconciled(
        metrics["net_usd"], EXPECTED_NET_USD, tol_pct=0.001,
        label="Aegis net USD vs canonical",
    )
    assert_reconciled(
        metrics["pf"], EXPECTED_PF, tol_pct=0.005,
        label="Aegis PF vs canonical",
    )
    assert_reconciled(
        metrics["max_dd_intra_pct"], EXPECTED_DD_INTRA_PCT, tol_pct=0.01,
        label="Aegis intra-trade DD% vs canonical (5.01%)",
    )
    assert_reconciled(
        metrics["max_dd_close_pct"], EXPECTED_DD_CLOSE_PCT, tol_pct=0.025,
        label="Aegis trade-close DD% vs CHANGELOG (3.76%)",
    )
    print(
        f"  [Reconcile] trades={metrics['trade_count']} net=${metrics['net_usd']:,.2f} "
        f"PF={metrics['pf']:.4f} WR={metrics['win_rate']*100:.2f}% "
        f"DD_intra={metrics['max_dd_intra_pct']:.2f}% "
        f"DD_close={metrics['max_dd_close_pct']:.2f}% OK"
    )

    # --- Family 5: Code-vs-doc ---
    assert_file_contains(
        str(pine_path), "dayofmonth >= 29",
        label="Aegis EOM rule literal in Pine source",
    )
    print(f"  [Code-vs-doc] '{pine_path.name}' contains 'dayofmonth >= 29' OK")

    print()
    print("All 9 MVD helpers exercised. Dry-run PASS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
