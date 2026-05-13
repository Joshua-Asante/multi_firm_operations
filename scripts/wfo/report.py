"""Emit markdown + JSON summary for a Path B run directory."""
from __future__ import annotations

import json
from pathlib import Path


def emit_reports(run_dir: str | Path) -> None:
    run_dir = Path(run_dir)
    manifest_path = run_dir / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = {
        "run_id": manifest.get("run_id"),
        "grid_hash": manifest.get("grid_hash"),
        "fold_spec_hash": manifest.get("fold_spec_hash"),
        "status": "stub_no_metrics",
    }
    (run_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        f"# WFO run {report['run_id']}",
        "",
        f"- grid_hash: `{report['grid_hash']}`",
        f"- fold_spec_hash: `{report['fold_spec_hash']}`",
        "",
        "_Metrics aggregation not yet executed for this stub run._",
        "",
    ]
    (run_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")
