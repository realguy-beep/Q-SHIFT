"""Model-grid minimax proposal selection for the six-category e-factor.

Deterministic population-law optimization only. The proposal remains null-valid
for any fixed normalized q because the denominator is the certified category
upper envelope; this optimization does not establish decoder utility.
"""
from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

import categorical_circuit_parameter_grid_audit as grid
import cofire_category_continuous_envelope as envelope


HERE = Path(__file__).resolve().parent
CERT = HERE / "COFIRE_CATEGORY_CONTINUOUS_ENVELOPE_CERTIFICATE.json"
PB_ALT = (0.010, 0.014, 0.018)
PM_TUNE = np.linspace(0.001, 0.005, 101)
PM_DENSE = np.linspace(0.001, 0.005, 1001)


def make_laws(polys, pm_grid):
    return np.vstack([
        np.stack([envelope.evaluate_grid(poly, np.array([pb]), pm_grid)[0] for poly in polys], axis=-1)
        for pb in PB_ALT
    ])


def main() -> None:
    cert = json.loads(CERT.read_text(encoding="utf-8"))
    upper = np.array([row["upper_bound"] for row in cert["category_envelopes"]])
    template, _ = envelope.category_polynomials(grid.construct(0.010, 0.003))
    P_tune = make_laws(template, PM_TUNE)

    mixture = np.array([row["mixture_q"] for row in cert["category_envelopes"]])
    beta = 2500.0

    def softmin_and_gradient(q):
        growth = P_tune @ np.log(q / upper)
        shifted = growth - np.min(growth)
        weights = np.exp(-beta * shifted)
        weights /= weights.sum()
        softmin = float(np.min(growth) - np.log(np.exp(-beta * shifted).sum()) / beta)
        gradient = weights @ (P_tune / q[None, :])
        return softmin, gradient

    result = minimize(
        fun=lambda q: -softmin_and_gradient(q)[0],
        x0=mixture,
        jac=lambda q: -softmin_and_gradient(q)[1],
        method="SLSQP",
        bounds=[(1e-12, 1.0)] * 6,
        constraints=[{"type": "eq", "fun": lambda q: float(np.sum(q) - 1), "jac": lambda q: np.ones(6)}],
        options={"ftol": 1e-13, "maxiter": 1000, "disp": False},
    )
    if not result.success or abs(float(np.sum(result.x)) - 1) > 1e-10:
        raise RuntimeError(f"softmin proposal optimization failed: {result.message}")

    # Freeze a reproducible rational q: round the first five components to 14
    # decimal places and choose the sixth as the exact remainder.
    q_rat = [Fraction(str(round(float(x), 14))) for x in result.x[:5]]
    q_rat.append(Fraction(1) - sum(q_rat, Fraction(0)))
    if any(x <= 0 for x in q_rat) or sum(q_rat, Fraction(0)) != 1:
        raise RuntimeError("rationalized minimax proposal is not a positive probability vector")
    q = np.array([float(x) for x in q_rat])

    P_dense = make_laws(template, PM_DENSE)
    dense_growth = P_dense @ np.log(q / upper)
    tune_growth = P_tune @ np.log(q / upper)
    scalar = cert["scalar_mean_eincrement_comparison"]
    result_json = {
        "classification": "FINITE_MODEL_GRID_SOFTMIN_PROXY_FOR_MAXIMIN_Q_SELECTION_NOT_DATA_TUNING",
        "optimizer": {"method": "SciPy SLSQP on smooth soft-min of all 303 alternative rows", "success": bool(result.success), "message": str(result.message), "iterations": int(result.nit), "softmin_beta": beta, "softmin_approximation_gap_bound": float(np.log(len(P_tune)) / beta), "finite_grid_objective": float(np.min(tune_growth))},
        "alternative_grid": {"burst_p": list(PB_ALT), "tuning_measurement_p": [float(PM_TUNE[0]), float(PM_TUNE[-1]), len(PM_TUNE)], "dense_measurement_sensitivity_grid": [float(PM_DENSE[0]), float(PM_DENSE[-1]), len(PM_DENSE)]},
        "rational_q": [{"numerator": str(x.numerator), "denominator": str(x.denominator)} for x in q_rat],
        "q_float": q.tolist(),
        "q_sums_exactly_to_one": sum(q_rat, Fraction(0)) == 1,
        "e_factor": (q / upper).tolist(),
        "minimum_expected_log_tuning_grid": float(np.min(tune_growth)),
        "minimum_expected_log_dense_sensitivity_grid": float(np.min(dense_growth)),
        "maximum_expected_log_dense_sensitivity_grid": float(np.max(dense_growth)),
        "scalar_mean_fixed_lambda_minimum_on_prior_dense_grid": scalar["minimum_expected_log_increment_on_same_alternative_grid"],
        "comparison": "The proposal maximizes a smooth soft-min surrogate on a model-generated finite alternative grid, not the exact minimum objective. The pointwise soft-min approximation gap is bounded by log(N)/beta, while numerical optimizer convergence does not independently certify a global optimum. Dense-grid checking reduces but does not remove grid-selection risk; alternative continuous drift is not certified. Any fixed normalized q remains null-valid analytically under the exact category envelope, subject to exact constant implementation.",
        "limitations": ["The proposal selection uses only deterministic model laws, not observations or outcomes.", "The optimizer is numerical and the stated objective is a finite-grid maximin criterion.", "The continuous alternative expected-log lower bound is not established.", "No stream, alarm, decoder action, or logical outcome was evaluated."],
    }
    out = HERE / "COFIRE_CATEGORY_PROPOSAL_MINIMAX.json"
    out.write_text(json.dumps(result_json, indent=2) + "\n", encoding="utf-8")
    print("optimizer", result.message, "iterations", result.nit)
    print("minimax_tune", result_json["minimum_expected_log_tuning_grid"], "minimax_dense", result_json["minimum_expected_log_dense_sensitivity_grid"], "scalar", scalar["minimum_expected_log_increment_on_same_alternative_grid"])
    print(f"wrote={out}")


if __name__ == "__main__":
    main()
