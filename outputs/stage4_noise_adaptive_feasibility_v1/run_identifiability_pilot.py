"""Run only the frozen 48k-shot Stage 4 feasibility/identifiability pilot."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import statistics
import sys
import time
from pathlib import Path

import numpy as np
import pymatching
import stim

from outputs.stage4_noise_adaptive_feasibility_v1.freeze_stage4 import HERE, REPO, verify as verify_freeze
from outputs.stage4_noise_adaptive_feasibility_v1.prototype import (
    DetectorProfileEstimator,
    build_decoder,
    decode_prediction,
    logical_error_mask,
)
from outputs.phase3a_correlated_noise_preflight.simulator import build_spatial_burst_circuit

RAW = HERE / "run_v1"
CONFIG_PATH = HERE / "stage4_feasibility_config.json"
INVENTORY_PATH = HERE / "seed_inventory.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_npz(path: Path, **arrays) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as f:
        np.savez_compressed(f, **arrays)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def atomic_json(path: Path, value: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def get_seed(rows: list[dict], kind: str, *, p: float | None = None,
             replicate: int | None = None, root: int | None = None) -> int:
    found = []
    for r in rows:
        if r["kind"] != kind:
            continue
        if p is not None and float(r.get("probability", -1)) != p:
            continue
        if replicate is not None and r.get("replicate") != replicate:
            continue
        if root is not None and r.get("root") != root:
            continue
        found.append(int(r["seed"]))
    if len(found) != 1:
        raise RuntimeError(f"expected one seed for {kind}, p={p}, replicate={replicate}, root={root}; got {found}")
    return found[0]


def sample_detectors(probability: float, shots: int, seed: int):
    circuit = build_spatial_burst_circuit(memory_basis="z", regime="balanced", distance=3, rounds=5,
        gate_p=0.003, measurement_p=0.003, bias_ratio=10.0,
        burst_probability=probability, burst_pair=(8, 10))
    sample = circuit.compile_detector_sampler(seed=seed).sample(shots, separate_observables=False)
    d = np.asarray(sample, dtype=np.uint8)
    if d.shape != (shots, 40) or not np.isin(d, (0, 1)).all():
        raise RuntimeError(f"detector-only sample invalid: {d.shape}")
    return d


def sample_eval(probability: float, shots: int, seed: int):
    circuit = build_spatial_burst_circuit(memory_basis="z", regime="balanced", distance=3, rounds=5,
        gate_p=0.003, measurement_p=0.003, bias_ratio=10.0,
        burst_probability=probability, burst_pair=(8, 10))
    d, o = circuit.compile_detector_sampler(seed=seed).sample(shots, separate_observables=True)
    d, o = np.asarray(d, dtype=np.uint8), np.asarray(o, dtype=np.uint8).reshape(-1)
    if d.shape != (shots, 40) or o.shape != (shots,):
        raise RuntimeError(f"paired evaluation sample invalid: {d.shape}, {o.shape}")
    if not np.isin(d, (0, 1)).all() or not np.isin(o, (0, 1)).all():
        raise RuntimeError("sample contains nonbinary values")
    return d, o


def t_interval(values: list[float]) -> list[float] | None:
    if len(values) < 2:
        return None
    mean = statistics.mean(values)
    sd = statistics.stdev(values)
    # Small feasibility strata use n=3; critical value for df=2.
    critical = {1: 12.7062, 2: 4.3027, 3: 3.1824}.get(len(values) - 1)
    if critical is None:
        return None
    half = critical * sd / np.sqrt(len(values))
    return [mean - half, mean + half]


def run() -> dict:
    start = time.perf_counter()
    freeze_check = verify_freeze()
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    if cfg["status"] != "FROZEN_BEFORE_SAMPLING" or freeze_check["status"] != "PASS":
        raise RuntimeError("Stage 4 pre-sampling freeze validation failed")
    if inventory["independent_test_allocated"] or len(inventory["streams"]) != 19:
        raise RuntimeError("seed inventory unexpected or test stream allocated")
    if RAW.exists():
        raise RuntimeError("run_v1 already exists; refusing duplicate sampling or overwrite")
    RAW.mkdir(parents=True)
    (RAW / "samples").mkdir()
    rows = inventory["streams"]
    atomic_json(RAW / "status.json", {"status": "running", "unique_shots": 0, "independent_test_accessed": False})

    # Build and validate graphlike DEMs for every probability knot and the
    # unseen evaluation values before drawing any shots.
    p_all = sorted(set(cfg["estimator"]["profile_probabilities"] + cfg["pilot"]["unseen_evaluation_probabilities"] + [0.0]))
    dem_records = {}
    decoders = {}
    build_seconds = {}
    for p in p_all:
        t0 = time.perf_counter()
        circuit, dem, matcher = build_decoder(float(p))
        build_seconds[str(p)] = time.perf_counter() - t0
        decoders[float(p)] = matcher
        lines = [line for line in str(dem).splitlines() if line.startswith("error(")]
        burst = [line for line in lines if any(f"D{a} D{b}" in line for a, b in ((8,10),(16,18),(24,26),(32,34),(36,38)))]
        if p == 0.0:
            if burst:
                raise RuntimeError("zero-burst DEM unexpectedly contains burst mechanisms")
        elif len(burst) != 5 or not all(f"error({p:g})" in line for line in burst):
            raise RuntimeError(f"DEM does not encode five burst mechanisms at p={p}: {burst}")
        burst_edge_weights = []
        if p > 0:
            for a, b in ((8,10),(16,18),(24,26),(32,34),(36,38)):
                edge = matcher.get_edge_data(a, b)
                if edge is None or abs(float(edge["error_probability"]) - p) > 1e-12:
                    raise RuntimeError(f"PyMatching graph lost burst mechanism ({a},{b}) at p={p}: {edge}")
                burst_edge_weights.append({"detectors": [a, b], "error_probability": edge["error_probability"],
                                           "weight": edge["weight"]})
        dem_records[str(p)] = {
            "detectors": dem.num_detectors, "observables": dem.num_observables,
            "error_mechanisms": dem.num_errors, "pymatching_edges": matcher.num_edges,
            "burst_error_records": burst, "burst_edge_weights": burst_edge_weights,
            "dem_sha256": hashlib.sha256(str(dem).encode()).hexdigest(),
        }
    if any((v["detectors"], v["observables"]) != (40, 1) for v in dem_records.values()):
        raise RuntimeError("DEM shape changed across burst probabilities")

    profile_batches: list[tuple[float, np.ndarray]] = []
    profile_arrays: dict[str, np.ndarray] = {}
    sample_hashes = {}
    profile_ps = [float(p) for p in cfg["estimator"]["profile_probabilities"]]
    for p in profile_ps:
        for rep in range(2):
            seed = get_seed(rows, "profile_calibration_detectors", p=p, replicate=rep)
            d = sample_detectors(p, 2000, seed)
            name = f"profile_p{p:.3f}_rep{rep}"
            profile_arrays[name] = d
            profile_batches.append((p, d))
            sample_hashes[name] = hashlib.sha256(d.tobytes()).hexdigest()
            atomic_npz(RAW / "samples" / f"{name}.npz", detectors=d)
    estimator = DetectorProfileEstimator.fit(profile_batches)
    profile_means_json = {str(float(p)): estimator.means[i].tolist() for i, p in enumerate(estimator.probabilities)}
    scales_json = estimator.scales.tolist()
    profile_archive = RAW / "profile_calibration.npz"
    atomic_npz(profile_archive, **profile_arrays)

    # Fixed p=0 and a fixed p-mismatch grid are references. The true-p arm is
    # privileged and is included for feasibility only. All decode identical
    # detector rows and are scored against identical observable labels.
    mismatch_grid = [0.0, 0.002, 0.006, 0.010, 0.014, 0.018]
    for p in mismatch_grid:
        if p not in decoders:
            _, _, decoders[p] = build_decoder(p)
            build_seconds[f"{p}:mismatch_grid"] = 0.0
    per_root = []
    bootstrap_rng = np.random.default_rng(4100000019)
    eval_ps = [float(p) for p in cfg["pilot"]["unseen_evaluation_probabilities"]]
    decode_seconds = {"fixed": 0.0, "estimated": 0.0, "oracle": 0.0, "mismatch_grid": 0.0}
    for p in eval_ps:
        for root in range(3):
            cal_seed = get_seed(rows, "unseen_parameter_calibration_detectors", p=p, root=root)
            eval_seed = get_seed(rows, "unseen_parameter_paired_evaluation", p=p, root=root)
            cal = sample_detectors(p, 2000, cal_seed)
            d, obs = sample_eval(p, 4000, eval_seed)
            p_hat = estimator.estimate(cal)
            ci = estimator.bootstrap_interval(cal, rng=bootstrap_rng, replicates=500)
            _, _, estimated_decoder = build_decoder(p_hat)
            t0 = time.perf_counter(); pred_fixed = decode_prediction(decoders[0.0], d); decode_seconds["fixed"] += time.perf_counter() - t0
            t0 = time.perf_counter(); pred_est = decode_prediction(estimated_decoder, d); decode_seconds["estimated"] += time.perf_counter() - t0
            t0 = time.perf_counter(); pred_oracle = decode_prediction(decoders[p], d); decode_seconds["oracle"] += time.perf_counter() - t0
            mismatch = {}
            mismatch_preds = {}
            for q in mismatch_grid:
                t0 = time.perf_counter(); pred = decode_prediction(decoders[q], d); decode_seconds["mismatch_grid"] += time.perf_counter() - t0
                mismatch[str(q)] = int(np.count_nonzero(logical_error_mask(pred, obs)))
                mismatch_preds[f"prediction_p{q:.3f}"] = pred
            err_fixed = logical_error_mask(pred_fixed, obs)
            err_est = logical_error_mask(pred_est, obs)
            err_oracle = logical_error_mask(pred_oracle, obs)
            row = {
                "true_probability_for_analysis_only": p,
                "root": root,
                "calibration_seed": cal_seed,
                "evaluation_seed": eval_seed,
                "calibration_shots": int(len(cal)),
                "evaluation_shots": int(len(obs)),
                "estimated_probability": p_hat,
                "bootstrap_95_interval": ci,
                "absolute_estimation_error": abs(p_hat - p),
                "signed_estimation_error": p_hat - p,
                "fixed_nominal_errors": int(err_fixed.sum()),
                "estimated_model_errors": int(err_est.sum()),
                "oracle_errors": int(err_oracle.sum()),
                "estimated_candidate_only_failures": int(np.count_nonzero(err_est & ~err_fixed)),
                "estimated_fixed_only_failures": int(np.count_nonzero(~err_est & err_fixed)),
                "estimated_disagreements_with_fixed": int(np.count_nonzero(pred_est != pred_fixed)),
                "oracle_candidate_only_failures": int(np.count_nonzero(err_oracle & ~err_fixed)),
                "oracle_fixed_only_failures": int(np.count_nonzero(~err_oracle & err_fixed)),
                "oracle_disagreements_with_fixed": int(np.count_nonzero(pred_oracle != pred_fixed)),
                "mismatch_grid_errors": mismatch,
            }
            name = f"eval_p{p:.3f}_root{root}"
            arrays = {
                "calibration_detectors": cal,
                "evaluation_detectors": d,
                "observable": obs,
                "prediction_fixed": pred_fixed,
                "prediction_estimated": pred_est,
                "prediction_oracle": pred_oracle,
                **mismatch_preds,
            }
            sample_hashes[name] = hashlib.sha256(d.tobytes() + obs.tobytes()).hexdigest()
            atomic_npz(RAW / "samples" / f"{name}.npz", **arrays)
            row["evidence_file"] = f"samples/{name}.npz"
            row["evidence_sha256"] = sha256(RAW / "samples" / f"{name}.npz")
            per_root.append(row)
            atomic_json(RAW / "progress.json", {"status": "running", "completed_roots": len(per_root),
                "total_roots": 6, "completed_unique_shots": 12000 + len(per_root) * 6000,
                "independent_test_accessed": False})

    if len(per_root) != 6:
        raise RuntimeError("pilot did not complete all six unseen-parameter roots")
    aggregate = {}
    for p in eval_ps:
        subset = [r for r in per_root if r["true_probability_for_analysis_only"] == p]
        n = sum(r["evaluation_shots"] for r in subset)
        fixed = sum(r["fixed_nominal_errors"] for r in subset)
        est = sum(r["estimated_model_errors"] for r in subset)
        oracle = sum(r["oracle_errors"] for r in subset)
        diffs = [r["estimated_model_errors"] / r["evaluation_shots"] - r["fixed_nominal_errors"] / r["evaluation_shots"] for r in subset]
        aggregate[str(p)] = {
            "shots": n, "fixed_nominal_errors": fixed, "fixed_nominal_ler": fixed / n,
            "estimated_model_errors": est, "estimated_model_ler": est / n,
            "estimated_minus_fixed_ler": est / n - fixed / n,
            "estimated_root_paired_differences": diffs,
            "estimated_root_t_interval_descriptive": t_interval(diffs),
            "oracle_errors": oracle, "oracle_ler": oracle / n,
            "mean_estimated_probability": statistics.mean(r["estimated_probability"] for r in subset),
            "mean_absolute_probability_error": statistics.mean(r["absolute_estimation_error"] for r in subset),
            "mean_signed_probability_error": statistics.mean(r["signed_estimation_error"] for r in subset),
            "root_estimates": [r["estimated_probability"] for r in subset],
            "root_estimation_intervals": [r["bootstrap_95_interval"] for r in subset],
        }
    result = {
        "status": "FEASIBILITY_PILOT_COMPLETE",
        "scope": "48,000-shot development-only identifiability/DEM rebuild pilot; not full Stage 4 and not confirmatory",
        "freeze_verification": verify_freeze(),
        "unique_shots": 48000,
        "shot_accounting": {"profile_calibration": 12000, "unseen_parameter_calibration": 12000,
                            "paired_evaluation": 24000, "total": 48000},
        "profile_probabilities_seen_during_estimator_fit": profile_ps,
        "unseen_evaluation_probabilities": eval_ps,
        "estimator_feature_names": [f"detector_rate_D{i}" for i in range(40)] +
                                   [f"joint_D{a}_D{b}" for a,b in ((8,10),(16,18),(24,26),(32,34),(36,38))],
        "estimator_profile_means": profile_means_json,
        "estimator_feature_scales": scales_json,
        "paired_aggregate": aggregate,
        "per_root": per_root,
        "dem_models": dem_records,
        "runtime_seconds": {"total": time.perf_counter() - start, "decoder_build_by_probability": build_seconds,
                            "decode_seconds": decode_seconds},
        "software": {"python": platform.python_version(), "numpy": np.__version__,
                     "stim": stim.__version__, "pymatching": pymatching.__version__},
        "calibration_labels_accessed_by_estimator": False,
        "observable_labels_accessed_during_calibration": False,
        "true_probability_used_by_estimator": False,
        "true_probability_used_for_oracle_and_error_scoring_only": True,
        "same_paired_evaluation_samples_across_arms": True,
        "independent_test_accessed": False,
        "independent_test_enumerated": False,
        "bootstrap": {"method": "resample calibration rows with replacement and recompute profile estimate",
                      "replicates_per_root": 500, "seed": 4100000019,
                      "interval": "percentile 95%, diagnostic calibration uncertainty only"},
        "integrity": {"freeze_file_sha256": sha256(HERE / "STAGE4_FEASIBILITY_FREEZE.json"),
                      "profile_archive_sha256": sha256(profile_archive), "sample_array_hashes": sample_hashes},
        "limitations": [
            "Only two unseen probability values and three independent roots per value; all performance intervals are descriptive.",
            "Estimator templates use known development probabilities, which are not available to estimator inference; they are used only to fit the profile map.",
            "Synthetic burst process is independent Bernoulli XX events at five fixed sites, not calibrated to hardware.",
            "DEM conversion inherits approximate_disjoint_errors=True for categorical PAULI_CHANNEL_2 channels.",
            "Matching probabilities are reconstructed by rebuilding Stim DEM and PyMatching; no direct arbitrary CNN-to-matching weight path is used.",
        ],
    }
    atomic_json(HERE / "STAGE4_FEASIBILITY_PILOT_RESULTS.json", result)
    with (HERE / "STAGE4_FEASIBILITY_PILOT_PER_ROOT.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["true_probability_for_analysis_only", "root", "calibration_shots", "evaluation_shots",
                  "estimated_probability", "bootstrap_95_interval", "absolute_estimation_error",
                  "fixed_nominal_errors", "estimated_model_errors", "oracle_errors",
                  "estimated_candidate_only_failures", "estimated_fixed_only_failures",
                  "estimated_disagreements_with_fixed", "oracle_candidate_only_failures",
                  "oracle_fixed_only_failures", "oracle_disagreements_with_fixed"]
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in per_root:
            w.writerow({k: r.get(k) for k in fields})
    atomic_json(RAW / "status.json", {"status": "completed", "unique_shots": 48000,
                                      "completed_roots": 6, "independent_test_accessed": False,
                                      "results_sha256": sha256(HERE / "STAGE4_FEASIBILITY_PILOT_RESULTS.json")})
    print(json.dumps({"status": result["status"], "unique_shots": result["unique_shots"],
                      "aggregate": aggregate, "runtime_seconds": result["runtime_seconds"]["total"]}, indent=2))
    return result


if __name__ == "__main__":
    run()

