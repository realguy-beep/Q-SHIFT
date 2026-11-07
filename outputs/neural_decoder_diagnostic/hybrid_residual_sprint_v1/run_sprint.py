"""Restartable, bounded development-only residual-decoder experiment.

This runner has no independent-test sampler, seed, path, or split. Final
development samples are first generated after all model and policy selections
are frozen.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import os
import random
import shutil
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import numpy as np
import psutil
import torch
import torch.nn.functional as F

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
AUTO = REPO / "outputs" / "neural_decoder_diagnostic" / "autonomous_development"
sys.path.insert(0, str(REPO / "dashboard"))
sys.path.insert(0, str(AUTO))

from experiment import (ResidualPositionCNN, balanced_epoch_batches, choose_temperature,
                        hash_state, macro_nll, save_npz_atomic, target_for)
from simulator import decode_matching, prepare, sample

CONFIG_PATH = HERE / "config.json"
INVENTORY_PATH = HERE / "SEED_INVENTORY.json"
FREEZE_PATH = HERE / "FREEZE.json"
RUN_DIR = HERE / "run"
ALLOWED_SPLITS = ("train", "monitor", "calibration", "threshold_selection",
                  "final_development_evaluation")
REGIMES = ("x_biased", "balanced", "z_biased")
T_CRIT_DF4 = 2.7764451051977987
RUN_STARTED_MONO = None
ACTIVE_WALL_BASE = 0.0


class PauseRun(Exception):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(value: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    # fsync must use a writable descriptor on Windows.  The old write_text()
    # followed by an rb open fails with EBADF on Windows and leaves a complete
    # but uncommitted .tmp file.
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(value, indent=2, allow_nan=False, default=str) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def append_event(value: dict) -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    with (RUN_DIR / "progress.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"utc": utc_now(), **value}, allow_nan=False, default=str) + "\n")
        f.flush()
        os.fsync(f.fileno())


def atomic_torch_save(value: dict, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as f:
        torch.save(value, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    digest = sha256(path)
    atomic_json({"sha256": digest, "bytes": path.stat().st_size}, path.with_suffix(path.suffix + ".json"))
    return digest


def verified_torch_load(path: Path):
    meta_path = path.with_suffix(path.suffix + ".json")
    if not path.is_file() or not meta_path.is_file():
        raise RuntimeError(f"Checkpoint or metadata missing: {path}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if sha256(path) != meta.get("sha256"):
        raise RuntimeError(f"Checkpoint SHA-256 mismatch: {path}")
    return torch.load(path, map_location="cpu", weights_only=False)


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def load_config_inventory():
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    inv = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    return cfg, inv


def verify_freeze() -> tuple[dict, dict, dict]:
    if not FREEZE_PATH.is_file():
        raise RuntimeError("Pre-sampling freeze is missing.")
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    cfg, inv = load_config_inventory()
    accepted_freeze_states = {
        "FROZEN BEFORE ALL NEW SAMPLING",
        "FROZEN BEFORE PRODUCTION SAMPLING; PREFLIGHT DIAGNOSTICS PRESERVED",
    }
    if freeze.get("status") not in accepted_freeze_states:
        raise RuntimeError("Freeze status is not an accepted pre-sampling state.")
    if sha256(CONFIG_PATH) != freeze.get("config_sha256"):
        raise RuntimeError("Config hash differs from pre-sampling freeze.")
    if sha256(HERE / "EXPERIMENT_PROTOCOL.md") != freeze.get("protocol_sha256"):
        raise RuntimeError("Protocol hash differs from pre-sampling freeze.")
    if sha256(HERE / "FAILURE_ANALYSIS.md") != freeze.get("failure_analysis_sha256"):
        raise RuntimeError("Failure-analysis hash differs from pre-sampling freeze.")
    for rel, digest in freeze.get("source_sha256", {}).items():
        path = HERE / rel if (HERE / rel).is_file() else REPO / rel
        if not path.is_file() or sha256(path) != digest:
            raise RuntimeError(f"Frozen source hash mismatch: {rel}")
    if freeze.get("python_executable") != sys.executable:
        raise RuntimeError("Python executable differs from the pre-sampling freeze.")
    for package, expected in freeze.get("packages", {}).items():
        actual = importlib.metadata.version(package)
        if actual != expected:
            raise RuntimeError(f"Frozen package version changed for {package}: {actual} != {expected}")
    if not torch.cuda.is_available() or torch.cuda.get_device_name(0) != freeze.get("cuda_device"):
        raise RuntimeError("CUDA runtime/device differs from the pre-sampling freeze.")
    if not inv.get("passed") or not inv.get("seed_collision_audit_passed") or inv.get("historical_collisions"):
        raise RuntimeError("Seed inventory collision audit did not pass.")
    if inv.get("derived_seed_count") != inv.get("unique_derived_seed_count"):
        raise RuntimeError("Seed inventory contains internal collisions.")
    if cfg.get("independent_test_access") != "prohibited; no test data or test seed stream is allocated":
        raise RuntimeError("Unexpected test-access configuration.")
    if any("test" in x.get("split", "").lower() for x in inv.get("streams", [])):
        raise RuntimeError("Forbidden test stream present in inventory.")
    if not (AUTO / "run" / "progress.json").is_file():
        raise RuntimeError("Previous autonomous-run completion record missing.")
    old_status = read_json(AUTO / "run" / "progress.json", {})
    if old_status.get("status") != "completed" or int(old_status.get("independent_test_access", -1)) != 0:
        raise RuntimeError("Previous run is not safely complete or its test-access audit is not zero.")
    if (AUTO / "run" / "controller.lock").exists():
        raise RuntimeError("Previous autonomous run still has a controller lock.")
    return freeze, cfg, inv


def resource_snapshot() -> dict:
    proc = psutil.Process(os.getpid())
    free = shutil.disk_usage(HERE).free / (1024 ** 3)
    cuda_alloc = torch.cuda.memory_allocated(0) / (1024 ** 3) if torch.cuda.is_available() else 0.0
    cuda_reserved = torch.cuda.memory_reserved(0) / (1024 ** 3) if torch.cuda.is_available() else 0.0
    return {"rss_gib": proc.memory_info().rss / (1024 ** 3), "free_disk_gib": free,
            "cuda_allocated_gib": cuda_alloc, "cuda_reserved_gib": cuda_reserved}


def binary(name: str, arr: np.ndarray) -> None:
    if not np.isfinite(arr).all() or np.any((arr != 0) & (arr != 1)):
        raise ValueError(f"{name} has nonfinite or non-binary values")


def normalize_prediction(pred: np.ndarray, n: int) -> np.ndarray:
    out = np.asarray(pred, dtype=np.uint8)
    if out.ndim == 2:
        if out.shape != (n, 1):
            raise ValueError(f"Unexpected PyMatching output shape {out.shape}")
        out = out[:, 0]
    if out.shape != (n,):
        raise ValueError(f"Unexpected PyMatching prediction shape {out.shape}")
    binary("PyMatching prediction", out)
    return out


def data_seed_stream(inv: dict, root: int, regime: str, split: str) -> dict:
    rows = [r for r in inv["streams"] if r["root"] == root and r["regime"] == regime and r["split"] == split]
    if len(rows) != 1:
        raise RuntimeError(f"Expected one seed stream for root={root} regime={regime} split={split}")
    return rows[0]


def committed_shots() -> int:
    total = 0
    data_dir = RUN_DIR / "data"
    if not data_dir.exists():
        return 0
    for meta_path in data_dir.glob("*.json"):
        try:
            total += int(json.loads(meta_path.read_text(encoding="utf-8")).get("shots", 0))
        except Exception:
            continue
    return total


def run_progress() -> dict:
    return read_json(RUN_DIR / "PROGRESS.json", {"status": "not_started", "completed_jobs": [],
        "active_wall_seconds": 0.0, "gpu_training_seconds": 0.0, "gpu_inference_seconds": 0.0,
        "sampling_attempted_shots": 0, "committed_unique_shots": 0, "independent_test_access": 0})


def set_progress(**updates) -> dict:
    p = run_progress()
    p.update(updates)
    if RUN_STARTED_MONO is not None:
        p["active_wall_seconds"] = ACTIVE_WALL_BASE + time.monotonic() - RUN_STARTED_MONO
    p["updated_utc"] = utc_now()
    p["committed_unique_shots"] = committed_shots()
    current = resource_snapshot()
    prior_max = p.get("resource_maxima", {})
    p["resource_maxima"] = {
        "rss_gib": max(float(prior_max.get("rss_gib", 0.0)), current["rss_gib"]),
        "cuda_allocated_gib": max(float(prior_max.get("cuda_allocated_gib", 0.0)), current["cuda_allocated_gib"]),
        "cuda_reserved_gib": max(float(prior_max.get("cuda_reserved_gib", 0.0)), current["cuda_reserved_gib"]),
        "minimum_free_disk_gib": min(float(prior_max.get("minimum_free_disk_gib", current["free_disk_gib"])), current["free_disk_gib"]),
    }
    p["resources"] = current
    atomic_json(p, RUN_DIR / "PROGRESS.json")
    return p


def enforce_limits(cfg: dict, progress: dict, run_started: float | None = None) -> None:
    res = resource_snapshot()
    lim = cfg["limits"]
    if res["free_disk_gib"] < float(lim["minimum_free_disk_gib"]):
        raise RuntimeError(f"Free disk fell below cap: {res['free_disk_gib']:.3f} GiB")
    if res["rss_gib"] > float(lim["maximum_process_rss_gib"]):
        raise RuntimeError(f"Process RSS exceeded cap: {res['rss_gib']:.3f} GiB")
    if res["cuda_allocated_gib"] > float(lim["maximum_cuda_allocated_gib"]):
        raise RuntimeError(f"CUDA allocation exceeded cap: {res['cuda_allocated_gib']:.3f} GiB")
    shot_cap = int(cfg["sampling"]["maximum_unique_production_shots"])
    if committed_shots() > shot_cap:
        raise RuntimeError(f"Committed unique simulation shots exceeded the frozen cap: {committed_shots()} > {shot_cap}")
    active = (ACTIVE_WALL_BASE + time.monotonic() - RUN_STARTED_MONO
              if RUN_STARTED_MONO is not None else float(progress.get("active_wall_seconds", 0.0)))
    if active >= float(lim["wall_seconds"]):
        raise PauseRun("3-hour active wall-clock cap reached")
    gpu = float(progress.get("gpu_training_seconds", 0.0)) + float(progress.get("gpu_inference_seconds", 0.0))
    if gpu >= float(lim["gpu_seconds"]):
        raise PauseRun("2.5-hour CUDA budget reached")
    if (RUN_DIR / "STOP").exists():
        raise PauseRun("Safe-stop marker detected")


def save_sample_archive(path: Path, arrays: dict, metadata: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as f:
        np.savez_compressed(f, **arrays)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    metadata["archive_sha256"] = sha256(path)
    atomic_json(metadata, path.with_suffix(".json"))


def load_sample_archive(path: Path, expected_split: str | None = None):
    meta_path = path.with_suffix(".json")
    if not path.is_file() or not meta_path.is_file():
        raise RuntimeError(f"Sample archive or metadata missing: {path}")
    meta = read_json(meta_path)
    if sha256(path) != meta.get("archive_sha256"):
        raise RuntimeError(f"Sample archive hash mismatch: {path}")
    if meta.get("independent_test_access") != 0:
        raise RuntimeError(f"Sample metadata has unexpected test-access value: {path}")
    if expected_split and meta.get("split") != expected_split:
        raise RuntimeError(f"Sample split mismatch for {path}: {meta.get('split')}")
    with np.load(path, allow_pickle=False) as z:
        arrays = {key: z[key] for key in z.files}
    return arrays, meta


def prepared_regimes(cfg: dict) -> dict:
    out = {}
    for regime in REGIMES:
        c = {"memory_basis": "z", "noise_regime": regime,
             "distance": cfg["circuit"]["distance"], "rounds": cfg["circuit"]["rounds"],
             "gate_p": cfg["circuit"]["gate_p"], "measurement_p": cfg["circuit"]["measurement_p"],
             "bias_ratio": cfg["circuit"]["bias_ratio"]}
        circuit, record, dem, matching, index, bank_records = prepare(c)
        if circuit.num_detectors != 40 or circuit.num_observables != 1:
            raise RuntimeError(f"Unexpected detector/observable count in {regime}")
        out[regime] = (circuit, matching, {"noise_record": record, "dem_sha256": hashlib.sha256(str(dem).encode()).hexdigest(),
                                           "selected_baseline_index": index})
    return out


def sample_partition(split: str, root: int, cfg: dict, inv: dict, prepared: dict,
                     progress: dict | None = None, run_started: float | None = None) -> Path:
    if split not in ALLOWED_SPLITS:
        raise RuntimeError(f"Prohibited partition: {split}")
    is_final = split == "final_development_evaluation"
    path = RUN_DIR / "data" / (f"final_root_{root:02d}.npz" if is_final else f"{split}_root_{root:02d}.npz")
    if path.exists():
        _, meta = load_sample_archive(path, split)
        if int(meta.get("root", -1)) != root:
            raise RuntimeError(f"Root mapping mismatch for {path}")
        return path
    # Final samples are withheld until all training, calibration and threshold
    # choices exist for every strategy, budget and root.
    if is_final:
        expected = int(cfg["roots"]) * len(cfg["models"]["strategies"]) * len(cfg["sampling"]["train_budgets_per_regime_root"])
        selections = list((RUN_DIR / "selections").glob("*.json"))
        if len(selections) != expected:
            raise RuntimeError(f"Final evaluation prohibited: only {len(selections)}/{expected} selections frozen.")
    all_arrays, seed_meta, per_regime_counts = {}, {}, {}
    for regime in REGIMES:
        circuit, matching, prep_meta = prepared[regime]
        stream = data_seed_stream(inv, root, regime, split)
        target_shots = int(stream["shots"])
        ds, ys, pms = [], [], []
        remaining = target_shots
        for seed in stream["seeds"]:
            if progress is not None:
                enforce_limits(cfg, progress, run_started)
            take = min(int(stream["batch_size"]), remaining)
            if take <= 0:
                break
            d, y = sample(circuit, int(seed), take)
            pm = normalize_prediction(decode_matching(matching, d), take)
            binary("detectors", d); binary("observable", y)
            if d.shape != (take, 40) or y.shape != (take,):
                raise ValueError(f"Invalid detector/observable alignment for {split}/{root}/{regime}")
            ds.append(d); ys.append(y); pms.append(pm)
            remaining -= take
            if progress is not None:
                progress = set_progress(sampling_attempted_shots=int(progress.get("sampling_attempted_shots", 0)) + take,
                                        current_root=root, current_split=split, status="sampling")
        if remaining != 0:
            raise RuntimeError(f"Seed allocation short for {split}/{root}/{regime}: {remaining} shots missing")
        all_arrays[f"detectors__{regime}"] = np.concatenate(ds)
        all_arrays[f"observable__{regime}"] = np.concatenate(ys)
        all_arrays[f"pymatching__{regime}"] = np.concatenate(pms)
        per_regime_counts[regime] = target_shots
        seed_meta[regime] = {"seeds": stream["seeds"], "shots": target_shots,
                             "dem_sha256": prep_meta["dem_sha256"],
                             "pymatching_index": prep_meta["selected_baseline_index"]}
    meta = {"root": root, "split": split, "shots": sum(per_regime_counts.values()),
            "per_regime_shots": per_regime_counts, "seed_streams": seed_meta,
            "independent_test_access": 0, "created_utc": utc_now(),
            "partition_rule": "distinct frozen Stim seeds by root, regime and split"}
    save_sample_archive(path, all_arrays, meta)
    append_event({"type": "sample_partition_committed", "root": root, "split": split,
                  "shots": meta["shots"], "sha256": meta["archive_sha256"]})
    return path


def load_root_split(root: int, split: str) -> dict:
    is_final = split == "final_development_evaluation"
    path = RUN_DIR / "data" / (f"final_root_{root:02d}.npz" if is_final else f"{split}_root_{root:02d}.npz")
    arrays, _ = load_sample_archive(path, split)
    return {r: {"detectors": arrays[f"detectors__{r}"], "observable": arrays[f"observable__{r}"],
                "pymatching": arrays[f"pymatching__{r}"]} for r in REGIMES}


def build_residual_targets(data: dict[str, dict]) -> dict[str, np.ndarray]:
    out = {}
    for regime, row in data.items():
        y = np.bitwise_xor(row["observable"], row["pymatching"]).astype(np.uint8)
        binary(f"residual target {regime}", y)
        out[regime] = y
    return out


def natural_epoch_batches(data_by_regime: dict, sizes: dict, batch_size: int,
                          rng: np.random.Generator, shuffle_rng: np.random.Generator):
    jobs = []
    for regime, data in data_by_regime.items():
        n = int(sizes[regime])
        ids = rng.permutation(n)
        for start in range(0, n, batch_size):
            jobs.append((regime, ids[start:start + batch_size].astype(np.int32).tolist()))
    shuffle_rng.shuffle(jobs)
    return jobs


def model_logits(model, data_by_regime: dict, device: torch.device, offset: float,
                 batch_size: int = 512, gpu_timer: list | None = None) -> dict[str, np.ndarray]:
    model.eval()
    result = {}
    with torch.inference_mode():
        for regime, data in data_by_regime.items():
            values = []
            for start in range(0, len(data["observable"]), batch_size):
                end = min(start + batch_size, len(data["observable"]))
                d = torch.as_tensor(data["detectors"][start:end], dtype=torch.float32, device=device)
                pm = torch.as_tensor(data["pymatching"][start:end], dtype=torch.float32, device=device)
                tic = time.perf_counter()
                logits = model(d, pm).float() + float(offset)
                if not torch.isfinite(logits).all():
                    raise FloatingPointError(f"Non-finite logits in {regime}")
                if device.type == "cuda":
                    torch.cuda.synchronize(device)
                    if gpu_timer is not None:
                        gpu_timer[0] += time.perf_counter() - tic
                values.append(logits.detach().cpu().numpy().astype(np.float64))
            result[regime] = np.concatenate(values)
    return result


def macro_brier(probs_by_regime: dict, data: dict) -> float:
    return float(np.mean([np.mean((np.asarray(probs_by_regime[r]) -
                                   np.bitwise_xor(data[r]["observable"], data[r]["pymatching"])) ** 2)
                          for r in REGIMES]))


def ece(probs: np.ndarray, labels: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = len(labels)
    result = 0.0
    for i in range(bins):
        mask = (probs >= edges[i]) & ((probs < edges[i + 1]) if i < bins - 1 else (probs <= edges[i + 1]))
        if mask.any():
            result += float(mask.sum() / total) * abs(float(probs[mask].mean()) - float(labels[mask].mean()))
    return result


def wilson_lower(successes: int, trials: int, alpha: float) -> float:
    if trials <= 0:
        return 0.0
    from statistics import NormalDist
    z = NormalDist().inv_cdf(1.0 - alpha)
    phat = successes / trials
    z2 = z * z
    denom = 1.0 + z2 / trials
    center = phat + z2 / (2.0 * trials)
    radius = z * math.sqrt((phat * (1.0 - phat) + z2 / (4.0 * trials)) / trials)
    return (center - radius) / denom


def select_min_ler_threshold(probs_by_regime: dict, threshold_data: dict, grid: list[float]) -> tuple[float, float]:
    scores = []
    for threshold in grid:
        lers = []
        for regime in REGIMES:
            residual = (np.asarray(probs_by_regime[regime]) >= threshold).astype(np.uint8)
            pred = np.bitwise_xor(threshold_data[regime]["pymatching"], residual)
            lers.append(float(np.mean(pred ^ threshold_data[regime]["observable"])))
        scores.append((float(np.mean(lers)), abs(float(threshold) - 0.5), float(threshold)))
    best = min(scores)
    return best[2], best[0]


def select_confidence_gate(probs_by_regime: dict, threshold_data: dict,
                           grid: list[float], alpha: float) -> dict:
    adjusted_alpha = float(alpha) / len(grid)
    residual_true = {r: np.bitwise_xor(threshold_data[r]["observable"],
                                       threshold_data[r]["pymatching"]).astype(np.uint8) for r in REGIMES}
    candidates = []
    for threshold in grid:
        chosen = {r: np.asarray(probs_by_regime[r]) >= threshold for r in REGIMES}
        n = sum(int(chosen[r].sum()) for r in REGIMES)
        hits = sum(int(np.sum(chosen[r] & (residual_true[r] == 1))) for r in REGIMES)
        lower = wilson_lower(hits, n, adjusted_alpha)
        if n and lower > 0.5:
            lers = []
            for regime in REGIMES:
                residual = chosen[regime].astype(np.uint8)
                pred = np.bitwise_xor(threshold_data[regime]["pymatching"], residual)
                lers.append(float(np.mean(pred ^ threshold_data[regime]["observable"])))
            candidates.append((float(np.mean(lers)), abs(float(threshold) - 0.5), -float(threshold),
                               float(threshold), n, hits, lower))
    if not candidates:
        return {"threshold": 1.01, "fallback": True, "reason": "no threshold passed Bonferroni-Wilson precision gate",
                "precision_lower_bound": None, "corrections_on_threshold_selection": 0,
                "beneficial_on_threshold_selection": 0, "selected_ler": None,
                "familywise_alpha": float(alpha), "per_threshold_alpha": adjusted_alpha}
    best = min(candidates)
    return {"threshold": best[3], "fallback": False, "reason": "Bonferroni-Wilson lower precision bound > 0.5",
            "precision_lower_bound": best[6], "corrections_on_threshold_selection": best[4],
            "beneficial_on_threshold_selection": best[5], "selected_ler": best[0],
            "familywise_alpha": float(alpha), "per_threshold_alpha": adjusted_alpha}


def job_id(root: int, strategy: str, size: int) -> str:
    return f"root{root:02d}_{strategy}_{int(size)}"


def job_seed(inv: dict, root: int, strategy: str, size: int) -> dict:
    rows = [x for x in inv["model_streams"] if x["root"] == root and
            x["strategy"] == strategy and int(x["train_size_per_regime"]) == int(size)]
    if len(rows) != 1:
        raise RuntimeError(f"Missing model RNG assignment for {root}/{strategy}/{size}")
    return rows[0]


def training_offset(strategy: str, prevalence: float, pos_weight: float) -> float:
    if strategy == "balanced_minibatch":
        p = min(max(prevalence, 1e-8), 1.0 - 1e-8)
        return math.log(p / (1.0 - p))
    if strategy == "natural_inverse_prevalence_weighted":
        return -math.log(pos_weight)
    raise ValueError(strategy)


def checkpoint_payload(job: dict, model: torch.nn.Module, optimizer, scheduler,
                       epoch: int, next_batch: int, batches, steps: int, best_state,
                       best_nll: float, best_epoch: int, patience: int, history: list,
                       np_rng, shuffle_rng, offset: float, gpu_seconds: float,
                       progress: dict) -> dict:
    return {"job_id": job["job_id"], "config_sha256": sha256(CONFIG_PATH),
            "model_state": {k: v.detach().cpu().clone() for k, v in model.state_dict().items()},
            "optimizer_state": optimizer.state_dict(), "scheduler_state": scheduler.state_dict(),
            "epoch": epoch, "next_batch": next_batch, "epoch_batches": batches,
            "steps": steps, "best_state": best_state, "best_nll": best_nll,
            "best_epoch": best_epoch, "patience": patience, "history": history,
            "numpy_rng_state": np_rng.bit_generator.state,
            "shuffle_rng_state": shuffle_rng.bit_generator.state,
            "torch_rng_state": torch.get_rng_state().cpu(),
            "cuda_rng_state": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None,
            "python_rng_state": random.getstate(), "decision_logit_offset": offset,
            "gpu_seconds": gpu_seconds, "progress_snapshot": progress}


def selected_training_gpu_seconds() -> float:
    total = 0.0
    for path in (RUN_DIR / "selections").glob("*.json"):
        try:
            total += float(read_json(path, {}).get("gpu_seconds_train_and_select", 0.0))
        except Exception:
            continue
    return total


def saved_inference_gpu_seconds() -> float:
    total = 0.0
    for path in (RUN_DIR / "predictions").glob("root*.json"):
        try:
            total += float(read_json(path, {}).get("gpu_inference_seconds", 0.0))
        except Exception:
            continue
    return total


def fit_one(job: dict, root_data: dict, coords: dict, cfg: dict, inv: dict,
            device: torch.device, started: float, progress: dict) -> dict:
    jid, strategy, size, root = job["job_id"], job["strategy"], job["train_size_per_regime"], job["root"]
    selection_path = RUN_DIR / "selections" / f"{jid}.json"
    weights_path = RUN_DIR / "checkpoints" / f"{jid}.weights.pt"
    state_path = RUN_DIR / "checkpoints" / f"{jid}.state.pt"
    if selection_path.exists() and weights_path.exists():
        selection = read_json(selection_path)
        if sha256(weights_path) != selection.get("weights_sha256"):
            raise RuntimeError(f"Frozen model hash mismatch: {jid}")
        if selection.get("final_development_evaluation_accessed") is not False:
            raise RuntimeError(f"Selection record lacks a pre-evaluation freeze for {jid}")
        append_event({"type": "job_selection_reused", "job_id": jid})
        return selection
    if selection_path.exists() and not weights_path.exists():
        raise RuntimeError(f"Frozen selection exists but its selected weights are missing: {jid}")

    train = {r: {k: v[:size] for k, v in root_data["train"][r].items()} for r in REGIMES}
    targets = build_residual_targets(train)
    total_pos = sum(int(targets[r].sum()) for r in REGIMES)
    total_count = sum(len(targets[r]) for r in REGIMES)
    if total_pos == 0 or total_pos == total_count:
        raise RuntimeError(f"Training target lacks a class for {jid}: {total_pos}/{total_count}")
    prevalence = total_pos / total_count
    pos_weight = (total_count - total_pos) / total_pos
    seeds = job_seed(inv, root, strategy, size)
    torch.manual_seed(int(seeds["torch_seed"]))
    torch.cuda.manual_seed_all(int(seeds["torch_seed"]))
    random.seed(int(seeds["torch_seed"]))
    np_rng = np.random.default_rng(int(seeds["sampling_seed"]))
    shuffle_rng = np.random.default_rng(int(seeds["shuffle_seed"]))
    model = ResidualPositionCNN(coords, channels=int(cfg["models"]["training"]["channels"]),
                                head_width=int(cfg["models"]["training"]["head_width"]),
                                dropout=float(cfg["models"]["training"]["dropout"])).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(cfg["models"]["training"]["learning_rate"]),
                                  weight_decay=float(cfg["models"]["training"]["weight_decay"]))
    scheduler_cfg = cfg["models"]["training"]["scheduler"]
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=int(scheduler_cfg["step_size_epochs"]),
                                                gamma=float(scheduler_cfg["gamma"]))
    offset = training_offset(strategy, prevalence, pos_weight)
    epoch, next_batch, epoch_batches, steps = 0, 0, None, 0
    best_state, best_nll, best_epoch, patience_count, history, gpu_seconds = None, float("inf"), 0, 0, [], 0.0
    if state_path.exists():
        state = verified_torch_load(state_path)
        if state.get("job_id") != jid or state.get("config_sha256") != sha256(CONFIG_PATH):
            raise RuntimeError(f"Checkpoint identity/config mismatch for {jid}")
        model.load_state_dict(state["model_state"]); optimizer.load_state_dict(state["optimizer_state"])
        scheduler.load_state_dict(state["scheduler_state"])
        epoch, next_batch, epoch_batches, steps = state["epoch"], state["next_batch"], state["epoch_batches"], state["steps"]
        best_state, best_nll, best_epoch = state["best_state"], state["best_nll"], state["best_epoch"]
        patience_count, history, gpu_seconds = state["patience"], state["history"], state["gpu_seconds"]
        np_rng.bit_generator.state = state["numpy_rng_state"]
        shuffle_rng.bit_generator.state = state["shuffle_rng_state"]
        torch.set_rng_state(state["torch_rng_state"])
        if state.get("cuda_rng_state") is not None: torch.cuda.set_rng_state_all(state["cuda_rng_state"])
        random.setstate(state["python_rng_state"])
        if abs(float(state["decision_logit_offset"]) - offset) > 1e-12:
            raise RuntimeError(f"Training prior correction changed on resume for {jid}")
        append_event({"type": "checkpoint_resumed", "job_id": jid, "epoch": epoch, "steps": steps})

    train_cfg = cfg["models"]["training"]
    max_epochs, patience_limit, batch_size = int(train_cfg["max_epochs"]), int(train_cfg["patience"]), int(train_cfg["batch_size"])
    while epoch < max_epochs:
        if epoch_batches is None:
            sizes = {r: size for r in REGIMES}
            if strategy == "balanced_minibatch":
                epoch_batches = balanced_epoch_batches(train, sizes, batch_size, np_rng,
                                                       residual=True, shuffle_rng=shuffle_rng)
            else:
                epoch_batches = natural_epoch_batches(train, sizes, batch_size, np_rng, shuffle_rng)
            next_batch = 0
        model.train()
        while next_batch < len(epoch_batches):
            if next_batch % int(train_cfg["checkpoint_every_batches"]) == 0:
                progress = run_progress()
                enforce_limits(cfg, progress, started)
            regime, ids = epoch_batches[next_batch]
            ix = np.asarray(ids, dtype=np.int32)
            d = torch.as_tensor(train[regime]["detectors"][ix], dtype=torch.float32, device=device)
            pm = torch.as_tensor(train[regime]["pymatching"][ix], dtype=torch.float32, device=device)
            y = torch.as_tensor(targets[regime][ix], dtype=torch.float32, device=device)
            optimizer.zero_grad(set_to_none=True)
            tic = time.perf_counter()
            logits = model(d, pm).float()
            if strategy == "natural_inverse_prevalence_weighted":
                loss = F.binary_cross_entropy_with_logits(logits, y,
                    pos_weight=torch.tensor(pos_weight, dtype=torch.float32, device=device))
            else:
                loss = F.binary_cross_entropy_with_logits(logits, y)
            if not torch.isfinite(loss):
                raise FloatingPointError(f"Non-finite training loss for {jid}")
            loss.backward()
            if any(p.grad is not None and not torch.isfinite(p.grad).all() for p in model.parameters()):
                raise FloatingPointError(f"Non-finite gradient for {jid}")
            optimizer.step()
            if device.type == "cuda":
                torch.cuda.synchronize(device)
                gpu_seconds += time.perf_counter() - tic
            steps += 1; next_batch += 1
            if next_batch % int(train_cfg["checkpoint_every_batches"]) == 0 or next_batch == len(epoch_batches):
                payload = checkpoint_payload(job, model, optimizer, scheduler, epoch, next_batch,
                    epoch_batches, steps, best_state, best_nll, best_epoch, patience_count, history,
                    np_rng, shuffle_rng, offset, gpu_seconds, progress)
                atomic_torch_save(payload, state_path)
                set_progress(current_job=jid, current_root=root, current_phase="training",
                    gpu_training_seconds=selected_training_gpu_seconds() + gpu_seconds,
                    current_job_gpu_seconds=gpu_seconds)
                if (RUN_DIR / "STOP").exists():
                    raise PauseRun("Safe stop requested at a saved optimizer-batch boundary")
        val_timer = [0.0]
        monitor_logits = model_logits(model, root_data["monitor"], device, offset,
                                      int(train_cfg["evaluation_batch_size"]), val_timer)
        gpu_seconds += val_timer[0]
        nll = macro_nll(monitor_logits, root_data["monitor"], residual=True)
        if not math.isfinite(nll):
            raise FloatingPointError(f"Non-finite monitor NLL for {jid}")
        improved = nll < best_nll - 1e-9
        if improved:
            best_nll, best_epoch, patience_count = nll, epoch + 1, 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            patience_count += 1
        history.append({"epoch": epoch + 1, "monitor_nll": nll, "selected": improved,
                        "learning_rate": float(optimizer.param_groups[0]["lr"])})
        scheduler.step(); epoch += 1; next_batch = 0; epoch_batches = None
        state = checkpoint_payload(job, model, optimizer, scheduler, epoch, next_batch, epoch_batches,
            steps, best_state, best_nll, best_epoch, patience_count, history, np_rng, shuffle_rng,
            offset, gpu_seconds, run_progress())
        atomic_torch_save(state, state_path)
        append_event({"type": "epoch_complete", "job_id": jid, "epoch": epoch, "monitor_nll": nll,
                      "best_epoch": best_epoch, "selected": improved, "gpu_seconds": gpu_seconds})
        set_progress(current_job=jid, current_root=root, current_phase="monitor",
                     gpu_training_seconds=selected_training_gpu_seconds() + gpu_seconds,
                     current_job_gpu_seconds=gpu_seconds)
        if patience_count >= patience_limit:
            break
    if best_state is None:
        raise RuntimeError(f"No monitor-selected checkpoint for {jid}")
    model.load_state_dict(best_state)
    model_path_tmp = weights_path.with_suffix(weights_path.suffix + ".tmp")
    with model_path_tmp.open("wb") as f:
        torch.save({k: v.detach().cpu().clone() for k, v in best_state.items()}, f)
        f.flush(); os.fsync(f.fileno())
    os.replace(model_path_tmp, weights_path)
    weights_hash = sha256(weights_path)

    calib_timer = [0.0]
    cal_logits = model_logits(model, root_data["calibration"], device, offset,
                              int(train_cfg["evaluation_batch_size"]), calib_timer)
    gpu_seconds += calib_timer[0]
    temperature = choose_temperature(cal_logits, root_data["calibration"], residual=True,
                                     grid=cfg["models"]["calibration_temperature_grid"])
    threshold_timer = [0.0]
    th_logits = model_logits(model, root_data["threshold_selection"], device, offset,
                             int(train_cfg["evaluation_batch_size"]), threshold_timer)
    gpu_seconds += threshold_timer[0]
    probs = {r: 1.0 / (1.0 + np.exp(-np.clip(th_logits[r] / temperature, -60, 60))) for r in REGIMES}
    threshold, selected_ler = select_min_ler_threshold(probs, root_data["threshold_selection"],
                                                       cfg["models"]["threshold_grid"])
    gate = select_confidence_gate(probs, root_data["threshold_selection"],
                                  cfg["models"]["threshold_grid"],
                                  float(cfg["models"]["confidence_gate"]["familywise_alpha"]))
    calibration_y = {r: np.bitwise_xor(root_data["calibration"][r]["observable"],
                                       root_data["calibration"][r]["pymatching"]) for r in REGIMES}
    cal_probs = {r: 1.0 / (1.0 + np.exp(-np.clip(cal_logits[r] / temperature, -60, 60))) for r in REGIMES}
    selection = {"job_id": jid, "root": root, "strategy": strategy, "train_size_per_regime": size,
        "model": "ResidualPositionCNN", "target": "observable_xor_frozen_pymatching_prediction",
        "inference": "pymatching_xor_predicted_residual", "prevalence": prevalence,
        "positive_examples": total_pos, "training_examples": total_count, "pos_weight": pos_weight,
        "logit_prior_correction": offset, "best_epoch": best_epoch, "best_monitor_nll": best_nll,
        "monitor_history": history, "temperature": temperature,
        "threshold_min_ler": threshold, "threshold_selection_ler": selected_ler,
        "confidence_gate": gate, "calibration_brier": macro_brier(cal_probs, root_data["calibration"]),
        "calibration_ece_10bin": float(np.mean([ece(cal_probs[r], calibration_y[r]) for r in REGIMES])),
        "weights_sha256": weights_hash, "selection_data": {
            "checkpoint": "monitor only", "temperature": "calibration only",
            "threshold_min_ler": "threshold_selection only", "confidence_gate": "threshold_selection only"},
        "final_development_evaluation_accessed": False, "gpu_seconds_train_and_select": gpu_seconds,
        "parameter_count": sum(p.numel() for p in model.parameters()), "created_utc": utc_now()}
    atomic_json(selection, selection_path)
    # Remove large optimizer checkpoint after final state and selection are
    # durable; the selected model weights remain sufficient for final scoring.
    # Keep optimizer state until the complete run ends for forensic/resume value.
    append_event({"type": "selection_frozen", "job_id": jid, "threshold": threshold,
                  "gate_threshold": gate["threshold"], "final_eval_accessed": False})
    set_progress(current_job=jid, current_root=root, current_phase="selection_frozen",
                 gpu_training_seconds=selected_training_gpu_seconds(), current_job_gpu_seconds=0.0)
    return selection


def confusion_metrics(pred: np.ndarray, y: np.ndarray, pm: np.ndarray) -> dict:
    pred, y, pm = (np.asarray(x, dtype=np.uint8) for x in (pred, y, pm))
    binary("candidate prediction", pred); binary("observable", y); binary("PyMatching", pm)
    wrong, pm_wrong = pred ^ y, pm ^ y
    target = pm_wrong
    corrections = pred ^ pm
    benefit = int(np.sum((corrections == 1) & (target == 1)))
    harm = int(np.sum((corrections == 1) & (target == 0)))
    total_corr = benefit + harm
    return {"shots": int(len(y)), "errors": int(wrong.sum()), "ler": float(wrong.mean()),
            "pymatching_errors": int(pm_wrong.sum()), "pymatching_ler": float(pm_wrong.mean()),
            "paired_difference": float(wrong.mean() - pm_wrong.mean()),
            "candidate_only": int(np.sum((wrong == 1) & (pm_wrong == 0)),),
            "pymatching_only": int(np.sum((wrong == 0) & (pm_wrong == 1)),),
            "prediction_disagreements": int(np.sum(pred != pm)),
            "residual_positive_examples": int(target.sum()), "residual_corrections": total_corr,
            "beneficial_corrections": benefit, "harmful_corrections": harm,
            "correction_precision": benefit / total_corr if total_corr else None,
            "correction_recall": benefit / int(target.sum()) if int(target.sum()) else None}


def evaluate_job(job: dict, root_data: dict, cfg: dict, device: torch.device,
                 progress: dict, started: float) -> tuple[list[dict], dict]:
    jid = job["job_id"]
    selection = read_json(RUN_DIR / "selections" / f"{jid}.json")
    weights_path = RUN_DIR / "checkpoints" / f"{jid}.weights.pt"
    if not selection or sha256(weights_path) != selection.get("weights_sha256"):
        raise RuntimeError(f"Selection/model hash mismatch before final evaluation: {jid}")
    out_path = RUN_DIR / "predictions" / f"{jid}.npz"
    existing = read_json(out_path.with_suffix(".json"), {})
    if out_path.is_file() and existing.get("archive_sha256") == sha256(out_path) and \
            existing.get("selection_sha256") == sha256(RUN_DIR / "selections" / f"{jid}.json"):
        with np.load(out_path, allow_pickle=False) as z:
            saved = {key: z[key] for key in z.files}
        cached_rows = []
        for regime in REGIMES:
            y = saved[f"observable__{regime}"]
            pm = saved[f"pymatching__{regime}"]
            for key in saved:
                suffix = "__" + regime
                if key.startswith("prediction_") and key.endswith(suffix):
                    policy = key[len("prediction_"):-len(suffix)]
                    row = confusion_metrics(saved[key], y, pm)
                    row.update({"root": int(job["root"]), "regime": regime,
                        "strategy": job["strategy"], "train_size_per_regime": int(job["train_size_per_regime"]),
                        "policy": policy, "threshold": float(selection["threshold_min_ler"] if policy == "min_ler"
                            else selection["confidence_gate"]["threshold"])})
                    cached_rows.append(row)
        return cached_rows, {"gpu_inference_seconds": float(existing.get("gpu_inference_seconds", 0.0)),
                             "prediction_path": str(out_path), "prediction_sha256": sha256(out_path), "reused": True}
    weights = torch.load(weights_path, map_location="cpu", weights_only=True)
    model = ResidualPositionCNN(root_data["coords"], channels=int(cfg["models"]["training"]["channels"]),
        head_width=int(cfg["models"]["training"]["head_width"]), dropout=float(cfg["models"]["training"]["dropout"])).to(device)
    model.load_state_dict(weights); model.eval()
    offset = float(selection["logit_prior_correction"])
    timer = [0.0]
    # Only now, after every model's thresholds are frozen, is this object
    # supplied by the caller from a final-development archive.
    logits = model_logits(model, root_data["final_development_evaluation"], device, offset,
                          int(cfg["models"]["training"]["evaluation_batch_size"]), timer)
    probs = {r: 1.0 / (1.0 + np.exp(-np.clip(logits[r] / float(selection["temperature"]), -60, 60))) for r in REGIMES}
    rows, save = [], {"job_id": jid, "root": job["root"], "strategy": job["strategy"],
                      "train_size_per_regime": job["train_size_per_regime"]}
    policy_thresholds = {"min_ler": float(selection["threshold_min_ler"])}
    if job["strategy"] == "balanced_minibatch":
        policy_thresholds["confidence_gate"] = float(selection["confidence_gate"]["threshold"])
    for regime in REGIMES:
        data = root_data["final_development_evaluation"][regime]
        target = np.bitwise_xor(data["observable"], data["pymatching"]).astype(np.uint8)
        save[f"observable__{regime}"] = data["observable"]
        save[f"pymatching__{regime}"] = data["pymatching"]
        save[f"residual_target__{regime}"] = target
        save[f"probability__{regime}"] = probs[regime].astype(np.float32)
        for policy, threshold in policy_thresholds.items():
            residual_pred = (probs[regime] >= threshold).astype(np.uint8)
            pred = np.bitwise_xor(data["pymatching"], residual_pred)
            metrics = confusion_metrics(pred, data["observable"], data["pymatching"])
            metrics.update({"root": job["root"], "regime": regime, "strategy": job["strategy"],
                            "train_size_per_regime": job["train_size_per_regime"],
                            "policy": policy, "threshold": threshold})
            rows.append(metrics)
            save[f"prediction_{policy}__{regime}"] = pred
            save[f"residual_prediction_{policy}__{regime}"] = residual_pred
    save_npz_atomic(out_path, save)
    manifest_path = out_path.with_suffix(".json")
    atomic_json({"job_id": jid, "root": job["root"], "strategy": job["strategy"],
        "train_size_per_regime": job["train_size_per_regime"], "archive_sha256": sha256(out_path),
        "shots": sum(len(root_data["final_development_evaluation"][r]["observable"]) for r in REGIMES),
        "gpu_inference_seconds": timer[0],
        "selection_sha256": sha256(RUN_DIR / "selections" / f"{jid}.json"),
        "independent_test_access": 0, "final_development_evaluation_accessed": True}, manifest_path)
    return rows, {"gpu_inference_seconds": timer[0], "prediction_path": str(out_path), "prediction_sha256": sha256(out_path)}


def mean_ci(values: list[float]) -> dict:
    arr = np.asarray(values, dtype=np.float64)
    mean = float(arr.mean()) if len(arr) else 0.0
    if len(arr) > 1:
        half = T_CRIT_DF4 * float(arr.std(ddof=1)) / math.sqrt(len(arr)) if len(arr) == 5 else float("nan")
        lo, hi = mean - half, mean + half
    else:
        lo = hi = mean
    return {"mean": mean, "ci95_low": lo, "ci95_high": hi, "n_roots": int(len(arr)),
            "sd_root": float(arr.std(ddof=1)) if len(arr) > 1 else 0.0}


def root_bootstrap_ci(values: list[float], indices: np.ndarray, confidence: float) -> dict:
    arr = np.asarray(values, dtype=np.float64)
    means = arr[indices].mean(axis=1)
    alpha = 1.0 - float(confidence)
    return {"low": float(np.quantile(means, alpha / 2)),
            "high": float(np.quantile(means, 1.0 - alpha / 2)),
            "confidence": float(confidence), "resamples": int(len(indices))}


def exact_root_signflip_p(values: list[float]) -> float:
    x = np.asarray(values, dtype=np.float64)
    observed = abs(float(x.mean()))
    if len(x) == 0:
        return 1.0
    count = 0
    for mask in range(1 << len(x)):
        signs = np.array([1.0 if (mask >> i) & 1 else -1.0 for i in range(len(x))])
        if abs(float((x * signs).mean())) >= observed - 1e-15:
            count += 1
    return count / (1 << len(x))


def holm_adjust(pvals: list[float]) -> list[float]:
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj, running = [1.0] * m, 0.0
    for rank, idx in enumerate(order):
        value = min(1.0, (m - rank) * pvals[idx])
        running = max(running, value)
        adj[idx] = running
    return adj


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0].keys()) if rows else ["status"]
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)


def summarize(rows: list[dict], training_rows: list[dict], cfg: dict, progress: dict) -> dict:
    keys = sorted({(r["strategy"], int(r["train_size_per_regime"]), r["policy"]) for r in rows})
    boot_n = int(cfg["analysis"]["bootstrap_resamples"])
    boot_seed = int(cfg["analysis"]["bootstrap_seed"])
    boot_rng = np.random.default_rng(boot_seed)
    boot_indices = boot_rng.integers(0, int(cfg["roots"]), size=(boot_n, int(cfg["roots"])), dtype=np.int16)
    summary = []
    for strategy, size, policy in keys:
        cell = [r for r in rows if r["strategy"] == strategy and int(r["train_size_per_regime"]) == size and r["policy"] == policy]
        root_ler, root_pm, root_delta = [], [], []
        for root in range(int(cfg["roots"])):
            rr = [x for x in cell if int(x["root"]) == root]
            if len(rr) != len(REGIMES):
                raise RuntimeError(f"Missing regime row(s) for root {root}/{strategy}/{size}/{policy}")
            root_ler.append(float(np.mean([x["ler"] for x in rr])))
            root_pm.append(float(np.mean([x["pymatching_ler"] for x in rr])))
            root_delta.append(float(np.mean([x["paired_difference"] for x in rr])))
        summary.append({"strategy": strategy, "train_size_per_regime": size, "policy": policy,
            "shots": sum(int(x["shots"]) for x in cell), "pooled_errors": sum(int(x["errors"]) for x in cell),
            "pooled_ler": sum(int(x["errors"]) for x in cell) / sum(int(x["shots"]) for x in cell),
            "root_equal_regime_ler": mean_ci(root_ler), "root_equal_regime_pymatching_ler": mean_ci(root_pm),
            "root_paired_delta": mean_ci(root_delta), "roots_won_vs_pm": sum(x < 0 for x in root_delta),
            "roots_lost_vs_pm": sum(x > 0 for x in root_delta), "roots_tied_vs_pm": sum(x == 0 for x in root_delta),
            "candidate_only": sum(int(x["candidate_only"]) for x in cell),
            "pymatching_only": sum(int(x["pymatching_only"]) for x in cell),
            "beneficial_corrections": sum(int(x["beneficial_corrections"]) for x in cell),
            "harmful_corrections": sum(int(x["harmful_corrections"]) for x in cell),
            "correction_precision": (sum(int(x["beneficial_corrections"]) for x in cell) /
                max(1, sum(int(x["beneficial_corrections"]) + int(x["harmful_corrections"]) for x in cell))),
            "root_deltas": root_delta,
            "root_paired_bootstrap_ci95": root_bootstrap_ci(root_delta, boot_indices,
                float(cfg["analysis"]["bootstrap_confidence"]))})
    ps = [exact_root_signflip_p(s["root_deltas"]) for s in summary]
    adj = holm_adjust(ps)
    for row, raw, adjusted in zip(summary, ps, adj):
        row["exploratory_root_signflip_p"] = raw
        row["holm_p_over_all_candidate_policies"] = adjusted
    by_regime = []
    for strategy, size, policy in keys:
        for regime in REGIMES:
            cell = [r for r in rows if r["strategy"] == strategy and int(r["train_size_per_regime"]) == size and r["policy"] == policy and r["regime"] == regime]
            regime_root_delta = []
            for root in range(int(cfg["roots"])):
                one = [x for x in cell if int(x["root"]) == root]
                if len(one) != 1:
                    raise RuntimeError(f"Missing per-regime root row: {root}/{strategy}/{size}/{policy}/{regime}")
                regime_root_delta.append(float(one[0]["paired_difference"]))
            by_regime.append({"strategy": strategy, "train_size_per_regime": size, "policy": policy,
                "regime": regime, "shots": sum(int(x["shots"]) for x in cell),
                "errors": sum(int(x["errors"]) for x in cell),
                "ler": sum(int(x["errors"]) for x in cell) / max(1, sum(int(x["shots"]) for x in cell)),
                "pymatching_errors": sum(int(x["pymatching_errors"]) for x in cell),
                "pymatching_ler": sum(int(x["pymatching_errors"]) for x in cell) / max(1, sum(int(x["shots"]) for x in cell)),
                "paired_difference": sum(int(x["errors"]) - int(x["pymatching_errors"]) for x in cell) / max(1, sum(int(x["shots"]) for x in cell)),
                "candidate_only": sum(int(x["candidate_only"]) for x in cell),
                "pymatching_only": sum(int(x["pymatching_only"]) for x in cell),
                "beneficial_corrections": sum(int(x["beneficial_corrections"]) for x in cell),
                "harmful_corrections": sum(int(x["harmful_corrections"]) for x in cell),
                "root_paired_delta": mean_ci(regime_root_delta), "root_deltas": regime_root_delta})
    return {"status": "completed_development_only", "unique_production_shots": progress.get("committed_unique_shots", 0),
            "unique_diagnostic_shots": int(cfg["sampling"]["diagnostic_shots_per_regime"]) * len(REGIMES),
            "unique_total_shots_including_preflight": int(progress.get("committed_unique_shots", 0)) +
                int(cfg["sampling"]["diagnostic_shots_per_regime"]) * len(REGIMES),
            "independent_test_access": 0, "root_count": int(cfg["roots"]),
            "summary": summary, "per_regime": by_regime,
            "training_jobs": training_rows,
            "bootstrap": {"resamples": boot_n, "confidence": cfg["analysis"]["bootstrap_confidence"],
                          "seed": boot_seed, "sampling_unit": "independent root clusters; each resample retains all three regimes"},
            "statistical_note": "Root-t and root-bootstrap intervals are descriptive with five roots. Exact two-sided sign-flip enumerates all 2^5 assignments; the preallocated sign-flip RNG seed is not consumed because enumeration is exhaustive. Holm adjustment covers all nine frozen candidate/policy/budget comparisons. No result is confirmatory."}


def acquire_lock() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    path = RUN_DIR / "sprint.lock"
    if path.exists():
        info = read_json(path, {})
        pid = int(info.get("pid", -1))
        if pid > 0 and psutil.pid_exists(pid):
            raise RuntimeError(f"Sprint appears active under PID {pid}; refusing a second process.")
        path.unlink()
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps({"pid": os.getpid(), "created_utc": utc_now(), "cwd": os.getcwd()}))
        f.flush(); os.fsync(f.fileno())


def release_lock() -> None:
    path = RUN_DIR / "sprint.lock"
    if path.exists():
        info = read_json(path, {})
        if int(info.get("pid", -1)) == os.getpid():
            path.unlink()


def make_jobs(cfg: dict) -> list[dict]:
    return [{"job_id": job_id(root, strategy, int(size)), "root": root,
             "strategy": strategy, "train_size_per_regime": int(size)}
            for root in range(int(cfg["roots"]))
            for strategy in cfg["models"]["strategies"]
            for size in cfg["sampling"]["train_budgets_per_regime_root"]]


def prepare_preflight() -> dict:
    freeze, cfg, inv = verify_freeze()
    if not torch.cuda.is_available():
        raise RuntimeError("Preflight requires CUDA; PyTorch reports unavailable.")
    if (AUTO / "run" / "controller.lock").exists():
        raise RuntimeError("Historical controller lock present.")
    progress_old = read_json(AUTO / "run" / "progress.json", {})
    if progress_old.get("status") != "completed" or int(progress_old.get("independent_test_access", -1)) != 0:
        raise RuntimeError("Historical run status/test-access guard failed.")
    prepared = prepared_regimes(cfg)
    preflight_dir = HERE / "preflight"
    preflight_dir.mkdir(exist_ok=True)
    archive = preflight_dir / "diagnostic_samples.npz"
    diagnostic_meta_path = archive.with_suffix(".json")
    diagnostic = {}
    if archive.exists():
        # A prior preflight attempt may have committed the NPZ and then failed
        # while committing its JSON sidecar. Recover only if the sidecar's
        # recorded digest and seed allocation match the immutable saved data.
        if not diagnostic_meta_path.exists():
            tmp_meta = diagnostic_meta_path.with_suffix(diagnostic_meta_path.suffix + ".tmp")
            if not tmp_meta.is_file():
                raise RuntimeError("Diagnostic archive exists without recoverable metadata; refusing to resample its seeds.")
            recovered_meta = read_json(tmp_meta, {})
            if (recovered_meta.get("archive_sha256") != sha256(archive) or
                    recovered_meta.get("split") != "diagnostic" or
                    int(recovered_meta.get("shots", -1)) != int(cfg["sampling"]["diagnostic_shots_per_regime"]) * len(REGIMES) or
                    recovered_meta.get("seed_ids") != inv["diagnostic_seeds"] or
                    int(recovered_meta.get("independent_test_access", -1)) != 0):
                raise RuntimeError("Incomplete diagnostic metadata does not authenticate the saved archive; refusing to resample.")
            os.replace(tmp_meta, diagnostic_meta_path)
        arrays, recovered_meta = load_sample_archive(archive, expected_split="diagnostic")
        if (int(recovered_meta.get("root", -2)) != -1 or
                recovered_meta.get("seed_ids") != inv["diagnostic_seeds"] or
                int(recovered_meta.get("shots", -1)) != int(cfg["sampling"]["diagnostic_shots_per_regime"]) * len(REGIMES)):
            raise RuntimeError("Saved diagnostic metadata does not match the frozen preflight allocation.")
        expected_keys = {f"{kind}__{regime}" for regime in REGIMES
                         for kind in ("detectors", "observable", "pymatching", "residual")}
        if set(arrays) != expected_keys:
            raise RuntimeError("Saved diagnostic archive schema differs from the frozen preflight schema.")
        for i, regime in enumerate(REGIMES):
            circuit, matching, meta = prepared[regime]
            d = arrays[f"detectors__{regime}"]
            y = arrays[f"observable__{regime}"]
            pm = arrays[f"pymatching__{regime}"]
            target = arrays[f"residual__{regime}"]
            n = int(cfg["sampling"]["diagnostic_shots_per_regime"])
            if d.shape != (n, 40) or y.shape != (n,) or pm.shape != (n,) or target.shape != (n,):
                raise RuntimeError(f"Saved diagnostic dimensions are invalid for {regime}.")
            for name, value in (("detectors", d), ("observable", y), ("PyMatching", pm), ("residual", target)):
                binary(f"saved diagnostic {regime} {name}", value)
            if not np.array_equal(target, np.bitwise_xor(y, pm)):
                raise RuntimeError(f"Saved diagnostic residual labels do not match outcomes for {regime}.")
            decoded = normalize_prediction(decode_matching(matching, d), n)
            if not np.array_equal(decoded, pm):
                raise RuntimeError(f"Saved diagnostic PyMatching predictions do not reproduce for {regime}.")
            diagnostic[regime] = {"seed": int(inv["diagnostic_seeds"][i]), "shots": n,
                "detectors": d.shape[1], "observable_shape": y.shape,
                "pymatching_errors": int(np.sum(pm ^ y)), "residual_positives": int(target.sum()),
                "dem_sha256": meta["dem_sha256"], "reused_saved_samples": True}
    else:
        arrays = {}
        for i, regime in enumerate(REGIMES):
            circuit, matching, meta = prepared[regime]
            seed = int(inv["diagnostic_seeds"][i])
            d, y = sample(circuit, seed, int(cfg["sampling"]["diagnostic_shots_per_regime"]))
            pm = normalize_prediction(decode_matching(matching, d), len(d))
            binary("diagnostic detector", d); binary("diagnostic observable", y)
            target = np.bitwise_xor(y, pm).astype(np.uint8)
            if d.shape != (len(y), 40) or target.shape != y.shape:
                raise RuntimeError("Diagnostic label/feature alignment failed.")
            arrays[f"detectors__{regime}"] = d
            arrays[f"observable__{regime}"] = y
            arrays[f"pymatching__{regime}"] = pm
            arrays[f"residual__{regime}"] = target
            diagnostic[regime] = {"seed": seed, "shots": len(y), "detectors": d.shape[1],
                "observable_shape": y.shape, "pymatching_errors": int(np.sum(pm ^ y)),
                "residual_positives": int(target.sum()), "dem_sha256": meta["dem_sha256"],
                "reused_saved_samples": False}
        save_sample_archive(archive, arrays, {"split": "diagnostic", "root": -1,
            "shots": sum(len(arrays[f"observable__{r}"]) for r in REGIMES),
            "independent_test_access": 0, "seed_ids": inv["diagnostic_seeds"]})

    # Run the same model/data validation whether this is a first preflight or a
    # recovery from an already committed diagnostic archive.
    coords = prepared["balanced"][0].get_detector_coordinates()
    diagnostic_model = ResidualPositionCNN(coords,
        channels=int(cfg["models"]["training"]["channels"]),
        head_width=int(cfg["models"]["training"]["head_width"]),
        dropout=float(cfg["models"]["training"]["dropout"])).cuda()
    diagnostic_model.eval()
    with torch.inference_mode():
        for regime in REGIMES:
            d = torch.as_tensor(arrays[f"detectors__{regime}"], dtype=torch.float32, device="cuda")
            pm = torch.as_tensor(arrays[f"pymatching__{regime}"], dtype=torch.float32, device="cuda")
            logits = diagnostic_model(d, pm)
            if logits.shape != (len(d),) or not torch.isfinite(logits).all():
                raise RuntimeError(f"Diagnostic model output shape/finiteness check failed for {regime}.")

    # Verify an actual optimizer-resume sequence exactly on diagnostic data.
    rng_seed = int(inv["preflight_model_seed"])
    torch.manual_seed(rng_seed); torch.cuda.manual_seed_all(rng_seed)
    torch.use_deterministic_algorithms(True); torch.backends.cudnn.deterministic = True
    random.seed(rng_seed); np.random.seed(rng_seed)
    d = torch.as_tensor(arrays["detectors__balanced"][:32], dtype=torch.float32, device="cuda")
    pm = torch.as_tensor(arrays["pymatching__balanced"][:32], dtype=torch.float32, device="cuda")
    y = torch.as_tensor(arrays["residual__balanced"][:32], dtype=torch.float32, device="cuda")
    m1 = ResidualPositionCNN(prepared["balanced"][0].get_detector_coordinates(), 4, 16, 0.05).cuda()
    o1 = torch.optim.AdamW(m1.parameters(), lr=0.003)
    s1 = torch.optim.lr_scheduler.StepLR(o1, step_size=1, gamma=0.5)
    def step(m, opt):
        opt.zero_grad(set_to_none=True)
        loss = F.binary_cross_entropy_with_logits(m(d, pm), y)
        loss.backward(); opt.step()
        return float(loss.detach().cpu())
    step(m1, o1); s1.step()
    checkpoint = {"model": {k: v.detach().cpu().clone() for k, v in m1.state_dict().items()},
                  "optimizer": o1.state_dict(), "scheduler": s1.state_dict(),
                  "torch_rng": torch.get_rng_state().cpu(), "cuda_rng": torch.cuda.get_rng_state_all(),
                  "python_rng": random.getstate(), "numpy_rng": np.random.get_state()}
    probe = preflight_dir / "resume_probe.pt"
    atomic_torch_save(checkpoint, probe)
    step(m1, o1); s1.step()
    expected = {k: v.detach().cpu().clone() for k, v in m1.state_dict().items()}
    m2 = ResidualPositionCNN(prepared["balanced"][0].get_detector_coordinates(), 4, 16, 0.05).cuda()
    o2 = torch.optim.AdamW(m2.parameters(), lr=0.003)
    s2 = torch.optim.lr_scheduler.StepLR(o2, step_size=1, gamma=0.5)
    saved = verified_torch_load(probe)
    m2.load_state_dict(saved["model"]); o2.load_state_dict(saved["optimizer"]); s2.load_state_dict(saved["scheduler"])
    torch.set_rng_state(saved["torch_rng"]); torch.cuda.set_rng_state_all(saved["cuda_rng"])
    random.setstate(saved["python_rng"]); np.random.set_state(saved["numpy_rng"])
    step(m2, o2); s2.step()
    equal = (all(torch.equal(expected[k], m2.state_dict()[k].detach().cpu()) for k in expected)
             and s1.state_dict() == s2.state_dict()
             and o1.param_groups[0]["lr"] == o2.param_groups[0]["lr"])
    if not equal:
        raise RuntimeError("Checkpoint resume equivalence failed on deterministic diagnostic step.")
    report = {"status": "PASS", "completed_utc": utc_now(), "freeze_sha256": sha256(FREEZE_PATH),
        "cuda_device": torch.cuda.get_device_name(0), "diagnostic_shots": sum(x["shots"] for x in diagnostic.values()),
        "diagnostics": diagnostic, "partition_seed_disjointness": inv["unique_derived_seed_count"] == inv["all_derived_seed_count"],
        "checkpoint_resume_equivalence": equal, "prediction_label_alignment": True,
        "independent_test_access": 0, "historical_run_status": progress_old.get("status"),
        "resources": resource_snapshot(), "diagnostic_archive_sha256": sha256(archive)}
    atomic_json(report, preflight_dir / "PREFLIGHT.json")
    return report


def run_experiment(resume: bool) -> None:
    global RUN_STARTED_MONO, ACTIVE_WALL_BASE
    freeze, cfg, inv = verify_freeze()
    preflight = read_json(HERE / "preflight" / "PREFLIGHT.json", {})
    if preflight.get("status") != "PASS" or preflight.get("freeze_sha256") != sha256(FREEZE_PATH):
        raise RuntimeError("A passing preflight bound to the current freeze is required.")
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    old_progress = run_progress()
    if old_progress.get("status") == "completed":
        print("The frozen sprint is already completed; no samples or models were changed.")
        return
    if not resume and old_progress.get("status") not in ("not_started", None):
        raise RuntimeError(f"Run status is {old_progress.get('status')}; use --resume to continue safely.")
    if resume and (RUN_DIR / "STOP").exists():
        (RUN_DIR / "STOP").unlink()
    acquire_lock()
    started = time.monotonic()
    prev = run_progress()
    RUN_STARTED_MONO = started
    ACTIVE_WALL_BASE = float(prev.get("active_wall_seconds", 0.0))
    progress = set_progress(status="running", pid=os.getpid(), started_utc=prev.get("started_utc", utc_now()),
        resumed=bool(resume), working_directory=os.getcwd(), output_directory=str(RUN_DIR),
        freeze_sha256=sha256(FREEZE_PATH), target_jobs=30, independent_test_access=0,
        unique_diagnostic_shots=int(preflight.get("diagnostic_shots", 0)),
        current_phase="start", active_wall_seconds=ACTIVE_WALL_BASE,
        gpu_training_seconds=float(prev.get("gpu_training_seconds", 0.0)),
        gpu_inference_seconds=float(prev.get("gpu_inference_seconds", 0.0)))
    append_event({"type": "controller_started", "pid": os.getpid(), "resume": bool(resume),
                  "cwd": os.getcwd(), "freeze_sha256": sha256(FREEZE_PATH)})
    try:
        torch.use_deterministic_algorithms(True); torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        device = torch.device("cuda")
        prepared = prepared_regimes(cfg)
        # Generate only train/monitor/calibration/threshold data first.
        for root in range(int(cfg["roots"])):
            root_data = {}
            for split in ("train", "monitor", "calibration", "threshold_selection"):
                sample_partition(split, root, cfg, inv, prepared, run_progress(), started)
                root_data[split] = load_root_split(root, split)
            coords = prepared["balanced"][0].get_detector_coordinates()
            root_data["coords"] = coords
            for strategy in cfg["models"]["strategies"]:
                for size in cfg["sampling"]["train_budgets_per_regime_root"]:
                    job = {"job_id": job_id(root, strategy, int(size)), "root": root,
                           "strategy": strategy, "train_size_per_regime": int(size)}
                    selection = fit_one(job, root_data, coords, cfg, inv, device, started, run_progress())
                    progress = run_progress()
                    completed = sorted(set(progress.get("selection_jobs", [])) | {job["job_id"]})
                    set_progress(selection_jobs=completed, current_job=job["job_id"], current_root=root,
                                 current_phase="selection_frozen")
            progress = run_progress()
            set_progress(completed_roots_training=int(progress.get("completed_roots_training", 0)) + 1)
        jobs = make_jobs(cfg)
        expected = len(jobs)
        selections = list((RUN_DIR / "selections").glob("*.json"))
        if len(selections) != expected:
            raise RuntimeError(f"Cannot open final development evaluation: {len(selections)}/{expected} frozen selections.")
        set_progress(gpu_training_seconds=selected_training_gpu_seconds(), current_phase="all_selections_frozen")
        append_event({"type": "all_selections_frozen", "count": len(selections), "final_samples_not_yet_generated": True})
        # Final evaluation generation starts only now.
        for root in range(int(cfg["roots"])):
            sample_partition("final_development_evaluation", root, cfg, inv, prepared, run_progress(), started)
        all_rows, training_rows, learning_rows = [], [], []
        total_inference = 0.0
        for job in jobs:
            progress = run_progress()
            enforce_limits(cfg, progress, started)
            root = job["root"]
            final_data = load_root_split(root, "final_development_evaluation")
            root_data = {"final_development_evaluation": final_data,
                         "coords": prepared["balanced"][0].get_detector_coordinates()}
            rows, runtime = evaluate_job(job, root_data, cfg, device, progress, started)
            all_rows.extend(rows); total_inference += runtime["gpu_inference_seconds"]
            sel = read_json(RUN_DIR / "selections" / f"{job['job_id']}.json")
            training_row = {"job_id": job["job_id"], "root": root, "strategy": job["strategy"],
                "train_size_per_regime": job["train_size_per_regime"], "train_positive_examples": sel["positive_examples"],
                "train_prevalence": sel["prevalence"], "pos_weight": sel["pos_weight"],
                "best_epoch": sel["best_epoch"], "best_monitor_nll": sel["best_monitor_nll"],
                "temperature": sel["temperature"], "threshold_min_ler": sel["threshold_min_ler"],
                "gate_threshold": sel["confidence_gate"]["threshold"],
                "gate_fallback": sel["confidence_gate"]["fallback"],
                "gate_precision_lcb": sel["confidence_gate"]["precision_lower_bound"],
                "parameter_count": sel["parameter_count"], "gpu_seconds_train_and_select": sel["gpu_seconds_train_and_select"]}
            training_rows.append(training_row)
            for hist in sel["monitor_history"]:
                learning_rows.append({"job_id": job["job_id"], "root": root, "strategy": job["strategy"],
                    "train_size_per_regime": job["train_size_per_regime"], **hist})
            completed = sorted(set(run_progress().get("completed_jobs", [])) | {job["job_id"]})
            set_progress(completed_jobs=completed, current_job=job["job_id"], current_root=root,
                         current_phase="final_evaluation", gpu_inference_seconds=saved_inference_gpu_seconds())
        # All reports below are computed from saved per-shot prediction archives.
        write_csv(RUN_DIR / "PAIRED_EVALUATION.csv", all_rows)
        write_csv(RUN_DIR / "TRAINING_RESULTS.csv", training_rows)
        write_csv(HERE / "learning_curves" / "epoch_metrics.csv", learning_rows)
        results = summarize(all_rows, training_rows, cfg, run_progress())
        atomic_json(results, RUN_DIR / "RESULTS.json")
        atomic_json({"status": "completed", "gpu_training_seconds": run_progress().get("gpu_training_seconds", 0.0),
            "gpu_inference_seconds": total_inference, "unique_sample_shots": committed_shots(),
            "diagnostic_shots": int(preflight.get("diagnostic_shots", 0)),
            "unique_total_shots_including_diagnostics": committed_shots() + int(preflight.get("diagnostic_shots", 0)),
            "maximum_rss_gib": run_progress().get("resource_maxima", {}).get("rss_gib", resource_snapshot()["rss_gib"]),
            "maximum_cuda_allocated_gib": max(run_progress().get("resource_maxima", {}).get("cuda_allocated_gib", 0.0),
                torch.cuda.max_memory_allocated(0) / (1024 ** 3)),
            "maximum_cuda_reserved_gib": run_progress().get("resource_maxima", {}).get("cuda_reserved_gib", 0.0),
            "minimum_free_disk_gib": run_progress().get("resource_maxima", {}).get("minimum_free_disk_gib", resource_snapshot()["free_disk_gib"])}, HERE / "RESOURCE_USAGE.json")
        create_final_report(results, cfg)
        verify_summary_from_archives()
        verifier = subprocess.run([sys.executable, str(HERE / "verify_results.py")], cwd=str(REPO),
                                  capture_output=True, text=True)
        (RUN_DIR / "independent_verifier.stdout.log").write_text(verifier.stdout, encoding="utf-8")
        (RUN_DIR / "independent_verifier.stderr.log").write_text(verifier.stderr, encoding="utf-8")
        if verifier.returncode != 0:
            raise RuntimeError(f"Independent evidence verifier failed ({verifier.returncode}): {verifier.stderr[-4000:]}")
        manifest = build_manifest()
        atomic_json(manifest, HERE / "CHECKPOINT_MANIFEST.json")
        progress = run_progress()
        set_progress(status="completed", completed_at_utc=utc_now(), completed_jobs=sorted(set(progress.get("completed_jobs", []))),
            independent_test_access=0, current_phase="complete", current_job=None, current_root=None)
        append_event({"type": "controller_completed", "jobs": len(jobs), "unique_sample_shots": committed_shots(),
                      "independent_test_access": 0})
    except PauseRun as exc:
        progress = run_progress()
        set_progress(status="paused", pause_reason=str(exc))
        append_event({"type": "controller_paused", "reason": str(exc)})
    except Exception as exc:
        progress = run_progress()
        tb = traceback.format_exc()
        atomic_json({"status": "failed", "error": repr(exc), "traceback": tb, "failed_utc": utc_now()}, RUN_DIR / "ERROR.json")
        set_progress(status="failed", error=repr(exc))
        append_event({"type": "controller_failed", "error": repr(exc), "traceback": tb})
        raise
    finally:
        release_lock()


def create_final_report(results: dict, cfg: dict) -> None:
    def pct(v): return f"{100.0 * float(v):.4f}%"
    lines = ["# Q-SHIFT Hybrid Residual Sprint — Development Report", "",
        "**Status:** development-only; independent test access = 0.", "",
        f"Unique new simulation shots: {results['unique_production_shots']:,} (plus {cfg['sampling']['diagnostic_shots_per_regime'] * len(REGIMES)} preflight diagnostics).",
        "The reported intervals use five independent roots and are descriptive; the experiment is not confirmatory.", "",
        "## Candidate summary", "",
        "| Strategy | Training shots/regime | Policy | Pooled LER | Root mean LER (95% t interval) | PM mean LER | Mean paired delta | Root bootstrap 95% delta CI | Candidate-only / PM-only | Roots win/loss/tie | Helpful/harmful corrections | Holm-adjusted root sign-flip p |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for s in results["summary"]:
        boot = s["root_paired_bootstrap_ci95"]
        lines.append(f"| {s['strategy']} | {s['train_size_per_regime']:,} | {s['policy']} | {pct(s['pooled_ler'])} | {pct(s['root_equal_regime_ler']['mean'])} [{pct(s['root_equal_regime_ler']['ci95_low'])}, {pct(s['root_equal_regime_ler']['ci95_high'])}] | {pct(s['root_equal_regime_pymatching_ler']['mean'])} | {pct(s['root_paired_delta']['mean'])} [{pct(s['root_paired_delta']['ci95_low'])}, {pct(s['root_paired_delta']['ci95_high'])}] | [{pct(boot['low'])}, {pct(boot['high'])}] | {s['candidate_only']} / {s['pymatching_only']} | {s['roots_won_vs_pm']}/{s['roots_lost_vs_pm']}/{s['roots_tied_vs_pm']} | {s['beneficial_corrections']} / {s['harmful_corrections']} | {s['holm_p_over_all_candidate_policies']:.4g} |")
    lines += ["", "## Interpretation", "",
        "These are exploratory development comparisons. Thresholds and temperatures were frozen using calibration/threshold-selection partitions before final-development scoring. The same final shots were used for all strategies within a root/regime. Holm-adjusted exact sign-flip values are exploratory with five root clusters; the sign-flip symmetry/exchangeability assumption is limited at this sample size. No result is an independent-test conclusion.", "",
        "A later study is justified only if one policy lowers paired LER consistently across roots, has useful correction precision, and does not rely on a single regime/root. Otherwise retain PyMatching and do not scale. See `NEXT_EXPERIMENT_DECISION.md` and `RESULTS.json` for all root and regime records.", ""]
    report = HERE / "FINAL_RESEARCH_REPORT.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    # Apply only the predeclared primary policy, not the post-hoc best of nine.
    primary_spec = cfg["analysis"]["primary_candidate"]
    primary = next(x for x in results["summary"] if
        x["strategy"] == primary_spec["strategy"] and
        int(x["train_size_per_regime"]) == int(primary_spec["train_size_per_regime"]) and
        x["policy"] == primary_spec["policy"])
    go = (primary["root_paired_delta"]["mean"] <= -float(cfg["analysis"]["development_go_gate"]["minimum_absolute_ler_reduction"]) and
          primary["roots_won_vs_pm"] >= int(cfg["analysis"]["development_go_gate"]["minimum_favorable_roots"]) and
          primary["root_paired_bootstrap_ci95"]["high"] < 0 and primary["correction_precision"] >
          float(cfg["analysis"]["development_go_gate"]["correction_precision_above"]))
    decision = "GO to propose a separate frozen confirmatory study" if go else "NO-GO for 10M/60M scaling"
    (HERE / "NEXT_EXPERIMENT_DECISION.md").write_text(
        "# Next-experiment decision\n\n" + f"**Decision:** {decision}.\n\n" +
        f"Predeclared primary: `{primary['strategy']}` / `{primary['train_size_per_regime']}` / `{primary['policy']}`. " +
        f"Mean root paired delta {pct(primary['root_paired_delta']['mean'])}, 95% descriptive root-t interval " +
        f"[{pct(primary['root_paired_delta']['ci95_low'])}, {pct(primary['root_paired_delta']['ci95_high'])}], " +
        f"root-bootstrap interval [{pct(primary['root_paired_bootstrap_ci95']['low'])}, {pct(primary['root_paired_bootstrap_ci95']['high'])}], " +
        f"roots won/lost/tied {primary['roots_won_vs_pm']}/{primary['roots_lost_vs_pm']}/{primary['roots_tied_vs_pm']}, " +
        f"correction precision {primary['correction_precision']:.3f}.\n\n" +
        "The gate requires a mean reduction of at least 0.0002, at least four favorable roots, bootstrap upper bound below zero, and correction precision above 0.5. All nine frozen comparisons are Holm-adjusted; with five roots, the smallest possible unadjusted exact sign-flip p-value is 0.0625, so this sprint cannot establish confirmatory significance. Preserve PyMatching as the default and keep the independent test sealed. A GO would only authorize designing a separately frozen confirmatory study.\n",
        encoding="utf-8")


def verify_summary_from_archives() -> None:
    rows = []
    for pred_path in sorted((RUN_DIR / "predictions").glob("root*.npz")):
        arrays, meta = load_sample_archive(pred_path, expected_split=None) if pred_path.with_suffix(".json").exists() else (None, None)
        if arrays is None:
            # Prediction metadata is a distinct schema and is still hash-bound.
            meta = read_json(pred_path.with_suffix(".json"), {})
            if sha256(pred_path) != meta.get("archive_sha256"):
                raise RuntimeError(f"Prediction archive hash mismatch: {pred_path}")
            with np.load(pred_path, allow_pickle=False) as z:
                arrays = {k: z[k] for k in z.files}
        for regime in REGIMES:
            y, pm = arrays[f"observable__{regime}"], arrays[f"pymatching__{regime}"]
            for key in arrays:
                if key.startswith("prediction_") and key.endswith("__" + regime):
                    policy = key[len("prediction_"):].split("__")[0]
                    pred = arrays[key]
                    m = confusion_metrics(pred, y, pm)
                    rows.append({"root": int(meta["root"]), "strategy": meta["strategy"],
                        "train_size_per_regime": int(meta["train_size_per_regime"]),
                        "policy": policy, "regime": regime, **m})
    csv_path = RUN_DIR / "PAIRED_EVALUATION.csv"
    csv_rows = list(csv.DictReader(csv_path.open("r", encoding="utf-8", newline="")))
    # CSV numeric serialization and NPZ recomputation must agree exactly in
    # integer metrics and within serialization tolerance for rates.
    if len(rows) != len(csv_rows):
        raise RuntimeError(f"Saved prediction audit row count mismatch: {len(rows)} vs {len(csv_rows)}")
    index = {(int(r["root"]), r["strategy"], int(r["train_size_per_regime"]), r["policy"], r["regime"]): r for r in rows}
    for saved in csv_rows:
        key = (int(saved["root"]), saved["strategy"], int(saved["train_size_per_regime"]), saved["policy"], saved["regime"])
        rec = index[key]
        for field in ("shots", "errors", "pymatching_errors", "candidate_only", "pymatching_only",
                      "prediction_disagreements", "beneficial_corrections", "harmful_corrections"):
            if int(float(saved[field])) != int(rec[field]):
                raise RuntimeError(f"Independent saved-array recomputation mismatch {field} {key}")
        if abs(float(saved["ler"]) - float(rec["ler"])) > 1e-12:
            raise RuntimeError(f"Independent LER recomputation mismatch {key}")
    atomic_json({"status": "PASS", "prediction_archives": len(list((RUN_DIR / "predictions").glob("root*.npz"))),
        "recomputed_rows": len(rows), "paired_evaluation_csv_rows": len(csv_rows),
        "all_aggregates_recomputed_from_saved_predictions": True, "independent_test_access": 0},
        RUN_DIR / "INDEPENDENT_RECOMPUTATION.json")


def build_manifest() -> dict:
    files = []
    for path in HERE.rglob("*"):
        rel = path.relative_to(HERE).as_posix()
        volatile = rel in {"run/PROGRESS.json", "run/progress.jsonl", "run/sprint.lock", "run/STOP"} or rel.startswith("run/logs/")
        if path.is_file() and path.name not in {"CHECKPOINT_MANIFEST.json", "sprint.lock", "STOP"} and not volatile and not path.name.endswith(".tmp"):
            files.append({"path": rel, "bytes": path.stat().st_size, "sha256": sha256(path)})
    return {"created_utc": utc_now(), "status": "development outputs; test untouched",
            "file_count": len(files), "independent_test_access": 0, "files": files}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--stop", action="store_true")
    args = ap.parse_args()
    if args.status:
        print(json.dumps(run_progress(), indent=2)); return
    if args.stop:
        RUN_DIR.mkdir(parents=True, exist_ok=True)
        (RUN_DIR / "STOP").write_text("safe stop requested\n", encoding="utf-8")
        print(f"Safe-stop marker written: {RUN_DIR / 'STOP'}"); return
    if args.preflight:
        report = prepare_preflight()
        print(json.dumps(report, indent=2)); return
    if args.run or args.resume:
        run_experiment(resume=args.resume)
        return
    ap.error("select --preflight, --run, --resume, --status, or --stop")


if __name__ == "__main__":
    main()
