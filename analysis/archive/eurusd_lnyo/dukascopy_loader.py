"""Dukascopy EURUSD M15 bid+ask loader.

Per parent brief §5 guardrail #4 (DST handling): EURUSD is double-DST-sensitive
(US and EU shift on different dates in March/November). All timestamps are
IANA tz-aware UTC; ET conversion via zoneinfo.ZoneInfo("America/New_York").

User-confirmed acquisition: PyPI dukascopy-python (v4.0.1).

Output schema:
    timestamp_utc (tz-aware UTC, M15 bar start)
    bid_open, bid_high, bid_low, bid_close
    ask_open, ask_high, ask_low, ask_close
    mid_close = (bid_close + ask_close) / 2
    volume   = ask volume (Dukascopy reports per-side; ask used as proxy)

Persisted to data/bar_data/EURUSD_dukascopy_m15_bidask_2022-01-04_to_2026-04-20.csv
"""
from __future__ import annotations

import datetime as dt
from datetime import timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ET = ZoneInfo("America/New_York")
UTC = timezone.utc

REPO_ROOT = Path(__file__).parent.parent.parent
OUT_PATH = REPO_ROOT / "data" / "bar_data" / "EURUSD_dukascopy_m15_bidask_2022-01-04_to_2026-04-20.csv"

PANEL_START = dt.datetime(2022, 1, 4, 0, 0, tzinfo=UTC)
PANEL_END = dt.datetime(2026, 4, 21, 0, 0, tzinfo=UTC)

# DST transitions to spot-check (parent brief §5 #4: 2-4 contaminated weeks/year)
# US DST starts 2nd Sun Mar, ends 1st Sun Nov.
DST_TRANSITIONS = [
    dt.date(2022, 3, 13), dt.date(2022, 11, 6),
    dt.date(2023, 3, 12), dt.date(2023, 11, 5),
    dt.date(2024, 3, 10), dt.date(2024, 11, 3),
    dt.date(2025, 3, 9),  dt.date(2025, 11, 2),
    dt.date(2026, 3, 8),
]


def fetch_eurusd_m15_bidask(
    start: dt.datetime = PANEL_START,
    end: dt.datetime = PANEL_END,
    out_path: Path | None = None,
    chunk_days: int = 60,
) -> pd.DataFrame:
    """Fetch EURUSD M15 bid+ask from Dukascopy and persist.

    Chunks the download to keep memory bounded and survive transient errors.
    """
    import dukascopy_python as dk
    out_path = out_path or OUT_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)

    chunks = []
    cursor = start
    while cursor < end:
        chunk_end = min(cursor + dt.timedelta(days=chunk_days), end)
        print(f"  fetching {cursor.date()} -> {chunk_end.date()}")
        bid = dk.fetch("EUR/USD", dk.INTERVAL_MIN_15, dk.OFFER_SIDE_BID, cursor, chunk_end)
        ask = dk.fetch("EUR/USD", dk.INTERVAL_MIN_15, dk.OFFER_SIDE_ASK, cursor, chunk_end)
        if bid.empty or ask.empty:
            print(f"  WARN empty chunk {cursor.date()}-{chunk_end.date()}: bid={len(bid)} ask={len(ask)}")
            cursor = chunk_end
            continue
        bid = bid.rename(columns={c: f"bid_{c}" for c in ["open", "high", "low", "close"]})
        ask = ask.rename(columns={c: f"ask_{c}" for c in ["open", "high", "low", "close"]})
        # Drop the bid volume; keep ask volume as proxy
        bid = bid.drop(columns=[c for c in bid.columns if "volume" in c])
        merged = bid.join(ask, how="inner")
        merged["mid_close"] = (merged["bid_close"] + merged["ask_close"]) / 2
        chunks.append(merged)
        cursor = chunk_end

    if not chunks:
        raise RuntimeError("No Dukascopy data returned for any chunk")
    df = pd.concat(chunks).sort_index()
    # Drop duplicate timestamps from chunk overlap
    df = df[~df.index.duplicated(keep="first")]
    # Ensure tz-aware UTC
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    df.index.name = "timestamp_utc"

    df.to_csv(out_path)
    print(f"Wrote {len(df)} rows to {out_path}")
    return df


def load_eurusd_m15_bidask(path: Path | None = None) -> pd.DataFrame:
    """Load previously-fetched Dukascopy CSV. Returns tz-aware UTC indexed DF."""
    path = path or OUT_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"Dukascopy data not found at {path}. Run --fetch first."
        )
    df = pd.read_csv(path, parse_dates=["timestamp_utc"], index_col="timestamp_utc")
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    return df


def add_et_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add ET-local columns: et_date, et_hour, et_minute, et_dow.

    Assumes df.index is tz-aware UTC. ET conversion uses IANA zoneinfo so
    DST transitions are handled correctly per parent brief §5 #4.
    """
    if df.index.tz is None:
        raise ValueError("df.index must be tz-aware UTC")
    et_idx = df.index.tz_convert(ET)
    out = df.copy()
    out["et_date"] = et_idx.date
    out["et_hour"] = et_idx.hour
    out["et_minute"] = et_idx.minute
    out["et_dow"] = et_idx.dayofweek  # Mon=0..Sun=6
    return out


# --- Probe / DST sanity ------------------------------------------------------

def _probe():
    print("=== dukascopy_loader.py probe ===")
    if not OUT_PATH.exists():
        print(f"No data at {OUT_PATH}. Run --fetch first.")
        return
    df = load_eurusd_m15_bidask()
    print(f"Rows: {len(df):,}")
    print(f"Range UTC: {df.index.min()} -> {df.index.max()}")
    bid_le_ask = (df["bid_close"] <= df["ask_close"]).mean()
    print(f"Invariant (bid_close <= ask_close): {bid_le_ask:.4%}")
    print(f"Mean spread (close): {(df['ask_close'] - df['bid_close']).mean()*10000:.3f} pips")

    print()
    print("=== DST sanity: 09:00 ET bar UTC offsets at transitions ===")
    df_et = add_et_columns(df)
    # For each DST transition date, look at 09:00 ET bars on the day before and after
    for dst_date in DST_TRANSITIONS:
        for offset in [-1, +1]:
            target_date = dst_date + dt.timedelta(days=offset)
            mask = (df_et["et_date"] == target_date) & (df_et["et_hour"] == 9) & (df_et["et_minute"] == 0)
            sub = df[mask]
            if len(sub):
                utc_h = sub.index[0].hour
                print(f"  {target_date} (DST {dst_date}, offset {offset:+d}d): 09:00 ET = {utc_h:02d}:00 UTC")


if __name__ == "__main__":
    import sys
    if "--fetch" in sys.argv:
        fetch_eurusd_m15_bidask()
    else:
        _probe()
