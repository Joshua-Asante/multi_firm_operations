"""Plot the MC anchor evolution charts.

Reads data.csv in this directory and emits 4 PNGs:
  pass_trajectory.png       — pass-rate over five anchors + OANDA overlay
  bust_trajectory.png       — bust-rate + dashed 1% lock gate
  p99_dd_trajectory.png     — p99 DD + dashed 5% lock gate
  bust_attribution.png      — stacked bust attribution across anchors

Determinism: no random numbers. matplotlib defaults only.
Reproduce:  python docs/analytics/mc_anchor_evolution/plot.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
CSV = HERE / "data.csv"

df = pd.read_csv(CSV)
# The "Pepperstone trajectory" in the user's framing starts at the 2026-04-17
# Alchemy-panel calibration anchor; the panel migrated to Pepperstone at
# 2026-04-23. The Alchemy anchor is included as the trajectory baseline and
# labeled explicitly. See ADR 2026-04-23-guardian-risk-relock-0.34 §Context.
pep = df[df["panel"].isin(("alchemy", "pepperstone"))].reset_index(drop=True)
oan = df[df["panel"] == "oanda"].reset_index(drop=True)

# Position pre/post 05-05 reconcile pair side-by-side; otherwise spaced by anchor.
xs = list(range(len(pep)))
xlabels = [
    f"{r.date}\n{r.label.split(' (')[0]}" for r in pep.itertuples()
]
short = ["2026-04-17\ninitial\n(Alchemy)",
         "2026-04-23\nPep re-lock\n0.34",
         "2026-05-05\n4-strat C0\n(pre)",
         "2026-05-05\n4-strat C0\n(post)",
         "2026-05-08\nC2 relock\n(all-data)",
         "2026-05-14\npanel-refresh\n(revert tgt)",
         "2026-05-14\nalloc refresh\n(150-day)",
         "2026-05-16\nFXIFY-correct\n(canonical)"]

# OANDA overlay maps to Pepperstone anchor x positions by date+anchor_id.
oanda_xmap = {("2026-05-05", "O4"): 3,
              ("2026-05-08", "O5"): 4,
              ("2026-05-14", "O7"): 6,
              ("2026-05-16", "O8"): 7}
oanda_x = [oanda_xmap[(d, aid)] for d, aid in zip(oan["date"], oan["anchor_id"])]


def _annotate(ax, x, y, txt, dy=0):
    ax.annotate(txt, (x, y), textcoords="offset points",
                xytext=(0, 8 + dy), ha="center", fontsize=8)


def plot_metric(metric_col, ylabel, gate_value, gate_label, fname, ylim=None,
                lower_better=False):
    fig, ax = plt.subplots(figsize=(13.0, 5.8))

    ys = pep[metric_col].astype(float).tolist()
    ax.plot(xs, ys, marker="o", color="#1f77b4", linewidth=2.0,
            label="Pepperstone (canonical)")
    for x, y in zip(xs, ys):
        _annotate(ax, x, y, f"{y:.2f}")

    # OANDA overlay
    oys = oan[metric_col].astype(float).tolist()
    ax.plot(oanda_x, oys, marker="s", color="#ff7f0e", linewidth=1.5,
            linestyle="--", label="OANDA (pattern-spotting)")
    for x, y in zip(oanda_x, oys):
        _annotate(ax, x, y, f"{y:.2f}", dy=-22)

    # Gate line
    if gate_value is not None:
        ax.axhline(gate_value, color="#d62728", linestyle=":", linewidth=1.6,
                   label=gate_label)

    ax.set_xticks(xs)
    ax.set_xticklabels(short, fontsize=8)
    ax.set_ylabel(ylabel)
    ax.set_xlabel("Anchor")
    ax.set_title(f"MC anchor evolution — {ylabel}")
    if ylim:
        ax.set_ylim(*ylim)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(HERE / fname, dpi=130)
    plt.close(fig)


# Pass-rate: higher is better, no hard gate (informational; 100% upper bound)
plot_metric("pass_pct", "Pass rate (%)", None, None, "pass_trajectory.png",
            ylim=(90, 100))

# Bust: lower is better; lock gate < 1.0%
plot_metric("bust_total_pct", "Bust rate (%)", 1.0,
            "Lock gate (< 1.00%)", "bust_trajectory.png",
            ylim=(0, 1.8), lower_better=True)

# p99 DD: lower is better; lock gate < 5.0%
plot_metric("p99_dd_pct", "p99 drawdown (%)", 5.0,
            "Lock gate (< 5.00%)", "p99_dd_trajectory.png",
            ylim=(4.0, 5.2), lower_better=True)


# Bust attribution stacked bar
def plot_attribution():
    cols = ["attrib_guardian", "attrib_striker_dj30",
            "attrib_aegis", "attrib_striker_nas100"]
    labels = ["Guardian (XAUUSD)", "Striker DJ30", "Aegis (USDJPY)",
              "Striker NAS100"]
    colors = ["#d4a017", "#2ca02c", "#9467bd", "#1f77b4"]

    fig, ax = plt.subplots(figsize=(13.0, 5.8))

    attrib = pep[cols].astype(float).fillna(0.0).values
    has_data = pep[cols].notna().any(axis=1).values

    bottoms = np.zeros(len(pep))
    for i, (lab, color) in enumerate(zip(labels, colors)):
        vals = np.where(has_data, attrib[:, i], 0.0)
        bars = ax.bar(xs, vals, bottom=bottoms, label=lab, color=color,
                      width=0.62, edgecolor="white", linewidth=0.6)
        # Inline value labels (only when meaningful, > 4 pp)
        for j, (b, v) in enumerate(zip(bars, vals)):
            if v >= 4.0 and has_data[j]:
                ax.text(b.get_x() + b.get_width() / 2,
                        bottoms[j] + v / 2, f"{v:.1f}",
                        ha="center", va="center", fontsize=8, color="white",
                        fontweight="bold")
        bottoms = bottoms + vals

    # Mark anchors without published attribution
    for j in range(len(pep)):
        if not has_data[j]:
            ax.text(xs[j], 50, "attribution\nnot published",
                    ha="center", va="center", fontsize=8,
                    style="italic", color="#555555",
                    bbox=dict(facecolor="#eeeeee", edgecolor="#cccccc",
                              boxstyle="round,pad=0.4"))

    ax.set_xticks(xs)
    ax.set_xticklabels(short, fontsize=8)
    ax.set_ylabel("Bust attribution share (%)")
    ax.set_xlabel("Anchor")
    ax.set_title("MC anchor evolution — bust attribution by strategy")
    ax.set_ylim(0, 105)
    ax.grid(True, alpha=0.3, axis="y")
    ax.legend(loc="lower right", fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(HERE / "bust_attribution.png", dpi=130)
    plt.close(fig)


plot_attribution()

print(f"wrote 4 charts to {HERE}")
