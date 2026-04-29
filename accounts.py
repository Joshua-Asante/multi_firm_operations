"""
Account dataclass and lot size calculation.
Single source of truth: data/accounts.json
"""

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from firm_rules import RISK_TIERS, BASELINE_BALANCE, BASELINE_RISK, FIRM_RULES

DATA_FILE = Path(__file__).parent / "data" / "accounts.json"


@dataclass
class Account:
    account_id: str
    firm: str
    phase: str              # challenge | funded | scaling | failed
    balance: float
    initial_balance: float
    dd_limit_pct: float     # max drawdown % (e.g. 5.0)
    profit_target_pct: float  # target % (e.g. 5.0)

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
        if self.dd_remaining_pct <= 0:
            flags.append("ACCOUNT FAILED")
        elif self.dd_remaining_pct < 1.5:
            flags.append("DD WARNING")
        if self.target_remaining <= 0 and self.profit_target_pct > 0:
            flags.append("TARGET HIT")
        return flags

    def to_dict(self) -> dict:
        return {
            "account_id": self.account_id,
            "firm": self.firm,
            "phase": self.phase,
            "balance": self.balance,
            "initial_balance": self.initial_balance,
            "dd_limit_pct": self.dd_limit_pct,
            "profit_target_pct": self.profit_target_pct,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Account":
        return cls(**d)


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
    """Return multipliers for all 3 strategies."""
    return {
        "guardian": calc_multiplier(account.balance, account.phase, "guardian"),
        "striker": calc_multiplier(account.balance, account.phase, "striker"),
        "aegis": calc_multiplier(account.balance, account.phase, "aegis"),
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

    account = Account(
        account_id=account_id,
        firm=firm_upper,
        phase=phase,
        balance=initial_balance,
        initial_balance=initial_balance,
        dd_limit_pct=dd_limit_pct if dd_limit_pct is not None else rules.get("max_dd_pct", 5.0),
        profit_target_pct=profit_target_pct if profit_target_pct is not None else rules.get("profit_target_pct", 5.0),
    )
    accounts.append(account)
    save_accounts(accounts)
    return account


def update_balance(account_id: str, new_balance: float) -> Account:
    """Update an account's balance. Auto-flags if DD breached or target hit."""
    accounts = load_accounts()
    for i, a in enumerate(accounts):
        if a.account_id == account_id:
            a.balance = new_balance
            # Auto-fail if DD breached
            if a.dd_remaining_pct <= 0 and a.phase != "failed":
                a.phase = "failed"
            save_accounts(accounts)
            return a
    raise ValueError(f"Account '{account_id}' not found")
