"""Illustrative Lorden/KL information scale from deterministic model laws.

This computes log(ARL)/D(P1||P0) for fixed IID simple hypotheses. It is the
first-order asymptotic lower-bound scale in classical quickest-change theory,
not a finite-sample delay prediction or a calibrated Q-SHIFT alarm result.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "BURST_STEP_INFORMATION_AUDIT.json"
OUTPUT = HERE / "QCD_LOWER_BOUND_SCALE.json"
ARL_TARGETS = (100, 1_000, 10_000)
TRANSITIONS = ((0.002, 0.010), (0.010, 0.018), (0.002, 0.018))


def main() -> None:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    rows = []
    for model in ("exact_categorical_circuit", "approximate_dem"):
        for old_p, new_p in TRANSITIONS:
            nominal = next(r for r in data["rows"]
                if r["old_burst_p"] == old_p and r["new_burst_p"] == new_p
                and r["measurement_p"] == 0.003)[model]["KL_new_given_old_nats_per_shot"]
            nuisance = next(r for r in data["measurement_nuisance_grid_minima"]
                if r["model"] == model and r["old_burst_p"] == old_p
                and r["new_burst_p"] == new_p)
            grid_min = nuisance["min_KL_new_given_old_over_independent_old_new_measurement_p_grid"]
            rows.append({
                "model": model,
                "old_burst_p": old_p,
                "new_burst_p": new_p,
                "nominal_measurement_p": 0.003,
                "nominal_D_new_given_old_nats_per_shot": nominal,
                "coarse_nuisance_grid_D_min_nats_per_shot": grid_min,
                "coarse_grid_attaining_measurement_ps": nuisance["measurement_p_old_new_attaining_minimum"],
                "illustrative_log_ARL_over_D_scales_shots": {
                    str(gamma): {
                        "nominal_simple_hypothesis": math.log(gamma) / nominal,
                        "coarse_grid_information_sensitivity_only": math.log(gamma) / grid_min,
                    } for gamma in ARL_TARGETS
                },
            })
    result = {
        "classification": "ASYMPTOTIC_KL_DELAY_LOWER_BOUND_SCALE_NOT_FINITE_HISTORY_ALARM_PERFORMANCE",
        "source_result": SOURCE.name,
        "method": "For known IID pre/post laws and Lorden worst-case delay, record the first-order asymptotic scale log(gamma)/D(P1||P0) under mean-time-to-false-alarm constraint gamma. Values are arithmetic only.",
        "illustrative_arl_targets_shots": list(ARL_TARGETS),
        "rows": rows,
        "assumptions_and_limits": [
            "The classical result assumes independent observations and known simple pre-change and post-change laws. Q-SHIFT's ten-bit detector vector is treated as one completed-shot observation.",
            "These values are asymptotic lower-bound scales as false-alarm horizon grows, not expected delays of CUSUM or another realized procedure. They are not finite-sample guarantees.",
            "The coarse nuisance calculation checks only old/new measurement p in {0.001,0.003,0.005}; it is not an infimum over a continuous composite nuisance family and cannot establish a robust composite lower bound.",
            "Only ten selected detectors are used. Full detector observations could carry more information. No alarm is calibrated, no history is generated, and no decoder outcome is evaluated.",
            "The listed ARL values are illustrative sensitivity points, not recommended owner-approved requirements or protocol choices."
        ],
        "sampling_calls": 0,
        "decoder_calls": 0,
    }
    OUTPUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": OUTPUT.name, "rows": rows}, indent=2))


if __name__ == "__main__":
    main()
