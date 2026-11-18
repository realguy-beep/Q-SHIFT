"""Oracle-known round-wise gate-rate heterogeneity screen versus pooled matching."""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pymatching
import stim
from scipy.stats import binomtest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "outputs" / "phase2b_pauli_bias"))
from noise_model import build_circuit  # noqa: E402

BASE_P = 0.003
FACTORS = {
    "phase_a": (0.25, 1.75, 1.0, 0.25, 1.75),
    "phase_b": (1.75, 0.25, 1.0, 1.75, 0.25),
}
PREFLIGHT_SEEDS = (2026113611, 2026113612)
MAIN_SEEDS = (2026113621, 2026113622)
PREFLIGHT_SHOTS = 100
MAIN_SHOTS = 200_000
DEM_THRESHOLD = 0.01


def profile_circuit(profile: str) -> tuple[stim.Circuit, dict]:
    factors = FACTORS[profile]
    source = build_circuit("z", "x_biased", distance=3, rounds=5,
                           gate_p=BASE_P, measurement_p=BASE_P, bias_ratio=10.0).flattened()
    out = stim.Circuit()
    round_index = 0
    pair_sites = 0
    rates = []
    for inst in source:
        if inst.name == "PAULI_CHANNEL_2":
            args = np.asarray(inst.gate_args_copy(), dtype=np.float64) * factors[round_index]
            if float(args.sum()) >= 1:
                raise RuntimeError("invalid channel probability")
            out.append(inst.name, inst.targets_copy(), args.tolist())
            rates.append(float(args.sum()))
            pair_sites += len(inst.targets_copy()) // 2
        else:
            out.append(inst.name, inst.targets_copy(), inst.gate_args_copy())
            if inst.name == "MR":
                round_index += 1
    if round_index != 5 or len(factors) != 5 or pair_sites != 120:
        raise RuntimeError(f"unexpected round/pair layout: {round_index}/{pair_sites}")
    meta = {
        "profile": profile,
        "round_factors": list(factors),
        "round_count": round_index,
        "two_qubit_pair_sites": pair_sites,
        "mean_two_qubit_instruction_rate": float(np.mean(rates)),
        "round_instruction_rates": [BASE_P * x for x in factors],
        "factor_mean": float(np.mean(factors)),
    }
    return out, meta


def clean(circuit: stim.Circuit) -> stim.Circuit:
    out = stim.Circuit()
    for inst in circuit.flattened():
        if inst.name in ("PAULI_CHANNEL_1", "PAULI_CHANNEL_2", "X_ERROR", "Z_ERROR"):
            continue
        out.append(inst.name, inst.targets_copy(), inst.gate_args_copy())
    return out


def make_matching(circuit: stim.Circuit) -> pymatching.Matching:
    dem = circuit.detector_error_model(
        decompose_errors=True, approximate_disjoint_errors=DEM_THRESHOLD)
    return pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)


def paired_summary(candidate: np.ndarray, pooled: np.ndarray) -> dict:
    delta = candidate.astype(np.float64) - pooled.astype(np.float64)
    mean = float(delta.mean())
    se = float(delta.std(ddof=1) / math.sqrt(len(delta)))
    candidate_only = int(np.count_nonzero(candidate & ~pooled))
    pooled_only = int(np.count_nonzero(pooled & ~candidate))
    discord = candidate_only + pooled_only
    return {
        "profile_specific_ler": float(candidate.mean()),
        "pooled_ler": float(pooled.mean()),
        "paired_delta_profile_specific_minus_pooled": mean,
        "paired_normal_95_ci": [mean - 1.95996398454 * se, mean + 1.95996398454 * se],
        "profile_specific_only_failures": candidate_only,
        "pooled_only_failures": pooled_only,
        "discordant": discord,
        "mcnemar_exact_two_sided": float(binomtest(candidate_only, discord, .5).pvalue) if discord else 1.0,
    }


