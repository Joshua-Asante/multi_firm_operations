# Portfolio MC — Aegis 2.00% sensitivity (scenario)

**Date:** 2026-04-20
**Scenario:** Guardian 0.30% / Striker 1.00% / **Aegis 2.00%** (vs baseline 1.50%)
**Strategies:** Guardian v5.4 / Striker v4.4 / Aegis v4.2 (same locks as baseline run)
**Compare against:** [portfolio_mc_2026-04-20_v5.4_v4.4_v4.2.md](portfolio_mc_2026-04-20_v5.4_v4.4_v4.2.md)

Note: this is a **scenario override** — `ALLOCATIONS` in [portfolio_mc.py:42](portfolio_mc.py:42) and `BASE_RISK` in [dd_protection.py:42](dd_protection.py:42) still hold Aegis at 1.50%. Source of truth unchanged.

---

## 1. Scale factor impact

| Strategy | Allocation | 1R ($) | Scale (baseline 1.50%) | Scale (scenario 2.00%) |
|---|---:|---:|---:|---:|
| Guardian | 0.30% | 988 | 0.607 | 0.607 |
| Striker  | 1.00% | 5,308 | 0.377 | 0.377 |
| **Aegis** | **2.00%** | 3,374 | **0.889** | **1.186** |

Aegis scale bumps from 0.889× to 1.186× (+33%). Guardian/Striker unchanged.

---

## 2. Headline comparison

| Metric | Aegis 1.50% (baseline) | Aegis 2.00% (scenario) | Δ |
|---|---:|---:|---:|
| **Pass** | 95.06% (σ 0.11%) | **95.32% (σ 0.13%)** | +0.26 pp |
| Bust (total) | 0.68% (σ 0.05%) | **1.24% (σ 0.11%)** | **+0.56 pp (~1.8×)** |
|   Static-DD bust | 0.68% | 1.24% | +0.56 pp |
|   Daily-limit bust | 0.00% | 0.00% | — |
| Timeout | 4.26% | 3.43% | −0.83 pp |
| Median days to pass | 28 | 26 | −2 |
| p50 DD | 1.54% | 1.54% | — |
| p95 DD | 3.97% | 4.31% | +0.34 pp |
| **p99 DD** | **4.96%** | **5.15%** | **+0.19 pp** |

Pass rate is essentially flat (+0.26pp, inside 2σ of seed noise). **Bust rate nearly doubles.** Timeout drops because higher risk = faster exits (pass or bust). Median pass is 2 days faster.

---

## 3. Bust attribution

| Strategy | Aegis 1.50% | Aegis 2.00% | Δ |
|---|---:|---:|---:|
| Aegis    | 30.4% | **44.2%** | +13.8 pp |
| Striker  | 37.3% | 31.6% | −5.7 pp |
| Guardian | 32.4% | 24.1% | −8.3 pp |

As expected: Aegis contributes more to busts when its size is larger. It's now the #1 bust culprit.

---

## 4. Tail risk flag

**p99 DD = 5.15% exceeds the 5.00% FXIFY static DD limit.**

Mechanically, this is consistent with the 1.24% static-DD bust rate — at Aegis 2%, ~1% of the tail touches the static wall hard enough to terminate. The 0.40× protection scaler clamps most of the exposure, but not all of it.

At Aegis 1.50%, p99 DD was 4.96% — just inside the 5% limit. The 2% scenario pushes the tail across the threshold.

---

## 5. Historical 2022-start replay

| Metric | Aegis 1.50% | Aegis 2.00% |
|---|---:|---:|
| Outcome | PASS | PASS |
| Day terminated | 161 (2022-08-16) | **286 (2023-02-07)** |
| Max DD | 2.22% | **3.08%** |
| DD tier trigger days | 112 | 200 |

Deterministic walk still passes, but takes 125 more days and triggers the DD protection tier 88 more times. The portfolio spends more time throttled to 0.40×, which drags out the climb to +5%.

---

## 6. Interpretation

**What Aegis 2% buys you:** ~2 days faster median pass, 0.26pp higher pass rate.
**What it costs:** bust rate roughly doubles (0.68% → 1.24%), p99 DD crosses the FXIFY static limit, and Aegis becomes the dominant tail contributor (44% of busts).

The pass-rate gain is noise-level. The bust-rate increase is real. **This is a bad trade.**

If the goal is to accelerate the challenge, allocation changes to Guardian or Striker would be a cleaner lever — both have lower bust-share currently and lots of headroom relative to Aegis, which is already the volatility leader in the panel.

---

## 7. Recommendation

**Do not move Aegis to 2%.** The 1.50% lock set (95.06% pass / 0.68% bust) is the better point on the frontier.

If you still want to explore, consider:
- Aegis 1.75% (halfway) — would likely put bust ~0.95% with pass still ~95.2%.
- Running `--sensitivity` against `DD_TRIGGER` instead, to see if a tighter trigger (e.g. 0.5%) buys back the tail budget.

Neither of these requires code changes — both are scenario overrides like this one.

---

## Appendix — raw output

```
Scale factors:
  guardian  1R=$ 988.00  scale= 0.607  n=224
  striker   1R=$5,308.09  scale= 0.377  n=240
  aegis     1R=$3,373.92  scale= 1.186  n=136
Historical panel: 2022-01-04 -> 2026-04-17  (1119 bdays, 223 week-blocks)

=== Portfolio MC ===
Config: DD 1.0% / 0.4× (single-tier)
Allocations: G 0.30% / S 1.00% / A 2.00%
Sims: 10,000 × 3 seeds, horizon 150 days

Pass:         95.32% (sigma 0.13%)
Bust:          1.24% (sigma 0.11%)
  Daily:       0.00%
  Static:      1.24%
Timeout:       3.43%
Median days to pass: 26
p50 DD:       1.54%
p95 DD:       4.31%
p99 DD:       5.15%

Bust attribution:
  Aegis      44.2%
  Striker    31.6%
  Guardian   24.1%

=== Portfolio MC — Historical (deterministic) ===
Config: DD 1.0% / 0.4× (single-tier)
Allocations: G 0.30% / S 1.00% / A 2.00%
Outcome:         PASS
Day terminated:  286 (2023-02-07)
Max DD:          3.08%
DD tier trigger days (through terminating day): 200
```
