"""Fixed-distance circuit/resource screen across syndrome-round counts."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

import numpy as np
import pymatching
from scipy.stats import beta

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "outputs/phase2b_pauli_bias"))
sys.path.insert(0, str(HERE))
from noise_model import MEMORY_BASES, REGIMES, build_circuit as source_build  # noqa: E402
from code_distance_scaling import build_scaled_circuit  # noqa: E402

ROUNDS = (3, 5, 7, 9)
PROFILES = ("x_biased", "z_biased")
BASES = ("x", "z")
CONDITIONS = tuple((r, p, b) for r in ROUNDS for p in PROFILES for b in BASES)
PREFLIGHT_SEEDS = tuple(range(2026112201, 2026112217))
MAIN_SEEDS = tuple(range(2026112221, 2026112237))
N_PREFLIGHT = 100
N_MAIN = 200_000
MAX_PROJECTED_SECONDS = 300.0
DEM_THRESHOLD = 0.0018


def wilson(errors: int, shots: int) -> list[float]:
    z = 1.959963984540054
    p = errors / shots
    den = 1 + z*z/shots
    center = (p + z*z/(2*shots)) / den
    half = z*np.sqrt(p*(1-p)/shots + z*z/(4*shots*shots)) / den
    return [float(center-half), float(center+half)]


def rate_ratio(a: int, b: int) -> dict:
    if a == 0 or b == 0:
        return {"ratio": (float(a/b) if b else None), "conditional_exact_95_ci": None}
    q = beta.ppf([0.025, 0.975], a, b+1)
    return {"ratio": float(a/b),
            "conditional_exact_95_ci": [float(x/(1-x)) for x in q]}


def resources(circuit) -> dict:
    flat = circuit.flattened()
    return {
        "physical_qubits": int(circuit.num_qubits),
        "detectors": int(circuit.num_detectors),
        "observables": int(circuit.num_observables),
        "two_qubit_channel_pairs": sum(len(i.targets_copy())//2 for i in flat
                                        if i.name == "PAULI_CHANNEL_2"),
        "one_qubit_pauli_targets": sum(len(i.targets_copy()) for i in flat
                                        if i.name == "PAULI_CHANNEL_1"),
        "one_qubit_measurement_flip_targets": sum(len(i.targets_copy()) for i in flat
                                                  if i.name in {"X_ERROR", "Y_ERROR", "Z_ERROR"}),
    }


def build_model(rounds: int, profile: str, basis: str):
    circuit = build_scaled_circuit(basis, profile, distance=3, rounds=rounds)
    dem = circuit.detector_error_model(decompose_errors=True,
                                       approximate_disjoint_errors=DEM_THRESHOLD)
    matching = pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)
    return circuit, matching


def decode(matching, detectors):
    return np.asarray(matching.decode_batch(detectors, enable_correlations=True),
                      dtype=np.bool_).reshape(len(detectors), -1)


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--shots", type=int, default=N_MAIN)
    args = ap.parse_args()
    if args.shots <= 0:
        ap.error("--shots must be positive")
    start = time.perf_counter()
    source_round5_matches = {}
    for profile in PROFILES:
        for basis in BASES:
            scaled = build_scaled_circuit(basis, profile, distance=3, rounds=5)
            source = source_build(basis, profile, distance=3, rounds=5, bias_ratio=10)
            source_round5_matches[f"{profile}_{basis}"] = str(scaled) == str(source)
            if not source_round5_matches[f"{profile}_{basis}"]:
                raise RuntimeError(f"scaled/source round-5 circuit mismatch: {profile}/{basis}")
    rows = []
    resources_by_round: dict[int, list[dict]] = {r: [] for r in ROUNDS}
    seeds = PREFLIGHT_SEEDS if args.preflight else MAIN_SEEDS
    n = N_PREFLIGHT if args.preflight else args.shots

    for (rounds, profile, basis), seed in zip(CONDITIONS, seeds, strict=True):
        t = time.perf_counter()
        circuit, matching = build_model(rounds, profile, basis)
        model_seconds = time.perf_counter() - t
        res = resources(circuit)
        resources_by_round[rounds].append(res)
        t = time.perf_counter()
        detectors, observables = circuit.compile_detector_sampler(seed=seed).sample(
            shots=n, separate_observables=True)
        sample_seconds = time.perf_counter() - t
        t = time.perf_counter()
        predicted = decode(matching, detectors)
        decode_seconds = time.perf_counter() - t
        if predicted.shape != observables.shape:
            raise RuntimeError(f"logical prediction shape mismatch at {rounds}/{profile}/{basis}")
        scalar_n = min(n, 100)
        scalar = np.asarray([matching.decode(s, enable_correlations=True)
                             for s in detectors[:scalar_n]], dtype=np.bool_).reshape(scalar_n, -1)
        if not np.array_equal(scalar, predicted[:scalar_n]):
            raise RuntimeError(f"batch/scalar correlation decode mismatch at {rounds}/{profile}/{basis}")
        failures = int(np.count_nonzero(np.any(predicted != observables, axis=1)))
        row = {
            "rounds": rounds,
            "profile": profile,
            "memory_basis": basis,
            "seed": seed,
            "shots": n,
            "resources": res,
            "matcher_edges": int(matching.num_edges),
            "failures_preflight_only": failures if args.preflight else None,
            "failures": None if args.preflight else failures,
            "ler": None if args.preflight else failures/n,
            "wilson_95": None if args.preflight else wilson(failures, n),
            "model_build_seconds": model_seconds,
            "sampling_seconds": sample_seconds,
            "decode_batch_seconds": decode_seconds,
            "scalar_batch_checked_shots": scalar_n,
        }
        rows.append(row)

    matched_resources = {}
    for rounds, group in resources_by_round.items():
        signatures = {tuple(sorted(row.items())) for row in group}
        matched_resources[str(rounds)] = len(signatures) == 1
        if not matched_resources[str(rounds)]:
            raise RuntimeError(f"basis/profile resource mismatch within rounds={rounds}: {group}")

    if args.preflight:
        projected = sum(r["model_build_seconds"]
                        + N_MAIN * (r["sampling_seconds"] + r["decode_batch_seconds"]) / n
                        for r in rows)
        out = {
            "status": "preflight_passed" if projected <= MAX_PROJECTED_SECONDS else "preflight_runtime_stop",
            "distance": 3,
            "rounds": ROUNDS,
            "profiles": PROFILES,
            "memory_bases": BASES,
            "gate_and_measurement_p": 0.003,
            "bias_ratio": 10,
            "dem_approximation_threshold": DEM_THRESHOLD,
            "decoder": "per-circuit correlation-enabled PyMatching",
            "round5_scaled_builder_byte_identical_to_source": source_round5_matches,
            "shots_per_cell": n,
            "conditions": rows,
            "resources_matched_within_round_count": matched_resources,
            "projected_main_seconds": projected,
            "runtime_cap_seconds": MAX_PROJECTED_SECONDS,
            "stochastic_circuit_shots": len(rows)*n,
        }
        path = HERE / "round_count_frontier_preflight.json"
        path.write_text(json.dumps(out, indent=2) + "\n")
        print(f"Wrote {path}; projected main {projected:.1f}s")
        if projected > MAX_PROJECTED_SECONDS:
            raise RuntimeError("round-count screen exceeds the five-minute cap")
        return

    by_key = {(r["rounds"], r["profile"], r["memory_basis"]): r for r in rows}
    comparisons = []
    for row in rows:
        if row["rounds"] == 5:
            continue
        baseline = by_key[(5, row["profile"], row["memory_basis"])]
        comparisons.append({
            "rounds": row["rounds"],
            "reference_rounds": 5,
            "profile": row["profile"],
            "memory_basis": row["memory_basis"],
            "candidate_failures": row["failures"],
            "reference_failures": baseline["failures"],
            "candidate_ler": row["ler"],
            "reference_ler": baseline["ler"],
            "rate_ratio_vs_5_rounds": rate_ratio(row["failures"], baseline["failures"]),
            "two_qubit_pair_resource_ratio_vs_5_rounds": (
                row["resources"]["two_qubit_channel_pairs"]
                / baseline["resources"]["two_qubit_channel_pairs"]),
        })
    out = {
        "status": "development_round_count_frontier",
        "distance": 3,
        "gate_and_measurement_p": 0.003,
        "bias_ratio": 10,
        "rounds": ROUNDS,
        "profiles": PROFILES,
        "memory_bases": BASES,
        "shots_per_cell": n,
        "conditions": rows,
        "matched_resources_within_round_count": matched_resources,
        "comparisons_vs_standard_5_rounds": comparisons,
        "decoder": "per-circuit correlation-enabled PyMatching from approximate DEM .0018",
        "round5_scaled_builder_byte_identical_to_source": source_round5_matches,
        "elapsed_seconds": time.perf_counter()-start,
        "stochastic_circuit_shots": len(rows)*n,
        "scope": "known-profile fixed-distance code/circuit resource screen; not threshold, adaptation, hardware, or decoder-only result",
    }
    path = HERE / "round_count_frontier_results.json"
    path.write_text(json.dumps(out, indent=2) + "\n")
    print(f"Wrote {path}; {n} shots x {len(rows)} cells; elapsed={out['elapsed_seconds']:.1f}s")
    for c in comparisons:
        print(c)


if __name__ == "__main__":
    main()
