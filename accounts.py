"""
Account dataclass and lot size calculation.
Single source of truth: data/accounts.json
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from firm_rules import RISK_TIERS, BASELINE_BALANCE, BASELINE_RISK, FIRM_RULES

DATA_FILE = Path(__file__).parent / "data" / "accounts.json"


def _parse_iso_datetime(s: str) -> datetime:
    """Parse stored last_trade_at; naive strings are treated as UTC."""
    t = s.strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(t)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@dataclass
class FxifyChallengeStatus:
    """Post-trade FXIFY rule evaluation using fxify_rule_validator."""

    limit_results: list[tuple[bool, str, str]]  # RuleResult tuples
    completion_results: list[tuple[bool, str, str]]
    skipped: list[str]

    @property
    def limit_breached(self) -> bool:
        return any((not passed) and kind == "limit" for passed, kind, _ in self.limit_results)

    @property
    def in_good_standing(self) -> bool:
        return not self.limit_breached

    @property
    def phase_complete(self) -> bool:
        return self.in_good_standing and all(
            passed for passed, kind, _ in self.completion_results if kind == "completion"
        )


@dataclass
class Account:
    account_id: str
    firm: str
    phase: str              # challenge | funded | scaling | failed
    balance: float
    initial_balance: float
    dd_limit_pct: float     # max drawdown % (e.g. 5.0)
    profit_target_pct: float  # target % (e.g. 5.0)
    prior_eod_equity: Optional[float] = None
    """Prior trading day EOD balance (5pm EST per FXIFY). Required for daily-loss check."""
    last_trade_at: Optional[str] = None
    """ISO 8601 timestamp of last trade (for inactivity)."""
    trading_days_count: int = 0
    """Completed trading days toward FXIFY min-trading-days completion."""

    @property
    def dd_remaining_pct(self) -> float:
        """How much DD room is left as % of initial balance."""
        lost = self.initial_balance - self.balance
        used_pct = (lost / self.initial_balance) * 100
        return round(self.dd_limit_pct - used_pct, 2)

    @property
    def target_remaining(self) -> float:
        """Dollars remaining to hit profit target."""
        target_balance = self.initial_balance * (1 + self.profit_target_pct / 100)
        return round(target_balance - self.balance, 2)

    @property
    def flags(self) -> list[str]:
        flags = []
        if self.firm == "FXIFY":
            st = evaluate_fxify_challenge_status(self)
            if st.limit_breached:
                flags.append("ACCOUNT FAILED")
            elif 0 < self.dd_remaining_pct < 1.5:
                flags.append("DD WARNING")
            profit_met = st.completion_results[0][0] if st.completion_results else False
            min_days_met = st.completion_results[1][0] if len(st.completion_results) > 1 else False
            if profit_met and min_days_met and self.profit_target_pct > 0:
                flags.append("PHASE COMPLETE")
            elif profit_met and self.profit_target_pct > 0:
                flags.append("TARGET HIT")
        else:
            if self.dd_remaining_pct <= 0:
                flags.append("ACCOUNT FAILED")
            elif self.dd_remaining_pct < 1.5:
                flags.append("DD WARNING")
            if self.target_remaining <= 0 and self.profit_target_pct > 0:
                flags.append("TARGET HIT")
        return flags

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "account_id": self.account_id,
            "firm": self.firm,
            "phase": self.phase,
            "balance": self.balance,
            "initial_balance": self.initial_balance,
            "dd_limit_pct": self.dd_limit_pct,
            "profit_target_pct": self.profit_target_pct,
        }
        if self.prior_eod_equity is not None:
            d["prior_eod_equity"] = self.prior_eod_equity
        if self.last_trade_at is not None:
            d["last_trade_at"] = self.last_trade_at
        if self.trading_days_count:
            d["trading_days_count"] = self.trading_days_count
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Account":
        return cls(
            account_id=d["account_id"],
            firm=d["firm"],
            phase=d["phase"],
            balance=float(d["balance"]),
            initial_balance=float(d["initial_balance"]),
            dd_limit_pct=float(d["dd_limit_pct"]),
            profit_target_pct=float(d["profit_target_pct"]),
            prior_eod_equity=float(d["prior_eod_equity"]) if d.get("prior_eod_equity") is not None else None,
            last_trade_at=d.get("last_trade_at"),
            trading_days_count=int(d.get("trading_days_count", 0)),
        )


def evaluate_fxify_challenge_status(
    account: Account,
    now: Optional[datetime] = None,
) -> FxifyChallengeStatus:
    """Run fxify_rule_validator against persisted account fields."""
    if account.firm != "FXIFY":
        raise ValueError("evaluate_fxify_challenge_status is only for firm=FXIFY")
    from fxify_rule_validator import (
        validate_daily_loss,
        validate_inactivity,
        validate_max_drawdown,
        validate_min_trading_days,
        validate_profit_target,
    )

    now = now or datetime.now(timezone.utc)
    skipped: list[str] = []
    limit_results: list[tuple[bool, str, str]] = []
    completion_results: list[tuple[bool, str, str]] = []

    limit_results.append(
        validate_max_drawdown(
            account.balance,
            account.initial_balance,
            account.dd_limit_pct,
        )
    )

    fx = FIRM_RULES["FXIFY"]
    if account.prior_eod_equity is not None and account.prior_eod_equity > 0:
        limit_results.append(
            validate_daily_loss(
                account.balance,
                account.prior_eod_equity,
                fx["daily_loss_pct"],
            )
        )
    else:
        skipped.append(
            "Daily loss check skipped (set prior_eod_equity on account or pass --prior-eod on update)"
        )

    if account.last_trade_at:
        try:
            last_t = _parse_iso_datetime(account.last_trade_at)
            limit_results.append(
                validate_inactivity(last_t, now, fx["inactivity_max_idle_days"])
            )
        except ValueError as e:
            skipped.append(f"Inactivity check error: {e}")
    else:
        skipped.append(
            "Inactivity check skipped (set last_trade_at or pass --last-trade-at on update)"
        )

    completion_results.append(
        validate_profit_target(
            account.balance,
            account.initial_balance,
            account.profit_target_pct,
        )
    )
    completion_results.append(
        validate_min_trading_days(
            account.trading_days_count,
            fx["min_trading_days"],
        )
    )

    return FxifyChallengeStatus(
        limit_results=limit_results,
        completion_results=completion_results,
        skipped=skipped,
    )


def fxify_status_summary(account: Account) -> str:
    """Short token for tabular status: ok | BREACH | partial."""
    if account.firm != "FXIFY":
        return "-"
    if account.phase == "failed":
        return "failed"
    st = evaluate_fxify_challenge_status(account)
    if st.limit_breached:
        return "BREACH"
    if st.skipped:
        return "partial"
    return "ok"


def calc_multiplier(balance: float, phase: str, strategy: str) -> float:
    """
    Multiplier relative to the $200K baseline that Pine Script indicators use.

    multiplier = (account_balance * account_risk_pct) / (200,000 * baseline_risk_pct)

    Pine Script outputs lot sizes for the baseline. Multiply its output by this
    to get the correct size for any account/phase combo.
    """
    tier = RISK_TIERS.get(phase)
    if tier is None:
        tier = RISK_TIERS["funded"]

    account_risk = balance * tier[strategy]
    baseline_risk = BASELINE_BALANCE * BASELINE_RISK[strategy]

    if baseline_risk <= 0:
        return 0.0

    # Round down to 2 decimal places (never round up on risk)
    return math.floor((account_risk / baseline_risk) * 100) / 100


def get_multipliers(account: Account) -> dict:
    """Return multipliers for all 4 strategies."""
    return {
        "guardian": calc_multiplier(account.balance, account.phase, "guardian"),
        "striker": calc_multiplier(account.balance, account.phase, "striker"),
        "aegis": calc_multiplier(account.balance, account.phase, "aegis"),
        "striker_nas100": calc_multiplier(account.balance, account.phase, "striker_nas100"),
    }


# --- Persistence ---

def _load_all() -> list[dict]:
    if not DATA_FILE.exists():
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def _save_all(accounts: list[dict]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(accounts, f, indent=2)


def load_accounts() -> list[Account]:
    return [Account.from_dict(d) for d in _load_all()]


def save_accounts(accounts: list[Account]) -> None:
    _save_all([a.to_dict() for a in accounts])


def get_account(account_id: str) -> Optional[Account]:
    for a in load_accounts():
        if a.account_id == account_id:
            return a
    return None


def add_account(account_id: str, firm: str, initial_balance: float,
                phase: str = "challenge", dd_limit_pct: Optional[float] = None,
                profit_target_pct: Optional[float] = None) -> Account:
    """Register a new account. Pulls DD/target from firm rules if not overridden."""
    accounts = load_accounts()
    if any(a.account_id == account_id for a in accounts):
        raise ValueError(f"Account '{account_id}' already exists")

    firm_upper = firm.upper()
    rules = FIRM_RULES.get(firm_upper, {})

    prior_eod: Optional[float] = None
    if firm_upper == "FXIFY":
        prior_eod = initial_balance

    account = Account(
        account_id=account_id,
        firm=firm_upper,
        phase=phase,
        balance=initial_balance,
        initial_balance=initial_balance,
        dd_limit_pct=dd_limit_pct if dd_limit_pct is not None else rules.get("max_dd_pct", 5.0),
        profit_target_pct=profit_target_pct if profit_target_pct is not None else rules.get("profit_target_pct", 5.0),
        prior_eod_equity=prior_eod,
    )
    accounts.append(account)
    save_accounts(accounts)
    return account


def update_balance(
    account_id: str,
    new_balance: float,
    fxify_updates: Optional[dict[str, Any]] = None,
) -> Account:
    """Update balance and optional FXIFY context keys (only keys present are applied)."""
    accounts = load_accounts()
    for i, a in enumerate(accounts):
        if a.account_id == account_id:
            a.balance = new_balance
            if fxify_updates:
                if "prior_eod_equity" in fxify_updates:
                    a.prior_eod_equity = fxify_updates["prior_eod_equity"]
                if "last_trade_at" in fxify_updates:
                    a.last_trade_at = fxify_updates["last_trade_at"]
                if "trading_days_count" in fxify_updates:
                    a.trading_days_count = int(fxify_updates["trading_days_count"])

            if a.firm == "FXIFY":
                st = evaluate_fxify_challenge_status(a)
                if st.limit_breached and a.phase != "failed":
                    a.phase = "failed"
            else:
                if a.dd_remaining_pct <= 0 and a.phase != "failed":
                    a.phase = "failed"
            save_accounts(accounts)
            return a
    raise ValueError(f"Account '{account_id}' not found")
