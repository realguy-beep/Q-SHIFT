"""Compare three syndrome rounds plus data idles against five active rounds."""
from __future__ import annotations

import json
import math
import re
import sys
import time
from pathlib import Path

import numpy as np
import pymatching
import stim

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "outputs" / "phase2b_pauli_bias"))
from noise_model import build_circuit as phase2b_build_circuit  # noqa: E402
from noise_model import one_qubit_probabilities, two_qubit_probabilities  # noqa: E402

CONDITIONS = (("x", "x_biased"), ("z", "z_biased"))
PREFLIGHT_SEEDS = (2026113701, 2026113702, 2026113703, 2026113704)
MAIN_SEEDS = (2026113711, 2026113712, 2026113713, 2026113714)
PREFLIGHT_SHOTS = 100
MAIN_SHOTS = 500_000
GATE_P = MEAS_P = 0.003
BIAS_RATIO = 10.0
DEM_THRESHOLD = 0.0018


def source_circuit(memory_basis: str, regime: str, rounds: int) -> stim.Circuit:
    p1 = one_qubit_probabilities(regime, GATE_P, BIAS_RATIO)
    p2 = two_qubit_probabilities(regime, GATE_P, BIAS_RATIO)
    generated = stim.Circuit.generated(
        f"surface_code:rotated_memory_{memory_basis}", distance=3, rounds=rounds,
        after_clifford_depolarization=GATE_P, before_measure_flip_probability=MEAS_P)
    body = str(generated)
    one = "PAULI_CHANNEL_1(" + ",".join(format(x, ".17g") for x in p1) + ")"
    two = "PAULI_CHANNEL_2(" + ",".join(format(x, ".17g") for x in p2) + ")"
    body, n1 = re.subn(r"DEPOLARIZE1\([^)]*\)", one, body)
    body, n2 = re.subn(r"DEPOLARIZE2\([^)]*\)", two, body)
    if not n1 or not n2:
        raise RuntimeError("failed to replace generated depolarizing channels")
    circuit = stim.Circuit(body)
    expected = {3: 24, 5: 40}[rounds]
    if circuit.num_detectors != expected or circuit.num_observables != 1:
        raise RuntimeError("generated source circuit shape mismatch")
    return circuit


def resources(circuit: stim.Circuit) -> dict:
    flat = circuit.flattened()
    counts = {name: 0 for name in ("PAULI_CHANNEL_1", "PAULI_CHANNEL_2")}
    targets = {name: 0 for name in ("PAULI_CHANNEL_1", "PAULI_CHANNEL_2")}
    for inst in flat:
        if inst.name in counts:
            counts[inst.name] += 1
            targets[inst.name] += len(inst.targets_copy())
    return {
        "qubits": int(circuit.num_qubits),
        "detectors": int(circuit.num_detectors),
        "observables": int(circuit.num_observables),
        "two_qubit_pair_sites": targets["PAULI_CHANNEL_2"] // 2,
        "one_qubit_pauli_targets": targets["PAULI_CHANNEL_1"],
        "one_qubit_instruction_count": counts["PAULI_CHANNEL_1"],
        "two_qubit_instruction_count": counts["PAULI_CHANNEL_2"],
    }


def make_idle_circuit(memory_basis: str, regime: str, idle_p: float = GATE_P) -> tuple[stim.Circuit, dict]:
    source = source_circuit(memory_basis, regime, 3).flattened()
    p1 = one_qubit_probabilities(regime, idle_p, BIAS_RATIO)
    out = stim.Circuit()
    data_targets = None
    idle_inserted = False
    for inst in source:
        if inst.name in ("M", "MX", "MY"):
            data_targets = list(inst.targets_copy())
            if len(data_targets) != 9:
                raise RuntimeError(f"expected nine terminal data measurements, found {len(data_targets)}")
            for idle_cycle in range(2):
                out.append("PAULI_CHANNEL_1", data_targets, p1)
                if idle_cycle == 0:
                    out.append("TICK")
            idle_inserted = True
        out.append(inst.name, inst.targets_copy(), inst.gate_args_copy())
    if not idle_inserted:
        raise RuntimeError("did not find terminal data measurement")
    return out, {"idle_cycles": 2, "idle_data_qubits_per_cycle": 9,
                 "idle_pauli_targets": 18, "idle_total_error_probability": float(sum(p1)),
                 "idle_p": idle_p,
                 "idle_pauli_probabilities_XYZ": list(p1),
                 "terminal_data_qubits": [int(x.value) for x in data_targets]}


