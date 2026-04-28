"""Tests for cli._fetch_oanda_balance two-tier canonical gate.

The gate enforces feedback_two_tier_canonical_pepperstone_oanda.md:
--from-oanda may only write into firm=OANDA accounts that match the
credentials in ~/.keys/oanda.txt. Anything else is rejected.
"""

from pathlib import Path

import pytest

from accounts import Account


NEEDS_OANDA = pytest.mark.skipif(
    not Path.home().joinpath(".keys/oanda.txt").exists(),
    reason="OANDA creds not present at ~/.keys/oanda.txt",
)


def _make_account(firm: str, account_id: str = "ACCT-1") -> Account:
    return Account(
        account_id=account_id, firm=firm, phase="challenge",
        balance=200_000.0, initial_balance=200_000.0,
        dd_limit_pct=5.0, profit_target_pct=5.0,
    )


def test_rejected_when_account_missing(monkeypatch):
    """Unknown account ID must surface a clear 'not found' error."""
    from cli import _fetch_oanda_balance
    monkeypatch.setattr("cli.get_account", lambda aid: None)
    with pytest.raises(ValueError, match="not found"):
        _fetch_oanda_balance("MISSING")


def test_rejected_for_non_oanda_firm(monkeypatch):
    """Two-tier canonical: FXIFY/Pepperstone accounts cannot accept OANDA NAV."""
    from cli import _fetch_oanda_balance
    monkeypatch.setattr("cli.get_account", lambda aid: _make_account("FXIFY"))
    with pytest.raises(ValueError, match="not allowed for FXIFY"):
        _fetch_oanda_balance("ACCT-1")


def test_rejected_on_oanda_account_mismatch(monkeypatch):
    """Even an OANDA-firm account is rejected if the ID doesn't match the
    cred-file ID — lib.oanda.account_summary would silently return another
    account's NAV otherwise."""
    from cli import _fetch_oanda_balance
    import lib.oanda_creds
    monkeypatch.setattr(
        "cli.get_account",
        lambda aid: _make_account("OANDA", account_id="OTHER-OANDA-1"),
    )
    monkeypatch.setattr(
        lib.oanda_creds, "load",
        lambda: ("fake-token", "101-001-FAKE-001"),
    )
    with pytest.raises(ValueError, match="does not match"):
        _fetch_oanda_balance("OTHER-OANDA-1")


@NEEDS_OANDA
def test_fetches_real_nav_when_account_matches(monkeypatch):
    """Smoke test: matching cred-file account returns a positive NAV."""
    from cli import _fetch_oanda_balance
    from lib.oanda_creds import load as load_creds
    _, cred_acct = load_creds()
    monkeypatch.setattr(
        "cli.get_account",
        lambda aid: _make_account("OANDA", account_id=cred_acct),
    )
    nav = _fetch_oanda_balance(cred_acct)
    assert nav > 0
