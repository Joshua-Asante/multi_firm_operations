#!/usr/bin/env python3
"""Regenerate docs/inventory/deletion_candidates.md from REPO_MAP + git ls-files.

No vendor CSV or network access. Uses stdlib + git only (git must be on PATH).

Usage:
  python scripts/deletion_candidate_report.py
  python scripts/deletion_candidate_report.py --csv docs/inventory/deletion_candidates.csv
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REPO_MAP_PATH = REPO_ROOT / "REPO_MAP.md"
OUTPUT_MD = REPO_ROOT / "docs" / "inventory" / "deletion_candidates.md"

# Mission tiers (aligned with CLAUDE.md + deletion_candidate surfacing plan).
TIER_INTRO = """## Mission tier rubric (P0–P3)

| Tier | Meaning | Typical action |
|------|---------|----------------|
| **P0 — Protect** | Live ops, CI contract, lock/MC anchors, immutable ADRs/historical docs | Not a deletion candidate |
| **P1 — Strong review** | `[X]` archive, **unmapped** tracked paths (REPO_MAP gap), superseded trees | Rehome, submodule split, or delete after audit |
| **P2 — Weak review** | `[U]` utilities / planning artifacts with weak references to hot path | Deprecate, compress, or archive |
| **P3 — Policy / borderline** | `[?]` or REPO_MAP open questions (e.g. retirement triggers) | Resolve disposition in REPO_MAP first |

