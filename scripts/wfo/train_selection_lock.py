"""Per-fold train-selection lock (Q-CORR-1.2 §6.5).

OOS CSV basename must match the lock written *before* OOS TV export.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def write_train_selection_lock(
    out_path: str | Path,
    *,
    fold_id: str,
    expected_oos_csv_basename: str,
    selected_config_id: str = "",
    extra: dict | None = None,
) -> str:
    """Write lock file; returns ``train_selection_committed_utc`` ISO string."""
    committed = datetime.now(timezone.utc).isoformat()
    payload: dict = {
        "fold_id": fold_id,
        "expected_oos_csv_basename": expected_oos_csv_basename,
        "train_selection_committed_utc": committed,
        "committed_utc": committed,
        "selected_config_id": selected_config_id,
    }
    if extra:
        payload.update(extra)
    Path(out_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return committed


def read_train_selection_lock(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def assert_oos_matches_lock(oos_csv_path: str | Path, lock_path: str | Path) -> None:
    lock = read_train_selection_lock(lock_path)
    expected = lock["expected_oos_csv_basename"]
    actual = Path(oos_csv_path).name
    if actual != expected:
        raise AssertionError(
            f"OOS basename mismatch for {lock_path}: got {actual!r}, expected {expected!r}"
        )
