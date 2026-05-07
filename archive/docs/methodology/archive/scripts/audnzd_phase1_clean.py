"""Phase 1.4 cleaning pass: produce the clean CSV per the brief's permitted-D-tests.

Permitted deletions (from brief):
  1. Weekend gap candles  -- N/A: OANDA does not emit candles during weekend closures
                              (the 234 'weekend gaps' detected by verify are
                              gaps BETWEEN bars, not bars to delete).
  2. complete=false bars  -- duplicated by next-bar complete=true.
  3. Bars with NaN OHLC   -- measurement artefact.
  4. Bars with volume=0   -- DO NOT auto-delete; surface for investigation.

For this dataset the verification step already confirmed:
  complete=false: 0   nan_ohlc: 0   zero_volume: 0
So the clean CSV is row-identical to the raw CSV. We still emit it as a
separate artifact per the brief, with its own SHA256.
"""
from __future__ import annotations

import csv
import hashlib
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW_CSV = REPO_ROOT / "data" / "audnzd_oanda_m15_2022-01-01_to_2026-04-26_raw.csv"
CLEAN_CSV = REPO_ROOT / "data" / "audnzd_oanda_m15_2022-01-01_to_2026-04-26_clean.csv"
CLEAN_HASH = REPO_ROOT / "data" / "audnzd_oanda_m15_2022-01-01_to_2026-04-26_clean.sha256"


def main() -> int:
    if not RAW_CSV.exists():
        print(f"FAIL: missing raw CSV at {RAW_CSV}")
        return 1

    in_rows = 0
    out_rows = 0
    deleted_complete_false = 0
    deleted_nan_ohlc = 0
    flagged_zero_volume = 0

    with RAW_CSV.open(newline="", encoding="utf-8") as fin, \
         CLEAN_CSV.open("w", newline="", encoding="utf-8") as fout:
        reader = csv.DictReader(fin)
        writer = csv.DictWriter(fout, fieldnames=reader.fieldnames)
        writer.writeheader()
        for r in reader:
            in_rows += 1

            # D-test 1: complete=false (permitted: duplication)
            if str(r.get("complete", "")).lower() != "true":
                deleted_complete_false += 1
                continue

            # D-test 2: NaN OHLC (permitted: measurement artefact)
            try:
                for k in ("open_bid","high_bid","low_bid","close_bid",
                          "open_ask","high_ask","low_ask","close_ask"):
                    float(r[k])
            except (TypeError, ValueError, KeyError):
                deleted_nan_ohlc += 1
                continue

            # Zero-volume: flag, do NOT delete
            try:
                if int(r.get("volume", "0")) == 0:
                    flagged_zero_volume += 1
            except (TypeError, ValueError):
                flagged_zero_volume += 1

            writer.writerow(r)
            out_rows += 1

    h = hashlib.sha256()
    with CLEAN_CSV.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    digest = h.hexdigest()
    CLEAN_HASH.write_text(f"{digest}  {CLEAN_CSV.name}\n")

    print(f"in_rows={in_rows}")
    print(f"deleted_complete_false={deleted_complete_false}  (permitted: duplication)")
    print(f"deleted_nan_ohlc={deleted_nan_ohlc}              (permitted: measurement artefact)")
    print(f"flagged_zero_volume={flagged_zero_volume}        (NOT deleted; surfaced)")
    print(f"out_rows={out_rows}")
    print(f"sha256={digest}")
    print(f"path={CLEAN_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