**Immutable docs:** `docs/adr/` and `docs/historical/` are P0 by policy (same spirit as `docs/operational_rules.md`).
"""


P0_EXACT = frozenset(
    {
        "accounts.py",
        "cli.py",
        "csv_parser.py",
        "firm_rules.py",
        "dd_protection.py",
        "portfolio_mc.py",
        "pyproject.toml",
        "CLAUDE.md",
        "README.md",
        "CHANGELOG.md",
        "REPO_MAP.md",
        ".gitignore",
    }
)

P0_PREFIXES = (
    "tests/",
    "lib/",
    ".github/workflows/",
    "docs/adr/",
    "docs/historical/",
    "live_journal/scripts/",
    "live_journal/references/",
    "data/reconciles/",
)

# Scripts and roots named explicitly in CLAUDE.md / integrity gate.
P0_PATH_PREFIXES = (
    "scripts/fetch_oanda_bars.py",
    "scripts/lock_event_hook.py",
    "scripts/build_us_releases.py",
    "scripts/check_data_manifests.py",
    "scripts/deletion_candidate_report.py",
    "analysis/time_to_pass.py",
)


def _git_ls_files() -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [ln.strip().replace("\\", "/") for ln in out.splitlines() if ln.strip()]


def _parse_repo_map() -> tuple[list[tuple[str, str]], list[str]]:
    """Return (classified_rows as (tag, path_pattern), raw_lines for Archive header scan)."""
    text = REPO_MAP_PATH.read_text(encoding="utf-8")
    rows: list[tuple[str, str]] = []
    for line in text.splitlines():
        m = re.match(r"^\[(A|U|X|\?)\]\s+(.+)$", line.strip())
        if not m:
            continue
        tag, rest = m.group(1), m.group(2)
        if " — " in rest:
            rest = rest.split(" — ", 1)[0]
        if " (" in rest:
            rest = rest.split(" (", 1)[0]
        rest = rest.strip()
        # Comma-separated multiple paths (no glob/brace)
        if ", " in rest and "*" not in rest and "{" not in rest:
            for part in rest.split(", "):
                p = part.strip()
                if p:
                    rows.append((tag, p))
        else:
            rows.append((tag, rest))
    return rows, text.splitlines()


def _expand_brace_pattern(pattern: str) -> list[str]:
    """Expand single `{a,b,c}` group in a pattern (REPO_MAP uses one group)."""
    if "{" not in pattern or "}" not in pattern:
        return [pattern]
    left, mid = pattern.split("{", 1)
    inner, right = mid.split("}", 1)
    opts = [x.strip() for x in inner.split(",")]
    return [left + opt + right for opt in opts]


def _matches_pattern(git_path: str, pattern: str) -> bool:
    git_path = git_path.replace("\\", "/")
    patterns = _expand_brace_pattern(pattern.strip())
    for p in patterns:
        p = p.strip().replace("\\", "/")
        if p.endswith("/"):
            if git_path.startswith(p) or git_path == p.rstrip("/"):
                return True
            continue
        if "*" in p or "?" in p:
            if fnmatch.fnmatch(git_path, p):
                return True
            continue
        if git_path == p:
            return True
    return False


def _coverage(git_paths: list[str], repo_map_rows: list[tuple[str, str]]) -> dict[str, tuple[str, str]]:
    """Map each git path -> (tag, matched_pattern)."""
    assignment: dict[str, tuple[str, str]] = {}
    for g in git_paths:
        for tag, pattern in repo_map_rows:
            if _matches_pattern(g, pattern):
                assignment[g] = (tag, pattern)
                break
    return assignment


def _mission_tier(path: str, tag: str | None, mapped: bool) -> str:
    if path in P0_EXACT:
        return "P0"
    for pref in P0_PREFIXES:
        if path.startswith(pref):
            return "P0"
    if path.startswith(P0_PATH_PREFIXES):
        return "P0"
    if path.startswith("strategies/MANIFEST.sha256"):
        return "P0"
    if path.startswith("strategies/") and (
        path.endswith("CHANGELOG.md") or path.endswith("LOCK.md") or path.endswith("MANIFEST.sha256")
    ):
        return "P0"
    if path.startswith("data/tv_exports/pepperstone/SHA256SUMS"):
        return "P0"
    if path in ("docs/rule_0.md", "docs/operational_rules.md"):
        return "P0"
    if not mapped:
        return "P1"
    assert tag is not None
    if tag == "?":
        return "P3"
    if tag == "X":
        return "P1"
    if tag == "U":
        return "P2"
    # [A] — active but not all ops-critical: default P2 unless matched above
    if path.startswith("docs/superpowers/"):
        return "P2"
    if path.startswith(("docs/adr/", "docs/historical/")):
        return "P0"
    if path.startswith("docs/methodology/") or path.startswith("docs/briefs/") or path.startswith("docs/audits/"):
        return "P2"
    if path.startswith("docs/templates/"):
        return "P2"
    if path.startswith("docs/notion/"):
        return "P2"
    if path.startswith("analysis/"):
        return "P2"
    if path.startswith("weekly_review_feeder/"):
        return "P2"
    if path.startswith(".claude/commands/") or path == ".claude/settings.json":
        return "P2"
    if path == "fxify_rule_validator.py":
        return "P2"
    # Remaining [A] at repo root / misc
    return "P2"


def _load_text_index(git_paths: list[str]) -> dict[str, str]:
    """Path -> utf-8 text for small-ish non-binary files."""
    out: dict[str, str] = {}
    for p in git_paths:
        full = REPO_ROOT / p
        try:
            data = full.read_bytes()
        except OSError:
            continue
        if b"\0" in data[:8192] or len(data) > 2_000_000:
            continue
        try:
            out[p] = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
    return out


def _reference_hits(text_index: dict[str, str], needle: str) -> list[str]:
    """Return paths whose text contains `needle` (excluding self-match policy in caller)."""
    hits: list[str] = []
    if not needle:
        return hits
    for p, text in text_index.items():
        if needle in text:
            hits.append(p)
    return hits


def _suggested_step(tier: str, tag: str | None, mapped: bool) -> str:
    if tier == "P0":
        return "keep"
    if tier == "P3":
        return "resolve_disposition_in_REPO_MAP"
    if not mapped:
        return "reclassify_in_REPO_MAP"
    if tag == "X":
        return "externalize_or_delete_after_audit"
    if tier == "P2":
        return "deprecate_merge_or_archive"
    return "review"


def _sort_queue_key_row(r: Row) -> tuple[int, str]:
    tier_order = {"P1": 0, "P2": 1, "P3": 2, "P0": 9}
    return (tier_order.get(r.mission_tier, 99), r.path)


@dataclass
class Row:
    path: str
    repo_map_tag: str
    mission_tier: str
    referenced_by: str
    risk_notes: str
    suggested_next_step: str


def build_rows(
    git_paths: list[str], coverage: dict[str, tuple[str, str]], text_index: dict[str, str]
) -> list[Row]:
    rows: list[Row] = []
    for p in sorted(git_paths):
        # Omit only the generator outputs from the tables (avoid self-reference noise).
        if p in (
            "docs/inventory/deletion_candidates.md",
            "docs/inventory/deletion_candidates.csv",
        ):
            continue
        mapped = p in coverage
        tag, pattern = coverage[p] if mapped else ("", "")
        disp_tag = tag if mapped else "—"
        tier = _mission_tier(p, tag if mapped else None, mapped)
        ref_parts: list[str] = []
        hits_path = [x for x in _reference_hits(text_index, p) if x != p]
        if hits_path:
            ref_parts.append(f"path_string({len(hits_path)})")
        base = Path(p).name
        hits_base = [x for x in _reference_hits(text_index, base) if x != p] if base else []
        if hits_base and not hits_path:
            ref_parts.append(f"basename({len(hits_base)})")
        referenced_by = ", ".join(ref_parts) if ref_parts else "—"

        risk_notes: list[str] = []
        if not mapped:
            risk_notes.append("unmapped_in_REPO_MAP")
        if mapped and tag == "X":
            risk_notes.append("archived_tag_X")
        if p.startswith("docs/adr/") or p.startswith("docs/historical/"):
            risk_notes.append("immutable_doc_policy")
        if referenced_by != "—":
            risk_notes.append("has_textual_refs")

        rows.append(
            Row(
                path=p,
                repo_map_tag=disp_tag if mapped else "unmapped",
                mission_tier=tier,
                referenced_by=referenced_by,
                risk_notes="; ".join(risk_notes) if risk_notes else "—",
                suggested_next_step=_suggested_step(tier, tag if mapped else None, mapped),
            )
        )
    return rows


def write_markdown(rows: list[Row], repo_map_row_count: int) -> str:
    today = date.today().isoformat()
    review_queue = [r for r in rows if r.mission_tier != "P0"]
    protect = [r for r in rows if r.mission_tier == "P0"]

    lines = [
        f"# Deletion candidate surfacing — inventory report",
        "",
        f"**Generated:** {today} (regenerate via `python scripts/deletion_candidate_report.py`)",
        f"**Inputs:** `REPO_MAP.md` ({repo_map_row_count} classified path patterns), `git ls-files`",
        "",
        TIER_INTRO,
        "",
        "## Summary",
        "",
        f"- **Tracked files:** {len(rows)}",
        f"- **P0 (protect):** {len(protect)}",
        f"- **Review queue (non-P0):** {len(review_queue)}",
        "",
        "## Review queue (sorted: P1 then P2 then P3)",
        "",
        "Lowest mission relevance first within tier (see rubric). **Do not delete** without resolving `risk_notes` and backlinks from ADRs/briefs.",
        "",
        "| path | repo_map_tag | mission_tier | referenced_by | risk_notes | suggested_next_step |",
        "|------|--------------|--------------|---------------|------------|---------------------|",
    ]

    rq_sorted = sorted([r for r in rows if r.mission_tier != "P0"], key=_sort_queue_key_row)
    for r in rq_sorted:
        lines.append(
            f"| `{r.path}` | {r.repo_map_tag} | {r.mission_tier} | {r.referenced_by} | "
            f"{r.risk_notes} | {r.suggested_next_step} |"
        )

    lines.extend(
        [
            "",
            "## P0 protect list (excerpt — do not treat as deletion candidates)",
            "",
            f"_Full count {len(protect)}; sample first 40 paths._",
            "",
            "| path | repo_map_tag |",
            "|------|--------------|",
        ]
    )
    for r in protect[:40]:
        lines.append(f"| `{r.path}` | {r.repo_map_tag} |")
    if len(protect) > 40:
        lines.append(f"| _… {len(protect) - 40} more …_ | |")

    lines.extend(
        [
            "",
            "## Mechanical procedure (repeatable)",
            "",
            "1. `git ls-files` enumerate tracked paths.",
            "2. Parse `REPO_MAP.md` lines matching `^[AUX?]` (see script).",
            "3. Match each file with `fnmatch` / prefix rules / brace expansion.",
            "4. Label mission tier via rubric; flag `unmapped_in_REPO_MAP` as P1.",
            "5. Textual reference scan (UTF-8, non-huge files): substring path + basename.",
            "6. Exclude local-only trees from git inventory (e.g. `.claude/worktrees/` untracked).",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def write_csv(rows: list[Row], dest: Path) -> None:
    import csv

    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "path",
                "repo_map_tag",
                "mission_tier",
                "referenced_by",
                "risk_notes",
                "suggested_next_step",
            ]
        )
        for r in rows:
            w.writerow(
                [
                    r.path,
                    r.repo_map_tag,
                    r.mission_tier,
                    r.referenced_by,
                    r.risk_notes,
                    r.suggested_next_step,
                ]
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deletion candidate inventory report.")
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Optional CSV output path (default: none)",
    )
    args = parser.parse_args()

    git_paths = _git_ls_files()
    repo_map_rows, raw_lines = _parse_repo_map()
    classified_line_count = sum(
        1 for line in raw_lines if re.match(r"^\[(A|U|X|\?)\]\s+(.+)$", line.strip())
    )
    coverage = _coverage(git_paths, repo_map_rows)
    text_index = _load_text_index(git_paths)
    rows = build_rows(git_paths, coverage, text_index)

    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text(
        write_markdown(rows, classified_line_count),
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT_MD.relative_to(REPO_ROOT)}")

    if args.csv:
        write_csv(rows, args.csv.resolve())
        print(f"Wrote {args.csv.resolve().relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
