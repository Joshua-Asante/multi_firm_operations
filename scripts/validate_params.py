#!/usr/bin/env python3
"""validate_params.py — drift check between config/params.toml and production sources.

`config/params.toml` is a DERIVED MIRROR — NOT canonical. Pine source is
canonical for strategy behavior per Rule 0; `dd_protection.py` /
`firm_rules.py` are canonical for live-sizing constants. This validator
asserts the manifest agrees with those sources.

Hard-fail (exit 1) — manifest disagrees with a current-state source:
  - `dd_protection.py` BASE_RISK dict
  - `dd_protection.py` DD_TRIGGER / DD_SCALE constants
  - `firm_rules.py` _BASE_RISK dict
  - `CLAUDE.md` "Strategy Reference" table
  - Pine source `input.float()` defaults, when Pine files are present locally
    (promoted from WARN on 2026-05-18 after two real drifts surfaced and
    were fixed — DJ30 strategy 0.70→1.00, NAS100 indicator 0.45→0.40).

Warn (exit 0 with warnings) — drift candidate, ratchet to hard-fail per
audit-hooks §10 when warn-count stays at 0 for 5 consecutive runs:
  - `strategies/*/LOCK.md` (only Guardian has one currently)
  - "No Pine files present" status — when ALL Pine files are gitignored on
    this clone (CI / public clone). Absence is not drift.

Excluded by design from hard-fail tier:
  - `docs/adr/*.md` — append-only historical records; old entries CORRECTLY
    contain old values.
  - `strategies/**/_CHANGELOG.md` — same; only Unreleased + most-recent
    entry could meaningfully drift, and the regex cost outweighs the
    benefit for v1.

Exit codes:
  0 — zero hard-fail (warns allowed)
  1 — one or more hard-fail violations
  2 — validator self-test failed (validator is broken; do not trust output)

Usage:
  python scripts/validate_params.py              # self-test then full validation
  python scripts/validate_params.py --self-test-only
  python scripts/validate_params.py --no-self-test
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
import time
import tomllib
from pathlib import Path
from typing import NamedTuple

# Pine v6 `input.float(default, "Label", ...)` and `input.int(default, "Label", ...)`.
# Captures: (1) varname, (2) default value, (3) label string.
INPUT_FLOAT_RE = re.compile(
    r"(\w+)\s*=\s*input\.(?:float|int)\(\s*"
    r"([+-]?\d+(?:\.\d+)?)\s*,\s*"
    r'"([^"]*)"'
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = REPO_ROOT / "config" / "params.toml"
FIXTURES_DIR = REPO_ROOT / "tests" / "validator_fixtures"

# Manifest-key → production-source-key mappings.
# Mirror of `dd_protection.py:BASE_RISK` keys.
STRATEGY_BASE_RISK_KEYS = {
    "guardian_gold_v5_5":  "Guardian",
    "striker_dj30_v4_5":   "Striker",
    "aegis_usdjpy_v4_3":   "Aegis",
    "striker_nas100_v1":   "Striker NAS100",
}

# Mirror of `firm_rules.py:_BASE_RISK` keys.
STRATEGY_FIRM_RULES_KEYS = {
    "guardian_gold_v5_5":  "guardian",
    "striker_dj30_v4_5":   "striker",
    "aegis_usdjpy_v4_3":   "aegis",
    "striker_nas100_v1":   "striker_nas100",
}

# Mirror of CLAUDE.md table column-1 names.
CLAUDE_MD_NAME_MAP = {
    "guardian_gold_v5_5":  "Guardian Gold",
    "striker_dj30_v4_5":   "Striker DJ30",
    "aegis_usdjpy_v4_3":   "Aegis USDJPY",
    "striker_nas100_v1":   "Striker NAS100",
}


class Violation(NamedTuple):
    severity: str  # "HARD" or "WARN"
    location: str
    expected: str
    found: str

    def __str__(self) -> str:
        return f"{self.severity}: {self.location} | manifest expects {self.expected} | found {self.found}"


def _rel(path: Path, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


# ── Manifest loader ────────────────────────────────────────────

def load_manifest(path: Path) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


# ── Python AST helpers ─────────────────────────────────────────

def _parse_python_assign(source: str, var_name: str):
    """Return (node.value, lineno) for top-level `var_name = ...` or None."""
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == var_name:
                    return node.value, node.lineno
    return None


def _eval_constant_dict(node: ast.AST) -> dict | None:
    """Eval an ast.Dict of (Constant -> Constant) safely. Returns None if non-trivial."""
    if not isinstance(node, ast.Dict):
        return None
    out = {}
    for k, v in zip(node.keys, node.values):
        if isinstance(k, ast.Constant) and isinstance(v, ast.Constant):
            out[k.value] = v.value
        else:
            return None
    return out


def _eval_constant_number(node: ast.AST):
    """Eval an ast.Constant numeric. Returns the number or None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    return None


