"""Expected log growth of bounded-mean e-process increments; no sampling."""
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
import categorical_circuit_parameter_grid_audit as grid
import categorical_circuit_feature_expectations as exact_features
import dem_feature_expectations as dem_features


PM_VALUES = (0.001, 0.003, 0.005)
ALT_BURST_VALUES = (0.010, 0.018)
LAMBDA_GRID = np.linspace(0.0, 0.999, 10000)
STATES = np.arange(1 << len(joint.SELECTED), dtype=np.uint16)
BITS = ((STATES[:, None] >> np.arange(len(joint.SELECTED))) & 1).astype(float)
X = np.column_stack([BITS[:, 2 * k] * BITS[:, 2 * k + 1] for k in range(5)]).mean(axis=1)


def maximize_growth(prob: np.ndarray, m: float) -> dict:
    if abs(float(prob.sum()) - 1.0) > 2e-12:
        raise ValueError("joint law normalization failed")
    counts = np.rint(X * 5).astype(int)
    masses = np.bincount(counts, weights=prob, minlength=6)
    levels = np.arange(6, dtype=float) / 5.0
    increments = 1.0 + LAMBDA_GRID[:, None] * (levels[None, :] / m - 1.0)
    if np.any(increments <= 0):
        raise RuntimeError("increment grid must be strictly positive for log evaluation")
    log_growth = np.log(increments) @ masses
    i = int(np.argmax(log_growth))
    return {
        "lambda_grid_argmax": float(LAMBDA_GRID[i]),
        "expected_log_increment_nats_per_shot": float(log_growth[i]),
        "grid_points": len(LAMBDA_GRID),
        "lambda_interval": [float(LAMBDA_GRID[0]), float(LAMBDA_GRID[-1])],
    }


def main() -> None:
    mean_audit = json.loads((HERE / "BOUNDED_PAIR_STATISTIC_MEAN_GRID.json").read_text(encoding="utf-8"))
    rectangle = json.loads((HERE / "EXACT_BURST_MEASUREMENT_RECTANGLE_CERTIFICATE.json").read_text(encoding="utf-8"))
    exact_null_max = rectangle["certified_continuous_bounds"]["null_mean_maximum"]["mean"]
    exact_alt_min = rectangle["certified_continuous_bounds"]["alternative_mean_minimum"]["mean"]
    exact_m = exact_null_max + 1e-10
    dem_m = mean_audit["approximate_dem"]["null_grid_maximum"]["mean"] + 1e-10
    fixed_lambda = 1e-5
    ratio_radius = 1.0 / exact_m - 1.0
    mean_ratio_excess = exact_alt_min / exact_m - 1.0
    uniform_log_growth_lower_bound = fixed_lambda * mean_ratio_excess - fixed_lambda**2 * ratio_radius**2
    if fixed_lambda * ratio_radius > 0.5 or uniform_log_growth_lower_bound <= 0:
        raise RuntimeError("uniform alternative log-growth lower bound did not validate")
    template_circuit = grid.construct(0.010, 0.003)
    template, _ = exact_features.categorical_sites(template_circuit)
    rows = []
    for model, m in (("exact_categorical_circuit", exact_m), ("approximate_dem", dem_m)):
        for burst_p in ALT_BURST_VALUES:
            for measurement_p in PM_VALUES:
                if model == "exact_categorical_circuit":
                    prob = joint.exact_circuit_distribution(template, burst_p, measurement_p)
                else:
                    prob = joint.dem_distribution(burst_p, measurement_p)
                growth = maximize_growth(prob, m)
                mean_x = float(prob @ X)
                if mean_x <= m or growth["expected_log_increment_nats_per_shot"] <= 0:
                    raise RuntimeError("tested alternative did not have positive mean/log growth")
                rows.append({
                    "model": model,
                    "burst_p": burst_p,
                    "measurement_p": measurement_p,
                    "null_mean_bound_plus_1e-10": m,
                    "alternative_mean_x": mean_x,
                    **growth,
                })
    result = {
        "classification": "DETERMINISTIC_EXPECTED_LOG_INCREMENT_GRID_NOT_ALARM_DELAY_OR_FALSE_ALARM_EVALUATION",
        "bounded_statistic": "mean of five pair-cofire bits over the selected ten-bit joint law",
        "null_bound_source": "exact categorical circuit uses the continuous rectangle certificate plus 1e-10; approximate DEM uses finite-grid maximum plus 1e-10 and remains uncertified",
        "lambda_grid": {"count": len(LAMBDA_GRID), "range": [float(LAMBDA_GRID[0]), float(LAMBDA_GRID[-1])]},
        "rows": rows,
        "exact_circuit_uniform_alternative_log_growth_bound": {
            "lambda_fixed": fixed_lambda,
            "null_bound_plus_margin": exact_m,
            "alternative_mean_lower_bound": exact_alt_min,
            "lambda_times_max_abs_normalized_increment": fixed_lambda * ratio_radius,
            "inequality_used": "log(1+y) >= y-y^2 for |y|<=1/2",
            "expected_log_increment_lower_bound_nats_per_shot": uniform_log_growth_lower_bound,
            "scope": "uniform over the certified exact-circuit alternative rectangle p_b in [.010,.018], p_m in [.001,.005], with gate p=.003; this is a population lower bound, not a delay/ARL bound",
        },
        "limitations": [
            "Expected log increment is a population quantity, not a realized sequence or detection delay.",
            "DEM positive log growth is conditional on its unproved continuum null-mean bound; the exact circuit row now uses the separate Bernstein certificate.",
            "The grid search over lambda is numerical and does not certify a global optimizer.",
            "No ARL, finite-horizon false-switch probability, alarm, decoder action, or logical outcome was evaluated.",
        ],
    }
    output = HERE / "BOUNDED_EINCREMENT_GROWTH_AUDIT.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"rows={len(rows)} max_grid_mean={max(r['expected_log_increment_nats_per_shot'] for r in rows):.9g}")
    print(f"wrote={output}")


if __name__ == "__main__":
    main()
