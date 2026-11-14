"""Finite-grid exploration of composite-null category-wise e-increments.

This is not a validity certificate: the null envelope is maximized on a finite
parameter grid only. No detector histories or alarms are generated.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import burst_step_information_audit as joint
import categorical_circuit_parameter_grid_audit as grid
import categorical_circuit_feature_expectations as features


HERE = Path(__file__).resolve().parent
PB_NULL = np.linspace(0.0001, 0.002, 10)
PB_ALT = (0.010, 0.014, 0.018)
PM = np.linspace(0.001, 0.005, 11)
PM_REF = 0.003
STATES = np.arange(1 << len(joint.SELECTED), dtype=np.uint16)
BITS = ((STATES[:, None] >> np.arange(len(joint.SELECTED))) & 1).astype(int)
PAIR_PRODUCTS = np.column_stack([BITS[:, 2 * k] * BITS[:, 2 * k + 1] for k in range(5)])
COUNT = PAIR_PRODUCTS.sum(axis=1)


def compress(prob: np.ndarray) -> np.ndarray:
    return np.bincount(COUNT, weights=prob, minlength=6)


def category_law(model: str, template: list, pb: float, pm: float) -> np.ndarray:
    if model == "exact_categorical_circuit":
        law = joint.exact_circuit_distribution(template, pb, pm)
    else:
        law = joint.dem_distribution(pb, pm)
    return compress(law)


def expected_log(p: np.ndarray, e_factor: np.ndarray) -> float:
    return float(np.sum(p * np.log(e_factor)))


def run_model(model: str, template: list) -> dict:
    null = np.stack([category_law(model, template, pb, float(pm)) for pb in PB_NULL for pm in PM])
    upper = null.max(axis=0)
    if np.any(upper <= 0):
        raise RuntimeError("nonpositive finite-grid category envelope")
    q_reference = category_law(model, template, 0.010, PM_REF)
    alt_laws = np.stack([category_law(model, template, pb, float(pm)) for pb in PB_ALT for pm in PM])
    q_mixture = alt_laws.mean(axis=0)
    outputs = {}
    for label, q in (("reference_pb010_pm003", q_reference), ("uniform_grid_alt_mixture", q_mixture)):
        e_factor = q / upper
        null_expectations = null @ e_factor
        growth = np.array([expected_log(law, e_factor) for law in alt_laws])
        outputs[label] = {
            "finite_grid_null_envelope": upper.tolist(),
            "proposal_q": q.tolist(),
            "e_factor": e_factor.tolist(),
            "max_null_expected_e_factor_on_grid": float(null_expectations.max()),
            "min_null_expected_e_factor_on_grid": float(null_expectations.min()),
            "min_alt_expected_log_growth_nats_per_shot": float(growth.min()),
            "max_alt_expected_log_growth_nats_per_shot": float(growth.max()),
            "grid_null_expectations_le_one": bool(np.all(null_expectations <= 1 + 2e-14)),
            "grid_alt_growth_rows": [
                {"pb": pb, "pm": float(pm), "expected_log_growth": float(g)}
                for g, (pb, pm) in zip(growth, ((pb, float(pm)) for pb in PB_ALT for pm in PM))
            ],
        }
    return {
        "model": model,
        "null_grid_shape": [len(PB_NULL), len(PM)],
        "alt_grid_shape": [len(PB_ALT), len(PM)],
        "null_pb_grid": PB_NULL.tolist(),
        "measurement_grid": PM.tolist(),
        "alternative_burst_grid": list(PB_ALT),
        "category_sum_error_max": float(max(np.max(np.abs(null.sum(axis=1) - 1)), np.max(np.abs(alt_laws.sum(axis=1) - 1)))),
        "proposals": outputs,
    }


def main() -> None:
    base = grid.construct(0.010, PM_REF)
    template, _ = features.categorical_sites(base)
    result = {
        "classification": "EXPLORATORY_FINITE_GRID_ONLY_NOT_CONTINUOUS_E_VALIDITY",
        "statistic": "C=sum of five documented within-pair detector cofires; C in 0..5",
        "increment_construction": "L(c)=q(c)/U_c with U_c=max null category probability over the finite grid",
        "models": [run_model(model, template) for model in ("exact_categorical_circuit", "approximate_dem")],
        "limitations": [
            "A finite-grid category envelope does not upper-bound probabilities between grid points and does not establish an e-process.",
            "The exact categorical circuit and approximate DEM are separate laws.",
            "Positive expected log increments are population calculations, not delay, ARL, false-alarm, decoder-switch, or logical-error results.",
            "No detector histories, alarms, or decoder actions were generated or evaluated.",
        ],
    }
    out = HERE / "COFIRE_CATEGORY_EINCREMENT_EXPLORATION.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"models={len(result['models'])}")
    for model in result["models"]:
        for label, proposal in model["proposals"].items():
            print(model["model"], label,
                  "max_null_E_on_grid", proposal["max_null_expected_e_factor_on_grid"],
                  "min_alt_log_growth", proposal["min_alt_expected_log_growth_nats_per_shot"],
                  "max_alt_log_growth", proposal["max_alt_expected_log_growth_nats_per_shot"])
    print(f"wrote={out}")


if __name__ == "__main__":
    main()
