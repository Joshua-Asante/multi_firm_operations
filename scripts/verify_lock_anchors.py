#!/usr/bin/env python3
"""
verify_lock_anchors — doc/code skew checker for prop_firm_pipeline.

Reads `CLAUDE.md`, `firm_rules.py`, and `dd_protection.py` as text (no imports,
to avoid tripping the `_validate_protection_rule` spec pin during a skew check).
Cross-references the locked anchors and routes per
docs/methodology/observation_routing.md:

    Closed   — all anchors aligned. Logs a 0-day window per Rule 6 fallback.
    Action   — drift between CLAUDE.md and code. Prints unified diff for human.
    Forward  — re-MC trigger fired (allocation outside G 0.30-0.34% safe band,
               or any dd_protection constant moved). Prints trigger + suggested
               re-MC invocation; never auto-runs.

Always exits 0 (advisory). Idempotent. Run inline with a lock event per Rule 6.
"""
from __future__ import annotations

import difflib
import re
import sys
from datetime import date
from pathlib import Path

# --------------------------------------------------------------------------
# Locked reference values (the contract this script enforces).
#
# These literals match the 2026-04-23 lock. Any drift in code or CLAUDE.md is
# what we are trying to detect. Updating these values is itself a lock event
# and must be paired with a re-MC.
# --------------------------------------------------------------------------

LOCKED_RISK = {
    "guardian": 0.0034,
    "striker":  0.0100,
    "aegis":    0.0150,
}
LOCKED_VERSIONS = {
    "guardian": "v5.5",
    "striker":  "v4.4",
    "aegis":    "v4.3",
}
LOCKED_DD_TRIGGER = 0.010
LOCKED_DD_SCALE = 0.40

# Guardian risk safe band — outside this band fires Forward (re-MC required).
GUARDIAN_SAFE_BAND = (0.0030, 0.0034)

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
FIRM_RULES = REPO_ROOT / "firm_rules.py"
DD_PROTECTION = REPO_ROOT / "dd_protection.py"
SKEW_AUDIT_DIR = REPO_ROOT / "analysis" / "skew_audit"


# --------------------------------------------------------------------------
# Parsing — read files as text. No imports of the modules being checked.
# --------------------------------------------------------------------------

def parse_firm_rules(text: str) -> dict:
    """Extract `RISK_TIERS["challenge"]` allocation."""
    block = re.search(
        r'"challenge"\s*:\s*\{([^}]*)\}', text, re.DOTALL,
    )
    if not block:
        raise SystemExit("firm_rules.py: could not locate RISK_TIERS['challenge'] block")
    out = {}
    for name in ("guardian", "striker", "aegis"):
        m = re.search(rf'"{name}"\s*:\s*([0-9.]+)', block.group(1))
        if not m:
            raise SystemExit(f"firm_rules.py: missing risk for {name}")
        out[name] = float(m.group(1))
    return out


def parse_dd_protection(text: str) -> dict:
    """Extract DD_TRIGGER, DD_SCALE, and BASE_RISK."""
    out = {}
    m = re.search(r'^DD_TRIGGER\s*=\s*([0-9.]+)', text, re.MULTILINE)
    if not m:
        raise SystemExit("dd_protection.py: DD_TRIGGER not found")
    out["DD_TRIGGER"] = float(m.group(1))

    m = re.search(r'^DD_SCALE\s*=\s*([0-9.]+)', text, re.MULTILINE)
    if not m:
        raise SystemExit("dd_protection.py: DD_SCALE not found")
    out["DD_SCALE"] = float(m.group(1))

    block = re.search(r'BASE_RISK\s*=\s*\{([^}]*)\}', text, re.DOTALL)
    if not block:
        raise SystemExit("dd_protection.py: BASE_RISK block not found")
    base_risk = {}
    for label, key in (("Guardian", "guardian"), ("Striker", "striker"), ("Aegis", "aegis")):
        m = re.search(rf'"{label}"\s*:\s*([0-9.]+)', block.group(1))
        if not m:
            raise SystemExit(f"dd_protection.py: missing BASE_RISK for {label}")
        base_risk[key] = float(m.group(1))
    out["BASE_RISK"] = base_risk
    return out


