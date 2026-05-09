"""Provenance / audit trail — SHA256, run logging."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def file_sha256(path: str | os.PathLike[str]) -> str | None:
    """Return hex SHA256 of file at path, or None if absent."""
    p = Path(path)
    if not p.exists():
        return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def assemble_provenance(
    *,
    fills_csv_path: str | None,
    backtest_csv_paths: dict[str, str],
    ptl_query_timestamp: str,
    mc_invocation: str,
    dd_log_snapshot_at: str,
    op_test_trades: list[dict[str, Any]] | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    """Assemble a provenance block for the JSON output."""
    return {
        "generated_at": now_utc_iso(),
        "fills_csv_path": fills_csv_path,
        "fills_csv_sha256": file_sha256(fills_csv_path) if fills_csv_path else None,
        "backtest_csvs": {
            k: {"path": p, "sha256": file_sha256(p)}
            for k, p in backtest_csv_paths.items()
        },
        "ptl_query_timestamp": ptl_query_timestamp,
        "mc_invocation": mc_invocation,
        "dd_log_snapshot_at": dd_log_snapshot_at,
        "op_test_trades": op_test_trades or [],
        "warnings": warnings or [],
    }


def log_feeder_run(runs_dir: str | os.PathLike[str], payload: dict[str, Any]) -> str:
    """Persist the full feeder output to disk for replay/audit."""
    runs_path = Path(runs_dir)
    runs_path.mkdir(parents=True, exist_ok=True)
    fname = datetime.now().strftime("%Y-%m-%d_%H%M%S") + ".json"
    full_path = runs_path / fname
    with full_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    return str(full_path)
