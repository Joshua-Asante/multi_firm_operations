"""Deterministic grid fingerprint (JSON canonical encoding, stdlib only)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def canonical_json_bytes(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def grid_hash_from_path(grid_path: str | Path) -> str:
    raw = Path(grid_path).read_bytes()
    obj = json.loads(raw.decode("utf-8"))
    return sha256_hex(canonical_json_bytes(obj))


def fold_spec_hash_from_path(fold_path: str | Path) -> str:
    raw = Path(fold_path).read_bytes()
    obj = json.loads(raw.decode("utf-8"))
    return sha256_hex(canonical_json_bytes(obj))


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python grid_hash.py <path/to/spec.json>", file=sys.stderr)
        raise SystemExit(2)
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"Not a file: {path}", file=sys.stderr)
        raise SystemExit(1)
    # Same canonical hash for grid or fold spec JSON.
    print(grid_hash_from_path(path))
