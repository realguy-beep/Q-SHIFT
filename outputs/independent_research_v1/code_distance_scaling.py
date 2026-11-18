"""Distance-5 bias-aligned memory-basis scaling check."""
from __future__ import annotations

import argparse
import json
import re
import resource
import sys
import time
from pathlib import Path

import numpy as np
import pymatching
import stim

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PHASE2B = REPO / "outputs" / "phase2b_pauli_bias"
sys.path.insert(0, str(PHASE2B))
from noise_model import (  # noqa: E402
    DEFAULT_BIAS_RATIO,
    DEFAULT_GATE_P,
    DEFAULT_MEAS_P,
    MEMORY_BASES,
    REGIMES,
    build_circuit as source_build_circuit,
    one_qubit_probabilities,
    two_qubit_probabilities,
)

DISTANCE = 5
ROUNDS = 9
REGIMES_TO_TEST = ("x_biased", "z_biased")
CONDITIONS = tuple((basis, regime) for regime in REGIMES_TO_TEST for basis in MEMORY_BASES)
PREFLIGHT_SEEDS = (2026111101, 2026111102, 2026111103, 2026111104)
MAIN_SEEDS = (2026111111, 2026111112, 2026111113, 2026111114)


def build_scaled_circuit(memory_basis: str, regime: str, distance: int, rounds: int) -> stim.Circuit:
    p1 = one_qubit_probabilities(regime, DEFAULT_GATE_P, DEFAULT_BIAS_RATIO)
    p2 = two_qubit_probabilities(regime, DEFAULT_GATE_P, DEFAULT_BIAS_RATIO)
    generated = stim.Circuit.generated(
        f"surface_code:rotated_memory_{memory_basis}",
        distance=distance,
        rounds=rounds,
        after_clifford_depolarization=DEFAULT_GATE_P,
        before_measure_flip_probability=DEFAULT_MEAS_P,
    )
    body = str(generated)
    p1_text = "PAULI_CHANNEL_1("+",".join(format(v, ".17g") for v in p1)+")"
    p2_text = "PAULI_CHANNEL_2("+",".join(format(v, ".17g") for v in p2)+")"
    body, n1 = re.subn(r"DEPOLARIZE1\([^)]*\)", p1_text, body)
    body, n2 = re.subn(r"DEPOLARIZE2\([^)]*\)", p2_text, body)
    if not n1 or not n2:
        raise RuntimeError(f"failed to substitute generated depolarizing channels: {n1}, {n2}")
    return stim.Circuit(body)


def wilson(errors: int, shots: int) -> list[float]:
    z = 1.959963984540054
    rate = errors/shots
    denominator = 1+z*z/shots
    center = (rate+z*z/(2*shots))/denominator
    half = z*np.sqrt(rate*(1-rate)/shots+z*z/(4*shots*shots))/denominator
    return [float(center-half), float(center+half)]


def run_condition(memory_basis: str, regime: str, shots: int, seed: int) -> dict:
    circuit = build_scaled_circuit(memory_basis, regime, DISTANCE, ROUNDS)
    dem = circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=0.0018)
    matching = pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)
    detectors, observables = circuit.compile_detector_sampler(seed=seed).sample(
        shots=shots, separate_observables=True)
    failures = 0
    decode_seconds = 0.0
    for i, syndrome in enumerate(detectors):
        start = time.perf_counter()
        predicted = np.asarray(matching.decode(syndrome), dtype=np.bool_).reshape(-1)
        decode_seconds += time.perf_counter()-start
        failures += not np.array_equal(predicted, observables[i])
    return {
        "memory_basis": memory_basis,
        "regime": regime,
        "seed": seed,
        "shots": shots,
        "physical_qubits": int(circuit.num_qubits),
        "detectors": int(circuit.num_detectors),
        "observables": int(circuit.num_observables),
        "two_qubit_channel_pairs": sum(
            len(inst.targets_copy())//2 for inst in circuit.flattened() if inst.name == "PAULI_CHANNEL_2"),
        "failures": int(failures),
        "ler": failures/shots,
        "wilson_95": wilson(failures, shots),
        "decode_seconds": decode_seconds,
        "seconds_per_decode": decode_seconds/shots,
        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--shots", type=int, default=50000)
    args = parser.parse_args()
    if args.shots <= 0:
        parser.error("--shots must be positive")

    # Verify this independent scalable builder reproduces both existing d=3 circuits.
    d3_reproduced = {}
    for basis in MEMORY_BASES:
        for regime in REGIMES:
            rebuilt = build_scaled_circuit(basis, regime, 3, 5)
            original = source_build_circuit(basis, regime, distance=3, rounds=5)
            d3_reproduced[f"{basis}_{regime}"] = str(rebuilt) == str(original)
            if not d3_reproduced[f"{basis}_{regime}"]:
                raise RuntimeError(f"distance-3 builder mismatch for {basis}/{regime}")

    preflight = args.preflight
    shots = 100 if preflight else args.shots
    seeds = PREFLIGHT_SEEDS if preflight else MAIN_SEEDS
    start = time.perf_counter()
    rows = [run_condition(b, r, shots, seed)
            for (b, r), seed in zip(CONDITIONS, seeds, strict=True)]
    elapsed = time.perf_counter()-start
    by_regime = {}
    for regime in REGIMES_TO_TEST:
        by_regime[regime] = {
            row["memory_basis"]: row["ler"] for row in rows if row["regime"] == regime
        }
    resource_match = all(
        next(row for row in rows if row["memory_basis"] == "x" and row["regime"] == regime)[k] ==
        next(row for row in rows if row["memory_basis"] == "z" and row["regime"] == regime)[k]
        for regime in REGIMES_TO_TEST for k in ("physical_qubits", "detectors", "observables", "two_qubit_channel_pairs")
    )
    output = {
        "status": "preflight" if preflight else "distance_5_development_screen",
        "stim_version": stim.__version__,
        "pymatching_version": pymatching.__version__,
        "distance": DISTANCE,
        "rounds": ROUNDS,
        "gate_error_probability": DEFAULT_GATE_P,
        "measurement_error_probability": DEFAULT_MEAS_P,
        "bias_ratio": DEFAULT_BIAS_RATIO,
        "d3_builder_byte_identical_to_source": d3_reproduced,
        "matched_resources_at_d5": resource_match,
        "shots_per_condition": shots,
        "conditions": rows,
        "lera_by_regime_and_basis": by_regime,
        "elapsed_seconds": elapsed,
        "stochastic_circuit_shots": shots*len(rows),
        "scope": "distance-5 scaling check only; not a threshold estimate",
    }
    target = HERE/("code_distance_preflight.json" if preflight else "code_distance_results.json")
    target.write_text(json.dumps(output, indent=2)+"\n", encoding="utf-8")
    print(f"Wrote {target}; elapsed={elapsed:.3f}s; resources_match={resource_match}")
    for row in rows:
        print(row["memory_basis"], row["regime"],
              f"LER={row['ler']:.6g}", f"errors={row['failures']}/{shots}",
              f"decode_s={row['decode_seconds']:.3f}")
    if preflight and elapsed*(50000/100)>300:
        print("Preflight projection exceeds five-minute cap; stop before main screen")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
