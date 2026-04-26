"""
Minimum Viable Defense (MVD) — assertion library.

See docs/adr/2026-04-24-mvd-discipline.md and docs/methodology/mvd.md.

Producer-side enforcement layer for artifacts that cross the live capital
boundary: MC input panels, lock decision inputs, risk-control production
code, allocation changes, and load-bearing claims in briefs / memory / ADRs.

Each helper is a one-liner at the call site. Failure raises AssertionError
with a clear message; success is silent. Stdlib only — no external deps.

Five families:
  1. Cardinality   — assert_min_rows, assert_window
  2. Identity      — assert_symbol, assert_broker, assert_version
  3. Contract      — assert_no_fallback, assert_guard_fired
  4. Cross-source  — assert_reconciled
  5. Code-vs-doc   — assert_file_contains
"""

from __future__ import annotations

import os
from datetime import datetime


# ----------------------------------------------------------------------
# Family 1 — Cardinality
# ----------------------------------------------------------------------

def assert_min_rows(actual: int, minimum: int, label: str = "") -> None:
    """Fail if row count is below the expected floor.

    Catches the OANDA fetch case (~10K rows where ~100K were expected,
    audit instance #2).
    """
    if actual < minimum:
        raise AssertionError(
            f"MVD cardinality fail [{label}]: "
            f"got {actual:,} rows, expected at least {minimum:,}"
        )


def assert_window(
    first_ts: datetime,
    last_ts: datetime,
    expected_min_days: int,
    label: str = "",
    tolerance_days: int = 30,
) -> None:
    """Fail if the time-window span is shorter than expected.

    Catches the '4yr Alchemy panel' actually 14mo case (audit instance #8).
    """
    span_days = (last_ts - first_ts).days
    if span_days < expected_min_days - tolerance_days:
        raise AssertionError(
            f"MVD window fail [{label}]: "
            f"span {span_days} days, expected at least {expected_min_days} days "
            f"(tolerance ±{tolerance_days})"
        )


# ----------------------------------------------------------------------
# Family 2 — Identity
# ----------------------------------------------------------------------

def assert_symbol(actual: str, expected: str) -> None:
    """Fail if symbol identifier does not match. Strict equality by design.

    'USDJPY' and 'USDJPY_X' are different feeds — never collapse them.
    Catches the Aegis USDJPY-vs-USDJPY_X mislabel case (audit instance #4).
    """
    if actual != expected:
        raise AssertionError(
            f"MVD identity fail (symbol): got '{actual}', expected '{expected}'"
        )


def assert_broker(actual: str, expected: str) -> None:
    """Fail if broker identifier does not match.

    Use to gate against Pepperstone-vs-Alchemy-vs-OANDA panel-source confusion.
    """
    if actual != expected:
        raise AssertionError(
            f"MVD identity fail (broker): got '{actual}', expected '{expected}'"
        )


def assert_version(actual: str, expected: str) -> None:
    """Fail if strategy version identifier does not match.

    Use at top of any calibration or lock script that is version-specific
    (Guardian v5.5, Striker v4.4, Aegis v4.3, etc.).
    """
    if actual != expected:
        raise AssertionError(
            f"MVD identity fail (version): got '{actual}', expected '{expected}'"
        )


def parse_tv_export_filename(filename: str) -> dict:
    """Parse the canonical OANDA TV-export CSV filename into identity fields.

    Pattern (7 underscore-delimited fields + .csv):
        <Strategy>_<Instrument>_<Version>_<Broker>_<Symbol>_<YYYY-MM-DD>_<hash>.csv

    Example:
        Guardian_Gold_v5.5_OANDA_XAUUSD_2026-04-25_9ae1f.csv
        -> strategy=Guardian, instrument=Gold, version=v5.5, broker=OANDA,
           symbol=XAUUSD, export_date=2026-04-25, hash_suffix=9ae1f

    Raises AssertionError on pattern mismatch (treated as identity failure).
    """
    base = filename[:-4] if filename.endswith(".csv") else filename
    parts = base.split("_")
    if len(parts) != 7:
        raise AssertionError(
            f"MVD identity fail (TV-export filename pattern): "
            f"got '{filename}', expected 7 underscore-delimited fields "
            f"(<Strategy>_<Instrument>_<Version>_<Broker>_<Symbol>_<YYYY-MM-DD>_<hash>.csv)"
        )
    strategy, instrument, version, broker, symbol, export_date, hash_suffix = parts
    return {
        "strategy": strategy,
        "instrument": instrument,
        "version": version,
        "broker": broker,
        "symbol": symbol,
        "export_date": export_date,
        "hash_suffix": hash_suffix,
        "filename": filename,
    }