def parse_claude_md(text: str) -> dict:
    """Extract anchors from CLAUDE.md.

    Three sources are checked:
    1. Multiplier System line ('Guardian X%, Striker Y%, Aegis Z%')
    2. Strategy Reference table rows (risk + version)
    3. Protection section (DD trigger threshold + scale factor)
    """
    out = {"multiplier_risk": {}, "table_risk": {}, "table_version": {}}

    # 1. Multiplier System line
    m = re.search(
        r"Baseline risk = current locked risk "
        r"\(Guardian ([0-9.]+)%, Striker ([0-9.]+)%, Aegis ([0-9.]+)%\)",
        text,
    )
    if not m:
        raise SystemExit("CLAUDE.md: could not parse Multiplier System baseline-risk line")
    out["multiplier_risk"] = {
        "guardian": float(m.group(1)) / 100.0,
        "striker":  float(m.group(2)) / 100.0,
        "aegis":    float(m.group(3)) / 100.0,
    }

    # 2. Strategy Reference table rows. Match each strategy line.
    for label, key in (("Guardian Gold", "guardian"), ("Striker DJ30", "striker"), ("Aegis USDJPY", "aegis")):
        # Row: | <name> | <inst> | <risk>% [optional parenthetical] | <version> LOCKED | ...
        m = re.search(
            rf"\|\s*{re.escape(label)}\s*\|[^|]+\|\s*([0-9.]+)%[^|]*\|\s*(v[0-9.]+)\s+LOCKED\s*\|",
            text,
        )
        if not m:
            raise SystemExit(f"CLAUDE.md: could not parse Strategy Reference row for {label}")
        out["table_risk"][key] = float(m.group(1)) / 100.0
        out["table_version"][key] = m.group(2)

    # 3. Protection — DD tier rule with trigger + scale.
    m = re.search(
        r"\(equity - peak\) / peak <= -([0-9.]+)`,\s*multiply day's sizing by ([0-9.]+)",
        text,
    )
    if not m:
        raise SystemExit("CLAUDE.md: could not parse Protection DD-tier rule line")
    out["dd_trigger"] = float(m.group(1))
    out["dd_scale"] = float(m.group(2))

    return out


# --------------------------------------------------------------------------
# Routing logic — Closed / Action / Forward.
# --------------------------------------------------------------------------

def _eq(a: float, b: float, places: int = 6) -> bool:
    """Float equality with rounding to N decimal places.

    CLAUDE.md anchors are written as percentages with 2 fractional digits
    (e.g. 0.34%) and parsed by dividing by 100, which can produce IEEE 754
    binary artifacts like 0.0034000000000000002. Comparisons against the
    code-side decimal literals (0.0034) need a small tolerance.
    """
    return round(a, places) == round(b, places)


def routing(claude: dict, firm: dict, dd: dict) -> tuple[str, list[str], list[str]]:
    """Return (route, drift_lines, forward_lines).

    Order:
    1. Forward triggers first (re-MC required) — supersedes Action.
    2. Action drift between doc and code.
    3. Closed — all aligned.
    """
    forward = []
    drift = []

    # ---- Forward triggers ------------------------------------------------
    g_risk = firm["guardian"]
    g_lo, g_hi = GUARDIAN_SAFE_BAND
    if not (round(g_lo, 6) <= round(g_risk, 6) <= round(g_hi, 6)):
        forward.append(
            f"Guardian risk {g_risk:.4f} outside safe band "
            f"[{g_lo:.4f}, {g_hi:.4f}] (firm_rules.py)"
        )
    if not _eq(dd["DD_TRIGGER"], LOCKED_DD_TRIGGER):
        forward.append(
            f"dd_protection.DD_TRIGGER moved {LOCKED_DD_TRIGGER} -> {dd['DD_TRIGGER']}"
        )
    if not _eq(dd["DD_SCALE"], LOCKED_DD_SCALE):
        forward.append(
            f"dd_protection.DD_SCALE moved {LOCKED_DD_SCALE} -> {dd['DD_SCALE']}"
        )

    # Per-strategy code-vs-locked risk drift -> Forward (any change to
    # allocation that is not already covered by Guardian's narrow safe-band
    # check above is itself a re-MC trigger).
    for k in ("striker", "aegis"):
        if not _eq(firm[k], LOCKED_RISK[k]):
            forward.append(f"firm_rules {k} moved {LOCKED_RISK[k]} -> {firm[k]}")

    # ---- Action: code-vs-doc drift --------------------------------------
    # firm_rules vs dd_protection (must agree internally first)
    for k in ("guardian", "striker", "aegis"):
        if not _eq(firm[k], dd["BASE_RISK"][k]):
            drift.append(
                f"code-vs-code: firm_rules.{k}={firm[k]} != "
                f"dd_protection.BASE_RISK[{k!r}]={dd['BASE_RISK'][k]}"
            )

    # CLAUDE.md vs code: Multiplier System risk numbers
    for k in ("guardian", "striker", "aegis"):
        if not _eq(claude["multiplier_risk"][k], firm[k]):
            drift.append(
                f"CLAUDE.md Multiplier System {k}={claude['multiplier_risk'][k]} "
                f"!= firm_rules.{k}={firm[k]}"
            )

    # CLAUDE.md table risk numbers
    for k in ("guardian", "striker", "aegis"):
        if not _eq(claude["table_risk"][k], firm[k]):
            drift.append(
                f"CLAUDE.md Strategy Reference {k}={claude['table_risk'][k]} "
                f"!= firm_rules.{k}={firm[k]}"
            )

    # CLAUDE.md table versions vs locked literals (no code anchor for version,
    # so this catches doc-side drift only — useful retroactively when CLAUDE.md
    # falls behind a Pine version bump).
    for k in ("guardian", "striker", "aegis"):
        if claude["table_version"][k] != LOCKED_VERSIONS[k]:
            drift.append(
                f"CLAUDE.md Strategy Reference {k} version="
                f"{claude['table_version'][k]} != locked={LOCKED_VERSIONS[k]}"
            )

    # CLAUDE.md Protection rule vs dd_protection constants
    if not _eq(claude["dd_trigger"], dd["DD_TRIGGER"]):
        drift.append(
            f"CLAUDE.md Protection trigger={claude['dd_trigger']} "
            f"!= dd_protection.DD_TRIGGER={dd['DD_TRIGGER']}"
        )
    if not _eq(claude["dd_scale"], dd["DD_SCALE"]):
        drift.append(
            f"CLAUDE.md Protection scale={claude['dd_scale']} "
            f"!= dd_protection.DD_SCALE={dd['DD_SCALE']}"
        )

    if forward:
        return "Forward", drift, forward
    if drift:
        return "Action", drift, forward
    return "Closed", drift, forward


