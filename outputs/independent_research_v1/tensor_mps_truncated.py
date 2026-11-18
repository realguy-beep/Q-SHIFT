"""Fixed-chi qecsim planar MPS versus MWPM code-capacity screen."""
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

HERE = Path(__file__).resolve().parent
P = 0.05
CHI = 16
PREFLIGHT_SEEDS = {3: 2026111301, 5: 2026111302}
MAIN_SEEDS = {3: 2026111311, 5: 2026111312}


def wilson(errors: int, shots: int) -> list[float]:
    z = 1.959963984540054
    rate = errors/shots
    d = 1+z*z/shots
    center = (rate+z*z/(2*shots))/d
    half = z*np.sqrt(rate*(1-rate)/shots+z*z/(4*shots*shots))/d
    return [float(center-half), float(center+half)]


def run_distance(distance: int, shots: int, seed: int) -> dict:
    code = PlanarCode(distance, distance)
    noise = DepolarizingErrorModel()
    rng = np.random.default_rng(seed)
    decoders = {
        "mwpm": PlanarMWPMDecoder(),
        "mps_chi16": PlanarMPSDecoder(chi=CHI, mode="c"),
    }
    failures = {name: 0 for name in decoders}
    only = {name: 0 for name in decoders}
    decode_seconds = {name: 0.0 for name in decoders}
    for shot in range(shots):
        error = noise.generate(code, P, rng)
        syndrome = pt.bsp(error, code.stabilizers.T)
        decoded = {}
        for name, decoder in decoders.items():
            start = time.perf_counter()
            recovery = decoder.decode(code, syndrome, error_model=noise, error_probability=P)
            decode_seconds[name] += time.perf_counter()-start
            recovered = np.bitwise_xor(error, recovery)
            if np.any(pt.bsp(recovered, code.stabilizers.T)):
                raise RuntimeError(f"{name} recovery outside codespace, d={distance}, shot={shot}")
            decoded[name] = bool(np.any(pt.bsp(recovered, code.logicals.T)))
            failures[name] += decoded[name]
        only["mwpm"] += decoded["mwpm"] and not decoded["mps_chi16"]
        only["mps_chi16"] += decoded["mps_chi16"] and not decoded["mwpm"]
    discordant = only["mwpm"]+only["mps_chi16"]
    delta = (failures["mps_chi16"]-failures["mwpm"])/shots
    sample_variance = max(0.0, (discordant-shots*delta*delta)/(shots-1)) if shots > 1 else 0.0
    paired_se = float(np.sqrt(sample_variance/shots))
    critical = float(t.ppf(0.975, shots-1)) if shots > 1 else 0.0
    return {
        "distance": distance,
        "code_shape": code.n_k_d,
        "error_model": "IID depolarizing code-capacity noise, P(X)=P(Y)=P(Z)=p/3",
        "p": P,
        "shots": shots,
        "seed": seed,
        "mps_chi": CHI,
        "mps_mode": "c",
        "failures": failures,
        "ler": {name: failures[name]/shots for name in failures},
        "wilson_95": {name: wilson(failures[name], shots) for name in failures},
        "paired_mps_minus_mwpm_ler": delta,
        "paired_normal_95": [delta-critical*paired_se, delta+critical*paired_se],
        "mwpm_only_failures": int(only["mwpm"]),
        "mps_only_failures": int(only["mps_chi16"]),
        "discordant_shots": int(discordant),
        "mcnemar_two_sided_p": float(binomtest(only["mwpm"], discordant, 0.5).pvalue) if discordant else 1.0,
        "decode_seconds": decode_seconds,
        "seconds_per_decode": {name: decode_seconds[name]/shots for name in decoders},
        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--shots", type=int, default=5000)
    args = parser.parse_args()
    if args.shots <= 0:
        parser.error("--shots must be positive")
    preflight = args.preflight
    shots = 100 if preflight else args.shots
    seeds = PREFLIGHT_SEEDS if preflight else MAIN_SEEDS
    started = time.perf_counter()
    rows = [run_distance(d, shots, seeds[d]) for d in (3, 5)]
    elapsed = time.perf_counter()-started
    output = {
        "status": "preflight" if preflight else "development_feasibility",
        "qecsim_version": qecsim.__version__,
        "python": "3.12",
        "mps_chi": CHI,
        "mps_mode": "c",
        "shots_per_distance": shots,
        "distance_results": rows,
        "elapsed_seconds": elapsed,
        "stochastic_qshift_circuit_shots": 0,
        "scope": "ideal-syndrome code-capacity depolarizing model; not Q-SHIFT circuit-level validation",
    }
    target = HERE/("tensor_mps_chi16_preflight.json" if preflight else "tensor_mps_chi16_results.json")
    target.write_text(json.dumps(output, indent=2)+"\n", encoding="utf-8")
    print(f"Wrote {target}; elapsed={elapsed:.3f}s")
    for row in rows:
        print(f"d={row['distance']} shots={shots} mwpm={row['ler']['mwpm']:.6g} "
              f"mps_chi16={row['ler']['mps_chi16']:.6g} paired_delta={row['paired_mps_minus_mwpm_ler']:.6g}")
    if preflight and elapsed*(5000/100)>300:
        print("Preflight extrapolation exceeds the five-minute runtime cap")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
