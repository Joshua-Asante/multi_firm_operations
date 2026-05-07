"""Generate equity curves for Phase 3 best-train configurations.

For both frameworks, plot train + OOS equity (in cumulative R) with the
boundary marked. Used in 2026-04-26_audnzd_framework_screen.md.
"""
from __future__ import annotations

import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from audnzd_phase3_backtest import (
    load_data, add_indicators, simulate, compute_metrics,
    TRAIN_START, TRAIN_END, OOS_START, OOS_END, set_slippage, verify_hash,
)

RESULTS_JSON = REPO_ROOT / "docs" / "methodology" / "findings" / "2026-04-26_audnzd_phase3_results.json"
PLOTS_DIR = REPO_ROOT / "docs" / "methodology" / "findings"


def main() -> int:
    verify_hash()
    df = load_data()
    df_train = df[(df["dt_utc"] >= TRAIN_START) & (df["dt_utc"] < TRAIN_END)].reset_index(drop=True)
    df_oos   = df[(df["dt_utc"] >= OOS_START)   & (df["dt_utc"] < OOS_END)].reset_index(drop=True)

    results = json.loads(RESULTS_JSON.read_text())
    set_slippage(2.0)

    for fw in ("aegis", "rangefade"):
        if "best_params" not in results.get(fw, {}):
            continue
        p = results[fw]["best_params"]

        di_train = add_indicators(df_train, p["bb_period"], p["bb_std"], p["atr_period"])
        di_oos   = add_indicators(df_oos,   p["bb_period"], p["bb_std"], p["atr_period"])
        tr_train = simulate(di_train, p, fw)
        tr_oos   = simulate(di_oos,   p, fw)

        eq_train = np.cumsum([t.pnl_r for t in tr_train])
        eq_oos = np.cumsum([t.pnl_r for t in tr_oos])

        fig, axes = plt.subplots(1, 2, figsize=(11, 3.6), sharey=False)
        if len(eq_train):
            t_train = pd.to_datetime([t.exit_time for t in tr_train])
            axes[0].plot(t_train, eq_train, lw=1)
            axes[0].axhline(0, color="black", lw=0.5)
            axes[0].set_title(f"{fw} TRAIN  (n={len(tr_train)}, "
                              f"PF={results[fw]['train_metrics']['pf']:.2f}, "
                              f"final={eq_train[-1]:.1f}R)")
            axes[0].set_ylabel("cumulative R")
            axes[0].grid(True, alpha=0.3)
        if len(eq_oos):
            t_oos = pd.to_datetime([t.exit_time for t in tr_oos])
            axes[1].plot(t_oos, eq_oos, lw=1, color="orange")
            axes[1].axhline(0, color="black", lw=0.5)
            axes[1].set_title(f"{fw} OOS  (n={len(tr_oos)}, "
                              f"PF={results[fw]['oos_metrics']['pf']:.2f}, "
                              f"final={eq_oos[-1]:.1f}R)")
            axes[1].set_ylabel("cumulative R")
            axes[1].grid(True, alpha=0.3)
        plt.suptitle(f"AUDNZD {fw} — equity curve (slippage 2.0 pips)")
        plt.tight_layout()
        out = PLOTS_DIR / f"2026-04-26_audnzd_phase3_equity_{fw}.png"
        plt.savefig(out, dpi=120)
        plt.close()
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
