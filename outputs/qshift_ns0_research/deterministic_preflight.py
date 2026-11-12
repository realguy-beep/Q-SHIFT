"""Reproduce the non-sampling Q-SHIFT/HAMLD structural and planning checks.

This script constructs Stim circuits/DEMs and reads historical development CSVs.
It does not compile a sampler, generate detector shots, decode syndromes, or
inspect protected evaluation material.
"""
from __future__ import annotations

import csv
import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "outputs" / "phase3a_correlated_noise_preflight"))
from simulator import build_spatial_burst_circuit  # noqa: E402


def dem_summary(burst_p: float, decompose: bool) -> dict:
    circuit = build_spatial_burst_circuit(
        memory_basis="z", regime="balanced", distance=3, rounds=5,
        gate_p=0.003, measurement_p=0.003, burst_probability=burst_p,
    )
    dem = circuit.detector_error_model(
        decompose_errors=decompose, approximate_disjoint_errors=True
    )
    errors = [inst for inst in dem if inst.type == "error"]
    return {
        "burst_p": burst_p,
        "decompose_errors": decompose,
        "detectors": dem.num_detectors,
        "observables": dem.num_observables,
        "instructions": len(list(dem)),
        "errors": len(errors),
        "separator_errors": sum(
            any(t.is_separator() for t in inst.targets_copy()) for inst in errors
        ),
        "max_detector_targets": max(
            (sum(t.is_relative_detector_id() for t in inst.targets_copy()) for inst in errors),
            default=0,
        ),
        "observable_errors": sum(
            any(t.is_logical_observable_id() for t in inst.targets_copy())
            for inst in errors
        ),
        "single_detector_error_mechanisms": sum(
            sum(t.is_relative_detector_id() for t in inst.targets_copy()) == 1
            for inst in errors
        ),
        "first_four_detector_coordinates": {
            str(k): v for k, v in list(circuit.get_detector_coordinates().items())[:4]
        },
        "last_three_detector_coordinates": {
            str(k): v for k, v in list(circuit.get_detector_coordinates().items())[-3:]
        },
        "observable_include": [
            str(inst) for inst in circuit.flattened()
            if inst.name == "OBSERVABLE_INCLUDE"
        ],
    }


def historical_and_power() -> dict:
    path = ROOT / "outputs/stage4_noise_adaptive_development_v1/PAIRED_COMPARISONS.csv"
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    nz = [r for r in rows if float(r["probability"]) > 0]
    cand_only = sum(int(r["estimated_candidate_only_vs_fixed"]) for r in nz)
    fixed_only = sum(int(r["estimated_fixed_only_vs_fixed"]) for r in nz)
    shots = sum(int(r["shots"]) for r in nz)
    q_hist = (cand_only + fixed_only) / shots

    # Small-sample historical component sensitivity: within each of four
    # nonzero strata, subtract the paired shot-noise term q/m from root
    # difference variance; truncate at zero, then pool by residual df.
    strata = []
    for p in ("0.004", "0.008", "0.012", "0.016"):
        rr = [r for r in nz if r["probability"] == p]
        diffs = [
            (int(r["detector_estimated_errors"]) - int(r["fixed_nominal_errors"]))
            / int(r["shots"])
            for r in rr
        ]
        q = sum(
            int(r["estimated_candidate_only_vs_fixed"])
            + int(r["estimated_fixed_only_vs_fixed"])
            for r in rr
        ) / sum(int(r["shots"]) for r in rr)
        m = int(rr[0]["shots"])
        tau2 = max(0.0, statistics.variance(diffs) - q / m)
        strata.append({"p": p, "roots": len(rr), "q": q, "tau2": tau2})
    tau = math.sqrt(
        sum((s["roots"] - 1) * s["tau2"] for s in strata)
        / sum(s["roots"] - 1 for s in strata)
    )

    scenarios = []
    for q, root_sd in [
        (0.001, tau), (q_hist, tau), (0.01, tau),
        (0.001, 0.0002), (q_hist, 0.0002), (0.01, 0.0002),
    ]:
        se = math.sqrt(q / 10_000 + root_sd**2) / math.sqrt(24)
        z_effect = 0.0002 / se
        alpha_critical = 1.959963984540054
        # Two-sided normal power under a fixed alternative.
        power = 0.5 * math.erfc((alpha_critical - z_effect) / math.sqrt(2))
        power += 0.5 * math.erfc((alpha_critical + z_effect) / math.sqrt(2))
        scenarios.append({
            "q": q, "root_sd": root_sd, "se": se,
            "ci95_halfwidth": alpha_critical * se,
            "mde_80_two_sided": (alpha_critical + 0.8416212335729143) * se,
            "power_for_abs_effect_0.0002": power,
        })
    return {
        "historical_stage4_nonzero": {
            "roots": len({(r["probability"], r["root"]) for r in nz}),
            "shots": shots, "candidate_only": cand_only,
            "fixed_only": fixed_only, "discordance_q": q_hist,
            "primary_mean_difference": (391 - 506) / 70_000,
        },
        "exploratory_pooled_historical_root_sd": tau,
        "stratum_components": strata,
        "normal_approximation_scenarios": scenarios,
    }


def main() -> None:
    summaries = [
        dem_summary(p, decompose)
        for p in (0.0, 0.01)
        for decompose in (False, True)
    ]
    assert all(x["detectors"] == 40 and x["observables"] == 1 for x in summaries)
    assert summaries[0]["errors"] == 443 and summaries[0]["separator_errors"] == 0
    assert summaries[1]["errors"] == 586 and summaries[1]["separator_errors"] == 444
    assert summaries[2]["errors"] == 448 and summaries[2]["separator_errors"] == 0
    assert summaries[3]["errors"] == 591 and summaries[3]["separator_errors"] == 444
    assert (506 - 391) / 506 * 100 == 22.727272727272727
    assert (590 - 474) / 590 * 100 == 19.661016949152543
    assert len([False] * summaries[0]["detectors"]) == 40
    assert len([False]) == summaries[0]["observables"]
    # Deterministic hand cases establish only input representation and Stim
    # target mapping; no HAMLD prediction is attempted.
    zero = [False] * summaries[0]["detectors"]
    one_hot = [False] * summaries[0]["detectors"]
    one_hot[0] = True
    toy = __import__("stim").DetectorErrorModel("error(0.1) D0 L0")
    target_fault = next(inst for inst in toy if inst.type == "error")
    det_ids = [t.val for t in target_fault.targets_copy() if t.is_relative_detector_id()]
    obs_ids = [t.val for t in target_fault.targets_copy() if t.is_logical_observable_id()]
    assert len(zero) == len(one_hot) == 40 and sum(zero) == 0 and sum(one_hot) == 1
    assert det_ids == [0] and obs_ids == [0]
    print(json.dumps({
        "dem": [{k: v for k, v in x.items() if "coordinates" not in k and "observable_include" not in k} for x in summaries],
        "detector_coordinates_first4": summaries[0]["first_four_detector_coordinates"],
        "detector_coordinates_last3": summaries[0]["last_three_detector_coordinates"],
        "observable_include": summaries[0]["observable_include"],
        "deterministic_input_cases": {
            "zero_syndrome_shape": [1, len(zero)], "zero_syndrome_weight": sum(zero),
            "one_hot_syndrome_shape": [1, len(one_hot)], "one_hot_index": 0,
            "hand_constructed_stim_error_targets": {"detectors": det_ids, "observables": obs_ids},
            "hamld_prediction_attempted": False,
        },
        "historical_and_power": historical_and_power(),
    }, indent=2))


if __name__ == "__main__":
    main()
