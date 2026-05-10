"""
CLI for multi-firm operations.
Usage:
    python cli.py add <account_id> <firm> <balance> [--phase challenge]
    python cli.py update <account_id> <balance> [--prior-eod ... --last-trade-at ... --trading-days ...]
    python cli.py status
    python cli.py challenge [account_id]
    python cli.py lots
"""

import argparse
import sys

from accounts import (
    add_account,
    evaluate_fxify_challenge_status,
    fxify_status_summary,
    get_account,
    get_multipliers,
    load_accounts,
    update_balance,
)


def _fetch_oanda_balance(account_id: str) -> float:
    """Read live NAV from the OANDA REST API for an OANDA-tracked account.

    Two-tier canonical rule (memory: feedback_two_tier_canonical_pepperstone_oanda):
    OANDA is the proxy/pattern-spotting source, not authoritative for lock
    decisions. This function is therefore restricted to accounts whose `firm`
    is 'OANDA'. Writing an OANDA NAV into a DXTrade-tracked (e.g. FXIFY) account
    record would silently violate the canonical-source distinction.

    Additionally restricted to the account_id stored in ~/.keys/oanda.txt —
    lib.oanda.account_summary uses that cred file's account ID, so calling
    --from-oanda on a different OANDA account would silently return another
    account's NAV.
    """
    account = get_account(account_id)
    if account is None:
        raise ValueError(f"Account '{account_id}' not found")
    if account.firm != "OANDA":
        raise ValueError(
            f"--from-oanda not allowed for {account.firm} accounts; "
            f"use manual balance entry"
        )
    from lib.oanda_creds import load as load_creds
    _, cred_account_id = load_creds()
    if account_id != cred_account_id:
        raise ValueError(
            f"--from-oanda only supports the account in ~/.keys/oanda.txt "
            f"({cred_account_id[:8]}...); requested {account_id} does not match"
        )
    from lib.oanda import account_summary
    summary = account_summary()
    return float(summary["NAV"])


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
        if args.from_oanda:
            if args.balance is not None:
                raise ValueError("--from-oanda and explicit balance are mutually exclusive")
            balance = _fetch_oanda_balance(args.account_id)
        else:
            if args.balance is None:
                raise ValueError("balance required (or pass --from-oanda for OANDA-tracked accounts)")
            balance = args.balance
        fx = {}
        if args.prior_eod is not None:
            fx["prior_eod_equity"] = args.prior_eod
        if args.last_trade_at is not None:
            fx["last_trade_at"] = args.last_trade_at
        if args.trading_days is not None:
            fx["trading_days_count"] = args.trading_days
        account = update_balance(
            args.account_id,
            balance,
            fxify_updates=fx if fx else None,
        )
        print(f"Updated: {account.account_id} -> ${account.balance:,.2f}")
        if account.firm != "FXIFY":
            print(f"  DD remaining: {account.dd_remaining_pct:.2f}%")
            print(f"  Target remaining: ${account.target_remaining:,.2f}")
        if account.firm == "FXIFY":
            st = evaluate_fxify_challenge_status(account)
            print("  FXIFY validators:")
            for passed, kind, reason in st.limit_results + st.completion_results:
                tag = "ok" if passed else "NO"
                print(f"    [{tag}] {reason}")
            for note in st.skipped:
                print(f"    (skipped) {note}")
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

    print(
        f"{'ID':<20} {'Firm':<10} {'Phase':<10} {'Balance':>12} {'DD Left':>8} "
        f"{'To Target':>12} {'FXIFY':>8} {'Flags'}"
    )
    print("-" * 102)
    for a in accounts:
        flags = ", ".join(a.flags) if a.flags else ""
        fx = fxify_status_summary(a)
        if a.firm == "FXIFY":
            dd_str = "    —"
            tgt_str = "         —"
        else:
            dd_str = f"{a.dd_remaining_pct:>6.2f}%"
            tgt_str = f"${a.target_remaining:>10,.2f}"
        print(
            f"{a.account_id:<20} {a.firm:<10} {a.phase:<10} ${a.balance:>10,.2f} "
            f"{dd_str:>8} {tgt_str:>12} {fx:>8} {flags}"
        )


