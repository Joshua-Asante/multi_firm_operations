"""Integration tests: Account + fxify_rule_validator + persistence hooks."""

from datetime import datetime, timezone

import pytest

import accounts


@pytest.fixture
def isolated_accounts_json(tmp_path, monkeypatch):
    path = tmp_path / "accounts.json"
    path.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(accounts, "DATA_FILE", path)
    return path


def test_add_fxify_sets_prior_eod_to_initial(isolated_accounts_json):
    a = accounts.add_account("FXIFY-TEST-1", "FXIFY", 200_000.0)
    assert a.prior_eod_equity == 200_000.0


def test_evaluate_fxify_non_fxify_raises(isolated_accounts_json):
    accounts.add_account("O-1", "OANDA", 100_000.0)
    a = accounts.get_account("O-1")
    with pytest.raises(ValueError, match="only for firm=FXIFY"):
        accounts.evaluate_fxify_challenge_status(a)


def test_max_dd_breach_sets_failed_phase(isolated_accounts_json):
    accounts.add_account("FX-BREACH", "FXIFY", 200_000.0)
    # Static DD floor at 5% = 190_000.00 inclusive breach below that
    accounts.update_balance("FX-BREACH", 189_999.99)
    a = accounts.get_account("FX-BREACH")
    assert a.phase == "failed"
    st = accounts.evaluate_fxify_challenge_status(a)
    assert st.limit_breached


def test_fxify_status_summary_partial_without_last_trade(isolated_accounts_json):
    accounts.add_account("FX-NEW", "FXIFY", 200_000.0)
    a = accounts.get_account("FX-NEW")
    assert accounts.fxify_status_summary(a) == "partial"


def test_fxify_status_summary_ok_with_last_trade(isolated_accounts_json):
    accounts.add_account("FX-OK", "FXIFY", 200_000.0)
    accounts.update_balance(
        "FX-OK",
        200_000.0,
        fxify_updates={"last_trade_at": datetime.now(timezone.utc).isoformat()},
    )
    a = accounts.get_account("FX-OK")
    assert accounts.fxify_status_summary(a) == "ok"


def test_daily_loss_breach(isolated_accounts_json):
    accounts.add_account("FX-DAILY", "FXIFY", 200_000.0)
    a = accounts.get_account("FX-DAILY")
    # Prior EOD 200k, daily loss 5% -> floor 190k
    accounts.update_balance(
        "FX-DAILY",
        189_999.99,
        fxify_updates={"prior_eod_equity": 200_000.0},
    )
    a = accounts.get_account("FX-DAILY")
    assert a.phase == "failed"


def test_last_trade_at_inactivity(isolated_accounts_json):
    accounts.add_account("FX-IDLE", "FXIFY", 200_000.0)
    old = datetime(2020, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    accounts.update_balance(
        "FX-IDLE",
        200_000.0,
        fxify_updates={"last_trade_at": old.isoformat()},
    )
    a = accounts.get_account("FX-IDLE")
    st = accounts.evaluate_fxify_challenge_status(a)
    assert st.limit_breached
    assert a.phase == "failed"


def test_phase_complete_flag(isolated_accounts_json):
    accounts.add_account("FX-DONE", "FXIFY", 200_000.0)
    target = 200_000.0 * 1.05  # 5% profit target
    accounts.update_balance(
        "FX-DONE",
        target,
        fxify_updates={
            "prior_eod_equity": 200_000.0,
            "trading_days_count": 5,
        },
    )
    a = accounts.get_account("FX-DONE")
    st = accounts.evaluate_fxify_challenge_status(a)
    assert st.phase_complete
    assert "PHASE COMPLETE" in a.flags
