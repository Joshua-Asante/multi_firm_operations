"""
Q-DDP-1 Step 4 — Pareto frontier plot.

(pass_rate, expected_drag) plane with all 5 configs and bootstrap robustness
halos for surviving candidates. Reads sweep_results.csv and
regime_robustness.csv, writes pareto_frontier.svg.
"""
from __future__ import annotations

import os
import sys

# Force this worktree's portfolio_mc (sibling worktrees may have stale editable installs)
_THIS_WORKTREE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, _THIS_WORKTREE)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def main():
    sweep = pd.read_csv("docs/briefs/Q-DDP-1/sweep_results.csv")
    regime = pd.read_csv("docs/briefs/Q-DDP-1/regime_robustness.csv")

    # Aggregate rows only (one per config)
    agg = sweep[sweep["seed"] == "AGGREGATE"].copy()
    agg = agg.sort_values("config_id").reset_index(drop=True)

    # Bootstrap pass-rates per config (only candidates that passed Step 2 strictly)
    bootstrap = regime[regime["analysis"] == "bootstrap"].copy()

    fig, ax = plt.subplots(figsize=(9, 6.5))

    # Plot all 5 configs as scatter points; pass-rate vs realized drag (% of unprotected)
    colors = {"C0": "#222222", "C1": "#1f77b4", "C2": "#2ca02c", "C3": "#ff7f0e", "C4": "#d62728"}
    for _, row in agg.iterrows():
        cid = row["config_id"]
        x = row["pass_rate"] * 100  # to %
        y = row["realized_drag_pct_of_unprotected_pnl"] * 100  # to %
        marker = "o"
        size = 140
        ax.scatter(x, y, c=colors[cid], s=size, marker=marker,
                   edgecolors="black", linewidths=0.8, zorder=3)
        # Label
        offset = (0.005, 0.5)
        ax.annotate(
            f"{cid}\n({row['dd_trigger']:.1%}/{row['dd_scale']}×)",
            xy=(x, y), xytext=(x + offset[0], y + offset[1]),
            fontsize=9, ha="left", va="center", zorder=4,
        )

    # Bootstrap halos for surviving candidates
    if len(bootstrap) > 0:
        for cid in bootstrap["config_id"].unique():
            cfg_boot = bootstrap[bootstrap["config_id"] == cid]
            row = agg[agg["config_id"] == cid].iloc[0]
            y_center = row["realized_drag_pct_of_unprotected_pnl"] * 100
            # Plot bootstrap pass-rate distribution as horizontal error band at y_center
            xs = cfg_boot["pass_rate"].values * 100
            p05 = np.percentile(xs, 5)
            p95 = np.percentile(xs, 95)
            ax.plot([p05, p95], [y_center, y_center], color=colors[cid],
                    linewidth=2.5, alpha=0.4, zorder=2,
                    solid_capstyle="butt")
            # 5th-pctile mark
            ax.scatter([p05], [y_center], color=colors[cid], marker="|",
                       s=200, linewidths=2, alpha=0.7, zorder=2)

    # Acceptance criteria reference lines
    ax.axvline(97.5, color="gray", linestyle=":", linewidth=1, alpha=0.6,
               label="Pass-rate floor (97.5%, adjusted)")
    ax.axvline(97.9, color="gray", linestyle="--", linewidth=1, alpha=0.4,
               label="Pass-rate floor (97.9%, brief original)")
    # Reference line at C0 drag = 100% reference (drag savings start there)
    c0_drag = agg[agg["config_id"] == "C0"]["realized_drag_pct_of_unprotected_pnl"].iloc[0] * 100
    ax.axhline(c0_drag * 0.9, color="orange", linestyle=":", linewidth=1, alpha=0.5,
               label=f"Drag-savings floor (≤90% of C0 drag = {c0_drag * 0.9:.1f}%)")

    ax.set_xlabel("Pass rate (%)", fontsize=11)
    ax.set_ylabel("Realized drag vs unprotected (% of unprotected PnL)", fontsize=11)
    ax.set_title("Q-DDP-1 — dd_protection relaxation Pareto frontier\n"
                 "(Pepperstone full panel 2022-01 → 2026-04, 4-strategy lock)",
                 fontsize=12)
    ax.grid(True, alpha=0.3, zorder=1)
    ax.legend(loc="lower left", fontsize=8.5, framealpha=0.85)

    # y-axis: drag is negative; flip so "less drag" reads up
    ax.invert_yaxis()

    plt.tight_layout()
    plt.savefig("docs/briefs/Q-DDP-1/pareto_frontier.svg", format="svg")
    plt.savefig("docs/briefs/Q-DDP-1/pareto_frontier.png", format="png", dpi=130)
    print("Wrote docs/briefs/Q-DDP-1/pareto_frontier.svg + .png")


if __name__ == "__main__":
    main()
