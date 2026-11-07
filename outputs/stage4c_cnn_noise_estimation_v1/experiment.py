"""Frozen Stage 4C sampling/training runner. CPU only, paired, resumable by root."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import tempfile
import time
from pathlib import Path

import numpy as np
import psutil
import stim
import pymatching
import torch

from outputs.stage4_noise_adaptive_feasibility_v1.prototype import (
    DetectorProfileEstimator, build_decoder, decode_prediction,
)
from outputs.phase3a_correlated_noise_preflight.simulator import build_spatial_burst_circuit
from .models import (
    BurstProbabilityCNN, RidgeBurstRegressor, batch_feature_vector,
    detector_coordinate_map, encode_calibration_batch, encode_training_batches,
    parameter_count, ridge_features_for_batches,
)

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CONFIG_PATH = HERE / "config.json"
INVENTORY_PATH = HERE / "seed_inventory.json"
SEED_AUDIT_PATH = HERE / "seed_audit.json"
FREEZE_PATH = HERE / "FREEZE.json"
RUN_DIR = HERE / "run"
ROOT_DIR = RUN_DIR / "roots"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                     delete=False, suffix=".tmp") as f:
        json.dump(value, f, indent=2)
        f.write("\n")
        tmp = Path(f.name)
    os.replace(tmp, path)


def atomic_npz(path: Path, **arrays) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False, suffix=".npz.tmp") as f:
        np.savez_compressed(f, **arrays)
        tmp = Path(f.name)
    os.replace(tmp, path)


def atomic_torch_save(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, suffix=".pt.tmp")
    os.close(fd)
    tmp = Path(name)
    try:
        torch.save(value, tmp)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def log(message: str) -> None:
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    with (RUN_DIR / "controller.log").open("a", encoding="utf-8") as f:
        f.write(f"{stamp} {message}\n")
    print(message, flush=True)


def load_frozen() -> tuple[dict, dict, dict]:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    audit = json.loads(SEED_AUDIT_PATH.read_text(encoding="utf-8"))
    if not FREEZE_PATH.is_file():
        raise RuntimeError("FREEZE.json is missing; refuse to sample")
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    if freeze.get("status") != "FROZEN_BEFORE_SAMPLING":
        raise RuntimeError("protocol freeze status is not FROZEN_BEFORE_SAMPLING")
    for rel, expected in freeze["files_sha256"].items():
        path = REPO / rel
        if not path.is_file() or sha256_file(path) != expected:
            raise RuntimeError(f"pre-sampling frozen file hash mismatch: {rel}")
    if audit.get("status") != "PASS_RECOVERABLE_DEVELOPMENT_METADATA" or audit.get("stage4c_historical_collisions") != []:
        raise RuntimeError("seed collision audit has not passed")
    if inventory.get("unique_seed_count") != 554 or len({int(s["seed"]) for s in inventory["streams"]}
            | {int(v) for v in inventory["analysis_rngs"].values()}) != 554:
        raise RuntimeError("Stage 4C seed inventory size or uniqueness is invalid")
    if config["total_unique_shots"] != 277500 or config["hard_shot_ceiling"] != 300000:
        raise RuntimeError("frozen shot allocation/ceiling mismatch")
    if config["independent_test"] != {"allocated": False, "accessed": False, "enumerated": False}:
        raise RuntimeError("independent-test seal state is not clean")
    return config, inventory, freeze


def stream_index(inventory: dict) -> dict[tuple, dict]:
    result = {}
    for item in inventory["streams"]:
        kind = item["kind"]
        if kind in ("training_detector_batch", "validation_detector_batch"):
            key = (kind, float(item["probability"]), int(item["batch"]))
        else:
            key = (kind, float(item["probability"]), int(item["root"]))
        if key in result:
            raise ValueError(f"duplicate stream key {key}")
        result[key] = item
    return result


def circuit_for(p: float):
    return build_spatial_burst_circuit(memory_basis="z", regime="balanced", distance=3,
        rounds=5, gate_p=0.003, measurement_p=0.003, bias_ratio=10.0,
        burst_probability=float(p), burst_pair=(8, 10))


def deterministic_preflight() -> dict:
    """Structural-only checks: no stochastic data or evaluation shots generated."""
    coords_by_p = []
    dem_shapes = []
    graph_meta = []
    for p in (0.0, 0.006, 0.016):
        circuit = circuit_for(p)
        dem = circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)
        matcher = pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)
        coords_by_p.append(circuit.get_detector_coordinates())
        dem_shapes.append([dem.num_detectors, dem.num_observables])
        graph_meta.append([matcher.num_detectors, matcher.num_fault_ids])
        if (circuit.num_detectors, circuit.num_observables) != (40, 1):
            raise RuntimeError("circuit detector/observable shape mismatch")
        if (dem.num_detectors, dem.num_observables) != (40, 1) or (matcher.num_detectors, matcher.num_fault_ids) != (40, 1):
            raise RuntimeError("DEM or matching graph shape mismatch")
        zero_predictions = np.asarray(matcher.decode_batch(np.zeros((4, 40), dtype=np.uint8)))
        if zero_predictions.shape not in ((4,), (4, 1)) or not np.isin(zero_predictions, (0, 1)).all():
            raise RuntimeError("deterministic zero-syndrome decoder prediction failed")
    if coords_by_p[0] != coords_by_p[1] or coords_by_p[0] != coords_by_p[2]:
        raise RuntimeError("detector coordinates changed across burst probabilities")
    coord_map = detector_coordinate_map(coords_by_p[0])
    noiseless = circuit_for(0.0).without_noise()
    if noiseless.num_detectors != 40 or noiseless.num_observables != 1:
        raise RuntimeError("noiseless circuit shape mismatch")
    torch.set_num_threads(1)
    model = BurstProbabilityCNN()
    fake = np.zeros((250, 40), dtype=np.uint8)
    x = encode_calibration_batch(fake, coord_map)
    with torch.no_grad():
        y = model(torch.from_numpy(x[None]))
    if y.shape != (1,) or not torch.isfinite(y).all():
        raise RuntimeError("CNN deterministic tensor preflight failed")
    return {"status": "PASS", "stochastic_shots_generated": 0, "stim": stim.__version__,
            "pymatching": pymatching.__version__, "torch": torch.__version__,
            "cuda_used": False, "detectors": 40, "observables": 1,
            "detector_grid_shape_time_y_x": [6, 4, 4], "occupied_grid_cells": len(coord_map),
            "occupancy_mask_cells": len(coord_map),
            "dem_shapes": dem_shapes, "matching_graph_shapes": graph_meta,
            "same_coordinates_across_p": True, "cnn_parameter_count": parameter_count(model)}


def make_partition(kind: str, probabilities: tuple[float, ...], batches_per_p: int,
                   streams: dict[tuple, dict]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    data, labels, seeds = [], [], []
    for p in probabilities:
        circuit = circuit_for(p)
        for batch in range(batches_per_p):
            item = streams[(kind, float(p), batch)]
            detectors = circuit.compile_detector_sampler(seed=int(item["seed"])).sample(int(item["shots"]))
            if detectors.shape != (int(item["shots"]), 40) or not np.isin(detectors, (0, 1)).all():
                raise RuntimeError(f"invalid detector sample shape/values for {kind}/{p}/{batch}")
            data.append(detectors.astype(np.uint8, copy=False))
            labels.append(float(p))
            seeds.append(int(item["seed"]))
    return np.stack(data), np.asarray(labels, dtype=np.float64), np.asarray(seeds, dtype=np.uint64)


def ensure_partition(path: Path, kind: str, probabilities: tuple[float, ...], batches_per_p: int,
                     streams: dict[tuple, dict]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if path.exists():
        with np.load(path, allow_pickle=False) as z:
            d, y, s = z["detectors"], z["probabilities"], z["seeds"]
        if d.shape != (len(probabilities) * batches_per_p, 250, 40) or y.shape != (d.shape[0],) or s.shape != y.shape:
            raise RuntimeError(f"existing partition schema mismatch; preserving file: {path.name}")
        expected = np.asarray([streams[(kind, float(p), b)]["seed"] for p in probabilities for b in range(batches_per_p)], dtype=np.uint64)
        if not np.array_equal(s, expected) or not np.array_equal(y, np.repeat(probabilities, batches_per_p)):
            raise RuntimeError(f"existing partition seed/label mismatch; preserving file: {path.name}")
        return d, y, s
    d, y, s = make_partition(kind, probabilities, batches_per_p, streams)
    atomic_npz(path, detectors=d, probabilities=y, seeds=s)
    return d, y, s


def fit_cnn(train_detectors: np.ndarray, train_p: np.ndarray, valid_detectors: np.ndarray,
            valid_p: np.ndarray, coord_map: dict[int, tuple[int, int, int]],
            inventory: dict, resource_deadline: float) -> tuple[BurstProbabilityCNN, dict]:
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(int(inventory["analysis_rngs"]["torch_initialization"]))
    model = BurstProbabilityCNN().cpu()
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.003, weight_decay=0.0001)
    loss_fn = torch.nn.MSELoss()
    x_train = torch.from_numpy(encode_training_batches(train_detectors, coord_map))
    y_train = torch.from_numpy((train_p / 0.02).astype(np.float32))
    x_valid = torch.from_numpy(encode_training_batches(valid_detectors, coord_map))
    y_valid = torch.from_numpy(valid_p.astype(np.float32))
    order_rng = torch.Generator(device="cpu").manual_seed(int(inventory["analysis_rngs"]["torch_batch_order"]))
    batch_size, patience, best_mae = 32, 30, float("inf")
    best_state, best_epoch, stale, trace = None, 0, 0, []
    start = time.perf_counter()
    for epoch in range(1, 401):
        if time.time() > resource_deadline:
            raise TimeoutError("18,000-second wall limit reached during CNN training")
        model.train()
        permutation = torch.randperm(x_train.shape[0], generator=order_rng)
        train_losses = []
        for start_index in range(0, x_train.shape[0], batch_size):
            ix = permutation[start_index:start_index + batch_size]
            optimizer.zero_grad(set_to_none=True)
            pred = model(x_train[ix])
            loss = loss_fn(pred, y_train[ix])
            if not torch.isfinite(loss):
                raise FloatingPointError("non-finite CNN training loss")
            loss.backward()
            optimizer.step()
            train_losses.append(float(loss.detach()))
        model.eval()
        with torch.no_grad():
            val_predictions = model(x_valid).numpy() * 0.02
            val_mae = float(np.mean(np.abs(val_predictions - y_valid.numpy())))
        if not np.isfinite(val_mae):
            raise FloatingPointError("non-finite CNN validation MAE")
        trace.append({"epoch": epoch, "train_mse_normalized": float(np.mean(train_losses)),
                      "validation_mae": val_mae})
        if val_mae < best_mae - 1e-12:
            best_mae, best_epoch, stale = val_mae, epoch, 0
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        else:
            stale += 1
        if stale >= patience:
            break
    if best_state is None:
        raise RuntimeError("CNN did not produce a valid validation checkpoint")
    model.load_state_dict(best_state)
    model.eval()
    ckpt_path = RUN_DIR / "cnn_checkpoint.pt"
    checkpoint = {"state_dict": best_state,
        "best_epoch": best_epoch, "validation_mae": best_mae,
        "initialization_seed": int(inventory["analysis_rngs"]["torch_initialization"]),
        "batch_order_seed": int(inventory["analysis_rngs"]["torch_batch_order"]),
        "config_sha256": sha256_file(CONFIG_PATH)}
    if ckpt_path.exists():
        previous = torch.load(ckpt_path, map_location="cpu", weights_only=True)
        if int(previous.get("best_epoch", -1)) != best_epoch or any(
                not torch.allclose(previous["state_dict"][k], best_state[k], rtol=0, atol=1e-7)
                for k in best_state):
            raise RuntimeError("existing CNN checkpoint differs from deterministic frozen retraining; preserving it")
    else:
        atomic_torch_save(ckpt_path, checkpoint)
    details = {"best_epoch": best_epoch, "epochs_run": len(trace), "best_validation_mae": best_mae,
        "parameter_count": parameter_count(model), "device": "cpu", "threads": 1,
        "training_seconds": time.perf_counter() - start, "trace": trace,
        "checkpoint_sha256": sha256_file(ckpt_path)}
    atomic_json(RUN_DIR / "training_diagnostics.json", details)
    return model, details


def choose_ridge(train_d: np.ndarray, train_p: np.ndarray, valid_d: np.ndarray,
                 valid_p: np.ndarray) -> tuple[RidgeBurstRegressor, dict]:
    train_x = ridge_features_for_batches(train_d)
    valid_x = ridge_features_for_batches(valid_d)
    candidates = []
    for alpha in (0.01, 0.1, 1.0, 10.0):
        model = RidgeBurstRegressor.fit(train_x, train_p, alpha)
        mae = float(np.mean(np.abs(model.predict(valid_x) - valid_p)))
        candidates.append({"alpha": alpha, "validation_mae": mae, "model": model})
    chosen = min(candidates, key=lambda x: (x["validation_mae"], x["alpha"]))
    m = chosen["model"]
    atomic_json(RUN_DIR / "ridge_model.json", {"alpha": m.alpha, "mean": m.mean.tolist(),
        "scale": m.scale.tolist(), "coef": m.coef.tolist(),
        "validation_mae": chosen["validation_mae"], "candidates": [
            {"alpha": x["alpha"], "validation_mae": x["validation_mae"]} for x in candidates]})
    return m, {"selected_alpha": m.alpha, "validation_mae": chosen["validation_mae"],
               "candidates": [{"alpha": x["alpha"], "validation_mae": x["validation_mae"]} for x in candidates]}


def cnn_probability(model: BurstProbabilityCNN, detectors: np.ndarray,
                    coord_map: dict[int, tuple[int, int, int]]) -> tuple[float, float]:
    d = np.asarray(detectors)
    if d.ndim != 2 or d.shape != (2000, 40):
        raise ValueError("CNN inference requires the frozen (2000,40) calibration array")
    estimates = []
    start = time.perf_counter()
    model.eval()
    with torch.no_grad():
        for batch in d.reshape(8, 250, 40):
            encoded = encode_calibration_batch(batch, coord_map)
            x = torch.from_numpy(encoded[None])
            estimates.append(float(model(x).item() * 0.02))
    return float(np.clip(np.mean(estimates), 0.0, 0.02)), time.perf_counter() - start


def check_root_checkpoint(path: Path, expected: dict) -> bool:
    if not path.exists():
        return False
    required = {"calibration_detectors", "evaluation_detectors", "observables", "pred_fixed",
                "pred_profile", "pred_ridge", "pred_cnn", "pred_privileged", "metadata_json"}
    with np.load(path, allow_pickle=False) as z:
        if not required.issubset(z.files):
            raise RuntimeError(f"invalid checkpoint schema; preserved: {path}")
        arrays = {k: z[k] for k in required - {"metadata_json"}}
        meta = json.loads(str(z["metadata_json"].item()))
    if meta != expected:
        raise RuntimeError(f"checkpoint provenance mismatch; preserved: {path}")
    if arrays["calibration_detectors"].shape != (2000, 40) or arrays["evaluation_detectors"].shape != (2500, 40):
        raise RuntimeError(f"checkpoint detector shape mismatch; preserved: {path}")
    if arrays["observables"].shape != (2500,) or any(arrays[k].shape != (2500,) for k in
            ("pred_fixed", "pred_profile", "pred_ridge", "pred_cnn", "pred_privileged")):
        raise RuntimeError(f"checkpoint prediction/label shape mismatch; preserved: {path}")
    if any(not np.isin(arrays[k], (0, 1)).all() for k in ("observables", "pred_fixed", "pred_profile", "pred_ridge", "pred_cnn", "pred_privileged")):
        raise RuntimeError(f"checkpoint non-binary values; preserved: {path}")
    return True


def execute() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true", required=True,
                        help="execute or resume the frozen, bounded development allocation")
    args = parser.parse_args()
    del args
    config, inventory, freeze = load_frozen()
    preflight = deterministic_preflight()
    if preflight["status"] != "PASS":
        raise RuntimeError("deterministic preflight failed")
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    ROOT_DIR.mkdir(parents=True, exist_ok=True)
    status_path = RUN_DIR / "status.json"
    freeze_hash = sha256_file(FREEZE_PATH)
    prior = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
    if prior.get("status") == "completed":
        raise RuntimeError("Stage 4C is already completed; do not rerun")
    if prior and prior.get("freeze_sha256") != freeze_hash:
        raise RuntimeError("existing run belongs to a different freeze; preserve and stop")
    started = float(prior.get("started_unix", time.time()))
    deadline = started + int(config["resources"]["wall_seconds_max"])
    process = psutil.Process()
    if process.memory_info().rss > int(config["resources"]["peak_rss_bytes_max"]):
        raise MemoryError("process RSS exceeds 2 GiB before sampling")
    if psutil.disk_usage(str(REPO)).free < 1 * 1024**3:
        raise OSError("less than 1 GiB free disk before sampling")
    status = {"status": "running", "started_unix": started, "pid": os.getpid(),
        "working_directory": str(REPO), "freeze_sha256": freeze_hash,
        "completed_roots": prior.get("completed_roots", []), "completed_shots": 0,
        "generated_unique_shots": 0, "unique_shot_ceiling": 300000,
        "independent_test_accessed": 0, "preflight": preflight,
        "software": {"python": platform.python_version(), "numpy": np.__version__,
            "stim": stim.__version__, "pymatching": pymatching.__version__, "torch": torch.__version__}}
    atomic_json(status_path, status)
    stream_items = stream_index(inventory)
    log("Stage 4C starts with frozen 277500-shot allocation; CPU-only CNN estimator.")

    train_d, train_p, train_s = ensure_partition(RUN_DIR / "training_batches.npz",
        "training_detector_batch", (0.0, 0.01, 0.02), 120, stream_items)
    valid_d, valid_p, valid_s = ensure_partition(RUN_DIR / "validation_batches.npz",
        "validation_detector_batch", (0.005, 0.015), 60, stream_items)
    for name, d, p, s in (("training", train_d, train_p, train_s), ("validation", valid_d, valid_p, valid_s)):
        expected_seeds = np.asarray([i["seed"] for i in inventory["streams"] if i["kind"] == ("training_detector_batch" if name == "training" else "validation_detector_batch")], dtype=np.uint64)
        if not np.array_equal(s, expected_seeds) or d.shape[1:] != (250, 40):
            raise RuntimeError(f"{name} data did not match frozen seed allocation")
    status["generated_unique_shots"] = 120000
    status["completed_shots"] = 120000
    status["training_partition_sha256"] = sha256_file(RUN_DIR / "training_batches.npz")
    status["validation_partition_sha256"] = sha256_file(RUN_DIR / "validation_batches.npz")
    atomic_json(status_path, status)
    log("Training and validation detector-only partitions available: 120000 unique shots.")

    profile_batches = [(float(p), d) for p, d in zip(train_p, train_d)]
    profile_estimator = DetectorProfileEstimator.fit(profile_batches)
    coord_map = detector_coordinate_map(circuit_for(0.0).get_detector_coordinates())
    ridge, ridge_info = choose_ridge(train_d, train_p, valid_d, valid_p)
    cnn, cnn_info = fit_cnn(train_d, train_p, valid_d, valid_p, coord_map, inventory, deadline)
    atomic_json(RUN_DIR / "profile_estimator.json", {"probabilities": profile_estimator.probabilities.tolist(),
        "means": profile_estimator.means.tolist(), "scales": profile_estimator.scales.tolist(),
        "grid_step": profile_estimator.grid_step})
    atomic_json(RUN_DIR / "estimator_selection.json", {"ridge": ridge_info, "cnn": cnn_info,
        "validation_batches": int(valid_d.shape[0]), "evaluation_labels_used": False})
    fixed_build = time.perf_counter()
    fixed_circuit, fixed_dem, fixed_matcher = build_decoder(0.0)
    if (fixed_dem.num_detectors, fixed_dem.num_observables) != (40, 1):
        raise RuntimeError("fixed decoder graph shape mismatch")
    fixed_build_s = time.perf_counter() - fixed_build
    coord_map_for_run = coord_map
    conditions = (0.0, 0.004, 0.008, 0.012, 0.016)
    completed_root_names = {Path(x["path"]).name for x in prior.get("completed_roots", []) if "path" in x}
    all_root_files = {p.name for p in ROOT_DIR.glob("*.npz")}
    expected_names = {f"p{int(round(p*1000)):03d}_root{r:02d}.npz" for p in conditions for r in range(7)}
    if all_root_files - expected_names:
        raise RuntimeError(f"unexpected pre-existing root archives: {sorted(all_root_files-expected_names)}")
    root_manifest = []
    for p in conditions:
        for root in range(7):
            if time.time() > deadline:
                raise TimeoutError("1800-second wall limit reached")
            if process.memory_info().rss > int(config["resources"]["peak_rss_bytes_max"]):
                raise MemoryError("2 GiB process RSS limit reached")
            cal_stream = stream_items[("evaluation_calibration_detectors", p, root)]
            eval_stream = stream_items[("paired_evaluation_detectors_observables", p, root)]
            out = ROOT_DIR / f"p{int(round(p*1000)):03d}_root{root:02d}.npz"
            projected = 120000 + 4500 * (len(root_manifest) + 1)
            if projected > int(config["hard_shot_ceiling"]):
                raise RuntimeError("frozen 300000-unique-shot ceiling would be exceeded")
            if out.exists():
                # Existing root archives are accepted only after exact seed/hash provenance and
                # shape checks; the independent audit later re-decodes every stored prediction.
                with np.load(out, allow_pickle=False) as z:
                    meta = json.loads(str(z["metadata_json"].item()))
                if (meta.get("seeds") != {"calibration": int(cal_stream["seed"]), "evaluation": int(eval_stream["seed"])}
                        or float(meta.get("probability", -1)) != p or int(meta.get("root", -1)) != root):
                    raise RuntimeError(f"existing root seed mismatch; preserved: {out.name}")
                check_root_checkpoint(out, meta)
                root_manifest.append({"path": str(out.relative_to(REPO)), "sha256": sha256_file(out),
                                      "probability": p, "root": root, "resumed": True})
                continue
            circuit = circuit_for(p)
            cal_det = circuit.compile_detector_sampler(seed=int(cal_stream["seed"])).sample(2000).astype(np.uint8, copy=False)
            eval_det, observable = circuit.compile_detector_sampler(seed=int(eval_stream["seed"])).sample(2500, separate_observables=True)
            eval_det = eval_det.astype(np.uint8, copy=False)
            observable = np.asarray(observable, dtype=np.uint8).reshape(-1)
            if cal_det.shape != (2000, 40) or eval_det.shape != (2500, 40) or observable.shape != (2500,):
                raise RuntimeError("invalid calibration/evaluation sample shape")
            if not np.isin(cal_det, (0, 1)).all() or not np.isin(eval_det, (0, 1)).all() or not np.isin(observable, (0, 1)).all():
                raise RuntimeError("non-binary Stim sample values")
            # Estimators receive calibration detectors only; no label/evaluation argument exists.
            t0 = time.perf_counter()
            p_profile = profile_estimator.estimate(cal_det)
            profile_inference_s = time.perf_counter() - t0
            ridgex = np.stack([batch_feature_vector(c) for c in cal_det.reshape(8, 250, 40)])
            t0 = time.perf_counter()
            p_ridge = float(ridge.predict(ridgex).mean())
            ridge_inference_s = time.perf_counter() - t0
            p_cnn, cnn_inference_s = cnn_probability(cnn, cal_det, coord_map_for_run)
            estimators = {"profile": p_profile, "ridge": p_ridge, "cnn": p_cnn, "privileged": p}
            predictions = {"fixed": decode_prediction(fixed_matcher, eval_det)}
            build_seconds = {"fixed": fixed_build_s}
            for name in ("profile", "ridge", "cnn", "privileged"):
                t0 = time.perf_counter()
                _, dem, matcher = build_decoder(float(estimators[name]))
                build_seconds[name] = time.perf_counter() - t0
                if (dem.num_detectors, dem.num_observables, matcher.num_detectors, matcher.num_fault_ids) != (40, 1, 40, 1):
                    raise RuntimeError(f"{name} decoder has invalid detector/observable graph")
                predictions[name] = decode_prediction(matcher, eval_det)
            # The observable is first accessed for scoring/archival after all decoder predictions exist.
            metadata = {"probability": p, "root": root,
                "seeds": {"calibration": int(cal_stream["seed"]), "evaluation": int(eval_stream["seed"])},
                "p_estimates": estimators, "decoder_build_seconds": build_seconds,
                "estimator_inference_seconds": {"profile": profile_inference_s,
                    "ridge": ridge_inference_s, "cnn": cnn_inference_s},
                "cnn_parameter_count": parameter_count(cnn), "fixed_dem_sha256": hashlib.sha256(str(fixed_dem).encode()).hexdigest(),
                "paired_samples": True, "label_used_for_estimation": False}
            atomic_npz(out, calibration_detectors=cal_det, evaluation_detectors=eval_det,
                observables=observable, pred_fixed=predictions["fixed"],
                pred_profile=predictions["profile"], pred_ridge=predictions["ridge"],
                pred_cnn=predictions["cnn"], pred_privileged=predictions["privileged"],
                metadata_json=np.asarray(json.dumps(metadata, sort_keys=True)))
            rec = {"path": str(out.relative_to(REPO)), "sha256": sha256_file(out),
                   "probability": p, "root": root, "resumed": False}
            root_manifest.append(rec)
            completed_root_names.add(out.name)
            status["completed_roots"] = root_manifest
            status["generated_unique_shots"] = 120000 + 4500 * len(root_manifest)
            status["completed_shots"] = status["generated_unique_shots"]
            status["peak_rss_bytes"] = max(int(status.get("peak_rss_bytes", 0)), int(process.memory_info().rss))
            status["active_runtime_seconds"] = time.time() - started
            atomic_json(status_path, status)
            log(f"completed {out.name}: paired shots=2500, total unique shots={status['completed_shots']}")
    if len(root_manifest) != 35:
        raise RuntimeError(f"expected 35 evaluation roots, observed {len(root_manifest)}")
    status["status"] = "completed"
    status["completed_roots"] = root_manifest
    status["completed_jobs"] = len(root_manifest)
    status["generated_unique_shots"] = 277500
    status["completed_shots"] = 277500
    status["active_runtime_seconds"] = time.time() - started
    status["peak_rss_bytes"] = max(int(status.get("peak_rss_bytes", 0)), int(process.memory_info().rss))
    status["independent_test_accessed"] = 0
    atomic_json(status_path, status)
    log("Stage 4C sampling and decoder execution completed; no independent test was accessed.")


if __name__ == "__main__":
    try:
        execute()
    except Exception as ex:
        RUN_DIR.mkdir(parents=True, exist_ok=True)
        status_path = RUN_DIR / "status.json"
        if status_path.exists():
            import traceback
            failed = json.loads(status_path.read_text(encoding="utf-8"))
            failed["status"] = "failed"
            failed["failure"] = f"{type(ex).__name__}: {ex}"
            failed["traceback"] = traceback.format_exc()
            failed["failure_unix"] = time.time()
            atomic_json(status_path, failed)
            log(f"Stage 4C stopped: {type(ex).__name__}: {ex}")
        raise
