#!/usr/bin/env python3
"""verify_lock_anchors.py — drift checker for CLAUDE.md vs locked code.

Reads:
  - CLAUDE.md          (Strategy table, Multiplier System line, Protection block)
  - firm_rules.py      (RISK_TIERS challenge allocations)
  - dd_protection.py   (DD_TRIGGER, DD_SCALE, BASE_RISK)
  - portfolio_mc.py    (OANDA_PANELS filenames -> strategy versions)

Routes Closed / Action / Forward per docs/methodology/observation_routing.md.

Exit code 0 always (advisory). Output goes to stdout AND appends to
analysis/skew_audit/<YYYY-MM-DD>.md. "0-day window logged as 0" per Rule 6
fallback clause in docs/operational_rules.md.

Notion anchor pages (manual cross-check, script does not fetch):
  - Strategy lock:    https://www.notion.so/346dc0b53c1181d1b8d5e12df4bd3810
  - FINAL protection: https://www.notion.so/346dc0b53c11816085bbf2292be934cc
  - The Algorithm:    https://www.notion.so/34ddc0b53c11811eb6a0d9192b63d252
"""
from __future__ import annotations

import math
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLAUDE_MD = ROOT / "CLAUDE.md"
FIRM_RULES = ROOT / "firm_rules.py"
DD_PROTECTION = ROOT / "dd_protection.py"
PORTFOLIO_MC = ROOT / "portfolio_mc.py"
SKEW_AUDIT_DIR = ROOT / "analysis" / "skew_audit"

# Per docs/methodology/observation_routing.md re-MC triggers + Rule 6.
GUARDIAN_SAFE_BAND = (0.0030, 0.0034)

NAME_TO_KEY = {
    "Guardian Gold": "guardian",
    "Striker DJ30":  "striker",
    "Aegis USDJPY":  "aegis",
}


def _grep(pattern: str, text: str, *, flags: int = 0) -> re.Match | None:
    return re.search(pattern, text, flags)


def extract_code_constants() -> dict:
    fr = FIRM_RULES.read_text(encoding="utf-8")
    ddp = DD_PROTECTION.read_text(encoding="utf-8")

    challenge_block = _grep(r'"challenge":\s*\{([^}]+)\}', fr)
    risks = {}
    if challenge_block:
        for m in re.finditer(r'"(\w+)":\s*([\d.]+)', challenge_block.group(1)):
            risks[m.group(1)] = float(m.group(2))

    dd_trigger_m = _grep(r"^DD_TRIGGER\s*=\s*([\d.]+)", ddp, flags=re.M)
    dd_scale_m   = _grep(r"^DD_SCALE\s*=\s*([\d.]+)", ddp, flags=re.M)

    base_risk_block = _grep(r"BASE_RISK\s*=\s*\{([^}]+)\}", ddp)
    base_risk = {}
    if base_risk_block:
        for m in re.finditer(r'"(\w+)":\s*([\d.]+)', base_risk_block.group(1)):
            base_risk[m.group(1).lower()] = float(m.group(2))

    return {
        "challenge_risks": risks,
        "dd_trigger": float(dd_trigger_m.group(1)) if dd_trigger_m else None,
        "dd_scale":   float(dd_scale_m.group(1))   if dd_scale_m   else None,
        "base_risk":  base_risk,
    }


def extract_panel_versions() -> dict:
    pm = PORTFOLIO_MC.read_text(encoding="utf-8")
    block = _grep(r"OANDA_PANELS[^{]*\{([^}]+)\}", pm)
    versions = {}
    if block:
        for m in re.finditer(r'"(\w+)":\s*OANDA_DIR\s*/\s*"([^"]+)"', block.group(1)):
            strat = m.group(1)
            parts = m.group(2).split("_")
            if len(parts) == 7:
                versions[strat] = parts[2]
    return versions


def extract_claudemd_anchors() -> dict:
    md = CLAUDE_MD.read_text(encoding="utf-8")

    table_risks: dict[str, float] = {}
    table_versions: dict[str, str] = {}
    for m in re.finditer(
        r"\|\s*(Guardian Gold|Striker DJ30|Aegis USDJPY)\s*\|[^|]+\|\s*([\d.]+)%[^|]*\|\s*(v[\d.]+)\s+LOCKED",
        md,
    ):
        key = NAME_TO_KEY[m.group(1)]
        table_risks[key] = float(m.group(2)) / 100.0
        table_versions[key] = m.group(3)

    mult_match = _grep(
        r"Guardian\s+([\d.]+)%,\s*Striker\s+([\d.]+)%,\s*Aegis\s+([\d.]+)%", md
    )
    mult_risks = {}
    if mult_match:
        mult_risks = {
            "guardian": float(mult_match.group(1)) / 100.0,
            "striker":  float(mult_match.group(2)) / 100.0,
            "aegis":    float(mult_match.group(3)) / 100.0,
        }

    prot_match = _grep(r"<=\s*-([\d.]+).*?multiply.*?by\s+([\d.]+)\s*[×x]", md)
    return {
        "table_risks":      table_risks,
        "table_versions":   table_versions,
        "mult_system_risks": mult_risks,
        "dd_trigger":       float(prot_match.group(1)) if prot_match else None,
        "dd_scale":         float(prot_match.group(2)) if prot_match else None,
    }


