#!/usr/bin/env python3
"""Path B WFO orchestration entry.

Commands:
  init-run      -- write run directory skeleton + manifest template from grid/fold specs.
  ingest        -- validate Silver §16 filename, TV schema, dedupe sha256, metrics -> manifest.
                   --csv accepts either a single CSV path or a directory (batch mode).
  select        -- §16 train selection ladder + train_selection_lock.json + manifest fold.
  emit-reports  -- write report.md + report.json; auto-evaluate §14 gates when OOS present
                   (disposition verdict printed to stdout per Q-CORR-1.2 handoff §5.8).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

_WFO_DIR = Path(__file__).resolve().parent
if str(_WFO_DIR) not in sys.path:
    sys.path.insert(0, str(_WFO_DIR))

from grid_hash import fold_spec_hash_from_path, grid_hash_from_path

from report import emit_reports


def _ensure_wfo_path() -> None:
    if str(_WFO_DIR) not in sys.path:
        sys.path.insert(0, str(_WFO_DIR))


def cmd_init_run(args: argparse.Namespace) -> int:
    run_dir = Path(args.out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    gh = grid_hash_from_path(args.grid)
    fh = fold_spec_hash_from_path(args.fold_spec)
    manifest = {
        "run_id": args.run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "grid_path": str(Path(args.grid).resolve()),
        "grid_hash": gh,
        "fold_spec_path": str(Path(args.fold_spec).resolve()),
        "fold_spec_hash": fh,
        "comparator_csv_sha256": args.comparator_sha256,
        "seed": int(args.seed),
        "bootstrap_seed": int(args.bootstrap_seed),
        "bootstrap_n_panels": int(args.bootstrap_n_panels),
        "folds": [],
        "ingests": [],
    }
    (run_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    shutil.copy(args.grid, run_dir / "grid.json")
    shutil.copy(args.fold_spec, run_dir / "fold_spec.json")
    emit_reports(run_dir)
    print(f"Wrote {run_dir / 'run_manifest.json'}")
    return 0


def cmd_emit_reports(args: argparse.Namespace) -> int:
    comparator_dir = Path(args.comparator_dir) if args.comparator_dir else None
    result = emit_reports(args.run_dir, comparator_dir=comparator_dir)
    print(f"Wrote reports under {args.run_dir}")
    if result.get("mode") == "full":
        print(f"\nDISPOSITION: {result['disposition']}")
        return 0 if result["disposition"] == "RESOLVED" else 2
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    _ensure_wfo_path()
    import operations  # noqa: E402

    csv_path = Path(args.csv)
    run_dir = Path(args.run_dir)
    if csv_path.is_dir():
        rows = []
        files = sorted(csv_path.glob("*.csv"))
        if not files:
            print(json.dumps({"batch_count": 0, "rows": []}, indent=2))
            return 1
        for f in files:
            row = operations.ingest_tv_csv(
                run_dir,
                f,
                min_raw_rows=args.min_raw_rows,
                min_trades=args.min_trades,
                max_trades=args.max_trades,
                notional=args.notional,
                validate_grid=not args.skip_grid_validate,
            )
            rows.append(row)
        print(json.dumps({"batch_count": len(rows), "rows": rows}, indent=2, default=str))
        return 0

    row = operations.ingest_tv_csv(
        run_dir,
        csv_path,
        min_raw_rows=args.min_raw_rows,
        min_trades=args.min_trades,
        max_trades=args.max_trades,
        notional=args.notional,
        validate_grid=not args.skip_grid_validate,
    )
    print(json.dumps(row, indent=2, default=str))
    return 0


def cmd_select(args: argparse.Namespace) -> int:
    _ensure_wfo_path()
    import operations  # noqa: E402

    try:
        out = operations.select_train_fold(Path(args.run_dir), fold_id=str(args.fold_id))
    except ValueError as e:
        print(json.dumps({"selection_status": "ERROR", "message": str(e)}, indent=2))
        return 1
    print(json.dumps(out, indent=2, default=str))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init-run", help="create run_manifest.json + copy specs")
    p_init.add_argument("--run-id", required=True)
    p_init.add_argument("--grid", type=Path, required=True)
    p_init.add_argument("--fold-spec", type=Path, required=True)
    p_init.add_argument("--out-dir", type=Path, required=True)
    p_init.add_argument(
        "--comparator-sha256",
        required=True,
        help="64-char sha256 of comparator Guardian Gold CSV (from SHA256SUMS)",
    )
    p_init.add_argument("--seed", type=int, default=42)
    p_init.add_argument(
        "--bootstrap-seed",
        type=int,
        default=42,
        help=(
            "Canonical RNG seed for §14 Gate 9 regime bootstrap (orchestration "
            "metadata, not gate definition). Recorded in manifest at init-run; "
            "Gate 9 disposition uses these values for reproducibility."
        ),
    )
    p_init.add_argument(
        "--bootstrap-n-panels",
        type=int,
        default=1000,
        help="Canonical n_panels for §14 Gate 9 regime bootstrap (orchestration metadata).",
    )

    p_rep = sub.add_parser("emit-reports", help="write report.md + report.json; §14 if OOS present")
    p_rep.add_argument("--run-dir", type=Path, required=True)
    p_rep.add_argument(
        "--comparator-dir",
        type=Path,
        default=None,
        help="directory containing comparator CSV + SHA256SUMS (default: data/tv_exports/pepperstone/ under repo root)",
    )

    p_ing = sub.add_parser("ingest", help="ingest one TV CSV (or a directory) into run manifest")
    p_ing.add_argument("--run-dir", type=Path, required=True)
    p_ing.add_argument(
        "--csv",
        type=Path,
        required=True,
        help="path to a single CSV, or to a directory containing *.csv files (batch ingest, alphabetical order)",
    )
    p_ing.add_argument("--min-raw-rows", type=int, default=100)
    p_ing.add_argument("--min-trades", type=int, default=10)
    p_ing.add_argument("--max-trades", type=int, default=5000)
    p_ing.add_argument("--notional", type=float, default=200_000.0)
    p_ing.add_argument(
        "--skip-grid-validate",
        action="store_true",
        help="skip tunable_dimensions membership check (not for production)",
    )

    p_sel = sub.add_parser("select", help="train-fold selection + lock file (§16)")
    p_sel.add_argument("--run-dir", type=Path, required=True)
    p_sel.add_argument("--fold-id", type=str, default="1")

    args = ap.parse_args()
    if args.cmd == "init-run":
        return cmd_init_run(args)
    if args.cmd == "emit-reports":
        return cmd_emit_reports(args)
    if args.cmd == "ingest":
        return cmd_ingest(args)
    if args.cmd == "select":
        return cmd_select(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
