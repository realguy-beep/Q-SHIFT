"""Compare instrumented-direct categorical samples against unmodified Stim circuits."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pymatching
import stim

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PHASE2B = REPO / "outputs" / "phase2b_pauli_bias"
sys.path.insert(0, str(PHASE2B))
from noise_model import MEMORY_BASES, REGIMES, build_circuit  # noqa: E402

SEEDS = (202611551, 202611552, 202611553, 202611554, 202611555, 202611556)
CONDITIONS = tuple((basis, regime) for basis in MEMORY_BASES for regime in REGIMES)
SHOTS = 20000


def main() -> int:
    prior_path = HERE / "categorical_importance_results.json"
    prior = json.loads(prior_path.read_text(encoding="utf-8"))
    rows = []
    for condition, seed, instrumented_row in zip(CONDITIONS, SEEDS, prior["conditions"], strict=True):
        basis, regime = condition
        circuit = build_circuit(basis, regime)
        dem = circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=0.0018)
        matching = pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)
        detectors, observables = circuit.compile_detector_sampler(seed=seed).sample(
            shots=SHOTS, separate_observables=True)
        failures = np.empty(SHOTS, dtype=np.bool_)
        for i, syndrome in enumerate(detectors):
            prediction = np.asarray(matching.decode(syndrome), dtype=np.bool_).reshape(-1)
            failures[i] = not np.array_equal(prediction, observables[i])
        raw_ler = float(failures.mean())
        instrumented_ler = float(instrumented_row["direct_ler"])
        raw_var = raw_ler*(1-raw_ler)/SHOTS
        inst_n = int(instrumented_row["shots_per_arm"])
        inst_var = instrumented_ler*(1-instrumented_ler)/inst_n
        denom = float(np.sqrt(raw_var+inst_var))
        z = (raw_ler-instrumented_ler)/denom if denom else 0.0
        rows.append({
            "memory_basis": basis,
            "regime": regime,
            "seed": seed,
            "shots": SHOTS,
            "raw_circuit_failures": int(failures.sum()),
            "raw_circuit_ler": raw_ler,
            "instrumented_direct_ler": instrumented_ler,
            "difference_raw_minus_instrumented": raw_ler-instrumented_ler,
            "independent_binomial_z": z,
            "detectors": int(detectors.shape[1]),
            "observables": int(observables.shape[1]),
        })
    passed = all(abs(row["independent_binomial_z"]) < 4 for row in rows)
    output = {
        "status": "pass" if passed else "failed",
        "stim_version": stim.__version__,
        "pymatching_version": pymatching.__version__,
        "shots_per_condition": SHOTS,
        "condition_results": rows,
        "max_abs_z": max(abs(row["independent_binomial_z"]) for row in rows),
        "stochastic_original_circuit_shots": SHOTS*len(rows),
        "scope": "independent validation that instrumented alpha=1 sampling preserves source-circuit logical failure rates",
    }
    target = HERE / "categorical_sampler_crosscheck.json"
    target.write_text(json.dumps(output, indent=2)+"\n", encoding="utf-8")
    print(f"Wrote {target}; pass={passed}; max_abs_z={output['max_abs_z']:.3f}")
    for row in rows:
        print(row["memory_basis"], row["regime"],
              f"raw={row['raw_circuit_ler']:.6g}",
              f"instrumented={row['instrumented_direct_ler']:.6g}",
              f"z={row['independent_binomial_z']:.3f}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
