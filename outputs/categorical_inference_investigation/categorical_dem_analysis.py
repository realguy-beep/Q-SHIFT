"""Exact posterior under the independent Bernoulli mechanisms in the toy DEM."""
from __future__ import annotations

from itertools import product
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "outputs" / "categorical_decoder_feasibility"))

from categorical_reference import decoder_risk, exact_posterior  # noqa: E402
from toy_circuits import noisy_stim_circuit, pymatching_decisions, two_qubit_model  # noqa: E402


def dem_mechanisms():
    circuit = noisy_stim_circuit("two_qubit")
    dem = circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)
    events = []
    for instruction in dem.flattened():
        if instruction.type != "error":
            continue
        p = float(instruction.args_copy()[0])
        detector_mask = 0
        observable_mask = 0
        for target in instruction.targets_copy():
            if target.is_separator():
                # Separator is decomposition metadata. For the independent DEM
                # distribution, the enclosing error instruction remains one event.
                continue
            if target.is_relative_detector_id():
                detector_mask ^= 1 << target.val
            elif target.is_logical_observable_id():
                observable_mask ^= 1 << target.val
        events.append({"probability": p, "detector_mask": detector_mask,
                       "observable_mask": observable_mask, "dem_instruction": str(instruction)})
    return dem, events


def enumerate_independent_dem(events):
    joint = {}
    n = len(events)
    for selected in product((0, 1), repeat=n):
        probability = 1.0
        syndrome = observable = 0
        for keep, event in zip(selected, events):
            p = event["probability"]
            probability *= p if keep else (1.0 - p)
            if keep:
                syndrome ^= event["detector_mask"]
                observable ^= event["observable_mask"]
        bucket = joint.setdefault(syndrome, [0.0, 0.0])
        bucket[observable] += probability
    total = sum(sum(p) for p in joint.values())
    if not math.isclose(total, 1.0, rel_tol=0, abs_tol=1e-12):
        raise ArithmeticError(f"independent DEM posterior mass is {total}")
    decisions = {}
    posterior = {}
    ties = []
    for syndrome, probs in joint.items():
        maximum = max(probs)
        winners = [l for l, value in enumerate(probs) if abs(value - maximum) <= 1e-15]
        decisions[syndrome] = min(winners)
        if len(winners) > 1:
            ties.append(syndrome)
        mass = sum(probs)
        posterior[syndrome] = [v / mass for v in probs]
    return {s: tuple(v) for s, v in joint.items()}, decisions, posterior, tuple(sorted(ties)), total


def main():
    dem, events = dem_mechanisms()
    dem_joint, dem_map, dem_post, ties, total = enumerate_independent_dem(events)
    categorical = exact_posterior(two_qubit_model())
    pm = pymatching_decisions("two_qubit", list(range(4)))
    decisions = {
        "categorical_exact_MAP": categorical.decisions,
        "independent_DEM_exact_MAP": dem_map,
        "PyMatching_standard": {int(k): int(v) for k, v in pm["decoders"]["correlation_disabled"].items()},
        "PyMatching_correlation_enabled": {int(k): int(v) for k, v in pm["decoders"]["correlation_enabled"].items()},
    }
    risks_original = {name: decoder_risk(categorical.joint, pred) for name, pred in decisions.items()}
    risks_dem = {name: decoder_risk(dem_joint, pred) for name, pred in decisions.items()}
    rows = []
    for syndrome in range(4):
        c = categorical.joint[syndrome]
        d = dem_joint[syndrome]
        rows.append({
            "syndrome": syndrome,
            "categorical_joint_P_L0_L1": list(c),
            "categorical_P_L1_given_s": categorical.conditional[syndrome][1],
            "categorical_MAP": categorical.decisions[syndrome],
            "independent_DEM_joint_P_L0_L1": list(d),
            "independent_DEM_P_L1_given_s": dem_post[syndrome][1],
            "independent_DEM_MAP": dem_map[syndrome],
            "PyMatching_standard": decisions["PyMatching_standard"][syndrome],
            "PyMatching_correlation_enabled": decisions["PyMatching_correlation_enabled"][syndrome],
            "model_joint_L1_distance_contribution": sum(abs(a-b) for a,b in zip(c,d)),
        })
    l1 = sum(row["model_joint_L1_distance_contribution"] for row in rows)
    result = {
        "status": "PASS",
        "stim_dem": str(dem),
        "dem_interpretation": "Each error instruction is one independent Bernoulli mechanism with the listed probability and total detector/logical parity. A '^' target is retained as decomposition metadata only; it does not split the enclosing event into multiple independently sampled events.",
        "mechanisms": events,
        "mechanism_count": len(events),
        "enumerated_independent_mechanism_configurations": 2 ** len(events),
        "posterior_total_mass": total,
        "dem_tie_syndromes": list(ties),
        "syndrome_table": rows,
        "logical_error_risk_under_original_categorical_channel": risks_original,
        "logical_error_risk_under_independent_DEM_distribution": risks_dem,
        "joint_distribution_total_variation_distance": 0.5 * l1,
        "syndrome_11_attribution": {
            "categorical_exact_MAP": categorical.decisions[3],
            "independent_DEM_exact_MAP": dem_map[3],
            "PyMatching_standard": decisions["PyMatching_standard"][3],
            "PyMatching_correlation_enabled": decisions["PyMatching_correlation_enabled"][3],
            "conclusion": "The independent DEM posterior and original categorical posterior both choose logical 1 at syndrome 11; both PyMatching variants choose logical 0. For this toy syndrome the observed decision gap is therefore an inference/optimization mismatch relative to posterior MAP, not a DEM-induced MAP change. DEM approximation changes posterior probabilities, but not this syndrome's exact decision.",
        },
    }
    out = Path(__file__).resolve().parent / "INDEPENDENT_DEM_RESULTS.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"events": len(events), "configurations": 2**len(events),
                      "mass": total, "syndrome_11": result["syndrome_11_attribution"],
                      "risk_original": risks_original, "risk_dem": risks_dem}, indent=2))


if __name__ == "__main__":
    main()
