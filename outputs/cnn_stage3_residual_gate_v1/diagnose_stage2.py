"""Read-only retrospective diagnostics on Stage 2 FINAL-DEVELOPMENT arrays only.

This file is intentionally excluded from the Stage 3 training and policy code.
It must not be used to fit weights, select an architecture, or set Stage 3
thresholds. It never enumerates or opens independent-test material.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PREDICTIONS = ROOT / "outputs/cnn_architecture_stage2_v1/run_v1/predictions"
MODELS = ("historical_residual_position_cnn", "residual_position_v2",
          "factorized_spatiotemporal_residual")
CONDITIONS = ("nominal", "synthetic_spatial_burst")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def auc(scores: np.ndarray, labels: np.ndarray) -> float | None:
    labels = labels.astype(bool)
    n_pos, n_neg = int(labels.sum()), int((~labels).sum())
    if not n_pos or not n_neg:
        return None
    order = np.argsort(scores, kind="mergesort")
    ranks = np.empty(len(scores), dtype=np.float64)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and scores[order[j]] == scores[order[i]]:
            j += 1
        ranks[order[i:j]] = (i + 1 + j) / 2.0
        i = j
    return float((ranks[labels].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def main() -> None:
    if not PREDICTIONS.is_dir():
        raise FileNotFoundError(PREDICTIONS)
    result = {"source": "Stage 2 final-development predictions only",
              "independent_test_accessed": False, "roots": {}, "aggregate": {}}
    rows = []
    for root_i in range(5):
        root = f"dev-root-{root_i:02d}"
        path = PREDICTIONS / f"{root}.npz"
        with np.load(path, allow_pickle=False) as z:
            root_row = {"prediction_archive_sha256": sha256(path), "conditions": {}}
            for condition in CONDITIONS:
                y = z[f"{condition}__observable"].astype(np.uint8)
                pm = z[f"{condition}__nominal_prediction"].astype(np.uint8)
                detectors = z[f"{condition}__detectors"]
                residual = y ^ pm
                cell = {"shots": len(y), "pymatching_errors": int(residual.sum()),
                        "residual_positive_prevalence": float(residual.mean()),
                        "unique_pymatching_failure_syndromes": int(len({bytes(row) for row in detectors[residual == 1]})),
                        "models": {}}
                for model in MODELS:
                    prefix = f"{condition}__{model}__"
                    pred = z[prefix + "prediction"].astype(np.uint8)
                    p = z[prefix + "probability"].astype(np.float64)
                    changed = pred != pm
                    useful = changed & (residual == 1)
                    harmful = changed & (residual == 0)
                    model_row = {
                        "errors": int(np.count_nonzero(pred ^ y)),
                        "changed_decisions": int(changed.sum()),
                        "useful_corrections": int(useful.sum()),
                        "harmful_corrections": int(harmful.sum()),
                        "correction_precision": float(useful.sum() / changed.sum()) if changed.any() else None,
                        "correction_recall": float(useful.sum() / residual.sum()) if residual.any() else None,
                        "residual_score_auc": auc(p, residual),
                        "residual_prevalence": float(residual.mean()),
                        "mean_probability": float(p.mean()),
                        "brier": float(np.mean((p - residual) ** 2)),
                        "nll": float(-np.mean(residual * np.log(np.clip(p, 1e-12, 1)) +
                                                (1 - residual) * np.log(np.clip(1 - p, 1e-12, 1)))),
                    }
                    cell["models"][model] = model_row
                    rows.append((condition, model, residual, p))
                root_row["conditions"][condition] = cell
            result["roots"][root] = root_row
    for condition in CONDITIONS:
        result["aggregate"][condition] = {}
        for model in MODELS:
            selected = [(r, p) for c, m, r, p in rows if c == condition and m == model]
            residual = np.concatenate([x[0] for x in selected])
            probability = np.concatenate([x[1] for x in selected])
            ece = 0.0
            for lo in np.linspace(0, 0.9, 10):
                hi = lo + 0.1
                mask = (probability >= lo) & ((probability < hi) if hi < 1 else (probability <= hi))
                if mask.any():
                    ece += float(mask.mean() * abs(probability[mask].mean() - residual[mask].mean()))
            result["aggregate"][condition][model] = {
                "shots": len(residual), "residual_positives": int(residual.sum()),
                "score_auc": auc(probability, residual), "mean_probability": float(probability.mean()),
                "brier": float(np.mean((probability - residual) ** 2)), "ece_10_equal_width": ece,
            }
    out = Path(__file__).with_name("STAGE2_RETROSPECTIVE_DIAGNOSTICS.json")
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS_READ_ONLY", "output": str(out),
                      "roots": len(result["roots"]), "independent_test_accessed": False}))


if __name__ == "__main__":
    main()