# ── Hard-fail checks ───────────────────────────────────────────

def check_dd_protection_py(manifest: dict, repo_root: Path) -> list[Violation]:
    violations: list[Violation] = []
    pyfile = repo_root / "dd_protection.py"
    if not pyfile.exists():
        violations.append(Violation(
            "HARD", f"{_rel(pyfile, repo_root)}:0",
            "dd_protection.py present", "file missing",
        ))
        return violations
    source = pyfile.read_text(encoding="utf-8")
    rel = _rel(pyfile, repo_root)

    # BASE_RISK dict
    found = _parse_python_assign(source, "BASE_RISK")
    if found is None:
        violations.append(Violation("HARD", f"{rel}:0", "BASE_RISK assignment", "not found"))
    else:
        node, lineno = found
        base_risk = _eval_constant_dict(node)
        if base_risk is None:
            violations.append(Violation(
                "HARD", f"{rel}:{lineno}",
                "BASE_RISK = {{Constant: Constant}}", "non-literal dict",
            ))
        else:
            for manifest_key, py_key in STRATEGY_BASE_RISK_KEYS.items():
                expected_pct = manifest["strategies"][manifest_key]["risk_pct"]
                expected_decimal = expected_pct / 100.0
                if py_key not in base_risk:
                    violations.append(Violation(
                        "HARD", f"{rel}:{lineno} BASE_RISK",
                        f"key '{py_key}' = {expected_decimal}",
                        f"key '{py_key}' missing",
                    ))
                elif abs(base_risk[py_key] - expected_decimal) > 1e-9:
                    violations.append(Violation(
                        "HARD", f"{rel}:{lineno} BASE_RISK['{py_key}']",
                        f"{expected_decimal} (= manifest {expected_pct}%)",
                        f"{base_risk[py_key]}",
                    ))

    # DD_TRIGGER
    found = _parse_python_assign(source, "DD_TRIGGER")
    expected_trigger = manifest["dd_protection"]["trigger_pct"] / 100.0
    if found is None:
        violations.append(Violation("HARD", f"{rel}:0 DD_TRIGGER",
                                    f"{expected_trigger}", "constant not found"))
    else:
        value = _eval_constant_number(found[0])
        if value is None or abs(value - expected_trigger) > 1e-9:
            violations.append(Violation(
                "HARD", f"{rel}:{found[1]} DD_TRIGGER",
                f"{expected_trigger}", str(value),
            ))

    # DD_SCALE
    found = _parse_python_assign(source, "DD_SCALE")
    expected_scale = manifest["dd_protection"]["scale_factor"]
    if found is None:
        violations.append(Violation("HARD", f"{rel}:0 DD_SCALE",
                                    f"{expected_scale}", "constant not found"))
    else:
        value = _eval_constant_number(found[0])
        if value is None or abs(value - expected_scale) > 1e-9:
            violations.append(Violation(
                "HARD", f"{rel}:{found[1]} DD_SCALE",
                f"{expected_scale}", str(value),
            ))

    return violations


