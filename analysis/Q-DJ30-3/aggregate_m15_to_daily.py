"""Phase B Step 2 — daily OHLC + per-day session-boundary gap from M15 OANDA US30USD.

Reads:  data/bar_data/US30USD.csv  (101245 M15 OANDA bars, 2022-01-02 → 2026-04-19)
Writes: analysis/Q-DJ30-3/dj30_daily_gap.csv

Mechanistically-correct gap definition (revised after first-pass discovery
that DJ30 futures trade nearly 24/5, so a 13:00-UTC session boundary
creates artificial 15-min 'gaps' between back-to-back weekday sessions):

  For each weekday d in the panel:
    bar_1300_open(d)    = open of M15 bar at d 13:00 UTC
                          (start of Pine v4.5 active window per striker_dj30_v4.5.pine:105-109)
    prior_2100_close(d) = close of M15 bar at 21:00 UTC of the most recent prior weekday d'
                          (futures RTH close ~ 17:00 ET; for Mon entries, this is Fri 21:00 UTC)
    gap_points(d)       = bar_1300_open(d) - prior_2100_close(d)
                          — captures overnight + Asia + London + early-NY pre-market
    daily ATR uses calendar-day OHLC (00:00 UTC → 23:45 UTC) and Wilder-style SMA over 14 days
    gap_atr_normalized(d) = gap_points(d) / atr_14(d-1)
                          — lagging ATR (no look-ahead); d-1 is prior calendar day

Sensitivity: a 00:00-UTC calendar-day "gap" (ie just open-vs-prior-close for the
calendar day) is included in the output for completeness. The 21:00→13:00 form is
the canonical conditioning variable for §4.2 of the pre-registration.
"""
from pathlib import Path
import csv
import datetime as dt

CSV_M15 = Path("data/bar_data/US30USD.csv")
OUT = Path("analysis/Q-DJ30-3/dj30_daily_gap.csv")
ATR_PERIOD = 14


def parse_iso_utc(s: str) -> dt.datetime:
    s = s.rstrip("Z").split(".")[0]
    return dt.datetime.fromisoformat(s).replace(tzinfo=dt.timezone.utc)


# --- Load M15 ---
print(f"Loading {CSV_M15}...")
m15 = []
with CSV_M15.open(newline="", encoding="utf-8") as f:
    for line in csv.DictReader(f):
        m15.append({
            "t": parse_iso_utc(line["time"]),
            "o": float(line["open"]),
            "h": float(line["high"]),
            "l": float(line["low"]),
            "c": float(line["close"]),
        })
print(f"  Loaded {len(m15)} M15 bars  ({m15[0]['t'].isoformat()} -> {m15[-1]['t'].isoformat()})")
print()

# --- Index by (date, hour, minute) for O(1) lookups ---
bar_by_key = {(b["t"].date(), b["t"].hour, b["t"].minute): b for b in m15}

# --- Aggregate to calendar-day OHLC for ATR ---
calendar_days = {}
for b in m15:
    d = b["t"].date()
    if d not in calendar_days:
        calendar_days[d] = {"open": b["o"], "high": b["h"], "low": b["l"], "close": b["c"],
                            "first_t": b["t"], "last_t": b["t"], "n": 1}
    else:
        e = calendar_days[d]
        if b["t"] < e["first_t"]:
            e["open"] = b["o"]
            e["first_t"] = b["t"]
        if b["t"] > e["last_t"]:
            e["close"] = b["c"]
            e["last_t"] = b["t"]
        if b["h"] > e["high"]:
            e["high"] = b["h"]
        if b["l"] < e["low"]:
            e["low"] = b["l"]
        e["n"] += 1

dates_sorted = sorted(calendar_days.keys())
print(f"Calendar days: {len(dates_sorted)}  ({dates_sorted[0]} -> {dates_sorted[-1]})")

# --- Compute ATR(14) on calendar daily ---
prev_close = None
atr_history = []
for d in dates_sorted:
    e = calendar_days[d]
    if prev_close is None:
        tr = e["high"] - e["low"]
    else:
        tr = max(e["high"] - e["low"], abs(e["high"] - prev_close), abs(e["low"] - prev_close))
    atr_history.append(tr)
    e["tr"] = tr
    e["atr_14"] = sum(atr_history[-ATR_PERIOD:]) / min(len(atr_history), ATR_PERIOD)
    prev_close = e["close"]


# --- Identify weekdays in the panel where we have BOTH a 13:00 bar (or near) and a prior weekday's 21:00 close ---

def find_bar_near(d, hour, minute, tolerance_minutes=60):
    """Look up the M15 bar at d hour:minute UTC. If exact key absent, scan within +/- tolerance."""
    key = (d, hour, minute)
    if key in bar_by_key:
        return bar_by_key[key]
    target_dt = dt.datetime.combine(d, dt.time(hour, minute), tzinfo=dt.timezone.utc)
    # scan all minutes within tolerance, prefer earliest after target then closest
    best = None
    best_diff = None
    for off_min in range(-tolerance_minutes, tolerance_minutes + 1, 15):
        check_dt = target_dt + dt.timedelta(minutes=off_min)
        ck = (check_dt.date(), check_dt.hour, check_dt.minute)
        if ck in bar_by_key:
            diff = abs(off_min)
            if best is None or diff < best_diff:
                best = bar_by_key[ck]
                best_diff = diff
    return best


