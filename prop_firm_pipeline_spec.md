# Prop Firm Pipeline — Simplified Spec (Algorithm-Audited)

## Context

This spec was produced by applying The Algorithm (Question → Delete → Simplify → Accelerate → Automate) to the original prop_firm_pipeline scope. The strategies are locked. The Monte Carlo is done. The only operational risk at scale is **wrong position size** or **missing a blown account**.

---

## What Was Deleted (and Why)

| Original Scope | Verdict | Reasoning |
|---|---|---|
| Challenge lifecycle state machine | **Deleted** → status field | States are just: challenge / funded / scaling / failed. No complex transitions needed. |
| Monte Carlo pass probability | **Deleted** | Already validated at portfolio level (97.9%, 10K sims). Strategies are locked. No per-account decision this informs. |
| Diagnostics module | **Deleted** | Diagnostics inform strategy changes. Strategies are locked. Weekly CSV sanity check is sufficient. |
| Portfolio dashboard | **Simplified** → lookup table | The dashboard served development. Operations need a reference sheet, not a dashboard. |

---

## What Survives: The Account Lookup Table

### Core Data Model

```python
@dataclass
class Account:
    account_id: str          # e.g. "FXIFY-200K-01"
    firm: str                # FXIFY | FundedNext | The5ers | BrightFunded
    phase: str               # challenge | funded | scaling | failed
    balance: float           # current balance (updated weekly from CSV)
    initial_balance: float   # starting balance for DD calculation
    dd_limit_pct: float      # max drawdown % (e.g. 5.0 for FXIFY)
    profit_target_pct: float # target % (e.g. 5.0 for FXIFY challenge)
    
    # Derived (computed on update)
    dd_remaining_pct: float  # how much room before failure
    target_remaining: float  # dollars to target
    
    # Pre-calculated lot sizes per strategy
    lots_guardian: float     # at Guardian risk tier for this phase
    lots_striker: float      # at Striker risk tier for this phase
    lots_aegis: float        # at Aegis risk tier for this phase
```

### Risk Tiers (Locked)

```python
RISK_TIERS = {
    "challenge": {"guardian": 0.0030, "striker": 0.0070, "aegis": 0.0075},
    "funded":    {"guardian": 0.0045, "striker": 0.0075, "aegis": 0.0080},
}
```

### Lot Size Calculation

This is the core function — the one that prevents the $1M mistake:

```
lot_size = (balance × risk_pct) / (SL_in_price_units)

Where SL_in_price_units:
  Guardian: 1.55 × ATR(14) on XAUUSD 15min
  Striker:  1.4 × ATR(11) on DJ30 15min (contractValue = 10)
  Aegis:    1.5 × ATR(17) on USDJPY 15min
```

ATR values must be input manually or pulled from TradingView at time of reference — they change daily. The lookup table stores the **risk % and balance**; lot size is computed at query time with current ATR.

### Operations

1. **`add_account(account_id, firm, initial_balance, ...)`** — register a new account
2. **`update_from_csv(account_id, csv_path)`** — weekly CSV upload, updates balance, computes DD remaining and target remaining
3. **`get_lot_sizes(account_id, atr_guardian, atr_striker, atr_aegis)`** — returns lot sizes for all 3 strategies given current ATRs
4. **`status()`** — print all accounts: phase, DD remaining, target remaining, any flags

### Flags (The Only Alerts That Matter)

- **DD WARNING**: `dd_remaining_pct < 1.5%` — approaching failure, review before next session
- **ACCOUNT FAILED**: `dd_remaining_pct <= 0` — mark as failed, stop trading
- **TARGET HIT**: `balance >= initial_balance × (1 + profit_target_pct/100)` — ready to advance phase

---

## Firm Rules Reference

Each firm has its own DD type, target, and constraints. Keep these as config, not code:

```python
FIRM_RULES = {
    "FXIFY": {
        "dd_type": "static",        # non-trailing
        "max_dd_pct": 5.0,
        "daily_loss_pct": 5.0,
        "profit_target_pct": 5.0,
        "min_trading_days": 5,
        "news_trading": True,
        "weekend_holds": True,
    },
    # FundedNext, The5ers, BrightFunded: define when onboarding those accounts
}
```

---

## What This Is NOT

- Not a real-time monitor (DXTrade handles that per-account)
- Not a diagnostics engine (strategies are locked)
- Not a Monte Carlo simulator (already done)
- Not a journal (deleted — weekly CSV is the record)

---

## File Structure (Simplified)

```
prop_firm_pipeline/
├── CLAUDE.md              # project instructions for Claude Code
├── accounts.py            # Account dataclass + lot size calc
├── firm_rules.py          # firm config (already exists, keep)
├── csv_parser.py          # DXTrade CSV → balance update (already exists as dxtrade_parser.py)
├── cli.py                 # simple CLI: add, update, status, lots
└── data/
    └── accounts.json      # persistent account state
```

Delete: `account_manager.py` (replaced by simpler `accounts.py`), `diagnostics.py` (deleted per Algorithm Step 2).

---

## Implementation Notes for Claude Code

- Keep it simple. This is a lookup tool, not a platform.
- `accounts.json` is the single source of truth. No database.
- CLI-first. No web UI. Joshua runs this from terminal.
- ATR is an input parameter, not something the pipeline fetches. The pipeline doesn't connect to markets.
- When Joshua onboards a new firm, he adds its rules to `firm_rules.py` as config. No code changes needed.