def run() -> None:
    start = time.perf_counter()
    pooled = build_circuit("z", "x_biased", distance=3, rounds=5,
                           gate_p=BASE_P, measurement_p=BASE_P, bias_ratio=10.0)
    pooled_decoder = make_matching(pooled)
    metadata = {}
    local_circuits = {}
    local_decoders = {}
    preflight_rows = []
    for profile, seed in zip(FACTORS, PREFLIGHT_SEEDS, strict=True):
        circuit, meta = profile_circuit(profile)
        if (circuit.num_qubits, circuit.num_detectors, circuit.num_observables) != (26, 40, 1):
            raise RuntimeError("profile changed circuit geometry")
        if meta["factor_mean"] != 1.0 or abs(meta["mean_two_qubit_instruction_rate"] - BASE_P) > 1e-12:
            raise RuntimeError("profile does not preserve the mean gate rate")
        noiseless_det, noiseless_obs = clean(circuit).compile_detector_sampler(seed=1).sample(
            20, separate_observables=True)
        if noiseless_det.any() or noiseless_obs.any():
            raise RuntimeError("noiseless deterministic circuit check failed")
        local_decoder = make_matching(circuit)
        det, obs = circuit.compile_detector_sampler(seed=seed).sample(
            shots=PREFLIGHT_SHOTS, separate_observables=True)
        batch_local = np.asarray(local_decoder.decode_batch(det, enable_correlations=True), dtype=bool).reshape(PREFLIGHT_SHOTS, -1)
        batch_pool = np.asarray(pooled_decoder.decode_batch(det, enable_correlations=True), dtype=bool).reshape(PREFLIGHT_SHOTS, -1)
        for decoder, batch in ((local_decoder, batch_local), (pooled_decoder, batch_pool)):
            scalar = np.asarray([decoder.decode(row, enable_correlations=True) for row in det[:20]], dtype=bool).reshape(20, -1)
            if not np.array_equal(scalar, batch[:20]):
                raise RuntimeError("scalar/batch mismatch")
        metadata[profile] = meta
        local_circuits[profile] = circuit
        local_decoders[profile] = local_decoder
        preflight_rows.append({"profile": profile, "seed": seed, "shots": PREFLIGHT_SHOTS})

    if metadata["phase_a"]["round_factors"] != list(reversed(metadata["phase_b"]["round_factors"])):
        raise RuntimeError("profiles are not temporal reversals")
    t0 = time.perf_counter()
    for profile in FACTORS:
        circuit = local_circuits[profile]
        decoder = local_decoders[profile]
        det, _ = circuit.compile_detector_sampler(seed=1).sample(
            shots=PREFLIGHT_SHOTS, separate_observables=True)
        decoder.decode_batch(det, enable_correlations=True)
        pooled_decoder.decode_batch(det, enable_correlations=True)
    preflight_seconds = time.perf_counter() - t0
    projected = preflight_seconds * MAIN_SHOTS / PREFLIGHT_SHOTS
    if projected > 300:
        result = {"status": "preflight_runtime_stop", "profiles": metadata,
                  "preflight": preflight_rows, "projected_main_seconds": projected,
                  "runtime_cap_seconds": 300, "stochastic_samples_generated": 400,
                  "scope": "development preflight only; no main comparison"}
        (HERE / "temporal_rate_hotspot_preflight.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"status": result["status"], "projected": projected}))
        return

    rows = []
    for profile, seed in zip(FACTORS, MAIN_SEEDS, strict=True):
        circuit = local_circuits[profile]
        det, obs = circuit.compile_detector_sampler(seed=seed).sample(
            shots=MAIN_SHOTS, separate_observables=True)
        local_decoder = local_decoders[profile]
        t0 = time.perf_counter()
        local_pred = np.asarray(local_decoder.decode_batch(det, enable_correlations=True), dtype=bool).reshape(MAIN_SHOTS, -1)
        local_seconds = time.perf_counter() - t0
        t0 = time.perf_counter()
        pooled_pred = np.asarray(pooled_decoder.decode_batch(det, enable_correlations=True), dtype=bool).reshape(MAIN_SHOTS, -1)
        pooled_seconds = time.perf_counter() - t0
        local_fail = np.any(local_pred != obs, axis=1)
        pooled_fail = np.any(pooled_pred != obs, axis=1)
        summary = paired_summary(local_fail, pooled_fail)
        summary.update({"profile": profile, "seed": seed, "shots": MAIN_SHOTS,
                        "local_decode_seconds": local_seconds,
                        "pooled_decode_seconds": pooled_seconds,
                        "local_to_pooled_decode_time_ratio": local_seconds / pooled_seconds})
        rows.append(summary)
    reductions = [1 - row["profile_specific_ler"] / row["pooled_ler"] if row["pooled_ler"] else 0.0 for row in rows]
    macro_reduction = float(np.mean(reductions))
    harmed = [1 - reduction for reduction in reductions]
    time_ok = all(row["local_to_pooled_decode_time_ratio"] < 2 for row in rows)
    result = {
        "status": "temporal_rate_hotspot_development",
        "profiles": metadata,
        "profile_results": rows,
        "per_profile_relative_reduction": reductions,
        "equal_weight_macro_relative_reduction": macro_reduction,
        "no_profile_harmed_by_more_than_5pct": all(x <= .05 for x in harmed),
        "decode_time_gate_passed": time_ok,
        "advancement_gate_passed": macro_reduction >= .10 and all(x <= .05 for x in harmed) and time_ok,
        "shots_per_profile": MAIN_SHOTS,
        "stochastic_qshift_shots": 2 * MAIN_SHOTS,
        "approximate_dem_threshold": DEM_THRESHOLD,
        "projected_preflight_seconds": projected,
        "elapsed_seconds": time.perf_counter() - start,
        "scope": "known round-wise two-qubit rate map versus same-mean pooled model; simulator development only; not online adaptation",
    }
    (HERE / "temporal_rate_hotspot_results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "macro_reduction": macro_reduction,
                      "gate": result["advancement_gate_passed"], "elapsed": result["elapsed_seconds"],
                      "profiles": [{"name": r["profile"], "local": r["profile_specific_ler"],
                                    "pooled": r["pooled_ler"], "delta": r["paired_delta_profile_specific_minus_pooled"]}
                                   for r in rows]}, indent=2))


if __name__ == "__main__":
    run()
