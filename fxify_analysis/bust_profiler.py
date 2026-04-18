"""
Bust Profiler — Profile DD bust scenarios from Monte Carlo simulation.

Re-runs 10K sims with DD protection and S@0.60%, captures every bust,
and extracts per-bust and aggregate diagnostics.

Usage:
    python bust_profiler.py
"""

import numpy as np
import pandas as pd
from collections import Counter

from config import STRATEGIES, MONTE_CARLO
from master_analysis import load_all_strategies, scale_profit


def profile_busts():
    print("Loading strategies...")
    all_trades = load_all_strategies()

    overrides = {"guardian": 0.30, "striker": 0.60, "aegis": 0.75}

    # Build combined profit/strategy arrays
    all_profits = []
    for key, trades in all_trades.items():
        original_risk = STRATEGIES[key]["risk_pct_challenge"]
        new_risk = overrides.get(key, original_risk)
        for _, trade in trades.iterrows():
            scaled_p = scale_profit(trade["profit"], original_risk, new_risk)
            all_profits.append({
                "profit": scaled_p,
                "strategy": key,
            })

    profits_df = pd.DataFrame(all_profits)
    profit_array = profits_df["profit"].values
    strategy_array = profits_df["strategy"].values

    account = MONTE_CARLO["account_size"]
    target = account * (MONTE_CARLO["target_pct"] / 100)
    dd_limit = account * (MONTE_CARLO["dd_limit_pct"] / 100)
    n_sims = MONTE_CARLO["n_simulations"]

    # DD protection thresholds
    DD_THRESH = 0.02
    DD_MULT = 0.40
    EQ_THRESH = 0.035
    EQ_MULT = 0.60

    np.random.seed(MONTE_CARLO["seed"])

    busts = []

    for sim in range(n_sims):
        perm = np.random.permutation(len(profit_array))
        shuffled_profits = profit_array[perm]
        shuffled_strats = strategy_array[perm]

        equity = 0.0
        peak = 0.0
        passed = False
        busted = False

        dd_prot_first_trade = None  # trade index when DD protection first triggered
        peak_before_bust = 0.0
        trade_log = []  # (strategy, raw_pnl, scaled_pnl, equity_after, peak, dd_pct, mult)

        for i in range(len(shuffled_profits)):
            raw_pnl = shuffled_profits[i]
            strat = shuffled_strats[i]

            # DD protection
            dd_from_peak = (peak - equity) / account if equity < peak else 0.0
            gain_from_start = equity / account

            if dd_from_peak >= DD_THRESH and gain_from_start >= EQ_THRESH:
                mult = min(DD_MULT, EQ_MULT)
            elif dd_from_peak >= DD_THRESH:
                mult = DD_MULT
            elif gain_from_start >= EQ_THRESH:
                mult = EQ_MULT
            else:
                mult = 1.0

            if mult < 1.0 and dd_prot_first_trade is None:
                dd_prot_first_trade = i

            pnl = raw_pnl * mult
            equity += pnl
            peak = max(peak, equity)
            dd = peak - equity
            dd_pct = dd / account * 100

            trade_log.append({
                "idx": i,
                "strategy": strat,
                "raw_pnl": raw_pnl,
                "scaled_pnl": pnl,
                "mult": mult,
                "equity": equity,
                "peak": peak,
                "dd_pct": dd_pct,
            })

            if equity >= target:
                passed = True
                break

            if dd >= dd_limit:
                busted = True
                break

        if not busted:
            continue

        # ── Analyze this bust ──
        log_df = pd.DataFrame(trade_log)
        bust_trade = len(log_df) - 1
        est_bust_day = max(1, int(np.ceil((bust_trade + 1) / 2.5)))

        # Peak equity before the final drawdown leg
        peak_eq = log_df["peak"].max()

        # Find where the final drawdown leg started (last time equity == peak)
        peak_indices = log_df[log_df["equity"] == log_df["peak"]].index
        if len(peak_indices) > 0:
            dd_leg_start = peak_indices[-1]
        else:
            dd_leg_start = 0

        dd_leg = log_df.iloc[dd_leg_start:]

        # Which strategy drove the terminal DD (largest single loss in the leg)
        worst_trade_in_leg = dd_leg.loc[dd_leg["scaled_pnl"].idxmin()]
        driver_strategy = worst_trade_in_leg["strategy"]
        driver_loss = worst_trade_in_leg["scaled_pnl"]

        # DD protection timing
        if dd_prot_first_trade is not None:
            dd_prot_day = max(1, int(np.ceil((dd_prot_first_trade + 1) / 2.5)))
            prot_triggered_before = dd_prot_first_trade < bust_trade
        else:
            dd_prot_day = None
            prot_triggered_before = False

        # Timing bucket
        if est_bust_day <= 5:
            timing = "early"
        elif est_bust_day <= 15:
            timing = "mid"
        else:
            timing = "late"

        # Consecutive loss streak leading into bust (last N trades before bust)
        lookback = log_df.iloc[max(0, bust_trade - 30):bust_trade + 1]
        is_loss = lookback["scaled_pnl"] < 0

        # Max consecutive losses across all strategies
        max_consec = 0
        streak = 0
        for v in is_loss.values:
            if v:
                streak += 1
                max_consec = max(max_consec, streak)
            else:
                streak = 0

        # Per-strategy consecutive losses in the bust window (last 15 trades)
        bust_window = log_df.iloc[max(0, bust_trade - 15):bust_trade + 1]
        strat_3plus_consec = []
        for s in ["guardian", "striker", "aegis"]:
            s_trades = bust_window[bust_window["strategy"] == s]["scaled_pnl"]
            streak = 0
            max_s = 0
            for v in s_trades.values:
                if v < 0:
                    streak += 1
                    max_s = max(max_s, streak)
                else:
                    streak = 0
            if max_s >= 3:
                strat_3plus_consec.append(f"{s}({max_s})")

        # Same-day multi-strategy losses in the DD leg
        # Approximate: trades within 2 indices of each other from different strategies
        multi_strat_cluster = False
        for j in range(len(dd_leg) - 1):
            for k in range(j + 1, min(j + 3, len(dd_leg))):
                row_j = dd_leg.iloc[j]
                row_k = dd_leg.iloc[k]
                if (row_j["scaled_pnl"] < 0 and row_k["scaled_pnl"] < 0
                        and row_j["strategy"] != row_k["strategy"]):
                    multi_strat_cluster = True
                    break
            if multi_strat_cluster:
                break

        busts.append({
            "sim": sim,
            "bust_day": est_bust_day,
            "timing": timing,
            "peak_equity": account + peak_eq,
            "peak_pnl_pct": peak_eq / account * 100,
            "driver": driver_strategy,
            "driver_loss": driver_loss,
            "dd_leg_trades": len(dd_leg),
            "dd_prot_day": dd_prot_day,
            "prot_triggered_before": prot_triggered_before,
            "max_consec_loss": max_consec,
            "strat_3plus_consec": ", ".join(strat_3plus_consec) if strat_3plus_consec else "none",
            "multi_strat_cluster": multi_strat_cluster,
        })

    # ═══════════════════════════════════════════════
    #  OUTPUT
    # ═══════════════════════════════════════════════

    n_busts = len(busts)
    print(f"\n{'=' * 80}")
    print(f"  BUST PROFILER — {n_busts} busts out of {n_sims:,} sims")
    print(f"  Allocations: G0.30% / S0.60% / A0.75% + DD Protection")
    print(f"{'=' * 80}")

    if n_busts == 0:
        print("  No busts to profile.")
        return

    # ── Per-Bust Table ──
    print(f"\n  {'#':>3}  {'Sim':>5}  {'Day':>4}  {'Phase':>5}  {'Peak$':>10}  "
          f"{'Driver':>10}  {'Loss$':>9}  {'Leg':>4}  "
          f"{'DDProt':>6}  {'Consec':>6}  {'3+Strat':>12}  {'Multi':>5}")
    print("  " + "-" * 100)

    for i, b in enumerate(busts):
        prot_str = f"d{b['dd_prot_day']}" if b['dd_prot_day'] is not None else "never"
        print(f"  {i+1:>3}  {b['sim']:>5}  {b['bust_day']:>4}  {b['timing']:>5}  "
              f"${b['peak_equity']:>9,.0f}  "
              f"{b['driver']:>10}  ${b['driver_loss']:>8,.0f}  {b['dd_leg_trades']:>4}  "
              f"{prot_str:>6}  {b['max_consec_loss']:>6}  "
              f"{b['strat_3plus_consec']:>12}  {'Y' if b['multi_strat_cluster'] else 'N':>5}")

    # ── Aggregate Analysis ──
    bust_df = pd.DataFrame(busts)

    print(f"\n{'=' * 80}")
    print(f"  AGGREGATE ANALYSIS")
    print(f"{'=' * 80}")

    # Timing distribution
    print(f"\n  -- Timing Distribution --")
    for bucket in ["early", "mid", "late"]:
        count = (bust_df["timing"] == bucket).sum()
        pct = count / n_busts * 100
        print(f"  {bucket:>5} (d1-5/6-15/16+):  {count:>3} busts ({pct:.0f}%)")

    # Primary driver
    print(f"\n  -- Primary Driver (largest loss in DD leg) --")
    driver_counts = bust_df["driver"].value_counts()
    for strat, count in driver_counts.items():
        pct = count / n_busts * 100
        avg_loss = bust_df[bust_df["driver"] == strat]["driver_loss"].mean()
        print(f"  {strat:>10}:  {count:>3} busts ({pct:.0f}%), "
              f"avg terminal loss ${avg_loss:,.0f}")

    # DD protection timing
    print(f"\n  -- DD Protection Timing --")
    prot_before = bust_df["prot_triggered_before"].sum()
    prot_never = bust_df["dd_prot_day"].isna().sum()
    prot_too_late = n_busts - prot_before - prot_never
    print(f"  Triggered before bust:  {prot_before:>3} ({prot_before/n_busts*100:.0f}%)")
    print(f"  Never triggered:        {prot_never:>3} ({prot_never/n_busts*100:.0f}%)")
    print(f"  Triggered same trade:   {prot_too_late:>3} ({prot_too_late/n_busts*100:.0f}%)")

    prot_days = bust_df["dd_prot_day"].dropna()
    bust_days = bust_df["bust_day"]
    if len(prot_days) > 0:
        print(f"\n  Avg DD protection trigger day:  {prot_days.mean():.1f}")
        print(f"  Avg bust day:                  {bust_days.mean():.1f}")
        runway = bust_days.values - bust_df["dd_prot_day"].fillna(bust_days).values
        print(f"  Avg runway (bust - trigger):   {runway.mean():.1f} days")

    # Peak equity before bust
    print(f"\n  -- Peak Equity Before Bust --")
    print(f"  Avg peak:   ${bust_df['peak_equity'].mean():,.0f} "
          f"({bust_df['peak_pnl_pct'].mean():.2f}% above start)")
    print(f"  Max peak:   ${bust_df['peak_equity'].max():,.0f}")
    print(f"  Min peak:   ${bust_df['peak_equity'].min():,.0f} "
          f"({'never profitable' if bust_df['peak_pnl_pct'].min() <= 0 else 'was profitable'})")

    # Consecutive losses
    print(f"\n  -- Loss Streaks --")
    print(f"  Avg max consecutive losses before bust: {bust_df['max_consec_loss'].mean():.1f}")
    print(f"  Max consecutive losses seen:            {bust_df['max_consec_loss'].max()}")
    has_3plus = (bust_df["strat_3plus_consec"] != "none").sum()
    print(f"  Busts with 3+ consec from one strategy: {has_3plus}/{n_busts}")

    # Multi-strategy clustering
    print(f"\n  -- Multi-Strategy Clustering --")
    multi = bust_df["multi_strat_cluster"].sum()
    print(f"  Busts with 2+ strategies losing together in DD leg: "
          f"{multi}/{n_busts} ({multi/n_busts*100:.0f}%)")
    single = n_busts - multi
    print(f"  Busts from sequential single-strategy losses:       "
          f"{single}/{n_busts} ({single/n_busts*100:.0f}%)")

    # DD leg length
    print(f"\n  -- DD Leg Length --")
    print(f"  Avg trades in terminal DD leg: {bust_df['dd_leg_trades'].mean():.1f}")
    print(f"  Min: {bust_df['dd_leg_trades'].min()}, Max: {bust_df['dd_leg_trades'].max()}")

    # Actionable summary
    print(f"\n{'=' * 80}")
    print(f"  ACTIONABLE FINDINGS")
    print(f"{'=' * 80}")

    early_pct = (bust_df["timing"] == "early").mean() * 100
    if early_pct > 50:
        print(f"\n  !! {early_pct:.0f}% of busts are EARLY-PHASE (days 1-5).")
        print(f"     -> Consider a conservative first-week overlay (e.g., 0.50x risk days 1-3).")

    never_pct = prot_never / n_busts * 100
    if never_pct > 30:
        print(f"\n  !! {never_pct:.0f}% of busts happen before DD protection ever triggers.")
        print(f"     -> Protection gap: these are fast crashes from starting equity.")

    if len(driver_counts) > 0:
        top_driver = driver_counts.index[0]
        top_pct = driver_counts.iloc[0] / n_busts * 100
        if top_pct > 60:
            print(f"\n  !! {top_driver} drives {top_pct:.0f}% of all busts.")
            print(f"     -> Consider further risk reduction or a per-strategy daily loss cap.")

    if multi / n_busts > 0.5:
        print(f"\n  !! {multi/n_busts*100:.0f}% of busts involve multi-strategy clustering.")
        print(f"     -> Cross-strategy cooldown may help (skip strategy B after A stops out).")
    elif single / n_busts > 0.7:
        print(f"\n  !! {single/n_busts*100:.0f}% of busts are single-strategy sequential losses.")
        print(f"     -> Per-strategy daily loss circuit breaker would be most effective.")

    print()


if __name__ == "__main__":
    profile_busts()
