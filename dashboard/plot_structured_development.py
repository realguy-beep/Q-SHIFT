"""Render small, reproducible development-only learning diagnostics."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def plot(run_dir: Path, output: Path) -> None:
    run_dir = run_dir.resolve()
    audit = json.loads((run_dir / "independent_evidence_audit.json").read_text(encoding="utf-8"))
    result = json.loads((run_dir / "structured_development_results.json").read_text(encoding="utf-8"))
    baseline = audit["baseline_errors"]
    n = sum(v["shots"] for v in baseline["identity"].values())
    names = ["Identity", "PyMatching", "Direct MLP", "Residual MLP", "3D CNN\nunweighted", "3D CNN\nweighted"]
    lers = [sum(r["errors"] for r in baseline["identity"].values()) / n,
            sum(r["errors"] for r in baseline["pymatching"].values()) / n]
    for candidate in ("direct_mlp", "residual_mlp", "structured_ch8_unweighted", "structured_ch8_weighted"):
        threshold = str(result["selected_thresholds"][candidate])
        errors = sum(audit["per_candidate_per_regime"][candidate][r]["thresholds"][threshold]["logical_errors"]
                     for r in ("x_biased", "balanced", "z_biased"))
        lers.append(errors / n)

    # Confusion and calibration are against the logical-observable flip label.
    candidates = ["direct_mlp", "structured_ch8_unweighted", "structured_ch8_weighted"]
    cm = []
    bins = {name: [[] for _ in range(10)] for name in candidates}
    for path in sorted((run_dir / "validation_evidence").glob("*.npz")):
        with np.load(path, allow_pickle=False) as data:
            y = np.asarray(data["observable"], dtype=np.uint8)
            for name in candidates:
                p = np.asarray(data[f"probability__{name}"], dtype=np.float64)
                pred = (p >= 0.5).astype(np.uint8)
                if name == "direct_mlp" or name.startswith("structured_"):
                    cm.append((name, int(np.count_nonzero((y == 0) & (pred == 0))),
                               int(np.count_nonzero((y == 0) & (pred == 1))),
                               int(np.count_nonzero((y == 1) & (pred == 0))),
                               int(np.count_nonzero((y == 1) & (pred == 1)))))
                idx = np.minimum((p * 10).astype(int), 9)
                for b in range(10):
                    mask = idx == b
                    if mask.any():
                        bins[name][b].append((int(mask.sum()), float(p[mask].sum()), float(y[mask].sum())))
    # cm contains one record per evidence batch; aggregate once per candidate.
    cm_agg = {}
    for name, tn, fp, fn, tp in cm:
        values = cm_agg.setdefault(name, [0, 0, 0, 0])
        values[0] += tn; values[1] += fp; values[2] += fn; values[3] += tp

    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    ax = axes[0, 0]
    colors = ["#8993a4", "#26a69a", "#9a7ad6", "#5277bf", "#7464ac", "#cd8d4a"]
    bars = ax.bar(range(len(names)), np.array(lers) * 100, color=colors)
    ax.set_xticks(range(len(names)), names, rotation=18, ha="right")
    ax.set_ylabel("Validation logical error rate (%)")
    ax.set_title("Paired 3,000-shot development validation")
    ax.grid(axis="y", alpha=0.25)
    for bar, value in zip(bars, lers):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05, f"{value*100:.2f}%",
                ha="center", va="bottom", fontsize=8)

    ax = axes[0, 1]
    confusion_names = ["direct_mlp", "structured_ch8_unweighted", "structured_ch8_weighted"]
    recall, predicted_rate = [], []
    for name in confusion_names:
        tn, fp, fn, tp = cm_agg[name]
        recall.append(tp / max(1, tp + fn))
        predicted_rate.append((tp + fp) / max(1, tn + fp + fn + tp))
    x = np.arange(len(confusion_names))
    width = 0.35
    ax.bar(x - width/2, np.array(recall) * 100, width, label="Positive recall", color="#e36b6b")
    ax.bar(x + width/2, np.array(predicted_rate) * 100, width, label="Predicted-positive rate", color="#647dd1")
    ax.set_xticks(x, ["Direct MLP", "CNN\nunweighted", "CNN\nweighted"])
    ax.set_ylabel("Percent")
    ax.set_title("Logical-flip detection at threshold 0.5")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.25)

    ax = axes[1, 0]
    y_values = []
    for name, color in (("direct_mlp", "#9a7ad6"),
                        ("structured_ch8_unweighted", "#7464ac"),
                        ("structured_ch8_weighted", "#cd8d4a")):
        observed, predicted = [], []
        for counts in bins[name]:
            nbin = sum(row[0] for row in counts)
            if nbin:
                observed.append(sum(row[2] for row in counts) / nbin)
                predicted.append(sum(row[1] for row in counts) / nbin)
        ax.plot(predicted, observed, marker="o", label=name.replace("structured_ch8_", "CNN ").replace("direct_mlp", "Direct MLP"), color=color)
    ax.plot([0, 1], [0, 1], linestyle="--", color="#555", linewidth=1, label="Perfect calibration")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Observed positive fraction")
    ax.set_title("Calibration on the same validation set")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.25)

    ax = axes[1, 1]
    thresholds = [0.25, 0.5, 0.75]
    for candidate, label, color in (("structured_ch8_unweighted", "CNN unweighted", "#7464ac"),
                                    ("structured_ch8_weighted", "CNN weighted", "#cd8d4a")):
        values = [result["candidates"][candidate]["equal_regime_ler_by_threshold"][str(t)] * 100
                  for t in thresholds]
        ax.plot(thresholds, values, marker="o", label=label, color=color)
    ax.axhline(sum(r["errors"] for r in baseline["pymatching"].values()) / n * 100,
               color="#26a69a", linestyle="--", label="PyMatching")
    ax.set_xlabel("Probability threshold")
    ax.set_ylabel("Equal-regime validation LER (%)")
    ax.set_title("Threshold sensitivity; validation-selected")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)

    fig.suptitle("Q-SHIFT structured decoder · development only · no test samples", fontsize=14)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=160)
    plt.close(fig)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plot(args.run_dir, args.output)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
