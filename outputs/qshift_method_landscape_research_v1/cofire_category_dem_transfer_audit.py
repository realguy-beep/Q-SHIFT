"""Finite-grid transfer stress for exact-circuit category e-factor constants.

No detector histories, sampling, alarms, or decoder calls are made. Results
are diagnostics only and do not extend the exact-circuit continuous guarantee.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import burst_step_information_audit as joint


HERE = Path(__file__).resolve().parent
CERTIFICATE = HERE / "COFIRE_CATEGORY_CONTINUOUS_ENVELOPE_CERTIFICATE.json"
PB_NULL = (0.0001, 0.0005, 0.0010, 0.0015, 0.0020)
PB_ALT = (0.010, 0.014, 0.018)
PM = np.linspace(0.001, 0.005, 101)
STATES = np.arange(1 << len(joint.SELECTED), dtype=np.uint16)
BITS = (STATES[:, None] >> np.arange(len(joint.SELECTED))) & 1
PAIR_COUNT = sum(BITS[:, 2 * k] * BITS[:, 2 * k + 1] for k in range(5))


def category_law(pb: float, pm: float) -> np.ndarray:
    law = joint.dem_distribution(pb, pm)
    return np.bincount(PAIR_COUNT, weights=law, minlength=6)


def main() -> None:
    cert = json.loads(CERTIFICATE.read_text(encoding="utf-8"))
    envelopes = np.array([row["upper_bound"] for row in cert["category_envelopes"]])
    proposals = {
        name: np.array([row[key] for row in cert["category_envelopes"]]) / envelopes
        for name, key in (("reference_pb010_pm003", "reference_q"), ("uniform_grid_alt_mixture", "mixture_q"))
    }
    null_rows = []
    max_violation = np.full(6, -np.inf)
    max_e = {name: -np.inf for name in proposals}
    min_e = {name: np.inf for name in proposals}
    for pb in PB_NULL:
        for pm in PM:
            law = category_law(pb, float(pm))
            if abs(float(law.sum()) - 1) > 2e-12:
                raise RuntimeError("approximate-DEM category law failed normalization")
            delta = law - envelopes
            max_violation = np.maximum(max_violation, delta)
            for name, factor in proposals.items():
                value = float(law @ factor)
                max_e[name] = max(max_e[name], value)
                min_e[name] = min(min_e[name], value)
            null_rows.append({"pb": pb, "pm": float(pm), "dem_category_probabilities": law.tolist()})

    alt_rows = []
    alt_growth = {name: [] for name in proposals}
    for pb in PB_ALT:
        for pm in PM:
            law = category_law(pb, float(pm))
            for name, factor in proposals.items():
                growth = float(law @ np.log(factor))
                alt_growth[name].append(growth)
            alt_rows.append({"pb": pb, "pm": float(pm), "dem_category_probabilities": law.tolist()})

    result = {
        "classification": "APPROXIMATE_DEM_FINITE_GRID_TRANSFER_STRESS_ONLY",
        "source_exact_circuit_certificate": CERTIFICATE.name,
        "grid": {"null_burst_p": list(PB_NULL), "alternative_burst_p": list(PB_ALT), "measurement_p": [float(PM[0]), float(PM[-1]), len(PM)]},
        "per_category_max_DEM_probability_minus_exact_certified_upper": max_violation.tolist(),
        "any_category_envelope_exceeded_on_grid": bool(np.any(max_violation > 0)),
        "proposal_null_expected_e_ranges_on_grid": {name: [min_e[name], max_e[name]] for name in proposals},
        "proposal_alternative_expected_log_growth_ranges_on_grid": {
            name: [min(values), max(values)] for name, values in alt_growth.items()
        },
        "normalization_max_error": max(abs(sum(row["dem_category_probabilities"]) - 1) for row in null_rows + alt_rows),
        "limitations": [
            "Finite parameter grid only; the DEM has no continuous category-envelope certificate.",
            "An exact-circuit e-factor guarantee does not automatically transfer to the approximate DEM or to physical model error.",
            "Expected log growth is not alarm delay, false-alarm probability, decoder utility, or logical error.",
            "No detector histories, e-process recursion, or decoder action was evaluated.",
        ],
    }
    out = HERE / "COFIRE_CATEGORY_DEM_TRANSFER_AUDIT.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("category_envelope_exceeded", result["any_category_envelope_exceeded_on_grid"],
          "max_null_e", result["proposal_null_expected_e_ranges_on_grid"],
          "alt_growth", result["proposal_alternative_expected_log_growth_ranges_on_grid"],
          "norm_err", result["normalization_max_error"])
    print(f"wrote={out}")


if __name__ == "__main__":
    main()
