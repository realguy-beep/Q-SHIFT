"""Paired decoder comparison summaries for a single smoke-test sample."""
from __future__ import annotations

from math import sqrt
import numpy as np
from scipy.stats import binomtest


def wilson(errors: int, shots: int, z: float = 1.959963984540054) -> list[float]:
    if shots <= 0:
        return [0.0, 0.0]
    p = errors / shots
    den = 1 + z * z / shots
    center = (p + z * z / (2 * shots)) / den
    radius = z * sqrt((p * (1 - p) / shots) + (z * z / (4 * shots * shots))) / den
    return [max(0.0, center - radius), min(1.0, center + radius)]


def compare_predictions(labels: np.ndarray, predictions: dict[str, np.ndarray]) -> dict:
    y = np.asarray(labels, dtype=np.uint8).reshape(-1)
    result, error_masks = {}, {}
    for name, raw in predictions.items():
        p = np.asarray(raw, dtype=np.uint8).reshape(-1)
        if p.shape != y.shape or np.any((p != 0) & (p != 1)):
            raise ValueError(f"prediction shape/value mismatch for {name}")
        wrong = p != y
        error_masks[name] = wrong
        errors = int(wrong.sum())
        result[name] = {"errors": errors, "shots": int(len(y)), "ler": errors / len(y),
                        "successes": int(len(y) - errors), "wilson95": wilson(errors, len(y))}
    baseline_name = "pymatching"
    if baseline_name in error_masks:
        for name in predictions:
            if name == baseline_name:
                continue
            a, b = error_masks[name], error_masks[baseline_name]
            candidate_only = int((a & ~b).sum())
            baseline_only = int((~a & b).sum())
            n = candidate_only + baseline_only
            pvalue = float(binomtest(min(candidate_only, baseline_only), n, 0.5,
                                     alternative="two-sided").pvalue) if n else 1.0
            p_arr = np.asarray(predictions[name], dtype=np.uint8).reshape(-1)
            b_arr = np.asarray(predictions[baseline_name], dtype=np.uint8).reshape(-1)
            result[name]["paired_vs_pymatching"] = {
                "candidate_only_failures": candidate_only,
                "pymatching_only_failures": baseline_only,
                "prediction_disagreements": int((p_arr != b_arr).sum()),
                "delta_ler_candidate_minus_pymatching": result[name]["ler"] - result[baseline_name]["ler"],
                "relative_error_reduction": ((result[baseline_name]["errors"] - result[name]["errors"]) / result[baseline_name]["errors"]
                                             if result[baseline_name]["errors"] else None),
                "exact_mcnemar_two_sided_p_descriptive": pvalue,
                "inference_note": "Shot-paired descriptive statistic from one smoke-test root; not a seed-cluster or confirmatory result.",
            }
    return result
