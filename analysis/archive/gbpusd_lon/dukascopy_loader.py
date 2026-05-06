"""Dukascopy GBPUSD M15 bid+ask loader (port of analysis/archive/eurusd_lnyo/dukascopy_loader.py).

Per parent Notice §5 #4 (data + tz handling): IANA tz-aware UTC; ET conversion via
zoneinfo.ZoneInfo("America/New_York") for cross-strategy DOW masks; BST conversion
via zoneinfo.ZoneInfo("Europe/London") for the OR window 08:00-09:00 BST.

User-confirmed acquisition: PyPI dukascopy-python.

Output schema:
    timestamp_utc (tz-aware UTC, M15 bar start)
    bid_open, bid_high, bid_low, bid_close
    ask_open, ask_high, ask_low, ask_close
    mid_close = (bid_close + ask_close) / 2
    volume   = ask volume

Persisted to data/bar_data/GBPUSD_dukascopy_m15_bidask_2022-01-04_to_2026-04-20.csv
"""
from __future__ import annotations

import datetime as dt
from datetime import timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ET = ZoneInfo("America/New_York")
BST = ZoneInfo("Europe/London")
UTC = timezone.utc

REPO_ROOT = Path(__file__).parent.parent.parent
OUT_PATH = REPO_ROOT / "data" / "bar_data" / "GBPUSD_dukascopy_m15_bidask_2022-01-04_to_2026-04-20.csv"

PANEL_START = dt.datetime(2022, 1, 4, 0, 0, tzinfo=UTC)
PANEL_END = dt.datetime(2026, 4, 21, 0, 0, tzinfo=UTC)

# DST transitions to spot-check. Note: GBPUSD is double-DST-sensitive (UK BST and
# US ET shift on different dates in Mar/Oct/Nov). UK BST: last Sunday of March
# starts; last Sunday of October ends. US: 2nd Sun Mar starts; 1st Sun Nov ends.
DST_TRANSITIONS = [
    dt.date(2022, 3, 13), dt.date(2022, 3, 27), dt.date(2022, 10, 30), dt.date(2022, 11, 6),
    dt.date(2023, 3, 12), dt.date(2023, 3, 26), dt.date(2023, 10, 29), dt.date(2023, 11, 5),
    dt.date(2024, 3, 10), dt.date(2024, 3, 31), dt.date(2024, 10, 27), dt.date(2024, 11, 3),
    dt.date(2025, 3, 9),  dt.date(2025, 3, 30), dt.date(2025, 10, 26), dt.date(2025, 11, 2),
    dt.date(2026, 3, 8),  dt.date(2026, 3, 29),
]


def fetch_gbpusd_m15_bidask(
    start: dt.datetime = PANEL_START,
    end: dt.datetime = PANEL_END,
    out_path: Path | None = None,
    chunk_days: int = 60,
) -> pd.DataFrame:
    """Fetch GBPUSD M15 bid+ask from Dukascopy and persist."""
    import dukascopy_python as dk
    out_path = out_path or OUT_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)

    chunks = []
    cursor = start
    while cursor < end:
        chunk_end = min(cursor + dt.timedelta(days=chunk_days), end)
        print(f"  fetching {cursor.date()} -> {chunk_end.date()}")
        bid = dk.fetch("GBP/USD", dk.INTERVAL_MIN_15, dk.OFFER_SIDE_BID, cursor, chunk_end)
        ask = dk.fetch("GBP/USD", dk.INTERVAL_MIN_15, dk.OFFER_SIDE_ASK, cursor, chunk_end)
        if bid.empty or ask.empty:
            print(f"  WARN empty chunk {cursor.date()}-{chunk_end.date()}: bid={len(bid)} ask={len(ask)}")
            cursor = chunk_end
            continue
        bid = bid.rename(columns={c: f"bid_{c}" for c in ["open", "high", "low", "close"]})
        ask = ask.rename(columns={c: f"ask_{c}" for c in ["open", "high", "low", "close"]})
        bid = bid.drop(columns=[c for c in bid.columns if "volume" in c])
        merged = bid.join(ask, how="inner")
        merged["mid_close"] = (merged["bid_close"] + merged["ask_close"]) / 2
        chunks.append(merged)
        cursor = chunk_end

    if not chunks:
        raise RuntimeError("No Dukascopy data returned for any chunk")
    df = pd.concat(chunks).sort_index()
    df = df[~df.index.duplicated(keep="first")]
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    df.index.name = "timestamp_utc"

    df.to_csv(out_path)
    print(f"Wrote {len(df)} rows to {out_path}")
    return df


def load_gbpusd_m15_bidask(path: Path | None = None) -> pd.DataFrame:
    """Load previously-fetched Dukascopy CSV."""
    path = path or OUT_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"Dukascopy data not found at {path}. Run --fetch first."
        )
    df = pd.read_csv(path, parse_dates=["timestamp_utc"], index_col="timestamp_utc")
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    return df


def add_bst_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add BST-local columns: bst_date, bst_hour, bst_minute, bst_dow."""
    if df.index.tz is None:
        raise ValueError("df.index must be tz-aware UTC")
    bst_idx = df.index.tz_convert(BST)
    out = df.copy()
    out["bst_date"] = bst_idx.date
    out["bst_hour"] = bst_idx.hour
    out["bst_minute"] = bst_idx.minute
    out["bst_dow"] = bst_idx.dayofweek
    return out


def add_et_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add ET-local columns for cross-strategy correlation alignment."""
    if df.index.tz is None:
        raise ValueError("df.index must be tz-aware UTC")
    et_idx = df.index.tz_convert(ET)
    out = df.copy()
    out["et_date"] = et_idx.date
    out["et_hour"] = et_idx.hour
    out["et_minute"] = et_idx.minute
    out["et_dow"] = et_idx.dayofweek
    return out


def _probe():
    print("=== dukascopy_loader.py (GBPUSD) probe ===")
    if not OUT_PATH.exists():
        print(f"No data at {OUT_PATH}. Run --fetch first.")
        return
    df = load_gbpusd_m15_bidask()
    print(f"Rows: {len(df):,}")
    print(f"Range UTC: {df.index.min()} -> {df.index.max()}")
    bid_le_ask = (df["bid_close"] <= df["ask_close"]).mean()
    print(f"Invariant (bid_close <= ask_close): {bid_le_ask:.4%}")
    print(f"Mean spread (close): {(df['ask_close'] - df['bid_close']).mean()*10000:.3f} pips")

    print()
    print("=== DST sanity: 08:00 BST bar UTC offsets at transitions ===")
    df_bst = add_bst_columns(df)
    for dst_date in DST_TRANSITIONS:
        for offset in [-1, +1]:
            target_date = dst_date + dt.timedelta(days=offset)
            mask = (df_bst["bst_date"] == target_date) & (df_bst["bst_hour"] == 8) & (df_bst["bst_minute"] == 0)
            sub = df[mask]
            if len(sub):
                utc_h = sub.index[0].hour
                print(f"  {target_date} (DST {dst_date}, offset {offset:+d}d): 08:00 BST = {utc_h:02d}:00 UTC")


if __name__ == "__main__":
    import sys
    if "--fetch" in sys.argv:
        fetch_gbpusd_m15_bidask()
    else:
        _probe()
