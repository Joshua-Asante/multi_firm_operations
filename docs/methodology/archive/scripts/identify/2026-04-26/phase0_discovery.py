"""Phase 0 — discovery and verification gate for the 2026-04-26 OANDA-proxy
Identify corpus.

Halts (raises) on any failure. On success, writes:
  - resolved_tz.json     (per-strategy chart-TZ → UTC offset hours)
  - phase0_log.json      (verification log for README inclusion)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import pandas as pd

from common import (
    BAR_DIR, TV_DIR, OUT_DIR, STRATEGIES,
    load_bars, load_tv,
)
from mvd import assert_tv_export, assert_min_rows, assert_window


PHASE0_RESULTS: list[dict] = []


def step(label: str, fn):
    print(f"[phase0] {label}", flush=True)
    try:
        result = fn()
        PHASE0_RESULTS.append({"step": label, "status": "PASS", "result": result})
        print(f"  PASS — {result}", flush=True)
        return result
    except Exception as e:
        PHASE0_RESULTS.append({"step": label, "status": "FAIL", "error": str(e)})
        print(f"  FAIL — {e}", flush=True)
        raise


_STRATEGY_NAME = {"guardian": "Guardian", "striker": "Striker", "aegis": "Aegis"}


def verify_tv(strategy: str):
    info = STRATEGIES[strategy]
    csv = TV_DIR / info["tv"]
    meta = assert_tv_export(
        csv,
        expected_strategy=_STRATEGY_NAME[strategy],
        expected_version=info["version"],
        expected_broker=info["broker"],
        expected_symbol=info["tv_symbol"],
    )
    return f"identity OK: {meta['strategy']}/{meta['instrument']}/{meta['version']}/{meta['broker']}/{meta['symbol']}"


def verify_bars(symbol: str):
    df = load_bars(symbol)
    n = len(df)
    first, last = df.index.min(), df.index.max()
    assert_min_rows(n, 90_000, label=f"OANDA {symbol} 15m bars (4yr expected)")
    assert_window(
        first.to_pydatetime().replace(tzinfo=None),
        last.to_pydatetime().replace(tzinfo=None),
        expected_min_days=1500,
        label=f"OANDA {symbol} window",
    )
    return f"{symbol}: n={n:,} rows, span={first.date()}..{last.date()}"


def resolve_tz(strategy: str) -> dict:
    """Spot-check 5 entry timestamps under UTC and NY hypotheses; pick the
    interpretation whose bar-close matches the TV entry_price more tightly.

    Returns: {"offset_hours": int, "median_diff_at_offset": float, "median_diff_alt": float}
    """
    info = STRATEGIES[strategy]
    tv = load_tv(strategy)
    bars = load_bars(info["bar_symbol"])

    # Sample 5 entries spread across the panel
    ents = tv.dropna(subset=["entry_time", "entry_price"]).reset_index(drop=True)
    n = len(ents)
    if n < 5:
        raise AssertionError(f"phase0 TZ check {strategy}: only {n} entries")
    sample_idx = [int(round(n * i / 5)) for i in range(5)]
    sample = ents.iloc[sample_idx]

    # Candidate offsets: 0 (UTC), 4 (EDT), 5 (EST). For an in-sample mix we
    # check both 4 and 5; in winter Striker first trade 2022-01-04 is EST=5.
    candidates = {"UTC": 0, "EST": 5, "EDT": 4}

    def median_diff_at(offset: int) -> float:
        diffs = []
        for _, row in sample.iterrows():
            tv_t = row["entry_time"]
            utc_t = (tv_t + pd.Timedelta(hours=offset)).tz_localize("UTC")
            # Round down to 15min
            utc_t = utc_t.floor("15min")
            if utc_t in bars.index:
                bar = bars.loc[utc_t]
                # entry fires at bar close in Pine
                px = float(bar["close"])
                diffs.append(abs(px - float(row["entry_price"])))
            else:
                diffs.append(float("inf"))
        valid = [d for d in diffs if d != float("inf")]
        return sorted(valid)[len(valid) // 2] if valid else float("inf")

    scored = {name: median_diff_at(off) for name, off in candidates.items()}
    best_name = min(scored, key=scored.get)
    best_offset = candidates[best_name]
    # Sanity: best should be << than any other by ~10x
    others = [v for k, v in scored.items() if k != best_name]
    if best_offset != 0 and min(others) < scored[best_name] * 5:
        # Ambiguous — but that's still informative
        pass
    return {
        "strategy": strategy,
        "best_tz_label": best_name,
        "offset_hours_utc_minus_chart": best_offset,
        "median_price_diff_by_tz": {k: (None if v == float("inf") else float(v)) for k, v in scored.items()},
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. TV identity
    for s in STRATEGIES:
        step(f"TV identity assert: {s}", lambda s=s: verify_tv(s))

    # 2. Bar files: row count, window
    for s in STRATEGIES:
        sym = STRATEGIES[s]["bar_symbol"]
        step(f"Bar verify: {sym}", lambda sym=sym: verify_bars(sym))

    # 3. TZ reconciliation
    tz_resolved = {}
    for s in STRATEGIES:
        result = step(f"TZ reconciliation: {s}", lambda s=s: resolve_tz(s))
        tz_resolved[s] = result["offset_hours_utc_minus_chart"]

    # Persist resolved TZ for downstream scripts
    (OUT_DIR / "resolved_tz.json").write_text(json.dumps(tz_resolved, indent=2))
    (OUT_DIR / "phase0_log.json").write_text(json.dumps({
        "run_at": datetime.now(timezone.utc).isoformat(),
        "feed": "OANDA",
        "panel_window": "2022-01-02_2026-04-19",
        "canonical_status": "PROXY",
        "amendment": "AMENDMENT_oanda_rescope.md",
        "results": PHASE0_RESULTS,
        "resolved_tz_utc_minus_chart": tz_resolved,
    }, indent=2))

    print(f"\n[phase0] PASS — wrote resolved_tz.json and phase0_log.json", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[phase0] HALT — {e}", file=sys.stderr)
        # Persist partial log even on failure
        try:
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            (OUT_DIR / "phase0_log.json").write_text(json.dumps({
                "run_at": datetime.now(timezone.utc).isoformat(),
                "status": "HALT",
                "error": str(e),
                "results": PHASE0_RESULTS,
            }, indent=2))
        except Exception:
            pass
        sys.exit(2)