def prior_weekday(d):
    """Step back one day, skipping weekends. Returns prior weekday calendar date.

    NOTE: this returns the *calendar* prior weekday only. Holidays (Thanksgiving,
    New Year's Day, MLK Day, etc.) are still weekdays but have no market bars.
    For finding the prior weekday WITH a usable 21:00 UTC close, use
    prior_weekday_with_close().
    """
    p = d - dt.timedelta(days=1)
    while p.weekday() >= 5:  # 5=Sat, 6=Sun
        p = p - dt.timedelta(days=1)
    return p


def prior_weekday_with_close(d, max_lookback_days=10):
    """Walk back through weekends AND holidays until a weekday with a 21:00 UTC
    bar is found. Returns (date, bar) or (None, None) if exhausted.

    Handles cases like Black Friday (prior = Thanksgiving Thursday, no bars)
    and post-New-Year Tuesdays (prior = New Year's Monday, no bars).
    """
    p = d - dt.timedelta(days=1)
    for _ in range(max_lookback_days):
        if p.weekday() < 5:  # weekday
            bar = find_bar_near(p, 21, 0, tolerance_minutes=60)
            if bar is not None:
                return p, bar
        p = p - dt.timedelta(days=1)
    return None, None


# --- Build per-trading-day gap records ---
gap_rows = []
skipped = 0
for d in dates_sorted:
    if d.weekday() >= 5:  # skip weekends
        continue
    bar_1300 = find_bar_near(d, 13, 0, tolerance_minutes=60)
    if bar_1300 is None:
        skipped += 1
        continue
    pd, bar_prior_2100 = prior_weekday_with_close(d)
    if bar_prior_2100 is None:
        skipped += 1
        continue

    e_today = calendar_days.get(d)
    e_prior = calendar_days.get(pd)
    if e_today is None or e_prior is None:
        skipped += 1
        continue

    gap_pts = bar_1300["o"] - bar_prior_2100["c"]
    atr_lagged = e_prior["atr_14"]  # ATR through prior weekday — no look-ahead
    gap_atr = gap_pts / atr_lagged if atr_lagged > 0 else 0.0

    gap_rows.append({
        "date": d.isoformat(),
        "weekday": d.strftime("%a"),
        "daily_open_00utc": round(e_today["open"], 4),
        "daily_high": round(e_today["high"], 4),
        "daily_low": round(e_today["low"], 4),
        "daily_close_2345utc": round(e_today["close"], 4),
        "atr_14_lagged": round(atr_lagged, 4),
        "bar_1300_open": round(bar_1300["o"], 4),
        "prior_weekday": pd.isoformat(),
        "prior_2100_close": round(bar_prior_2100["c"], 4),
        "gap_points": round(gap_pts, 4),
        "gap_atr_normalized": round(gap_atr, 6),
        "abs_gap_atr": round(abs(gap_atr), 6),
    })

# --- Write ---
OUT.parent.mkdir(parents=True, exist_ok=True)
fieldnames = list(gap_rows[0].keys())
with OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(gap_rows)

print(f"Wrote {len(gap_rows)} weekday rows to {OUT}  (skipped {skipped} for missing 13:00/21:00 bars)")
print()

# --- Sanity ---
abs_gaps = sorted(r["abs_gap_atr"] for r in gap_rows)
n = len(abs_gaps)
print("=== Sanity (absolute gap distribution) ===")
print(f"  count                : {n}")
print(f"  mean |gap_atr|       : {sum(abs_gaps)/n:.4f}")
print(f"  median               : {abs_gaps[n//2]:.4f}")
print(f"  p80                  : {abs_gaps[int(0.80*n)]:.4f}")
print(f"  p85                  : {abs_gaps[int(0.85*n)]:.4f}")
print(f"  p90                  : {abs_gaps[int(0.90*n)]:.4f}")
print(f"  p95                  : {abs_gaps[int(0.95*n)]:.4f}")
print(f"  p99                  : {abs_gaps[int(0.99*n)]:.4f}")
print(f"  max                  : {abs_gaps[-1]:.4f}")
print()

# Closing price range
closes = [r["daily_close_2345utc"] for r in gap_rows]
print(f"  daily close range    : {min(closes):.0f} -> {max(closes):.0f}  (DJ30 expected 28000-46000 in 2022-2026)")

# Specific anchor check: 2025-02-07
anchor = next((r for r in gap_rows if r["date"] == "2025-02-07"), None)
if anchor:
    print()
    print("=== Anchor check: 2025-02-07 (NFP day, trade #168) ===")
    print(f"  prior_weekday        : {anchor['prior_weekday']}  ({anchor['prior_2100_close']})")
    print(f"  bar_1300_open        : {anchor['bar_1300_open']}")
    print(f"  gap_points           : {anchor['gap_points']:+.1f}")
    print(f"  atr_14_lagged        : {anchor['atr_14_lagged']:.1f}")
    print(f"  gap_atr_normalized   : {anchor['gap_atr_normalized']:+.4f}")
    print(f"  |gap_atr|            : {anchor['abs_gap_atr']:.4f}")
    pct = sum(1 for g in abs_gaps if g <= anchor["abs_gap_atr"]) / n
    print(f"  empirical percentile : {100*pct:.1f}% (>{100*pct:.0f}% of all panel days have smaller |gap|)")
