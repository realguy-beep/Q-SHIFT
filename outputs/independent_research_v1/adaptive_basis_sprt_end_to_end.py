"""Direct LER and circuit-shot utility evaluation of detector-only calibration policies."""
from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pymatching
from scipy.stats import beta

from adaptive_basis_sprt import PROFILES, sample_scores
from basis_alignment_distance7 import build

HERE = Path(__file__).resolve().parent
FROZEN = json.loads((HERE / "adaptive_basis_sprt_results.json").read_text())
FROZEN_REPLICATION = json.loads((HERE / "adaptive_basis_sprt_replication_results.json").read_text())
MEANS = FROZEN["training_score_means"]
VARS = FROZEN["training_score_variances"]
THRESHOLD = float(FROZEN["wald_threshold"])
WINDOWS = 2_500
BLOCK = 100
PRE_SHOTS = 5_000
PRE_SEEDS = (2026115601, 2026115602, 2026115603, 2026115604)
MAIN_SEEDS = (2026115611, 2026115612, 2026115613, 2026115614)
BOOTSTRAPS = 5_000
BOOT_SEED = 2026115691


def classifier_choices(scores: np.ndarray, profile: str) -> tuple[dict[str, np.ndarray], np.ndarray]:
    x = scores.reshape(WINDOWS, 500)
    x_mu, z_mu = float(MEANS["x_biased"]), float(MEANS["z_biased"])
    x_var, z_var = float(VARS["x_biased"]), float(VARS["z_biased"])

    def log_pdf(value: np.ndarray, mean: float, var: float) -> np.ndarray:
        return -0.5 * (np.log(2 * np.pi * var) + np.square(value - mean) / var)

    llr = log_pdf(x, z_mu, z_var) - log_pdf(x, x_mu, x_var)
    cumulative = np.cumsum(llr, axis=1)
    crossed = np.abs(cumulative) >= THRESHOLD
    crossed_any = crossed.any(axis=1)
    first = np.argmax(crossed, axis=1)
    consumed = np.where(crossed_any, first + 1, 500)
    stopped = np.where(crossed_any, cumulative[np.arange(WINDOWS), np.maximum(consumed - 1, 0)], cumulative[:, -1])
    choices = {"sprt": stopped < 0}
    for n in (25, 100, 500):
        choices[f"lda_{n}"] = x[:, :n].mean(axis=1) < 0
        choices[f"gaussian_llr_{n}"] = cumulative[:, n - 1] < 0
    return choices, consumed


def source_checks() -> tuple[dict, dict]:
    from noise_model import build_circuit as source_build

    matches, resources = {}, {}
    for profile in PROFILES:
        for basis in ("x", "z"):
            circuit = build(basis, profile, 3, 5, bias_ratio=10.0)
            reference = source_build(basis, profile, distance=3, rounds=5, bias_ratio=10.0)
            matches[f"{profile}_{basis}"] = str(circuit) == str(reference)
            instructions = list(circuit.flattened())
            resources[f"{profile}_{basis}"] = {
                "qubits": int(circuit.num_qubits),
                "detectors": int(circuit.num_detectors),
                "observables": int(circuit.num_observables),
                "ticks": int(circuit.num_ticks),
                "operations": dict(Counter(instruction.name for instruction in instructions)),
                "two_qubit_interactions": sum(
                    len(instruction.targets_copy()) // 2
                    for instruction in instructions
                    if instruction.name in ("CX", "CZ", "XCX", "CY")
                ),
                "two_qubit_noise_targets": sum(
                    len(instruction.targets_copy()) // 2
                    for instruction in instructions
                    if instruction.name == "PAULI_CHANNEL_2"
                ),
                "one_qubit_noise_targets": sum(
                    len(instruction.targets_copy())
                    for instruction in instructions
                    if instruction.name in ("PAULI_CHANNEL_1", "X_ERROR", "Y_ERROR", "Z_ERROR")
                ),
            }
            clean = circuit.without_noise()
            d, o = clean.compile_detector_sampler(seed=8800).sample(shots=100, separate_observables=True)
            if d.any() or o.any():
                raise RuntimeError(f"noiseless circuit is not deterministic for {profile}/{basis}")
    if not all(matches.values()):
        raise RuntimeError(f"circuit builder mismatch: {matches}")
    for profile in PROFILES:
        x, z = resources[f"{profile}_x"], resources[f"{profile}_z"]
        common = ("qubits", "detectors", "observables", "ticks", "two_qubit_interactions", "two_qubit_noise_targets")
        if any(x[field] != z[field] for field in common):
            raise RuntimeError(f"X/Z common resources differ within profile {profile}: {x} vs {z}")
    return matches, resources


