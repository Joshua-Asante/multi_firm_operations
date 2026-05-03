"""DXY (US Dollar Index) daily-close loader via yfinance.

Used for parent Notice §5 #7 (DXY anti-correlation):
  GBPUSD has stronger USD-leg sensitivity than EURUSD overlap. |r|
  GBPUSD-LORB-trade-pnl vs DXY computed pooled and on Guardian-active-day
  intersection.

For H-LORB falsification we use DXY daily change as the macro-driver proxy:
the candidate is "DXY-coupled" if H-LORB daily P&L moves with -DXY (since
GBPUSD long is approximately equivalent to short-DXY exposure).

Symbol: DX-Y.NYB (ICE U.S. Dollar Index futures, daily). Ported unchanged
from the EURUSD predecessor; shared output path `data/external/dxy.csv`
(parent Notice §5 #13 + entry stub §5).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

OUT_PATH = Path(__file__).parent.parent.parent / "data" / "external" / "dxy.csv"


def fetch_dxy(start: str = "2022-01-01", end: str = "2026-04-21",
              out_path: Path | None = None) -> pd.DataFrame:
    """Fetch DX-Y.NYB daily close from yfinance, persist to CSV, return DataFrame."""
    import yfinance as yf
    ticker = yf.Ticker("DX-Y.NYB")
    hist = ticker.history(start=start, end=end, auto_adjust=False)
    if hist.empty:
        raise RuntimeError("yfinance returned empty for DX-Y.NYB")
    df = pd.DataFrame({"close": hist["Close"].values}, index=pd.to_datetime(hist.index.date))
    df.index.name = "date"
    df["dxy_chg"] = df["close"].pct_change().fillna(0.0)
    out_path = out_path or OUT_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path)
    return df


def load_dxy(path: Path | None = None) -> pd.DataFrame:
    """Load previously-fetched DXY CSV; raises if missing."""
    path = path or OUT_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"DXY data not found at {path}. Run: python -m analysis.gbpusd_lon.dxy_loader --fetch"
        )
    df = pd.read_csv(path, parse_dates=["date"]).set_index("date")
    return df


def _probe():
    print("=== dxy_loader.py (H-LORB) probe ===")
    if OUT_PATH.exists():
        df = load_dxy()
        print(f"Loaded existing DXY: {OUT_PATH}")
    else:
        print(f"Fetching fresh DXY -> {OUT_PATH}")
        df = fetch_dxy()
    print(f"Rows: {len(df)}")
    print(f"Range: {df.index.min().date()} -> {df.index.max().date()}")
    print(f"Mean close: {df['close'].mean():.2f}")
    print(f"Daily-change std: {df['dxy_chg'].std():.4%}")
    print(df.tail(5))


if __name__ == "__main__":
    import sys
    if "--fetch" in sys.argv:
        df = fetch_dxy()
        print(f"Wrote {len(df)} rows to {OUT_PATH}")
    else:
        _probe()
