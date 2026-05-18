# Validator self-test — KNOWN-BAD CLAUDE.md mock
# SEEDED VIOLATION: Guardian Gold row claims risk 0.50% — manifest expects 0.34%.
# Validator MUST surface this as a HARD violation.

| Strategy        | Instrument / TF | Risk/trade              | Version       | DXTrade contractValue                             |
|-----------------|-----------------|-------------------------|---------------|---------------------------------------------------|
| Guardian Gold   | XAUUSD 15m      | 0.50% (SEEDED DRIFT)    | v5.5 LOCKED   | 100                                               |
| Striker DJ30    | DJ30 15m        | 1.00%                   | v4.5 LOCKED   | **10** (critical — default of 1 gives ~7% risk)   |
| Aegis USDJPY    | USDJPY 15m      | 1.50%                   | v4.3 LOCKED   | default (1)                                       |
| Striker NAS100  | NAS100 15m      | 0.40%                   | v1 LOCKED     | 10                                                |