def logical_failures(profile: str, basis: str, shots: int, seed: int) -> tuple[np.ndarray, dict, float]:
    circuit = build(basis, profile, 3, 5, bias_ratio=10.0)
    dem = circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=0.0018)
    matching = pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)
    started = time.perf_counter()
    det, obs = circuit.compile_detector_sampler(seed=seed).sample(shots=shots, separate_observables=True)
    sample_seconds = time.perf_counter() - started
    started = time.perf_counter()
    pred = np.asarray(matching.decode_batch(det), dtype=np.uint8).reshape(shots, -1)
    decode_seconds = time.perf_counter() - started
    if pred.shape != obs.shape:
        raise RuntimeError(f"prediction shape mismatch for {profile}/{basis}: {pred.shape} vs {obs.shape}")
    check = min(100, shots)
    scalar = np.asarray([matching.decode(det[i]) for i in range(check)], dtype=np.uint8).reshape(check, -1)
    if not np.array_equal(scalar, pred[:check]):
        raise RuntimeError(f"scalar/batch mismatch for {profile}/{basis}")
    fail = np.any(pred != obs, axis=1)
    if shots % BLOCK:
        raise RuntimeError("logical shot count must be divisible into fixed blocks")
    return fail.reshape(-1, BLOCK).sum(axis=1).astype(np.int64), {
        "code": "correlation-enabled PyMatching from approximate_disjoint_errors=0.0018 DEM",
        "seed": seed,
        "shots": shots,
        "failures": int(fail.sum()),
        "sampling_seconds": sample_seconds,
        "decode_seconds": decode_seconds,
        "scalar_batch_checks": check,
    }, sample_seconds + decode_seconds


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    started = time.perf_counter()
    builder_matches, resources = source_checks()
    seeds = PRE_SEEDS if args.preflight else MAIN_SEEDS
    logical_n = PRE_SHOTS if args.preflight else WINDOWS * BLOCK

    calibration_choices, consumed_by_profile = {}, {}
    for profile, seed in zip(PROFILES, FROZEN_REPLICATION["sample_rows"], strict=True):
        # Regenerate the saved-seed 2,500-window stream exactly; it is reused evidence.
        scores, _, _ = sample_scores(profile, WINDOWS * 500, seed["seed"])
        calibration_choices[profile], consumed_by_profile[profile] = classifier_choices(scores, profile)

    streams, stream_meta = {}, []
    new_samples = 0
    total_runtime = 0.0
    for i, profile in enumerate(PROFILES):
        for j, basis in enumerate(("x", "z")):
            seed = seeds[2 * i + j]
            block_failures, meta, runtime = logical_failures(profile, basis, logical_n, seed)
            streams[(profile, basis)] = block_failures
            stream_meta.append({"profile": profile, "basis": basis, **meta})
            total_runtime += runtime
            new_samples += logical_n

    if args.preflight:
        projected = time.perf_counter() + 0.0
        projected = total_runtime * (WINDOWS * BLOCK / PRE_SHOTS)
        elapsed = time.perf_counter() - started
        output = {
            "status": "sprt_end_to_end_preflight",
            "source_builder_byte_identical": builder_matches,
            "resources": resources,
            "logical_rows": stream_meta,
            "elapsed_seconds": elapsed,
            "projected_main_seconds": projected,
            "runtime_cap_seconds": 300,
            "runtime_gate_passed": projected <= 300,
            "new_source_equivalent_samples": new_samples,
            "calibration_streams_reused": True,
        }
        path = HERE / "adaptive_basis_sprt_end_to_end_preflight.json"
        path.write_text(json.dumps(output, indent=2) + "\n")
        print(json.dumps({"status": output["status"], "projected_main_seconds": projected, "output": str(path)}, indent=2))
        if not output["runtime_gate_passed"]:
            raise SystemExit(1)
        return

    failures = {}
    selectors = ["sprt"] + [f"lda_{n}" for n in (25, 100, 500)] + [f"gaussian_llr_{n}" for n in (25, 100, 500)] + ["static_x", "static_z", "oracle"]
    for name in selectors:
        per_profile = {}
        for profile in PROFILES:
            if name in ("static_x", "static_z", "oracle"):
                choose_x = name == "static_x" or (name == "oracle" and profile == "x_biased")
                decisions = np.full(WINDOWS, choose_x, dtype=bool)
                if name == "static_z":
                    decisions[:] = False
            else:
                decisions = calibration_choices[profile][name]
            x_fail = streams[(profile, "x")]
            z_fail = streams[(profile, "z")]
            per_profile[profile] = np.where(decisions, x_fail, z_fail)
        failures[name] = per_profile

    nlogical = len(PROFILES) * WINDOWS * BLOCK
    rng = np.random.default_rng(BOOT_SEED)
    boot_indices = {profile: rng.integers(0, WINDOWS, size=(BOOTSTRAPS, WINDOWS)) for profile in PROFILES}
    summary = {}
    static_z_ler = int(sum(failures["static_z"][p].sum() for p in PROFILES)) / nlogical
    for name, per_profile in failures.items():
        error_count = int(sum(per_profile[p].sum() for p in PROFILES))
        total_cal = int(sum(consumed_by_profile[p].sum() for p in PROFILES)) if name == "sprt" else 0
        if name.startswith("lda_") or name.startswith("gaussian_llr_"):
            budget = int(name.rsplit("_", 1)[1])
            total_cal = budget * WINDOWS * len(PROFILES)
        boot_fail = np.zeros(BOOTSTRAPS, dtype=np.int64)
        for profile in PROFILES:
            boot_fail += per_profile[profile][boot_indices[profile]].sum(axis=1)
        boot_ler = boot_fail / nlogical
        boot_static_z = np.zeros(BOOTSTRAPS, dtype=np.int64)
        for profile in PROFILES:
            boot_static_z += failures["static_z"][profile][boot_indices[profile]].sum(axis=1)
        delta = boot_ler - boot_static_z / nlogical
        summary[name] = {
            "logical_failures": error_count,
            "logical_attempts": nlogical,
            "ler": error_count / nlogical,
            "ler_exact_95_ci": [
                0.0 if error_count == 0 else float(beta.ppf(0.025, error_count, nlogical - error_count + 1)),
                1.0 if error_count == nlogical else float(beta.ppf(0.975, error_count + 1, nlogical - error_count)),
            ],
            "calibration_shots": total_cal,
            "correct_outputs_per_logical_plus_calibration_circuit_shot": (nlogical - error_count) / (nlogical + total_cal),
            "paired_cluster_bootstrap_ler_delta_vs_static_z_95_ci": [float(np.quantile(delta, 0.025)), float(np.quantile(delta, 0.975))],
            "profile_failures": {p: int(per_profile[p].sum()) for p in PROFILES},
        }
    out = {
        "status": "sprt_end_to_end_development_result",
        "distance": 3,
        "rounds": 5,
        "bias_ratio": 10,
        "profiles_equal_weight": True,
        "logical_attempts_per_profile": WINDOWS * BLOCK,
        "calibration_streams_reused_from_sequential_validation": True,
        "logical_samples": stream_meta,
        "source_builder_byte_identical": builder_matches,
        "resources": resources,
        "summary": summary,
        "bootstrap_replicates": BOOTSTRAPS,
        "bootstrap_seed": BOOT_SEED,
        "elapsed_seconds": time.perf_counter() - started,
        "new_source_equivalent_samples": new_samples,
        "scope": "development-only separate X/Z logical-memory tasks under two fixed simulator profiles; not arbitrary-state or change-point evaluation",
    }
    path = HERE / "adaptive_basis_sprt_end_to_end_results.json"
    path.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"status": out["status"], "ler": {k: v["ler"] for k, v in summary.items()}, "output": str(path)}, indent=2))


if __name__ == "__main__":
    main()
