"""Run the frozen Q-SHIFT Phase 3B independent replication."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import platform
import statistics
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pymatching
import stim

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "CONFIG.json").read_text(encoding="utf-8"))
PHASE3A_ROOT = ROOT.parent / "phase3_geometry_investigation"
PHASE3A_RUNNER = PHASE3A_ROOT / "run_phase3_pilot.py"
PHASE3A_RESULT = PHASE3A_ROOT / "results" / "phase3a_surface_pilot_v4.json"
PROTOCOL_PATH = ROOT / "PRE_REGISTERED_PROTOCOL.md"
CONDITIONS = tuple(x["name"] for x in CFG["conditions"])
SPECIALISTS = ("x_biased_specialist", "z_biased_specialist", "depolarizing_specialist")
DECODERS = ("fixed_nominal", *SPECIALISTS, "oracle_noise_informed")
RAW_DIR, PLOT_DIR = ROOT / "raw_data", ROOT / "plots"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_phase3a():
    if sha256(PROTOCOL_PATH) != CFG["protocol_sha256"]:
        raise RuntimeError("Frozen protocol SHA-256 mismatch; refusing to generate test data")
    if CFG.get("runner_sha256") and sha256(ROOT/"run_phase3b_replication.py") != CFG["runner_sha256"]:
        raise RuntimeError("Frozen Phase 3B runner SHA-256 mismatch; refusing to generate test data")
    if sha256(PHASE3A_RUNNER) != CFG["phase3a_runner_sha256"]:
        raise RuntimeError("Audited Phase 3A runner changed; refusing silent methodology drift")
    if sha256(PHASE3A_RESULT) != CFG["phase3a_v4_result_sha256"]:
        raise RuntimeError("Audited Phase 3A v4 result changed; refusing silent baseline drift")
    spec = importlib.util.spec_from_file_location("phase3a_frozen", PHASE3A_RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def exact_binomial_two_sided_p(k: int, n: int) -> float:
    if n == 0:
        return 1.0
    tail = min(k, n-k)
    return min(1.0, 2 * sum(math.comb(n, j) for j in range(tail + 1)) / (2**n))


def sign_test(seed_differences: list[float]) -> dict:
    positive = sum(x > 0 for x in seed_differences)
    negative = sum(x < 0 for x in seed_differences)
    ties = sum(x == 0 for x in seed_differences)
    return {"x_specialist_wins": negative, "fixed_wins": positive, "ties": ties,
            "non_tied_seeds": positive + negative,
            "exact_two_sided_sign_test_p": exact_binomial_two_sided_p(min(positive, negative), positive+negative)}


def mcnemar(a: int, b: int, n: int) -> dict:
    difference = a-b
    delta = difference/n
    discordant = a+b
    se = math.sqrt(max(0.0, discordant - difference*difference/n))/n
    return {"x_specialist_only_wrong": a, "fixed_only_wrong": b,
            "discordant_shots": discordant, "difference_errors": difference,
            "paired_rate_difference": delta,
            "paired_rate_difference_ci95_approx": [delta-1.96*se, delta+1.96*se],
            "exact_two_sided_mcnemar_p": exact_binomial_two_sided_p(min(a,b), a+b)}


def wilson(k: int, n: int) -> list[float]:
    z = 1.959963984540054
    p = k/n
    den = 1 + z*z/n
    center = (p + z*z/(2*n))/den
    half = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/den
    return [center-half, center+half]


def bootstrap_mean_ci(values: list[float]) -> list[float]:
    rng = np.random.default_rng(CFG["primary_bootstrap_seed"])
    values = np.asarray(values, dtype=float)
    indices = rng.integers(0, len(values), size=(CFG["primary_seed_bootstrap_resamples"], len(values)))
    means = values[indices].mean(axis=1)
    return [float(np.quantile(means, .025)), float(np.quantile(means, .975))]


def holm_adjust(pvalues: list[float]) -> list[float]:
    order = np.argsort(pvalues)
    adjusted = [0.0] * len(pvalues)
    running = 0.0
    m = len(pvalues)
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (m-rank) * pvalues[int(index)]))
        adjusted[int(index)] = running
    return adjusted


def model_set(phase3a, models, condition):
    return {"fixed_nominal": models["depolarizing"],
            "x_biased_specialist": models["x_biased"],
            "z_biased_specialist": models["z_biased"],
            "depolarizing_specialist": models["depolarizing"],
            "oracle_noise_informed": models[condition]}


def run():
    RAW_DIR.mkdir(exist_ok=True); PLOT_DIR.mkdir(exist_ok=True)
    seed_roots = [CFG["independent_seed_roots"]["start"] + i*CFG["independent_seed_roots"]["step"]
                  for i in range(CFG["independent_seed_roots"]["count"])]
    raw_paths = [RAW_DIR / f"phase3b_seed_{root}.npz" for root in seed_roots]
    final_paths = [ROOT/"RESULTS.json", ROOT/"per_seed_results.csv", ROOT/"statistical_analysis.json",
                   ROOT/"SHA256_MANIFEST.json", ROOT/"REPORT.md",
                   PLOT_DIR/"primary_seed_differences.png", PLOT_DIR/"decoder_error_rates.png"]
    collisions = [p for p in [*raw_paths, *final_paths] if p.exists()]
    if collisions:
        raise FileExistsError("Refusing to overwrite Phase 3B artifacts: " + ", ".join(str(p) for p in collisions))

    phase3a = load_phase3a()
    prior = json.loads(PHASE3A_RESULT.read_text(encoding="utf-8"))
    # The root identifiers and all derived Stim seeds must be disjoint from Phase 3A and the timing check.
    sample_seeds = [root + 101 + 100*c for root in seed_roots for c in range(len(CONDITIONS))]
    forbidden = {31503001 + 100000*r + 100*c for r in range(3) for c in range(4)} | {31999001}
    if len(set(sample_seeds)) != len(sample_seeds) or set(sample_seeds) & forbidden:
        raise RuntimeError("Seed derivation is not independent of prior experiments")

    circuits, dems, models, metadata = {}, {}, {}, {}
    for condition in CONDITIONS:
        circuit, dem, matcher = phase3a.decoder_for(condition)
        circuits[condition], dems[condition], models[condition] = circuit, dem, matcher
        metadata[condition] = prior["models"][condition]
        if phase3a.structure_signature(circuit) != prior["models"][condition]["ideal_structure_sha256"]:
            raise RuntimeError(f"Phase 3A structure signature mismatch for {condition}")
        if circuit.num_detectors != CFG["detectors"] or circuit.num_observables != CFG["observables"]:
            raise RuntimeError(f"Unexpected detector/observable schema for {condition}")

    ideal = stim.Circuit.generated(CFG["circuit_task"], distance=CFG["distance"], rounds=CFG["rounds"])
    ideal_d, ideal_o = phase3a.sample(ideal, 256, 31603999)
    ideal_ok = not ideal_d.any() and not ideal_o.any()
    if not ideal_ok:
        raise RuntimeError("Ideal circuit validation failed")

    per_seed, raw_entries, rows = [], [], []
    aggregate = {c: {name: {"errors": 0, "shots": 0, "prediction_disagreements": 0,
                              "candidate_only_wrong": 0, "fixed_only_wrong": 0} for name in DECODERS}
                 for c in CONDITIONS}
    paired_disagreements = {c: 0 for c in CONDITIONS}
    raw_errors = {c: 0 for c in CONDITIONS}
    timings = {name: [] for name in DECODERS}
    shot_hash_audit = []

    for rep_index, root_seed in enumerate(seed_roots):
        raw = {"seed_root": np.asarray(root_seed, dtype=np.int64)}
        seed_record = {"seed_root": root_seed, "conditions": {}}
        for ci, condition in enumerate(CONDITIONS):
            stim_seed = root_seed + 101 + 100*ci
            detectors, observables = phase3a.sample(circuits[condition], CFG["shots_per_seed_condition"], stim_seed)
            obs = np.asarray(observables, dtype=np.uint8).reshape(-1)
            if detectors.shape != (CFG["shots_per_seed_condition"], CFG["detectors"]):
                raise RuntimeError(f"Detector shape mismatch: {condition}, {root_seed}, {detectors.shape}")
            if obs.shape != (CFG["shots_per_seed_condition"],):
                raise RuntimeError(f"Observable shape mismatch: {condition}, {root_seed}, {obs.shape}")
            det_hash = hashlib.sha256(np.ascontiguousarray(detectors).tobytes()).hexdigest()
            shot_hash_audit.append({"seed_root": root_seed, "condition": condition,
                                    "stim_seed": stim_seed, "detector_sha256": det_hash})
            raw[f"{condition}_detectors"] = detectors
            raw[f"{condition}_observable_audit_only"] = obs
            raw[f"{condition}_stim_seed"] = np.asarray(stim_seed, dtype=np.int64)

            predictions, residuals, decode_times = {}, {}, {}
            decoders = model_set(phase3a, models, condition)
            for name, matcher in decoders.items():
                start = time.perf_counter()
                prediction = np.asarray(matcher.decode_batch(detectors), dtype=np.uint8).reshape(-1)
                decode_times[name] = (time.perf_counter()-start)/len(detectors)
                if prediction.shape != obs.shape:
                    raise RuntimeError(f"Prediction shape mismatch for {name}: {prediction.shape}")
                predictions[name] = prediction
                residuals[name] = obs ^ prediction
                timings[name].append(decode_times[name])

            fixed_residual = residuals["fixed_nominal"]
            condition_record = {"stim_seed": stim_seed, "shots": len(obs), "raw_observable_errors": int(obs.sum()),
                                "detector_sha256": det_hash, "decoders": {}}
            raw_errors[condition] += int(obs.sum())
            for name in DECODERS:
                residual = residuals[name]
                err = int(residual.sum())
                pred_disagree = int(np.count_nonzero(predictions[name] != predictions["fixed_nominal"]))
                only_model = int(np.count_nonzero((residual == 1) & (fixed_residual == 0)))
                only_fixed = int(np.count_nonzero((residual == 0) & (fixed_residual == 1)))
                aggregate[condition][name]["errors"] += err
                aggregate[condition][name]["shots"] += len(obs)
                aggregate[condition][name]["prediction_disagreements"] += pred_disagree
                if name != "fixed_nominal":
                    aggregate[condition][name]["candidate_only_wrong"] += only_model
                    aggregate[condition][name]["fixed_only_wrong"] += only_fixed
                condition_record["decoders"][name] = {
                    "residual_errors": err, "residual_rate": err/len(obs),
                    "residual_wilson95": wilson(err, len(obs)),
                    "prediction_disagreements_vs_fixed": pred_disagree,
                    "candidate_only_wrong": only_model,
                    "fixed_only_wrong": only_fixed,
                    "runtime_seconds_per_shot": decode_times[name],
                }
                delta_errors = err - int(fixed_residual.sum())
                rows.append({"seed_root": root_seed, "condition": condition, "stim_seed": stim_seed,
                             "decoder": name, "shots": len(obs), "raw_observable_errors": int(obs.sum()),
                             "residual_errors": err, "residual_rate": err/len(obs),
                             "prediction_disagreements_vs_fixed": pred_disagree,
                             "candidate_only_wrong": only_model, "fixed_only_wrong": only_fixed,
                             "difference_errors_vs_fixed": delta_errors,
                             "difference_rate_vs_fixed": delta_errors/len(obs),
                             "runtime_seconds_per_shot": decode_times[name]})
            paired_disagreements[condition] += int(np.count_nonzero(predictions["x_biased_specialist"] != predictions["fixed_nominal"]))
            seed_record["conditions"][condition] = condition_record

        per_seed.append(seed_record)
        raw_path = raw_paths[rep_index]
        np.savez_compressed(raw_path, **raw)
        raw_entries.append({"file": raw_path.name, "bytes": raw_path.stat().st_size, "sha256": sha256(raw_path)})
        print(f"Saved independent test seed {root_seed} ({rep_index+1}/{len(seed_roots)})", flush=True)

    # Verify aggregate decoder counts exactly equal the sum of seed-level counts.
    for condition in CONDITIONS:
        for decoder in DECODERS:
            summed = sum(s["conditions"][condition]["decoders"][decoder]["residual_errors"] for s in per_seed)
            if summed != aggregate[condition][decoder]["errors"]:
                raise RuntimeError(f"Aggregate mismatch: {condition}/{decoder}")

    for condition in CONDITIONS:
        for name in DECODERS:
            item = aggregate[condition][name]
            item["residual_rate"] = item["errors"]/item["shots"]
            item["wilson95"] = wilson(item["errors"], item["shots"])
            item["prediction_disagreement_rate_vs_fixed"] = item["prediction_disagreements"]/item["shots"]
            if name != "fixed_nominal":
                item["paired_rate_difference"] = (item["errors"]-aggregate[condition]["fixed_nominal"]["errors"])/item["shots"]

    # Primary inference uses seed-level rates; shot-level paired inference is supplemental.
    primary_condition = CFG["primary_condition"]
    primary_model = "x_biased_specialist"
    seed_differences = []
    for seed in per_seed:
        c = seed["conditions"][primary_condition]
        seed_differences.append((c["decoders"][primary_model]["residual_errors"]-
                                 c["decoders"]["fixed_nominal"]["residual_errors"])/c["shots"])
    primary_sign = sign_test(seed_differences)
    primary_ci = bootstrap_mean_ci(seed_differences)
    primary = {"endpoint": "x_specialist residual logical-observable error rate minus fixed nominal rate",
               "alpha_two_sided": .05, "seed_count": len(seed_differences),
               "seed_level_differences": seed_differences,
               "mean_seed_level_difference": float(np.mean(seed_differences)),
               "median_seed_level_difference": float(np.median(seed_differences)),
               "seed_bootstrap_mean_ci95": primary_ci,
               "seed_sign_test": primary_sign,
               "mean_fixed_residual_rate": aggregate[primary_condition]["fixed_nominal"]["residual_rate"],
               "mean_x_specialist_residual_rate": aggregate[primary_condition][primary_model]["residual_rate"],
               "prediction_disagreements": aggregate[primary_condition][primary_model]["prediction_disagreements"],
               "paired_shot_analysis": mcnemar(aggregate[primary_condition][primary_model]["candidate_only_wrong"],
                                                aggregate[primary_condition][primary_model]["fixed_only_wrong"],
                                                aggregate[primary_condition][primary_model]["shots"])}
    primary["supports_reproducible_improvement_by_preregistered_rule"] = (
        primary_sign["exact_two_sided_sign_test_p"] < .05 and primary_ci[1] < 0)

    secondary_specs = []
    for condition in CONDITIONS:
        for candidate in DECODERS:
            if candidate == "fixed_nominal":
                continue
            if condition == primary_condition and candidate == primary_model:
                continue
            if condition != primary_condition or candidate in ("z_biased_specialist", "depolarizing_specialist", "oracle_noise_informed"):
                secondary_specs.append((condition, candidate))
    if len(secondary_specs) != CFG["secondary_comparison_count"]:
        raise RuntimeError(f"Secondary comparison family mismatch: {len(secondary_specs)}")

    secondary = []
    for condition, candidate in secondary_specs:
        per_seed_diff, candidate_wrong, fixed_wrong = [], 0, 0
        for seed in per_seed:
            c = seed["conditions"][condition]
            a = c["decoders"][candidate]["residual_errors"]
            b = c["decoders"]["fixed_nominal"]["residual_errors"]
            per_seed_diff.append((a-b)/c["shots"])
            candidate_wrong += c["decoders"][candidate]["candidate_only_wrong"]
            fixed_wrong += c["decoders"][candidate]["fixed_only_wrong"]
        st = sign_test(per_seed_diff)
        mc = mcnemar(candidate_wrong, fixed_wrong, aggregate[condition][candidate]["shots"])
        secondary.append({"condition": condition, "candidate": candidate,
                          "seed_level_differences": per_seed_diff,
                          "mean_seed_level_difference": float(np.mean(per_seed_diff)),
                          "seed_sign_test_p": st["exact_two_sided_sign_test_p"],
                          "seed_sign_test_counts": st,
                          "pooled_mcnemar_p": mc["exact_two_sided_mcnemar_p"],
                          "pooled_mcnemar": mc})
    seed_adj = holm_adjust([x["seed_sign_test_p"] for x in secondary])
    shot_adj = holm_adjust([x["pooled_mcnemar_p"] for x in secondary])
    for i, item in enumerate(secondary):
        item["seed_sign_test_holm_p"] = seed_adj[i]
        item["pooled_mcnemar_holm_p"] = shot_adj[i]

    stats = {"primary": primary, "secondary_family_size": len(secondary), "secondary": secondary,
             "secondary_adjustments": "Holm step-down, separately for seed sign tests and pooled exact McNemar tests",
             "seed_unit_warning": "Pooled shot tests are dependent within seed and are complementary only; seed-level inference is primary."}
    csv_path = ROOT / "per_seed_results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    (ROOT/"statistical_analysis.json").write_text(json.dumps(stats, indent=2)+"\n", encoding="utf-8")

    result = {"experiment_id": CFG["experiment_id"], "protocol_sha256": CFG["protocol_sha256"],
              "config": CFG, "software": {"python": platform.python_version(), "stim": stim.__version__,
                                             "pymatching": pymatching.__version__, "numpy": np.__version__},
              "integrity": {"phase3a_runner_sha256": sha256(PHASE3A_RUNNER),
                            "phase3a_v4_result_sha256": sha256(PHASE3A_RESULT),
                            "ideal_circuit_zero_check_passed": ideal_ok,
                            "common_structure_hashes": {k: v["ideal_structure_sha256"] for k,v in metadata.items()},
                            "detector_shot_hashes": shot_hash_audit,
                            "aggregate_counts_equal_seed_sums": True},
              "model_metadata": metadata, "raw_observable_errors": raw_errors,
              "aggregate_by_condition": aggregate, "per_seed": per_seed,
              "primary_statistical_analysis": primary, "secondary_statistical_analysis": secondary,
              "mean_runtime_seconds_per_shot": {k: float(np.mean(v)) for k,v in timings.items()},
              "raw_files": raw_entries}
    result_path = ROOT / "RESULTS.json"
    result_path.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    make_plots(per_seed, aggregate, PLOT_DIR)
    manifest = {"protocol_sha256": sha256(PROTOCOL_PATH), "config_sha256": sha256(ROOT/"CONFIG.json"),
                "runner_sha256": sha256(ROOT/"run_phase3b_replication.py"),
                "phase3a_runner_sha256": sha256(PHASE3A_RUNNER), "phase3a_v4_result_sha256": sha256(PHASE3A_RESULT),
                "raw_files": raw_entries,
                "deliverable_files": {p.name: sha256(p) for p in [result_path, csv_path, ROOT/"statistical_analysis.json",
                                      PLOT_DIR/"primary_seed_differences.png", PLOT_DIR/"decoder_error_rates.png"]}}
    (ROOT/"SHA256_MANIFEST.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    print("Replication complete; wrote RESULTS.json and integrity manifest.")


def make_plots(per_seed, aggregate, plot_dir):
    c = CFG["primary_condition"]
    deltas = np.asarray([(s["conditions"][c]["decoders"]["x_biased_specialist"]["residual_errors"]-
                          s["conditions"][c]["decoders"]["fixed_nominal"]["residual_errors"])/
                         s["conditions"][c]["shots"] for s in per_seed]) * 100
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.axhline(0, color="black", linewidth=1)
    ax.scatter(np.arange(1, len(deltas)+1), deltas, color="#d95f02", label="Seed-level paired difference")
    ci = np.asarray(bootstrap_mean_ci(list(deltas/100))) * 100
    mean = float(deltas.mean())
    ax.errorbar([len(deltas)+1], [mean], yerr=[[mean-ci[0]], [ci[1]-mean]], fmt="D", color="#1b6ca8",
                capsize=4, label="Mean and seed-bootstrap 95% CI")
    ax.set_xticks(range(1, len(deltas)+2), [str(i) for i in range(1,len(deltas)+1)]+["Mean"])
    ax.set_xlabel("Independent seed replicate"); ax.set_ylabel("X specialist − fixed (percentage points)")
    ax.set_title("Primary paired seed-level residual error difference")
    ax.grid(axis="y", alpha=.25); ax.legend(); fig.tight_layout()
    fig.savefig(plot_dir/"primary_seed_differences.png", dpi=180); plt.close(fig)

    models = DECODERS
    labels = ["Fixed", "X specialist", "Z specialist", "Depolarizing specialist", "Noise-informed oracle"]
    conditions = list(aggregate)
    fig, ax = plt.subplots(figsize=(11, 5.5)); x = np.arange(len(conditions)); width=.15
    for j, (model,label) in enumerate(zip(models,labels)):
        rates = np.asarray([aggregate[cond][model]["residual_rate"] for cond in conditions])
        cis = np.asarray([aggregate[cond][model]["wilson95"] for cond in conditions])
        pos=x+(j-2)*width; ax.bar(pos,rates,width,label=label)
        ax.errorbar(pos,rates,yerr=np.vstack([np.maximum(0,rates-cis[:,0]),np.maximum(0,cis[:,1]-rates)]),
                    fmt="none",ecolor="black",capsize=2,linewidth=.7)
    ax.set_xticks(x,conditions,rotation=18,ha="right"); ax.set_ylabel("Residual logical-observable error rate")
    ax.set_title("Phase 3B paired decoder error rates; Wilson 95% intervals")
    ax.legend(fontsize=8); ax.grid(axis="y",alpha=.25); fig.tight_layout()
    fig.savefig(plot_dir/"decoder_error_rates.png",dpi=180); plt.close(fig)


if __name__ == "__main__":
    run()
