"""Dense old/new measurement-nuisance audit for ten-bit and cofire-count laws."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import burst_step_information_audit as joint
import categorical_circuit_parameter_grid_audit as grid
import categorical_circuit_feature_expectations as features


PM_GRID = np.linspace(0.001, 0.005, 101)
TRANSITIONS = ((0.002, 0.010), (0.010, 0.018), (0.002, 0.018))
STATES = np.arange(1 << len(joint.SELECTED), dtype=np.uint16)
BITS = ((STATES[:, None] >> np.arange(len(joint.SELECTED))) & 1).astype(int)
COFIRE_COUNT = np.sum(np.column_stack([BITS[:, 2*k] * BITS[:, 2*k+1] for k in range(5)]), axis=1)


def kl_grid(new: np.ndarray, old: np.ndarray, old_chunk: int = 8) -> np.ndarray:
    # Arrays are [measurement setting, outcome]. All selected joint states are
    # positive under the configured circuit and DEM, allowing direct logs.
    if np.any(new <= 0) or np.any(old <= 0):
        raise RuntimeError("expected strictly positive law for nuisance KL grid")
    out = np.empty((len(new), len(old)))
    for start in range(0, len(old), old_chunk):
        o = old[start:start + old_chunk]
        out[:, start:start + len(o)] = np.sum(
            new[:, None, :] * np.log(new[:, None, :] / o[None, :, :]), axis=2
        )
    return out


def compress(prob: np.ndarray) -> np.ndarray:
    return np.stack([np.bincount(COFIRE_COUNT, weights=row, minlength=6) for row in prob])


def main() -> None:
    exact_template, _ = features.categorical_sites(grid.construct(0.010, 0.003))
    burst_values = sorted({p for edge in TRANSITIONS for p in edge})
    laws = {}
    for model in ("exact_categorical_circuit", "approximate_dem"):
        for burst_p in burst_values:
            if model == "exact_categorical_circuit":
                laws[(model, burst_p)] = np.stack([
                    joint.exact_circuit_distribution(exact_template, burst_p, float(pm)) for pm in PM_GRID
                ])
            else:
                laws[(model, burst_p)] = np.stack([
                    joint.dem_distribution(burst_p, float(pm)) for pm in PM_GRID
                ])
    rows = []
    max_norm_error = 0.0
    max_dpi_violation = 0.0
    for model in ("exact_categorical_circuit", "approximate_dem"):
        count_laws = {p: compress(laws[(model, p)]) for p in burst_values}
        for old_p, new_p in TRANSITIONS:
            full_matrix = kl_grid(laws[(model, new_p)], laws[(model, old_p)])
            count_matrix = kl_grid(count_laws[new_p], count_laws[old_p])
            max_norm_error = max(max_norm_error, float(np.max(np.abs(laws[(model, old_p)].sum(axis=1)-1))))
            max_norm_error = max(max_norm_error, float(np.max(np.abs(laws[(model, new_p)].sum(axis=1)-1))))
            violation = float(np.max(count_matrix - full_matrix))
            max_dpi_violation = max(max_dpi_violation, violation)
            if violation > 2e-11:
                raise RuntimeError(f"data-processing inequality failed: {violation}")
            i_full = np.unravel_index(int(np.argmin(full_matrix)), full_matrix.shape)
            i_count = np.unravel_index(int(np.argmin(count_matrix)), count_matrix.shape)
            ratio_matrix = count_matrix / full_matrix
            i_ratio = np.unravel_index(int(np.argmin(ratio_matrix)), ratio_matrix.shape)
            rows.append({
                "model": model,
                "old_burst_p": old_p,
                "new_burst_p": new_p,
                "pm_grid": [float(PM_GRID[0]), float(PM_GRID[-1]), len(PM_GRID)],
                "full_ten_bit_min_KL_new_given_old": float(full_matrix[i_full]),
                "full_min_old_pm": float(PM_GRID[i_full[1]]),
                "full_min_new_pm": float(PM_GRID[i_full[0]]),
                "cofire_count_min_KL_new_given_old": float(count_matrix[i_count]),
                "count_min_old_pm": float(PM_GRID[i_count[1]]),
                "count_min_new_pm": float(PM_GRID[i_count[0]]),
                "ratio_of_separate_grid_infima_count_over_full": float(count_matrix[i_count] / full_matrix[i_full]),
                "count_KL_at_full_min_pair": float(count_matrix[i_full]),
                "count_fraction_of_full_KL_at_full_min_pair": float(ratio_matrix[i_full]),
                "minimum_count_to_full_KL_ratio_same_pm_pair": float(ratio_matrix[i_ratio]),
                "minimum_ratio_old_pm": float(PM_GRID[i_ratio[1]]),
                "minimum_ratio_new_pm": float(PM_GRID[i_ratio[0]]),
            })
    result = {
        "classification": "DETERMINISTIC_DENSE_NUISANCE_GRID_NOT_CONTINUUM_ROBUSTNESS_CERTIFICATE",
        "old_new_measurement_p_grid": [float(PM_GRID[0]), float(PM_GRID[-1]), len(PM_GRID)],
        "compression": "ten selected detector bits to six-level count of five within-pair cofires",
        "rows": rows,
        "validation": {"max_joint_law_normalization_error": max_norm_error, "max_data_processing_violation": max_dpi_violation},
        "limitations": [
            "Grid minima are not continuous nuisance infima or composite sequential guarantees.",
            "The count KL is information in the full compressed count law, not in a specific e-process increment.",
            "Exact categorical circuit and approximate DEM remain separate.",
            "No sample histories, alarms, decoder actions, or logical outcomes were evaluated.",
        ],
    }
    out = HERE / "COFIRE_COUNT_DENSE_NUISANCE_AUDIT.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"rows={len(rows)} max_norm={max_norm_error:.3g} max_dpi_violation={max_dpi_violation:.3g}")
    for r in rows:
        print(r["model"], r["old_burst_p"], r["new_burst_p"], r["full_ten_bit_min_KL_new_given_old"], r["cofire_count_min_KL_new_given_old"], r["ratio_of_separate_grid_infima_count_over_full"], r["minimum_count_to_full_KL_ratio_same_pm_pair"])
    print(f"wrote={out}")


if __name__ == "__main__":
    main()
