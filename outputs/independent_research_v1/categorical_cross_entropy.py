"""Cross-entropy projection proposal for exact categorical circuit importance sampling."""
from __future__ import annotations

import json
import resource
import sys
import time
from pathlib import Path

import numpy as np
import stim
import pymatching

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PHASE2B = REPO / "outputs" / "phase2b_pauli_bias"
sys.path.insert(0, str(PHASE2B))
from noise_model import MEMORY_BASES, REGIMES, build_circuit  # noqa: E402
from categorical_importance_sampler import (  # noqa: E402
    categorical_log_weights,
    decode_failures,
    instrument_circuit,
)

TRAIN_SHOTS = 100000
VALIDATION_SHOTS = 20000
SHRINKAGE_MASS = 50.0
GLOBAL_ALPHA = 5.0
TRAIN_SEEDS = (2026111001, 2026111002, 2026111003, 2026111004, 2026111005, 2026111006)
DIRECT_SEEDS = (2026111011, 2026111012, 2026111013, 2026111014, 2026111015, 2026111016)
GLOBAL_SEEDS = (2026111021, 2026111022, 2026111023, 2026111024, 2026111025, 2026111026)
CE_SEEDS = (2026111031, 2026111032, 2026111033, 2026111034, 2026111035, 2026111036)
CONDITIONS = tuple((basis, regime) for basis in MEMORY_BASES for regime in REGIMES)


def proposal_from_training(circuit: stim.Circuit, matching: pymatching.Matching,
                           seed: int) -> tuple[list[list[float]], dict]:
    train_circuit, train_events = instrument_circuit(circuit, GLOBAL_ALPHA)
    detectors, outputs = train_circuit.compile_detector_sampler(seed=seed).sample(
        shots=TRAIN_SHOTS, separate_observables=True)
    base_logicals = outputs[:, :circuit.num_observables]
    flags = outputs[:, circuit.num_observables:].reshape(TRAIN_SHOTS, len(train_events), 4)
    logw, codes = categorical_log_weights(flags, train_events)
    weights = np.exp(logw)
    failures = decode_failures(matching, detectors, base_logicals)
    weighted_failure = weights*failures
    total_weighted_failure = float(weighted_failure.sum())
    q_vectors: list[list[float]] = []
    event_diagnostics = []
    for j, event in enumerate(train_events):
        p16 = np.asarray([event["p_identity"], *event["p"]], dtype=np.float64)
        counts = np.bincount(codes[:, j], weights=weighted_failure, minlength=16)
        q16 = (counts + SHRINKAGE_MASS*p16)/(total_weighted_failure+SHRINKAGE_MASS)
        if np.any(q16 <= 0) or not np.isclose(q16.sum(), 1.0, atol=1e-10):
            raise RuntimeError(f"cross-entropy proposal invalid at event {j}")
        q_vectors.append(q16[1:].astype(float).tolist())
        event_diagnostics.append({
            "p_identity": float(p16[0]),
            "p_nonidentity": float(1-p16[0]),
            "q_identity": float(q16[0]),
            "q_nonidentity": float(1-q16[0]),
            "minimum_nonidentity_q": float(q16[1:].min()),
            "maximum_nonidentity_q": float(q16[1:].max()),
        })
    failure_weights = weights[failures]
    training = {
        "shots": TRAIN_SHOTS,
        "unweighted_failures_under_global_tilt": int(failures.sum()),
        "weighted_failure_mass": total_weighted_failure,
        "failure_weight_ess": (float(failure_weights.sum()**2/np.square(failure_weights).sum())
                               if len(failure_weights) and np.square(failure_weights).sum() else 0.0),
        "max_abs_log_weight": float(np.max(np.abs(logw))),
        "event_diagnostics": event_diagnostics,
    }
    return q_vectors, training


