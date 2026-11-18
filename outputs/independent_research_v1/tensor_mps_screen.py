"""Paired qecsim MPS versus MWPM screen under ideal code-capacity noise."""
from __future__ import annotations

import argparse
import json
import resource
import time
from pathlib import Path

import numpy as np
import qecsim
import qecsim.paulitools as pt
from scipy.stats import binomtest, t
from qecsim.models.generic import DepolarizingErrorModel
from qecsim.models.planar import PlanarCode, PlanarMPSDecoder, PlanarMWPMDecoder

ROOT = Path(__file__).resolve().parent
P = 0.05
SEEDS = {3: 202611181, 5: 202611182}
PREFLIGHT_SEEDS = {3: 202611183, 5: 202611184}


def wilson_interval(errors: int, shots: int, z: float = 1.959963984540054) -> list[float]:
    rate = errors / shots
    denominator = 1 + z * z / shots
    center = (rate + z * z / (2 * shots)) / denominator
    half = z * np.sqrt(rate * (1 - rate) / shots + z * z / (4 * shots * shots)) / denominator
    return [float(center - half), float(center + half)]


def run_distance(distance: int, shots: int, seed: int) -> dict:
    code = PlanarCode(distance, distance)
    noise = DepolarizingErrorModel()
    rng = np.random.default_rng(seed)
    decoders = {
        "mwpm": PlanarMWPMDecoder(),
        "mps": PlanarMPSDecoder(chi=None, mode="c"),
    }
    failures = {name: 0 for name in decoders}
    only_failures = {name: 0 for name in decoders}
    paired_differences = np.empty(shots, dtype=np.int8)
    decode_seconds = {name: 0.0 for name in decoders}
    for shot in range(shots):
        error = noise.generate(code, P, rng)
        syndrome = pt.bsp(error, code.stabilizers.T)
        shot_results = {}
        for name, decoder in decoders.items():
            start = time.perf_counter()
            recovery = decoder.decode(code, syndrome, error_model=noise, error_probability=P)
            decode_seconds[name] += time.perf_counter() - start
            recovered = np.bitwise_xor(error, recovery)
            if np.any(pt.bsp(recovered, code.stabilizers.T)):
                raise RuntimeError(f"{name} returned a recovery outside the codespace at d={distance}, shot={shot}")
            failed = bool(np.any(pt.bsp(recovered, code.logicals.T)))
            shot_results[name] = failed
            failures[name] += failed
        only_failures["mwpm"] += shot_results["mwpm"] and not shot_results["mps"]
        only_failures["mps"] += shot_results["mps"] and not shot_results["mwpm"]
        paired_differences[shot] = int(shot_results["mps"]) - int(shot_results["mwpm"])

    delta = float(np.mean(paired_differences))
    standard_error = float(np.std(paired_differences, ddof=1) / np.sqrt(shots)) if shots > 1 else 0.0
    critical = float(t.ppf(0.975, shots - 1)) if shots > 1 else 0.0
    discordant = only_failures["mwpm"] + only_failures["mps"]
    return {
        "distance": distance,
        "code_shape": code.n_k_d,
        "error_model": "qecsim IID depolarizing code-capacity noise, P(X)=P(Y)=P(Z)=p/3",
        "p": P,
        "shots": shots,
        "seed": seed,
        "failures": failures,
        "ler": {name: failures[name] / shots for name in failures},
        "wilson_95": {name: wilson_interval(failures[name], shots) for name in failures},
        "paired_mps_minus_mwpm_ler": delta,
        "paired_normal_95": [delta - critical * standard_error, delta + critical * standard_error],
        "mwpm_only_failures": int(only_failures["mwpm"]),
        "mps_only_failures": int(only_failures["mps"]),
        "discordant_shots": discordant,
        "mcnemar_two_sided_p": float(binomtest(only_failures["mwpm"], discordant, 0.5).pvalue) if discordant else 1.0,
        "decode_seconds": decode_seconds,
        "seconds_per_decode": {name: decode_seconds[name] / shots for name in decode_seconds},
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
    seeds = PREFLIGHT_SEEDS if args.preflight else SEEDS
    start = time.perf_counter()
    results = [run_distance(d, shots, seeds[d]) for d in (3, 5)]
    elapsed = time.perf_counter() - start
    outcome = {
        "status": "preflight" if args.preflight else "development_feasibility",
        "qecsim_version": qecsim.__version__,
        "python": "3.12",
        "shots_per_distance": shots,
        "distance_results": results,
        "elapsed_seconds": elapsed,
        "stochastic_qshift_circuit_shots": 0,
        "scope": "ideal-syndrome code-capacity depolarizing model; not Q-SHIFT circuit-level validation",
    }
    target = ROOT / ("tensor_mps_preflight.json" if args.preflight else "tensor_mps_results.json")
    target.write_text(json.dumps(outcome, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {target}; elapsed={elapsed:.3f}s")
    for result in results:
        print(f"d={result['distance']} shots={shots} mwpm={result['ler']['mwpm']:.6g} "
              f"mps={result['ler']['mps']:.6g} paired_delta={result['paired_mps_minus_mwpm_ler']:.6g}")
    if args.preflight and elapsed > 300:
        print("Preflight exceeded the five-minute budget")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