def check_firm_rules_py(manifest: dict, repo_root: Path) -> list[Violation]:
    violations: list[Violation] = []
    pyfile = repo_root / "firm_rules.py"
    if not pyfile.exists():
        violations.append(Violation(
            "HARD", f"{_rel(pyfile, repo_root)}:0",
            "firm_rules.py present", "file missing",
        ))
        return violations
    source = pyfile.read_text(encoding="utf-8")
    rel = _rel(pyfile, repo_root)

    found = _parse_python_assign(source, "_BASE_RISK")
    if found is None:
        violations.append(Violation("HARD", f"{rel}:0", "_BASE_RISK assignment", "not found"))
        return violations
    node, lineno = found
    base_risk = _eval_constant_dict(node)
    if base_risk is None:
        violations.append(Violation(
            "HARD", f"{rel}:{lineno}",
            "_BASE_RISK = {{Constant: Constant}}", "non-literal dict",
        ))
        return violations
    for manifest_key, py_key in STRATEGY_FIRM_RULES_KEYS.items():
        expected_pct = manifest["strategies"][manifest_key]["risk_pct"]
        expected_decimal = expected_pct / 100.0
        if py_key not in base_risk:
            violations.append(Violation(
                "HARD", f"{rel}:{lineno} _BASE_RISK",
                f"key '{py_key}' = {expected_decimal}",
                f"key '{py_key}' missing",
            ))
        elif abs(base_risk[py_key] - expected_decimal) > 1e-9:
            violations.append(Violation(
                "HARD", f"{rel}:{lineno} _BASE_RISK['{py_key}']",
                f"{expected_decimal} (= manifest {expected_pct}%)",
                f"{base_risk[py_key]}",
            ))
    return violations


def _parse_claude_md_strategy_table(text: str) -> dict[str, tuple[int, list[str]]]:
    """Find the Strategy Reference markdown table; return {name: (lineno, [cells])}."""
    out: dict[str, tuple[int, list[str]]] = {}
    lines = text.splitlines()
    in_table = False
    header_seen = False
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped.startswith("|"):
            if in_table:
                in_table = False
                header_seen = False
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not cells:
            continue
        if not in_table:
            if cells[0].lower().startswith("strategy"):
                in_table = True
                header_seen = False
                continue
        else:
            if not header_seen and cells[0].startswith("-"):
                header_seen = True
                continue
            if header_seen:
                name = cells[0]
                if name and not name.startswith("-"):
                    out[name] = (i, cells)
    return out


def check_claude_md(manifest: dict, repo_root: Path) -> list[Violation]:
    violations: list[Violation] = []
    md = repo_root / "CLAUDE.md"
    if not md.exists():
        violations.append(Violation(
            "HARD", f"{_rel(md, repo_root)}:0",
            "CLAUDE.md present", "file missing",
        ))
        return violations
    text = md.read_text(encoding="utf-8")
    rel = _rel(md, repo_root)
    table = _parse_claude_md_strategy_table(text)
    for manifest_key, claude_name in CLAUDE_MD_NAME_MAP.items():
        expected_pct = manifest["strategies"][manifest_key]["risk_pct"]
        expected_cv = manifest["strategies"][manifest_key]["contract_value"]
        if claude_name not in table:
            violations.append(Violation(
                "HARD", f"{rel} (Strategy table)",
                f"row '{claude_name}'", "row missing",
            ))
            continue
        lineno, cells = table[claude_name]
        # Expected cell layout: [Strategy, Instrument/TF, Risk/trade, Version, contractValue]
        if len(cells) < 5:
            violations.append(Violation(
                "HARD", f"{rel}:{lineno}",
                f"5+ columns for '{claude_name}'", f"{len(cells)} cols",
            ))
            continue
        risk_cell = cells[2]
        cv_cell = cells[4]
        # Risk: look for "<float>%" prefix in the cell.
        risk_num = _extract_leading_pct(risk_cell)
        if risk_num is None or abs(risk_num - expected_pct) > 0.001:
            violations.append(Violation(
                "HARD", f"{rel}:{lineno}",
                f"{claude_name} risk={expected_pct}%",
                f"'{risk_cell}'",
            ))
        # contractValue: int or "default (1)".
        cv_num = _extract_contract_value(cv_cell)
        if cv_num is None:
            violations.append(Violation(
                "HARD", f"{rel}:{lineno}",
                f"{claude_name} contractValue={expected_cv}",
                f"'{cv_cell}' (unparseable)",
            ))
        elif cv_num != expected_cv:
            violations.append(Violation(
                "HARD", f"{rel}:{lineno}",
                f"{claude_name} contractValue={expected_cv}",
                f"{cv_num} ('{cv_cell}')",
            ))
    return violations


