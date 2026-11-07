"""Paired Phase 3A pilot: composition-specialized PyMatching on a rotated surface code."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pymatching
import stim

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
RESULTS, RAW, FIGURES = ROOT / "results", ROOT / "raw", ROOT / "figures"
COMPOSITIONS = CONFIG["composition"]
CONDITIONS = tuple(COMPOSITIONS)
SPECIALISTS = ("x_biased", "z_biased", "depolarizing")
DECODERS = ("fixed_nominal", *SPECIALISTS, "oracle_noise_informed")


def make_circuit(composition: str) -> stim.Circuit:
    """Hold Stim's rotated memory circuit and fault locations fixed; only Pauli weights vary."""
    p = float(CONFIG["p_local_nonidentity"])
    # Config entries are conditional composition fractions; convert them to
    # unconditional Stim channel probabilities whose sum is p.
    p_x, p_y, p_z = (p * fraction for fraction in COMPOSITIONS[composition])
    source = stim.Circuit.generated(
        CONFIG["code_task"], distance=CONFIG["distance"], rounds=CONFIG["rounds"],
        after_clifford_depolarization=p,
        before_measure_flip_probability=float(CONFIG["measurement_noise"]),
    ).flattened()
    out = stim.Circuit()
    replaced = {"DEPOLARIZE1": 0, "DEPOLARIZE2": 0}
    for inst in source:
        if inst.name in replaced:
            if not math.isclose(float(inst.gate_args_copy()[0]), p, rel_tol=0, abs_tol=1e-15):
                raise ValueError(f"Unexpected generated noise probability in {inst}")
            out.append("PAULI_CHANNEL_1", inst.targets_copy(), [p_x, p_y, p_z])
            replaced[inst.name] += 1
        else:
            out.append(inst.name, inst.targets_copy(), inst.gate_args_copy())
    if not all(replaced.values()):
        raise RuntimeError(f"Expected both one- and two-qubit post-Clifford noise, got {replaced}")
    return out


def decoder_for(composition: str):
    circuit = make_circuit(composition)
    dem = circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)
    matcher = pymatching.Matching.from_detector_error_model(dem)
    return circuit, dem, matcher


def sample(circuit: stim.Circuit, shots: int, seed: int):
    detectors, observables = circuit.compile_detector_sampler(seed=seed).sample(
        shots=shots, separate_observables=True
    )
    return detectors.astype(np.uint8), observables.astype(np.uint8)


def structure_signature(circuit: stim.Circuit) -> str:
    """Hash gate/target order while ignoring only the Pauli-channel probability arguments."""
    rows = []
    for inst in circuit:
        if inst.name == "PAULI_CHANNEL_1":
            rows.append((inst.name, tuple(str(t) for t in inst.targets_copy()), "NOISE_ARGS"))
        else:
            rows.append((inst.name, tuple(str(t) for t in inst.targets_copy()), tuple(inst.gate_args_copy())))
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


def wilson(errors: int, n: int):
    z = 1.959963984540054
    p = errors / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [mid - half, mid + half]


def pair_metrics(residual: np.ndarray, fixed: np.ndarray):
    a = int(np.count_nonzero((residual == 1) & (fixed == 0)))
    b = int(np.count_nonzero((residual == 0) & (fixed == 1)))
    return {"candidate_only_wrong": a, "fixed_only_wrong": b, "difference_errors": a-b,
            "discordant_shots": a+b}


def exact_mcnemar_p(a: int, b: int) -> float:
    n = a + b
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, j) for j in range(min(a, b) + 1)) / (2**n))


