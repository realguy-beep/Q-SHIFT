"""Deterministic, resumable execution of the frozen Q-SHIFT CNN Stage 2 study.

The only sampling/training entry point is ``python .../run_stage2.py --run``.
It verifies FREEZE_IMPLEMENTATION_V4.json before any sampler is constructed.
All data/checkpoints/status live under ignored run_v1/raw, checkpoints, and
predictions directories; the independent-test allocation is never referenced.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import shutil
import sys
import time
import traceback
from pathlib import Path
from typing import Any

import numpy as np
import psutil
import pymatching
import stim
import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
for path in (ROOT, ROOT / "dashboard"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from outputs.cnn_architecture_stage1_v1.cnn_architectures import (  # noqa: E402
    FactorizedSpatialTemporalResidualCNN,
    ResidualPositionCNNV2,
    parameter_count,
)
from outputs.neural_decoder_diagnostic.autonomous_development.experiment import (  # noqa: E402
    ResidualPositionCNN as HistoricalResidualPositionCNN,
)
from outputs.phase3a_correlated_noise_preflight.simulator import (  # noqa: E402
    build_matching,
    build_spatial_burst_circuit,
)

CONFIG_PATH = HERE / "stage2_config.json"
FREEZE_PATH = HERE / "FREEZE_IMPLEMENTATION_V4.json"
RUN_DIR = HERE / "run_v1"
RAW_DIR = RUN_DIR / "raw"
CHECKPOINT_DIR = RUN_DIR / "checkpoints"
PREDICTION_DIR = RUN_DIR / "predictions"
STATUS_PATH = RAW_DIR / "status.json"
LOCK_PATH = RAW_DIR / "runner.lock"
MODEL_ORDER = (
    "historical_residual_position_cnn",
    "residual_position_v2",
    "factorized_spatiotemporal_residual",
)
CONDITIONS = ("nominal", "synthetic_spatial_burst")
SPLIT_NAMES = ("training", "monitor", "probability_calibration", "threshold_selection")


class Stage2Error(RuntimeError):
    """Base error for frozen-protocol violations or unsafe execution."""


class ResourceLimitError(Stage2Error):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_array(value: np.ndarray) -> str:
    arr = np.ascontiguousarray(value)
    h = hashlib.sha256()
    h.update(str(arr.dtype).encode())
    h.update(json.dumps(list(arr.shape), separators=(",", ":")).encode())
    h.update(arr.tobytes())
    return h.hexdigest()


def state_dict_hash(state: dict[str, torch.Tensor]) -> str:
    h = hashlib.sha256()
    for key in sorted(state):
        tensor = state[key].detach().cpu().contiguous()
        h.update(key.encode())
        h.update(str(tensor.dtype).encode())
        h.update(np.asarray(tensor.shape, dtype=np.int64).tobytes())
        h.update(tensor.numpy().tobytes())
    return h.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    data = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    with tmp.open("wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def atomic_npz(path: Path, arrays: dict[str, np.ndarray]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as f:
        np.savez_compressed(f, **arrays)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    return sha256_file(path)


def atomic_torch_save(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as f:
        torch.save(payload, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    return sha256_file(path)


def verify_freeze() -> tuple[dict, dict]:
    if not FREEZE_PATH.is_file():
        raise Stage2Error("Missing superseding implementation freeze; refuse to sample.")
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    if freeze.get("status") != "FROZEN_IMPLEMENTATION_V4_NOT_EXECUTED":
        raise Stage2Error(f"Unexpected implementation freeze status: {freeze.get('status')}")
    if freeze.get("shots_generated") != 0 or freeze.get("training_started") is not False:
        raise Stage2Error("Implementation freeze no longer represents a pre-sampling state.")
    old_freeze = HERE / "FREEZE.json"
    if not old_freeze.is_file() or sha256_file(old_freeze) != freeze.get("historical_original_freeze_sha256"):
        raise Stage2Error("The original historical freeze no longer matches the supersession record")
    previous_freeze = HERE / "FREEZE_IMPLEMENTATION_V3.json"
    if not previous_freeze.is_file() or sha256_file(previous_freeze) != freeze.get("supersedes_freeze_file_sha256"):
        raise Stage2Error("Immediately superseded V3 freeze hash mismatch")
    for record in freeze["source_and_protocol_files"]:
        path = ROOT / record["path"]
        if not path.is_file():
            raise Stage2Error(f"Frozen input missing: {record['path']}")
        if path.stat().st_size != record["bytes"] or sha256_file(path) != record["sha256"]:
            raise Stage2Error(f"Frozen input hash mismatch: {record['path']}")
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    inv = json.loads((HERE / "seed_inventory.json").read_text(encoding="utf-8"))
    seeds = [int(item["seed"]) for item in inv["streams"]]
    if len(seeds) != 95 or len(seeds) != len(set(seeds)):
        raise Stage2Error("Seed inventory no longer has 95 unique allocations.")
    if inv.get("independent_test_seed_allocated") is not False:
        raise Stage2Error("Test seed allocation is forbidden.")
    if freeze.get("seed_count") != len(seeds) or freeze.get("unique_seed_count") != len(set(seeds)):
        raise Stage2Error("Freeze and seed inventory disagree.")
    file_records = freeze["source_and_protocol_files"]
    canonical = json.dumps({"files": file_records, "inventory": inv}, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if sha256_bytes(canonical) != freeze.get("protocol_id_sha256"):
        raise Stage2Error("Implementation freeze protocol ID does not match the file/seed inventory")
    if (freeze.get("prior_superseded_hash_count") != 6 or
            len(freeze.get("superseded_freeze_sha256s", [])) != 7 or
            freeze["superseded_freeze_sha256s"][-1] != freeze["supersedes_freeze_file_sha256"]):
        raise Stage2Error("Superseded-freeze chain/count does not reconcile to four drafts plus original freeze")
    return cfg, inv


def seed_for(inventory: dict, root_id: str, *, split: str | None = None,
             condition: str | None = None, model: str | None = None,
             purpose: str | None = None) -> int:
    matches = []
    for item in inventory["streams"]:
        if item.get("root_id") != root_id:
            continue
        if item.get("kind") == "stim_sample_stream":
            if item.get("split") == split and item.get("condition") == condition:
                matches.append(int(item["seed"]))
        elif model is not None and item.get("model") == model and item.get("purpose") == purpose:
            matches.append(int(item["seed"]))
    if len(matches) != 1:
        raise Stage2Error(f"Seed lookup must resolve exactly once: {root_id}/{split}/{condition}/{model}/{purpose}")
    return matches[0]


def binary_array(name: str, arr: np.ndarray) -> np.ndarray:
    result = np.asarray(arr)
    if not np.isin(result, (0, 1)).all():
        raise Stage2Error(f"{name} contains non-binary values")
    return result.astype(np.uint8, copy=False)


def validate_partition(arrays: dict[str, np.ndarray], expected_shots: int | None = None) -> None:
    required = {"detectors", "observable", "nominal_prediction", "burst_prediction"}
    if not required.issubset(arrays):
        raise Stage2Error(f"Partition missing arrays: {sorted(required - set(arrays))}")
    d = binary_array("detectors", arrays["detectors"])
    y = binary_array("observable", arrays["observable"])
    p = binary_array("nominal prediction", arrays["nominal_prediction"])
    b = binary_array("burst prediction", arrays["burst_prediction"])
    n = len(d)
    if expected_shots is not None and n != expected_shots:
        raise Stage2Error(f"Expected {expected_shots} shots, found {n}")
    if d.ndim != 2 or d.shape[1] != 40:
        raise Stage2Error(f"Expected detector shape [shots,40], got {d.shape}")
    if y.shape != (n,) or p.shape != (n,) or b.shape != (n,):
        raise Stage2Error(f"Observable/prediction rows do not align with detectors: {y.shape},{p.shape},{b.shape}")


def partition_hash(arrays: dict[str, np.ndarray]) -> dict[str, str]:
    return {name: hash_array(arrays[name]) for name in sorted(arrays)}


def paired_training_hashes(root_parts: dict) -> dict[str, dict[str, dict[str, str]]]:
    """Stable hashes proving every architecture received the same root arrays."""
    return {split: {condition: partition_hash(root_parts[split][condition])
                    for condition in CONDITIONS} for split in SPLIT_NAMES}


def restore_best_model_state(model: torch.nn.Module, best_state: dict[str, torch.Tensor]) -> None:
    if not best_state:
        raise Stage2Error("Cannot restore an empty best-validation checkpoint")
    model.load_state_dict(best_state)


def partition_paths(root_id: str, split: str, condition: str) -> tuple[Path, Path]:
    folder = RAW_DIR / root_id
    stem = f"{split}__{condition}"
    return folder / f"{stem}.npz", folder / f"{stem}.json"


def load_partition(root_id: str, split: str, condition: str,
                   expected_shots: int | None = None) -> dict[str, np.ndarray] | None:
    archive, meta_path = partition_paths(root_id, split, condition)
    if not archive.exists() and not meta_path.exists():
        return None
    if not archive.exists() or not meta_path.exists():
        raise Stage2Error(f"Incomplete partition pair: {archive} / {meta_path}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("archive_sha256") != sha256_file(archive):
        raise Stage2Error(f"Partition archive integrity failure: {archive}")
    with np.load(archive, allow_pickle=False) as z:
        arrays = {name: z[name] for name in z.files}
    validate_partition(arrays, expected_shots)
    if partition_hash(arrays) != meta.get("array_sha256"):
        raise Stage2Error(f"Partition array hashes failed: {archive}")
    if (meta.get("root_id"), meta.get("split"), meta.get("condition")) != (root_id, split, condition):
        raise Stage2Error(f"Partition filename/metadata mapping mismatch: {archive}")
    return arrays


def save_partition(root_id: str, split: str, condition: str,
                   arrays: dict[str, np.ndarray], seed: int,
                   extra_metadata: dict | None = None) -> dict:
    validate_partition(arrays)
    archive, meta_path = partition_paths(root_id, split, condition)
    if archive.exists() or meta_path.exists():
        existing = load_partition(root_id, split, condition, len(arrays["observable"]))
        if existing is None or partition_hash(existing) != partition_hash(arrays):
            raise Stage2Error(f"Refusing to overwrite different partition: {archive}")
        return json.loads(meta_path.read_text(encoding="utf-8"))
    arr_hashes = partition_hash(arrays)
    archive_hash = atomic_npz(archive, arrays)
    payload = {
        "root_id": root_id, "split": split, "condition": condition,
        "seed": int(seed), "shots": int(len(arrays["observable"])),
        "detector_count": 40, "observable_count": 1,
        "array_sha256": arr_hashes, "archive_sha256": archive_hash,
        "paired_identity_sha256": sha256_bytes("".join(arr_hashes[k] for k in ("detectors", "observable")).encode()),
        "burst_prediction_status": ("burst-informed matcher output" if condition == "synthetic_spatial_burst"
                                     else "not applicable; nominal prediction copied for schema alignment"),
        "saved_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if extra_metadata:
        payload.update(extra_metadata)
    atomic_json(meta_path, payload)
    return payload


def prepare_context(cfg: dict) -> dict:
    c = cfg["circuit"]
    circuits = {
        "nominal": build_spatial_burst_circuit(
            memory_basis=c["memory_basis"], regime=c["pauli_regime"], distance=c["distance"],
            rounds=c["rounds"], gate_p=c["gate_probability"],
            measurement_p=c["measurement_probability"], bias_ratio=c["bias_ratio"],
            burst_probability=c["conditions"]["nominal"]["burst_probability_per_round"],
            burst_pair=tuple(c["conditions"]["nominal"]["burst_pair_data_qubits"]),
        ),
        "synthetic_spatial_burst": build_spatial_burst_circuit(
            memory_basis=c["memory_basis"], regime=c["pauli_regime"], distance=c["distance"],
            rounds=c["rounds"], gate_p=c["gate_probability"],
            measurement_p=c["measurement_probability"], bias_ratio=c["bias_ratio"],
            burst_probability=c["conditions"]["synthetic_spatial_burst"]["burst_probability_per_round"],
            burst_pair=tuple(c["conditions"]["synthetic_spatial_burst"]["burst_pair_data_qubits"]),
        ),
    }
    signatures = {(circuit.num_detectors, circuit.num_observables) for circuit in circuits.values()}
    if signatures != {(40, 1)}:
        raise Stage2Error(f"Circuit detector/observable signature changed: {signatures}")
    coordinate_maps = [circuits[key].get_detector_coordinates() for key in CONDITIONS]
    if coordinate_maps[0] != coordinate_maps[1] or sorted(coordinate_maps[0]) != list(range(40)):
        raise Stage2Error("Nominal and burst detector ID/coordinate maps differ")
    dems, matchers = {}, {}
    for condition, circuit in circuits.items():
        dem, matcher = build_matching(circuit, enable_correlations=True)
        if (dem.num_detectors, dem.num_observables) != (40, 1) or matcher.num_detectors != 40:
            raise Stage2Error(f"DEM/matching dimensions invalid for {condition}")
        dems[condition], matchers[condition] = dem, matcher
    return {"circuits": circuits, "dems": dems, "matchers": matchers,
            "coordinates": coordinate_maps[0],
            "circuit_sha256": {k: sha256_bytes(str(v).encode()) for k, v in circuits.items()},
            "dem_sha256": {k: sha256_bytes(str(v).encode()) for k, v in dems.items()}}


def sample_arrays(sampler, shots: int, context: dict, condition: str) -> dict[str, np.ndarray]:
    detectors, observables = sampler.sample(shots, separate_observables=True)
    detectors = binary_array("Stim detectors", detectors)
    observables = binary_array("Stim observables", observables)
    if detectors.shape != (shots, 40) or observables.shape != (shots, 1):
        raise Stage2Error(f"Stim shape mismatch: {detectors.shape} / {observables.shape}")
    nominal = np.asarray(context["matchers"]["nominal"].decode_batch(detectors), dtype=np.uint8).reshape(-1)
    if condition == "synthetic_spatial_burst":
        burst = np.asarray(context["matchers"]["synthetic_spatial_burst"].decode_batch(detectors), dtype=np.uint8).reshape(-1)
    else:
        burst = nominal.copy()
    arrays = {
        "detectors": np.ascontiguousarray(detectors),
        "observable": np.ascontiguousarray(observables[:, 0]),
        "nominal_prediction": np.ascontiguousarray(binary_array("nominal decoder predictions", nominal)),
        "burst_prediction": np.ascontiguousarray(binary_array("burst decoder predictions", burst)),
    }
    validate_partition(arrays, shots)
    return arrays


def save_prefix(root_id: str, arrays: dict[str, np.ndarray], seed: int) -> str:
    path = RAW_DIR / root_id / "training__nominal_prefix256.npz"
    if path.exists():
        with np.load(path, allow_pickle=False) as z:
            saved = {k: z[k] for k in z.files}
        if partition_hash(saved) != partition_hash(arrays):
            raise Stage2Error("Dry-run prefix does not reproduce from the frozen stream seed")
        return sha256_file(path)
    return atomic_npz(path, arrays)


def sigmoid(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    return 1.0 / (1.0 + np.exp(-np.clip(x, -60, 60)))


def nll(logits: np.ndarray, labels: np.ndarray) -> float:
    z = np.clip(np.asarray(logits, dtype=np.float64), -60, 60)
    y = np.asarray(labels, dtype=np.float64)
    return float(np.mean(np.logaddexp(0.0, z) - y * z))


def residual_target(data: dict[str, np.ndarray]) -> np.ndarray:
    return np.bitwise_xor(data["observable"], data["nominal_prediction"]).astype(np.uint8)


def choose_temperature(logits: dict[str, np.ndarray], data: dict[str, dict], grid: list[float]) -> float:
    candidates = []
    for temp in grid:
        score = float(np.mean([nll(logits[c] / float(temp), residual_target(data[c])) for c in CONDITIONS]))
        candidates.append((score, abs(float(temp) - 1.0), float(temp)))
    return min(candidates)[2]


def choose_threshold(probabilities: dict[str, np.ndarray], data: dict[str, dict]) -> float:
    candidates = []
    grid = [i / 100 for i in range(1, 100)]
    for threshold in grid:
        lers = []
        for condition in CONDITIONS:
            correction = (probabilities[condition] >= threshold).astype(np.uint8)
            pred = data[condition]["nominal_prediction"] ^ correction
            lers.append(float(np.mean(pred ^ data[condition]["observable"])))
        candidates.append((float(np.mean(lers)), abs(threshold - 0.5), threshold))
    return min(candidates)[2]


def model_factory(name: str, coords: dict) -> torch.nn.Module:
    if name == "historical_residual_position_cnn":
        return HistoricalResidualPositionCNN(coords, channels=4, head_width=16, dropout=0.05)
    if name == "residual_position_v2":
        return ResidualPositionCNNV2(coords, channels=4, head_width=32, dropout=0.05)
    if name == "factorized_spatiotemporal_residual":
        return FactorizedSpatialTemporalResidualCNN(coords, channels=4, head_width=32, dropout=0.05)
    raise Stage2Error(f"Unknown frozen model name: {name}")


def torch_state_hash(state: dict[str, torch.Tensor]) -> str:
    return state_dict_hash(state)


def selected_model_paths(root_id: str, model_name: str) -> tuple[Path, Path]:
    base = RAW_DIR / root_id / "selections" / model_name
    return base.with_suffix(".json"), CHECKPOINT_DIR / root_id / f"{model_name}_selected.pt"


def checkpoint_paths(root_id: str, model_name: str) -> tuple[Path, Path]:
    base = CHECKPOINT_DIR / root_id / f"{model_name}"
    return base.with_name(base.name + "_a.pt"), base.with_name(base.name + "_b.pt"), base.with_suffix(".json")


def atomic_checkpoint(root_id: str, model_name: str, payload: dict) -> dict:
    slot_a, slot_b, manifest_path = checkpoint_paths(root_id, model_name)
    old = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
    active = old.get("current", {}).get("file") if old else None
    target = slot_b if active == slot_a.name else slot_a
    digest = atomic_torch_save(target, payload)
    record = {"file": target.name, "sha256": digest, "completed_epochs": int(payload["completed_epochs"]),
              "model": model_name, "root_id": root_id, "config_sha256": payload["config_sha256"]}
    manifest = {"current": record, "previous": old.get("current") if old else None,
                "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    atomic_json(manifest_path, manifest)
    return manifest


def load_checkpoint(root_id: str, model_name: str, config_sha: str) -> dict | None:
    _, _, manifest_path = checkpoint_paths(root_id, model_name)
    if not manifest_path.exists():
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors = []
    for record in (manifest.get("current"), manifest.get("previous")):
        if not record:
            continue
        path = CHECKPOINT_DIR / root_id / record["file"]
        try:
            if sha256_file(path) != record["sha256"]:
                raise Stage2Error("checkpoint file SHA-256 mismatch")
            payload = torch.load(path, map_location="cpu", weights_only=False)
            if payload.get("config_sha256") != config_sha or payload.get("model_name") != model_name:
                raise Stage2Error("checkpoint model/config identity mismatch")
            return payload
        except Exception as exc:
            errors.append(f"{record.get('file')}: {exc}")
    raise Stage2Error("No valid checkpoint slot: " + "; ".join(errors))


def resource_snapshot(device: torch.device) -> dict:
    proc = psutil.Process(os.getpid())
    rss = int(proc.memory_info().rss)
    if device.type == "cuda":
        torch.cuda.synchronize(device)
        allocated = int(torch.cuda.memory_allocated(device))
        peak = int(torch.cuda.max_memory_allocated(device))
    else:
        allocated = peak = 0
    free_disk = shutil.disk_usage(ROOT).free
    return {"process_rss_bytes": rss, "cuda_allocated_bytes": allocated,
            "cuda_peak_allocated_bytes": peak, "free_disk_bytes": int(free_disk)}


def enforce_resources(cfg: dict, device: torch.device, *, wall_seconds: float,
                      cuda_seconds: float) -> dict:
    snap = resource_snapshot(device)
    limits = cfg["resources"]
    if wall_seconds > limits["maximum_wall_seconds"]:
        raise ResourceLimitError("Wall-clock limit exceeded")
    if cuda_seconds > limits["maximum_measured_cuda_training_validation_seconds"]:
        raise ResourceLimitError("CUDA-time limit exceeded")
    if snap["free_disk_bytes"] < limits["minimum_free_disk_gib_before_sampling"] * (1024 ** 3):
        raise ResourceLimitError("Free-disk limit violated")
    if snap["process_rss_bytes"] > limits["maximum_process_rss_gib"] * (1024 ** 3):
        raise ResourceLimitError("Process RSS limit exceeded")
    if snap["cuda_peak_allocated_bytes"] > limits["maximum_cuda_allocated_gib"] * (1024 ** 3):
        raise ResourceLimitError("CUDA allocation limit exceeded")
    return snap


def set_determinism(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed % (2 ** 32))
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.use_deterministic_algorithms(True)


def evaluate_logits(model: torch.nn.Module, data_by_condition: dict[str, dict],
                    prevalence: float, device: torch.device, cuda_counter: list[float]) -> dict[str, np.ndarray]:
    model.eval()
    results = {}
    prior = math.log(max(prevalence, 1e-8) / max(1.0 - prevalence, 1e-8))
    with torch.inference_mode():
        for condition in CONDITIONS:
            d = data_by_condition[condition]["detectors"]
            pm = data_by_condition[condition]["nominal_prediction"]
            outputs = []
            for start in range(0, len(d), 1024):
                x = torch.as_tensor(d[start:start + 1024], dtype=torch.float32, device=device)
                p = torch.as_tensor(pm[start:start + 1024], dtype=torch.float32, device=device)
                t0 = time.perf_counter()
                logits = model(x, p).float()
                if not torch.isfinite(logits).all():
                    raise Stage2Error("Non-finite validation logits")
                if device.type == "cuda":
                    torch.cuda.synchronize(device)
                    cuda_counter[0] += time.perf_counter() - t0
                outputs.append(logits.detach().cpu().numpy().astype(np.float64) + prior)
            results[condition] = np.concatenate(outputs)
    return results


def _copy_state(state: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    return {k: v.detach().cpu().clone() for k, v in state.items()}


def balanced_batches(train: dict[str, dict], batch_size: int,
                     rng: np.random.Generator, order_rng: np.random.Generator) -> list[tuple[str, np.ndarray]]:
    jobs = []
    for condition in CONDITIONS:
        labels = residual_target(train[condition])
        pos, neg = np.flatnonzero(labels == 1), np.flatnonzero(labels == 0)
        if not len(pos) or not len(neg):
            raise Stage2Error(f"Balanced sampler lacks a class in {condition}")
        for start in range(0, len(labels), batch_size):
            count = min(batch_size, len(labels) - start)
            n_pos = (count + 1) // 2
            n_neg = count - n_pos
            ids = np.concatenate((rng.choice(pos, n_pos, replace=len(pos) < n_pos),
                                  rng.choice(neg, n_neg, replace=len(neg) < n_neg)))
            rng.shuffle(ids)
            jobs.append((condition, ids.astype(np.int32)))
    order_rng.shuffle(jobs)
    return jobs


def train_and_select(root_id: str, model_name: str, root_parts: dict,
                     coords: dict, cfg: dict, cfg_sha: str,
                     device: torch.device, start_time: float,
                     runtime: dict) -> dict:
    selection_path, selected_weights_path = selected_model_paths(root_id, model_name)
    if selection_path.exists() and selected_weights_path.exists():
        record = json.loads(selection_path.read_text(encoding="utf-8"))
        if record.get("final_development_data_accessed") is not False:
            raise Stage2Error(f"Selection file shows final-label access before selection for {root_id}/{model_name}")
        if (record.get("root_id"), record.get("model")) != (root_id, model_name):
            raise Stage2Error(f"Selection identity mismatch for {root_id}/{model_name}")
        if sha256_file(selected_weights_path) != record.get("selected_weights_file_sha256"):
            raise Stage2Error(f"Selected model checkpoint hash mismatch: {selected_weights_path}")
        payload = torch.load(selected_weights_path, map_location="cpu", weights_only=False)
        if payload.get("config_sha256") != cfg_sha or payload.get("state_dict_sha256") != record.get("selected_state_dict_sha256"):
            raise Stage2Error(f"Selected model/config identity mismatch: {selected_weights_path}")
        return record

    train = root_parts["training"]
    monitor = root_parts["monitor"]
    calibration = root_parts["probability_calibration"]
    threshold_data = root_parts["threshold_selection"]
    labels_by_cond = {c: residual_target(train[c]) for c in CONDITIONS}
    positive_counts = {c: int(labels_by_cond[c].sum()) for c in CONDITIONS}
    additional_positive_counts = {
        split: {c: int(residual_target(root_parts[split][c]).sum()) for c in CONDITIONS}
        for split in ("monitor", "probability_calibration", "threshold_selection")
    }
    minimum = int(cfg["rare_residual_target_safeguards"]["minimum_unique_training_residual_positives_per_root_condition"])
    if any(positive_counts[c] < minimum for c in CONDITIONS):
        raise Stage2Error(f"Insufficient residual positives at {root_id}: {positive_counts}; minimum={minimum}")
    total_positive = sum(positive_counts.values())
    total_train = sum(len(labels_by_cond[c]) for c in CONDITIONS)
    prevalence = total_positive / total_train
    if not 0.0 < prevalence < 1.0:
        raise Stage2Error(f"Invalid pooled residual prevalence={prevalence}")

    torch_seed = seed_for(runtime["inventory"], root_id, model=model_name, purpose="torch")
    sample_seed = seed_for(runtime["inventory"], root_id, model=model_name, purpose="balanced_sampling")
    order_seed = seed_for(runtime["inventory"], root_id, model=model_name, purpose="batch_order")
    set_determinism(torch_seed)
    model = model_factory(model_name, coords).to(device)
    opt_cfg = cfg["training"]
    optimizer = torch.optim.AdamW(model.parameters(), lr=opt_cfg["learning_rate"],
                                  weight_decay=opt_cfg["weight_decay"])
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer,
        step_size=opt_cfg["scheduler"]["step_size_epochs"], gamma=opt_cfg["scheduler"]["gamma"])
    rng = np.random.default_rng(sample_seed)
    order_rng = np.random.default_rng(order_seed)
    ckpt = load_checkpoint(root_id, model_name, cfg_sha)
    history: list[dict] = []
    if ckpt:
        model.load_state_dict(ckpt["model_state"])
        optimizer.load_state_dict(ckpt["optimizer_state"])
        scheduler.load_state_dict(ckpt["scheduler_state"])
        history = list(ckpt["history"])
        completed_epochs = int(ckpt["completed_epochs"])
        best_state = ckpt["best_state"]
        best_nll = float(ckpt["best_monitor_nll"])
        best_epoch = int(ckpt["best_epoch"])
        patience = int(ckpt["patience"])
        steps = int(ckpt["steps"])
        positive_draws_total = dict(ckpt.get("positive_draws_total", {c: 0 for c in CONDITIONS}))
        rng.bit_generator.state = ckpt["sampling_rng_state"]
        order_rng.bit_generator.state = ckpt["order_rng_state"]
        torch.set_rng_state(ckpt["torch_rng_state"].cpu())
        if device.type == "cuda" and ckpt.get("cuda_rng_state") is not None:
            torch.cuda.set_rng_state_all(ckpt["cuda_rng_state"])
    else:
        completed_epochs, best_state, best_nll, best_epoch, patience, steps = 0, None, float("inf"), 0, 0, 0
        positive_draws_total = {c: 0 for c in CONDITIONS}

    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)
    while completed_epochs < int(opt_cfg["maximum_epochs"]):
        model.train()
        batches = balanced_batches(train, int(opt_cfg["batch_size"]), rng, order_rng)
        if len(batches) != 80:
            raise Stage2Error(f"Frozen optimizer schedule changed: expected 80 batches/epoch, got {len(batches)}")
        epoch_positive_draws = {c: 0 for c in CONDITIONS}
        for condition, ids in batches:
            d = train[condition]["detectors"][ids]
            pm = train[condition]["nominal_prediction"][ids]
            y = labels_by_cond[condition][ids].astype(np.float32)
            epoch_positive_draws[condition] += int(y.sum())
            x_t = torch.as_tensor(d, dtype=torch.float32, device=device)
            p_t = torch.as_tensor(pm, dtype=torch.float32, device=device)
            y_t = torch.as_tensor(y, dtype=torch.float32, device=device)
            tic = time.perf_counter()
            optimizer.zero_grad(set_to_none=True)
            logits = model(x_t, p_t).float()
            loss = F.binary_cross_entropy_with_logits(logits, y_t)
            if not torch.isfinite(loss):
                raise Stage2Error("Non-finite training loss")
            loss.backward()
            if any(p.grad is not None and not torch.isfinite(p.grad).all() for p in model.parameters()):
                raise Stage2Error("Non-finite training gradient")
            optimizer.step()
            if device.type == "cuda":
                torch.cuda.synchronize(device)
                runtime["cuda_seconds"] += time.perf_counter() - tic
            steps += 1
            enforce_resources(cfg, device, wall_seconds=time.perf_counter() - start_time,
                              cuda_seconds=runtime["cuda_seconds"])

        if any(epoch_positive_draws[c] != 5000 for c in CONDITIONS):
            raise Stage2Error(f"Frozen condition-wise balanced positive draw count changed: {epoch_positive_draws}")
        for condition in CONDITIONS:
            positive_draws_total[condition] += epoch_positive_draws[condition]

        eval_before = runtime["cuda_counter"][0]
        monitor_logits = evaluate_logits(model, monitor, prevalence, device, runtime["cuda_counter"])
        runtime["cuda_seconds"] += runtime["cuda_counter"][0] - eval_before
        monitor_score = float(np.mean([nll(monitor_logits[c], residual_target(monitor[c])) for c in CONDITIONS]))
        if not math.isfinite(monitor_score):
            raise Stage2Error("Non-finite equal-condition monitor NLL")
        improved = monitor_score < best_nll - 1e-9
        if improved:
            best_nll = monitor_score
            best_state = _copy_state(model.state_dict())
            best_epoch = completed_epochs + 1
            patience = 0
        else:
            patience += 1
        history.append({"epoch": completed_epochs + 1, "monitor_equal_condition_nll": monitor_score,
                        "improved": improved, "positive_counts_train": positive_counts})
        scheduler.step()
        completed_epochs += 1
        checkpoint_payload = {
            "model_name": model_name, "root_id": root_id, "config_sha256": cfg_sha,
            "model_state": _copy_state(model.state_dict()), "optimizer_state": optimizer.state_dict(),
            "scheduler_state": scheduler.state_dict(), "completed_epochs": completed_epochs,
            "best_state": best_state, "best_monitor_nll": best_nll, "best_epoch": best_epoch,
            "patience": patience, "steps": steps, "history": history,
            "positive_draws_total": positive_draws_total,
            "sampling_rng_state": rng.bit_generator.state, "order_rng_state": order_rng.bit_generator.state,
            "torch_rng_state": torch.get_rng_state().cpu(),
            "cuda_rng_state": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None,
        }
        atomic_checkpoint(root_id, model_name, checkpoint_payload)
        runtime["max_epoch_count"] = max(runtime["max_epoch_count"], completed_epochs)
        if patience >= int(opt_cfg["early_stopping_patience"]):
            break
        enforce_resources(cfg, device, wall_seconds=time.perf_counter() - start_time,
                          cuda_seconds=runtime["cuda_seconds"])
    if best_state is None:
        raise Stage2Error("No monitor-selected checkpoint exists")
    restore_best_model_state(model, best_state)
    selected_hash = torch_state_hash(best_state)

    eval_before = runtime["cuda_counter"][0]
    cal_logits = evaluate_logits(model, calibration, prevalence, device, runtime["cuda_counter"])
    runtime["cuda_seconds"] += runtime["cuda_counter"][0] - eval_before
    temperature = choose_temperature(cal_logits, calibration, cfg["selection"]["temperature_grid"])
    eval_before = runtime["cuda_counter"][0]
    threshold_logits = evaluate_logits(model, threshold_data, prevalence, device, runtime["cuda_counter"])
    runtime["cuda_seconds"] += runtime["cuda_counter"][0] - eval_before
    probs = {c: sigmoid(threshold_logits[c] / temperature) for c in CONDITIONS}
    threshold = choose_threshold(probs, threshold_data)
    weight_payload = {"model_name": model_name, "root_id": root_id,
                      "config_sha256": cfg_sha, "model_state": best_state,
                      "state_dict_sha256": selected_hash}
    selected_file_hash = atomic_torch_save(selected_weights_path, weight_payload)
    record = {
        "root_id": root_id, "model": model_name, "status": "selection_frozen",
        "selected_weights_path": str(selected_weights_path.relative_to(ROOT)).replace("\\", "/"),
        "selected_weights_file_sha256": selected_file_hash,
        "selected_state_dict_sha256": selected_hash,
        "train_partition_array_hashes": {c: partition_hash(train[c]) for c in CONDITIONS},
        "monitor_partition_array_hashes": {c: partition_hash(monitor[c]) for c in CONDITIONS},
        "calibration_partition_array_hashes": {c: partition_hash(calibration[c]) for c in CONDITIONS},
        "threshold_partition_array_hashes": {c: partition_hash(threshold_data[c]) for c in CONDITIONS},
        "shared_partition_array_hashes": paired_training_hashes(root_parts),
        "positive_counts_by_condition": positive_counts,
        "positive_counts_by_split_and_condition": {
            "training": positive_counts, **additional_positive_counts,
        },
        "positive_draws_total_by_condition": positive_draws_total,
        "positive_example_reuse_ratio_by_condition": {
            c: float(positive_draws_total[c] / positive_counts[c]) for c in CONDITIONS
        },
        "balanced_positive_draws_per_condition_epoch": 5000,
        "pooled_residual_training_prevalence": prevalence,
        "best_epoch": best_epoch, "best_monitor_nll": best_nll,
        "epochs_completed": completed_epochs, "optimizer_steps": steps,
        "temperature": temperature, "threshold": threshold,
        "selection_data": "checkpoint: monitor; temperature: probability_calibration; threshold: threshold_selection",
        "final_development_data_accessed": False,
        "selection_frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "history": history, "parameter_count": parameter_count(model),
    }
    selection_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_json(selection_path, record)
    return record


def selected_model(root_id: str, model_name: str, coords: dict,
                   device: torch.device, cfg_sha: str) -> tuple[torch.nn.Module, dict]:
    selection_path, weights_path = selected_model_paths(root_id, model_name)
    if not selection_path.exists() or not weights_path.exists():
        raise Stage2Error(f"Selection is not frozen for {root_id}/{model_name}")
    record = json.loads(selection_path.read_text(encoding="utf-8"))
    if record.get("final_development_data_accessed") is not False:
        raise Stage2Error("Selection metadata permits final label access before freezing")
    if sha256_file(weights_path) != record["selected_weights_file_sha256"]:
        raise Stage2Error("Selected model file hash mismatch")
    payload = torch.load(weights_path, map_location="cpu", weights_only=False)
    if payload.get("config_sha256") != cfg_sha or payload.get("state_dict_sha256") != record["selected_state_dict_sha256"]:
        raise Stage2Error("Selected model payload does not match frozen configuration/state hash")
    model = model_factory(model_name, coords).to(device)
    model.load_state_dict(payload["model_state"])
    model.eval()
    return model, record


def frozen_selection_hashes() -> list[dict]:
    records = []
    for ridx in range(5):
        rid = f"dev-root-{ridx:02d}"
        for model_name in MODEL_ORDER:
            selection_path, weights_path = selected_model_paths(rid, model_name)
            if not selection_path.is_file() or not weights_path.is_file():
                raise Stage2Error(f"Final sampling blocked; selection incomplete for {rid}/{model_name}")
            selection = json.loads(selection_path.read_text(encoding="utf-8"))
            if selection.get("final_development_data_accessed") is not False:
                raise Stage2Error(f"Selection {rid}/{model_name} is not pre-evaluation")
            if sha256_file(weights_path) != selection.get("selected_weights_file_sha256"):
                raise Stage2Error(f"Selected weight hash mismatch for {rid}/{model_name}")
            records.append({"root_id": rid, "model": model_name,
                            "selection_sha256": sha256_file(selection_path),
                            "weights_sha256": sha256_file(weights_path)})
    if len(records) != 15:
        raise Stage2Error(f"Expected 15 frozen model choices, found {len(records)}")
    return records


def selection_manifest_payload(records: list[dict], freeze: dict, cfg_sha: str) -> dict:
    """Create the immutable list of all 15 choices required before test-like scoring."""
    expected = {(f"dev-root-{i:02d}", model) for i in range(5) for model in MODEL_ORDER}
    actual = {(row["root_id"], row["model"]) for row in records}
    if actual != expected or len(records) != 15:
        raise Stage2Error("The global selection manifest must contain exactly 15 unique model/root choices")
    body = {
        "status": "ALL_SELECTIONS_FROZEN_BEFORE_FINAL_DEVELOPMENT",
        "freeze_protocol_id_sha256": freeze["protocol_id_sha256"],
        "config_sha256": cfg_sha,
        "final_development_accessed_at_freeze": False,
        "selections": records,
    }
    body["manifest_sha256"] = sha256_bytes(json.dumps(body, sort_keys=True, separators=(",", ":")).encode())
    return body


def verify_selection_manifest(path: Path, expected: dict) -> None:
    if not path.is_file():
        raise Stage2Error("All model choices must be frozen before final-development sampling")
    saved = json.loads(path.read_text(encoding="utf-8"))
    if saved != expected:
        raise Stage2Error("Persisted global selection manifest differs from frozen model choices")
    check = dict(saved)
    digest = check.pop("manifest_sha256", None)
    actual = sha256_bytes(json.dumps(check, sort_keys=True, separators=(",", ":")).encode())
    if digest != actual:
        raise Stage2Error("Global selection manifest self-hash is invalid")


def generate_final_partition(root_id: str, condition: str, context: dict,
                             inventory: dict, cfg: dict,
                             all_selections: list[dict]) -> tuple[dict[str, np.ndarray], dict]:
    shots = int(cfg["shots_per_root_condition"]["final_development_evaluation"])
    expected_keys = {(f"dev-root-{i:02d}", model) for i in range(5) for model in MODEL_ORDER}
    if len(all_selections) != 15 or {(x["root_id"], x["model"]) for x in all_selections} != expected_keys:
        raise Stage2Error("Refusing final-development access before every model/root choice is frozen")
    if frozen_selection_hashes() != all_selections:
        raise Stage2Error("Model/root choices changed after the global selection barrier")
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    manifest_expected = selection_manifest_payload(all_selections, freeze, sha256_file(CONFIG_PATH))
    verify_selection_manifest(RAW_DIR / "selection_manifest_before_final.json", manifest_expected)
    # Causality/leakage gate: all model selections must be atomically frozen first.
    existing = load_partition(root_id, "final_development_evaluation", condition, shots)
    if existing is not None:
        meta_path = partition_paths(root_id, "final_development_evaluation", condition)[1]
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        old = meta.get("selection_hashes_before_final_sampling")
        if old is None:
            raise Stage2Error("Existing final-development partition has no pre-sampling selection provenance")
        if old != all_selections:
            raise Stage2Error("Final partition was generated under a different selection manifest")
        return existing, meta
    seed = seed_for(inventory, root_id, split="final_development_evaluation", condition=condition)
    sampler = context["circuits"][condition].compile_detector_sampler(seed=seed)
    arrays = sample_arrays(sampler, shots, context, condition)
    # Save evidence tying the evaluation partition to the exact frozen selections.
    meta = save_partition(root_id, "final_development_evaluation", condition, arrays, seed,
                          extra_metadata={"selection_hashes_before_final_sampling": all_selections})
    return arrays, meta


def training_sample_stream(root_id: str, context: dict, inventory: dict,
                           cfg: dict, status: dict, runtime: dict,
                           device: torch.device, start_time: float) -> dict[str, np.ndarray]:
    """Dry-run the first 256 rows, then continue the same Stim sampler to 10K."""
    split, condition = "training", "nominal"
    full = load_partition(root_id, split, condition,
                          int(cfg["shots_per_root_condition"][split]))
    if full is not None:
        return full
    shots = int(cfg["shots_per_root_condition"][split])
    seed = seed_for(inventory, root_id, split=split, condition=condition)
    sampler = context["circuits"][condition].compile_detector_sampler(seed=seed)
    prefix_n = 256
    prefix = sample_arrays(sampler, prefix_n, context, condition)
    prefix_hash = save_prefix(root_id, prefix, seed)
    status["dry_run_prefix"] = {"root_id": root_id, "condition": condition, "shots": prefix_n,
                                "seed": seed, "array_sha256": partition_hash(prefix),
                                "archive_sha256": prefix_hash, "counted_within_training_partition": True}
    write_status(status)
    report_path = RUN_DIR / "dry_run_report.json"
    if not report_path.exists():
        dry = bounded_dry_run(prefix, context, cfg, device, runtime, start_time)
        atomic_json(report_path, dry)
        status["dry_run_status"] = dry["status"]
        status["dry_run_report_sha256"] = sha256_file(report_path)
        write_status(status)
        if dry["status"] != "PASS_WITHIN_FROZEN_LIMITS":
            raise ResourceLimitError("256-shot end-to-end estimate exceeded a frozen resource limit")
    else:
        dry = json.loads(report_path.read_text(encoding="utf-8"))
        if dry.get("status") != "PASS_WITHIN_FROZEN_LIMITS":
            raise ResourceLimitError("Saved 256-shot dry run did not pass frozen resource limits")

    rest = sample_arrays(sampler, shots - prefix_n, context, condition)
    arrays = {name: np.concatenate((prefix[name], rest[name]), axis=0) for name in prefix}
    validate_partition(arrays, shots)
    save_partition(root_id, split, condition, arrays, seed)
    return arrays


def bounded_dry_run(prefix: dict[str, np.ndarray], context: dict,
                    cfg: dict, device: torch.device, runtime: dict,
                    start_time: float) -> dict:
    """Small transient throughput probe using only the allocated 256-row prefix."""
    if len(prefix["observable"]) != 256:
        raise Stage2Error("Dry run must use exactly the first 256 allocated shots")
    batch = prefix
    y = residual_target(batch).astype(np.float32)
    x = torch.as_tensor(batch["detectors"], dtype=torch.float32, device=device)
    pm = torch.as_tensor(batch["nominal_prediction"], dtype=torch.float32, device=device)
    y_t = torch.as_tensor(y, dtype=torch.float32, device=device)
    per_model = {}
    training_seconds = []
    inference_seconds = []
    peak_bytes = 0
    rss_before = psutil.Process(os.getpid()).memory_info().rss
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)
    for index, name in enumerate(MODEL_ORDER):
        seed = seed_for(runtime["inventory"], "dev-root-00", model=name, purpose="torch")
        set_determinism(seed)
        model = model_factory(name, context["coordinates"]).to(device)
        optimizer = torch.optim.AdamW(model.parameters(), lr=cfg["training"]["learning_rate"],
                                      weight_decay=cfg["training"]["weight_decay"])
        model.train()
        step_times = []
        for _ in range(5):
            tic = time.perf_counter()
            optimizer.zero_grad(set_to_none=True)
            logits = model(x, pm).float()
            loss = F.binary_cross_entropy_with_logits(logits, y_t)
            loss.backward()
            optimizer.step()
            if device.type == "cuda":
                torch.cuda.synchronize(device)
                runtime["cuda_seconds"] += time.perf_counter() - tic
            step_times.append(time.perf_counter() - tic)
        model.eval()
        with torch.inference_mode():
            for _ in range(3):
                tic = time.perf_counter()
                model(x, pm)
                if device.type == "cuda":
                    torch.cuda.synchronize(device)
                    runtime["cuda_seconds"] += time.perf_counter() - tic
                inference_seconds.append(time.perf_counter() - tic)
        median_step = float(np.median(step_times))
        training_seconds.append(median_step)
        per_model[name] = {"parameter_count": parameter_count(model),
                           "step_seconds_median": median_step,
                           "training_shots_per_second": 256 / median_step,
                           "inference_seconds_median": float(np.median(inference_seconds[-3:])),
                           "training_steps_timed": len(step_times), "unique_samples_used": 256}
        if device.type == "cuda":
            peak_bytes = max(peak_bytes, int(torch.cuda.max_memory_allocated(device)))
        del optimizer, model
        if device.type == "cuda":
            torch.cuda.empty_cache()

    # Measure the actual fixed and burst matcher calls on this same paired prefix.
    decode_times = {}
    for name in CONDITIONS:
        tic = time.perf_counter()
        pred = np.asarray(context["matchers"][name].decode_batch(batch["detectors"])).reshape(-1)
        decode_times[name] = (time.perf_counter() - tic) / len(pred)

    sim_per_shot = float(runtime["dry_sim_seconds"]) / 256.0
    step_p95 = float(max(training_seconds))
    inferred_per_shot = float(np.median(inference_seconds) / 256.0)
    # Conservative cost estimate for all configured work; then add a 2x safety factor.
    total_shots = int(cfg["total_unique_shot_ceiling"])
    fixed_decode_shots = total_shots
    burst_decode_shots = total_shots // 2
    training_steps = int(cfg["training"]["maximum_optimizer_steps_across_15_model_root_jobs"])
    eval_shots = 480_000  # 3 architectures x 5 roots x 2 conditions x (2k+2k+2k+10k).
    gpu_estimate = 2.0 * (step_p95 * training_steps + inferred_per_shot * eval_shots)
    wall_estimate = 2.0 * (sim_per_shot * total_shots
                           + decode_times["nominal"] * fixed_decode_shots
                           + decode_times["synthetic_spatial_burst"] * burst_decode_shots
                           + step_p95 * training_steps + inferred_per_shot * eval_shots)
    snap = resource_snapshot(device)
    resource_limits = cfg["resources"]
    status = "PASS_WITHIN_FROZEN_LIMITS"
    reasons = []
    if wall_estimate > resource_limits["maximum_wall_seconds"]:
        status = "FAIL_RESOURCE_ESTIMATE"; reasons.append("conservative wall-time estimate exceeds cap")
    if gpu_estimate > resource_limits["maximum_measured_cuda_training_validation_seconds"]:
        status = "FAIL_RESOURCE_ESTIMATE"; reasons.append("conservative CUDA estimate exceeds cap")
    if snap["free_disk_bytes"] < resource_limits["minimum_free_disk_gib_before_sampling"] * (1024 ** 3):
        status = "FAIL_RESOURCE_PREFLIGHT"; reasons.append("free disk below cap")
    if snap["process_rss_bytes"] > resource_limits["maximum_process_rss_gib"] * (1024 ** 3):
        status = "FAIL_RESOURCE_PREFLIGHT"; reasons.append("process RSS above cap")
    if peak_bytes > resource_limits["maximum_cuda_allocated_gib"] * (1024 ** 3):
        status = "FAIL_RESOURCE_PREFLIGHT"; reasons.append("CUDA memory above cap")
    runtime["cuda_seconds"] += 0.0
    return {
        "status": status, "scope": "256 unique samples from dev-root-00 nominal training prefix; first 256 rows reused in the 10,000-shot training partition",
        "independent_test_accessed": False, "models": per_model,
        "runtime": {"simulation_prefix_seconds": runtime["dry_sim_seconds"],
                    "matching_seconds_per_shot": decode_times,
                    "training_seconds_per_step_median": training_seconds,
                    "gpu_seconds_used_by_probe": runtime["cuda_seconds"]},
        "memory": {"process_rss_before_bytes": int(rss_before),
                   "process_rss_after_bytes": int(psutil.Process(os.getpid()).memory_info().rss),
                   "cuda_peak_allocated_bytes": int(peak_bytes),
                   "free_disk_bytes": int(snap["free_disk_bytes"])},
        "conservative_estimate": {"wall_seconds_with_2x_safety": wall_estimate,
                                  "cuda_seconds_with_2x_safety": gpu_estimate,
                                  "training_optimizer_steps_max": training_steps,
                                  "evaluation_shots": eval_shots,
                                  "unique_sample_ceiling": total_shots},
        "limits": resource_limits, "failure_reasons": reasons,
        "interpretation": "Transient diagnostic updates were discarded. No model was selected or evaluated; only the already-allocated 256 training-prefix samples were used.",
    }


def generate_partition(root_id: str, split: str, condition: str, context: dict,
                       inventory: dict, cfg: dict, status: dict) -> dict[str, np.ndarray]:
    shots = int(cfg["shots_per_root_condition"][split])
    existing = load_partition(root_id, split, condition, shots)
    if existing is not None:
        return existing
    seed = seed_for(inventory, root_id, split=split, condition=condition)
    sampler = context["circuits"][condition].compile_detector_sampler(seed=seed)
    arrays = sample_arrays(sampler, shots, context, condition)
    meta = save_partition(root_id, split, condition, arrays, seed)
    status.setdefault("partitions", {})[f"{root_id}/{split}/{condition}"] = meta
    status["completed_unique_shots"] = recompute_unique_sample_count()
    write_status(status)
    return arrays


def recompute_unique_sample_count() -> int:
    total = 0
    if not RAW_DIR.exists():
        return 0
    for root_id in (f"dev-root-{i:02d}" for i in range(5)):
        for split in (*SPLIT_NAMES, "final_development_evaluation"):
            for condition in CONDITIONS:
                archive, meta = partition_paths(root_id, split, condition)
                if archive.is_file() and meta.is_file():
                    m = json.loads(meta.read_text(encoding="utf-8"))
                    if m.get("archive_sha256") == sha256_file(archive):
                        total += int(m["shots"])
        prefix = RAW_DIR / root_id / "training__nominal_prefix256.npz"
        # Count a prefix only until its complete partition has been persisted.
        full, _ = partition_paths(root_id, "training", "nominal")
        if prefix.is_file() and not full.is_file():
            total += 256
    return total


def write_status(status: dict) -> None:
    status["updated_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    status["completed_unique_shots"] = recompute_unique_sample_count()
    atomic_json(STATUS_PATH, status)


def atomic_text(path: Path, contents: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    data = contents.replace("\r\n", "\n").encode("utf-8")
    with tmp.open("wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def write_execution_reports(status: dict, audit_result: dict) -> None:
    dry_path = RUN_DIR / "dry_run_report.json"
    dry = json.loads(dry_path.read_text(encoding="utf-8")) if dry_path.is_file() else {}
    lines = [
        "# Q-SHIFT CNN Stage 2 Execution Report\n",
        "This report records a development-only execution. The independent-test allocation remained sealed. Completion is written only after the independent rescore and evidence manifest have passed.\n",
        f"- Independent rescore: **{audit_result.get('status')}**.",
        f"- Unique sampled shots accounted: {recompute_unique_sample_count():,} / 260,000.",
        f"- Completed model/root training jobs: {status.get('completed_model_root_jobs', 0)}/15.",
        f"- Completed final-development roots: {len(status.get('completed_roots', []))}/5.",
        f"- Measured active wall time so far: {status.get('active_wall_seconds', 0):.1f} seconds.",
        f"- Measured training/validation/final inference CUDA time: {status.get('cuda_seconds', 0):.1f} seconds.",
        f"- Device: {status.get('cuda_device', 'unknown')}.",
        f"- Final-development access occurred only after all 15 model/root selections were hashed and frozen: {status.get('all_model_choices_frozen', False)}.",
        "- Independent-test access: false.\n",
        "## Bounded 256-shot diagnostic\n",
        f"Status: {dry.get('status', 'missing')}. It used the first 256 rows from the allocated root-00 nominal training stream and those exact rows were included in that 10,000-shot training partition.\n",
        f"Conservative estimates: {dry.get('conservative_estimate', {})}.\n",
        "## Frozen decision rule\n",
        "The only primary model is ResidualPositionCNNV2. The development gate is an equal-condition mean LER improvement of at least 0.0002, at least four favorable roots, and no condition mean harm greater than 0.0002. This gate is descriptive feasibility evidence, not a confirmatory superiority claim.\n",
    ]
    atomic_text(HERE / "CNN_STAGE2_EXECUTION_REPORT.md", "\n".join(lines))
    gate = audit_result.get("primary_development_gate", {})
    summary = [
        "# Q-SHIFT CNN Stage 2 Competition Summary\n",
        "Q-SHIFT was evaluated in a reproducible Stim simulation with paired detector samples, frozen PyMatching baselines, and three residual CNN designs. The synthetic burst is an experimental stress condition, not a hardware-calibrated noise claim.\n",
        f"- Data status: {audit_result.get('unique_shot_total', 0):,} development shots, five independent roots; no independent-test access.",
        f"- Frozen primary development gate: **{gate.get('status', 'INCONCLUSIVE')}**.",
        "- Interpret the reported root intervals as descriptive. No result from this bounded development study establishes general superiority or hardware compatibility.",
        "- The burst-informed matching comparator has privileged knowledge of the injected burst model.\n",
    ]
    atomic_text(HERE / "CNN_STAGE2_COMPETITION_SUMMARY.md", "\n".join(summary))


def write_evidence_manifest(status: dict, audit_result: dict) -> str:
    files: dict[str, dict] = {}
    runtime_dirs = (RAW_DIR, CHECKPOINT_DIR, PREDICTION_DIR)
    for base in runtime_dirs:
        if not base.exists():
            continue
        for path in sorted(p for p in base.rglob("*") if p.is_file()):
            if path in (STATUS_PATH, LOCK_PATH) or path.name.endswith((".tmp", ".temp")):
                continue
            files[path.relative_to(ROOT).as_posix()] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
    top_level = [
        HERE / "FREEZE.json", HERE / "FREEZE_IMPLEMENTATION_V2.json", HERE / "FREEZE_IMPLEMENTATION_V3.json",
        HERE / "FREEZE_IMPLEMENTATION_V4.json", CONFIG_PATH,
        HERE / "seed_inventory.json", HERE / "seed_audit.json", HERE / "STAGE2_FREEZE_SUPERSESSION.md",
        HERE / "CNN_STAGE2_IMPLEMENTATION_READINESS.md", HERE / "CNN_STAGE2_IMPLEMENTATION_READINESS_V3.md",
        HERE / "STAGE2_FREEZE_SUPERSESSION_V3.md", HERE / "freeze_stage2_v3.py", HERE / "run_stage2.py",
        HERE / "STAGE2_FREEZE_SUPERSESSION_V4.md", HERE / "CNN_STAGE2_IMPLEMENTATION_READINESS_V4.md",
        HERE / "freeze_stage2_v4.py",
        HERE / "audit_stage2.py", HERE / "freeze_stage2_v2.py",
        HERE / "tests" / "test_stage2_runner.py", HERE / "CNN_STAGE2_RESULTS.md",
        HERE / "CNN_STAGE2_INDEPENDENT_AUDIT.md", HERE / "CNN_STAGE2_PER_ROOT.csv",
        HERE / "CNN_STAGE2_EXECUTION_REPORT.md", HERE / "CNN_STAGE2_COMPETITION_SUMMARY.md",
    ]
    for path in top_level:
        if path.is_file():
            files[path.relative_to(ROOT).as_posix()] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
    payload = {
        "status": "EVIDENCE_AUDIT_PASS",
        "freeze_protocol_id_sha256": status["freeze_protocol_id_sha256"],
        "unique_shots": audit_result["unique_shot_total"],
        "independent_test_accessed": False,
        "mutable_status_and_lock_excluded_to_avoid_self_reference": True,
        "files": files,
    }
    manifest_path = HERE / "STAGE2_EVIDENCE_MANIFEST.json"
    atomic_json(manifest_path, payload)
    return sha256_file(manifest_path)


def acquire_lock() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if LOCK_PATH.exists():
        try:
            info = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
            if psutil.pid_exists(int(info["pid"])):
                raise Stage2Error(f"Runner appears active under PID {info['pid']}; refusing a second process")
        except Stage2Error:
            raise
        except Exception:
            raise Stage2Error("Unverifiable lock file; inspect manually rather than deleting it")
        LOCK_PATH.unlink()
    atomic_json(LOCK_PATH, {"pid": os.getpid(), "created": time.time()})


def release_lock() -> None:
    if LOCK_PATH.exists():
        try:
            info = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
            if int(info.get("pid", -1)) == os.getpid():
                LOCK_PATH.unlink()
        except Exception:
            pass


def initialize_status(cfg: dict, freeze: dict, resume: bool) -> dict:
    if STATUS_PATH.exists():
        old = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        if old.get("freeze_protocol_id_sha256") != freeze["protocol_id_sha256"]:
            raise Stage2Error("Persisted status belongs to a different implementation freeze")
        if old.get("status") == "completed":
            return old
        if old.get("status") == "failed" and old.get("recoverable") is False:
            raise Stage2Error("Previous failure was marked non-recoverable")
        if old.get("status") in ("paused", "failed", "running") and not resume:
            raise Stage2Error("Persisted experiment exists; use --resume after checking the saved state")
        old["status"] = "running"
        old["resume_count"] = int(old.get("resume_count", 0)) + 1
        return old
    if resume:
        raise Stage2Error("--resume requested but no persisted experiment status exists")
    return {
        "status": "running", "freeze_protocol_id_sha256": freeze["protocol_id_sha256"],
        "config_sha256": sha256_file(CONFIG_PATH), "completed_jobs": [], "partitions": {},
        "completed_unique_shots": 0, "planned_unique_shot_ceiling": int(cfg["total_unique_shot_ceiling"]),
        "independent_test_accessed": False, "final_development_accessed": False,
        "active_wall_seconds": 0.0, "cuda_seconds": 0.0, "resource_maxima": {}, "resume_count": 0,
        "start_time_epoch": time.time(), "recoverable": True,
    }


def check_environment(cfg: dict) -> torch.device:
    expected = cfg["resources"]["software_reference_from_stage1_preflight"]
    if torch.__version__ != expected["torch"] or stim.__version__ != expected["stim"] or pymatching.__version__ != expected["pymatching"]:
        raise Stage2Error(f"Software versions differ from Stage 1 reference: torch={torch.__version__}, stim={stim.__version__}, pymatching={pymatching.__version__}")
    if not torch.cuda.is_available():
        raise Stage2Error("CUDA required by frozen device policy; no CPU fallback")
    if sys.version.split()[0] != expected["python"]:
        raise Stage2Error(f"Unexpected Python version: {sys.version.split()[0]}; expected {expected['python']}")
    if torch.cuda.get_device_name(0) != expected["gpu"]:
        raise Stage2Error(f"Unexpected CUDA device: {torch.cuda.get_device_name(0)}")
    device = torch.device("cuda:0")
    if shutil.disk_usage(ROOT).free < cfg["resources"]["minimum_free_disk_gib_before_sampling"] * (1024 ** 3):
        raise ResourceLimitError("Free disk is below the frozen minimum")
    return device


def summarize_per_root(root_id: str, prediction_arrays: dict[str, np.ndarray],
                       final_arrays: dict[str, dict], selections: dict[str, dict]) -> dict:
    out = {"root_id": root_id, "conditions": {}}
    for condition in CONDITIONS:
        data = final_arrays[condition]
        y = data["observable"]
        pm = data["nominal_prediction"]
        pm_error = pm ^ y
        burst_comparable = condition == "synthetic_spatial_burst"
        record = {"shots": int(len(y)), "observable_positive_count": int(y.sum()),
                  "nominal_fixed_errors": int(pm_error.sum()), "nominal_fixed_ler": float(pm_error.mean()),
                  "burst_informed_errors": (int(np.sum(data["burst_prediction"] ^ y)) if burst_comparable else None),
                  "burst_informed_ler": (float(np.mean(data["burst_prediction"] ^ y)) if burst_comparable else None)}
        if burst_comparable:
            bursterr = data["burst_prediction"] ^ y
            record["burst_informed_candidate_only"] = int(np.sum((bursterr == 1) & (pm_error == 0)))
            record["burst_informed_nominal_only"] = int(np.sum((bursterr == 0) & (pm_error == 1)))
        for model_name in MODEL_ORDER:
            pred = prediction_arrays[f"{condition}__{model_name}__prediction"]
            prob = prediction_arrays[f"{condition}__{model_name}__probability"]
            err = pred ^ y
            residual_target_arr = y ^ pm
            correction = pred ^ pm
            record[model_name] = {
                "errors": int(err.sum()), "ler": float(err.mean()),
                "prediction_positive_count": int(pred.sum()),
                "residual_positive_count": int(residual_target_arr.sum()),
                "candidate_only_failures": int(np.sum((err == 1) & (pm_error == 0))),
                "pymatching_only_failures": int(np.sum((err == 0) & (pm_error == 1))),
                "prediction_disagreements": int(np.sum(pred != pm)),
                "useful_corrections": int(np.sum((correction == 1) & (pm_error == 1) & (err == 0))),
                "harmful_corrections": int(np.sum((correction == 1) & (pm_error == 0) & (err == 1))),
                "positive_precision": float(np.sum((correction == 1) & (pm_error == 1)) / max(1, np.sum(correction == 1))),
                "positive_recall": float(np.sum((correction == 1) & (pm_error == 1)) / max(1, np.sum(pm_error == 1))),
                "brier_score_residual": float(np.mean((prob - residual_target_arr) ** 2)),
                "residual_nll": nll(np.log(np.clip(prob, 1e-12, 1-1e-12) / np.clip(1-prob, 1e-12, 1)), residual_target_arr),
                "threshold": float(selections[model_name]["threshold"]),
                "temperature": float(selections[model_name]["temperature"]),
            }
        out["conditions"][condition] = record
    return out


def run(resume: bool = False) -> dict:
    cfg, inventory = verify_freeze()
    if len(inventory["streams"]) != 95:
        raise Stage2Error("Frozen stream count does not match required 95")
    device = check_environment(cfg)
    acquire_lock()
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    cfg_sha = sha256_file(CONFIG_PATH)
    try:
        status = initialize_status(cfg, freeze, resume)
    except Exception:
        release_lock()
        raise
    if status.get("status") == "completed":
        release_lock()
        return status
    prior_wall = float(status.get("active_wall_seconds", 0.0))
    start_time = time.perf_counter() - prior_wall
    status["status"] = "running"
    status["worker_pid"] = os.getpid()
    status["working_directory"] = str(ROOT)
    status["cuda_device"] = torch.cuda.get_device_name(0)
    status["software"] = {"torch": torch.__version__, "stim": stim.__version__,
                           "pymatching": pymatching.__version__, "python": sys.version.split()[0]}
    write_status(status)
    runtime = {"inventory": inventory, "cuda_seconds": float(status.get("cuda_seconds", 0.0)),
               "cuda_counter": [0.0], "dry_sim_seconds": 0.0, "max_epoch_count": 0}
    try:
        context = prepare_context(cfg)
        status["circuit_sha256"] = context["circuit_sha256"]
        status["dem_sha256"] = context["dem_sha256"]
        status["coordinates_sha256"] = sha256_bytes(json.dumps(context["coordinates"], sort_keys=True).encode())
        write_status(status)

        root_results_path = RAW_DIR / "per_root_results.json"
        per_root_results = (json.loads(root_results_path.read_text(encoding="utf-8"))
                            if root_results_path.exists() else {})
        root_parts_by_id: dict[str, dict[str, dict]] = {}

        # PHASE 1: materialize the four development-only partitions and freeze all
        # 15 root/model choices. No final-development stream is opened in this loop.
        for root_index in range(int(cfg["roots"]["count"])):
            root_id = f"dev-root-{root_index:02d}"
            parts: dict[str, dict[str, dict]] = {split: {} for split in SPLIT_NAMES}
            for split in SPLIT_NAMES:
                for condition in CONDITIONS:
                    expected = int(cfg["shots_per_root_condition"][split])
                    if split == "training" and root_id == "dev-root-00" and condition == "nominal":
                        existing = load_partition(root_id, split, condition, expected)
                        if existing is not None:
                            report_path = RUN_DIR / "dry_run_report.json"
                            if not report_path.is_file():
                                raise Stage2Error("Root-00 nominal training exists without its required dry-run report")
                            dry = json.loads(report_path.read_text(encoding="utf-8"))
                            if dry.get("status") != "PASS_WITHIN_FROZEN_LIMITS" or dry.get("unique_samples_used") != 256:
                                raise ResourceLimitError("Persisted 256-shot dry-run record is absent or failed")
                            arrays = existing
                        else:
                            tic = time.perf_counter()
                            sampler_seed = seed_for(inventory, root_id, split=split, condition=condition)
                            sampler = context["circuits"][condition].compile_detector_sampler(seed=sampler_seed)
                            prefix = sample_arrays(sampler, 256, context, condition)
                            runtime["dry_sim_seconds"] = time.perf_counter() - tic
                            prefix_hash = save_prefix(root_id, prefix, sampler_seed)
                            prefix_path = RAW_DIR / root_id / "training__nominal_prefix256.npz"
                            if sha256_file(prefix_path) != prefix_hash:
                                raise Stage2Error("Dry-run prefix changed while being verified")
                            status["dry_run_prefix"] = {
                                "root_id": root_id, "condition": condition, "shots": 256,
                                "seed": sampler_seed, "archive_sha256": prefix_hash,
                                "array_sha256": partition_hash(prefix),
                                "counted_within_training_partition": True,
                            }
                            write_status(status)
                            report_path = RUN_DIR / "dry_run_report.json"
                            if report_path.exists():
                                dry = json.loads(report_path.read_text(encoding="utf-8"))
                                if dry.get("status") != "PASS_WITHIN_FROZEN_LIMITS":
                                    raise ResourceLimitError("Previously saved 256-shot dry run failed; refusing to continue")
                            else:
                                dry = bounded_dry_run(prefix, context, cfg, device, runtime, start_time)
                                dry["freeze_protocol_id_sha256"] = freeze["protocol_id_sha256"]
                                dry["config_sha256"] = cfg_sha
                                dry["prefix_archive_sha256"] = prefix_hash
                                dry["software"] = status["software"]
                                atomic_json(report_path, dry)
                            if dry.get("prefix_archive_sha256") != prefix_hash or dry.get("config_sha256") != cfg_sha:
                                raise Stage2Error("Saved dry-run evidence does not match the frozen prefix/configuration")
                            status["dry_run_status"] = dry["status"]
                            status["dry_run_report_sha256"] = sha256_file(report_path)
                            write_status(status)
                            if dry["status"] != "PASS_WITHIN_FROZEN_LIMITS":
                                raise ResourceLimitError("256-shot dry run exceeded a frozen resource limit")
                            rest = sample_arrays(sampler, expected - 256, context, condition)
                            arrays = {name: np.concatenate((prefix[name], rest[name]), axis=0)
                                      for name in prefix}
                            validate_partition(arrays, expected)
                            meta = save_partition(root_id, split, condition, arrays, sampler_seed)
                            status.setdefault("partitions", {})[f"{root_id}/{split}/{condition}"] = meta
                            write_status(status)
                            runtime["dry_sim_seconds"] = 0.0
                    else:
                        arrays = generate_partition(root_id, split, condition, context, inventory, cfg, status)
                    parts[split][condition] = arrays
                    status["active_root"] = root_id
                    status["active_job"] = f"partition:{split}:{condition}"
                    status["active_wall_seconds"] = time.perf_counter() - start_time
                    status["cuda_seconds"] = runtime["cuda_seconds"]
                    snap = enforce_resources(cfg, device, wall_seconds=time.perf_counter() - start_time,
                                             cuda_seconds=runtime["cuda_seconds"])
                    status["resource_maxima"] = snap
                    write_status(status)

            positive_counts = {c: int(residual_target(parts["training"][c]).sum()) for c in CONDITIONS}
            min_pos = int(cfg["rare_residual_target_safeguards"]["minimum_unique_training_residual_positives_per_root_condition"])
            if any(v < min_pos for v in positive_counts.values()):
                raise Stage2Error(f"Insufficient residual positives; stopping before fitting {root_id}: {positive_counts}")
            root_parts_by_id[root_id] = parts

            for model_name in MODEL_ORDER:
                job_id = f"{root_id}/{model_name}"
                selection = train_and_select(root_id, model_name, parts, context["coordinates"],
                                             cfg, cfg_sha, device, start_time, runtime)
                if selection.get("final_development_data_accessed") is not False:
                    raise Stage2Error(f"{job_id} selection records premature final-data access")
                if job_id not in status["completed_jobs"]:
                    status["completed_jobs"].append(job_id)
                    status["max_optimizer_steps"] = int(status.get("max_optimizer_steps", 0)) + int(selection["optimizer_steps"])
                status["completed_model_root_jobs"] = len(set(status["completed_jobs"]))
                status["active_root"] = root_id
                status["active_job"] = model_name
                status["active_wall_seconds"] = time.perf_counter() - start_time
                status["cuda_seconds"] = runtime["cuda_seconds"]
                status["resource_maxima"] = enforce_resources(
                    cfg, device, wall_seconds=time.perf_counter() - start_time,
                    cuda_seconds=runtime["cuda_seconds"])
                write_status(status)

        # The global barrier prevents per-root final-label leakage. Persist and
        # verify the full choice set before touching any final-development stream.
        frozen_records = frozen_selection_hashes()
        frozen_manifest = selection_manifest_payload(frozen_records, freeze, cfg_sha)
        selection_manifest_path = RAW_DIR / "selection_manifest_before_final.json"
        if selection_manifest_path.exists():
            verify_selection_manifest(selection_manifest_path, frozen_manifest)
        else:
            atomic_json(selection_manifest_path, frozen_manifest)
        status["all_model_choices_frozen"] = True
        status["selection_manifest_sha256"] = frozen_manifest["manifest_sha256"]
        status["all_model_choices_frozen_utc"] = status.get("all_model_choices_frozen_utc") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        write_status(status)

        # PHASE 2: final-development access starts only after the global barrier.
        status["final_development_accessed"] = True
        status.setdefault("final_development_roots_started", [])
        write_status(status)
        for root_index in range(int(cfg["roots"]["count"])):
            root_id = f"dev-root-{root_index:02d}"
            root_selection_records = {}
            for model_name in MODEL_ORDER:
                sel_path, _ = selected_model_paths(root_id, model_name)
                root_selection_records[model_name] = json.loads(sel_path.read_text(encoding="utf-8"))
            final_arrays: dict[str, dict] = {}
            final_metadata = {}
            for condition in CONDITIONS:
                data, meta = generate_final_partition(root_id, condition, context, inventory, cfg, frozen_records)
                final_arrays[condition] = data
                final_metadata[condition] = meta

            pred_path = PREDICTION_DIR / f"{root_id}.npz"
            if root_id in per_root_results and pred_path.is_file():
                saved_result = per_root_results[root_id]
                if sha256_file(pred_path) != saved_result.get("prediction_archive_sha256"):
                    raise Stage2Error(f"Saved prediction/result hash mismatch for {root_id}")
                with np.load(pred_path, allow_pickle=False) as z:
                    prediction_arrays = {k: z[k] for k in z.files}
                recomputed = summarize_per_root(root_id, prediction_arrays, final_arrays, root_selection_records)
                for condition in CONDITIONS:
                    if recomputed["conditions"][condition] != saved_result["conditions"][condition]:
                        raise Stage2Error(f"Saved per-root metrics do not recompute for {root_id}/{condition}")
                status["completed_roots"] = sorted(per_root_results)
                status.setdefault("final_development_roots_started", []).append(root_id) if root_id not in status["final_development_roots_started"] else None
                continue

            prediction_arrays: dict[str, np.ndarray] = {}
            per_model_inference_wall: dict[str, float] = {model: 0.0 for model in MODEL_ORDER}
            for condition in CONDITIONS:
                data = final_arrays[condition]
                prediction_arrays[f"{condition}__nominal_prediction"] = data["nominal_prediction"]
                prediction_arrays[f"{condition}__burst_prediction"] = data["burst_prediction"]
                prediction_arrays[f"{condition}__observable"] = data["observable"]
                prediction_arrays[f"{condition}__detectors"] = data["detectors"]
            for model_name in MODEL_ORDER:
                model, selection = selected_model(root_id, model_name, context["coordinates"], device, cfg_sha)
                for condition in CONDITIONS:
                    data = final_arrays[condition]
                    all_logits, elapsed = [], 0.0
                    inference_wall_started = time.perf_counter()
                    with torch.inference_mode():
                        for start in range(0, len(data["observable"]), 1024):
                            x = torch.as_tensor(data["detectors"][start:start + 1024], dtype=torch.float32, device=device)
                            p = torch.as_tensor(data["nominal_prediction"][start:start + 1024], dtype=torch.float32, device=device)
                            tic = time.perf_counter()
                            logits_batch = model(x, p).float()
                            if not torch.isfinite(logits_batch).all():
                                raise Stage2Error("Non-finite final-development logits")
                            if device.type == "cuda":
                                torch.cuda.synchronize(device)
                                elapsed += time.perf_counter() - tic
                            all_logits.append(logits_batch.detach().cpu().numpy().astype(np.float64))
                    per_model_inference_wall[model_name] += time.perf_counter() - inference_wall_started
                    runtime["cuda_seconds"] += elapsed
                    logits = np.concatenate(all_logits) + math.log(
                        max(selection["pooled_residual_training_prevalence"], 1e-8) /
                        max(1 - selection["pooled_residual_training_prevalence"], 1e-8))
                    probs = sigmoid(logits / float(selection["temperature"])).astype(np.float32)
                    correction = (probs >= float(selection["threshold"])).astype(np.uint8)
                    pred = data["nominal_prediction"] ^ correction
                    prefix = f"{condition}__{model_name}__"
                    prediction_arrays[prefix + "logits"] = logits.astype(np.float32)
                    prediction_arrays[prefix + "probability"] = probs
                    prediction_arrays[prefix + "prediction"] = pred.astype(np.uint8)
                    status["active_root"] = root_id
                    status["active_job"] = f"final-inference:{model_name}:{condition}"
                    status["cuda_seconds"] = runtime["cuda_seconds"]
                    status["active_wall_seconds"] = time.perf_counter() - start_time
                    status["resource_maxima"] = enforce_resources(
                        cfg, device, wall_seconds=time.perf_counter() - start_time,
                        cuda_seconds=runtime["cuda_seconds"])
                    write_status(status)
                del model
                if device.type == "cuda":
                    torch.cuda.empty_cache()

            if pred_path.exists():
                with np.load(pred_path, allow_pickle=False) as z:
                    old_predictions = {k: z[k] for k in z.files}
                if set(old_predictions) != set(prediction_arrays) or any(
                        not np.array_equal(old_predictions[k], prediction_arrays[k]) for k in prediction_arrays):
                    raise Stage2Error(f"Interrupted prediction archive differs from deterministic recomputation: {root_id}")
                pred_hash = sha256_file(pred_path)
            else:
                pred_hash = atomic_npz(pred_path, prediction_arrays)
            root_result = summarize_per_root(root_id, prediction_arrays, final_arrays, root_selection_records)
            root_result["final_sample_metadata"] = final_metadata
            root_result["prediction_archive_sha256"] = pred_hash
            root_result["model_runtime"] = {
                model: {
                    "parameters": int(root_selection_records[model]["parameter_count"]),
                    "inference_wall_seconds_for_two_conditions": float(per_model_inference_wall[model]),
                    "inference_wall_seconds_per_shot": float(per_model_inference_wall[model] / 20000),
                } for model in MODEL_ORDER
            }
            per_root_results[root_id] = root_result
            atomic_json(root_results_path, per_root_results)
            if root_id not in status["final_development_roots_started"]:
                status["final_development_roots_started"].append(root_id)
            status["completed_roots"] = sorted(per_root_results)
            status["active_wall_seconds"] = time.perf_counter() - start_time
            status["cuda_seconds"] = runtime["cuda_seconds"]
            status["completed_unique_shots"] = recompute_unique_sample_count()
            write_status(status)

        status["status"] = "finalizing"
        status["active_wall_seconds"] = time.perf_counter() - start_time
        write_status(status)
        from outputs.cnn_architecture_stage2_v1.audit_stage2 import independently_rescore
        audit_result = independently_rescore(RUN_DIR, write_outputs=True)
        if audit_result.get("status") != "PASS":
            raise Stage2Error(f"Independent rescore failed: {audit_result.get('failures')}")
        status["independent_audit_status"] = "PASS"
        status["active_wall_seconds"] = time.perf_counter() - start_time
        status["cuda_seconds"] = runtime["cuda_seconds"]
        status["completed_unique_shots"] = recompute_unique_sample_count()
        write_execution_reports(status, audit_result)
        evidence_manifest_sha = write_evidence_manifest(status, audit_result)
        status["status"] = "completed"
        status["independent_audit_status"] = "PASS"
        status["evidence_manifest_sha256"] = evidence_manifest_sha
        status["completed_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        status["active_wall_seconds"] = time.perf_counter() - start_time
        status["cuda_seconds"] = runtime["cuda_seconds"]
        status["completed_unique_shots"] = recompute_unique_sample_count()
        status["recoverable"] = False
        write_status(status)
        return status
    except KeyboardInterrupt:
        status["status"] = "paused"
        status["recoverable"] = True
        status["active_wall_seconds"] = time.perf_counter() - start_time
        status["cuda_seconds"] = runtime["cuda_seconds"]
        status["completed_unique_shots"] = recompute_unique_sample_count()
        write_status(status)
        return status
    except Exception as exc:
        status["status"] = "failed"
        status["failure"] = f"{type(exc).__name__}: {exc}"
        status["traceback"] = traceback.format_exc()
        status["recoverable"] = not isinstance(exc, Stage2Error)
        status["failed_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        status["active_wall_seconds"] = time.perf_counter() - start_time
        status["cuda_seconds"] = runtime["cuda_seconds"]
        status["completed_unique_shots"] = recompute_unique_sample_count()
        write_status(status)
        raise
    finally:
        release_lock()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run frozen Q-SHIFT CNN Stage 2; no independent-test path exists.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run", action="store_true", help="start the frozen development experiment")
    group.add_argument("--resume", action="store_true", help="resume a recoverable interrupted run")
    args = parser.parse_args()
    result = run(resume=args.resume)
    print(json.dumps({"status": result.get("status"),
                      "completed_model_root_jobs": result.get("completed_model_root_jobs", 0),
                      "completed_roots": result.get("completed_roots", []),
                      "completed_unique_shots": result.get("completed_unique_shots", 0),
                      "active_wall_seconds": result.get("active_wall_seconds"),
                      "cuda_seconds": result.get("cuda_seconds")}, indent=2))
    return 0 if result.get("status") == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