def assert_tv_export(
    csv_path,
    *,
    expected_strategy: str,
    expected_version: str,
    expected_broker: str,
    expected_symbol: str,
) -> dict:
    """Assert a TV-export CSV's filename declares the expected identity.

    Catches the 'wrong CSV in load slot' class — e.g. a Striker CSV in
    Guardian's path, or a v5.4 export where v5.5 is locked. Returns the
    parsed metadata dict for further use by the caller.

    Use within ~5 lines of a TV-export CSV path declaration in any script
    that loads load-bearing OANDA panels (MC inputs, 1R diagnosis, lock
    decision inputs).
    """
    filename = os.path.basename(str(csv_path))
    meta = parse_tv_export_filename(filename)
    fields = (
        ("strategy", expected_strategy),
        ("version",  expected_version),
        ("broker",   expected_broker),
        ("symbol",   expected_symbol),
    )
    for field, expected in fields:
        actual = meta[field]
        if actual != expected:
            raise AssertionError(
                f"MVD identity fail (TV-export {field}): "
                f"got '{actual}', expected '{expected}' in {filename}"
            )
    return meta


# ----------------------------------------------------------------------
# Family 3 — Contract
# ----------------------------------------------------------------------

def assert_no_fallback(fallback_count: int, label: str = "") -> None:
    """Fail if a 'should never fire' fallback path was taken.

    Catches the portfolio_mc 1R median-fallback silent-trigger case
    (audit instance #1).
    """
    if fallback_count != 0:
        raise AssertionError(
            f"MVD contract fail [{label}]: "
            f"fallback path triggered {fallback_count} times (expected 0)"
        )


def assert_guard_fired(event_count: int, label: str = "") -> None:
    """Fail if a guard / stop / cap that should fire never did across the panel.

    Catches the Striker dayStopPct -3% inert case (audit instance #6).
    If the guard is intentionally inactive in the panel, document that
    explicitly rather than silencing this assertion.
    """
    if event_count <= 0:
        raise AssertionError(
            f"MVD contract fail [{label}]: "
            f"guard never fired in panel (event_count={event_count}); "
            f"if intentionally inactive, document it explicitly"
        )


# ----------------------------------------------------------------------
# Family 4 — Cross-source
# ----------------------------------------------------------------------

def assert_reconciled(
    actual: float,
    expected: float,
    tol_pct: float,
    label: str = "",
) -> None:
    """Fail if a value disagrees with an independent source by more than tol_pct.

    tol_pct is a fraction (0.05 = 5%). Use for TV-vs-Python P&L,
    Pepperstone-vs-OANDA bar count, etc. Catches the TV <30-day JPY
    P&L distortion case (audit instance #9).
    """
    if expected == 0:
        gap = abs(actual)
    else:
        gap = abs(actual - expected) / abs(expected)
    if gap > tol_pct:
        raise AssertionError(
            f"MVD reconcile fail [{label}]: "
            f"actual={actual:.4f} vs expected={expected:.4f}, "
            f"gap={gap*100:.2f}% > tol={tol_pct*100:.2f}%"
        )


# ----------------------------------------------------------------------
# Family 5 — Code-vs-doc
# ----------------------------------------------------------------------

def assert_file_contains(path: str, expected_text: str, label: str = "") -> None:
    """Fail if a file does not contain a literal text fragment.

    Use to anchor a doc claim to a specific production line:
        assert_file_contains('strategies/aegis_v4_3.pine',
                             'dayofmonth >= 29',
                             label='Aegis EOM rule')
    Catches the Aegis EOM 'last 3 trading days' prose-vs-Pine drift
    (audit instance #7).
    """
    if not os.path.exists(path):
        raise AssertionError(
            f"MVD code-vs-doc fail [{label}]: file not found: {path}"
        )
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if expected_text not in content:
        raise AssertionError(
            f"MVD code-vs-doc fail [{label}]: "
            f"'{expected_text}' not found in {path}"
        )
