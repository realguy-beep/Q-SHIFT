"""Export compact CSV tables and diagnostic plot from saved root-cause JSON."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
result = json.loads((HERE / "diagnostic_results.json").read_text(encoding="utf-8"))

old_rows = []
old = result["old_saved_validation_recomputation"]
for reg, errors in old["identity"].items():
    old_rows.append({"model": "identity", "regime": reg, "n": old["validation_shots_by_regime"][reg],
                     "errors": errors, "ler": errors / old["validation_shots_by_regime"][reg]})
for reg, errors in old["pymatching"].items():
    old_rows.append({"model": "pymatching", "regime": reg, "n": old["validation_shots_by_regime"][reg],
                     "errors": errors, "ler": errors / old["validation_shots_by_regime"][reg]})
for model, regimes in old["candidates"].items():
    for reg, item in regimes.items():
        old_rows.append({"model": model, "regime": reg, "n": item["n"], "errors": item["logical_errors"],
                         "ler": item["ler"], "target_positive_count": item["target_positive_count"],
                         "candidate_only_vs_pm": item["candidate_only_vs_pm"],
                         "pymatching_only": item["pm_only_vs_candidate"],
                         "prediction_disagreements": item["prediction_disagreements_vs_pm"],
                         "bce_negative": item["class_conditional_bce"][0],
                         "bce_positive": item["class_conditional_bce"][1],
                         "confusion": json.dumps(item["confusion_at_0_5"], sort_keys=True),
                         "score_histogram_10_bins": json.dumps(item["predicted_positive_histogram_at_0_5"])} )

def write_csv(name, rows):
    path = HERE / name
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader(); writer.writerows(rows)

write_csv("OLD_VALIDATION_RECOMPUTED.csv", old_rows)

aggregate_rows, regime_rows = [], []
for item in result["scale_comparison_results"]:
    row = {k: item[k] for k in ("model", "strategy", "training_size_per_regime", "epochs_requested",
                                 "selected_threshold_validation", "equal_regime_ler",
                                 "equal_regime_pymatching_ler", "paired_delta_ler_candidate_minus_pymatching",
                                 "candidate_only", "pymatching_only", "paired_disagreements",
                                 "mcnemar_exact_two_sided_p_descriptive")}
    row["conditional_shot_bootstrap_95ci_low"] = item["conditional_stratified_shot_bootstrap_95ci"][0]
    row["conditional_shot_bootstrap_95ci_high"] = item["conditional_stratified_shot_bootstrap_95ci"][1]
    aggregate_rows.append(row)
    for reg, m in item["per_regime"].items():
        regime_rows.append({"model": item["model"], "strategy": item["strategy"],
                            "training_size_per_regime": item["training_size_per_regime"],
                            "regime": reg, **m})
write_csv("FRESH_POLICY_COMPARISON.csv", aggregate_rows)
write_csv("FRESH_POLICY_PER_REGIME.csv", regime_rows)

fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.6))
# Prior saved validation score histograms, pooled over regimes.
hist_models = ("direct_mlp", "structured_ch8_unweighted", "structured_ch8_weighted")
labels = ("Direct MLP", "CNN unweighted", "CNN weighted (raw score)")
bins = np.arange(11)
for model, label in zip(hist_models, labels):
    hist = np.sum([old["candidates"][model][r]["predicted_positive_histogram_at_0_5"] for r in old["candidates"][model]], axis=0)
    axes[0].step(bins[:-1], hist, where="post", label=label)
axes[0].set_xticks(np.arange(0, 11, 2), [f"{x/10:.1f}" for x in range(0, 11, 2)])
axes[0].set_xlabel("Saved validation score bin"); axes[0].set_ylabel("Shots / 3,000")
axes[0].set_title("Previous run: score concentration"); axes[0].legend(fontsize=8)

# Tiny-set positive recall confirms optimization sensitivity.
tiny = result["tiny_set_gate"]["results"]
selected_tiny = [x for x in tiny if x["case"].startswith("balanced")]
for kind, marker in (("mlp", "o"), ("cnn", "s")):
    data = [x for x in selected_tiny if x["model"] == kind]
    axes[1].plot([x["learning_rate"] for x in data], [x["positive_recall"] for x in data],
                 marker=marker, label=kind.upper())
axes[1].set_xscale("log"); axes[1].set_ylim(0, 1.05)
axes[1].set_xlabel("Learning rate"); axes[1].set_ylabel("Positive recall (tiny-set train)")
axes[1].set_title("256-example memorization probe"); axes[1].legend()

# Fresh validation paired LER by model, strategy and sample size.
styles = {"natural": "--", "weighted": ":", "balanced": "-"}
colors = {"mlp": "tab:blue", "cnn": "tab:orange"}
for model in ("mlp", "cnn"):
    for strategy in ("natural", "weighted", "balanced"):
        rows = [x for x in result["scale_comparison_results"] if x["model"] == model and x["strategy"] == strategy]
        rows.sort(key=lambda x: x["training_size_per_regime"])
        axes[2].plot([x["training_size_per_regime"] for x in rows], [x["equal_regime_ler"] for x in rows],
                     linestyle=styles[strategy], marker="o", color=colors[model],
                     label=f"{model} {strategy}")
axes[2].axhline(result["scale_comparison_results"][0]["equal_regime_pymatching_ler"],
                color="black", linewidth=1, label="PyMatching")
axes[2].set_xlabel("Training shots per regime"); axes[2].set_ylabel("Equal-regime validation LER")
axes[2].set_title("Fresh paired validation"); axes[2].legend(fontsize=7, ncol=2)
fig.suptitle("Q-SHIFT neural collapse diagnostics (development only)", fontsize=13)
fig.tight_layout()
fig.savefig(HERE / "diagnostics.png", dpi=170, bbox_inches="tight")
plt.close(fig)
print(json.dumps({"outputs": ["OLD_VALIDATION_RECOMPUTED.csv", "FRESH_POLICY_COMPARISON.csv",
                              "FRESH_POLICY_PER_REGIME.csv", "diagnostics.png"]}, indent=2))