def circuit_for(arm: str, basis: str, regime: str, idle_p: float = GATE_P) -> tuple[stim.Circuit, dict]:
    if arm == "three_rounds_plus_idle":
        return make_idle_circuit(basis, regime, idle_p=idle_p)
    if arm == "five_active_rounds":
        circuit = source_circuit(basis, regime, 5)
        return circuit, {"idle_cycles": 0, "idle_data_qubits_per_cycle": 0,
                         "idle_pauli_targets": 0, "terminal_data_qubits": []}
    raise ValueError(arm)


def terminal_data_targets(circuit: stim.Circuit) -> list[int]:
    measurements = [inst for inst in circuit.flattened() if inst.name in ("M", "MX", "MY")]
    if len(measurements) != 1:
        raise RuntimeError("expected one terminal data measurement instruction")
    return [int(t.value) for t in measurements[0].targets_copy()]


def make_matching(circuit: stim.Circuit) -> pymatching.Matching:
    dem = circuit.detector_error_model(
        decompose_errors=True, approximate_disjoint_errors=DEM_THRESHOLD)
    return pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)


def wilson(errors: int, shots: int) -> list[float]:
    z = 1.959963984540054
    p = errors / shots
    den = 1 + z*z/shots
    center = (p + z*z/(2*shots))/den
    half = z*math.sqrt(p*(1-p)/shots + z*z/(4*shots*shots))/den
    return [center-half, center+half]


def compare(errors_a: int, n_a: int, errors_b: int, n_b: int) -> dict:
    pa, pb = errors_a/n_a, errors_b/n_b
    delta = pa-pb
    delta_se = math.sqrt(pa*(1-pa)/n_a + pb*(1-pb)/n_b)
    rr = pa/pb if pb else None
    rr_se = math.sqrt(1/errors_a + 1/errors_b) if errors_a and errors_b else None
    return {
        "ler_difference_three_idle_minus_five_active": delta,
        "ler_difference_normal_95_ci": [delta-1.95996398454*delta_se, delta+1.95996398454*delta_se],
        "rate_ratio_three_idle_over_five_active": rr,
        "rate_ratio_log_normal_95_ci": [math.exp(math.log(rr)-1.95996398454*rr_se),
                                         math.exp(math.log(rr)+1.95996398454*rr_se)] if rr and rr_se is not None else None,
    }


