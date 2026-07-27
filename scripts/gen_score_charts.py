#!/usr/bin/env python3
"""Generate README trial-score PNGs (run via Docker)."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

OUT = Path(__file__).resolve().parents[1] / "docs" / "assets"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "axes.facecolor": "#FFFCFA",
        "figure.facecolor": "#FFFCFA",
        "axes.edgecolor": "#D6D3D1",
        "axes.labelcolor": "#44403C",
        "xtick.color": "#57534E",
        "ytick.color": "#57534E",
        "text.color": "#1C1917",
        "grid.color": "#E7E5E4",
        "grid.linewidth": 0.8,
    }
)

GENE = "#0F766E"
BASE = "#78716C"
HARD_BASE = "#C2410C"
HARD_GENE = "#115E59"


def finish(ax, title, subtitle, path, handles):
    ax.set_ylim(0, 100)
    ax.set_xlim(0.8, 5.2)
    ax.set_xticks([1, 2, 3, 4, 5])
    ax.set_xlabel("trial")
    ax.set_ylabel("score")
    ax.axhline(90, color="#A8A29E", ls="--", lw=1, zorder=0)
    ax.grid(True, axis="y")
    ax.set_title(title, loc="left", fontsize=13, fontweight="600", pad=22)
    ax.text(0.0, 1.015, subtitle, transform=ax.transAxes, fontsize=9, color="#78716C", va="bottom")
    ax.legend(handles=handles, frameon=False, fontsize=9, loc="lower right", ncol=2)
    fig = ax.figure
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print("wrote", path)


def main():
    x5 = [1, 2, 3, 4, 5]
    x3 = [1, 2, 3]

    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    ax.plot(x5, [69.9, 35.5, 67.2, 55.5, 85.6], color=BASE, lw=2.4, marker="o", ms=6)
    ax.plot(x5, [94.3, 94.4, 96.3, 93.8, 95.0], color=GENE, lw=2.4, marker="s", ms=6)
    ax.plot(x3, [63.05, 79.8, 73.3], color=HARD_BASE, lw=2.4, ls="--", marker="o", ms=6)
    ax.plot(x3, [88.3, 74.4, 83.3], color=HARD_GENE, lw=2.4, ls="--", marker="D", ms=6)
    finish(
        ax,
        "Critical thinking · Kimi 3",
        "basic/hard x baseline/gene  ·  dashed gray = 90",
        OUT / "scores_criticalthinking_kimi3.png",
        [
            Line2D([0], [0], color=BASE, lw=2.4, marker="o", label="basic · baseline"),
            Line2D([0], [0], color=GENE, lw=2.4, marker="s", label="basic · gene"),
            Line2D([0], [0], color=HARD_BASE, lw=2.4, ls="--", marker="o", label="hard · baseline"),
            Line2D([0], [0], color=HARD_GENE, lw=2.4, ls="--", marker="D", label="hard · gene"),
        ],
    )

    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    ax.plot(x5, [97.5, 96.5, 98.4, 57.0, 93.1], color="#94A3B8", lw=2.2, marker="o", ms=5.5)
    ax.plot(x5, [97.2, 97.1, 97.3, 93.7, 97.3], color=GENE, lw=2.2, marker="s", ms=5.5)
    ax.plot(x5, [92.6, 90.0, 91.8, 92.0, 91.8], color="#A8A29E", lw=2.2, ls="--", marker="o", ms=5.5)
    ax.plot(x5, [93.5, 91.7, 94.7, 94.4, 94.7], color="#0D9488", lw=2.2, ls="--", marker="D", ms=5.5)
    finish(
        ax,
        "Other tasks · Kimi 3 · basic x5",
        "task decomposition / work report",
        OUT / "scores_per_trial_kimi3.png",
        [
            Line2D([0], [0], color="#94A3B8", lw=2.2, marker="o", label="decomp · baseline"),
            Line2D([0], [0], color=GENE, lw=2.2, marker="s", label="decomp · gene"),
            Line2D([0], [0], color="#A8A29E", lw=2.2, ls="--", marker="o", label="write · baseline"),
            Line2D([0], [0], color="#0D9488", lw=2.2, ls="--", marker="D", label="write · gene"),
        ],
    )

    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    ax.plot(x5, [85.6, 80.4, 78.1, 80.4, 84.0], color=BASE, lw=2.2, marker="o", ms=5.5)
    ax.plot(x5, [95.5, 96.2, 96.2, 94.6, 93.8], color=GENE, lw=2.2, marker="s", ms=5.5)
    ax.plot(x5, [92.9, 100, 96.7, 96.7, 69.1], color="#94A3B8", lw=2.2, ls="--", marker="o", ms=5.5)
    ax.plot(x5, [97.2, 96.7, 94.2, 96.5, 98.0], color="#0D9488", lw=2.2, ls="--", marker="D", ms=5.5)
    finish(
        ax,
        "Kimi 2.6 · basic x5",
        "no hard contrast yet",
        OUT / "scores_per_trial_kimi26.png",
        [
            Line2D([0], [0], color=BASE, lw=2.2, marker="o", label="CT · baseline"),
            Line2D([0], [0], color=GENE, lw=2.2, marker="s", label="CT · gene"),
            Line2D([0], [0], color="#94A3B8", lw=2.2, ls="--", marker="o", label="decomp · baseline"),
            Line2D([0], [0], color="#0D9488", lw=2.2, ls="--", marker="D", label="decomp · gene"),
        ],
    )


if __name__ == "__main__":
    main()
