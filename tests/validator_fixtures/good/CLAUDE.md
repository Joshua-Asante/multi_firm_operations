# Validator self-test — KNOWN-GOOD CLAUDE.md mock

The validator looks for the Strategy Reference table below.

| Strategy        | Instrument / TF | Risk/trade              | Version       | DXTrade contractValue                             |
|-----------------|-----------------|-------------------------|---------------|---------------------------------------------------|
| Guardian Gold   | XAUUSD 15m      | 0.34% (cold-start base) | v5.5 LOCKED   | 100                                               |
| Striker DJ30    | DJ30 15m        | 1.00%                   | v4.5 LOCKED   | **10** (critical — default of 1 gives ~7% risk)   |
| Aegis USDJPY    | USDJPY 15m      | 1.50%                   | v4.3 LOCKED   | default (1)                                       |
| Striker NAS100  | NAS100 15m      | 0.40%                   | v1 LOCKED     | 10                                                |
