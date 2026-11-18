"""Paired development screen of BP+LSD against PyMatching on Phase 2B circuits."""
from __future__ import annotations

import argparse
import json
import resource
import sys
import time
from pathlib import Path

import numpy as np
import pymatching
import stim
from ldpc import BpLsdDecoder
from scipy.stats import binomtest, t

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PHASE2B = REPO / "outputs" / "phase2b_pauli_bias"
sys.path.insert(0, str(PHASE2B))
from noise_model import MEMORY_BASES, REGIMES, build_circuit  # noqa: E402

THRESHOLD = 0.0018
LSD_METHODS = ("LSD_0", "LSD_E", "LSD_CS")
PREFLIGHT_SEEDS = (202611201, 202611202, 202611203, 202611204, 202611205, 202611206)
MAIN_SEEDS = (202611191, 202611192, 202611193, 202611194, 202611195, 202611196)
CONDITIONS = tuple((basis, regime) for basis in MEMORY_BASES for regime in REGIMES)


def model_matrices(dem: stim.DetectorErrorModel) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return H, logical map L, and one probability per flattened DEM instruction."""
    flat = dem.flattened()
    n_det, n_obs = flat.num_detectors, flat.num_observables
    h_cols: list[np.ndarray] = []
    l_cols: list[np.ndarray] = []
    probabilities: list[float] = []
    for instruction in flat:
        if instruction.type != "error":
            continue
        h = np.zeros(n_det, dtype=np.uint8)
        logical = np.zeros(n_obs, dtype=np.uint8)
        for target in instruction.targets_copy():
            if target.is_relative_detector_id():
                h[target.val] ^= 1
            elif target.is_logical_observable_id():
                logical[target.val] ^= 1
        h_cols.append(h)
        l_cols.append(logical)
        probabilities.append(float(instruction.args_copy()[0]))
    if not probabilities:
        raise ValueError("DEM has no flattened error instructions")
    return (np.stack(h_cols, axis=1), np.stack(l_cols, axis=1),
            np.asarray(probabilities, dtype=np.float64))


def make_decoders(circuit: stim.Circuit) -> tuple[pymatching.Matching, dict[str, BpLsdDecoder], np.ndarray, np.ndarray]:
    dem = circuit.detector_error_model(
        decompose_errors=True, approximate_disjoint_errors=THRESHOLD)
    h, logical_map, probabilities = model_matrices(dem)
    matching = pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)
    decoders = {
        method: BpLsdDecoder(
            pcm=h,
            error_channel=probabilities.tolist(),
            max_iter=200,
            bp_method="minimum_sum",
            ms_scaling_factor=0.9,
            lsd_order=0,
            lsd_method=method,
            bits_per_step=1,
        )
        for method in LSD_METHODS
    }
    # Ensure each method maps a fixed syndrome to a stable fault vector of the expected width.
    probe = np.zeros(h.shape[0], dtype=np.uint8)
    for method, decoder in decoders.items():
        first = np.asarray(decoder.decode(probe), dtype=np.uint8).reshape(-1)
        second = np.asarray(decoder.decode(probe), dtype=np.uint8).reshape(-1)
        if first.shape != (h.shape[1],) or not np.array_equal(first, second):
            raise RuntimeError(f"{method} failed output-shape/determinism preflight")
    return matching, decoders, h, logical_map


def wilson(errors: int, shots: int) -> list[float]:
    z = 1.959963984540054
    rate = errors / shots
    denom = 1 + z*z/shots
    center = (rate + z*z/(2*shots))/denom
    half = z*np.sqrt(rate*(1-rate)/shots + z*z/(4*shots*shots))/denom
    return [float(center-half), float(center+half)]


def run_condition(basis: str, regime: str, shots: int, seed: int) -> dict:
    circuit = build_circuit(basis, regime)
    matching, decoders, h, logical_map = make_decoders(circuit)
    detectors, observables = circuit.compile_detector_sampler(seed=seed).sample(
        shots=shots, separate_observables=True)
    failures = {"pymatching_corr": 0, **{m: 0 for m in LSD_METHODS}}
    invalid_syndromes = {m: 0 for m in LSD_METHODS}
    discordant = {m: [0, 0] for m in LSD_METHODS}  # baseline-only, LSD-only
    paired_delta = {m: np.empty(shots, dtype=np.int8) for m in LSD_METHODS}
    decode_seconds = {"pymatching_corr": 0.0, **{m: 0.0 for m in LSD_METHODS}}

    for i, syndrome in enumerate(detectors):
        started = time.perf_counter()
        baseline_obs = np.asarray(matching.decode(syndrome), dtype=np.uint8).reshape(-1)
        decode_seconds["pymatching_corr"] += time.perf_counter() - started
        baseline_failed = not np.array_equal(baseline_obs, observables[i])
        failures["pymatching_corr"] += baseline_failed
        for method, decoder in decoders.items():
            started = time.perf_counter()
            fault_estimate = np.asarray(decoder.decode(syndrome), dtype=np.uint8).reshape(-1)
            decode_seconds[method] += time.perf_counter() - started
            if fault_estimate.shape != (logical_map.shape[1],):
                raise RuntimeError(f"{method} returned wrong fault-vector width")
            syndrome_reproduced = np.array_equal((h @ fault_estimate) & 1, syndrome)
            invalid_syndromes[method] += not syndrome_reproduced
            predicted_obs = (logical_map @ fault_estimate) & 1
            failed = (not syndrome_reproduced) or not np.array_equal(predicted_obs, observables[i])
            failures[method] += failed
            discordant[method][0] += baseline_failed and not failed
            discordant[method][1] += failed and not baseline_failed
            paired_delta[method][i] = int(failed) - int(baseline_failed)

    comparisons = {}
    for method in LSD_METHODS:
        delta = float(paired_delta[method].mean())
        se = float(paired_delta[method].std(ddof=1) / np.sqrt(shots)) if shots > 1 else 0.0
        crit = float(t.ppf(0.975, shots - 1)) if shots > 1 else 0.0
        a, b = discordant[method]
        comparisons[method] = {
            "paired_ler_delta_vs_pymatching": delta,
            "paired_normal_95": [delta-crit*se, delta+crit*se],
            "baseline_only_failures": int(a),
            "lsd_only_failures": int(b),
            "mcnemar_two_sided_p": float(binomtest(a, a+b, 0.5).pvalue) if a+b else 1.0,
        }
    return {
        "memory_basis": basis,
        "regime": regime,
        "seed": seed,
        "shots": shots,
        "detectors": int(detectors.shape[1]),
        "observables": int(observables.shape[1]),
        "dem_fault_variables": int(logical_map.shape[1]),
        "approximate_dem_threshold": THRESHOLD,
        "failures": failures,
        "invalid_syndrome_estimates": invalid_syndromes,
        "ler": {name: failures[name]/shots for name in failures},
        "wilson_95": {name: wilson(failures[name], shots) for name in failures},
        "comparisons": comparisons,
        "decode_seconds": decode_seconds,
        "seconds_per_decode": {name: decode_seconds[name]/shots for name in decode_seconds},
        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--shots", type=int, default=5000)
    args = parser.parse_args()
    if args.shots <= 0:
        parser.error("--shots must be positive")
    shots = 100 if args.preflight else args.shots
    seeds = PREFLIGHT_SEEDS if args.preflight else MAIN_SEEDS
    start = time.perf_counter()
    results = [run_condition(b, r, shots, seed)
               for (b, r), seed in zip(CONDITIONS, seeds, strict=True)]
    elapsed = time.perf_counter() - start
    output = {
        "status": "preflight" if args.preflight else "development_screen",
        "ldpc_version": "2.4.1",
        "stim_version": stim.__version__,
        "pymatching_version": pymatching.__version__,
        "bp_lsd": {"methods": list(LSD_METHODS), "bp_method": "minimum_sum",
                   "ms_scaling_factor": 0.9, "max_iter": 200,
                   "lsd_order": 0, "bits_per_step": 1},
        "shots_per_condition": shots,
        "distance": 3,
        "elapsed_seconds": elapsed,
        "stochastic_qshift_shots": sum(r["shots"] for r in results),
        "scope": "development only; circuit samples are exact but all candidate decoders use the same approximate DEM",
        "conditions": results,
    }
    target = HERE / ("bplsd_preflight.json" if args.preflight else "bplsd_results.json")
    target.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {target}; elapsed={elapsed:.3f}s")
    for row in results:
        print(row["memory_basis"], row["regime"], row["failures"],
              {m: row["comparisons"][m]["paired_ler_delta_vs_pymatching"] for m in LSD_METHODS})
    if args.preflight and elapsed * (5000/100) > 300:
        print("Preflight extrapolation exceeds the five-minute runtime gate")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
