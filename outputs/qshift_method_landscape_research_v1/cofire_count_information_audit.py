"""Data-processing audit for compressing ten pair bits to cofire count 0..5."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import burst_step_information_audit as joint


TRANSITIONS = ((0.002, 0.010), (0.010, 0.018), (0.002, 0.018))
MEASUREMENT_PS = (0.001, 0.003, 0.005)
STATES = np.arange(1 << len(joint.SELECTED), dtype=np.uint16)
BITS = ((STATES[:, None] >> np.arange(len(joint.SELECTED))) & 1).astype(int)
COFIRE_COUNT = np.sum(np.column_stack([BITS[:, 2*k] * BITS[:, 2*k+1] for k in range(5)]), axis=1)


def kl(p: np.ndarray, q: np.ndarray) -> float:
    mask = p > 0
    if np.any(q[mask] <= 0):
        return float("inf")
    return float(np.sum(p[mask] * np.log(p[mask] / q[mask])))


def compress(prob: np.ndarray) -> np.ndarray:
    return np.bincount(COFIRE_COUNT, weights=prob, minlength=6).astype(float)


def main() -> None:
    rows = []
    for model, get_dist in (
        ("exact_categorical_circuit", joint.exact_circuit_distribution),
        ("approximate_dem", joint.dem_distribution),
    ):
        template = None
        if model == "exact_categorical_circuit":
            import categorical_circuit_parameter_grid_audit as grid
            import categorical_circuit_feature_expectations as features
            template, _ = features.categorical_sites(grid.construct(0.010, 0.003))
        for old_p, new_p in TRANSITIONS:
            for pm in MEASUREMENT_PS:
                if model == "exact_categorical_circuit":
                    p_old = get_dist(template, old_p, pm)
                    p_new = get_dist(template, new_p, pm)
                else:
                    p_old = get_dist(old_p, pm)
                    p_new = get_dist(new_p, pm)
                c_old, c_new = compress(p_old), compress(p_new)
                full = kl(p_new, p_old)
                compressed = kl(c_new, c_old)
                if abs(float(p_old.sum()) - 1) > 2e-12 or abs(float(p_new.sum()) - 1) > 2e-12:
                    raise RuntimeError("full law normalization failure")
                if abs(float(c_old.sum()) - 1) > 2e-12 or abs(float(c_new.sum()) - 1) > 2e-12:
                    raise RuntimeError("cofire-count law normalization failure")
                if compressed > full + 2e-11:
                    raise RuntimeError("data-processing inequality check failed")
                rows.append({
                    "model": model,
                    "old_burst_p": old_p,
                    "new_burst_p": new_p,
                    "measurement_p": pm,
                    "full_ten_detector_KL_new_given_old_nats_per_shot": full,
                    "cofire_count_KL_new_given_old_nats_per_shot": compressed,
                    "retained_information_fraction": compressed / full,
                })
    result = {
        "classification": "DETERMINISTIC_DATA_PROCESSING_COMPARISON_NOT_DETECTOR_PERFORMANCE",
        "compression": "ten selected detector bits (1024 states) -> count C of five within-pair cofires (six states); X=C/5",
        "measurement_noise": "same pm before and after; nuisance drift not included",
        "rows": rows,
        "limitations": [
            "Information KL is for simple IID population laws and does not evaluate a sequential alarm.",
            "The cofire-count KL is the information in the full six-state compressed observation; a specific e-increment may use less.",
            "Exact circuit and approximate DEM laws are kept separate.",
            "No histories, alarms, decoder outputs, or logical outcomes were generated.",
        ],
    }
    output = HERE / "COFIRE_COUNT_INFORMATION_AUDIT.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"rows={len(rows)} min_retained={min(r['retained_information_fraction'] for r in rows):.6f} max_retained={max(r['retained_information_fraction'] for r in rows):.6f}")
    print(f"wrote={output}")


if __name__ == "__main__":
    main()
