"""Render the committed benchmark tables, without hardcoded result values."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "evidence/full"
m = json.loads((p / "metrics.json").read_text())
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titleweight": "bold",
    }
)
fig, axes = plt.subplots(1, 3, figsize=(15, 5), facecolor="#f7fafc")
fig.suptitle(
    "CommercePulse • Measured performance & explicit assumptions",
    fontsize=18,
    fontweight="bold",
    x=0.06,
    ha="left",
)
axes[0].bar(
    ["Trend + weekday", "Seasonal baseline"],
    [m["forecast"]["wape"] * 100, m["forecast"]["seasonal_naive_wape"] * 100],
    color=["#087f8c", "#a9b8c7"],
)
axes[0].set(title="28-day demand holdout", ylabel="WAPE (%) · lower is better")
r = pd.read_csv(p / "retention_sensitivity.csv")
axes[1].bar(
    ["2 pp", "4 pp", "6 pp"],
    r.modeled_net_contribution_eur / 1000,
    color=["#a9b8c7", "#087f8c", "#087f8c"],
)
axes[1].axhline(0, color="#334155", linewidth=0.7)
axes[1].set(
    title="Retention sensitivity",
    xlabel="Assumed incremental purchase probability",
    ylabel="Modeled net contribution (€ thousands)",
)
i = pd.read_csv(p / "inventory_allocation.csv")
axes[2].bar(i.market, i.modeled_recovery_eur / 1000, color="#087f8c")
axes[2].set(title="Constrained inventory allocation", ylabel="Modeled recovery (€ thousands)")
fig.text(
    0.06,
    0.025,
    "Synthetic portfolio evidence. Forecast fixture is independent of the 8M-event stream. Business scenarios are not realized returns.",
    fontsize=10,
    color="#475569",
)
fig.tight_layout(rect=(0.03, 0.08, 1, 0.92), w_pad=3)
fig.savefig(p / "evaluation.png", dpi=150)
