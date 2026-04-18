#!/usr/bin/env python3
# Single-tier protection (validated 2026-04-17):
#   - 10K-sim MC: bust 1.55% / pass 93.00% at current portfolio
#   - Equity tier deleted after Claude Code proved it was dead code under min semantics
#   - Do not change without re-running portfolio_mc
# See: https://www.notion.so/346dc0b53c11816085bbf2292be934cc
"""
DD Protection Scaler — FXIFY $200K Challenge
=============================================
Morning pre-market tool. Input current DXTrade equity,
get back the risk_pct to set on each TradingView strategy.

Rule: When portfolio DD from peak >= 1.0%, scale all risk to 0.40x.
      Clears automatically when equity returns to peak.

Usage:
    python dd_protection.py                  # show current status
    python dd_protection.py <equity>         # log equity and get today's risk levels
    python dd_protection.py --history        # show equity log
    python dd_protection.py --reset          # reset state (new challenge attempt)
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────
STARTING_EQUITY = 200_000
PROFIT_TARGET = 0.05          # 5% = $10,000
DAILY_LOSS_LIMIT = 0.05       # 5% = $10,000
STATIC_DD_LIMIT = 0.05        # 5% = $10,000

# DD protection rule — single tier (retuned 2026-04-17)
DD_TRIGGER = 0.010            # 1.0% DD from peak triggers scaling
DD_SCALE = 0.40               # multiply risk by 0.40x when triggered

# Unified allocations (locked 2026-04-17, challenge = funded)
BASE_RISK = {
    "Guardian": 0.0030,       # 0.30%
    "Striker":  0.0100,       # 1.00%
    "Aegis":    0.0150,       # 1.50%
}

STATE_FILE = Path(__file__).parent / "dd_protection_state.json"

# ── State Management ──────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        "starting_equity": STARTING_EQUITY,
        "peak_equity": STARTING_EQUITY,
        "last_equity": STARTING_EQUITY,
        "history": [],
    }

def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def reset_state():
    state = {
        "starting_equity": STARTING_EQUITY,
        "peak_equity": STARTING_EQUITY,
        "last_equity": STARTING_EQUITY,
        "history": [],
    }
    save_state(state)
    print("State reset. Peak equity = $200,000.00")

# ── Core Logic ────────────────────────────────────────────────

def calculate_protection(equity: float, peak: float) -> dict:
    """Determine active multiplier and scaled risk levels."""
    dd_from_peak = (peak - equity) / peak if equity < peak else 0.0
    dd_triggered = dd_from_peak >= DD_TRIGGER

    if dd_triggered:
        multiplier = DD_SCALE
        rule = f"DD PROTECTION (DD {dd_from_peak:.2%} ≥ {DD_TRIGGER:.1%})"
    else:
        multiplier = 1.0
        rule = "NONE — full risk"

    scaled_risk = {k: v * multiplier for k, v in BASE_RISK.items()}

    return {
        "dd_from_peak": dd_from_peak,
        "dd_triggered": dd_triggered,
        "multiplier": multiplier,
        "rule": rule,
        "scaled_risk": scaled_risk,
    }

# ── Display ───────────────────────────────────────────────────

def display_status(equity: float, peak: float, result: dict, is_update: bool = False):
    """Print the dashboard."""
    pnl = equity - STARTING_EQUITY
    target_remaining = (STARTING_EQUITY * PROFIT_TARGET) - pnl
    dd_from_start = (STARTING_EQUITY - equity) / STARTING_EQUITY if equity < STARTING_EQUITY else 0.0

    print()
    print("=" * 56)
    print("  FXIFY $200K CHALLENGE — DD PROTECTION STATUS")
    print("=" * 56)
    print()
    print(f"  Equity:        ${equity:>12,.2f}")
    print(f"  Peak:          ${peak:>12,.2f}")
    print(f"  P&L:           ${pnl:>12,.2f}  ({pnl/STARTING_EQUITY:>+.2%})")
    print(f"  DD from peak:  {result['dd_from_peak']:>12.2%}")
    print(f"  DD from start: {dd_from_start:>12.2%}  (limit: {STATIC_DD_LIMIT:.0%})")

    if target_remaining > 0:
        print(f"  To target:     ${target_remaining:>12,.2f}")
    else:
        print(f"  TARGET REACHED  ✓")

    print()

    # Safety warnings
    if dd_from_start >= 0.04:
        print("  ⚠️  DD > 4% FROM START — HALT ALL TRADING")
        print()
    elif dd_from_start >= 0.03:
        print("  ⚠️  DD > 3% FROM START — REVIEW BEFORE TRADING")
        print()

    # Active rule
    if result['multiplier'] < 1.0:
        print(f"  ⚡ ACTIVE RULE: {result['rule']}")
        print(f"  ⚡ MULTIPLIER:  {result['multiplier']:.2f}x")
    else:
        print(f"  ✅ {result['rule']}")
    print()

    # Risk table
    print("  ┌─────────────┬──────────┬──────────┐")
    print("  │ Strategy    │   Base   │  Today   │")
    print("  ├─────────────┼──────────┼──────────┤")
    for name, base in BASE_RISK.items():
        scaled = result['scaled_risk'][name]
        marker = " ◀" if scaled != base else ""
        print(f"  │ {name:<11} │  {base:.2%}  │  {scaled:.2%}{marker:>2} │")
    print("  └─────────────┴──────────┴──────────┘")
    print()

    # TV input helper — show exact values to type
    if result['multiplier'] < 1.0:
        print("  Set in TradingView strategy inputs:")
        for name, risk in result['scaled_risk'].items():
            print(f"    {name}: risk_pct = {risk * 100:.2f}")
        print()
        print("  Restore to base when multiplier returns to 1.0x:")
        for name, base in BASE_RISK.items():
            print(f"    {name}: risk_pct = {base * 100:.2f}")
        print()


def display_history(state: dict):
    """Show equity log."""
    if not state["history"]:
        print("\nNo equity readings logged yet.\n")
        return

    print()
    print("  Date/Time              Equity        Peak     DD%     Mult")
    print("  " + "─" * 62)
    for entry in state["history"][-30:]:  # last 30 entries
        dt = entry["timestamp"][:16]
        eq = entry["equity"]
        pk = entry["peak"]
        dd = entry["dd_from_peak"]
        mult = entry["multiplier"]
        marker = " ⚡" if mult < 1.0 else ""
        print(f"  {dt}  ${eq:>11,.2f}  ${pk:>11,.2f}  {dd:>5.2%}  {mult:.2f}x{marker}")
    print()


# ── Main ──────────────────────────────────────────────────────

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        confirm = input("Reset DD protection state? This clears peak equity and history. [y/N] ")
        if confirm.lower() == "y":
            reset_state()
        return

    state = load_state()

    if len(sys.argv) > 1 and sys.argv[1] == "--history":
        display_history(state)
        return

    if len(sys.argv) > 1:
        # Equity update mode
        try:
            equity = float(sys.argv[1].replace(",", "").replace("$", ""))
        except ValueError:
            print(f"Invalid equity value: {sys.argv[1]}")
            print("Usage: python dd_protection.py <equity>")
            sys.exit(1)

        # Sanity checks
        if equity <= 0:
            print("Equity must be positive.")
            sys.exit(1)
        if equity > STARTING_EQUITY * 1.5:
            print(f"Warning: ${equity:,.2f} is >50% above starting equity. Confirm? [y/N] ", end="")
            if input().lower() != "y":
                return

        # Update peak
        old_peak = state["peak_equity"]
        if equity > state["peak_equity"]:
            state["peak_equity"] = equity

        result = calculate_protection(equity, state["peak_equity"])

        # Log entry
        state["history"].append({
            "timestamp": datetime.now().isoformat(),
            "equity": equity,
            "peak": state["peak_equity"],
            "dd_from_peak": round(result["dd_from_peak"], 6),
            "multiplier": result["multiplier"],
        })
        state["last_equity"] = equity
        save_state(state)

        display_status(equity, state["peak_equity"], result, is_update=True)

        if equity > old_peak:
            print(f"  📈 New peak equity: ${equity:,.2f} (was ${old_peak:,.2f})")
            print()

    else:
        # Status mode — show current state without updating
        result = calculate_protection(state["last_equity"], state["peak_equity"])
        display_status(state["last_equity"], state["peak_equity"], result)


if __name__ == "__main__":
    main()
