#!/usr/bin/env python3
"""ADR 2026-05-16-fixture-test-requirement Hook 1.

Verify every .py path cited in any brief or ADR §0 block has a fixture test
under ``tests/test_<basename>.py``. Exits 0 if all covered; prints missing
entries to stdout and exits 1 if not.

Anchor invariant: a brief whose §0 cites an analysis script as a production
read implies that script's output is load-bearing for the brief's claims;
the fixture test is the mechanical correctness anchor for that output.
"""

from __future__ import annotations

import pathlib
import re
import sys


SECTION_RE = re.compile(r"(?m)^##\s*§0[^\n]*\n(.*?)(?=^##\s|\Z)", re.DOTALL)
PY_REF_RE = re.compile(r"`([\w/]+\.py)`")


def main() -> int:
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    brief_paths = list((repo_root / "docs" / "briefs").rglob("*.md")) + list(
        (repo_root / "docs" / "adr").rglob("*.md")
    )
    missing: list[str] = []
    for bp in brief_paths:
        text = bp.read_text(encoding="utf-8", errors="replace")
        m = SECTION_RE.search(text)
        if not m:
            continue
        for script in PY_REF_RE.findall(m.group(1)):
            # Skip test files themselves — §0 may legitimately cite a test file
            # as a Rule-0 read (to verify test structure), but test files are
            # not analysis scripts whose output enters brief evidence.
            if script.startswith("tests/") or pathlib.Path(script).stem.startswith("test_"):
                continue
            base = pathlib.Path(script).stem
            test_path = repo_root / "tests" / f"test_{base}.py"
            if not test_path.exists():
                rel_bp = bp.relative_to(repo_root)
                rel_test = test_path.relative_to(repo_root)
                missing.append(f"{rel_bp}: section 0 cites {script} but {rel_test} missing")

    for line in missing:
        print(line)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
