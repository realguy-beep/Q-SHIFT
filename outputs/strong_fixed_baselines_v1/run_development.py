"""Execute/resume the prespecified 3.66M-shot development comparison."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

import numpy as np

from experiment_core import (
    acquire_exclusive_lock, atomic_json, atomic_npz, build_models,
    current_rss_bytes, detector_profile_estimator, make_circuit,
    root_errors, sample_arrays, sha256,
    safety_validation_accept, select_safety_constrained_static,
    dem_kwargs,
    decode_candidate_grid,
)
from freeze_pretest import HERE, ROOT, verify_freeze


CONFIG_PATH = HERE / "experiment_config.json"
INVENTORY_PATH = HERE / "seed_inventory.json"


def pkey(p: float) -> str:
    return f"p_{float(p):.3f}"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_seed_allocation(cfg: dict, inventory: dict) -> None:
    streams = inventory.get("streams", [])
    seeds = [int(row["seed"]) for row in streams]
    if len(seeds) != len(set(seeds)) or inventory.get("collisions"):
        raise RuntimeError("seed inventory uniqueness/collision check failed")
    planned = sum(int(row["shots"]) for row in streams if row.get("included_in_allocation"))
    if planned != int(cfg["allocation"]["unique_shots"]):
        raise RuntimeError(f"seed inventory sample allocation mismatch: {planned}")
    if planned != int(inventory.get("expected_unique_shots", -1)):
        raise RuntimeError("inventory's allocation declaration disagrees with stream records")
    if int(inventory.get("sampling_stream_count", -1)) != sum(
        row["role"] in {"profile_template", "calibration", "scoring", "evaluation"} for row in streams
    ):
        raise RuntimeError("sampling stream count does not reconcile")
    if inventory.get("sampling_performed") is not False or inventory.get("sealed_test_access") is not False:
        raise RuntimeError("invalid seed inventory provenance state")


def nonzero_condition_probabilities(values) -> list[float]:
    """Return the frozen positive burst conditions without iterator slicing."""
    return [float(p) for p in values if float(p) > 0.0]


def stream_for(inventory: dict, role: str, split: str, p: float | None = None,
               root: int | None = None) -> dict:
    found = [s for s in inventory["streams"]
             if s["role"] == role and s["split"] == split
             and s["root"] == root
             and (s["probability"] is None if p is None else float(s["probability"]) == float(p))]
    if len(found) != 1:
        raise RuntimeError(f"seed inventory expected one stream for {role}/{split}/{p}/{root}; got {len(found)}")
    return found[0]


def acquire_run_lock(path: Path) -> int:
    try:
        return acquire_exclusive_lock(path)
    except FileExistsError as e:
        try:
            owner = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            owner = {"unreadable": True}
        raise RuntimeError(f"run lock exists; fail closed and inspect owner before resume: {owner}") from e


def health(cfg: dict, start_epoch: float) -> None:
    if time.time() - start_epoch > float(cfg["resources"]["wall_seconds_max"]):
        raise TimeoutError("two-hour wall-clock limit exceeded")
    if current_rss_bytes() > int(cfg["resources"]["rss_bytes_max"]):
        raise MemoryError("configured 2 GiB RSS limit exceeded")
    free = shutil.disk_usage(HERE.anchor).free
    if free < int(cfg["resources"]["free_disk_min_bytes"]):
        raise OSError("free disk reserve below configured 5 GiB")


def archive_path(run_dir: Path, partition: str, p: float | None, root: int | None) -> Path:
    if partition == "templates":
        return run_dir / "templates" / f"{pkey(float(p))}.npz"
    return run_dir / partition / pkey(float(p)) / f"root_{int(root):03d}.npz"


def checkpoint(run_dir: Path, partition: str, p: float | None, root: int | None,
               seed_row: dict, arrays: dict[str, np.ndarray], extra: dict | None = None) -> Path:
    path = archive_path(run_dir, partition, p, root)
    marker = path.with_suffix(path.suffix + ".commit.json")
    if path.exists() or marker.exists():
        if not (path.exists() and marker.exists()):
            raise RuntimeError(f"ambiguous archive/commit-marker state: {path}")
        saved = read_json(marker)
        if saved.get("sha256") != sha256(path):
            raise RuntimeError(f"checkpoint hash mismatch: {path}")
        with np.load(path, allow_pickle=False) as z:
            meta = json.loads(str(z["metadata_json"].item()))
        expected = {"partition": partition, "probability": p, "root": root,
                    "seed": int(seed_row["seed"]), "shots": int(seed_row.get("shots") or arrays.get("detectors", np.empty((0,))).shape[0])}
        for key, value in expected.items():
            if meta.get(key) != value:
                raise RuntimeError(f"checkpoint metadata mismatch {key}: {path}")
        return path
    meta = {"partition": partition, "probability": p, "root": root,
            "seed": int(seed_row["seed"]),
            "shots": int(seed_row.get("shots") or arrays["detectors"].shape[0])}
    if extra:
        meta.update(extra)
    arrays = dict(arrays)
    arrays["metadata_json"] = np.asarray(json.dumps(meta, sort_keys=True))
    digest = atomic_npz(path, **arrays)
    atomic_json(marker, {"schema_version": 1, "sha256": digest, "metadata": meta})
    return path


def load_checkpoint(path: Path, *, partition: str, p: float | None,
                    root: int | None, seed: int) -> tuple[dict, dict]:
    marker_path = path.with_suffix(path.suffix + ".commit.json")
    if not (path.is_file() and marker_path.is_file()):
        raise RuntimeError(f"checkpoint not committed: {path}")
    marker = read_json(marker_path)
    digest = sha256(path)
    if marker.get("sha256") != digest:
        raise RuntimeError(f"checkpoint digest mismatch: {path}")
    with np.load(path, allow_pickle=False) as z:
        arrays = {k: z[k] for k in z.files}
    meta = json.loads(str(arrays.pop("metadata_json").item()))
    if marker.get("metadata") != meta:
        raise RuntimeError(f"checkpoint commit-marker metadata mismatch: {path}")
    if (meta.get("partition"), meta.get("probability"), meta.get("root"), meta.get("seed")) != (partition, p, root, int(seed)):
        raise RuntimeError(f"checkpoint identity mismatch: {path}")
    return arrays, meta


def ensure_archive(run_dir: Path, partition: str, p: float, root: int | None,
                   seed_row: dict, sampler, cfg: dict, extra: dict | None = None) -> Path:
    path = archive_path(run_dir, partition, p, root)
    marker = path.with_suffix(path.suffix + ".commit.json")
    if path.exists() or marker.exists():
        load_checkpoint(path, partition=partition, p=p, root=root, seed=int(seed_row["seed"]))
        return path
    shots = int(seed_row["shots"] or cfg["decoders"].get("calibration_shots_per_root"))
    if sampler == "calibration":
        detectors = sample_arrays(p, int(seed_row["seed"]), shots, cfg, labels=False)
        arrays = {"detectors": detectors}
    else:
        detectors, observable = sample_arrays(p, int(seed_row["seed"]), shots, cfg, labels=True)
        arrays = {"detectors": detectors, "observable": observable}
    return checkpoint(run_dir, partition, p, root, seed_row, arrays, extra)


def read_data(path: Path, part: str, p: float, root: int, seed: int) -> dict:
    arrays, _ = load_checkpoint(path, partition=part, p=p, root=root, seed=seed)
    return arrays


def bootstrap_upper(differences: np.ndarray, seed: int, replicates: int = 100_000) -> float:
    x = np.asarray(differences, dtype=np.float64)
    if x.ndim != 1 or x.size < 2:
        raise ValueError("root differences must be a vector with at least two roots")
    rng = np.random.Generator(np.random.PCG64(int(seed)))
    draws = np.empty(replicates, dtype=np.float64)
    batch = 2_000
    for start in range(0, replicates, batch):
        n = min(batch, replicates - start)
        idx = rng.integers(0, x.size, size=(n, x.size))
        draws[start:start+n] = x[idx].mean(axis=1)
    return float(np.quantile(draws, 0.95, method="linear"))


def score_grid_dataset(run_dir: Path, partition: str, p_values: list[float], roots: int,
                       cfg: dict, inventory: dict, model_cache: dict, started: float) -> tuple[list[dict], dict]:
    per_root: list[dict] = []
    candidate_probabilities = [float(q) for q in model_cache]
    sums = {q: {"errors": 0, "shots": 0} for q in candidate_probabilities}
    for p in p_values:
        for root in range(roots):
            health(cfg, started)
            cal_seed = stream_for(inventory, "calibration", partition, p, root)
            eval_seed = stream_for(inventory, "scoring", partition, p, root)
            cal_path = archive_path(run_dir, partition + "_calibration", p, root)
            # Calibration and scoring are separate archive namespaces.
            ensure_archive(run_dir, partition + "_calibration", p, root, cal_seed, "calibration", cfg)
            ensure_archive(run_dir, partition, p, root, eval_seed, "scoring", cfg)
            record_latest_checkpoint(run_dir, partition, started, p, root,
                                     archive_path(run_dir, partition, p, root))
            data = read_data(archive_path(run_dir, partition, p, root), partition, p, root, int(eval_seed["seed"]))
            d, o = data["detectors"], data["observable"]
            decoded_probabilities, predictions = decode_candidate_grid(d, model_cache)
            if decoded_probabilities != candidate_probabilities:
                raise RuntimeError("candidate grid order changed while scoring paired samples")
            errors = (predictions ^ o[None, :]).sum(axis=1).astype(int)
            per_root.append({"partition": partition, "probability": float(p), "root": root,
                             "shots": int(o.size), "errors_by_grid": errors.tolist()})
            for i, q in enumerate(candidate_probabilities):
                sums[float(q)]["errors"] += int(errors[i])
                sums[float(q)]["shots"] += int(o.size)
            # Persist all candidate outputs for independent reconstruction.
            path = archive_path(run_dir, partition, p, root)
            arrays = {"detectors": d, "observable": o, "candidate_predictions": predictions}
            # Archive is initially written without predictions. Replace only via a separate immutable evidence file.
            pred_path = path.with_name(path.stem + "_candidate_predictions.npz")
            pred_seed = {**eval_seed, "shots": int(o.size)}
            checkpoint(run_dir, partition + "_predictions", p, root, pred_seed,
                       {"detectors": d, "observable": o, "candidate_predictions": predictions},
                       {"source_archive_sha256": sha256(path)})
    return per_root, sums


def load_template_estimator(run_dir: Path, cfg: dict, inventory: dict, started: float):
    batches = []
    for p in cfg["decoders"]["profile_template_probabilities"]:
        health(cfg, started)
        seed = stream_for(inventory, "profile_template", "templates", float(p), None)
        entry = next(s for s in inventory["streams"] if s["role"] == "profile_template" and float(s["probability"]) == float(p))
        shots = int(cfg["partitions"]["template_shots_per_probability"])
        path = archive_path(run_dir, "templates", p, None)
        if path.exists() or path.with_suffix(path.suffix + ".commit.json").exists():
            arrays, _ = load_checkpoint(path, partition="templates", p=float(p), root=None, seed=int(seed["seed"]))
            d = arrays["detectors"]
        else:
            d = sample_arrays(float(p), int(seed["seed"]), shots, cfg, labels=False)
            checkpoint(run_dir, "templates", float(p), None, {**seed, "shots": shots}, {"detectors": d})
        batches.append((float(p), d))
    return detector_profile_estimator(batches)


def write_status(run_dir: Path, status: str, started: float, **extra) -> None:
    path = run_dir / "status.json"
    previous = read_json(path) if path.exists() else {}
    previous.update({"schema_version": 1, "status": status, "pid": os.getpid(),
                     "started_unix": started, "updated_unix": time.time(), **extra})
    atomic_json(path, previous)


def record_latest_checkpoint(run_dir: Path, phase: str, started: float,
                             p: float, root: int | None, path: Path) -> None:
    state_path = run_dir / "status.json"
    state = read_json(state_path)
    state.update({"status": state.get("status", "running"), "phase": phase,
                  "current_condition_probability": float(p), "current_root": root,
                  "latest_committed_checkpoint": str(path.relative_to(run_dir)),
                  "latest_committed_checkpoint_sha256": sha256(path),
                  "updated_unix": time.time(), "elapsed_seconds": time.time() - started})
    atomic_json(state_path, state)


def write_immutable_json(path: Path, value: dict) -> None:
    if path.exists():
        # JSON object keys are strings on disk; normalize the proposed Python
        # record through the same encoding before comparing (e.g. float keys).
        normalized = json.loads(json.dumps(value, sort_keys=True, allow_nan=False))
        if read_json(path) != normalized:
            raise RuntimeError(f"immutable frozen/run record mismatch: {path}")
    else:
        atomic_json(path, value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, default=HERE / "run")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    cfg, inv = read_json(CONFIG_PATH), read_json(INVENTORY_PATH)
    verify_freeze()
    validate_seed_allocation(cfg, inv)
    run_dir = args.run_dir.resolve()
    if run_dir.exists() and not args.resume:
        raise FileExistsError("run directory exists; pass --resume only after inspecting its status and checkpoints")
    run_dir.mkdir(parents=True, exist_ok=True)
    lock_path = run_dir / ".run.lock"
    lock_fd = acquire_run_lock(lock_path)
    started = time.time()
    status_path = run_dir / "status.json"
    if status_path.exists():
        saved_status = read_json(status_path)
        started = float(saved_status.get("started_unix", started))
    try:
        if time.time() - started > float(cfg["resources"]["wall_seconds_max"]):
            raise TimeoutError("two-hour wall-clock budget already elapsed")
        if not status_path.exists():
            write_status(run_dir, "running", started, completed_archives=0,
                         allocated_unique_shots=cfg["allocation"]["unique_shots"],
                         sampled_partition_shots=0, final_evaluation_shots=0)
        health(cfg, started)
        # Input circuit/DEM preflight is structural only: no study shots are sampled here.
        for p in [0.0, *map(float, cfg["circuit"]["probabilities"])]:
            c = make_circuit(p, cfg)
            dem = c.detector_error_model(**dem_kwargs(cfg))
            if dem.num_detectors != c.num_detectors or dem.num_observables != c.num_observables:
                raise RuntimeError("DEM/circuit observable structure mismatch")

        estimator = load_template_estimator(run_dir, cfg, inv, started)
        grid = list(map(float, cfg["decoders"]["static_candidate_grid"]))
        grid_models = build_models(grid)
        # Selection and validation are independent and scored on paired detector arrays.
        sel_roots, val_roots = int(cfg["partitions"]["selection_roots_per_condition"]), int(cfg["partitions"]["validation_roots_per_condition"])
        selection_rows, selection_totals = score_grid_dataset(run_dir, "selection", list(map(float, cfg["circuit"]["probabilities"])), sel_roots, cfg, inv, grid_models, started)
        selection_record = {"per_root": selection_rows, "totals": selection_totals}
        write_immutable_json(run_dir / "selection_scores.json", selection_record)
        p0 = float(cfg["circuit"]["probabilities"][0])
        by_condition = {}
        zero_p_lers = {}
        for q in grid:
            zero_p_lers[q] = np.asarray([
                r["errors_by_grid"][grid.index(q)] / r["shots"]
                for r in selection_rows if r["probability"] == p0
            ], dtype=np.float64)
        for p in nonzero_condition_probabilities(cfg["circuit"]["probabilities"]):
            by_condition[p] = {q: np.asarray([
                r["errors_by_grid"][grid.index(q)] / r["shots"]
                for r in selection_rows if r["probability"] == p
            ], dtype=np.float64) for q in grid}
        chosen, selection_diagnostics = select_safety_constrained_static(
            grid, zero_p_lers, by_condition,
            float(cfg["decoders"]["static_zero_burst_mean_harm_limit"]),
        )
        selection_p0_means = {q: float(zero_p_lers[q].mean()) for q in grid}
        zero_harm = {q: selection_diagnostics[q]["p0_harm"] for q in grid}
        prevalidation_choice = float(chosen)
        # Validation only assesses the selected candidate at p=0; it cannot reselect.
        if chosen == 0.0:
            val_upper = 0.0
            val_diffs = []
        else:
            # Generate/score validation grid data; all nine candidates are kept for audit.
            validation_rows, validation_totals = score_grid_dataset(run_dir, "validation", list(map(float, cfg["circuit"]["probabilities"])), val_roots, cfg, inv, grid_models, started)
            p0_rows = [r for r in validation_rows if r["probability"] == 0.0]
            j = grid.index(chosen)
            val_diffs = [r["errors_by_grid"][j] / r["shots"] - r["errors_by_grid"][0] / r["shots"] for r in p0_rows]
            boot_seed = stream_for(inv, "bootstrap_validation", "validation_analysis")["seed"]
            val_upper = bootstrap_upper(np.asarray(val_diffs), int(boot_seed), int(cfg["statistics"]["bootstrap_replicates"]))
            chosen, _accepted = safety_validation_accept(
                chosen, val_upper, float(cfg["decoders"]["validation_upper_bound_harm_limit"])
            )
        if chosen == 0.0 and not (run_dir / "validation_scores.json").exists():
            validation_rows, validation_totals = score_grid_dataset(run_dir, "validation", list(map(float, cfg["circuit"]["probabilities"])), val_roots, cfg, inv, grid_models, started)
            validation_record = {"per_root": validation_rows, "totals": validation_totals}
        elif chosen != 0.0:
            validation_record = {"per_root": validation_rows, "totals": validation_totals}
        else:
            validation_record = read_json(run_dir / "validation_scores.json")
        write_immutable_json(run_dir / "validation_scores.json", validation_record)
        safe_selection_freeze = {
            "created_before_final_evaluation_sampling": True,
            "chosen_probability": float(chosen),
            "selection_candidate_before_validation": prevalidation_choice,
            "validation_p0_root_differences": val_diffs,
            "validation_one_sided_95_upper": float(val_upper),
            "selection_mean_p0_ler_by_candidate": {str(k): v for k, v in selection_p0_means.items()},
            "selection_mean_p0_harm_by_candidate": {str(k): v for k, v in zero_harm.items()},
            "selection_nonzero_objective_by_candidate": {str(q): selection_diagnostics[q]["equal_nonzero_mean_ler"] for q in grid},
            "rule": "frozen selection objective and tie-break; validation only accepts or falls back to p=0",
            "bootstrap_seed": stream_for(inv, "bootstrap_validation", "validation_analysis")["seed"],
            "bootstrap_replicates": int(cfg["statistics"]["bootstrap_replicates"]),
        }
        write_immutable_json(run_dir / "BASELINE_SELECTION_FREEZE.json", safe_selection_freeze)

        # Final calibration detector pool. No observable labels are saved or used.
        eval_roots = int(cfg["partitions"]["evaluation_roots_per_condition"])
        final_cal_batches: list[tuple[float, np.ndarray]] = []
        cal_refs = []
        for p in map(float, cfg["circuit"]["probabilities"]):
            for root in range(eval_roots):
                health(cfg, started)
                seed = stream_for(inv, "calibration", "heldout_development", p, root)
                shots = int(cfg["decoders"]["calibration_shots_per_root"])
                path = archive_path(run_dir, "heldout_development_calibration", p, root)
                if not path.exists():
                    d = sample_arrays(p, int(seed["seed"]), shots, cfg, labels=False)
                    checkpoint(run_dir, "heldout_development_calibration", p, root, seed, {"detectors": d})
                arrays = read_data(path, "heldout_development_calibration", p, root, int(seed["seed"]))
                final_cal_batches.append((p, arrays["detectors"]))
                cal_refs.append({"probability": p, "root": root, "seed": int(seed["seed"]), "path": str(path.relative_to(run_dir)), "sha256": sha256(path)})
                record_latest_checkpoint(run_dir, "heldout_development_calibration", started, p, root, path)
        pooled_estimator = detector_profile_estimator(final_cal_batches)
        pooled_detectors = np.concatenate([d for _, d in final_cal_batches], axis=0)
        p_pool = pooled_estimator.estimate(pooled_detectors)
        if not (0.0 <= p_pool <= 0.02):
            raise RuntimeError("pooled detector-only estimate outside frozen profile range")
        pooled_cal_record = {"estimated_p": float(p_pool), "calibration_shots": int(pooled_detectors.shape[0]),
                            "calibration_archives": cal_refs,
                            "estimator": "frozen Stage 4 DetectorProfileEstimator; detectors and pair co-fire features only"}
        pooled_path = run_dir / "POOLED_CALIBRATION_FREEZE.json"
        if pooled_path.exists():
            old = read_json(pooled_path)
            if old != pooled_cal_record:
                raise RuntimeError("pooled calibration freeze differs on resume")
        else:
            atomic_json(pooled_path, pooled_cal_record)
        # Crucial order: all baseline choices are frozen before evaluation sampler invocation.
        eval_selection_freeze_path = run_dir / "FINAL_EVAL_SELECTION_FREEZE.json"
        eval_selection_freeze = {
            "created_before_final_evaluation_sampling": True,
            "experiment_config_sha256": sha256(CONFIG_PATH),
            "nominal_fixed_p": 0.0, "pooled_detector_static_p": float(p_pool),
            "safety_constrained_static_p": float(chosen),
            "decoder_arm_order": ["nominal_fixed", "pooled_detector_static", "safety_constrained_static", "adaptive_profile", "privileged_true_p"],
            "dem_conversion": dem_kwargs(cfg),
            "pymatching_correlations_enabled": bool(cfg["circuit"]["dem"]["enable_correlations"]),
            "adaptive_rule": "per-root detector-only estimate from that root's separate 2,000-shot calibration batch",
            "privileged_reference_rule": "true generating burst probability; diagnostic only and not deployable",
            "pooled_calibration_freeze_sha256": sha256(pooled_path),
            "baseline_selection_freeze_sha256": sha256(run_dir / "BASELINE_SELECTION_FREEZE.json"),
            "all_eval_calibration_archive_hashes": cal_refs,
        }
        if eval_selection_freeze_path.exists():
            if read_json(eval_selection_freeze_path) != eval_selection_freeze:
                raise RuntimeError("final evaluation selection freeze mismatch on resume")
        else:
            atomic_json(eval_selection_freeze_path, eval_selection_freeze)

        fixed_models = build_models([0.0, float(p_pool), float(chosen), *map(float, cfg["circuit"]["probabilities"])])
        profile_batches = [(float(p), d) for p, d in zip(
            cfg["decoders"]["profile_template_probabilities"],
            [read_data(archive_path(run_dir, "templates", p, None), "templates", float(p), None,
                       int(stream_for(inv, "profile_template", "templates", float(p), None)["seed"]))["detectors"]
             for p in cfg["decoders"]["profile_template_probabilities"]])]
        root_estimator = detector_profile_estimator(profile_batches)
        status = read_json(status_path)
        status.update({"status": "running_final_evaluation", "pooled_p": float(p_pool), "safe_static_p": float(chosen)})
        atomic_json(status_path, status)
        completed_eval = 0
        for p in map(float, cfg["circuit"]["probabilities"]):
            for root in range(eval_roots):
                seed = stream_for(inv, "evaluation", "heldout_development", p, root)
                path = archive_path(run_dir, "evaluation", p, root)
                marker = path.with_suffix(path.suffix + ".commit.json")
                if path.exists() or marker.exists():
                    load_checkpoint(path, partition="evaluation", p=p, root=root, seed=int(seed["seed"]))
                    completed_eval += 1
        for p in map(float, cfg["circuit"]["probabilities"]):
            for root in range(eval_roots):
                health(cfg, started)
                cal_seed = stream_for(inv, "calibration", "heldout_development", p, root)
                cal = read_data(archive_path(run_dir, "heldout_development_calibration", p, root),
                                "heldout_development_calibration", p, root, int(cal_seed["seed"]))["detectors"]
                p_hat = float(root_estimator.estimate(cal))
                eval_seed = stream_for(inv, "evaluation", "heldout_development", p, root)
                path = archive_path(run_dir, "evaluation", p, root)
                marker = path.with_suffix(path.suffix + ".commit.json")
                if path.exists() or marker.exists():
                    arrays, meta = load_checkpoint(path, partition="evaluation", p=p, root=root, seed=int(eval_seed["seed"]))
                    if not np.isclose(float(meta["p_hat"]), p_hat, rtol=0, atol=1e-12):
                        raise RuntimeError(f"saved p_hat changed from frozen calibration for {path}")
                else:
                    det, obs = sample_arrays(p, int(eval_seed["seed"]), int(cfg["decoders"]["evaluation_shots_per_root"]), cfg, labels=True)
                    pred_nominal = fixed_models[0.0].decode_batch(det).reshape(-1).astype(np.uint8)
                    pred_pooled = fixed_models[float(p_pool)].decode_batch(det).reshape(-1).astype(np.uint8)
                    pred_safe = fixed_models[float(chosen)].decode_batch(det).reshape(-1).astype(np.uint8)
                    if p_hat not in fixed_models:
                        fixed_models.update(build_models([p_hat]))
                    pred_adaptive = fixed_models[p_hat].decode_batch(det).reshape(-1).astype(np.uint8)
                    pred_privileged = fixed_models[p].decode_batch(det).reshape(-1).astype(np.uint8)
                    predictions = np.stack([pred_nominal, pred_pooled, pred_safe, pred_adaptive, pred_privileged])
                    arrays = {"detectors": det, "observable": obs, "predictions": predictions,
                              "p_hat": np.asarray(p_hat)}
                    checkpoint(run_dir, "evaluation", p, root, eval_seed, arrays,
                               {"p_hat": p_hat, "decoder_order": ["nominal_fixed", "pooled_detector_static", "safety_constrained_static", "adaptive_profile", "privileged_true_p"]})
                    completed_eval += 1
                if completed_eval % 10 == 0:
                    status = read_json(status_path)
                    status.update({"completed_evaluation_roots": completed_eval,
                                   "final_evaluation_shots_committed": completed_eval * int(cfg["decoders"]["evaluation_shots_per_root"]),
                                   "updated_unix": time.time()})
                    atomic_json(status_path, status)
        root_count = len(list(run_dir.glob("evaluation/*/root_*.npz")))
        expected_roots = len(cfg["circuit"]["probabilities"]) * eval_roots
        if root_count != expected_roots:
            raise RuntimeError(f"expected {expected_roots} final roots, found {root_count}")
        write_status(run_dir, "sampling_completed", started,
                     completed_evaluation_roots=root_count,
                     final_evaluation_shots_committed=root_count * int(cfg["decoders"]["evaluation_shots_per_root"]),
                     sampling_complete=True)
        print(json.dumps({"status": "SAMPLING_COMPLETE_AUDIT_PENDING", "run_dir": str(run_dir),
                          "final_evaluation_roots": root_count,
                          "final_evaluation_shots": root_count * int(cfg["decoders"]["evaluation_shots_per_root"]),
                          "total_unique_shots": cfg["allocation"]["unique_shots"]}, indent=2))
    except Exception as exc:
        write_status(run_dir, "failed", started, error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        os.close(lock_fd)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    main()
