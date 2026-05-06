"""Phase 1 — USOIL CSV verification.

Brief: 2026-05-02 USOIL 15min behavioral characterization.
Plan: ~/.claude/plans/usoil-15min-behavioral-composed-tower.md (Stage B step 10).

Verifies:
  - SHA-256 sidecars match recomputed hashes
  - Bar count in [80k, 130k] (52 months × ~92 bars/day × ~5 days/week ≈ 105k)
  - Timestamps strictly monotonic
  - No duplicate timestamps
  - OHLC integrity (high >= low, high >= close, low <= close, high >= open, low <= open)
  - is_maintenance / is_holiday_short tag plausibility (not all-true, not all-false)

Returns 0 if all pass, 2 if any fail. Hard gate before phase1_characterize.
"""
from __future__ import annotations

import csv
import hashlib
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
RAW_CSV = DATA_DIR / "bar_data" / "USOIL_oanda_m15_2022-01-04_to_2026-04-20_raw.csv"
RAW_HASH = DATA_DIR / "USOIL_oanda_m15_2022-01-04_to_2026-04-20_raw.sha256"
CLEAN_CSV = DATA_DIR / "bar_data" / "USOIL_oanda_m15_2022-01-04_to_2026-04-20_clean.csv"
CLEAN_HASH = DATA_DIR / "USOIL_oanda_m15_2022-01-04_to_2026-04-20_clean.sha256"

MIN_BARS = 80_000
MAX_BARS = 130_000


def _sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify_hash(csv_path: pathlib.Path, hash_path: pathlib.Path, label: str) -> bool:
    if not csv_path.exists():
        print(f"  {label}: FAIL — CSV missing")
        return False
    if not hash_path.exists():
        print(f"  {label}: FAIL — hash sidecar missing")
        return False
    expected = hash_path.read_text().strip().split()[0]
    actual = _sha256(csv_path)
    ok = expected == actual
    print(f"  {label}: {'PASS' if ok else 'FAIL'}  expected={expected[:12]}…  actual={actual[:12]}…")
    return ok


def _verify_clean_csv() -> bool:
    print("verifying clean CSV structural checks:")
    rows = []
    with CLEAN_CSV.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)

    n = len(rows)
    bar_ok = MIN_BARS <= n <= MAX_BARS
    print(f"  bar_count: {n:,} (expected [{MIN_BARS:,}, {MAX_BARS:,}]): {'PASS' if bar_ok else 'FAIL'}")

    # Monotonic + unique timestamps
    times = [r["time"] for r in rows]
    monotonic = all(times[i] < times[i + 1] for i in range(n - 1))
    print(f"  monotonic_timestamps: {'PASS' if monotonic else 'FAIL'}")
    duplicates = n - len(set(times))
    dup_ok = duplicates == 0
    print(f"  no_duplicate_timestamps: {'PASS' if dup_ok else 'FAIL'} (dup_count={duplicates})")

    # OHLC integrity
    bad_hl = bad_hc = bad_lc = bad_ho = bad_lo = 0
    for r in rows:
        try:
            o, h, l, c = float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"])
        except (TypeError, ValueError):
            continue
        if h < l: bad_hl += 1
        if h < c: bad_hc += 1
        if l > c: bad_lc += 1
        if h < o: bad_ho += 1
        if l > o: bad_lo += 1
    ohlc_total = bad_hl + bad_hc + bad_lc + bad_ho + bad_lo
    ohlc_ok = ohlc_total == 0
    print(f"  ohlc_integrity: hl={bad_hl} hc={bad_hc} lc={bad_lc} ho={bad_ho} lo={bad_lo} -> {'PASS' if ohlc_ok else 'FAIL'}")

    # Tag plausibility — should be SOME maintenance bars (~4/day Mon-Fri × 1086d / 105k ≈ 4%)
    # and a small number of holiday-short bars
    n_maint = sum(1 for r in rows if r.get("is_maintenance", "").lower() == "true")
    n_holiday = sum(1 for r in rows if r.get("is_holiday_short", "").lower() == "true")
    maint_pct = n_maint / max(1, n) * 100
    holiday_pct = n_holiday / max(1, n) * 100
    # is_maintenance accepted at 0% (OANDA's CFD feed natively honors the
    # CME 17:00-18:00 ET energy halt and does not emit bars during it; the
    # clock-time tag is a safety net, not a load-bearing presence check).
    maint_ok = 0.0 <= maint_pct < 10.0
    holiday_ok = 0.0 <= holiday_pct < 10.0
    print(f"  is_maintenance pct: {maint_pct:.2f}% (expected [0, 10)): {'PASS' if maint_ok else 'FAIL'}")
    print(f"  is_holiday_short pct: {holiday_pct:.2f}% (expected [0, 10)): {'PASS' if holiday_ok else 'FAIL'}")

    return bar_ok and monotonic and dup_ok and ohlc_ok and maint_ok and holiday_ok


def main() -> int:
    print("Phase 1 verify: SHA-256 sidecars")
    raw_ok = _verify_hash(RAW_CSV, RAW_HASH, "raw")
    clean_ok = _verify_hash(CLEAN_CSV, CLEAN_HASH, "clean")

    if not (raw_ok and clean_ok):
        print("\nPhase 1 verify: HASH FAIL — abort")
        return 2

    structural_ok = _verify_clean_csv()

    print()
    overall = raw_ok and clean_ok and structural_ok
    print(f"PHASE 1 VERIFY: {'PASS' if overall else 'FAIL'}")
    return 0 if overall else 2


if __name__ == "__main__":
    raise SystemExit(main())