def main() -> None:
    start = time.perf_counter()
    rows = []
    total_preflight_samples = 0
    total_main_samples = 0
    preflight_elapsed = 0.0
    projected_total = 0.0
    idx = 0
    circuits = {}
    decoders = {}
    for basis, regime in CONDITIONS:
        for arm in ("three_rounds_plus_idle", "five_active_rounds"):
            circuit, extra = circuit_for(arm, basis, regime)
            expected_detectors = 24 if arm == "three_rounds_plus_idle" else 40
            if (circuit.num_qubits, circuit.num_detectors, circuit.num_observables) != (26, expected_detectors, 1):
                raise RuntimeError("unexpected circuit geometry")
            five_round_reference = phase2b_build_circuit(
                basis, regime, distance=3, rounds=5, gate_p=GATE_P,
                measurement_p=MEAS_P, bias_ratio=BIAS_RATIO)
            if arm == "five_active_rounds" and str(circuit) != str(five_round_reference):
                raise RuntimeError("five-round arm differs from the Phase 2B source builder")
            if terminal_data_targets(circuit) != terminal_data_targets(five_round_reference):
                raise RuntimeError("terminal data-readout targets changed between arms")
            if arm == "three_rounds_plus_idle" and extra["idle_pauli_targets"] != 18:
                raise RuntimeError("unexpected data-idle target count")
            decoder = make_matching(circuit)
            clean = stim.Circuit()
            for inst in circuit.flattened():
                if inst.name not in ("PAULI_CHANNEL_1", "PAULI_CHANNEL_2", "X_ERROR", "Z_ERROR"):
                    clean.append(inst.name, inst.targets_copy(), inst.gate_args_copy())
            nd, no = clean.compile_detector_sampler(seed=1).sample(20, separate_observables=True)
            if nd.any() or no.any():
                raise RuntimeError("noiseless deterministic circuit check failed")
            sample_start = time.perf_counter()
            det, obs = circuit.compile_detector_sampler(seed=PREFLIGHT_SEEDS[idx]).sample(
                shots=PREFLIGHT_SHOTS, separate_observables=True)
            sample_preflight = time.perf_counter() - sample_start
            t0 = time.perf_counter()
            pred = np.asarray(decoder.decode_batch(det, enable_correlations=True), dtype=bool).reshape(PREFLIGHT_SHOTS, -1)
            decode_preflight = time.perf_counter() - t0
            scalar = np.asarray([decoder.decode(row, enable_correlations=True) for row in det[:20]], dtype=bool).reshape(20, -1)
            if not np.array_equal(pred[:20], scalar) or pred.shape != obs.shape:
                raise RuntimeError("scalar/batch output shape or result mismatch")
            total_preflight_samples += PREFLIGHT_SHOTS
            projected = (decode_preflight + sample_preflight) * MAIN_SHOTS / PREFLIGHT_SHOTS
            projected_total += projected
            preflight_elapsed += time.perf_counter() - t0
            circuits[(basis, regime, arm)] = (circuit, extra)
            decoders[(basis, regime, arm)] = decoder
            rows.append({"memory_basis": basis, "regime": regime, "arm": arm,
                         "resources": resources(circuit), "extra": extra,
                         "preflight_seed": PREFLIGHT_SEEDS[idx], "preflight_shots": PREFLIGHT_SHOTS,
                         "preflight_failures": int(np.count_nonzero(np.any(pred != obs, axis=1))),
                         "preflight_decode_seconds": decode_preflight,
                         "preflight_sample_seconds": sample_preflight})
            idx += 1

    if projected_total > 300:
        result = {"status": "preflight_runtime_stop", "conditions": rows,
                  "preflight_samples": total_preflight_samples,
                  "projected_main_seconds": projected_total, "runtime_cap_seconds": 300,
                  "scope": "preflight only; no main samples generated"}
        (HERE / "equal_duration_rounds_results.json").write_text(json.dumps(result, indent=2)+"\n")
        print(json.dumps({"status": result["status"], "projection": projected_total}))
        return

    results = []
    idx = 0
    for basis, regime in CONDITIONS:
        rates = {}
        for arm in ("three_rounds_plus_idle", "five_active_rounds"):
            circuit, extra = circuits[(basis, regime, arm)]
            decoder = decoders[(basis, regime, arm)]
            det, obs = circuit.compile_detector_sampler(seed=MAIN_SEEDS[idx]).sample(
                shots=MAIN_SHOTS, separate_observables=True)
            pred = np.asarray(decoder.decode_batch(det, enable_correlations=True), dtype=bool).reshape(MAIN_SHOTS, -1)
            failed = np.any(pred != obs, axis=1)
            errors = int(failed.sum())
            rates[arm] = {"errors": errors, "ler": errors/MAIN_SHOTS,
                          "wilson_95": wilson(errors, MAIN_SHOTS),
                          "seed": MAIN_SEEDS[idx], "shots": MAIN_SHOTS}
            total_main_samples += MAIN_SHOTS
            idx += 1
        pair = compare(rates["three_rounds_plus_idle"]["errors"], MAIN_SHOTS,
                       rates["five_active_rounds"]["errors"], MAIN_SHOTS)
        results.append({"memory_basis": basis, "regime": regime,
                        "three_rounds_plus_idle": rates["three_rounds_plus_idle"],
                        "five_active_rounds": rates["five_active_rounds"], **pair})
    rr = [r["rate_ratio_three_idle_over_five_active"] for r in results]
    macro_rr = float(np.mean(rr))
    not_harmed = all(x <= 1.05 for x in rr)
    result = {
        "status": "equal_duration_rounds_development",
        "conditions": results,
        "equal_weight_macro_rate_ratio": macro_rr,
        "macro_relative_reduction": 1-macro_rr,
        "no_workload_harmed_by_more_than_5pct": not_harmed,
        "advancement_gate_passed": macro_rr <= .90 and not_harmed,
        "p_gate_and_measurement": GATE_P,
        "bias_ratio": BIAS_RATIO,
        "approximate_dem_threshold": DEM_THRESHOLD,
        "preflight_samples": total_preflight_samples,
        "main_samples": total_main_samples,
        "preflight_conditions": rows,
        "projected_main_seconds": projected_total,
        "elapsed_seconds": time.perf_counter()-start,
        "scope": "aligned d3 workloads; three active syndrome rounds plus two biased data-idle cycles versus five active rounds; development only",
    }
    (HERE / "equal_duration_rounds_results.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps({"status": result["status"], "macro_rr": macro_rr,
                      "advancement": result["advancement_gate_passed"],
                      "elapsed": result["elapsed_seconds"], "conditions": results}, indent=2))


if __name__ == "__main__":
    main()