def cmd_challenge(args):
    """FXIFY rule detail: limit + completion checks from fxify_rule_validator."""
    accounts = load_accounts()
    fxify = [a for a in accounts if a.firm == "FXIFY"]
    if args.account_id:
        fxify = [a for a in fxify if a.account_id == args.account_id]
    if not fxify:
        print("No FXIFY accounts" + (f" matching {args.account_id!r}" if args.account_id else "."))
        return
    for a in fxify:
        st = evaluate_fxify_challenge_status(a)
        print(f"{a.account_id}  phase={a.phase}  balance=${a.balance:,.2f}")
        if a.phase_completed_at:
            print(f"  phase_completed_at: {a.phase_completed_at}")
        print("  Limits:")
        for passed, _kind, reason in st.limit_results:
            tag = "ok" if passed else "FAIL"
            print(f"    [{tag}] {reason}")
        print("  Completion:")
        for passed, _kind, reason in st.completion_results:
            tag = "met" if passed else "open"
            print(f"    [{tag}] {reason}")
        for note in st.skipped:
            print(f"  (skipped) {note}")
        print()


def cmd_tearsheet(args):
    from pathlib import Path
    from lib.tearsheet import from_csv
    out_path = Path(args.out) if args.out else Path(args.csv_path).with_suffix(".tearsheet.html")
    try:
        path = from_csv(args.csv_path, args.starting_equity, out_path,
                        title=args.title or "Prop Firm Tearsheet")
        print(f"Tearsheet written: {path}")
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_lots(args):
    accounts = load_accounts()
    active = [a for a in accounts if a.phase != "failed"]
    if not active:
        print("No active accounts.")
        return

    print(f"{'Account':<25}| {'G x':>6} | {'S x':>6} | {'A x':>6} | {'N x':>6}")
    print("-" * 61)
    for a in active:
        m = get_multipliers(a)
        label = a.account_id
        if a.phase != "challenge":
            label += f" ({a.phase})"
        print(f"{label:<25}| {m['guardian']:>5.2f} | {m['striker']:>5.2f} | {m['aegis']:>5.2f} | {m['striker_nas100']:>5.2f}")

    print(f"\nBaseline: $200K challenge. Multiply indicator lot size by account multiplier.")
    print("G=Guardian, S=Striker DJ30, A=Aegis, N=Striker NAS100.")


def main():
    parser = argparse.ArgumentParser(description="Multi-firm operations CLI")
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
    p_update.add_argument("balance", type=float, nargs="?", default=None,
                          help="New balance in account currency. Omit when --from-oanda is set.")
    p_update.add_argument("--from-oanda", action="store_true",
                          help="Read live NAV from OANDA REST API. Only allowed for firm=OANDA accounts that match the credentials in ~/.keys/oanda.txt.")
    p_update.add_argument(
        "--prior-eod",
        type=float,
        default=None,
        metavar="BALANCE",
        help="FXIFY: prior trading day EOD balance (5pm EST) for daily-loss check",
    )
    p_update.add_argument(
        "--last-trade-at",
        default=None,
        metavar="ISO_DATETIME",
        help="FXIFY: last trade time ISO 8601 (e.g. 2026-05-10T14:30:00Z) for inactivity",
    )
    p_update.add_argument(
        "--trading-days",
        type=int,
        default=None,
        metavar="N",
        help="FXIFY: completed trading days count toward min-trading-days",
    )
    p_update.set_defaults(func=cmd_update)

    # status
    p_status = sub.add_parser("status", help="Show all accounts")
    p_status.set_defaults(func=cmd_status)

    # challenge (FXIFY detail)
    p_ch = sub.add_parser(
        "challenge",
        help="Show FXIFY validator detail (fxify_rule_validator) for FXIFY accounts",
    )
    p_ch.add_argument(
        "account_id",
        nargs="?",
        default=None,
        help="Optional account id filter",
    )
    p_ch.set_defaults(func=cmd_challenge)

    # lots
    p_lots = sub.add_parser("lots", help="Multiplier reference card for all active accounts")
    p_lots.set_defaults(func=cmd_lots)

    # tearsheet
    p_tear = sub.add_parser("tearsheet", help="Generate HTML tearsheet from DXTrade CSV")
    p_tear.add_argument("csv_path", help="Path to DXTrade CSV export")
    p_tear.add_argument("--out", default=None,
                        help="Output HTML path (default: <csv>.tearsheet.html)")
    p_tear.add_argument("--starting-equity", type=float, default=200_000.0,
                        help="Starting equity for return-series normalization (default: 200000)")
    p_tear.add_argument("--title", default=None, help="Tearsheet title")
    p_tear.set_defaults(func=cmd_tearsheet)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
