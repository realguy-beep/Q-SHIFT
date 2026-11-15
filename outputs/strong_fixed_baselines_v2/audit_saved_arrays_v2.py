"""Independent, read-only audit of a completed V2 run's saved arrays.

This module never imports the V2 runner or its reporting code and never samples.
It reimplements the small detector-profile estimator, verifies committed arrays,
re-decodes paired samples, reconstructs the safety-static choice, and writes an
audit result outside the supplied run directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from outputs.strong_fixed_baselines_v1.experiment_core import build_models

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PAIRS = ((8, 10), (16, 18), (24, 26), (32, 34), (36, 38))
REQUIRED_FREEZE_FILES = {
    "outputs/strong_fixed_baselines_v2/experiment_config_v2.json",
    "outputs/strong_fixed_baselines_v2/seed_inventory_v2_r2.json",
    "outputs/strong_fixed_baselines_v2/run_development_v2.py",
    "outputs/strong_fixed_baselines_v2/pooled_calibration_v2.py",
    "outputs/strong_fixed_baselines_v2/prepare_seed_inventory_v2.py",
    "outputs/strong_fixed_baselines_v2/audit_saved_arrays_v2.py",
    "outputs/strong_fixed_baselines_v2/freeze_pretest_v2.py",
    "outputs/strong_fixed_baselines_v2/create_pretest_freeze_v2.py",
    "outputs/strong_fixed_baselines_v2/test_pooled_calibration_v2.py",
    "outputs/strong_fixed_baselines_v2/test_saved_array_audit_v2.py",
    "outputs/strong_fixed_baselines_v2/test_seed_inventory_v2.py",
    "outputs/strong_fixed_baselines_v2/PROSPECTIVE_REPLICATION_PLAN_V2.md",
    "outputs/strong_fixed_baselines_v2/FAIRNESS_AND_LEAKAGE_REVIEW_V2.md",
    "outputs/strong_fixed_baselines_v2/INDEPENDENT_AUDIT_PLAN_V2.md",
    "outputs/strong_fixed_baselines_v2/SEED_COLLISION_AUDIT_V2.md",
    "outputs/strong_fixed_baselines_v2/README.md",
    "outputs/strong_fixed_baselines_v1/experiment_core.py",
    "outputs/phase3a_correlated_noise_preflight/simulator.py",
    "outputs/stage4_noise_adaptive_feasibility_v1/prototype.py",
    "outputs/stage5_secondary_inference_repair_v1/STAGE5_SAMPLE_SEED_INVENTORY.json",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_binary(name: str, value: Any, shape: tuple[int, ...] | None = None) -> np.ndarray:
    array = np.asarray(value)
    if shape is not None and array.shape != shape:
        raise ValueError(f"{name} shape {array.shape}, expected {shape}")
    if array.dtype.kind not in "bui" or not np.isin(array, (0, 1)).all():
        raise ValueError(f"{name} must contain binary integer values")
    return array.astype(np.uint8, copy=False)


def verify_archive(
    path: Path,
    *,
    expected_partition: str,
    expected_probability: float | None,
    expected_root: int | None,
    expected_seed: int,
    expected_shots: int,
    expected_arrays: set[str],
) -> tuple[dict[str, np.ndarray], dict]:
    """Verify marker, hash, archive identity and common detector dimensions."""
    marker_path = path.with_suffix(path.suffix + ".commit.json")
    if not path.is_file() or not marker_path.is_file():
        raise RuntimeError(f"archive/commit marker is missing: {path}")
    marker = read_json(marker_path)
    digest = sha256(path)
    if marker.get("sha256") != digest:
        raise RuntimeError(f"archive SHA-256 mismatch: {path}")
    with np.load(path, allow_pickle=False) as archive:
        if "metadata_json" not in archive.files:
            raise RuntimeError(f"archive metadata_json missing: {path}")
        arrays = {key: archive[key] for key in archive.files if key != "metadata_json"}
        metadata = json.loads(str(archive["metadata_json"].item()))
    if marker.get("metadata") != metadata:
        raise RuntimeError(f"commit marker metadata mismatch: {path}")
    if set(arrays) != expected_arrays:
        raise RuntimeError(f"archive arrays {sorted(arrays)} != expected {sorted(expected_arrays)}: {path}")
    if metadata.get("partition") != expected_partition:
        raise RuntimeError(f"archive partition mismatch: {path}")
    if metadata.get("root") != expected_root or metadata.get("seed") != int(expected_seed):
        raise RuntimeError(f"archive root/seed mismatch: {path}")
    if metadata.get("shots") != int(expected_shots):
        raise RuntimeError(f"archive shot-count metadata mismatch: {path}")
    saved_p = metadata.get("probability")
    if expected_probability is None:
        if saved_p is not None:
            raise RuntimeError(f"archive unexpectedly has a probability: {path}")
    elif saved_p is None or not math.isclose(float(saved_p), float(expected_probability), rel_tol=0, abs_tol=1e-15):
        raise RuntimeError(f"archive probability mismatch: {path}")
    detectors = validate_binary("detectors", arrays["detectors"], (expected_shots, 40))
    arrays["detectors"] = detectors
    if "observable" in arrays:
        arrays["observable"] = validate_binary("observable", arrays["observable"], (expected_shots,))
    return arrays, metadata


def detector_features(detectors: np.ndarray) -> np.ndarray:
    d = validate_binary("detector features", detectors)
    if d.ndim != 2 or d.shape[1] != 40:
        raise ValueError("detectors must have shape (shots,40)")
    pairs = np.stack([d[:, left] & d[:, right] for left, right in PAIRS], axis=1)
    return np.concatenate((d, pairs), axis=1).astype(np.uint8, copy=False)


def fit_reference_profiles(template_batches: list[tuple[float, np.ndarray]]) -> dict:
    """Independent calculation of template means and pooled feature scales."""
    if len(template_batches) < 2:
        raise ValueError("at least two independent template probabilities are required")
    groups: dict[float, list[np.ndarray]] = {}
    all_features = []
    for probability, detectors in template_batches:
        p = float(probability)
        features = detector_features(detectors).astype(np.float64)
        if features.shape[0] < 2:
            raise ValueError("each template batch needs at least two shots")
        groups.setdefault(p, []).append(features)
        all_features.append(features)
    probabilities = np.asarray(sorted(groups), dtype=np.float64)
    if probabilities.size < 2:
        raise ValueError("template probabilities must be distinct")
    means = np.stack([np.concatenate(groups[float(p)], axis=0).mean(axis=0) for p in probabilities])
    pooled = np.concatenate(all_features, axis=0)
    scales = np.sqrt(np.maximum(pooled.var(axis=0), 1e-6))
    return {"probabilities": probabilities, "means": means, "scales": scales}


def estimate_probability(profile: dict, calibration_detectors: np.ndarray, grid_step: float) -> float:
    features = detector_features(calibration_detectors).astype(np.float64)
    if features.shape[0] < 2:
        raise ValueError("calibration needs at least two detector shots")
    knots = profile["probabilities"]
    means = profile["means"]
    scales = profile["scales"]
    count = int(round((float(knots[-1]) - float(knots[0])) / float(grid_step))) + 1
    grid = np.linspace(float(knots[0]), float(knots[-1]), max(2, count), dtype=np.float64)
    expected = np.column_stack([
        np.interp(grid, knots, means[:, column]) for column in range(means.shape[1])
    ])
    observed = features.mean(axis=0)
    scores = np.mean(((expected - observed[None, :]) / scales[None, :]) ** 2, axis=1)
    return float(grid[int(np.argmin(scores))])


def archive_path(run_dir: Path, partition: str, probability: float, root: int | None) -> Path:
    if partition == "templates":
        return run_dir / "templates" / f"p_{float(probability):.3f}.npz"
    return run_dir / partition / f"p_{float(probability):.3f}" / f"root_{int(root):03d}.npz"


def find_stream(inventory: dict, role: str, split: str, probability: float | None = None,
                root: int | None = None) -> dict:
    found = [row for row in inventory["streams"]
             if row["role"] == role and row["split"] == split and row["root"] == root
             and (row["probability"] is None if probability is None
                  else float(row["probability"]) == float(probability))]
    if len(found) != 1:
        raise RuntimeError(f"inventory stream is not unique for {role}/{split}/{probability}/{root}")
    return found[0]


def committed_archive(run_dir: Path, inventory: dict, partition: str, role: str,
                      split: str, probability: float, root: int,
                      arrays: set[str]) -> tuple[Path, dict[str, np.ndarray], dict]:
    seed_row = find_stream(inventory, role, split, probability, root)
    path = archive_path(run_dir, partition, probability, root)
    payload, metadata = verify_archive(
        path,
        expected_partition=partition,
        expected_probability=probability,
        expected_root=root,
        expected_seed=int(seed_row["seed"]),
        expected_shots=int(seed_row["shots"]),
        expected_arrays=arrays,
    )
    return path, payload, metadata


def decoder_prediction(model_cache: dict[float, Any], probability: float, detectors: np.ndarray) -> np.ndarray:
    p = float(probability)
    if p not in model_cache:
        model_cache[p] = build_models([p])[p]
    prediction = np.asarray(model_cache[p].decode_batch(detectors)).reshape(-1)
    return validate_binary("decoder prediction", prediction, (detectors.shape[0],))


def decode_grid(detectors: np.ndarray, grid: list[float], models: dict[float, Any]) -> np.ndarray:
    return np.stack([decoder_prediction(models, p, detectors) for p in grid]).astype(np.uint8)


def root_errors(prediction: np.ndarray, observable: np.ndarray) -> int:
    pred = validate_binary("prediction", prediction, observable.shape)
    obs = validate_binary("observable", observable)
    return int(np.sum(pred ^ obs))


def bootstrap_upper(values: np.ndarray, seed: int, replicates: int) -> float:
    x = np.asarray(values, dtype=np.float64)
    if x.ndim != 1 or x.size < 2:
        raise ValueError("at least two root-level differences are required")
    rng = np.random.Generator(np.random.PCG64(int(seed)))
    result = np.empty(int(replicates), dtype=np.float64)
    for start in range(0, int(replicates), 2000):
        n = min(2000, int(replicates) - start)
        idx = rng.integers(0, x.size, size=(n, x.size))
        result[start:start + n] = x[idx].mean(axis=1)
    return float(np.quantile(result, 0.95, method="linear"))


def selection_from_rows(grid: list[float], rows: list[dict], zero_harm_limit: float) -> tuple[float, dict]:
    p0_rows = [row for row in rows if float(row["probability"]) == 0.0]
    conditions = sorted({float(row["probability"]) for row in rows if float(row["probability"]) > 0})
    if len(p0_rows) < 2 or not conditions:
        raise RuntimeError("selection partition lacks required independent roots/conditions")
    zero_means = {}
    diagnostics = {}
    for j, q in enumerate(grid):
        p0_lers = np.asarray([r["errors_by_grid"][j] / r["shots"] for r in p0_rows], dtype=np.float64)
        zero_means[q] = p0_lers
    reference_mean = float(zero_means[0.0].mean())
    eligible = []
    for j, q in enumerate(grid):
        harm = float(zero_means[q].mean() - reference_mean)
        condition_means = []
        for p in conditions:
            condition_rows = [r for r in rows if float(r["probability"]) == p]
            lers = [r["errors_by_grid"][j] / r["shots"] for r in condition_rows]
            condition_means.append(float(np.mean(lers)))
        objective = float(np.mean(condition_means))
        diagnostics[q] = {"p0_harm": harm, "equal_nonzero_mean_ler": objective}
        if harm <= float(zero_harm_limit):
            eligible.append((objective, q))
    selected = min(eligible, key=lambda pair: (pair[0], pair[1]))[1] if eligible else 0.0
    return selected, diagnostics


def score_grid_partition(run_dir: Path, inventory: dict, config: dict, partition: str,
                         roots: int, grid: list[float]) -> list[dict]:
    probabilities = list(map(float, config["circuit"]["probabilities"]))
    models: dict[float, Any] = {}
    rows = []
    for p in probabilities:
        for root in range(roots):
            # The runner allocates these detector-only streams alongside each
            # scoring root. Verify them even though the fixed candidate grid
            # does not estimate from them.
            committed_archive(
                run_dir, inventory, partition + "_calibration", "calibration", partition,
                p, root, {"detectors"},
            )
            _, scored, _ = committed_archive(
                run_dir, inventory, partition, "scoring", partition, p, root,
                {"detectors", "observable"},
            )
            prediction_path, stored, prediction_meta = committed_archive(
                run_dir, inventory, partition + "_predictions", "scoring", partition, p, root,
                {"detectors", "observable", "candidate_predictions"},
            )
            source = archive_path(run_dir, partition, p, root)
            if prediction_meta.get("source_archive_sha256") != sha256(source):
                raise RuntimeError(f"prediction archive source hash mismatch: {prediction_path}")
            np.testing.assert_array_equal(stored["detectors"], scored["detectors"])
            np.testing.assert_array_equal(stored["observable"], scored["observable"])
            predictions = validate_binary("candidate predictions", stored["candidate_predictions"],
                                          (len(grid), scored["observable"].size))
            recomputed = decode_grid(scored["detectors"], grid, models)
            np.testing.assert_array_equal(predictions, recomputed)
            errors = np.sum(predictions ^ scored["observable"][None, :], axis=1).astype(int)
            rows.append({"partition": partition, "probability": p, "root": root,
                         "shots": int(scored["observable"].size), "errors_by_grid": errors.tolist()})
    return rows


def _close(a: float, b: float, atol: float = 1e-12) -> bool:
    return math.isclose(float(a), float(b), rel_tol=0, abs_tol=atol)


def verify_candidate_freeze(root: Path, config: dict, inventory: dict) -> dict:
    freeze_path = root / "outputs/strong_fixed_baselines_v2/PRETEST_FREEZE_V2.json"
    freeze = read_json(freeze_path)
    if freeze.get("sampling_performed_at_freeze") is not False or freeze.get("sampling_authorized") is not False:
        raise RuntimeError("candidate freeze must record no sampling authorization")
    if freeze.get("primary_contrast") != config["statistics"]["primary_contrast"]:
        raise RuntimeError("candidate freeze/config primary contrast mismatch")
    if freeze.get("primary_benefit_boundary") != config["statistics"]["primary_benefit_boundary"]:
        raise RuntimeError("candidate freeze/config practical-benefit boundary mismatch")
    if config.get("execution", {}).get("sampling_authorized") is not False:
        raise RuntimeError("V2 config is not sampling-disabled")
    if config.get("seeds", {}).get("inventory_path") != "outputs/strong_fixed_baselines_v2/seed_inventory_v2_r2.json":
        raise RuntimeError("candidate config points to a different seed inventory")
    if inventory.get("sampling_performed") is not False or inventory.get("sealed_test_access") is not False:
        raise RuntimeError("seed inventory provenance is invalid")
    if inventory.get("historical_collisions") or inventory.get("candidate_internal_collisions"):
        raise RuntimeError("seed inventory reports collisions")
    if inventory.get("historical_coverage_complete") is not False or not inventory.get("allowlisted_metadata_sources_verified"):
        raise RuntimeError("seed inventory must disclose limited, allowlisted metadata coverage")
    expected_hashes = freeze.get("sha256", {})
    if set(expected_hashes) != REQUIRED_FREEZE_FILES:
        raise RuntimeError("candidate freeze hash inventory is incomplete or unexpected")
    for relative, expected in expected_hashes.items():
        path = root / relative
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"candidate freeze hash mismatch: {relative}")
    return freeze


def audit_run(run_dir: Path, output_path: Path) -> dict:
    run_dir = run_dir.resolve()
    output_path = output_path.resolve()
    if HERE.resolve() not in run_dir.parents:
        raise ValueError("auditor accepts only a run directory contained under the V2 candidate directory")
    if run_dir == output_path or run_dir in output_path.parents:
        raise ValueError("audit output must be outside the run directory")
    if not run_dir.is_dir():
        raise FileNotFoundError(f"V2 run directory does not exist: {run_dir}")
    config_path = HERE / "experiment_config_v2.json"
    inventory_path = HERE / "seed_inventory_v2_r2.json"
    config = read_json(config_path)
    inventory = read_json(inventory_path)
    freeze = verify_candidate_freeze(ROOT, config, inventory)
    streams = inventory["streams"]
    seeds = [int(row["seed"]) for row in streams]
    if len(seeds) != len(set(seeds)):
        raise RuntimeError("candidate inventory contains duplicate stream seeds")
    if inventory.get("expected_unique_shots") != int(config["allocation"]["unique_shots"]):
        raise RuntimeError("candidate inventory allocation differs from frozen config")
    if inventory.get("configuration_sha256") != sha256(HERE / "experiment_config_v2.json"):
        raise RuntimeError("candidate inventory was prepared from another config")
    for relative, value in freeze["sha256"].items():
        if not (ROOT / relative).is_file() or sha256(ROOT / relative) != value:
            raise RuntimeError(f"candidate source freeze changed: {relative}")

    # Rebuild the template profile from committed template detector arrays only.
    template_batches = []
    for p in map(float, config["decoders"]["profile_template_probabilities"]):
        seed_row = find_stream(inventory, "profile_template", "templates", p, None)
        path = archive_path(run_dir, "templates", p, None)
        arrays, _ = verify_archive(path, expected_partition="templates", expected_probability=p,
                                   expected_root=None, expected_seed=int(seed_row["seed"]),
                                   expected_shots=int(seed_row["shots"]), expected_arrays={"detectors"})
        template_batches.append((p, arrays["detectors"]))
    profile = fit_reference_profiles(template_batches)

    p_values = list(map(float, config["circuit"]["probabilities"]))
    eval_roots = int(config["partitions"]["evaluation_roots_per_condition"])
    grid = list(map(float, config["decoders"]["static_candidate_grid"]))

    # Reconstruct selection and validation from their saved paired detector/label arrays.
    selection_rows = score_grid_partition(
        run_dir, inventory, config, "selection",
        int(config["partitions"]["selection_roots_per_condition"]), grid,
    )
    validation_rows = score_grid_partition(
        run_dir, inventory, config, "validation",
        int(config["partitions"]["validation_roots_per_condition"]), grid,
    )
    selection_scores = read_json(run_dir / "selection_scores.json")
    validation_scores = read_json(run_dir / "validation_scores.json")
    if selection_scores.get("per_root") != selection_rows:
        raise RuntimeError("saved selection scores differ from independent recomputation")
    if validation_scores.get("per_root") != validation_rows:
        raise RuntimeError("saved validation scores differ from independent recomputation")

    def totals_from_rows(rows: list[dict]) -> dict:
        result = {q: {"errors": 0, "shots": 0} for q in grid}
        for row in rows:
            for index, q in enumerate(grid):
                result[q]["errors"] += int(row["errors_by_grid"][index])
                result[q]["shots"] += int(row["shots"])
        return {str(q): item for q, item in result.items()}

    if selection_scores.get("totals") != totals_from_rows(selection_rows):
        raise RuntimeError("saved selection totals differ from independent recomputation")
    if validation_scores.get("totals") != totals_from_rows(validation_rows):
        raise RuntimeError("saved validation totals differ from independent recomputation")

    chosen_before_validation, selection_diagnostics = selection_from_rows(
        grid, selection_rows, float(config["decoders"]["static_zero_burst_mean_harm_limit"])
    )
    if chosen_before_validation == 0.0:
        validation_diffs = []
        validation_upper = 0.0
        chosen = 0.0
    else:
        j = grid.index(chosen_before_validation)
        validation_diffs = [
            row["errors_by_grid"][j] / row["shots"] - row["errors_by_grid"][0] / row["shots"]
            for row in validation_rows if float(row["probability"]) == 0.0
        ]
        boot_seed = int(find_stream(inventory, "bootstrap_validation", "validation_analysis")["seed"])
        validation_upper = bootstrap_upper(
            np.asarray(validation_diffs), boot_seed, int(config["statistics"]["bootstrap_replicates"])
        )
        chosen = chosen_before_validation if validation_upper <= float(config["decoders"]["validation_upper_bound_harm_limit"]) else 0.0
    selection_freeze = read_json(run_dir / "BASELINE_SELECTION_FREEZE.json")
    if float(selection_freeze["selection_candidate_before_validation"]) != chosen_before_validation:
        raise RuntimeError("safety-static prevalidation selection mismatch")
    if float(selection_freeze["chosen_probability"]) != chosen:
        raise RuntimeError("safety-static validation/fallback choice mismatch")
    if not _close(selection_freeze["validation_one_sided_95_upper"], validation_upper):
        raise RuntimeError("safety-static validation upper bound mismatch")
    p0_rows = [row for row in selection_rows if float(row["probability"]) == 0.0]
    saved_p0_lers = selection_freeze["selection_mean_p0_ler_by_candidate"]
    saved_p0_harms = selection_freeze["selection_mean_p0_harm_by_candidate"]
    saved_objectives = selection_freeze["selection_nonzero_objective_by_candidate"]
    for j, q in enumerate(grid):
        actual_mean = float(np.mean([row["errors_by_grid"][j] / row["shots"] for row in p0_rows]))
        if not _close(saved_p0_lers[str(q)], actual_mean):
            raise RuntimeError("saved selection p=0 candidate mean differs from re-scoring")
        if not _close(saved_p0_harms[str(q)], selection_diagnostics[q]["p0_harm"]):
            raise RuntimeError("saved selection p=0 harm differs from re-scoring")
        if not _close(saved_objectives[str(q)], selection_diagnostics[q]["equal_nonzero_mean_ler"]):
            raise RuntimeError("saved nonzero selection objective differs from re-scoring")

    # Recompute pooled p and every root-specific estimate from detector matrices.
    all_calibration = []
    root_calibration: dict[tuple[float, int], np.ndarray] = {}
    cal_archive_refs = []
    for p in p_values:
        for root in range(eval_roots):
            seed_row = find_stream(inventory, "calibration", "heldout_development", p, root)
            path = archive_path(run_dir, "heldout_development_calibration", p, root)
            arrays, _ = verify_archive(
                path, expected_partition="heldout_development_calibration", expected_probability=p,
                expected_root=root, expected_seed=int(seed_row["seed"]), expected_shots=int(seed_row["shots"]),
                expected_arrays={"detectors"},
            )
            detector_rows = arrays["detectors"]
            root_calibration[(p, root)] = detector_rows
            all_calibration.append(detector_rows)
            cal_archive_refs.append({"probability": p, "root": root, "seed": int(seed_row["seed"]),
                                     "path": str(path.relative_to(run_dir)), "sha256": sha256(path)})
    pooled_detectors = np.concatenate(all_calibration, axis=0)
    pooled_p = estimate_probability(profile, pooled_detectors, float(config["decoders"]["profile_grid_step"]))
    pooled_record = read_json(run_dir / "POOLED_CALIBRATION_FREEZE.json")
    if not _close(pooled_record["estimated_p"], pooled_p) or pooled_record["calibration_shots"] != pooled_detectors.shape[0]:
        raise RuntimeError("pooled detector-only calibration freeze mismatch")
    if pooled_record.get("calibration_archives") != cal_archive_refs:
        raise RuntimeError("pooled calibration archive provenance mismatch")

    final_selection = read_json(run_dir / "FINAL_EVAL_SELECTION_FREEZE.json")
    if not _close(final_selection["pooled_detector_static_p"], pooled_p):
        raise RuntimeError("final selection freeze has a different pooled p")
    if not _close(final_selection["safety_constrained_static_p"], chosen):
        raise RuntimeError("final selection freeze has a different safety-static p")
    if float(final_selection["nominal_fixed_p"]) != 0.0:
        raise RuntimeError("nominal fixed p differs from protocol")
    if final_selection.get("experiment_config_sha256") != sha256(config_path):
        raise RuntimeError("final evaluation freeze does not match the frozen V2 config")
    expected_dem = {key: value for key, value in config["circuit"]["dem"].items() if key != "enable_correlations"}
    if final_selection.get("dem_conversion") != expected_dem:
        raise RuntimeError("final evaluation freeze DEM conversion differs from config")
    if final_selection.get("pymatching_correlations_enabled") != bool(config["circuit"]["dem"]["enable_correlations"]):
        raise RuntimeError("final evaluation freeze correlation setting differs from config")
    if final_selection.get("decoder_arm_order") != ["nominal_fixed", "pooled_detector_static",
                                                       "safety_constrained_static", "adaptive_profile",
                                                       "privileged_true_p"]:
        raise RuntimeError("final evaluation decoder arm order differs from protocol")
    if final_selection.get("all_eval_calibration_archive_hashes") != cal_archive_refs:
        raise RuntimeError("final evaluation freeze calibration archive list differs")

    # Re-decode every final root from saved paired arrays with the five arms.
    model_cache: dict[float, Any] = {}
    root_results = []
    expected_arm_order = ["nominal_fixed", "pooled_detector_static", "safety_constrained_static",
                          "adaptive_profile", "privileged_true_p"]
    condition_results = {}
    for p in p_values:
        condition_rows = []
        for root in range(eval_roots):
            cal_detectors = root_calibration[(p, root)]
            p_hat = estimate_probability(profile, cal_detectors, float(config["decoders"]["profile_grid_step"]))
            eval_seed = find_stream(inventory, "evaluation", "heldout_development", p, root)
            path = archive_path(run_dir, "evaluation", p, root)
            arrays, metadata = verify_archive(
                path, expected_partition="evaluation", expected_probability=p, expected_root=root,
                expected_seed=int(eval_seed["seed"]), expected_shots=int(eval_seed["shots"]),
                expected_arrays={"detectors", "observable", "predictions", "p_hat"},
            )
            if metadata.get("decoder_order") != expected_arm_order:
                raise RuntimeError(f"decoder arm order mismatch: {path}")
            stored_phat = float(np.asarray(arrays["p_hat"]).item())
            if not _close(stored_phat, p_hat):
                raise RuntimeError(f"stored p_hat differs from independent estimate: {path}")
            detector_rows = arrays["detectors"]
            observable = arrays["observable"]
            stored_predictions = validate_binary("predictions", arrays["predictions"],
                                                 (5, detector_rows.shape[0]))
            arm_ps = [0.0, pooled_p, chosen, p_hat, p]
            recomputed = np.stack([decoder_prediction(model_cache, q, detector_rows) for q in arm_ps])
            np.testing.assert_array_equal(stored_predictions, recomputed,
                                          err_msg=f"saved decoder predictions differ: {path}")
            errors = np.sum(recomputed ^ observable[None, :], axis=1).astype(int)
            residual_adaptive = recomputed[3] ^ observable
            residual_pooled = recomputed[1] ^ observable
            adaptive_only = int(np.sum((residual_adaptive == 1) & (residual_pooled == 0)))
            pooled_only = int(np.sum((residual_adaptive == 0) & (residual_pooled == 1)))
            row = {"probability": p, "root": root, "shots": int(observable.size),
                   "errors_by_arm": errors.tolist(), "adaptive_only_vs_pooled": adaptive_only,
                   "pooled_only_vs_adaptive": pooled_only, "decoder_disagreements": int(np.sum(recomputed[3] != recomputed[1]))}
            root_results.append(row)
            condition_rows.append(row)
        condition_results[f"{p:.3f}"] = {
            "roots": len(condition_rows),
            "shots": int(sum(r["shots"] for r in condition_rows)),
            "error_counts_by_arm": [int(sum(r["errors_by_arm"][j] for r in condition_rows)) for j in range(5)],
            "ler_by_arm": [float(sum(r["errors_by_arm"][j] for r in condition_rows) /
                                  sum(r["shots"] for r in condition_rows)) for j in range(5)],
            "adaptive_only_vs_pooled": int(sum(r["adaptive_only_vs_pooled"] for r in condition_rows)),
            "pooled_only_vs_adaptive": int(sum(r["pooled_only_vs_adaptive"] for r in condition_rows)),
            "decoder_disagreements": int(sum(r["decoder_disagreements"] for r in condition_rows)),
        }

    if len(root_results) != len(p_values) * eval_roots:
        raise RuntimeError("final root coverage mismatch")
    expected_eval_archives = len(list((run_dir / "evaluation").glob("p_*/root_*.npz")))
    if expected_eval_archives != len(root_results):
        raise RuntimeError("unexpected or duplicate evaluation archive count")
    expected_shots = sum(row["shots"] for row in root_results)
    if expected_shots != int(config["allocation"]["paired_evaluation_shots"]):
        raise RuntimeError("paired final evaluation shot count differs from frozen allocation")
    nonzero_differences = []
    for p in p_values:
        if p == 0.0:
            continue
        rows = [row for row in root_results if row["probability"] == p]
        nonzero_differences.append(float(np.mean([
            row["errors_by_arm"][3] / row["shots"] - row["errors_by_arm"][1] / row["shots"]
            for row in rows
        ])))
    primary = float(np.mean(nonzero_differences))
    bootstrap_seed = int(find_stream(inventory, "bootstrap_results", "heldout_development_analysis")["seed"])
    rng = np.random.Generator(np.random.PCG64(bootstrap_seed))
    replicates = int(config["statistics"]["bootstrap_replicates"])
    boot = np.empty(replicates, dtype=np.float64)
    grouped = {p: [r for r in root_results if r["probability"] == p] for p in p_values if p > 0}
    for start in range(0, replicates, 2000):
        n = min(2000, replicates - start)
        condition_draws = []
        for p, rows in grouped.items():
            values = np.asarray([r["errors_by_arm"][3] / r["shots"] - r["errors_by_arm"][1] / r["shots"]
                                 for r in rows], dtype=np.float64)
            indices = rng.integers(0, values.size, size=(n, values.size))
            condition_draws.append(values[indices].mean(axis=1))
        boot[start:start + n] = np.stack(condition_draws, axis=1).mean(axis=1)
    ci = [float(np.quantile(boot, 0.025, method="linear")),
          float(np.quantile(boot, 0.975, method="linear"))]

    output = {
        "schema_version": 1,
        "audit_status": "PASS_INDEPENDENT_ARRAY_RECOMPUTATION",
        "read_only": True,
        "sealed_test_access": False,
        "v2_sampling_executed_by_auditor": False,
        "freeze_sha256": sha256(ROOT / "outputs/strong_fixed_baselines_v2/PRETEST_FREEZE_V2.json"),
        "expected_evaluation_roots": len(root_results),
        "expected_evaluation_shots": int(sum(row["shots"] for row in root_results)),
        "pooled_estimated_probability": pooled_p,
        "safety_static_probability": chosen,
        "primary_contrast": config["statistics"]["primary_contrast"],
        "primary_adaptive_minus_pooled_equal_condition_ler": primary,
        "primary_condition_differences": nonzero_differences,
        "primary_root_stratified_bootstrap_95_percent_interval": ci,
        "primary_practical_effect_benchmark": float(config["statistics"]["primary_practical_effect_benchmark"]),
        "primary_benefit_boundary": float(config["statistics"]["primary_benefit_boundary"]),
        "primary_favorable_nonzero_conditions": int(sum(value < 0 for value in nonzero_differences)),
        "primary_practical_benchmark_met_descriptively": bool(primary <= float(config["statistics"]["primary_benefit_boundary"])),
        "zero_burst_adaptive_minus_nominal_ler": (
            condition_results["0.000"]["ler_by_arm"][3] - condition_results["0.000"]["ler_by_arm"][0]
        ),
        "zero_burst_pooled_minus_nominal_ler": (
            condition_results["0.000"]["ler_by_arm"][1] - condition_results["0.000"]["ler_by_arm"][0]
        ),
        "primary_bootstrap_seed": bootstrap_seed,
        "primary_bootstrap_replicates": replicates,
        "condition_results": condition_results,
        "per_root": root_results,
        "limitations": [
            "Development-only descriptive analysis; no confirmatory p-value is computed.",
            "The audit is independent of the runner but uses the frozen shared Stim/PyMatching construction primitives.",
            "Execution of this auditor requires an already-completed V2 run and is not part of this review checkpoint.",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only V2 saved-array verification; does not sample")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit_run(args.run_dir.resolve(), args.output.resolve())
    print(json.dumps({
        "audit_status": result["audit_status"],
        "verified_roots": result["expected_evaluation_roots"],
        "verified_evaluation_shots": result["expected_evaluation_shots"],
        "primary_effect": result["primary_adaptive_minus_pooled_equal_condition_ler"],
        "output": str(args.output.resolve()),
    }, indent=2))


if __name__ == "__main__":
    main()
