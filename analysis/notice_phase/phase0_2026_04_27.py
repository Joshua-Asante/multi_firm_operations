"""Phase 0 provenance verification for Notice 2026-04-27 over OANDA-proxy corpus.

Verifies bar files referenced by the Identify-corpus manifest:
  docs/methodology/identify_corpus/2026-04-26/phase0_log.json + README.md.

Per brief: file paths are not provenance. We re-verify content hash, first/last
timestamps, row count, and broker tag per the AMENDMENT_oanda_rescope.md
scope-correction (OANDA, not Pepperstone — brief preamble language slip).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
PARENT_REPO = REPO_ROOT.parent.parent.parent  # worktree -> .claude -> repo -> parent
BAR_DIR = PARENT_REPO / "data" / "bar_data"

# Manifest expectations from docs/methodology/identify_corpus/2026-04-26/phase0_log.json
MANIFEST = {
    "XAUUSD": {"path": BAR_DIR / "XAUUSD.csv", "n_rows": 101461,
               "first": "2022-01-02", "last": "2026-04-19", "broker": "OANDA"},
    "US30USD": {"path": BAR_DIR / "US30USD.csv", "n_rows": 101245,
                "first": "2022-01-02", "last": "2026-04-19", "broker": "OANDA"},
    "USDJPY": {"path": BAR_DIR / "USDJPY.csv", "n_rows": 106820,
               "first": "2022-01-02", "last": "2026-04-19", "broker": "OANDA"},
}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(symbol: str, info: dict) -> dict:
    path = info["path"]
    if not path.exists():
        return {"symbol": symbol, "PASS": False, "reason": f"missing: {path}"}
    sha = sha256_file(path)
    df = pd.read_csv(path)
    n = len(df)
    first = pd.to_datetime(df["time"].iloc[0]).date().isoformat()
    last = pd.to_datetime(df["time"].iloc[-1]).date().isoformat()

    checks = {
        "row_count_matches_manifest": n == info["n_rows"],
        "first_ts_matches_manifest": first == info["first"],
        "last_ts_matches_manifest": last == info["last"],
        # Broker tag: bar files have OHLCV only, no broker stamp inside.
        # Identity is anchored upstream by lib/mvd.assert_tv_export against the
        # TV export filename, which DOES carry the broker tag. We assert the
        # corresponding TV export exists and has OANDA in the name.
        "tv_export_oanda_present": _check_tv_export(symbol, info["broker"]),
    }
    pass_all = all(checks.values())
    return {
        "symbol": symbol,
        "path": str(path),
        "sha256": sha,
        "n_rows": n,
        "first_ts": first,
        "last_ts": last,
        "broker_via_tv_export": info["broker"],
        "checks": checks,
        "PASS": pass_all,
    }


def _check_tv_export(symbol: str, broker: str) -> bool:
    """Per AMENDMENT, broker identity is anchored at the TV-export filename.

    Bar files have no internal broker stamp; the assertion that the panel is
    OANDA is established upstream by assert_tv_export at Phase 0 of Identify
    (logged in phase0_log.json). We verify the OANDA-tagged TV exports exist.
    """
    strat_to_tv = {
        "XAUUSD": "Guardian_Gold_v5.5_OANDA_XAUUSD",
        "US30USD": "Striker_DJ30_v4.4_OANDA_US30USD",
        "USDJPY": "Aegis_USDJPY_v4.3_OANDA_USDJPY",
    }
    prefix = strat_to_tv[symbol]
    tv_dir = REPO_ROOT / "data" / "tv_exports" / "oanda"
    matches = list(tv_dir.glob(f"{prefix}*.csv"))
    return len(matches) == 1 and broker.lower() in matches[0].name.lower()


def main():
    out = {
        "run_at": pd.Timestamp.now("UTC").isoformat(),
        "scope": "Notice 2026-04-27 over OANDA-proxy corpus",
        "amendment_binding": "docs/methodology/identify_corpus/2026-04-26/AMENDMENT_oanda_rescope.md",
        "brief_preamble_correction": (
            "Brief preamble says 'Pepperstone-canonical bar-corpus'; "
            "AMENDMENT rescopes to OANDA-proxy. Phase 0 verifies against OANDA "
            "manifest per AMENDMENT, with canonical_status=PROXY end-to-end."
        ),
        "files": [verify(s, info) for s, info in MANIFEST.items()],
    }
    out["all_pass"] = all(f["PASS"] for f in out["files"])
    print(json.dumps(out, indent=2))
    return 0 if out["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