def _values_match(a, b) -> bool:
    if a is None or b is None:
        return a is b
    if isinstance(a, float) and isinstance(b, float):
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)
    return a == b


def diff_lines(label: str, code_val, doc_val) -> list[str]:
    if _values_match(code_val, doc_val):
        return []
    return [f"  - {label}: code={code_val!r}, CLAUDE.md={doc_val!r}"]


def check_remc_triggers(code: dict, claudemd: dict) -> list[str]:
    triggers = []
    g = code["challenge_risks"].get("guardian")
    if g is not None and not (GUARDIAN_SAFE_BAND[0] <= g <= GUARDIAN_SAFE_BAND[1]):
        triggers.append(
            f"Guardian risk {g} outside safe band {GUARDIAN_SAFE_BAND} -> re-MC required"
        )
    if not _values_match(code["dd_trigger"], claudemd["dd_trigger"]):
        triggers.append(
            f"dd_protection DD_TRIGGER drift: code={code['dd_trigger']}, doc={claudemd['dd_trigger']} -> re-MC required"
        )
    if not _values_match(code["dd_scale"], claudemd["dd_scale"]):
        triggers.append(
            f"dd_protection DD_SCALE drift: code={code['dd_scale']}, doc={claudemd['dd_scale']} -> re-MC required"
        )
    return triggers


def main() -> int:
    code = extract_code_constants()
    panels = extract_panel_versions()
    claudemd = extract_claudemd_anchors()

    drifts: list[str] = []
    for k in ("guardian", "striker", "aegis"):
        drifts += diff_lines(
            f"{k} risk (challenge tier vs CLAUDE.md table)",
            code["challenge_risks"].get(k),
            claudemd["table_risks"].get(k),
        )
        drifts += diff_lines(
            f"{k} risk (challenge tier vs Multiplier System line)",
            code["challenge_risks"].get(k),
            claudemd["mult_system_risks"].get(k),
        )
        drifts += diff_lines(
            f"{k} risk (challenge tier vs dd_protection BASE_RISK)",
            code["challenge_risks"].get(k),
            code["base_risk"].get(k),
        )
        drifts += diff_lines(
            f"{k} version (panel filename vs CLAUDE.md table)",
            panels.get(k),
            claudemd["table_versions"].get(k),
        )
    drifts += diff_lines("DD_TRIGGER (code vs Protection block)", code["dd_trigger"], claudemd["dd_trigger"])
    drifts += diff_lines("DD_SCALE (code vs Protection block)",   code["dd_scale"],   claudemd["dd_scale"])

    triggers = check_remc_triggers(code, claudemd)

    if triggers:
        bucket = "Forward"
        body_parts = ["Re-MC trigger fired:"] + [f"  - {t}" for t in triggers]
        if drifts:
            body_parts += ["", "Doc drift also present:"] + drifts
        body_parts += [
            "",
            "Suggested action: run `python -m portfolio_mc`, then update CLAUDE.md MC anchors.",
            "Re-MC triggers per docs/methodology/observation_routing.md.",
        ]
    elif drifts:
        bucket = "Action"
        body_parts = ["CLAUDE.md / code drift detected:"] + drifts + [
            "",
            "No re-MC trigger fired; documentation update only.",
            "Apply patches manually; this script does not write to CLAUDE.md.",
        ]
    else:
        bucket = "Closed"
        body_parts = [
            "All anchors aligned. Skew window logged as 0-day.",
            "Per Rule 6 in docs/operational_rules.md: even a 0-day window is a logged 0.",
        ]

    today = date.today().isoformat()
    output_lines = [
        f"# Lock-anchor verification — {today}",
        "",
        f"**Routing: {bucket}**",
        "",
        *body_parts,
        "",
    ]
    output = "\n".join(output_lines)
    print(output)

    SKEW_AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    log_file = SKEW_AUDIT_DIR / f"{today}.md"
    with log_file.open("a", encoding="utf-8") as f:
        f.write(output + "\n---\n\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
