# ADR: Aegis session selection — 10:00–13:45, Mon/Tue/Wed

**Date:** 2026-03-01 _(approximate — originally decided during Aegis v4 development; carried forward unchanged into v4.1)_
**Status:** Accepted
**Scope:** Aegis-Reversion strategy (USDJPY 15min mean-reversion)

## Context

Mean-reversion edge on USDJPY is regime-dependent and session-dependent in a way that trend strategies on other instruments are not. USDJPY trades across three major sessions (Tokyo, London, NY) with distinct flow characteristics:
- **Tokyo session:** dominated by Japanese corporate flows and BoJ-sensitive positioning; often trending on BoJ or MoF news, mean-reverting otherwise.
- **London open to fix:** highest liquidity, but structural flows (London fix at 16:00 London / 11:00 ET) produce directional pressure that violates mean-reversion assumptions.
- **NY session:** overlaps with London late-morning, then thins out; afternoon is often directional continuation on US data.

The strategy's edge is measurable only in specific windows where reversion flow dominates directional flow.

Day-of-week effects are also material: end-of-week (Thu/Fri) sees weekend-risk repositioning and option-expiry flows that contaminate mean-reversion setups.

## Decision

Session window: **10:00–13:45 ET**, Monday / Tuesday / Wednesday only.

## Alternatives considered

- **Full 24-hour window.** Rejected — Tokyo overnight sessions dilute edge significantly; Asian range-trading behavior is different in character from the post-Tokyo reversion pattern the strategy captures.
- **London-open window (03:00–07:00 ET).** Rejected — directional flow dominance during London open violates the mean-reversion assumption the strategy relies on.
- **NY-only window (09:30–16:00 ET).** Tested — broader NY window introduces directional afternoon flows and London-fix distortion at 11:00. Narrower window (10:00–13:45) cleaner.
- **Mon–Fri days.** Rejected — Thu/Fri backtest performance materially worse due to weekend-risk flows and end-of-week option positioning. Removing Thu/Fri improved risk-adjusted returns.
- **Mon/Tue only.** Tested — loses meaningful trade count without improving per-trade edge. Wednesday adds trades at comparable quality.

## Consequences

Positive:
- Clean edge window: post-Tokyo-close / pre-London-fix USDJPY mean-reversion regime.
- v4 backtest under this session: Net ~$62K, PF 2.28, WR 59.9%, Max DD 3.46%.
- Structural countercyclicality with Guardian and Striker — Aegis's edge-window flow dynamics are uncorrelated with trend-strategy flow assumptions.

Negative:
- Low trade count by design. Aegis fires less often than Guardian or Striker. Individual session outcomes have higher variance as a result.
- Narrow window means the strategy is idle most of the week. Requires discipline to not chase edge outside the defined window.

Risks:
- **BOJ April 28, 2026 meeting** is a binary vol event that could shift USDJPY regime. If post-meeting regime is sustained trending (BoJ tightening shock or dovish surprise producing extended drift), Aegis's session window may temporarily stop producing edge. Monitor, do not preemptively change session.
- DST transitions shift the effective GMT window. Confirm session times align with intended post-Tokyo-close / pre-London-fix flows after each DST change.
- Iran-Israel conflict regime has produced violent USDJPY round-trips that Aegis has benefited from (yen safe-haven bid capture). Ceasefire scenarios may compress this dynamic.

## Cross-references

- Notion: FXIFY Command Center — live parameter source of truth
- Code: `strategies/aegis/aegis_usdjpy_v4.3.txt` (decision was made against v4.1; session-selection logic carried forward unchanged through v4.3)
- Related: ADR 2026-04-17-portfolio-allocations (Aegis 1.50% allocation rationale)
- Related: `docs/overlays/guardian_conflict_risk.md` (conflict regime context affects Aegis positively)
