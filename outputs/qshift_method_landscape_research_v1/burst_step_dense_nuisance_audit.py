"""Dense deterministic measurement-nuisance sensitivity grid for step KL.

Computes KL(P_new || P_old) for independent old/new measurement rates on a
101-point grid, using exact ten-detector laws. It creates no shot histories.
This remains a finite grid sensitivity audit, not continuous minimization.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import burst_step_information_audit as info
import categorical_circuit_parameter_grid_audit as grid
from categorical_circuit_feature_expectations import direct_xor
from dem_feature_expectations import build_dem, direct_xor_convolution

TRANSITIONS = info.TRANSITIONS
PM_GRID = np.linspace(0.001, 0.005, 101)
CHUNK = 8


def law_cache() -> dict[str, dict[tuple[float, int], np.ndarray]]:
    base = grid.construct(0.010, 0.003)
    template, _ = grid.categorical_sites(base)
    ps = sorted({p for pair in TRANSITIONS for p in pair})
    cache: dict[str, dict[tuple[float, int], np.ndarray]] = {
        "exact_categorical_circuit": {}, "approximate_dem": {}}
    for p in ps:
        for j, pm in enumerate(PM_GRID):
            circuit = grid.construct(p, float(pm))
            exact = direct_xor(grid.reweight(template, circuit), info.SELECTED)
            _, mechanisms = build_dem(p, float(pm))
            dem = direct_xor_convolution(mechanisms, info.SELECTED)
            for model, dist in (("exact_categorical_circuit", exact), ("approximate_dem", dem)):
                if np.any(dist < 0) or abs(float(dist.sum()) - 1.0) > 2e-12:
                    raise RuntimeError(f"invalid law: {model}, p={p}, pm={pm}")
                cache[model][(p, j)] = dist
    return cache


def pairwise_kl_min(old: np.ndarray, new: np.ndarray) -> tuple[float, int, int, float]:
    """Minimum matrix cell KL(new_j || old_i) with bounded temporary memory."""
    eps = np.finfo(np.float64).tiny
    log_new = np.log(np.maximum(new, eps))
    best = (float("inf"), -1, -1, 0.0)
    for start in range(0, len(old), CHUNK):
        stop = min(start + CHUNK, len(old))
        q0 = old[start:stop]
        if np.any((q0 == 0).any(axis=1)):
            raise RuntimeError("support check: old law contains zeros; use explicit KL support logic")
        log_old = np.log(q0)
        matrix = np.sum(new[None, :, :] * (log_new[None, :, :] - log_old[:, None, :]), axis=2)
        i, j = np.unravel_index(int(np.argmin(matrix)), matrix.shape)
        value = float(matrix[i, j])
        if value < best[0]:
            best = (value, start + i, j, float(matrix.min()))
    return best


def main() -> None:
    cache = law_cache()
    rows = []
    norm_error = 0.0
    for model, laws in cache.items():
        for old_p, new_p in TRANSITIONS:
            old = np.stack([laws[(old_p, j)] for j in range(len(PM_GRID))])
            new = np.stack([laws[(new_p, j)] for j in range(len(PM_GRID))])
            norm_error = max(norm_error, float(np.max(np.abs(old.sum(1) - 1))),
                             float(np.max(np.abs(new.sum(1) - 1))))
            minimum, old_j, new_j, matrix_min = pairwise_kl_min(old, new)
            if minimum < -2e-12:
                raise RuntimeError("KL grid contains a negative minimum")
            # Independent direct evaluation at the selected least-favorable grid point.
            p0, p1 = old[old_j], new[new_j]
            direct = float(np.sum(p1 * np.log(p1 / p0)))
            if abs(direct - minimum) > 2e-12:
                raise RuntimeError("selected-cell KL did not reproduce")
            coarse = next(r for r in info_data["measurement_nuisance_grid_minima"]
                if r["model"] == model and r["old_burst_p"] == old_p and r["new_burst_p"] == new_p)
            rows.append({
                "model": model, "old_burst_p": old_p, "new_burst_p": new_p,
                "minimum_KL_new_given_old_nats_per_shot": minimum,
                "old_measurement_p_at_minimum_grid": float(PM_GRID[old_j]),
                "new_measurement_p_at_minimum_grid": float(PM_GRID[new_j]),
                "grid_spacing": float(PM_GRID[1] - PM_GRID[0]),
                "coarse_3point_minimum": coarse["min_KL_new_given_old_over_independent_old_new_measurement_p_grid"],
                "dense_minus_coarse": minimum - coarse["min_KL_new_given_old_over_independent_old_new_measurement_p_grid"],
            })
    result = {
        "classification": "DETERMINISTIC_DENSE_GRID_NUISANCE_SENSITIVITY_NOT_CONTINUOUS_ROBUSTNESS_GUARANTEE",
        "configuration": {"selected_detectors": list(info.SELECTED), "states": 2 ** len(info.SELECTED),
            "burst_transitions": [list(x) for x in TRANSITIONS],
            "independent_old_new_measurement_p_grid": [float(PM_GRID[0]), float(PM_GRID[-1]), len(PM_GRID)],
            "grid_spacing": float(PM_GRID[1] - PM_GRID[0]), "memory_chunk_old_rates": CHUNK},
        "method": "Compute 101 exact categorical-circuit and approximate-DEM joint distributions per distinct burst p; evaluate all 101x101 old/new measurement-rate pairs using chunked vectorized KL, then compare the minimum with the prior 3x3 coarse grid.",
        "rows": rows,
        "validation": {"max_normalization_error": norm_error,
            "selected_minima_recomputed_directly": True, "all_grid_minima_nonnegative": True,
            "stochastic_sampling": False, "continuous_optimization": False},
        "interpretation": [
            "The dense grid tests a wider range of independent old/new measurement nuisance values than the prior three-point check. It is not an infimum over the continuous interval and not a calibrated composite change detector.",
            "KL is directional expected log-likelihood evidence under fully specified IID simple laws. No finite-history stopping rule, alarm probability, or decoder utility is evaluated.",
            "The ten detector subset and exact categorical circuit / approximate DEM remain distinct representations."
        ], "sampling_calls": 0, "decoder_calls": 0}
    (HERE / "BURST_STEP_DENSE_NUISANCE_AUDIT.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"rows": rows, "validation": result["validation"]}, indent=2))


if __name__ == "__main__":
    info_data = json.loads((HERE / "BURST_STEP_INFORMATION_AUDIT.json").read_text(encoding="utf-8"))
    main()