def _extract_leading_pct(cell: str) -> float | None:
    """Extract leading '<float>%' from a cell. Returns float or None."""
    s = cell.strip()
    # Strip markdown bold
    while s.startswith("*"):
        s = s[1:]
    s = s.strip()
    # Match leading number followed by %
    i = 0
    while i < len(s) and (s[i].isdigit() or s[i] == "."):
        i += 1
    if i == 0:
        return None
    if i < len(s) and s[i] == "%":
        try:
            return float(s[:i])
        except ValueError:
            return None
    return None


def _extract_contract_value(cell: str) -> int | None:
    """Extract contractValue from a CLAUDE.md cell. Handles:
       '100', '**10** (critical — ...)', 'default (1)'."""
    # Strip markdown bold up front so the cell-starts-with check is reliable.
    s = cell.replace("**", "").strip()
    # 'default (1)' style — cell STARTS with 'default', then the int is in parens.
    if s.lower().startswith("default"):
        for tok in s.replace("(", " ").replace(")", " ").split():
            if tok.isdigit():
                return int(tok)
        return None
    # Otherwise pick the leading integer (parenthetical 'default of 1' is ignored).
    i = 0
    while i < len(s) and s[i].isdigit():
        i += 1
    if i == 0:
        return None
    try:
        return int(s[:i])
    except ValueError:
        return None


# ── Warn-tier checks ───────────────────────────────────────────

def check_lock_md(manifest: dict, repo_root: Path) -> list[Violation]:
    """Strategy LOCK.md drift (warn-only initially). Currently only Guardian
    has a LOCK.md. Looks for the risk_pct claim line."""
    violations: list[Violation] = []
    for manifest_key, strat in manifest["strategies"].items():
        lock_md = strat.get("lock_md")
        if not lock_md:
            continue
        path = repo_root / lock_md
        if not path.exists():
            # LOCK.md declared in manifest but not present — warn
            violations.append(Violation(
                "WARN", f"{lock_md}:0",
                "LOCK.md present", "file missing",
            ))
            continue
        text = path.read_text(encoding="utf-8")
        rel = _rel(path, repo_root)
        expected_pct = strat["risk_pct"]
        # Look for `risk_pct = expected_pct%` or `risk N.NN%` style.
        # The Guardian LOCK.md says `**Risk per trade:** 0.34% (...)` and `risk 0.34%` in the config block.
        # Tight pattern: find any line that mentions "risk" + "N.NN%". Compare; warn if disagrees.
        expected_token = f"{expected_pct:.2f}%"
        found_disagreement = False
        for lineno, line in enumerate(text.splitlines(), start=1):
            low = line.lower()
            if "risk" in low and "%" in line:
                # Pull all "N.NN%" tokens
                for tok in _extract_pct_tokens(line):
                    if abs(tok - expected_pct) > 0.001:
                        violations.append(Violation(
                            "WARN", f"{rel}:{lineno}",
                            f"{manifest_key} risk={expected_token}",
                            f"line mentions {tok}%",
                        ))
                        found_disagreement = True
        # No-disagreement is normal; nothing to report.
        _ = found_disagreement  # silence linter
    return violations


