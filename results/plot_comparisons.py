"""Render the README figure from saved responses. Requires Matplotlib."""
from itertools import combinations
from statistics import mean

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import report


def main():
    runs = report.load_runs(report.ct.load_bank())
    rows = []
    for first, second in combinations(report.MODELS, 2):
        diffs = [
            mean(runs[second, seed]["pair_credit"][pair] - runs[first, seed]["pair_credit"][pair]
                 for seed in report.ORDERS)
            for pair in sorted(runs[first, 41]["pairs"])
        ]
        estimate = 100 * mean(diffs)
        bounds = report.ct.paired_interval(diffs)
        label = f"{report.MODELS[second]} − {report.MODELS[first]}"
        rows.append((estimate, label, bounds))
    rows.sort(reverse=True)

    ink, teal, gray = "#172F3A", "#006A70", "#546877"
    fig, ax = plt.subplots(figsize=(9.4, 4.45), facecolor="white")
    fig.subplots_adjust(left=.365, right=.89, top=.775, bottom=.18)
    fig.text(.035, .925, "Which model differences did the benchmark resolve?",
             fontsize=17, fontweight="bold", color=ink)
    fig.text(.035, .848, "Dots show the mean difference. Lines show the 95% paired bootstrap interval.",
             fontsize=11, color=gray)
    for y, (estimate, _, bounds) in enumerate(rows):
        color = teal if bounds and (bounds[0] > 0 or bounds[1] < 0) else gray
        if bounds:
            ax.hlines(y, *bounds, color=color, lw=2.4)
            ax.plot(bounds, [y, y], "|", color=color, markersize=8)
        ax.scatter(estimate, y, s=50, color=color, zorder=3)
        ax.text(1.025, y, f"{estimate:+.1f}", transform=ax.get_yaxis_transform(),
                va="center", fontsize=11, color=ink, fontweight="bold")
    ax.axvline(0, color=ink, linestyle="--", linewidth=1, zorder=0)
    ax.set_axisbelow(True)
    ax.grid(axis="x", color="#DEE5E8", linewidth=.7)
    ax.set_xlim(-10, 30)
    ax.set_xticks(range(-10, 31, 10))
    ax.set_ylim(len(rows) - .5, -.5)
    ax.set_yticks(range(len(rows)), [label for _, label, _ in rows])
    ax.tick_params(axis="both", length=0, labelsize=10.5, colors=ink, pad=7)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xlabel("Difference in evidence score (percentage points)", fontsize=11, color=ink, labelpad=9)
    fig.savefig(report.HERE / "paired-differences.png", dpi=180, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    main()
