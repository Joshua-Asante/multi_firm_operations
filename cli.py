"""
CLI for the prop firm pipeline.
Usage:
    python cli.py add <account_id> <firm> <balance> [--phase challenge]
    python cli.py update <account_id> <balance>
    python cli.py status
    python cli.py lots
"""

import argparse
import sys

from accounts import (
    add_account, update_balance, load_accounts, get_account, get_multipliers
)


def cmd_add(args):
    try:
        account = add_account(
            account_id=args.account_id,
            firm=args.firm,
            initial_balance=args.balance,
            phase=args.phase,
        )
        print(f"Added: {account.account_id} ({account.firm} ${account.initial_balance:,.0f} {account.phase})")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_update(args):
    try:
        account = update_balance(args.account_id, args.balance)
        print(f"Updated: {account.account_id} -> ${account.balance:,.2f}")
        print(f"  DD remaining: {account.dd_remaining_pct:.2f}%")
        print(f"  Target remaining: ${account.target_remaining:,.2f}")
        for flag in account.flags:
            print(f"  *** {flag} ***")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_status(args):
    accounts = load_accounts()
    if not accounts:
        print("No accounts registered.")
        return

    print(f"{'ID':<20} {'Firm':<10} {'Phase':<10} {'Balance':>12} {'DD Left':>8} {'To Target':>12} {'Flags'}")
    print("-" * 90)
    for a in accounts:
        flags = ", ".join(a.flags) if a.flags else ""
        print(f"{a.account_id:<20} {a.firm:<10} {a.phase:<10} ${a.balance:>10,.2f} "
              f"{a.dd_remaining_pct:>6.2f}% ${a.target_remaining:>10,.2f} {flags}")


def cmd_lots(args):
    accounts = load_accounts()
    active = [a for a in accounts if a.phase != "failed"]
    if not active:
        print("No active accounts.")
        return

    print(f"{'Account':<25}| {'G x':>6} | {'S x':>6} | {'A x':>6}")
    print("-" * 52)
    for a in active:
        m = get_multipliers(a)
        label = a.account_id
        if a.phase != "challenge":
            label += f" ({a.phase})"
        print(f"{label:<25}| {m['guardian']:>5.2f} | {m['striker']:>5.2f} | {m['aegis']:>5.2f}")

    print(f"\nBaseline: $200K challenge. Multiply indicator lot size by account multiplier.")


def main():
    parser = argparse.ArgumentParser(description="Prop firm pipeline CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # add
    p_add = sub.add_parser("add", help="Register a new account")
    p_add.add_argument("account_id")
    p_add.add_argument("firm")
    p_add.add_argument("balance", type=float)
    p_add.add_argument("--phase", default="challenge")
    p_add.set_defaults(func=cmd_add)

    # update
    p_update = sub.add_parser("update", help="Update account balance")
    p_update.add_argument("account_id")
    p_update.add_argument("balance", type=float)
    p_update.set_defaults(func=cmd_update)

    # status
    p_status = sub.add_parser("status", help="Show all accounts")
    p_status.set_defaults(func=cmd_status)

    # lots
    p_lots = sub.add_parser("lots", help="Multiplier reference card for all active accounts")
    p_lots.set_defaults(func=cmd_lots)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