def _extract_pct_tokens(line: str) -> list[float]:
    """Extract all `<float>%` tokens from a line."""
    out: list[float] = []
    i = 0
    while i < len(line):
        c = line[i]
        if c.isdigit():
            j = i
            while j < len(line) and (line[j].isdigit() or line[j] == "."):
                j += 1
            if j < len(line) and line[j] == "%":
                try:
                    out.append(float(line[i:j]))
                except ValueError:
                    pass
                i = j + 1
                continue
            i = j
        else:
            i += 1
    return out


def _resolve_pine_targets(repo_root: Path, pine_path: str) -> list[Path]:
    """Return ALL Pine files to check for one strategy: the canonical
    strategy file at `pine_path` (if present) AND the `_indicator.pine`
    sibling (if present). Both must agree with the manifest — surfacing
    research-mode drift that creeps into one file but not the other
    (observed 2026-05-18: NAS100 strategy at 0.37, indicator at 0.45,
    locked value 0.40 — three different numbers for the same param)."""
    targets: list[Path] = []
    primary = repo_root / pine_path
    if primary.exists():
        targets.append(primary)
    if pine_path.endswith(".pine"):
        indicator = repo_root / (pine_path[:-5] + "_indicator.pine")
        if indicator.exists():
            targets.append(indicator)
    return targets


def check_pine_opportunistic(manifest: dict, repo_root: Path) -> list[Violation]:
    """Pine source is gitignored. If files are present locally (Joshua's box),
    parse `input.float()` declarations and compare risk-related defaults
    against the manifest. Falls back to `_indicator.pine` when the strategy
    file is absent. Emits a single WARN noting the skip when no Pine
    is reachable for any declared strategy."""
    violations: list[Violation] = []
    pine_files_expected = 0
    pine_files_seen = 0
    for manifest_key, strat in manifest["strategies"].items():
        pine_path = strat.get("pine_path")
        if not pine_path:
            continue
        pine_files_expected += 1
        targets = _resolve_pine_targets(repo_root, pine_path)
        if not targets:
            continue
        pine_files_seen += 1
        expected_pct = strat["risk_pct"]
        for target in targets:
            text = target.read_text(encoding="utf-8", errors="replace")
            rel = _rel(target, repo_root)
            risk_inputs_seen = 0
            for m in INPUT_FLOAT_RE.finditer(text):
                varname, default_str, label = m.group(1), m.group(2), m.group(3)
                is_risk = "risk" in varname.lower() or "risk" in label.lower()
                if not is_risk:
                    continue
                risk_inputs_seen += 1
                try:
                    default = float(default_str)
                except ValueError:
                    continue
                line_no = text[:m.start()].count("\n") + 1
                if abs(default - expected_pct) > 0.001:
                    violations.append(Violation(
                        "HARD", f"{rel}:{line_no}",
                        f"{manifest_key} risk_pct={expected_pct}",
                        f"input.float default={default} ('{label}')",
                    ))
            if risk_inputs_seen == 0:
                violations.append(Violation(
                    "HARD", f"{rel}:0",
                    f"{manifest_key} risk input.float present",
                    "no risk-labeled input.float() found",
                ))
    if pine_files_expected > 0 and pine_files_seen == 0:
        violations.append(Violation(
            "WARN", "(Pine source)",
            "opportunistic Pine grep",
            "no Pine files present (gitignored on this clone)",
        ))
    return violations


# ── Top-level run ──────────────────────────────────────────────

def run_validation(manifest_path: Path, repo_root: Path) -> tuple[list[Violation], list[Violation]]:
    """Run all checks. Returns (hard_violations, warn_violations)."""
    manifest = load_manifest(manifest_path)
    all_v: list[Violation] = []
    all_v.extend(check_dd_protection_py(manifest, repo_root))
    all_v.extend(check_firm_rules_py(manifest, repo_root))
    all_v.extend(check_claude_md(manifest, repo_root))
    all_v.extend(check_lock_md(manifest, repo_root))
    all_v.extend(check_pine_opportunistic(manifest, repo_root))
    hard = [v for v in all_v if v.severity == "HARD"]
    warn = [v for v in all_v if v.severity == "WARN"]
    return hard, warn