# --------------------------------------------------------------------------
# Output — print + append to analysis/skew_audit/<date>.md.
# --------------------------------------------------------------------------

def render_action_diff(claude: dict, firm: dict, dd: dict) -> str:
    """Build a small CLAUDE.md draft using current code values, then diff
    against the live CLAUDE.md anchors. The diff is what a human would apply.
    """
    current = (
        f"Multiplier System: Guardian {claude['multiplier_risk']['guardian']*100:.2f}%, "
        f"Striker {claude['multiplier_risk']['striker']*100:.2f}%, "
        f"Aegis {claude['multiplier_risk']['aegis']*100:.2f}%\n"
        f"Strategy Reference Guardian: {claude['table_risk']['guardian']*100:.2f}% / "
        f"{claude['table_version']['guardian']}\n"
        f"Strategy Reference Striker: {claude['table_risk']['striker']*100:.2f}% / "
        f"{claude['table_version']['striker']}\n"
        f"Strategy Reference Aegis: {claude['table_risk']['aegis']*100:.2f}% / "
        f"{claude['table_version']['aegis']}\n"
        f"Protection trigger={claude['dd_trigger']} scale={claude['dd_scale']}\n"
    )
    proposed = (
        f"Multiplier System: Guardian {firm['guardian']*100:.2f}%, "
        f"Striker {firm['striker']*100:.2f}%, "
        f"Aegis {firm['aegis']*100:.2f}%\n"
        f"Strategy Reference Guardian: {firm['guardian']*100:.2f}% / "
        f"{LOCKED_VERSIONS['guardian']}\n"
        f"Strategy Reference Striker: {firm['striker']*100:.2f}% / "
        f"{LOCKED_VERSIONS['striker']}\n"
        f"Strategy Reference Aegis: {firm['aegis']*100:.2f}% / "
        f"{LOCKED_VERSIONS['aegis']}\n"
        f"Protection trigger={dd['DD_TRIGGER']} scale={dd['DD_SCALE']}\n"
    )
    diff = difflib.unified_diff(
        current.splitlines(keepends=True),
        proposed.splitlines(keepends=True),
        fromfile="CLAUDE.md (current)",
        tofile="CLAUDE.md (aligned to code)",
        n=0,
    )
    return "".join(diff)


def append_audit_log(route: str, drift: list[str], forward: list[str]) -> Path:
    SKEW_AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    log = SKEW_AUDIT_DIR / f"{date.today().isoformat()}.md"
    line_parts = [f"- {date.today().isoformat()}T_run: {route}"]
    if forward:
        line_parts.append(" | forward: " + "; ".join(forward))
    if drift:
        line_parts.append(" | drift: " + "; ".join(drift))
    with log.open("a", encoding="utf-8") as f:
        f.write("".join(line_parts) + "\n")
    return log


# --------------------------------------------------------------------------
# Main.
# --------------------------------------------------------------------------

def main() -> int:
    for p in (CLAUDE_MD, FIRM_RULES, DD_PROTECTION):
        if not p.exists():
            print(f"missing required file: {p}", file=sys.stderr)
            return 0  # advisory only — never break the caller

    claude = parse_claude_md(CLAUDE_MD.read_text(encoding="utf-8"))
    firm = parse_firm_rules(FIRM_RULES.read_text(encoding="utf-8"))
    dd = parse_dd_protection(DD_PROTECTION.read_text(encoding="utf-8"))

    route, drift, forward = routing(claude, firm, dd)
    log_path = append_audit_log(route, drift, forward)

    print(f"verify_lock_anchors -> {route}")
    if forward:
        print()
        print("FORWARD (re-MC required):")
        for line in forward:
            print(f"  - {line}")
        print()
        print("Suggested re-MC invocation (run manually after addressing trigger):")
        print("  python portfolio_mc.py")
        print()
        print("Do NOT auto-run. Re-MC results must be reviewed and the lock decision")
        print("must be re-authored before updating CLAUDE.md anchors.")
    elif drift:
        print()
        print("ACTION (code-vs-doc drift):")
        for line in drift:
            print(f"  - {line}")
        print()
        print("Suggested CLAUDE.md change (apply manually):")
        print(render_action_diff(claude, firm, dd))
    else:
        print("All anchors aligned. 0-day skew window logged.")

    print(f"audit log: {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
