#!/usr/bin/env python3
"""Verify or regenerate SHA256SUMS manifests for gitignored vendor CSV trees.

Hashes working-tree bytes as read from disk (open(..., \"rb\")) — on Windows
with core.autocrlf=true this is CRLF as checked out, not the git blob.

Usage:
    python scripts/check_data_manifests.py              # default: --check
    python scripts/check_data_manifests.py --check
    python scripts/check_data_manifests.py --regenerate --dry-run
    python scripts/check_data_manifests.py --regenerate

Exit codes:
    0 — check passed or regenerate completed
    1 — check failed (drift, missing, extra, parse error) or invalid CLI
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Each directory contains SHA256SUMS covering non-hidden *.csv in that dir only.
MANIFEST_DIRS = [
    REPO_ROOT / "data/tv_exports/pepperstone",
    REPO_ROOT / "data/tv_exports/oanda",
    REPO_ROOT / "data/bar_data",
    REPO_ROOT / "data/external",
]

MANIFEST_NAME = "SHA256SUMS"
LINE_RE = re.compile(r"^([0-9a-f]{64}) \*(.+)$")
REGEN_HINT = "Run: python scripts/check_data_manifests.py --regenerate"


def _rel_posix(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _list_csv_basenames(dir_path: Path) -> dict[str, Path]:
    """basename -> full path for non-hidden *.csv in dir_path (no recursion)."""
    out: dict[str, Path] = {}
    if not dir_path.is_dir():
        return out
    for p in sorted(dir_path.iterdir()):
        if not p.is_file():
            continue
        if p.name.startswith("."):
            continue
        if p.suffix.lower() != ".csv":
            continue
        out[p.name] = p
    return out


def _parse_manifest(manifest_path: Path) -> tuple[dict[str, str], list[str]]:
    """Returns (basename -> hex digest, parse errors)."""
    errors: list[str] = []
    entries: dict[str, str] = {}
    if not manifest_path.is_file():
        errors.append(f"MISSING_MANIFEST {_rel_posix(manifest_path)}")
        return entries, errors
    text = manifest_path.read_text(encoding="utf-8", errors="replace")
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        m = LINE_RE.match(line)
        if not m:
            errors.append(
                f"BAD_LINE {_rel_posix(manifest_path)}:{lineno} {line!r}"
            )
            continue
        digest, name = m.group(1), m.group(2)
        if name in entries:
            errors.append(
                f"DUPLICATE {_rel_posix(manifest_path)} basename={name!r}"
            )
            continue
        entries[name] = digest
    return entries, errors


def _emit_regen_hint() -> None:
    print(REGEN_HINT, file=sys.stderr)


def check_all() -> int:
    failed = False
    for d in MANIFEST_DIRS:
        manifest = d / MANIFEST_NAME
        entries, parse_errs = _parse_manifest(manifest)
        for e in parse_errs:
            print(e, file=sys.stderr)
            failed = True
        if parse_errs:
            continue

        # An empty manifest is a legitimate state: the manifest dir
        # tracks zero CSVs. The EXTRA / MISSING checks below still cover
        # the accidental-strip case (CSVs on disk but not in manifest →
        # EXTRA per file) and the silent-loss case (manifest entry exists
        # but file missing → MISSING). Removed the standalone EMPTY_MANIFEST
        # hard-failure on 2026-05-13 to support intentionally-empty manifest
        # dirs (e.g., dead datasets being stripped from the integrity gate).

        on_disk = _list_csv_basenames(d)
        manifest_names = set(entries)

        for name in sorted(on_disk.keys() - manifest_names):
            print(f"EXTRA {_rel_posix(on_disk[name])}", file=sys.stderr)
            failed = True

        for name in sorted(manifest_names):
            path = d / name
            if name not in on_disk:
                print(f"MISSING {_rel_posix(path)}", file=sys.stderr)
                failed = True
                continue
            got = _hash_file(path)
            exp = entries[name]
            if got != exp:
                print(
                    f"MISMATCH {_rel_posix(path)} "
                    f"manifest={exp[:8]}... ondisk={got[:8]}...",
                    file=sys.stderr,
                )
                failed = True

    if failed:
        _emit_regen_hint()
        return 1
    return 0


def _build_manifest_body(dir_path: Path) -> str:
    csvs = _list_csv_basenames(dir_path)
    lines: list[str] = []
    for name in sorted(csvs.keys()):
        digest = _hash_file(csvs[name])
        lines.append(f"{digest} *{name}")
    return "\n".join(lines) + ("\n" if lines else "")


def regenerate_all(*, dry_run: bool) -> int:
    for d in MANIFEST_DIRS:
        manifest = d / MANIFEST_NAME
        body = _build_manifest_body(d)
        rel = _rel_posix(manifest)
        if dry_run:
            print(f"--- {rel} (proposed) ---", file=sys.stdout)
            sys.stdout.write(body)
            if body and not body.endswith("\n"):
                print(file=sys.stdout)
        else:
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text(body, encoding="utf-8", newline="\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check or regenerate vendor data SHA256SUMS manifests.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify manifests vs on-disk CSVs (default if neither mode given)",
    )
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="rewrite SHA256SUMS from current CSVs (sorted by filename)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="with --regenerate: print proposed manifests to stdout; do not write",
    )
    args = parser.parse_args()

    if args.dry_run and not args.regenerate:
        print("--dry-run requires --regenerate", file=sys.stderr)
        return 1

    if args.regenerate and args.check:
        print("use either --regenerate or --check, not both", file=sys.stderr)
        return 1

    if args.regenerate:
        return regenerate_all(dry_run=args.dry_run)

    # default + explicit --check
    return check_all()


if __name__ == "__main__":
    sys.exit(main())
