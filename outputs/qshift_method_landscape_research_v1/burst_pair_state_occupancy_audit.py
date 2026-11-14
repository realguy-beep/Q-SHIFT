"""Exact expected state occupancy for the ten burst-pair detector outcomes."""
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

P_VALUES = (0.002, 0.010, 0.018)
PM = 0.003
WINDOWS = (25, 50, 100, 200, 500)


def distributions() -> dict[str, dict[float, np.ndarray]]:
    base = grid.construct(0.010, PM)
    template, _ = grid.categorical_sites(base)
    result = {"exact_categorical_circuit": {}, "approximate_dem": {}}
    for p in P_VALUES:
        c = grid.construct(p, PM)
        exact = direct_xor(grid.reweight(template, c), info.SELECTED)
        _, mechanisms = build_dem(p, PM)
        dem = direct_xor_convolution(mechanisms, info.SELECTED)
        for model, dist in (("exact_categorical_circuit", exact), ("approximate_dem", dem)):
            if np.any(dist < 0) or abs(float(dist.sum()) - 1.0) > 2e-12:
                raise RuntimeError("invalid detector-state law")
            result[model][p] = dist
    return result


def occupancy(prob: np.ndarray, window: int) -> dict:
    # Exact expectations under independent, identically distributed shots.
    seen = -np.expm1(window * np.log1p(-prob))
    singleton = window * prob * np.exp((window - 1) * np.log1p(-prob))
    return {
        "window_shots": window,
        "expected_occupied_states": float(seen.sum()),
        "expected_unoccupied_states": float(len(prob) - seen.sum()),
        "expected_singleton_states": float(singleton.sum()),
        "states_with_expected_count_below_1": int(np.count_nonzero(window * prob < 1)),
        "states_with_expected_count_below_5": int(np.count_nonzero(window * prob < 5)),
        "states_with_probability_below_1_over_window": int(np.count_nonzero(prob < 1/window)),
    }


def main() -> None:
    laws = distributions()
    rows = []
    max_norm = 0.0
    for model, model_laws in laws.items():
        for p, dist in model_laws.items():
            max_norm = max(max_norm, abs(float(dist.sum())-1))
            rows.append({"model": model, "burst_p": p, "measurement_p": PM,
                "positive_probability_states": int(np.count_nonzero(dist)),
                "effective_support_entropy_exp": float(np.exp(-np.sum(dist[dist>0]*np.log(dist[dist>0])))),
                "effective_support_inverse_collision": float(1/np.sum(dist**2)),
                "windows": [occupancy(dist, w) for w in WINDOWS]})
    result = {
        "classification": "DETERMINISTIC_EXPECTED_OCCUPANCY_NOT_HISTORY_GENERATION",
        "configuration": {"detector_bits": list(info.SELECTED), "state_count": 2**len(info.SELECTED),
            "measurement_p": PM, "burst_values": list(P_VALUES), "windows": list(WINDOWS)},
        "method": "For IID draws from each exact outcome distribution q_s, compute E[occupied]=sum_s[1-(1-q_s)^W] and E[singletons]=sum_s W q_s(1-q_s)^(W-1). No draws are made.",
        "rows": rows,
        "validation": {"maximum_normalization_error": max_norm,
            "occupied_expectation_in_bounds": all(0 <= r['windows'][0]['expected_occupied_states'] <= 1024 for r in rows)},
        "interpretation": [
            "A full 1024-cell multinomial table may be sparsely observed at short W, particularly in rare cells. However, the proposed full likelihood has only the declared low-dimensional model parameters; it is not an unconstrained 1024-parameter fit.",
            "Expected occupancy does not characterize the finite-history estimator bias/RMSE, numerical likelihood conditioning, boundary mass, or robustness. Those require exact count-distribution analysis or an authorized study.",
            "Results assume stationary independent shots at a fixed point. Across-shot drift invalidates the IID occupancy formula for a pooled window unless the mixture is modeled."
        ], "sampling_calls": 0, "decoder_calls": 0}
    (HERE / "BURST_PAIR_STATE_OCCUPANCY_AUDIT.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"rows": [{"model": r["model"], "burst_p": r["burst_p"],
        "effective_support": r["effective_support_entropy_exp"], "windows": r["windows"]} for r in rows],
        "validation": result["validation"]}, indent=2))


if __name__ == "__main__":
    main()