def sample_arm(circuit: stim.Circuit, matching: pymatching.Matching, *, shots: int,
               seed: int, mode: str, proposal: list[list[float]] | None = None) -> dict:
    if mode == "direct":
        sample_circuit, events = instrument_circuit(circuit, 1.0)
    elif mode == "global_5x":
        sample_circuit, events = instrument_circuit(circuit, GLOBAL_ALPHA)
    elif mode == "cross_entropy":
        if proposal is None:
            raise ValueError("cross-entropy mode requires a frozen proposal")
        sample_circuit, events = instrument_circuit(circuit, 1.0, channel_proposals=proposal)
    else:
        raise ValueError(mode)
    detectors, outputs = sample_circuit.compile_detector_sampler(seed=seed).sample(
        shots=shots, separate_observables=True)
    logicals = outputs[:, :circuit.num_observables]
    failures = decode_failures(matching, detectors, logicals)
    if mode == "direct":
        weighted = failures.astype(np.float64)
    else:
        flags = outputs[:, circuit.num_observables:].reshape(shots, len(events), 4)
        logw, _ = categorical_log_weights(flags, events)
        weighted = np.exp(logw)*failures
    estimate = float(weighted.mean())
    se = float(weighted.std(ddof=1)/np.sqrt(shots)) if shots > 1 else float("inf")
    return {
        "mode": mode,
        "seed": seed,
        "shots": shots,
        "unweighted_failures": int(failures.sum()),
        "ler_estimate": estimate,
        "standard_error": se,
        "relative_standard_error": se/estimate if estimate > 0 else float("inf"),
        "failure_weight_ess": (float(weighted[failures].sum()**2/np.square(weighted[failures]).sum())
                               if np.any(failures) and np.square(weighted[failures]).sum() else 0.0),
        "max_abs_log_weight": 0.0 if mode == "direct" else float(np.max(np.abs(logw))),
        "max_weight": 1.0 if mode == "direct" else float(np.exp(logw).max()),
    }


def main() -> int:
    results = []
    started = time.perf_counter()
    for i, ((basis, regime), train_seed, direct_seed, global_seed, ce_seed) in enumerate(zip(
            CONDITIONS, TRAIN_SEEDS, DIRECT_SEEDS, GLOBAL_SEEDS, CE_SEEDS, strict=True)):
        circuit = build_circuit(basis, regime)
        dem = circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=0.0018)
        matching = pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)
        q_vectors, training = proposal_from_training(circuit, matching, train_seed)
        validation_start = time.perf_counter()
        arms = [
            sample_arm(circuit, matching, shots=VALIDATION_SHOTS, seed=direct_seed, mode="direct"),
            sample_arm(circuit, matching, shots=VALIDATION_SHOTS, seed=global_seed, mode="global_5x"),
            sample_arm(circuit, matching, shots=VALIDATION_SHOTS, seed=ce_seed,
                       mode="cross_entropy", proposal=q_vectors),
        ]
        by_mode = {arm["mode"]: arm for arm in arms}
        direct = by_mode["direct"]
        global_tilt = by_mode["global_5x"]
        candidate = by_mode["cross_entropy"]
        compatible = {}
        for comparator in (direct, global_tilt):
            diff = candidate["ler_estimate"]-comparator["ler_estimate"]
            combined_se = float(np.hypot(candidate["standard_error"], comparator["standard_error"]))
            compatible[comparator["mode"]] = {
                "difference": diff,
                "combined_standard_error": combined_se,
                "absolute_z": abs(diff/combined_se) if combined_se else 0.0,
                "within_3_se": bool(abs(diff) <= 3*combined_se),
            }
        advances = (
            candidate["standard_error"] <= 0.75*direct["standard_error"] and
            candidate["standard_error"] <= 0.75*global_tilt["standard_error"] and
            all(x["within_3_se"] for x in compatible.values())
        )
        results.append({
            "memory_basis": basis,
            "regime": regime,
            "training": training,
            "validation_arms": arms,
            "cross_entropy_vs_comparators": compatible,
            "condition_advancement_gate_passed": bool(advances),
            "validation_seconds": time.perf_counter()-validation_start,
            "proposal_q_nonidentity_range": [
                min(min(q) for q in q_vectors), max(max(q) for q in q_vectors)],
        })
        print(basis, regime,
              {a["mode"]: (round(a["ler_estimate"], 7), round(a["relative_standard_error"], 3)) for a in arms},
              "gate", advances)
    gate_count = sum(row["condition_advancement_gate_passed"] for row in results)
    output = {
        "status": "cross_entropy_proposal_development_validation",
        "stim_version": stim.__version__,
        "pymatching_version": pymatching.__version__,
        "proposal": "per-location categorical failure-marginal forward-KL projection",
        "global_training_tilt": GLOBAL_ALPHA,
        "shrinkage_mass_baseline_observations": SHRINKAGE_MASS,
        "training_shots_per_condition": TRAIN_SHOTS,
        "validation_shots_per_arm_per_condition": VALIDATION_SHOTS,
        "conditions": results,
        "conditions_passed_advancement_gate": int(gate_count),
        "all_conditions_passed": gate_count == len(results),
        "elapsed_seconds": time.perf_counter()-started,
        "stochastic_circuit_shots": len(results)*(TRAIN_SHOTS+3*VALIDATION_SHOTS),
        "scope": "training and validation are separate exact categorical circuit samples; decoder remains fixed to approximate-DEM PyMatching",
        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    target = HERE/"categorical_cross_entropy_results.json"
    target.write_text(json.dumps(output, indent=2)+"\n", encoding="utf-8")
    print(f"Wrote {target}; gate passed {gate_count}/6; elapsed={output['elapsed_seconds']:.3f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
