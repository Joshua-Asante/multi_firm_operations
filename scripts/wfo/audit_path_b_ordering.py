#!/usr/bin/env python3
"""Verify Path B discipline: OOS CSV mtimes postdate train-selection commits.

Usage:
    python scripts/wfo/audit_path_b_ordering.py scripts/wfo/runs/<id>/run_manifest.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _parse_commit_ts(s: str) -> datetime:
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def audit_manifest(manifest_path: Path, *, slack_seconds: float = 2.0) -> list[str]:
    errors: list[str] = []
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    folds = data.get("folds") or []
    for i, fold in enumerate(folds):
        fold_id = fold.get("fold_id", f"fold_{i}")
        commit_raw = fold.get("train_selection_committed_utc")
        oos_paths = fold.get("oos_csv_paths") or []
        if not commit_raw:
            errors.append(f"{fold_id}: missing train_selection_committed_utc")
            continue
        try:
            commit = _parse_commit_ts(commit_raw)
            if commit.tzinfo is None:
                commit = commit.replace(tzinfo=timezone.utc)
        except ValueError as e:
            errors.append(f"{fold_id}: bad train_selection timestamp {commit_raw!r}: {e}")
            continue
        commit_ts = commit.timestamp()
        for p in oos_paths:
            pp = Path(p)
            if not pp.is_file():
                errors.append(f"{fold_id}: OOS path missing {pp}")
                continue
            mtime = pp.stat().st_mtime
            if mtime + slack_seconds < commit_ts:
                errors.append(
                    f"{fold_id}: OOS file {pp.name} mtime precedes train_selection "
                    f"(mtime={mtime}, commit={commit_ts})"
                )
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("manifest", type=Path, help="run_manifest.json")
    args = ap.parse_args()
    errs = audit_manifest(args.manifest)
    if errs:
        for e in errs:
            print(e, file=sys.stderr)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
