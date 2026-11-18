"""Known-profile X/Z memory-basis sensitivity at intermediate bias ratios."""
from __future__ import annotations

import argparse
import json
import time
import sys
from pathlib import Path

import numpy as np
import pymatching
import stim
from scipy.stats import beta, binomtest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PHASE2B = REPO / "outputs" / "phase2b_pauli_bias"
sys.path.insert(0, str(PHASE2B))
from noise_model import (  # noqa: E402
    MEMORY_BASES,
    REGIMES,
    build_circuit,
    circuit_noise_record,
)

BIAS_RATIOS = (2.0, 5.0)
TEST_REGIMES = ("x_biased", "z_biased")
CONDITIONS = tuple((ratio, regime, basis)
                   for ratio in BIAS_RATIOS
                   for regime in TEST_REGIMES
                   for basis in MEMORY_BASES)
PREFLIGHT_SEEDS = tuple(range(2026111201, 2026111209))
MAIN_SEEDS = tuple(range(2026111211, 2026111219))


def wilson(errors: int, shots: int) -> list[float]:
    z = 1.959963984540054
    rate = errors/shots
    d = 1+z*z/shots
    center = (rate+z*z/(2*shots))/d
    half = z*np.sqrt(rate*(1-rate)/shots+z*z/(4*shots*shots))/d
    return [float(center-half), float(center+half)]


def rate_ratio(a: int, b: int) -> dict:
    if not a or not b:
        return {"ratio": None, "conditional_exact_95_ci": None,
                "equal_rate_exact_p": float(binomtest(a, a+b, 0.5).pvalue)}
    p = a/(a+b)
    interval = beta.ppf([0.025, 0.975], a, b+1)
    return {
        "ratio": float(p/(1-p)),
        "conditional_exact_95_ci": [float(x/(1-x)) for x in interval],
        "equal_rate_exact_p": float(binomtest(a, a+b, 0.5).pvalue),
    }


def run_condition(ratio: float, regime: str, basis: str, shots: int, seed: int) -> dict:
    circuit = build_circuit(basis, regime, bias_ratio=ratio)
    dem = circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=0.0018)
    matching = pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)
    detectors, observables = circuit.compile_detector_sampler(seed=seed).sample(
        shots=shots, separate_observables=True)
    errors = 0
    decode_seconds = 0.0
    for i, syndrome in enumerate(detectors):
        start = time.perf_counter()
        predicted = np.asarray(matching.decode(syndrome), dtype=np.bool_).reshape(-1)
        decode_seconds += time.perf_counter()-start
        errors += not np.array_equal(predicted, observables[i])
    _, record = circuit_noise_record(basis, regime, bias_ratio=ratio)
    return {
        "bias_ratio": ratio,
        "memory_basis": basis,
        "regime": regime,
        "seed": seed,
        "shots": shots,
        "physical_qubits": int(circuit.num_qubits),
        "detectors": int(circuit.num_detectors),
        "observables": int(circuit.num_observables),
        "noise_target_counts": record["flattened_noise_target_counts"],
        "noise_channel_counts": record["flattened_instruction_counts"],
        "failures": int(errors),
        "ler": errors/shots,
        "wilson_95": wilson(errors, shots),
        "decode_seconds": decode_seconds,
        "seconds_per_decode": decode_seconds/shots,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--shots", type=int, default=50000)
    args = parser.parse_args()
    if args.shots <= 0:
        parser.error("--shots must be positive")
    preflight = args.preflight
    shots = 200 if preflight else args.shots
    seeds = PREFLIGHT_SEEDS if preflight else MAIN_SEEDS
    started = time.perf_counter()
    rows = [run_condition(ratio, regime, basis, shots, seed)
            for (ratio, regime, basis), seed in zip(CONDITIONS, seeds, strict=True)]
    elapsed = time.perf_counter()-started
    comparisons = []
    for ratio in BIAS_RATIOS:
        for regime, aligned in (("x_biased", "x"), ("z_biased", "z")):
            selected = {x["memory_basis"]: x for x in rows
                        if x["bias_ratio"] == ratio and x["regime"] == regime}
            a, b = selected[aligned], selected["z" if aligned == "x" else "x"]
            comparisons.append({
                "bias_ratio": ratio,
                "regime": regime,
                "aligned_basis": aligned,
                "mismatched_basis": b["memory_basis"],
                "aligned_failures": a["failures"],
                "mismatched_failures": b["failures"],
                "aligned_ler": a["ler"],
                "mismatched_ler": b["ler"],
                "aligned_over_mismatched_rate_ratio": rate_ratio(a["failures"], b["failures"]),
            })
    resource_match = all(
        {(row["physical_qubits"], row["detectors"], row["observables"], tuple(sorted(row["noise_target_counts"].items())))
         for row in rows if row["bias_ratio"] == ratio and row["regime"] == regime}.__len__() == 1
        for ratio in BIAS_RATIOS for regime in TEST_REGIMES
    )
    output = {
        "status": "preflight" if preflight else "bias_crossover_development_screen",
        "stim_version": stim.__version__,
        "pymatching_version": pymatching.__version__,
        "bias_ratios": list(BIAS_RATIOS),
        "distance": 3,
        "rounds": 5,
        "shots_per_condition": shots,
        "matched_resources_by_regime_and_ratio": resource_match,
        "conditions": rows,
        "aligned_vs_mismatched": comparisons,
        "elapsed_seconds": elapsed,
        "stochastic_circuit_shots": shots*len(rows),
        "scope": "fixed known-profile basis comparison; no adaptive inference or threshold claim",
    }
    target = HERE/("bias_crossover_preflight.json" if preflight else "bias_crossover_results.json")
    target.write_text(json.dumps(output, indent=2)+"\n", encoding="utf-8")
    print(f"Wrote {target}; elapsed={elapsed:.3f}s; resources_match={resource_match}")
    for x in comparisons:
        print(x["bias_ratio"], x["regime"],
              f"aligned={x['aligned_ler']:.6g}",f"mismatch={x['mismatched_ler']:.6g}",
              x["aligned_over_mismatched_rate_ratio"])
    if preflight and elapsed*(50000/200)>300:
        print("Preflight projection exceeds five-minute cap; stop before main screen")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
