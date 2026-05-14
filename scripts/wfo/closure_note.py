#!/usr/bin/env python3
"""Generate a Q-CORR-1.2 closure-note SKELETON from a finished Path B run.

Consumes:
  - <run_dir>/run_manifest.json
  - <run_dir>/report.json  (written by `emit-reports`)

Emits a markdown skeleton with:
  - A <DISPOSITION> placeholder for Joshua to hand-fill (per parent brief §5.8:
    "disposition lives in the closure note Joshua writes by hand")
  - All three §17 branches included — operator deletes the non-applicable ones.

NOT a state-of-record artifact. The closure note Joshua finalizes is the
authoritative one; this script just structures it.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path


_DISPOSITION_PLACEHOLDER = "<DISPOSITION: RESOLVED | FALSIFIED | AMBIGUOUS — fill from `emit-reports` stdout>"


def _format_gate_table(gates: dict) -> list[str]:
    if not gates:
        return ["_No §14 gates evaluated — run is train-only or stub._"]
    lines = ["| Gate | Pass | Detail |", "|---|---|---|"]
    for gid in sorted(gates.keys()):
        g = gates[gid]
        ok = "OK" if g.get("pass") else "FAIL"
        detail_parts = []
        for k, v in g.items():
            if k == "pass":
                continue
            if isinstance(v, float):
                detail_parts.append(f"{k}={v:.4f}")
            else:
                detail_parts.append(f"{k}={v}")
        lines.append(f"| `{gid}` | {ok} | {', '.join(detail_parts)} |")
    return lines


def _resolved_branch() -> list[str]:
    return [
        "### §4.A — If RESOLVED (delete if not applicable)",
        "",
        "Per parent brief §17:",
        "",
        "- [ ] Belt update scoped to the Gold/Silver pair only (NOT a portfolio-wide methodology change).",
        "- [ ] Separate lock-decision brief authored for portfolio promotion to 5-strategy (do NOT auto-include in `portfolio_mc.py`).",
        "- [ ] Re-MC at 5-strategy composition (separate methodology layer; not in this Pre-Q).",
        "- [ ] Optional **Q-CORR-1.3** Pre-Q for wide optimization on (Wide, Path A) if Joshua chooses to pursue.",
        "- [ ] Append one-line hint note to `docs/notes/q-corr-1-hint-log.md` (create file on first entry if missing).",
        "    Format: `YYYY-MM-DD | <config_id> | PF=… WR=…% DD=…% ρ=… | one-line summary`.",
        "",
    ]


def _falsified_branch() -> list[str]:
    return [
        "### §4.B — If FALSIFIED (delete if not applicable)",
        "",
        "Per parent brief §17:",
        "",
        "- [ ] Append one-line row to `docs/rejected_candidates.md` (create file on first entry if missing).",
        "    Format: `YYYY-MM-DD | Q-CORR-1.2 | <selected config_id or NO_CANDIDATE> | FALSIFIED on <gate(s)> | one-line reason`.",
        "- [ ] Do NOT open Q-CORR-1.3 for a fresh grid sweep without **new mechanism evidence** —",
        "    Q-CORR-1 instrument-tightness conclusion stands.",
        "- [ ] If FALSIFIED via Path B *procedural* discipline (catastrophic OOS-before-commit, audit hooks 1-5),",
        "    note that this is a **discipline-falsifier**, NOT a strategy-falsifier; the parameter zone is",
        "    not invalidated and a clean re-run is permissible.",
        "- [ ] If FALSIFIED via **NO_CANDIDATE** at train selection (no config clears §16 floor): document",
        "    which floor each candidate violated (DD/WR/trades) in the closure prose.",
        "",
    ]


def _ambiguous_branch() -> list[str]:
    return [
        "### §4.C — If AMBIGUOUS (delete if not applicable)",
        "",
        "Per parent brief §17:",
        "",
        "- [ ] Document the reasoning in prose: which gate(s) sat in the ambiguous band, what evidence",
        "    would resolve them either way.",
        "- [ ] Next-step decision (pick ONE):",
        "    - [ ] New Pre-Q (Q-CORR-1.3) to investigate the AMBIGUOUS signal directly.",
        "    - [ ] Defer disposition; revisit after live-ops accumulates more comparator data.",
        "    - [ ] Close AMBIGUOUS-CONSERVATIVE (treat as FALSIFIED for action purposes; do not promote).",
        "- [ ] If AMBIGUOUS via correlation gate (ρ ∈ (0.10, 0.15]): note whether the residual is consistent",
        "    with selection-bias (the X′ = 0.10 buffer per §4.1) or signals a real correlation with Gold.",
        "",
    ]


def build_skeleton(
    run_dir: Path,
    *,
    today: date | None = None,
) -> str:
    today = today or date.today()
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    report_path = run_dir / "report.json"
    report = (
        json.loads(report_path.read_text(encoding="utf-8"))
        if report_path.is_file()
        else {"status": "no_report_yet"}
    )

    run_id = manifest.get("run_id", "?")
    grid_hash = manifest.get("grid_hash", "?")
    fold_spec_hash = manifest.get("fold_spec_hash", "?")
    comparator_sha = manifest.get("comparator_csv_sha256", "?")
    bootstrap_seed = manifest.get("bootstrap_seed", "?")
    bootstrap_n_panels = manifest.get("bootstrap_n_panels", "?")
    report_status = report.get("status", "?")
    oos = report.get("oos") or {}
    oos_config_id = oos.get("config_id", "?")
    oos_metrics = oos.get("metrics") or {}
    n_train = report.get("n_train_ingests", "?")
    gates = report.get("gates") or {}

    lines: list[str] = [
        "# Q-CORR-1.2 — Closure Note (DRAFT skeleton)",
        "",
        "**Status:** CLOSED-<DISPOSITION>  ← edit when you finalize the verdict",
        f"**Date:** {today.isoformat()}",
        "**Parent:** [Q-CORR-1.2 brief](Q-CORR-1.2-guardian-family-silver-wfo.md)",
        f"**Run ID:** `{run_id}`",
        f"**Run dir:** `{run_dir.as_posix()}`",
        f"**Report status:** `{report_status}`",
        "",
        "---",
        "",
        "## §1 — Disposition",
        "",
        _DISPOSITION_PLACEHOLDER,
        "",
        "**Reasoning** (1-2 paragraphs explaining which §14 gates drove the verdict, and how this",
        "maps to the §17 closure action below): _fill by hand_",
        "",
        "---",
        "",
        "## §2 — Run metadata",
        "",
        f"- grid_hash: `{grid_hash}`",
        f"- fold_spec_hash: `{fold_spec_hash}`",
        f"- comparator_csv_sha256: `{comparator_sha}`",
        f"- bootstrap_seed / n_panels: `{bootstrap_seed}` / `{bootstrap_n_panels}`",
        f"- OOS config_id: `{oos_config_id}`",
        f"- N train ingests: `{n_train}`",
        "",
        "### OOS metrics (from `report.json`)",
        "",
    ]
    if oos_metrics:
        lines.append("| Metric | Value |")
        lines.append("|---|---|")
        for k, v in oos_metrics.items():
            lines.append(f"| `{k}` | {v} |")
    else:
        lines.append("_No OOS metrics — train-only or stub run._")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## §3 — §14 gate evidence (from `report.json`)")
    lines.append("")
    lines.extend(_format_gate_table(gates))
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## §4 — Closure actions (per parent brief §17)")
    lines.append("")
    lines.append("**Instructions:** keep the sub-section matching your disposition; delete the other two.")
    lines.append("")
    lines.extend(_resolved_branch())
    lines.extend(_falsified_branch())
    lines.extend(_ambiguous_branch())
    lines.append("---")
    lines.append("")
    lines.append("## §5 — Audit-hooks attestation (operator confirms)")
    lines.append("")
    lines.append("- [ ] `git log --follow -- docs/briefs/Q-CORR-1.2-guardian-family-silver-wfo.md`")
    lines.append("    shows LOCK commit unchanged since 2026-05-13.")
    lines.append("- [ ] `grep 'LOCKED' docs/briefs/Q-CORR-1.2-guardian-family-silver-wfo.md` matches.")
    lines.append("- [ ] `python scripts/wfo/grid_hash.py scripts/wfo/examples/grid.json` →")
    lines.append("    `a8fdd34e800f312e6c064a595ee9ae3565472d0da0a0990348e07d28076f85b1`.")
    lines.append("- [ ] `python scripts/wfo/grid_hash.py scripts/wfo/examples/fold_spec.json` →")
    lines.append("    `5591f024515f422548bf9e60a7f23225e559a05346e8911e6397346acad6673e`.")
    lines.append("- [ ] `python scripts/wfo/audit_path_b_ordering.py <run_dir>/run_manifest.json` → PASS.")
    lines.append("- [ ] `python scripts/wfo/run_path_b.py emit-reports --run-dir <run_dir>` reproduces")
    lines.append("    the disposition above.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("_Skeleton generated by `scripts/wfo/closure_note.py`. This file is a starting",
                 )
    lines.append("point — the authoritative closure note is the version Joshua finalizes by hand._")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", type=Path, required=True, help="path B run directory")
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="output path (default: <run_dir>/closure_note_DRAFT.md)",
    )
    args = ap.parse_args()
    run_dir = args.run_dir.resolve()
    if not (run_dir / "run_manifest.json").is_file():
        print(f"ERROR: no run_manifest.json under {run_dir}", file=sys.stderr)
        return 1
    out = args.out or (run_dir / "closure_note_DRAFT.md")
    out.write_text(build_skeleton(run_dir), encoding="utf-8")
    print(f"Wrote closure-note skeleton: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