def run(args):
    RESULTS.mkdir(exist_ok=True); RAW.mkdir(exist_ok=True); FIGURES.mkdir(exist_ok=True)
    output = RESULTS / args.output
    manifest = RAW / f"manifest_{output.stem}.json"
    plot = FIGURES / f"{output.stem}_residual_rates.png"
    raw_paths = [RAW / f"{output.stem}_seed_{seed}.npz" for seed in CONFIG["seeds"]]
    collision = [p for p in [output, manifest, plot, *raw_paths] if p.exists()]
    if collision:
        raise FileExistsError("Refusing to overwrite Phase 3 artifacts: " + ", ".join(str(p) for p in collision))

    models, metadata, circuits, dems = {}, {}, {}, {}
    for condition in CONDITIONS:
        circuit, dem, matcher = decoder_for(condition)
        circuits[condition], dems[condition] = circuit, dem
        models[condition] = matcher
        metadata[condition] = {
            "stim_num_qubits": circuit.num_qubits,
            "detectors": circuit.num_detectors,
            "observables": circuit.num_observables,
            "dem_error_terms": sum(line.startswith("error(") for line in str(dem).splitlines()),
            "dem_text_bytes": len(str(dem).encode("utf-8")),
            "matching_edges": matcher.num_edges,
            "matching_num_detectors": matcher.num_detectors,
            "matching_python_wrapper_bytes": sys.getsizeof(matcher),
            "post_clifford_pauli_channel_instructions": sum(1 for inst in circuit if inst.name == "PAULI_CHANNEL_1"),
            "post_clifford_qubit_fault_opportunities": sum(len(inst.targets_copy()) for inst in circuit if inst.name == "PAULI_CHANNEL_1"),
            "local_channel_probabilities_px_py_pz": [float(CONFIG["p_local_nonidentity"] * f) for f in COMPOSITIONS[condition]],
            "measurement_fault_probability": CONFIG["measurement_noise"],
            "circuit_text_sha256": hashlib.sha256(str(circuit).encode()).hexdigest(),
            "dem_text_sha256": hashlib.sha256(str(dem).encode()).hexdigest(),
            "ideal_structure_sha256": structure_signature(circuit),
        }
    structure_hashes = {metadata[c]["ideal_structure_sha256"] for c in CONDITIONS}
    if len(structure_hashes) != 1:
        raise RuntimeError("Circuit structure or detector targets changed between noise conditions")

    # Fixed nominal is the depolarizing model. Its corrections are explicitly paired with all models.
    fixed = models["depolarizing"]
    baseline_predictions, static, per_seed, raw_manifest = {}, {c: {} for c in CONDITIONS}, [], []
    runtimes = {d: [] for d in DECODERS}
    for seed in CONFIG["seeds"]:
        raw = {"seed": np.asarray(seed, dtype=np.int64)}
        seed_result = {"seed": seed, "conditions": {}}
        for ci, condition in enumerate(CONDITIONS):
            detectors, observed = sample(circuits[condition], CONFIG["shots_per_condition_seed"], seed + 100 * ci)
            obs = observed[:, 0]
            raw[f"{condition}_detectors"] = detectors
            raw[f"{condition}_observable_audit_only"] = obs
            predictions, residuals, timing = {}, {}, {}
            models_this = {"fixed_nominal": fixed,
                           "x_biased": models["x_biased"],
                           "z_biased": models["z_biased"],
                           "depolarizing": models["depolarizing"],
                           "oracle_noise_informed": models[condition]}
            for name, matcher in models_this.items():
                start = time.perf_counter()
                pred = np.asarray(matcher.decode_batch(detectors), dtype=np.uint8).reshape(-1)
                timing[name] = (time.perf_counter() - start) / len(detectors)
                predictions[name] = pred
                residuals[name] = obs ^ pred
                runtimes[name].append(timing[name])
            fixed_residual = residuals["fixed_nominal"]
            condition_stats = {"shots": len(detectors), "raw_observable_flips": int(obs.sum()), "decoders": {}}
            for name in DECODERS:
                err = int(residuals[name].sum())
                pred_diff = int(np.count_nonzero(predictions[name] != predictions["fixed_nominal"]))
                entry = {"residual_errors": err, "residual_rate": float(err / len(obs)),
                         "residual_wilson95": wilson(err, len(obs)),
                         "prediction_disagreements_vs_fixed": pred_diff,
                         "prediction_disagreement_rate_vs_fixed": pred_diff / len(obs),
                         "runtime_seconds_per_shot": timing[name]}
                if name != "fixed_nominal":
                    paired = pair_metrics(residuals[name], fixed_residual)
                    delta = paired["difference_errors"] / len(obs)
                    se = math.sqrt(max(0, paired["discordant_shots"] - paired["difference_errors"]**2 / len(obs))) / len(obs)
                    paired["paired_rate_difference"] = delta
                    paired["paired_rate_difference_ci95_approx"] = [delta - 1.96 * se, delta + 1.96 * se]
                    paired["mcnemar_exact_two_sided_p"] = exact_mcnemar_p(paired["candidate_only_wrong"], paired["fixed_only_wrong"])
                    entry["paired_residual_comparison_vs_fixed"] = paired
                condition_stats["decoders"][name] = entry
                aggregate = static[condition].setdefault(name, {"errors": 0, "shots": 0, "prediction_disagreements": 0,
                                                                  "candidate_only_wrong": 0, "fixed_only_wrong": 0})
                aggregate["errors"] += err; aggregate["shots"] += len(obs); aggregate["prediction_disagreements"] += pred_diff
                if name != "fixed_nominal":
                    pair = entry["paired_residual_comparison_vs_fixed"]
                    aggregate["candidate_only_wrong"] += pair["candidate_only_wrong"]
                    aggregate["fixed_only_wrong"] += pair["fixed_only_wrong"]
            seed_result["conditions"][condition] = condition_stats
        raw_path = RAW / f"{output.stem}_seed_{seed}.npz"
        np.savez_compressed(raw_path, **raw)
        raw_manifest.append({"file": raw_path.name, "bytes": raw_path.stat().st_size,
                             "sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest()})
        per_seed.append(seed_result)
        print(f"Completed pilot seed {seed}; raw checkpoint saved.", flush=True)

    for condition in CONDITIONS:
        for name, item in static[condition].items():
            n, e = item["shots"], item["errors"]
            item["residual_rate"] = e / n
            item["wilson95"] = wilson(e, n)
            item["prediction_disagreement_rate_vs_fixed"] = item["prediction_disagreements"] / n
            if name != "fixed_nominal":
                item["paired_rate_difference"] = (e - static[condition]["fixed_nominal"]["errors"]) / n
                item["paired_candidate_only_wrong"] = item.pop("candidate_only_wrong")
                item["paired_fixed_only_wrong"] = item.pop("fixed_only_wrong")
                delta = item["paired_rate_difference"]
                discordant = item["paired_candidate_only_wrong"] + item["paired_fixed_only_wrong"]
                se = math.sqrt(max(0, discordant - (n * delta)**2 / n)) / n
                item["paired_rate_difference_ci95_approx"] = [delta - 1.96 * se, delta + 1.96 * se]
                item["mcnemar_exact_two_sided_p"] = exact_mcnemar_p(item["paired_candidate_only_wrong"], item["paired_fixed_only_wrong"])

    ideal = stim.Circuit.generated(CONFIG["code_task"], distance=CONFIG["distance"], rounds=CONFIG["rounds"])
    ideal_detectors, ideal_observables = sample(ideal, 256, 983999)
    ideal_validation = {"shots": 256, "all_detectors_zero": bool(not ideal_detectors.any()),
                        "all_logical_observables_zero": bool(not ideal_observables.any()),
                        "detector_shape": list(ideal_detectors.shape), "observable_shape": list(ideal_observables.shape)}
    if not ideal_validation["all_detectors_zero"] or not ideal_validation["all_logical_observables_zero"]:
        raise RuntimeError(f"Ideal-circuit validation failed: {ideal_validation}")
    validation_results = {}
    for condition, circuit in circuits.items():
        detectors, obs = sample(circuit, 256, 984000 + CONDITIONS.index(condition))
        pred = np.asarray(fixed.decode_batch(detectors), dtype=np.uint8).reshape(-1)
        validation_results[condition] = {"detector_shape": list(detectors.shape), "observable_shape": list(obs.shape),
                                         "prediction_shape": list(pred.shape),
                                         "residual_count": int(np.count_nonzero(obs[:, 0] ^ pred))}

    summary = {"experiment_id": CONFIG["experiment_id"], "pilot_only": True,
               "software": {"python": platform.python_version(), "stim": stim.__version__,
                            "pymatching": pymatching.__version__, "numpy": np.__version__},
               "config": CONFIG, "ideal_circuit_validation": ideal_validation, "circuit_validation": validation_results,
               "models": metadata, "aggregate_by_condition": static, "per_seed": per_seed,
               "mean_runtime_seconds_per_shot": {k: float(np.mean(v)) for k, v in runtimes.items()},
               "raw_files": raw_manifest}
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    manifest.write_text(json.dumps({"result": output.name, "files": raw_manifest}, indent=2) + "\n", encoding="utf-8")
    create_plot(static, plot)
    print(f"Saved {output} and {plot}")


def create_plot(aggregate, path):
    names = DECODERS
    labels = ["Fixed nominal", "X specialist", "Z specialist", "Depolarizing specialist", "Noise-informed oracle"]
    conditions = list(aggregate)
    fig, ax = plt.subplots(figsize=(10.5, 5.6))
    x = np.arange(len(conditions)); width = 0.15
    for i, (name, label) in enumerate(zip(names, labels)):
        rates = np.asarray([aggregate[c][name]["residual_rate"] for c in conditions])
        cis = np.asarray([aggregate[c][name]["wilson95"] for c in conditions])
        pos = x + (i - 2) * width
        ax.bar(pos, rates, width, label=label)
        ax.errorbar(pos, rates, yerr=np.vstack([np.maximum(0, rates-cis[:, 0]),
                                                np.maximum(0, cis[:, 1]-rates)]),
                    fmt="none", ecolor="black", capsize=2, linewidth=.7)
    ax.set_xticks(x, conditions, rotation=20, ha="right")
    ax.set_ylabel("Residual logical-observable error rate")
    ax.set_title("Distance-3 rotated surface-code pilot; paired shots")
    ax.legend(fontsize=8); ax.grid(axis="y", alpha=.25); fig.tight_layout()
    fig.savefig(path, dpi=180); plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="phase3a_surface_pilot_v1.json")
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
