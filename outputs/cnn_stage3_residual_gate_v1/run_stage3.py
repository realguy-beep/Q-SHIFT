"""Deterministic Stage 3 runner: burst-focused residual CNN development study.

Run only after the prospective freeze verifies and the no-sampling tests pass:
    python outputs/cnn_stage3_residual_gate_v1/run_stage3.py --validate-only
    python outputs/cnn_stage3_residual_gate_v1/run_stage3.py --run
The independent-test allocation is not referenced by this runner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import shutil
import subprocess
import sys
import time
import traceback
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
import psutil
import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
for p in (ROOT, ROOT / "dashboard"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from outputs.neural_decoder_diagnostic.autonomous_development.experiment import ResidualPositionCNN  # noqa: E402
from outputs.phase3a_correlated_noise_preflight.simulator import build_matching, build_spatial_burst_circuit  # noqa: E402
from outputs.cnn_stage3_residual_gate_v1.freeze_stage3 import sha256 as file_sha256  # noqa: E402

try:
    import stim
    import pymatching
except Exception as exc:  # pragma: no cover - surfaced by validation
    raise RuntimeError(f"Stage 3 dependencies unavailable: {exc}") from exc

CONFIG_PATH = HERE / "stage3_config.json"
INVENTORY_PATH = HERE / "seed_inventory.json"
FREEZE_PATH = HERE / "FREEZE.json"
RUN = HERE / "run_v1"
RAW = RUN / "raw"
CHECKPOINTS = RUN / "checkpoints"
PREDICTIONS = RUN / "predictions"
STATUS_PATH = RAW / "status.json"
LOCK_PATH = RAW / "runner.lock"
POLICY_PATH = HERE / "STAGE3_POLICY_FREEZE.json"
CONDITIONS = ("nominal", "synthetic_spatial_burst")
ROOT_IDS = tuple(f"stage3-root-{i:02d}" for i in range(5))
TRAIN_CONDITION = "synthetic_spatial_burst"
STAGE2_HISTORICAL_MODEL = "historical_residual_position_cnn"
STAGE3_MODEL = "stage3_burst_focused_residual_cnn"
STAGE2 = ROOT / "outputs/cnn_architecture_stage2_v1"
STAGE2_RUN = STAGE2 / "run_v1"


class Stage3Error(RuntimeError):
    """Frozen protocol, data integrity, or execution error."""


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_array(value: np.ndarray) -> str:
    a = np.ascontiguousarray(value)
    return digest_bytes(a.dtype.str.encode() + repr(a.shape).encode() + a.tobytes())


def digest_state(state: dict[str, torch.Tensor]) -> str:
    h = hashlib.sha256()
    for key in sorted(state):
        value = state[key].detach().cpu().contiguous()
        h.update(key.encode())
        h.update(value.numpy().tobytes())
        h.update(repr(tuple(value.shape)).encode())
    return h.hexdigest()


def restore_state_verified(model: torch.nn.Module, state: dict[str, torch.Tensor], expected_hash: str) -> None:
    if digest_state(state) != expected_hash:
        raise Stage3Error("Selected model state hash mismatch")
    model.load_state_dict(state)


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    data = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    with temp.open("wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


def atomic_npz(path: Path, arrays: dict[str, np.ndarray]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = BytesIO()
    np.savez_compressed(buffer, **arrays)
    data = buffer.getvalue()
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)
    return file_sha256(path)


def atomic_torch_save(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("wb") as f:
        torch.save(payload, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)
    return file_sha256(path)


def verify_freeze() -> tuple[dict, dict, str]:
    # The command-line verifier reports details; the direct checks below keep
    # the sampler entry point fail-closed if any source/config has drifted.
    payload = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    expected_freeze_id = digest_bytes(json.dumps({k: v for k, v in payload.items() if k != "protocol_id_sha256"},
        sort_keys=True, separators=(",", ":")).encode())
    if payload.get("protocol_id_sha256") != expected_freeze_id:
        bad = ["FREEZE.json protocol identifier hash"]
    else:
        bad = []
    supersedes = payload.get("supersedes_freeze")
    if supersedes is not None:
        old_path = HERE / supersedes.get("path", "")
        if not old_path.is_file() or file_sha256(old_path) != supersedes.get("sha256") or supersedes.get("sampled_shots_at_supersession") != 0:
            bad.append("superseded pre-sampling freeze record")
    for row in payload.get("inputs", []):
        p = ROOT / row["path"]
        if not p.is_file() or p.stat().st_size != row["bytes"] or file_sha256(p) != row["sha256"]:
            bad.append(row["path"])
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    audit = json.loads((HERE / "seed_audit.json").read_text(encoding="utf-8"))
    if bad or payload.get("status") != "FROZEN_BEFORE_SAMPLING" or audit.get("status") != "PASS":
        raise Stage3Error(f"Prospective freeze verification failed: changed={bad}")
    if payload.get("planned_unique_shots") != 200000 or inventory.get("stream_count") != 46:
        raise Stage3Error("Freeze/seed inventory does not match the protocol")
    seed_values = [int(x["seed"]) for x in inventory["streams"]]
    if len(seed_values) != len(set(seed_values)) or set(seed_values) & set(audit.get("historical_seed_values", [])):
        raise Stage3Error("Seed collision or duplicate found at run time")
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return cfg, inventory, payload["protocol_id_sha256"]


def seed_value(inventory: dict, root: str, *, split: str | None = None,
               condition: str | None = None, purpose: str | None = None) -> int:
    for row in inventory["streams"]:
        if row.get("root_id") != root:
            continue
        if split is not None and row.get("split") != split:
            continue
        if condition is not None and row.get("condition") != condition:
            continue
        if purpose is not None and row.get("purpose") != purpose:
            continue
        if split is None and condition is None and purpose is None:
            continue
        if "seed" in row:
            return int(row["seed"])
    raise Stage3Error(f"Seed not allocated: root={root}, split={split}, condition={condition}, purpose={purpose}")


def validate_binary(name: str, array: np.ndarray) -> np.ndarray:
    a = np.asarray(array)
    if a.size and not np.all((a == 0) | (a == 1)):
        raise Stage3Error(f"{name} contains non-binary values")
    return a.astype(np.uint8, copy=False)


def validate_arrays(arrays: dict[str, np.ndarray], shots: int | None = None) -> None:
    if set(arrays) != {"detectors", "observable", "nominal_prediction", "burst_prediction"}:
        raise Stage3Error(f"Unexpected partition schema: {sorted(arrays)}")
    n = arrays["detectors"].shape[0]
    if shots is not None and n != shots:
        raise Stage3Error(f"Expected {shots} shots, got {n}")
    if arrays["detectors"].shape != (n, 40):
        raise Stage3Error(f"Detector shape invalid: {arrays['detectors'].shape}")
    for key in ("observable", "nominal_prediction", "burst_prediction"):
        if arrays[key].shape != (n,):
            raise Stage3Error(f"{key} shape invalid: {arrays[key].shape}")
        validate_binary(key, arrays[key])
    validate_binary("detectors", arrays["detectors"])


def arrays_hashes(arrays: dict[str, np.ndarray]) -> dict[str, str]:
    return {key: digest_array(value) for key, value in sorted(arrays.items())}


def residual_target(arrays: dict[str, np.ndarray]) -> np.ndarray:
    return np.bitwise_xor(arrays["observable"], arrays["nominal_prediction"]).astype(np.uint8)


def correction_metrics(prediction: np.ndarray, fixed_prediction: np.ndarray,
                       observable: np.ndarray) -> dict[str, int | float | None]:
    pred = validate_binary("candidate prediction", prediction).reshape(-1)
    fixed = validate_binary("fixed prediction", fixed_prediction).reshape(-1)
    truth = validate_binary("observable", observable).reshape(-1)
    if not (pred.shape == fixed.shape == truth.shape):
        raise Stage3Error("Prediction/label lengths differ during correction accounting")
    fixed_wrong = fixed != truth
    candidate_wrong = pred != truth
    changed = pred != fixed
    useful = changed & fixed_wrong
    harmful = changed & ~fixed_wrong
    return {
        "errors": int(candidate_wrong.sum()),
        "candidate_only_failures": int((candidate_wrong & ~fixed_wrong).sum()),
        "fixed_only_failures": int((~candidate_wrong & fixed_wrong).sum()),
        "prediction_disagreements": int(changed.sum()),
        "useful_corrections": int(useful.sum()),
        "harmful_corrections": int(harmful.sum()),
        "correction_precision": float(useful.sum() / changed.sum()) if changed.any() else None,
        "correction_recall": float(useful.sum() / fixed_wrong.sum()) if fixed_wrong.any() else None,
    }


def choose_global_threshold(threshold_probs: dict[str, dict], roots: tuple[str, ...],
                            grid: list[float]) -> tuple[float, list[dict]]:
    scores = []
    for threshold in grid:
        root_lers = []
        for root in roots:
            arrays = threshold_probs[root]["arrays"]
            correction = (threshold_probs[root]["probability"] >= threshold).astype(np.uint8)
            prediction = arrays["nominal_prediction"] ^ correction
            root_lers.append(float(np.mean(prediction ^ arrays["observable"])))
        scores.append({"threshold": float(threshold), "equal_root_mean_ler": float(np.mean(root_lers)),
                       "root_lers": root_lers})
    best = min(scores, key=lambda row: (row["equal_root_mean_ler"], abs(row["threshold"] - 0.5), row["threshold"]))
    return float(best["threshold"]), scores


def validate_selection_partitions(parts: dict) -> None:
    """Fail closed unless training choices see only the four frozen pre-final splits."""
    allowed = {"training", "monitor", "probability_calibration", "threshold_selection"}
    if set(parts) != set(ROOT_IDS):
        raise Stage3Error("Selection data must contain exactly the five allocated roots")
    for root, root_parts in parts.items():
        if set(root_parts) != allowed:
            raise Stage3Error(f"Selection data for {root} includes missing or forbidden partitions: {sorted(root_parts)}")
        for split, conditions in root_parts.items():
            if set(conditions) != {TRAIN_CONDITION}:
                raise Stage3Error(f"Selection split {root}/{split} has an unexpected condition")


def sigmoid(values: np.ndarray) -> np.ndarray:
    z = np.asarray(values, dtype=np.float64)
    return 1.0 / (1.0 + np.exp(-np.clip(z, -60.0, 60.0)))


def binary_nll(logits: np.ndarray, labels: np.ndarray) -> float:
    z = np.clip(np.asarray(logits, dtype=np.float64), -60, 60)
    y = np.asarray(labels, dtype=np.float64)
    return float(np.mean(np.logaddexp(0.0, z) - y * z))


def set_determinism(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed & 0xFFFFFFFF)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.use_deterministic_algorithms(True)


def resource_snapshot(device: torch.device) -> dict:
    disk = shutil.disk_usage(ROOT)
    result = {"process_rss_bytes": int(psutil.Process().memory_info().rss),
              "free_disk_bytes": int(disk.free), "cuda_allocated_bytes": 0,
              "cuda_peak_allocated_bytes": 0}
    if device.type == "cuda":
        result["cuda_allocated_bytes"] = int(torch.cuda.memory_allocated(device))
        result["cuda_peak_allocated_bytes"] = int(torch.cuda.max_memory_allocated(device))
    return result


def enforce_resources(cfg: dict, device: torch.device, start: float,
                      cuda_seconds: float, wall_offset_seconds: float = 0.0) -> dict:
    snap = resource_snapshot(device)
    lim = cfg["resources"]
    failures = []
    elapsed_wall = wall_offset_seconds + time.perf_counter() - start
    if elapsed_wall > lim["maximum_wall_seconds"]:
        failures.append("wall-time limit")
    if cuda_seconds > lim["maximum_measured_cuda_training_seconds"]:
        failures.append("measured CUDA time limit")
    if snap["process_rss_bytes"] > lim["maximum_process_rss_gib"] * 1024**3:
        failures.append("process RSS limit")
    if snap["cuda_peak_allocated_bytes"] > lim["maximum_cuda_allocated_gib"] * 1024**3:
        failures.append("CUDA allocation limit")
    if snap["free_disk_bytes"] < lim["minimum_free_disk_gib"] * 1024**3:
        failures.append("free disk minimum")
    if failures:
        raise Stage3Error("Resource limit exceeded: " + ", ".join(failures))
    return snap


def build_context(cfg: dict) -> dict:
    c = cfg["circuit"]
    circuits = {
        "nominal": build_spatial_burst_circuit(
            memory_basis=c["memory_basis"], regime=c["pauli_regime"], distance=c["distance"], rounds=c["rounds"],
            gate_p=c["gate_probability"], measurement_p=c["measurement_probability"], bias_ratio=c["bias_ratio"],
            burst_probability=0.0, burst_pair=tuple(c["burst_pair_data_qubits"])),
        "synthetic_spatial_burst": build_spatial_burst_circuit(
            memory_basis=c["memory_basis"], regime=c["pauli_regime"], distance=c["distance"], rounds=c["rounds"],
            gate_p=c["gate_probability"], measurement_p=c["measurement_probability"], bias_ratio=c["bias_ratio"],
            burst_probability=c["burst_probability_per_round"], burst_pair=tuple(c["burst_pair_data_qubits"])),
    }
    signatures = {(v.num_detectors, v.num_observables) for v in circuits.values()}
    if signatures != {(40, 1)}:
        raise Stage3Error(f"Circuit signature mismatch: {signatures}")
    coords = [circuits[x].get_detector_coordinates() for x in CONDITIONS]
    if coords[0] != coords[1] or sorted(coords[0]) != list(range(40)):
        raise Stage3Error("Nominal and burst detector geometry differ or detector IDs are not contiguous")
    dems, matchers = {}, {}
    for condition, circuit in circuits.items():
        dem, matcher = build_matching(circuit, enable_correlations=True)
        if (dem.num_detectors, dem.num_observables, matcher.num_detectors) != (40, 1, 40):
            raise Stage3Error(f"DEM/matcher dimensions invalid for {condition}")
        dems[condition], matchers[condition] = dem, matcher
    noiseless = build_spatial_burst_circuit(memory_basis=c["memory_basis"], regime=c["pauli_regime"],
        distance=c["distance"], rounds=c["rounds"], gate_p=0.0, measurement_p=0.0,
        bias_ratio=c["bias_ratio"], burst_probability=0.0,
        burst_pair=tuple(c["burst_pair_data_qubits"]))
    if (noiseless.num_detectors, noiseless.num_observables) != (40, 1):
        raise Stage3Error("Noiseless circuit structure invalid")
    noiseless_dem = noiseless.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)
    if (noiseless_dem.num_detectors, noiseless_dem.num_observables, noiseless_dem.num_errors) != (40, 1, 0):
        raise Stage3Error("Noiseless DEM validation failed")
    # Preflight performs no shot sampling. The detector and observable definitions
    # are checked by the Stim circuit and DEM dimensions above.
    return {"circuits": circuits, "dems": dems, "matchers": matchers, "coordinates": coords[0],
            "circuit_hashes": {k: digest_bytes(str(v).encode()) for k, v in circuits.items()},
            "dem_hashes": {k: digest_bytes(str(v).encode()) for k, v in dems.items()},
            "noiseless_circuit_hash": digest_bytes(str(noiseless).encode()),
            "noiseless_dem_hash": digest_bytes(str(noiseless_dem).encode())}


def sample_arrays(sampler, shots: int, context: dict, condition: str) -> dict[str, np.ndarray]:
    detectors, obs = sampler.sample(shots, separate_observables=True)
    detectors = validate_binary("Stim detectors", np.asarray(detectors))
    obs = validate_binary("Stim observables", np.asarray(obs))
    if detectors.shape != (shots, 40) or obs.shape != (shots, 1):
        raise Stage3Error(f"Stim sample shape mismatch: {detectors.shape}, {obs.shape}")
    nominal = np.asarray(context["matchers"]["nominal"].decode_batch(detectors), dtype=np.uint8).reshape(-1)
    if condition == "synthetic_spatial_burst":
        burst = np.asarray(context["matchers"]["synthetic_spatial_burst"].decode_batch(detectors), dtype=np.uint8).reshape(-1)
    else:
        burst = nominal.copy()
    result = {"detectors": np.ascontiguousarray(detectors),
              "observable": np.ascontiguousarray(obs[:, 0]),
              "nominal_prediction": np.ascontiguousarray(validate_binary("nominal prediction", nominal)),
              "burst_prediction": np.ascontiguousarray(validate_binary("burst prediction", burst))}
    validate_arrays(result, shots)
    return result


def partition_paths(root: str, split: str, condition: str) -> tuple[Path, Path]:
    name = f"{split}__{condition}"
    folder = RAW / root
    return folder / f"{name}.npz", folder / f"{name}.json"


def partition_seed(inventory: dict, root: str, split: str, condition: str) -> int:
    return seed_value(inventory, root, split=split, condition=condition)


def load_partition(root: str, split: str, condition: str, expected: int | None = None) -> dict[str, np.ndarray] | None:
    path, meta_path = partition_paths(root, split, condition)
    if not path.is_file():
        if meta_path.exists():
            raise Stage3Error(f"Partition metadata exists without archive: {meta_path}")
        return None
    if not meta_path.is_file():
        # A crash can occur after the archive's atomic replace but before the
        # metadata commit. Recreate the frozen stream from its seed; the caller
        # will atomically replace this uncommitted archive and write metadata.
        return None
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if file_sha256(path) != meta.get("archive_sha256"):
        raise Stage3Error(f"Partition archive hash mismatch: {path}")
    with np.load(path, allow_pickle=False) as z:
        arrays = {k: z[k] for k in z.files}
    validate_arrays(arrays, expected)
    if arrays_hashes(arrays) != meta.get("array_sha256"):
        raise Stage3Error(f"Partition array hash mismatch: {path}")
    return arrays


def save_partition(root: str, split: str, condition: str, arrays: dict[str, np.ndarray], seed: int,
                   context: dict) -> dict:
    path, meta_path = partition_paths(root, split, condition)
    validate_arrays(arrays)
    archive_hash = atomic_npz(path, arrays)
    meta = {"kind": "stage3_partition", "root_id": root, "split": split, "condition": condition, "seed": int(seed),
            "shots": int(len(arrays["observable"])), "detector_count": 40, "observable_count": 1,
            "array_sha256": arrays_hashes(arrays), "archive_sha256": archive_hash,
            "circuit_sha256": context["circuit_hashes"][condition],
            "nominal_dem_sha256": context["dem_hashes"]["nominal"],
            "burst_dem_sha256": context["dem_hashes"]["synthetic_spatial_burst"],
            "saved_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    atomic_json(meta_path, meta)
    return meta


def model_for(coords: dict):
    return ResidualPositionCNN(coords, channels=4, head_width=16, dropout=0.05)


def natural_logits(model: torch.nn.Module, arrays: dict[str, np.ndarray], prevalence: float,
                   device: torch.device, batch: int = 1024) -> np.ndarray:
    model.eval()
    prior = math.log(max(prevalence, 1e-8) / max(1.0 - prevalence, 1e-8))
    outputs = []
    with torch.inference_mode():
        for start in range(0, len(arrays["observable"]), batch):
            d = torch.as_tensor(arrays["detectors"][start:start + batch], dtype=torch.float32, device=device)
            pm = torch.as_tensor(arrays["nominal_prediction"][start:start + batch], dtype=torch.float32, device=device)
            z = model(d, pm).float()
            if not torch.isfinite(z).all():
                raise Stage3Error("Non-finite model logits")
            outputs.append(z.detach().cpu().numpy().astype(np.float64) + prior)
    return np.concatenate(outputs) if outputs else np.empty(0, dtype=np.float64)


def balanced_batches(labels: np.ndarray, batch_size: int, rng: np.random.Generator,
                     order_rng: np.random.Generator) -> list[np.ndarray]:
    positive, negative = np.flatnonzero(labels == 1), np.flatnonzero(labels == 0)
    if not len(positive) or not len(negative):
        raise Stage3Error("Balanced sampler is missing a residual class")
    batches = []
    for start in range(0, len(labels), batch_size):
        size = min(batch_size, len(labels) - start)
        n_pos = (size + 1) // 2
        n_neg = size - n_pos
        ids = np.concatenate((rng.choice(positive, n_pos, replace=len(positive) < n_pos),
                              rng.choice(negative, n_neg, replace=len(negative) < n_neg)))
        rng.shuffle(ids)
        batches.append(ids.astype(np.int32))
    order_rng.shuffle(batches)
    return batches


def checkpoint_paths(root: str) -> tuple[Path, Path, Path]:
    folder = CHECKPOINTS / root
    return folder / "latest_training.pt", folder / "selected_model.pt", folder / "checkpoint_manifest.json"


def recovered_cuda_training_seconds() -> float:
    recovered = 0.0
    for manifest_path in CHECKPOINTS.glob("stage3-root-*/checkpoint_manifest.json"):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        root = manifest.get("root_id", manifest_path.parent.name)
        checkpoint_path = checkpoint_paths(root)[0]
        if not checkpoint_path.is_file() or file_sha256(checkpoint_path) != manifest.get("sha256"):
            raise Stage3Error(f"Cannot recover CUDA budget from a corrupt checkpoint: {manifest_path}")
        payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        recovered = max(recovered, float(payload.get("cuda_training_seconds", 0.0)))
    return recovered


def fit_candidate(root: str, arrays: dict[str, np.ndarray], monitor: dict[str, np.ndarray],
                  coords: dict, cfg: dict, inventory: dict, cfg_sha: str, device: torch.device,
                  start: float, runtime: dict) -> dict:
    selection_path = RAW / root / "candidate_selection.json"
    latest_path, selected_path, manifest_path = checkpoint_paths(root)
    if selection_path.is_file() and selected_path.is_file():
        rec = json.loads(selection_path.read_text(encoding="utf-8"))
        if file_sha256(selected_path) != rec.get("selected_checkpoint_sha256"):
            raise Stage3Error(f"Selected checkpoint hash mismatch for {root}")
        return rec

    fit_started = time.perf_counter()
    cuda_fit_started = float(runtime["cuda_training_seconds"])

    labels = residual_target(arrays)
    positive_count = int(labels.sum())
    minimum = int(cfg["training"]["minimum_unique_training_residual_positives_per_root"])
    if positive_count < minimum:
        raise Stage3Error(f"Insufficient unique residual positives for {root}: {positive_count} < {minimum}")
    prevalence = positive_count / len(labels)
    model_seed = seed_value(inventory, root, purpose="torch_initialization")
    batch_seed = seed_value(inventory, root, purpose="balanced_sampling")
    order_seed = seed_value(inventory, root, purpose="batch_order")
    set_determinism(model_seed)
    model = model_for(coords).to(device)
    train_cfg = cfg["training"]
    optimizer = torch.optim.AdamW(model.parameters(), lr=train_cfg["learning_rate"],
                                  weight_decay=train_cfg["weight_decay"])
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer,
        step_size=train_cfg["scheduler"]["step_size_epochs"], gamma=train_cfg["scheduler"]["gamma"])
    rng = np.random.default_rng(batch_seed)
    order_rng = np.random.default_rng(order_seed)
    latest_manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
    checkpoint = None
    if latest_manifest:
        p = latest_path
        if not p.is_file() or file_sha256(p) != latest_manifest.get("sha256"):
            raise Stage3Error(f"Latest training checkpoint corrupted for {root}")
        checkpoint = torch.load(p, map_location="cpu", weights_only=False)
        if checkpoint.get("config_sha256") != cfg_sha or checkpoint.get("root_id") != root:
            raise Stage3Error(f"Training checkpoint identity mismatch for {root}")
        if checkpoint.get("training_array_sha256") != arrays_hashes(arrays) or checkpoint.get("monitor_array_sha256") != arrays_hashes(monitor):
            raise Stage3Error(f"Training checkpoint data-partition hash mismatch for {root}")
        model.load_state_dict(checkpoint["model_state"])
        optimizer.load_state_dict(checkpoint["optimizer_state"])
        scheduler.load_state_dict(checkpoint["scheduler_state"])
        rng.bit_generator.state = checkpoint["sampling_rng_state"]
        order_rng.bit_generator.state = checkpoint["order_rng_state"]
        torch.set_rng_state(checkpoint["torch_rng_state"].cpu())
        if device.type == "cuda" and checkpoint.get("cuda_rng_state") is not None:
            torch.cuda.set_rng_state_all(checkpoint["cuda_rng_state"])
        completed_epochs = int(checkpoint["completed_epochs"])
        best_state = checkpoint["best_state"]
        best_nll = float(checkpoint["best_monitor_nll"])
        best_epoch = int(checkpoint["best_epoch"])
        stale_epochs = int(checkpoint["stale_epochs"])
        steps = int(checkpoint["steps"])
        history = list(checkpoint["history"])
        positive_draws = int(checkpoint["positive_draws"])
    else:
        completed_epochs, best_state, best_nll, best_epoch = 0, None, float("inf"), 0
        stale_epochs, steps, history, positive_draws = 0, 0, [], 0

    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)
    labels_by_monitor = residual_target(monitor)
    while completed_epochs < int(train_cfg["maximum_epochs"]):
        model.train()
        batches = balanced_batches(labels, int(train_cfg["batch_size"]), rng, order_rng)
        if len(batches) != int(cfg["training"]["expected_batches_per_epoch"]):
            raise Stage3Error(f"Optimizer schedule changed for {root}: {len(batches)} batches")
        epoch_positive = 0
        for ids in batches:
            idx = ids.astype(np.int64)
            d = torch.as_tensor(arrays["detectors"][idx], dtype=torch.float32, device=device)
            pm = torch.as_tensor(arrays["nominal_prediction"][idx], dtype=torch.float32, device=device)
            y = torch.as_tensor(labels[idx].astype(np.float32), dtype=torch.float32, device=device)
            epoch_positive += int(y.sum().item())
            t0 = time.perf_counter()
            optimizer.zero_grad(set_to_none=True)
            logits = model(d, pm).float()
            loss = F.binary_cross_entropy_with_logits(logits, y)
            if not torch.isfinite(loss):
                raise Stage3Error(f"Non-finite training loss for {root}")
            loss.backward()
            if any(p.grad is not None and not torch.isfinite(p.grad).all() for p in model.parameters()):
                raise Stage3Error(f"Non-finite gradient for {root}")
            optimizer.step()
            if device.type == "cuda":
                torch.cuda.synchronize(device)
                runtime["cuda_training_seconds"] += time.perf_counter() - t0
            steps += 1
            enforce_resources(cfg, device, start, runtime["cuda_training_seconds"], runtime.get("wall_offset_seconds", 0.0))

        monitor_logits = natural_logits(model, monitor, prevalence, device)
        monitor_nll = binary_nll(monitor_logits, labels_by_monitor)
        if not math.isfinite(monitor_nll):
            raise Stage3Error(f"Non-finite monitor NLL for {root}")
        completed_epochs += 1
        positive_draws += epoch_positive
        improved = monitor_nll < best_nll - 1e-12
        if improved:
            best_nll = monitor_nll
            best_epoch = completed_epochs
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            stale_epochs = 0
        else:
            stale_epochs += 1
        history.append({"epoch": completed_epochs, "monitor_nll": monitor_nll,
                        "positive_draws": epoch_positive, "improved": improved})
        scheduler.step()
        epoch_state_path = CHECKPOINTS / root / "epochs" / f"epoch_{completed_epochs:02d}.pt"
        epoch_hash = atomic_torch_save(epoch_state_path, {
            "root_id": root, "epoch": completed_epochs, "model_state": model.state_dict(),
            "monitor_nll": monitor_nll, "config_sha256": cfg_sha,
            "training_array_sha256": arrays_hashes(arrays), "monitor_array_sha256": arrays_hashes(monitor)})
        payload = {"root_id": root, "model_state": model.state_dict(), "optimizer_state": optimizer.state_dict(),
            "scheduler_state": scheduler.state_dict(), "config_sha256": cfg_sha,
            "training_array_sha256": arrays_hashes(arrays), "monitor_array_sha256": arrays_hashes(monitor),
            "cuda_training_seconds": float(runtime["cuda_training_seconds"]),
            "completed_epochs": completed_epochs, "best_state": best_state, "best_monitor_nll": best_nll,
            "best_epoch": best_epoch, "stale_epochs": stale_epochs, "steps": steps,
            "positive_draws": positive_draws, "sampling_rng_state": rng.bit_generator.state,
            "order_rng_state": order_rng.bit_generator.state, "torch_rng_state": torch.get_rng_state(),
            "cuda_rng_state": torch.cuda.get_rng_state_all() if device.type == "cuda" else None,
            "history": history}
        latest_hash = atomic_torch_save(latest_path, payload)
        atomic_json(manifest_path, {"root_id": root, "sha256": latest_hash,
                                    "completed_epochs": completed_epochs, "config_sha256": cfg_sha,
                                    "latest_epoch_checkpoint": str(epoch_state_path.relative_to(ROOT)),
                                    "latest_epoch_sha256": epoch_hash})
        runtime["resource_maxima"] = enforce_resources(cfg, device, start, runtime["cuda_training_seconds"], runtime.get("wall_offset_seconds", 0.0))
        if stale_epochs >= int(train_cfg["early_stopping_patience"]):
            break

    if best_state is None:
        raise Stage3Error(f"No best model state recorded for {root}")
    model.load_state_dict(best_state)
    selected_state_hash = digest_state(best_state)
    selected_hash = atomic_torch_save(selected_path, {"root_id": root, "model_name": STAGE3_MODEL,
        "model_state": best_state, "state_dict_sha256": selected_state_hash, "config_sha256": cfg_sha,
        "selected_epoch": best_epoch, "selected_monitor_nll": best_nll,
        "training_array_sha256": arrays_hashes(arrays), "monitor_array_sha256": arrays_hashes(monitor)})
    rec = {"root_id": root, "model": STAGE3_MODEL, "architecture": "HistoricalResidualPositionCNN",
        "parameter_count": sum(p.numel() for p in model.parameters()), "train_seed": model_seed,
        "balanced_sampling_seed": batch_seed, "batch_order_seed": order_seed,
        "training_shots": len(labels), "training_positive_count": positive_count,
        "training_residual_prevalence": prevalence, "positive_draws": positive_draws,
        "positive_reuse_ratio": positive_draws / positive_count, "best_epoch": best_epoch,
        "epochs_completed": completed_epochs, "optimizer_steps": steps,
        "best_monitor_nll": best_nll, "monitor_history": history,
        "training_wall_seconds": time.perf_counter() - fit_started,
        "training_cuda_seconds": float(runtime["cuda_training_seconds"]) - cuda_fit_started,
        "peak_cuda_allocated_bytes": resource_snapshot(device)["cuda_peak_allocated_bytes"],
        "peak_process_rss_bytes": resource_snapshot(device)["process_rss_bytes"],
        "selected_state_dict_sha256": selected_state_hash, "selected_checkpoint_sha256": selected_hash,
        "selected_checkpoint_path": str(selected_path.relative_to(ROOT)),
        "training_array_sha256": arrays_hashes(arrays), "monitor_array_sha256": arrays_hashes(monitor),
        "probability_calibration_data_accessed": False, "threshold_selection_data_accessed": False,
        "final_development_data_accessed": False}
    atomic_json(selection_path, rec)
    return rec


def choose_temperature(model: torch.nn.Module, arrays: dict[str, np.ndarray], prevalence: float,
                       device: torch.device, grid: list[float]) -> tuple[float, dict]:
    logits = natural_logits(model, arrays, prevalence, device)
    labels = residual_target(arrays)
    scores = [(binary_nll(logits / float(t), labels), abs(float(t) - 1.0), float(t)) for t in grid]
    score, _, selected = min(scores)
    return selected, {"selected_temperature": selected, "calibration_nll": score,
                      "grid_scores": [{"temperature": t, "nll": loss} for loss, _, t in scores],
                      "partition_array_sha256": arrays_hashes(arrays)}


def partition_location(root: str, split: str, condition: str) -> tuple[Path, Path]:
    return partition_paths(root, split, condition)


def run_dry_run(prefix: dict[str, np.ndarray], cfg: dict, context: dict,
                 device: torch.device, runtime: dict, model_seed: int,
                 sampling_seconds: float) -> dict:
    if len(prefix["observable"]) != 256:
        raise Stage3Error("The frozen dry run must use exactly 256 prefix rows")
    set_determinism(model_seed)
    model = model_for(context["coordinates"]).to(device)
    d = torch.as_tensor(prefix["detectors"], dtype=torch.float32, device=device)
    pm = torch.as_tensor(prefix["nominal_prediction"], dtype=torch.float32, device=device)
    y = torch.as_tensor(residual_target(prefix).astype(np.float32), device=device)
    start = time.perf_counter()
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg["training"]["learning_rate"])
    for _ in range(5):
        optimizer.zero_grad(set_to_none=True)
        logits = model(d, pm).float()
        loss = F.binary_cross_entropy_with_logits(logits, y)
        if not torch.isfinite(loss):
            raise Stage3Error("Dry-run produced non-finite loss")
        loss.backward()
        if any(p.grad is not None and not torch.isfinite(p.grad).all() for p in model.parameters()):
            raise Stage3Error("Dry-run produced non-finite gradients")
        optimizer.step()
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    elapsed = time.perf_counter() - start
    if device.type == "cuda":
        runtime["cuda_training_seconds"] += elapsed
    runtime["resource_maxima"] = enforce_resources(cfg, device, runtime["start_time"], runtime["cuda_training_seconds"], runtime.get("wall_offset_seconds", 0.0))
    if device.type == "cuda":
        runtime["dry_run_cuda_seconds"] = elapsed
    step_seconds = elapsed / 5
    projected_steps = int(cfg["training"]["maximum_steps_per_root"]) * len(ROOT_IDS)
    estimated_train_seconds = step_seconds * projected_steps
    estimated_sampler_seconds = sampling_seconds * (int(cfg["total_unique_shots_planned"]) / 256)
    conservative_wall_seconds = 2.0 * estimated_train_seconds + 3.0 * estimated_sampler_seconds + 600.0
    conservative_cuda_seconds = 1.5 * estimated_train_seconds + elapsed
    limits = cfg["resources"]
    feasibility_pass = (conservative_wall_seconds < limits["maximum_wall_seconds"] and
                        conservative_cuda_seconds < limits["maximum_measured_cuda_training_seconds"])
    rec = {"status": "PASS" if feasibility_pass else "FAIL", "shots": 256, "counted_within_training_allocation": True,
           "reused_as_training_prefix": True, "training_positive_examples_in_prefix": int(y.sum().item()),
           "sample_sha256": arrays_hashes(prefix), "prefix_sampling_seconds": sampling_seconds,
           "five_update_benchmark_seconds": elapsed, "seconds_per_optimizer_step": step_seconds,
           "projected_max_training_seconds": estimated_train_seconds,
           "projected_sampling_seconds": estimated_sampler_seconds,
           "projected_wall_seconds_excluding_validation_overhead": estimated_train_seconds + estimated_sampler_seconds,
           "conservative_projected_wall_seconds_including_overhead": conservative_wall_seconds,
           "conservative_projected_cuda_seconds": conservative_cuda_seconds,
           "resource_feasibility_gate": "PASS" if feasibility_pass else "FAIL",
           "samples_per_second_estimate": 256 / max(sampling_seconds, 1e-12),
           "peak_cuda_allocation_bytes": resource_snapshot(device)["cuda_peak_allocated_bytes"],
           "process_rss_bytes": resource_snapshot(device)["process_rss_bytes"]}
    atomic_json(RUN / "dry_run_report.json", rec)
    del model, d, pm, y, logits, loss, optimizer
    if device.type == "cuda":
        torch.cuda.empty_cache()
    if not feasibility_pass:
        raise Stage3Error("Dry-run projection cannot safely fit within the frozen wall/CUDA limits")
    return rec


def ensure_partition(root: str, split: str, condition: str, shots: int,
                     context: dict, inventory: dict, cfg: dict, device: torch.device,
                     runtime: dict, status: dict) -> dict[str, np.ndarray]:
    saved = load_partition(root, split, condition, shots)
    if saved is not None:
        return saved
    seed = partition_seed(inventory, root, split, condition)
    circuit = context["circuits"][condition]
    sampler = circuit.compile_detector_sampler(seed=seed)
    prefix_n = 256 if root == ROOT_IDS[0] and split == "training" and condition == TRAIN_CONDITION else 0
    if prefix_n:
        sample_started = time.perf_counter()
        prefix = sample_arrays(sampler, prefix_n, context, condition)
        prefix_sampling_seconds = time.perf_counter() - sample_started
        prefix_path = RAW / root / "training_prefix256.npz"
        if prefix_path.exists():
            with np.load(prefix_path, allow_pickle=False) as z:
                old = {k: z[k] for k in z.files}
            if arrays_hashes(old) != arrays_hashes(prefix):
                raise Stage3Error("Training prefix does not reproduce from its frozen seed")
        else:
            atomic_npz(prefix_path, prefix)
        dry_path = RUN / "dry_run_report.json"
        if not dry_path.exists():
            model_seed = seed_value(inventory, root, purpose="torch_initialization")
            run_dry_run(prefix, cfg, context, device, runtime, model_seed, prefix_sampling_seconds)
        tail = sample_arrays(sampler, shots - prefix_n, context, condition)
        arrays = {key: np.concatenate((prefix[key], tail[key]), axis=0) for key in prefix}
    else:
        arrays = sample_arrays(sampler, shots, context, condition)
    validate_arrays(arrays, shots)
    meta = save_partition(root, split, condition, arrays, seed, context)
    key = f"{root}/{split}/{condition}"
    status.setdefault("completed_partitions", []).append(key)
    status["completed_partitions"] = sorted(set(status["completed_partitions"]))
    status["completed_unique_shots"] = int(status.get("completed_unique_shots", 0)) + shots
    status["last_partition_archive_sha256"] = meta["archive_sha256"]
    status["active_wall_seconds"] = runtime.get("wall_offset_seconds", 0.0) + time.perf_counter() - runtime["start_time"]
    status["measured_cuda_training_seconds"] = runtime["cuda_training_seconds"]
    status["resource_maxima"] = enforce_resources(cfg, device, runtime["start_time"], runtime["cuda_training_seconds"], runtime.get("wall_offset_seconds", 0.0))
    update_status(status)
    return arrays


def load_selected_candidate(root: str, coords: dict, device: torch.device,
                            cfg_sha: str) -> tuple[torch.nn.Module, dict]:
    selection = json.loads((RAW / root / "candidate_selection.json").read_text(encoding="utf-8"))
    selected_path = ROOT / selection["selected_checkpoint_path"]
    if file_sha256(selected_path) != selection["selected_checkpoint_sha256"]:
        raise Stage3Error(f"Selected checkpoint corrupt for {root}")
    payload = torch.load(selected_path, map_location="cpu", weights_only=False)
    if payload.get("config_sha256") != cfg_sha or payload.get("state_dict_sha256") != selection["selected_state_dict_sha256"]:
        raise Stage3Error(f"Selected checkpoint metadata mismatch for {root}")
    model = model_for(coords).to(device)
    restore_state_verified(model, payload["model_state"], selection["selected_state_dict_sha256"])
    return model, selection


def load_stage2_historical(root: str, coords: dict, device: torch.device) -> tuple[torch.nn.Module, dict]:
    old_root = root.replace("stage3-root-", "dev-root-")
    select_path = STAGE2_RUN / "raw" / old_root / "selections" / f"{STAGE2_HISTORICAL_MODEL}.json"
    weights_path = STAGE2_RUN / "checkpoints" / old_root / f"{STAGE2_HISTORICAL_MODEL}_selected.pt"
    if not select_path.is_file() or not weights_path.is_file():
        raise Stage3Error(f"Stage 2 historical checkpoint/selection missing for {old_root}")
    selection = json.loads(select_path.read_text(encoding="utf-8"))
    if file_sha256(weights_path) != selection.get("selected_weights_file_sha256"):
        raise Stage3Error(f"Historical Stage 2 checkpoint hash mismatch for {old_root}")
    payload = torch.load(weights_path, map_location="cpu", weights_only=False)
    if payload.get("model_name") != STAGE2_HISTORICAL_MODEL or payload.get("root_id") != old_root:
        raise Stage3Error(f"Historical checkpoint identity mismatch for {old_root}")
    model = model_for(coords).to(device)
    model.load_state_dict(payload["model_state"])
    selection = {**selection, "selected_weights_path": str(weights_path.relative_to(ROOT)),
                 "selected_weights_file_sha256": file_sha256(weights_path)}
    return model, selection


def infer_candidate(model: torch.nn.Module, arrays: dict[str, np.ndarray], prevalence: float,
                    temperature: float, threshold: float, device: torch.device) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    logits = natural_logits(model, arrays, prevalence, device)
    probs = sigmoid(logits / temperature).astype(np.float32)
    residual = (probs >= threshold).astype(np.uint8)
    pred = arrays["nominal_prediction"] ^ residual
    return logits.astype(np.float32), probs, pred.astype(np.uint8)


def infer_historical(model: torch.nn.Module, arrays: dict[str, np.ndarray], selection: dict,
                     device: torch.device) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    prevalence = float(selection["pooled_residual_training_prevalence"])
    temperature = float(selection["temperature"])
    threshold = float(selection["threshold"])
    return infer_candidate(model, arrays, prevalence, temperature, threshold, device)


def record_policy_freeze(cfg: dict, context: dict, selections: dict,
                         threshold: float, threshold_scores: dict) -> dict:
    policy = {"status": "FROZEN_BEFORE_FINAL_DEVELOPMENT_SAMPLING",
              "protocol_id_sha256": json.loads(FREEZE_PATH.read_text(encoding="utf-8"))["protocol_id_sha256"],
              "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "candidate_model": STAGE3_MODEL, "inference_inputs": ["detectors", "nominal_prediction"],
              "global_threshold": float(threshold), "threshold_objective": "minimum equal-root burst LER on threshold-selection partitions",
              "threshold_grid_scores": threshold_scores,
              "root_selections": selections,
              "circuit_sha256": context["circuit_hashes"], "dem_sha256": context["dem_hashes"],
              "final_development_accessed": False, "independent_test_accessed": False,
              "policy_inputs_sha256": {root: {k: v for k, v in selections[root].items()
                  if k in ("selected_state_dict_sha256", "selected_checkpoint_sha256", "temperature",
                           "calibration_partition_array_sha256", "threshold_partition_array_sha256")}
                  for root in selections}}
    # The policy hash is computed before adding itself, then the JSON is written atomically.
    policy["policy_sha256"] = digest_bytes(json.dumps(policy, sort_keys=True, separators=(",", ":")).encode())
    atomic_json(POLICY_PATH, policy)
    return policy


def status_initial(cfg: dict, freeze_id: str, resume: bool) -> dict:
    if STATUS_PATH.exists():
        old = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        if old.get("freeze_protocol_id_sha256") != freeze_id or old.get("config_sha256") != file_sha256(CONFIG_PATH):
            raise Stage3Error("Existing Stage 3 run belongs to a different freeze/config")
        if old.get("status") == "completed":
            raise Stage3Error("Stage 3 already completed; refusing to rewrite outputs")
        if not resume or old.get("status") not in ("paused", "failed", "running", "finalizing") or old.get("recoverable") is not True:
            raise Stage3Error("Existing Stage 3 state requires a valid --resume or is unrecoverable")
        wall_offset = float(old.get("active_wall_seconds", 0.0))
        if old.get("status") == "running":
            last_update = float(old.get("updated_epoch", 0.0))
            if last_update <= 0:
                raise Stage3Error("Interrupted running state lacks a persisted update time; cannot enforce cumulative wall budget")
            # Count the interval after the last persisted progress update,
            # including any uncertain crash/recovery gap, conservatively.
            wall_offset += max(0.0, time.time() - last_update)
        old["resume_wall_offset_seconds"] = wall_offset
        old["active_wall_seconds"] = wall_offset
        old["last_launch_epoch"] = time.time()
        old["updated_epoch"] = time.time()
        old["status"] = "running"
        old["resume_count"] = int(old.get("resume_count", 0)) + 1
        old["active_job"] = None
        old["active_root"] = None
        old["completed_unique_shots"] = recompute_sample_total()
        old["completed_partitions"] = completed_partition_keys()
        old["measured_cuda_training_seconds"] = max(float(old.get("measured_cuda_training_seconds", 0.0)),
                                                     recovered_cuda_training_seconds())
        atomic_json(STATUS_PATH, old)
        return old
    if resume:
        raise Stage3Error("--resume requested but no Stage 3 status exists")
    status = {"status": "running", "freeze_protocol_id_sha256": freeze_id,
              "config_sha256": file_sha256(CONFIG_PATH), "start_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "completed_partitions": [], "completed_roots": [], "completed_unique_shots": 0,
              "completed_model_jobs": [], "policy_frozen": False, "final_development_accessed": False,
              "independent_test_accessed": False, "resume_count": 0, "recoverable": True}
    status["last_launch_epoch"] = time.time()
    status["resume_wall_offset_seconds"] = 0.0
    status["updated_epoch"] = time.time()
    atomic_json(STATUS_PATH, status)
    return status


def acquire_lock() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    if LOCK_PATH.exists():
        try:
            old_lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
            pid = int(old_lock["pid"])
        except Exception as exc:
            raise Stage3Error("Existing runner lock is unreadable; inspect it manually before resuming") from exc
        if psutil.pid_exists(pid):
            raise Stage3Error(f"Stage 3 runner lock belongs to live PID {pid}; refusing concurrent execution")
        stale = LOCK_PATH.with_name(f"runner.lock.stale.{pid}.{int(time.time())}")
        os.replace(LOCK_PATH, stale)
    try:
        with LOCK_PATH.open("x", encoding="utf-8") as f:
            f.write(json.dumps({"pid": os.getpid(), "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}))
            f.flush()
            os.fsync(f.fileno())
    except FileExistsError as exc:
        raise Stage3Error("Stage 3 runner lock exists; verify no other runner is active") from exc


def release_lock() -> None:
    try:
        LOCK_PATH.unlink()
    except FileNotFoundError:
        pass


def environment(cfg: dict) -> tuple[torch.device, dict]:
    if not torch.cuda.is_available():
        raise Stage3Error("CUDA is unavailable; frozen protocol forbids CPU fallback")
    device = torch.device("cuda")
    if torch.cuda.device_count() < 1:
        raise Stage3Error("No CUDA device is visible")
    software = {"python": sys.version.split()[0], "torch": torch.__version__, "stim": stim.__version__,
                "pymatching": pymatching.__version__, "cuda": torch.version.cuda,
                "gpu": torch.cuda.get_device_name(device)}
    if "RTX 4050" not in software["gpu"]:
        print(f"NOTE: executing on CUDA device {software['gpu']}")
    return device, software


def update_status(status: dict) -> None:
    status["updated_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    status["updated_epoch"] = time.time()
    atomic_json(STATUS_PATH, status)


def generate_pre_final_partitions(cfg: dict, context: dict, inventory: dict, device: torch.device,
                                  runtime: dict, status: dict) -> dict[str, dict[str, dict[str, np.ndarray]]]:
    result = {}
    split_map = (
        ("training", "synthetic_spatial_burst", int(cfg["shots_per_root"]["training_synthetic_spatial_burst"])),
        ("monitor", "synthetic_spatial_burst", int(cfg["shots_per_root"]["monitor_synthetic_spatial_burst"])),
        ("probability_calibration", "synthetic_spatial_burst", int(cfg["shots_per_root"]["probability_calibration_synthetic_spatial_burst"])),
        ("threshold_selection", "synthetic_spatial_burst", int(cfg["shots_per_root"]["threshold_selection_synthetic_spatial_burst"])),
    )
    for root in ROOT_IDS:
        result[root] = {}
        for split, condition, shots in split_map:
            status["active_root"] = root
            status["active_job"] = f"sample:{split}:{condition}"
            update_status(status)
            result[root][split] = {condition: ensure_partition(root, split, condition, shots,
                context, inventory, cfg, device, runtime, status)}
    return result


def train_all(cfg: dict, context: dict, inventory: dict, parts: dict,
              device: torch.device, runtime: dict, status: dict) -> tuple[dict, float, dict]:
    validate_selection_partitions(parts)
    if POLICY_PATH.is_file():
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        claimed = policy.get("policy_sha256")
        unhashed = {k: v for k, v in policy.items() if k != "policy_sha256"}
        actual = digest_bytes(json.dumps(unhashed, sort_keys=True, separators=(",", ":")).encode())
        if claimed != actual or policy.get("protocol_id_sha256") != json.loads(FREEZE_PATH.read_text(encoding="utf-8"))["protocol_id_sha256"]:
            raise Stage3Error("Existing policy freeze is corrupt or belongs to another protocol")
        selections = policy.get("root_selections", {})
        if set(selections) != set(ROOT_IDS):
            raise Stage3Error("Existing policy freeze does not contain all five root selections")
        for root in ROOT_IDS:
            selected_path = checkpoint_paths(root)[1]
            if not selected_path.is_file() or file_sha256(selected_path) != selections[root].get("selected_checkpoint_sha256"):
                raise Stage3Error(f"Frozen policy checkpoint missing or changed for {root}")
            selection_path = RAW / root / "candidate_selection.json"
            if not selection_path.is_file():
                raise Stage3Error(f"Frozen candidate selection missing for {root}")
            saved_selection = json.loads(selection_path.read_text(encoding="utf-8"))
            for key in ("selected_checkpoint_sha256", "temperature", "global_threshold"):
                if saved_selection.get(key) != selections[root].get(key):
                    raise Stage3Error(f"Frozen candidate selection mismatch for {root}: {key}")
        status["policy_frozen"] = True
        status["policy_sha256"] = claimed
        return selections, float(policy["global_threshold"]), policy
    if status.get("final_development_accessed") or status.get("policy_frozen"):
        raise Stage3Error("Final development began but its frozen candidate policy is unavailable")
    cfg_sha = file_sha256(CONFIG_PATH)
    selections = {}
    threshold_probs = {}
    for root in ROOT_IDS:
        status["active_root"] = root
        status["active_job"] = "train-and-calibrate-candidate"
        update_status(status)
        train = parts[root]["training"][TRAIN_CONDITION]
        monitor = parts[root]["monitor"][TRAIN_CONDITION]
        calibration = parts[root]["probability_calibration"][TRAIN_CONDITION]
        threshold_data = parts[root]["threshold_selection"][TRAIN_CONDITION]
        selection = fit_candidate(root, train, monitor, context["coordinates"], cfg, inventory,
                                  cfg_sha, device, runtime["start_time"], runtime)
        model, _ = load_selected_candidate(root, context["coordinates"], device, cfg_sha)
        temperature, cal_rec = choose_temperature(model, calibration, selection["training_residual_prevalence"],
            device, cfg["selection"]["temperature_grid"])
        logits = natural_logits(model, threshold_data, selection["training_residual_prevalence"], device)
        prob = sigmoid(logits / temperature).astype(np.float64)
        threshold_probs[root] = {"probability": prob, "arrays": threshold_data}
        selection["temperature"] = temperature
        selection["probability_calibration_data_accessed"] = True
        selection["calibration_partition_array_sha256"] = arrays_hashes(calibration)
        selection["calibration_grid_scores"] = cal_rec["grid_scores"]
        selection["calibration_nll"] = cal_rec["calibration_nll"]
        selection["threshold_partition_array_sha256"] = arrays_hashes(threshold_data)
        selection["final_development_data_accessed"] = False
        atomic_json(RAW / root / "candidate_selection_prethreshold.json", selection)
        selections[root] = selection
        del model
        if device.type == "cuda":
            torch.cuda.empty_cache()
        status["active_wall_seconds"] = runtime.get("wall_offset_seconds", 0.0) + time.perf_counter() - runtime["start_time"]
        status["measured_cuda_training_seconds"] = runtime["cuda_training_seconds"]
        update_status(status)

    grid = [i / 100 for i in range(1, 100)]
    global_threshold, threshold_scores = choose_global_threshold(threshold_probs, ROOT_IDS, grid)
    chosen = next(score for score in threshold_scores if score["threshold"] == global_threshold)
    for root in ROOT_IDS:
        selection = selections[root]
        selection["global_threshold"] = global_threshold
        selection["threshold_selection_objective"] = chosen["equal_root_mean_ler"]
        selection["threshold_selection_data_accessed"] = True
        selection["selection_frozen_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        atomic_json(RAW / root / "candidate_selection.json", selection)
        status.setdefault("completed_model_jobs", []).append(root)
    policy = record_policy_freeze(cfg, context, selections, global_threshold, threshold_scores)
    status["policy_frozen"] = True
    status["policy_sha256"] = policy["policy_sha256"]
    status["policy_frozen_utc"] = policy["frozen_utc"]
    status["active_wall_seconds"] = runtime.get("wall_offset_seconds", 0.0) + time.perf_counter() - runtime["start_time"]
    status["measured_cuda_training_seconds"] = runtime["cuda_training_seconds"]
    update_status(status)
    return selections, global_threshold, policy


def summarize_root(root: str, prediction: dict[str, np.ndarray], final_arrays: dict[str, dict],
                   selections: dict, historical_selections: dict) -> dict:
    result = {"root_id": root, "conditions": {}}
    for condition in CONDITIONS:
        arrays = final_arrays[condition]
        y = arrays["observable"]
        pm = arrays["nominal_prediction"]
        burst_pm = arrays["burst_prediction"]
        base_wrong = pm != y
        burst_wrong = burst_pm != y
        cell = {"shots": int(len(y)), "observable_errors_raw": int(y.sum()),
                "nominal_fixed_errors": int(base_wrong.sum()), "nominal_fixed_ler": float(base_wrong.mean()),
                "burst_informed_errors": int(burst_wrong.sum()) if condition == TRAIN_CONDITION else None,
                "burst_informed_ler": float(burst_wrong.mean()) if condition == TRAIN_CONDITION else None,
                "models": {}}
        for model_key in ("historical_residual_cnn", "stage3_burst_focused_residual_cnn"):
            pred = prediction[f"{condition}__{model_key}__prediction"]
            residual_probability = prediction[f"{condition}__{model_key}__probability"]
            counts = correction_metrics(pred, pm, y)
            cell["models"][model_key] = {
                **counts, "ler": float(counts["errors"] / len(y)),
                "brier_residual": float(np.mean((residual_probability - (y ^ pm)) ** 2)),
                "residual_score_nll": float(-np.mean((y ^ pm) * np.log(np.clip(residual_probability, 1e-12, 1)) +
                    (1 - (y ^ pm)) * np.log(np.clip(1 - residual_probability, 1e-12, 1)))),
            }
        result["conditions"][condition] = cell
    result["prediction_archive_sha256"] = file_sha256(PREDICTIONS / f"{root}.npz")
    return result


def generate_final_and_score(cfg: dict, context: dict, inventory: dict, device: torch.device,
                             runtime: dict, status: dict, selections: dict,
                             global_threshold: float, policy: dict) -> dict:
    if json.loads(POLICY_PATH.read_text(encoding="utf-8")).get("policy_sha256") != policy.get("policy_sha256"):
        raise Stage3Error("Candidate policy freeze changed before final sample generation")
    if policy.get("final_development_accessed") is not False:
        raise Stage3Error("Policy file shows final data was accessed before selection freeze")
    cfg_sha = file_sha256(CONFIG_PATH)
    per_root = {}
    for root in ROOT_IDS:
        status["active_root"] = root
        status["final_development_accessed"] = True
        status.setdefault("final_development_roots_started", []).append(root) if root not in status.get("final_development_roots_started", []) else None
        update_status(status)
        final_arrays = {}
        for condition in CONDITIONS:
            shots = int(cfg["shots_per_root"]["final_development_synthetic_spatial_burst"] if condition == TRAIN_CONDITION
                        else cfg["shots_per_root"]["final_development_nominal_control"])
            split = "final_development_evaluation"
            status["active_job"] = f"sample-final:{condition}"
            update_status(status)
            final_arrays[condition] = ensure_partition(root, split, condition, shots, context,
                inventory, cfg, device, runtime, status)

        candidate, selection = load_selected_candidate(root, context["coordinates"], device, cfg_sha)
        historical, historical_selection = load_stage2_historical(root, context["coordinates"], device)
        prediction = {}
        inference_started = time.perf_counter()
        for condition in CONDITIONS:
            data = final_arrays[condition]
            prediction[f"{condition}__nominal_prediction"] = data["nominal_prediction"]
            prediction[f"{condition}__burst_prediction"] = data["burst_prediction"]
            prediction[f"{condition}__observable"] = data["observable"]
            prediction[f"{condition}__detectors"] = data["detectors"]
            tic = time.perf_counter()
            hist_logits, hist_prob, hist_pred = infer_historical(historical, data, historical_selection, device)
            candidate_logits, candidate_prob, candidate_pred = infer_candidate(candidate, data,
                float(selection["training_residual_prevalence"]), float(selection["temperature"]),
                global_threshold, device)
            runtime["inference_wall_seconds"] += time.perf_counter() - tic
            prediction[f"{condition}__historical_residual_cnn__logits"] = hist_logits
            prediction[f"{condition}__historical_residual_cnn__probability"] = hist_prob
            prediction[f"{condition}__historical_residual_cnn__prediction"] = hist_pred
            prediction[f"{condition}__stage3_burst_focused_residual_cnn__logits"] = candidate_logits
            prediction[f"{condition}__stage3_burst_focused_residual_cnn__probability"] = candidate_prob
            prediction[f"{condition}__stage3_burst_focused_residual_cnn__prediction"] = candidate_pred
        if device.type == "cuda":
            torch.cuda.synchronize(device)
        inference_seconds = time.perf_counter() - inference_started
        pred_path = PREDICTIONS / f"{root}.npz"
        pred_hash = atomic_npz(pred_path, prediction)
        metric = summarize_root(root, prediction, final_arrays, selections, historical_selections={})
        metric["prediction_archive_sha256"] = pred_hash
        metric["candidate_global_threshold"] = global_threshold
        metric["candidate_temperature"] = float(selection["temperature"])
        metric["candidate_training_unique_positive_count"] = int(selection["training_positive_count"])
        metric["candidate_positive_reuse_ratio"] = float(selection["positive_reuse_ratio"])
        metric["candidate_best_epoch"] = int(selection["best_epoch"])
        metric["candidate_optimizer_steps"] = int(selection["optimizer_steps"])
        metric["candidate_parameter_count"] = int(selection["parameter_count"])
        metric["historical_threshold"] = float(historical_selection["threshold"])
        metric["historical_temperature"] = float(historical_selection["temperature"])
        metric["historical_selected_weights_sha256"] = historical_selection["selected_weights_file_sha256"]
        metric["inference_wall_seconds"] = inference_seconds
        per_root[root] = metric
        atomic_json(RAW / "per_root_results.json", per_root)
        status.setdefault("completed_roots", []).append(root)
        status["completed_roots"] = sorted(set(status["completed_roots"]))
        status["active_job"] = None
        status["active_root"] = None
        status["completed_unique_shots"] = recompute_sample_total()
        status["active_wall_seconds"] = runtime.get("wall_offset_seconds", 0.0) + time.perf_counter() - runtime["start_time"]
        status["measured_cuda_training_seconds"] = runtime["cuda_training_seconds"]
        status["resource_maxima"] = enforce_resources(cfg, device, runtime["start_time"], runtime["cuda_training_seconds"], runtime.get("wall_offset_seconds", 0.0))
        update_status(status)
        del candidate, historical
        if device.type == "cuda":
            torch.cuda.empty_cache()
    return per_root


def recompute_sample_total() -> int:
    total = 0
    for meta_path in RAW.glob("stage3-root-*/" + "*.json"):
        if meta_path.name in ("candidate_selection.json", "candidate_selection_prethreshold.json"):
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if meta.get("kind") == "stage3_partition":
            total += int(meta["shots"])
    return total


def completed_partition_keys() -> list[str]:
    keys = []
    for meta_path in RAW.glob("stage3-root-*/*.json"):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if meta.get("kind") == "stage3_partition":
            keys.append(f"{meta['root_id']}/{meta['split']}/{meta['condition']}")
    return sorted(set(keys))


def write_final_results(cfg: dict, per_root: dict, context: dict, runtime: dict,
                        freeze_id: str, software: dict) -> dict:
    from outputs.cnn_stage3_residual_gate_v1.audit_stage3 import aggregate_results
    result = aggregate_results(per_root, cfg, freeze_id, context, runtime, software)
    atomic_json(HERE / "CNN_STAGE3_RESULTS.json", result)
    return result


def write_manifest() -> str:
    files = {}
    for folder in (HERE, RUN):
        for path in sorted(x for x in folder.rglob("*") if x.is_file() and "__pycache__" not in x.parts and x.suffix != ".pyc"):
            if path == LOCK_PATH or path.name.endswith(".tmp") or path == RUN / "MANIFEST.json" or path == STATUS_PATH:
                continue
            files[path.relative_to(ROOT).as_posix()] = {"bytes": path.stat().st_size, "sha256": file_sha256(path)}
    payload = {"status": "RUN_COMPLETE_EVIDENCE_HASHED", "unique_shots": recompute_sample_total(),
               "roots": 5, "model_root_jobs": 5, "independent_test_accessed": False,
               "mutable_status_lock_and_manifest_excluded": True, "files": files}
    path = RUN / "MANIFEST.json"
    atomic_json(path, payload)
    return file_sha256(path)


def write_public_evidence_manifest(runtime_manifest_sha256: str) -> str:
    names = (
        "CNN_STAGE3_PROTOCOL.md", "CNN_STAGE3_DIAGNOSTIC_REVIEW.md", "CNN_STAGE3_REPRODUCE.md",
        "CNN_STAGE3_PROTOCOL_AMENDMENT_PRE_SAMPLING.md", "stage3_config.json", "seed_inventory.json", "seed_audit.json", "FREEZE.json", "FREEZE_SUPERSEDED_001.json",
        "STAGE3_POLICY_FREEZE.json", "CNN_STAGE3_RESULTS.json", "CNN_STAGE3_AUDIT_RESULTS.json",
        "CNN_STAGE3_RESULTS.md", "CNN_STAGE3_INDEPENDENT_AUDIT.md", "CNN_STAGE3_COMPETITION_EVIDENCE.md",
        "CNN_STAGE3_EXECUTION_REPORT.md", "CNN_STAGE3_PER_ROOT.csv", "run_stage3.py", "audit_stage3.py", "freeze_stage3.py",
        "tests/test_stage3.py")
    files = {}
    for name in names:
        path = HERE / name
        if not path.is_file():
            raise Stage3Error(f"Cannot make evidence manifest; missing {name}")
        files[path.relative_to(ROOT).as_posix()] = {"bytes": path.stat().st_size, "sha256": file_sha256(path)}
    payload = {"status": "PASS_INDEPENDENT_AUDIT_COMPLETED", "protocol_id_sha256": json.loads(FREEZE_PATH.read_text(encoding="utf-8"))["protocol_id_sha256"],
        "runtime_manifest_path": (RUN / "MANIFEST.json").relative_to(ROOT).as_posix(),
        "runtime_manifest_sha256": runtime_manifest_sha256, "unique_shots": recompute_sample_total(),
        "independent_roots": 5, "independent_test_accessed": False, "files": files}
    atomic_json(HERE / "CNN_STAGE3_EVIDENCE_MANIFEST.json", payload)
    return file_sha256(HERE / "CNN_STAGE3_EVIDENCE_MANIFEST.json")


def run_experiment(resume: bool = False) -> dict:
    run_started = time.perf_counter()
    cfg, inventory, freeze_id = verify_freeze()
    device, software = environment(cfg)
    context = build_context(cfg)
    if not resume and any(RUN.rglob("*.npz")):
        raise Stage3Error("Run already contains shot archives; use resume only if status allows it")
    acquire_lock()
    try:
        status = status_initial(cfg, freeze_id, resume)
    except Exception:
        release_lock()
        raise
    runtime = {"start_time": run_started,
               "wall_offset_seconds": float(status.get("resume_wall_offset_seconds", 0.0)),
               "cuda_training_seconds": float(status.get("measured_cuda_training_seconds", 0.0)),
               "inference_wall_seconds": 0.0, "resource_maxima": {}}
    try:
        status["software"] = software
        status["gpu"] = software["gpu"]
        status["circuit_sha256"] = context["circuit_hashes"]
        status["dem_sha256"] = context["dem_hashes"]
        status["active_job"] = "sample-and-train-development-partitions"
        update_status(status)
        parts = generate_pre_final_partitions(cfg, context, inventory, device, runtime, status)
        selections, threshold, policy = train_all(cfg, context, inventory, parts, device, runtime, status)
        status["completed_unique_shots"] = recompute_sample_total()
        if status["completed_unique_shots"] != 125000:
            raise Stage3Error(f"Pre-final unique shot count is not 125,000: {status['completed_unique_shots']}")
        per_root = generate_final_and_score(cfg, context, inventory, device, runtime, status,
                                            selections, threshold, policy)
        if recompute_sample_total() != 200000:
            raise Stage3Error(f"Final unique shot count is not 200,000: {recompute_sample_total()}")
        status["status"] = "finalizing"
        status["active_job"] = "independent-rescore"
        status["completed_unique_shots"] = 200000
        status["active_wall_seconds"] = runtime.get("wall_offset_seconds", 0.0) + time.perf_counter() - runtime["start_time"]
        status["measured_cuda_training_seconds"] = runtime["cuda_training_seconds"]
        status["inference_wall_seconds"] = runtime["inference_wall_seconds"]
        status["resource_maxima"] = enforce_resources(cfg, device, runtime["start_time"], runtime["cuda_training_seconds"], runtime.get("wall_offset_seconds", 0.0))
        update_status(status)
        audit = subprocess.run([sys.executable, str(HERE / "audit_stage3.py"), "--run-audit"],
                               cwd=ROOT, check=False, capture_output=True, text=True)
        if audit.returncode != 0:
            raise Stage3Error(f"Independent audit failed with exit {audit.returncode}: {audit.stdout}\n{audit.stderr}")
        audit_result = json.loads((HERE / "CNN_STAGE3_AUDIT_RESULTS.json").read_text(encoding="utf-8"))
        if audit_result.get("status") != "PASS":
            raise Stage3Error(f"Independent audit status not PASS: {audit_result.get('failures')}")
        result = json.loads((HERE / "CNN_STAGE3_RESULTS.json").read_text(encoding="utf-8"))
        status["status"] = "completed"
        status["active_job"] = None
        status["active_root"] = None
        status["independent_audit_status"] = "PASS"
        status["independent_test_accessed"] = False
        status["completed_unique_shots"] = 200000
        status["completed_model_jobs"] = list(ROOT_IDS)
        status["completed_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        status["active_wall_seconds"] = runtime.get("wall_offset_seconds", 0.0) + time.perf_counter() - runtime["start_time"]
        status["measured_cuda_training_seconds"] = runtime["cuda_training_seconds"]
        status["inference_wall_seconds"] = runtime["inference_wall_seconds"]
        status["resource_maxima"] = enforce_resources(cfg, device, runtime["start_time"], runtime["cuda_training_seconds"], runtime.get("wall_offset_seconds", 0.0))
        manifest_sha = write_manifest()
        public_manifest_sha = write_public_evidence_manifest(manifest_sha)
        status["evidence_manifest_sha256"] = manifest_sha
        status["public_evidence_manifest_sha256"] = public_manifest_sha
        update_status(status)
        return {"status": "completed", "shots": 200000, "roots": 5, "gate": result["development_gate"],
                "manifest_sha256": manifest_sha, "audit": audit_result["status"]}
    except KeyboardInterrupt:
        status["status"] = "paused"
        status["recoverable"] = True
        status["active_job"] = None
        status["active_root"] = None
        status["completed_unique_shots"] = recompute_sample_total()
        status["active_wall_seconds"] = runtime.get("wall_offset_seconds", 0.0) + time.perf_counter() - runtime["start_time"]
        status["measured_cuda_training_seconds"] = runtime["cuda_training_seconds"]
        update_status(status)
        raise
    except Exception as exc:
        status["status"] = "failed"
        status["failure"] = f"{type(exc).__name__}: {exc}"
        status["traceback"] = traceback.format_exc()
        status["recoverable"] = not isinstance(exc, Stage3Error)
        status["failed_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        status["active_job"] = None
        status["active_root"] = None
        status["completed_unique_shots"] = recompute_sample_total()
        status["active_wall_seconds"] = runtime.get("wall_offset_seconds", 0.0) + time.perf_counter() - runtime["start_time"]
        status["measured_cuda_training_seconds"] = runtime["cuda_training_seconds"]
        update_status(status)
        raise
    finally:
        release_lock()


def validate_only() -> dict:
    cfg, inventory, freeze_id = verify_freeze()
    device, software = environment(cfg)
    context = build_context(cfg)
    # Check the sample seed can be passed to Stim without sampling a shot.
    seed = partition_seed(inventory, ROOT_IDS[0], "training", TRAIN_CONDITION)
    _ = context["circuits"][TRAIN_CONDITION].compile_detector_sampler(seed=seed)
    model = model_for(context["coordinates"]).to(device)
    test_d = torch.zeros((2, 40), dtype=torch.float32, device=device)
    test_pm = torch.zeros((2,), dtype=torch.float32, device=device)
    with torch.inference_mode():
        output = model(test_d, test_pm)
    if output.shape != (2,) or not torch.isfinite(output).all():
        raise Stage3Error("Candidate model shape/finiteness validation failed")
    return {"status": "PASS_NO_SAMPLING", "freeze_protocol_id_sha256": freeze_id,
            "device": software, "detectors": 40, "observables": 1,
            "circuit_sha256": context["circuit_hashes"], "dem_sha256": context["dem_hashes"],
            "candidate_parameters": sum(p.numel() for p in model.parameters()),
            "sampled_shots": 0, "independent_test_accessed": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--validate-only", action="store_true")
    group.add_argument("--run", action="store_true")
    group.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.validate_only:
        print(json.dumps(validate_only(), indent=2))
        return 0
    print(json.dumps(run_experiment(resume=args.resume), indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Stage 3 stopped: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