def emit_report(hard: list[Violation], warn: list[Violation], elapsed_ms: float) -> int:
    """Print violations + summary. Return exit code (0 or 1)."""
    for v in hard:
        print(str(v))
    for v in warn:
        print(str(v))
    print()
    print(f"Summary: {len(hard)} HARD violation(s), {len(warn)} WARN violation(s)")
    print(f"Runtime: {elapsed_ms:.1f} ms")
    return 1 if hard else 0


# ── Self-test ──────────────────────────────────────────────────

def _self_test(verbose: bool = False) -> int:
    """Run validator on fixture pair. Returns 0 if both fixtures behave as expected."""
    good = FIXTURES_DIR / "good"
    bad = FIXTURES_DIR / "bad"
    if not good.is_dir() or not bad.is_dir():
        print(f"VALIDATOR SELF-TEST FAILED — fixture dirs missing at {FIXTURES_DIR}",
              file=sys.stderr)
        return 2

    # Good fixture: zero hard violations expected.
    hard_g, warn_g = run_validation(good / "params.toml", good)
    if hard_g:
        print("VALIDATOR SELF-TEST FAILED — good fixture produced HARD violations:",
              file=sys.stderr)
        for v in hard_g:
            print(f"  {v}", file=sys.stderr)
        return 2

    # Bad fixture: at least 2 hard violations expected (one Python-source mismatch,
    # one CLAUDE.md mismatch).
    hard_b, warn_b = run_validation(bad / "params.toml", bad)
    if len(hard_b) < 2:
        print(
            f"VALIDATOR SELF-TEST FAILED — bad fixture produced only {len(hard_b)} HARD "
            f"violation(s); expected >=2 (seeded: dd_protection.py mismatch + CLAUDE.md mismatch)",
            file=sys.stderr,
        )
        for v in hard_b:
            print(f"  {v}", file=sys.stderr)
        return 2

    # Confirm we hit both seeded paths.
    locations = " ".join(v.location for v in hard_b)
    if "dd_protection.py" not in locations:
        print("VALIDATOR SELF-TEST FAILED — bad fixture missing dd_protection.py violation",
              file=sys.stderr)
        return 2
    if "CLAUDE.md" not in locations:
        print("VALIDATOR SELF-TEST FAILED — bad fixture missing CLAUDE.md violation",
              file=sys.stderr)
        return 2

    if verbose:
        print(f"Self-test OK (good: 0 hard / {len(warn_g)} warn; "
              f"bad: {len(hard_b)} hard / {len(warn_b)} warn)")
    return 0


# ── CLI ────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST,
                        help="path to params.toml (default: config/params.toml)")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT,
                        help="root path for production-source lookup")
    parser.add_argument("--self-test-only", action="store_true",
                        help="run self-test, then exit (no real-repo validation)")
    parser.add_argument("--no-self-test", action="store_true",
                        help="skip self-test (CI debug only)")
    args = parser.parse_args()

    # Self-test always runs first unless --no-self-test.
    if not args.no_self_test:
        rc = _self_test(verbose=args.self_test_only)
        if rc != 0:
            print("Self-test failed — validator is broken, fix before trusting output.",
                  file=sys.stderr)
            return 2
        if args.self_test_only:
            return 0

    if not args.manifest.exists():
        print(f"manifest not found: {args.manifest}", file=sys.stderr)
        return 1

    t0 = time.perf_counter()
    hard, warn = run_validation(args.manifest, args.repo_root)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return emit_report(hard, warn, elapsed_ms)


if __name__ == "__main__":
    sys.exit(main())
