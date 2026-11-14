"""Deterministic grid audit for a bounded five-pair-cofire statistic.

No detector histories are generated. The statistic is X=(sum of five pair
cofires)/5 in [0,1]. Exact categorical-circuit and approximate-DEM means are
evaluated separately. Grid separation is exploratory and is not a continuum
certificate for an e-detector null-mean bound.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for path in (ROOT, ROOT / "outputs" / "phase3a_correlated_noise_preflight"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import categorical_circuit_parameter_grid_audit as exact_grid
import categorical_circuit_feature_expectations as exact_features
import dem_feature_expectations as dem_features


MEASUREMENT_GRID = np.linspace(0.001, 0.005, 101)
NULL_BURST_VALUES = (0.002,)
ALTERNATIVE_BURST_INTERVAL = (0.010, 0.018)


def exact_statistic_mean(template, burst_p: float, measurement_p: float) -> float:
    circuit = exact_grid.construct(float(burst_p), float(measurement_p))
    means = exact_features.means_from_characters(
        exact_grid.reweight(template, circuit)
    )
    return float(np.mean(means[40:45]))


def dem_statistic_mean(burst_p: float, measurement_p: float) -> float:
    _, mechanisms = dem_features.build_dem(float(burst_p), float(measurement_p))
    means = dem_features.feature_means(mechanisms)
    return float(np.mean(means[40:45]))


def audit(model: str, evaluator, template=None) -> dict:
    # The original configured null is fixed at burst p=.002. Across each
    # alternative interval, the independent Bernoulli burst probability makes
    # each parity-character moment and cofire mean affine in p, so endpoints
    # cover that interval for fixed measurement p. Measurement p remains a
    # finite exploratory grid.
    null = [
        (float(b), float(m), evaluator(template, float(b), float(m))
         if template is not None else evaluator(float(b), float(m)))
        for b in NULL_BURST_VALUES for m in MEASUREMENT_GRID
    ]
    alternative = [
        (float(b), float(m), evaluator(template, float(b), float(m))
         if template is not None else evaluator(float(b), float(m)))
        for b in ALTERNATIVE_BURST_INTERVAL for m in MEASUREMENT_GRID
    ]
    null_max = max(null, key=lambda row: row[2])
    alt_min = min(alternative, key=lambda row: row[2])
    midpoint_p = sum(ALTERNATIVE_BURST_INTERVAL) / 2
    probe_pm = 0.003
    midpoint_value = (
        evaluator(template, midpoint_p, probe_pm)
        if template is not None else evaluator(midpoint_p, probe_pm)
    )
    endpoint_values = [
        evaluator(template, float(b), probe_pm)
        if template is not None else evaluator(float(b), probe_pm)
        for b in ALTERNATIVE_BURST_INTERVAL
    ]
    affine_residual = midpoint_value - sum(endpoint_values) / 2
    if abs(affine_residual) > 1e-12:
        raise RuntimeError(f"burst-p affine midpoint validation failed for {model}: {affine_residual}")
    return {
        "model": model,
        "bounded_statistic": "mean of five within-pair detector cofire indicators; X in [0,1]",
        "null_grid": {
            "burst_p_values": list(NULL_BURST_VALUES),
            "measurement_p": [float(MEASUREMENT_GRID[0]), float(MEASUREMENT_GRID[-1]), len(MEASUREMENT_GRID)],
        },
        "alternative_grid": {
            "burst_p_interval_endpoint_evaluations": list(ALTERNATIVE_BURST_INTERVAL),
            "measurement_p": [float(MEASUREMENT_GRID[0]), float(MEASUREMENT_GRID[-1]), len(MEASUREMENT_GRID)],
        },
        "null_grid_maximum": {"burst_p": null_max[0], "measurement_p": null_max[1], "mean": null_max[2]},
        "alternative_grid_minimum": {"burst_p": alt_min[0], "measurement_p": alt_min[1], "mean": alt_min[2]},
        "grid_gap_alt_min_minus_null_max": alt_min[2] - null_max[2],
        "burst_p_affinity_midpoint_check": {
            "measurement_p": probe_pm,
            "burst_p_endpoints": list(ALTERNATIVE_BURST_INTERVAL),
            "endpoint_means": endpoint_values,
            "midpoint_burst_p": midpoint_p,
            "midpoint_mean": midpoint_value,
            "midpoint_minus_endpoint_average": affine_residual,
            "tolerance": 1e-12,
        },
        "interpretation": (
            "Burst-p endpoint evaluation is exact for each fixed measurement p because the independent burst Bernoulli parameter enters affine in the parity-character moment formulas. The measurement-p optimization is only a finite grid. Positive grid gap suggests this bounded statistic could support a one-sided mean e-process for these tested conditions. "
            "A valid null bound requires a proved continuum supremum and a defensible conditional-mean null; this finite grid does not supply either. "
            "Detection of pair-cofire change would not identify its physical cause or establish decoder benefit."
        ),
    }


def main() -> None:
    template_circuit = exact_grid.construct(0.010, 0.003)
    template, meta = exact_features.categorical_sites(template_circuit)
    result = {
        "classification": "DETERMINISTIC_POPULATION_MEAN_GRID_NOT_A_VALIDATED_SEQUENTIAL_TEST",
        "source_model": "Q-SHIFT distance-3, five-round Z-memory, balanced-regime circuit implementation; gate p=0.003; burst pair supports audited by exact single-fault mapping",
        "exact_categorical_circuit": audit("exact_categorical_circuit", exact_statistic_mean, template),
        "approximate_dem": audit("approximate_dem", dem_statistic_mean),
        "circuit_template_metadata": meta,
        "limitations": [
            "The deterministic circuit builder omits zero-probability burst sites; the attempted broader null interval [0,0.002] failed template reweighting with a noise-site-count mismatch, so this audit uses the documented p=0.002 null only.",
            "No continuous maximization or interval certificate was performed.",
            "No sequential boundary, false-alarm rate, detection delay, parameter estimate, or graph-switch decision was evaluated.",
            "The bounded-statistic e-detector analogy requires its null conditional expectation bound to hold at every shot.",
            "The DEM result describes its approximate independent-event model, not the original circuit law.",
        ],
    }
    output = HERE / "BOUNDED_PAIR_STATISTIC_MEAN_GRID.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for key in ("exact_categorical_circuit", "approximate_dem"):
        row = result[key]
        print(key, row["null_grid_maximum"], row["alternative_grid_minimum"], row["grid_gap_alt_min_minus_null_max"])
    print(f"wrote={output}")


if __name__ == "__main__":
    main()
