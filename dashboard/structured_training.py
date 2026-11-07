"""Streaming, resumable training integration for the structured Q-SHIFT decoder.

This module deliberately has no test-split sampling path.  The prepared test
allocation is screened and recorded, but only a later, explicitly frozen
evaluation program may open it.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import random
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import torch
import torch.nn.functional as F
import psutil

from models import DirectMLP, ResidualMLP
from seed_protocol import MAX_STIM_SEED, historical_seeds
from simulator import decode_matching, prepare, sample
from structured_decoder import StructuredConv3DDecoder
from telemetry import device_snapshot

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
OUTPUT_ROOT = REPO_ROOT / "outputs" / "neural_decoder_diagnostic"
PROTOCOL_CONFIG = OUTPUT_ROOT / "structured_diagnostic_config.json"
PROTOCOL_INVENTORY = OUTPUT_ROOT / "structured_seed_inventory.json"
PROTOCOL_FREEZE = OUTPUT_ROOT / "structured_diagnostic_freeze.json"
REGIMES = ("x_biased", "balanced", "z_biased")


class ResourceMonitor:
    """Low-frequency process/GPU memory sampling for the complete worker run."""
    def __init__(self, device: torch.device, interval: float = 0.5):
        self.device = device
        self.interval = interval
        self.process = psutil.Process(os.getpid())
        self.peak_rss = 0
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._sample, daemon=True, name="qshift-structured-resource-monitor")

    def _sample(self):
        while not self.stop_event.is_set():
            try:
                self.peak_rss = max(self.peak_rss, int(self.process.memory_info().rss))
            except (psutil.Error, OSError):
                pass
            self.stop_event.wait(self.interval)

    def start(self):
        self.thread.start()
        return self

    def finish(self) -> dict:
        self.stop_event.set()
        self.thread.join(timeout=2)
        try:
            self.peak_rss = max(self.peak_rss, int(self.process.memory_info().rss))
        except (psutil.Error, OSError):
            pass
        return {"host_peak_rss_bytes": self.peak_rss or None,
                "gpu_peak_allocated_bytes": int(torch.cuda.max_memory_allocated(0)) if self.device.type == "cuda" else None,
                "gpu_peak_reserved_bytes": int(torch.cuda.max_memory_reserved(0)) if self.device.type == "cuda" else None,
                "sample_interval_seconds": self.interval}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_config_for_hash(config: dict) -> dict:
    stable = copy.deepcopy(config)
    for key in ("seed_inventory", "train_seed_inventory"):
        nested = stable.get(key)
        if isinstance(nested, dict):
            nested.pop("latest_collision_rescreen", None)
    stable.pop("seed_screen", None)
    return stable


def config_hash(config: dict) -> str:
    return hashlib.sha256(json.dumps(stable_config_for_hash(config), sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def atomic_json(payload: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temp, path)


def atomic_torch(payload: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    torch.save(payload, temp)
    os.replace(temp, path)


def inventory_seed_values(inventory: dict) -> set[int]:
    values: set[int] = set()
    for stream in inventory.get("streams", []):
        values.update(int(seed) for seed in stream.get("seeds", []))
    if inventory.get("model_seed") is not None:
        values.add(int(inventory["model_seed"]))
    values.update(int(seed) for seed in inventory.get("model_seeds", []))
    values.update(int(seed) for seed in inventory.get("diagnostic_seeds", []))
    return values


def screen_inventory(inventory: dict, prior_allocations: list[dict] | None = None,
                     candidate_count: int = 6) -> dict:
    """Re-screen train, validation, reserved-test, and model RNG namespaces."""
    values = inventory_seed_values(inventory)
    model_root = int(inventory.get("model_seed", (inventory.get("model_seeds") or [0])[0]))
    model_seeds = list(range(model_root, model_root + int(candidate_count)))
    diagnostic_seeds = [int(x) for x in inventory.get("diagnostic_seeds", [model_root + 100 + i for i in range(3)])]
    collisions = []
    expected_counts = [inventory.get(k) for k in ("derived_seed_count_including_model", "unique_derived_seed_count", "unique_seed_count") if inventory.get(k) is not None]
    expected = int(expected_counts[0]) if expected_counts else len(values)
    if len(values) != expected or any(len(values) != int(v) for v in expected_counts):
        collisions.append({"kind": "inventory_count_mismatch", "actual_unique": len(values), "expected_counts": expected_counts})
    if set(model_seeds) & {seed for stream in inventory.get("streams", []) for seed in stream.get("seeds", [])}:
        collisions.append({"kind": "derived_model_seed_stream_collision", "seeds": sorted(
            set(model_seeds) & {seed for stream in inventory.get("streams", []) for seed in stream.get("seeds", [])})})
    if len(model_seeds) != len(set(model_seeds)):
        collisions.append({"kind": "duplicate_model_rng_seeds"})
    if len(diagnostic_seeds) != len(set(diagnostic_seeds)):
        collisions.append({"kind": "duplicate_diagnostic_seeds"})
    if any(seed < 1 or seed > MAX_STIM_SEED for seed in model_seeds + diagnostic_seeds):
        collisions.append({"kind": "derived_seed_outside_stim_range"})
    hist_hits = sorted((values | set(model_seeds) | set(diagnostic_seeds)) & historical_seeds())
    if hist_hits:
        collisions.append({"kind": "historical_seed_overlap", "seeds": hist_hits})
    diag_stream_hits = set(diagnostic_seeds) & {seed for stream in inventory.get("streams", []) for seed in stream.get("seeds", [])}
    if diag_stream_hits:
        collisions.append({"kind": "diagnostic_stream_collision", "seeds": sorted(diag_stream_hits)})
    if set(diagnostic_seeds) & set(model_seeds):
        collisions.append({"kind": "diagnostic_model_rng_collision", "seeds": sorted(set(diagnostic_seeds) & set(model_seeds))})
    for prior in prior_allocations or []:
        for stream in inventory.get("streams", []):
            lo, hi = stream["seed_range_inclusive"]
            for old_name, (old_lo, old_hi) in prior.get("stream_ranges_inclusive", {}).items():
                if max(int(lo), int(old_lo)) <= min(int(hi), int(old_hi)):
                    collisions.append({"kind": "dashboard_stream_overlap", "stream": f"{stream['split']}:{stream['regime']}",
                                       "other_stream": old_name,
                                       "overlap": [max(int(lo), int(old_lo)), min(int(hi), int(old_hi))]})
        for old_name, (old_lo, old_hi) in (prior.get("stream_ranges_inclusive", {}) or {}).items():
            for seed in model_seeds + diagnostic_seeds:
                if int(old_lo) <= seed <= int(old_hi):
                    collisions.append({"kind": "model_seed_dashboard_overlap", "seed": seed,
                                       "other_stream": old_name})
    return {"passed": not collisions, "collisions": collisions,
            "unique_stream_seed_count": len(values), "candidate_model_rng_seeds": model_seeds,
            "diagnostic_seeds": diagnostic_seeds,
            "historical_seed_values_checked": len(historical_seeds()),
            "prior_dashboard_allocations_checked": len(prior_allocations or []),
            "test_streams_included_in_collision_screen": [
                {"regime": s["regime"], "range": s["seed_range_inclusive"]}
                for s in inventory.get("streams", []) if s.get("split") == "test"]}


def make_development_inventory(train_per_regime: int, validation_per_regime: int,
                               batch_size: int = 128, prior_allocations: list[dict] | None = None) -> dict:
    """Build a new development-only namespace, disjoint from frozen allocations."""
    from structured_protocol import build_inventory

    # 1.10B–1.15B is reserved here for small development streams, separate
    # from the prospective 1.00B–1.08B 100K protocol allocations.
    root_map = {
        "train": {r: 1_100_000_001 + i * 100_000 for i, r in enumerate(REGIMES)},
        "validation": {r: 1_130_000_001 + i * 100_000 for i, r in enumerate(REGIMES)},
    }
    model_seed = 1_160_000_001
    streams = []
    model_seeds = list(range(model_seed, model_seed + 6))
    diagnostic_seeds = [1_170_000_001, 1_170_000_002, 1_170_000_003]
    all_values: list[int] = list(model_seeds) + diagnostic_seeds
    for split, amount in (("train", train_per_regime), ("validation", validation_per_regime)):
        for regime in REGIMES:
            root = root_map[split][regime]
            count = math.ceil(amount / batch_size)
            seeds = list(range(root, root + count))
            streams.append({"split": split, "regime": regime, "root": root, "shots": amount,
                            "batch_size": batch_size, "batch_count": count,
                            "seed_range_inclusive": [root, root + count - 1], "seeds": seeds})
            all_values.extend(seeds)
    collisions: list[dict] = []
    if len(all_values) != len(set(all_values)):
        collisions.append({"kind": "duplicate_within_development", "values": sorted(
            s for s in set(all_values) if all_values.count(s) > 1)})
    if any(seed < 1 or seed > MAX_STIM_SEED for seed in all_values):
        collisions.append({"kind": "outside_stim_seed_range"})
    hist = historical_seeds()
    hist_hits = sorted(set(all_values) & hist)
    if hist_hits:
        collisions.append({"kind": "historical_seed_overlap", "values": hist_hits})

    frozen_inventory = json.loads(PROTOCOL_INVENTORY.read_text(encoding="utf-8"))
    frozen_values = inventory_seed_values(frozen_inventory)
    frozen_hits = sorted(set(all_values) & frozen_values)
    if frozen_hits:
        collisions.append({"kind": "prepared_100k_namespace_overlap", "values": frozen_hits})
    for prior in prior_allocations or []:
        ranges = prior.get("stream_ranges_inclusive", {})
        for stream in streams:
            lo, hi = stream["seed_range_inclusive"]
            for old_name, (old_lo, old_hi) in ranges.items():
                if max(lo, int(old_lo)) <= min(hi, int(old_hi)):
                    collisions.append({"kind": "dashboard_run_overlap", "split": stream["split"],
                                       "regime": stream["regime"], "other_stream": old_name,
                                       "overlap": [max(lo, int(old_lo)), min(hi, int(old_hi))]})
    # Model RNG is checked against every source of recorded integer seeds too.
    model_hits = sorted(set(model_seeds) & (hist | frozen_values))
    if model_hits:
        collisions.append({"kind": "model_seed_overlap", "seeds": model_hits})
    for prior in prior_allocations or []:
        for old_name, (old_lo, old_hi) in prior.get("stream_ranges_inclusive", {}).items():
            for candidate_seed in model_seeds + diagnostic_seeds:
                if int(old_lo) <= candidate_seed <= int(old_hi):
                    collisions.append({"kind": "model_seed_dashboard_overlap", "seed": candidate_seed,
                                       "other_stream": old_name})
    return {"allocation": "one deterministic Stim seed per streamed batch; separate train/validation roots per regime",
            "train_per_regime": train_per_regime, "validation_per_regime": validation_per_regime,
            "batch_size": batch_size, "model_seed": model_seed, "model_seeds": model_seeds,
            "diagnostic_seeds": diagnostic_seeds, "streams": streams,
            "unique_derived_seed_count": len(set(all_values)), "derived_seed_count": len(all_values),
            "historical_seed_values_checked": len(hist), "prepared_100k_seed_values_checked": len(frozen_values),
            "collisions": collisions, "passed": not collisions,
            "coverage_limit": "screening covers recoverable historical scan values, frozen 100K allocation, and saved dashboard run inventories; unavailable seed records remain unknown."}


def scale_budget_allocation(total_unique_shots: int) -> dict:
    """Split 70/15/15. The test portion is reserved and never sampled here."""
    total = int(total_unique_shots)
    if total not in (100_000, 1_000_000, 10_000_000, 100_000_000):
        raise ValueError("Supported structured budgets are 100K, 1M, 10M, and 100M unique shots.")
    train_total = total * 70 // 100
    validation_total = total * 15 // 100
    test_reserved = total - train_total - validation_total
    def distribute(n: int) -> dict:
        q, r = divmod(n, 3)
        return {regime: q + (i < r) for i, regime in enumerate(REGIMES)}
    return {"total_unique_shots": total, "training": distribute(train_total),
            "validation": distribute(validation_total), "test_reserved_not_sampled": distribute(test_reserved)}


def make_scale_inventory(total_unique_shots: int, batch_size: int = 256,
                         prior_allocations: list[dict] | None = None) -> dict:
    """Allocate larger development budgets in separate, checked seed ranges."""
    alloc = scale_budget_allocation(total_unique_shots)
    if int(total_unique_shots) == 100_000:
        _, inventory = load_prepared_freeze()
        result = dict(inventory)
        result["budget_note"] = "Uses the already frozen Phase 100K allocation; its test stream remains unopened."
        return result
    # The 1.20–1.23B namespace is reserved for larger prospective runs.
    # Each regime receives a 200K-seed slot, enough for the 100M budget at
    # the supported 256-shot default (max 91,146 training batches/regime).
    split_base = {"train": 1_200_000_001, "validation": 1_201_000_001,
                  "test": 1_202_000_001}
    streams = []
    diagnostic_seeds = [1_204_000_001, 1_204_000_002, 1_204_000_003]
    values: list[int] = list(diagnostic_seeds)
    for split, count_map in (("train", alloc["training"]),
                             ("validation", alloc["validation"]),
                             ("test", alloc["test_reserved_not_sampled"])):
        for i, regime in enumerate(REGIMES):
            count = int(count_map[regime])
            n_batches = math.ceil(count / batch_size)
            if n_batches >= 200_000:
                raise ValueError("The selected batch size exceeds the reserved 200K seed slot; use batch_size >= 256.")
            root = split_base[split] + i * 200_000
            seeds = list(range(root, root + n_batches))
            streams.append({"split": split, "regime": regime, "root": root, "shots": count,
                            "batch_size": batch_size, "batch_count": n_batches,
                            "seed_range_inclusive": [root, root + n_batches - 1], "seeds": seeds})
            values.extend(seeds)
    model_seeds = list(range(1_203_000_001, 1_203_000_007))
    values.extend(model_seeds)
    collisions = []
    if len(values) != len(set(values)):
        collisions.append({"kind": "duplicate_proposed_seed"})
    if any(seed < 1 or seed > MAX_STIM_SEED for seed in values):
        collisions.append({"kind": "outside_stim_seed_range"})
    hist = historical_seeds()
    hits = sorted(set(values) & hist)
    if hits:
        collisions.append({"kind": "historical_seed_overlap", "values": hits})
    frozen_config, frozen_inventory = load_prepared_freeze()
    frozen_values = inventory_seed_values(frozen_inventory)
    frozen_hits = sorted(set(values) & frozen_values)
    if frozen_hits:
        collisions.append({"kind": "prepared_100k_seed_overlap", "values": frozen_hits})
    for prior in prior_allocations or []:
        for stream in streams:
            lo, hi = stream["seed_range_inclusive"]
            for prior_name, (p_lo, p_hi) in prior.get("stream_ranges_inclusive", {}).items():
                if max(lo, int(p_lo)) <= min(hi, int(p_hi)):
                    collisions.append({"kind": "dashboard_run_overlap", "stream": stream["split"],
                                       "regime": stream["regime"], "other_stream": prior_name,
                                       "overlap": [max(lo, int(p_lo)), min(hi, int(p_hi))]})
    for prior in prior_allocations or []:
        for prior_name, (p_lo, p_hi) in prior.get("stream_ranges_inclusive", {}).items():
            for seed in model_seeds + diagnostic_seeds:
                if int(p_lo) <= seed <= int(p_hi):
                    collisions.append({"kind": "model_seed_dashboard_overlap", "seed": seed,
                                       "other_stream": prior_name})
    result = {"allocation": "70/15/15 train/validation/reserved-test split; independent roots per regime",
              "total_unique_shots": int(total_unique_shots), "batch_size": int(batch_size),
              "model_seeds": model_seeds, "model_seed": model_seeds[0],
              "diagnostic_seeds": diagnostic_seeds, "streams": streams,
              "derived_seed_count": len(values), "unique_seed_count": len(set(values)),
              "historical_seed_values_checked": len(hist), "prepared_100k_seed_values_checked": len(frozen_values),
              "collisions": collisions, "passed": not collisions,
              "test_stream_policy": "reserved and collision-screened; not sampled by structured_training.py",
              "coverage_limit": "recoverable historical seed scan and saved dashboard manifests only"}
    return result


def load_prepared_freeze() -> tuple[dict, dict]:
    config = json.loads(PROTOCOL_CONFIG.read_text(encoding="utf-8"))
    inventory = json.loads(PROTOCOL_INVENTORY.read_text(encoding="utf-8"))
    frozen = json.loads(PROTOCOL_FREEZE.read_text(encoding="utf-8"))
    for path in (PROTOCOL_CONFIG, PROTOCOL_INVENTORY):
        expected = frozen["sha256"][path.name]
        if sha256_file(path) != expected:
            raise RuntimeError(f"Prepared protocol integrity check failed: {path.name}")
    if not inventory.get("passed"):
        raise RuntimeError("Prepared 100K seed inventory did not pass its historical collision screen.")
    return config, inventory


def prepare_regimes(config: dict, diagnostic_seeds: list[int]) -> tuple[dict, dict, dict]:
    base = {"distance": 3, "rounds": 5, "memory_basis": "z", "gate_p": 0.003,
            "measurement_p": 0.003, "bias_ratio": 10.0, "device": config.get("device", "auto")}
    envs: dict = {}
    coords: dict | None = None
    fingerprints: dict = {}
    if len(diagnostic_seeds) < len(REGIMES) or len(set(diagnostic_seeds)) != len(diagnostic_seeds):
        raise RuntimeError("Circuit diagnostic seeds must be unique and cover all three regimes.")
    for regime_index, regime in enumerate(REGIMES):
        circuit, noise_record, dem, matching, fixed_index, bank_records = prepare({**base, "noise_regime": regime})
        if circuit.num_detectors != 40 or circuit.num_observables != 1:
            raise RuntimeError(f"{regime}: expected 40 detectors and one observable")
        current_coords = circuit.get_detector_coordinates()
        if coords is None:
            coords = current_coords
        elif current_coords != coords:
            raise RuntimeError("Detector geometry changed across the three generation regimes.")
        noiseless = circuit.without_noise()
        d0, y0 = noiseless.compile_detector_sampler(seed=int(diagnostic_seeds[regime_index])).sample(
            shots=16, separate_observables=True)
        if np.any(d0) or np.any(y0):
            raise RuntimeError(f"Noiseless circuit validation failed for {regime}.")
        envs[regime] = {"circuit": circuit, "matching": matching, "fixed_index": fixed_index}
        fingerprints[regime] = {"noise_record": noise_record, "dem_sha256": hashlib.sha256(str(dem).encode()).hexdigest(),
                                "circuit_sha256": hashlib.sha256(str(circuit).encode()).hexdigest(),
                                "detectors": circuit.num_detectors, "observables": circuit.num_observables,
                                "fixed_decoder_index": fixed_index, "bank_records": bank_records}
    assert coords is not None
    return envs, coords, fingerprints


def batch_jobs(shot_counts: dict, batch_size: int, epoch: int, shuffle_seed: int) -> list[tuple[str, int, int]]:
    jobs: list[tuple[str, int, int]] = []
    for regime in REGIMES:
        n = int(shot_counts[regime])
        for index, start in enumerate(range(0, n, batch_size)):
            jobs.append((regime, index, min(batch_size, n - start)))
    random.Random(int(shuffle_seed) + int(epoch)).shuffle(jobs)
    return jobs


def stream_batch(envs: dict, inventory: dict, split: str, regime: str, batch_index: int,
                 count: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if split not in {"train", "validation"}:
        raise RuntimeError("The structured worker has no test-sampling path; requested split is blocked.")
    stream = next(item for item in inventory["streams"]
                  if item["split"] == split and item["regime"] == regime)
    seed = int(stream["root"]) + int(batch_index)
    d, y = sample(envs[regime]["circuit"], seed, count)
    matching = decode_matching(envs[regime]["matching"], d)
    return d, y, matching


def candidate_spec(name: str) -> dict:
    if name == "direct_mlp":
        return {"kind": "direct", "width": None, "weighted": False}
    if name == "residual_mlp":
        return {"kind": "residual", "width": None, "weighted": False}
    if name.startswith("structured_ch"):
        # e.g. structured_ch8_weighted / structured_ch16_unweighted
        parts = name.split("_")
        if len(parts) != 3 or parts[0] != "structured" or not parts[1].startswith("ch"):
            raise ValueError(f"Invalid candidate name: {name}")
        return {"kind": "structured", "width": int(parts[1][2:]), "weighted": parts[2] == "weighted"}
    raise ValueError(f"Unknown structured trainer candidate: {name}")


def make_model(spec: dict, coords: dict[int, list[float]]) -> torch.nn.Module:
    if spec["kind"] == "direct":
        return DirectMLP()
    if spec["kind"] == "residual":
        return ResidualMLP()
    return StructuredConv3DDecoder(coords, channels=int(spec["width"]), dropout=0.05)


def prediction_for(model, spec: dict, d: np.ndarray, fixed: np.ndarray, device: torch.device,
                   threshold: float = 0.5, positive_weight: float | None = None) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    x = torch.as_tensor(d, dtype=torch.float32, device=device)
    b = torch.as_tensor(fixed, dtype=torch.float32, device=device)
    with torch.inference_mode():
        logits = model(x, b) if spec["kind"] == "residual" else model(x)
        logits = _correct_weighted_logits(logits, positive_weight)
        probabilities = torch.sigmoid(logits).float().cpu().numpy()
    correction = (probabilities >= threshold).astype(np.uint8)
    if spec["kind"] == "residual":
        correction = np.bitwise_xor(fixed, correction)
    return probabilities.astype(np.float32), correction


def _correct_weighted_logits(logits: torch.Tensor, positive_weight: float | None) -> torch.Tensor:
    """Undo the ideal log-odds offset from positive-weighted binary cross entropy.

    BCEWithLogitsLoss(pos_weight=w) has optimum logit equal to the natural
    posterior logit plus log(w). Subtracting log(w) gives a calibrated-probability
    interpretation under correct model specification; validation still selects
    the operating threshold. This does not itself guarantee model calibration.
    """
    if positive_weight is None:
        return logits
    value = float(positive_weight)
    if not math.isfinite(value) or value <= 0:
        raise ValueError("positive_weight must be finite and positive")
    return logits - math.log(value)


def rng_state() -> dict:
    return {"torch": torch.get_rng_state(), "cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None,
            "numpy": np.random.get_state(), "python": random.getstate()}


def restore_rng_state(state: dict, device: torch.device) -> None:
    torch.set_rng_state(state["torch"].cpu())
    if device.type == "cuda" and state.get("cuda") is not None:
        torch.cuda.set_rng_state_all(state["cuda"])
    np.random.set_state(state["numpy"])
    random.setstate(state["python"])


def _validation_loss_and_ler(model, spec: dict, envs: dict, inventory: dict, val_counts: dict,
                             batch_size: int, device: torch.device,
                             positive_weight: float | None = None) -> tuple[float, float]:
    per_regime_ler = []
    total_loss, total_count = 0.0, 0
    model.eval()
    with torch.inference_mode():
        for regime in REGIMES:
            wrong, count = 0, 0
            for batch_index, start in enumerate(range(0, int(val_counts[regime]), batch_size)):
                size = min(batch_size, int(val_counts[regime]) - start)
                d, y, fixed = stream_batch(envs, inventory, "validation", regime, batch_index, size)
                x = torch.as_tensor(d, dtype=torch.float32, device=device)
                y_t = torch.as_tensor(y, dtype=torch.float32, device=device)
                f_t = torch.as_tensor(fixed, dtype=torch.float32, device=device)
                logits = model(x, f_t) if spec["kind"] == "residual" else model(x)
                logits = _correct_weighted_logits(logits, positive_weight)
                if spec["kind"] == "residual":
                    target = torch.as_tensor(np.bitwise_xor(fixed, y).astype(np.float32), device=device)
                else:
                    target = y_t
                total_loss += float(F.binary_cross_entropy_with_logits(logits.float(), target, reduction="sum").item())
                probabilities = torch.sigmoid(logits.float())
                correction = (probabilities >= 0.5).to(torch.uint8).cpu().numpy()
                if spec["kind"] == "residual":
                    correction = np.bitwise_xor(fixed, correction)
                wrong += int(np.count_nonzero(correction ^ y))
                count += size
            per_regime_ler.append(wrong / max(count, 1))
            total_count += count
    return total_loss / max(total_count, 1), float(np.mean(per_regime_ler))


def _training_positive_counts(envs: dict, inventory: dict, train_counts: dict,
                              batch_size: int) -> dict:
    counts = {"direct_positive": 0, "residual_positive": 0, "total": 0}
    for regime in REGIMES:
        n = int(train_counts[regime])
        for batch_index, start in enumerate(range(0, n, batch_size)):
            size = min(batch_size, n - start)
            _, y, matching = stream_batch(envs, inventory, "train", regime, batch_index, size)
            counts["direct_positive"] += int(y.sum())
            counts["residual_positive"] += int(np.bitwise_xor(y, matching).sum())
            counts["total"] += size
    counts["direct_prevalence"] = counts["direct_positive"] / max(1, counts["total"])
    counts["residual_prevalence"] = counts["residual_positive"] / max(1, counts["total"])
    return counts


def _positive_weight(spec: dict, prevalence: dict) -> float | None:
    if not spec["weighted"]:
        return None
    key = "residual_prevalence" if spec["kind"] == "residual" else "direct_prevalence"
    p = float(prevalence[key])
    if not 0 < p < 1:
        raise RuntimeError(f"Cannot compute positive weight from training-only prevalence {p}.")
    return (1.0 - p) / p


def _save_fit_state(path: Path, state: dict) -> None:
    atomic_torch(state, path)


def train_candidate(name: str, cfg: dict, envs: dict, coords: dict, inventory: dict,
                    train_counts: dict, val_counts: dict, prevalence: dict, run_dir: Path,
                    device: torch.device, resume: bool = False, event_callback=None,
                    wall_seconds_remaining: float | None = None) -> dict:
    spec = candidate_spec(name)
    candidate_index = list(cfg["candidates"]).index(name)
    model_seed = int(inventory["model_seed"]) + candidate_index
    random.seed(model_seed)
    np.random.seed(model_seed % (2**32))
    torch.manual_seed(model_seed)
    if device.type == "cuda":
        torch.cuda.manual_seed_all(model_seed)
    model = make_model(spec, coords).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(cfg["learning_rate"]), weight_decay=float(cfg["weight_decay"]))
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=0, threshold=1e-6)
    pos_weight_value = _positive_weight(spec, prevalence)
    pos_weight_tensor = (torch.tensor([pos_weight_value], dtype=torch.float32, device=device)
                         if pos_weight_value is not None else None)
    total_steps = sum(math.ceil(int(train_counts[r]) / int(cfg["batch_size"])) for r in REGIMES) * int(cfg["max_epochs"])
    checkpoint_path = run_dir / "checkpoints" / f"{name}.pt"
    config_hash_value = config_hash(cfg)
    epoch, next_job_idx, global_step, best_ler, best_loss, best_epoch, patience_count = 0, 0, 0, None, None, None, 0
    best_state = None
    history: list[dict] = []
    if resume and checkpoint_path.is_file():
        saved = torch.load(checkpoint_path, map_location=device, weights_only=False)
        if saved.get("config_sha256") != config_hash_value or saved.get("candidate") != name:
            raise RuntimeError(f"Cannot resume {name}: configuration or candidate mismatch.")
        model.load_state_dict(saved["model_state"])
        optimizer.load_state_dict(saved["optimizer_state"])
        scheduler.load_state_dict(saved["scheduler_state"])
        epoch, next_job_idx = int(saved["epoch"]), int(saved["next_job_idx"])
        global_step = int(saved["global_step"])
        best_ler, best_loss = saved["best_validation_ler"], saved["best_validation_loss"]
        best_epoch, patience_count = saved["best_epoch"], int(saved["patience_count"])
        best_state, history = saved["best_model_state"], list(saved["history"])
        restore_rng_state(saved["rng_state"], device)
    started = time.perf_counter()
    checkpoint_seconds = 0.0
    sim_seconds = 0.0
    decode_seconds = 0.0
    training_seconds = 0.0
    validation_total_seconds = 0.0
    cuda_training_verified = False
    max_wall = (float(wall_seconds_remaining) if wall_seconds_remaining is not None
                else float(cfg.get("max_wall_seconds_per_invocation", 0)))
    steps_since_ckpt = 0
    while epoch < int(cfg["max_epochs"]):
        jobs = batch_jobs(train_counts, int(cfg["batch_size"]), epoch, model_seed + 901)
        if next_job_idx >= len(jobs):
            validation_tick = time.perf_counter()
            val_loss, val_ler = _validation_loss_and_ler(model, spec, envs, inventory, val_counts,
                                                         int(cfg["batch_size"]), device,
                                                         positive_weight=pos_weight_value)
            validation_seconds = time.perf_counter() - validation_tick
            validation_total_seconds += validation_seconds
            scheduler.step(val_ler)
            improved = best_ler is None or val_ler < best_ler - 1e-12 or (
                abs(val_ler - best_ler) <= 1e-12 and val_loss < float(best_loss))
            if improved:
                best_ler, best_loss, best_epoch = float(val_ler), float(val_loss), epoch + 1
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
                patience_count = 0
            else:
                patience_count += 1
            history.append({"epoch": epoch + 1, "training_samples_seen": sum(int(v) for v in train_counts.values()),
                            "validation_bce": float(val_loss), "validation_equal_regime_ler": float(val_ler),
                            "improved": bool(improved), "validation_seconds": validation_seconds,
                            "learning_rate": float(optimizer.param_groups[0]["lr"])})
            epoch += 1
            next_job_idx = 0
            state = _fit_checkpoint_payload(name, config_hash_value, model, optimizer, scheduler, epoch,
                                            next_job_idx, global_step, best_ler, best_loss, best_epoch,
                                            patience_count, best_state, history, model_seed)
            checkpoint_tick = time.perf_counter()
            _save_fit_state(checkpoint_path, state)
            checkpoint_seconds += time.perf_counter() - checkpoint_tick
            if event_callback:
                event_callback({"type": "progress", "status": "running", "candidate": name,
                                "epoch": epoch, "global_step": global_step,
                                "total_training_shots": sum(int(v) for v in train_counts.values()),
                                "training_samples_processed": sum(int(v) for v in train_counts.values()),
                                "training_passes_completed": epoch,
                                "validation_ler": float(val_ler), "validation_loss": float(val_loss),
                                "device": str(device), "cuda_training_verified": device.type == "cuda",
                                "cuda_device_name": torch.cuda.get_device_name(0) if device.type == "cuda" else None,
                                "python_executable": sys.executable, "gpu_telemetry": device_snapshot()})
            if patience_count >= int(cfg["early_stopping_patience"]):
                break
            continue

        regime, batch_index, size = jobs[next_job_idx]
        t = time.perf_counter()
        d, y, fixed = stream_batch(envs, inventory, "train", regime, batch_index, size)
        sim_seconds += time.perf_counter() - t
        target_np = np.bitwise_xor(fixed, y) if spec["kind"] == "residual" else y
        x = torch.as_tensor(d, dtype=torch.float32, device=device)
        y_t = torch.as_tensor(target_np, dtype=torch.float32, device=device)
        fixed_t = torch.as_tensor(fixed, dtype=torch.float32, device=device)
        model.train()
        optimizer.zero_grad(set_to_none=True)
        train_tick = time.perf_counter()
        logits = model(x, fixed_t) if spec["kind"] == "residual" else model(x)
        loss = F.binary_cross_entropy_with_logits(logits.float(), y_t,
                                                   pos_weight=pos_weight_tensor)
        loss.backward()
        optimizer.step()
        if device.type == "cuda":
            torch.cuda.synchronize(device)
            cuda_training_verified = bool(x.is_cuda and loss.is_cuda and
                                          all(parameter.is_cuda for parameter in model.parameters()))
            if not cuda_training_verified:
                raise RuntimeError("CUDA was selected but the structured forward/backward/update was not executed on CUDA tensors.")
        training_seconds += time.perf_counter() - train_tick
        global_step += 1
        next_job_idx += 1
        steps_since_ckpt += 1

        requested = (run_dir / "control.request").is_file()
        request = (run_dir / "control.request").read_text(encoding="utf-8").strip() if requested else ""
        checkpoint_requested = (run_dir / "checkpoint.request").is_file()
        wall_expired = max_wall > 0 and (time.perf_counter() - started) >= max_wall
        if (steps_since_ckpt >= int(cfg["checkpoint_frequency_steps"]) or request in ("pause", "stop")
                or checkpoint_requested or wall_expired):
            state = _fit_checkpoint_payload(name, config_hash_value, model, optimizer, scheduler, epoch,
                                            next_job_idx, global_step, best_ler, best_loss, best_epoch,
                                            patience_count, best_state, history, model_seed)
            checkpoint_tick = time.perf_counter()
            _save_fit_state(checkpoint_path, state)
            checkpoint_seconds += time.perf_counter() - checkpoint_tick
            steps_since_ckpt = 0
            if checkpoint_requested:
                (run_dir / "checkpoint.request").unlink(missing_ok=True)
            if event_callback:
                event_callback({"type": "progress", "status": "running", "candidate": name,
                                "epoch": epoch + 1, "global_step": global_step,
                                "total_training_shots": sum(int(v) for v in train_counts.values()),
                                "training_samples_processed": int(sum(int(v) for v in train_counts.values()) *
                                                                       next_job_idx / max(1, len(jobs))),
                                "training_passes_completed": epoch,
                                "device": str(device), "cuda_training_verified": device.type == "cuda",
                                "cuda_device_name": torch.cuda.get_device_name(0) if device.type == "cuda" else None,
                                "python_executable": sys.executable, "gpu_telemetry": device_snapshot()})
        if request in ("pause", "stop") or wall_expired:
            if requested:
                (run_dir / "control.request").unlink(missing_ok=True)
            atomic_json({"status": "paused", "candidate": name, "epoch": epoch,
                         "next_job_index": next_job_idx, "global_step": global_step,
                         "wall_limit_hit": bool(wall_expired), "resume_command": "rerun with --resume"},
                        run_dir / "structured_progress.json")
            return {"status": "paused", "candidate": name, "global_step": global_step,
                    "elapsed_seconds": time.perf_counter() - started,
                    "timings": {"stim_generation_seconds": sim_seconds, "training_seconds": training_seconds,
                                "validation_seconds": validation_total_seconds,
                                "checkpoint_seconds": checkpoint_seconds},
                    "cuda_training_verified": cuda_training_verified}

    if best_state is None:
        # This is only possible if a run was paused before the first validation.
        raise RuntimeError(f"{name} ended without a best-validation snapshot.")
    model.load_state_dict(best_state)
    best_path = run_dir / "best_models" / f"{name}.pt"
    atomic_torch({"candidate": name, "spec": spec, "best_epoch": best_epoch,
                  "validation_ler_at_0_5": best_ler, "validation_bce": best_loss,
                  "state_dict": best_state, "model_seed": model_seed,
                  "positive_weight": pos_weight_value,
                  "config_sha256": config_hash_value}, best_path)
    return {"status": "completed", "candidate": name, "spec": spec, "best_epoch": best_epoch,
            "best_validation_ler_at_0_5": best_ler, "best_validation_bce": best_loss,
            "positive_weight": pos_weight_value, "positive_weight_source": "training split only" if pos_weight_value is not None else None,
            "history": history, "model_path": str(best_path),
            "global_steps": global_step, "elapsed_seconds": time.perf_counter() - started,
            "training_shot_presentations": len(history) * sum(int(v) for v in train_counts.values()),
            "validation_shot_presentations": len(history) * sum(int(v) for v in val_counts.values()),
            "cuda_training_verified": cuda_training_verified,
            "timings": {"stim_generation_and_matching_decode_seconds": sim_seconds, "training_seconds": training_seconds,
                        "validation_seconds": validation_total_seconds,
                        "checkpoint_seconds": checkpoint_seconds}}


def _fit_checkpoint_payload(name, config_hash, model, optimizer, scheduler, epoch, next_job_idx,
                            global_step, best_ler, best_loss, best_epoch, patience_count,
                            best_state, history, model_seed):
    return {"schema_version": 1, "candidate": name, "config_sha256": config_hash,
            "model_state": model.state_dict(), "optimizer_state": optimizer.state_dict(),
            "scheduler_state": scheduler.state_dict(), "epoch": int(epoch),
            "next_job_idx": int(next_job_idx), "global_step": int(global_step),
            "best_validation_ler": best_ler, "best_validation_loss": best_loss,
            "best_epoch": best_epoch, "patience_count": int(patience_count),
            "best_model_state": best_state, "history": history, "model_seed": int(model_seed),
            "rng_state": rng_state(), "saved_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def _checkpoint_positive_weight(model_artifact: dict, fit_results: dict, name: str) -> float | None:
    if "positive_weight" in model_artifact:
        return model_artifact["positive_weight"]
    return fit_results.get(name, {}).get("positive_weight")


def _clone_best_models(cfg: dict, coords: dict, run_dir: Path, device: torch.device) -> dict:
    models = {}
    fit_results_path = run_dir / "candidate_results.json"
    fit_results = json.loads(fit_results_path.read_text(encoding="utf-8")) if fit_results_path.is_file() else {}
    for name in cfg["candidates"]:
        p = run_dir / "best_models" / f"{name}.pt"
        if not p.is_file():
            raise RuntimeError(f"Missing best-validation model weights: {p.name}")
        data = torch.load(p, map_location=device, weights_only=False)
        model = make_model(data["spec"], coords).to(device)
        model.load_state_dict(data["state_dict"])
        model.eval()
        # Backward-compatible recovery for historical checkpoints whose fit
        # metadata stored the weight only in candidate_results.json.
        data["positive_weight"] = _checkpoint_positive_weight(data, fit_results, name)
        models[name] = (model, data["spec"], data)
    return models


def _empty_accumulator() -> dict:
    return {"n": 0, "target_positive_count": 0,
            "confusion_by_threshold": {str(t): {"tn": 0, "fp": 0, "fn": 0, "tp": 0}
                                                for t in (0.25, 0.5, 0.75)},
            "brier_sum": 0.0, "logloss_sum": 0.0, "ece_bins": [[0, 0.0, 0.0] for _ in range(10)],
            "error_count_by_threshold": {str(t): 0 for t in (0.25, 0.5, 0.75)}}


def _accumulate(acc: dict, target: np.ndarray, probabilities: np.ndarray, final_predictions: dict[float, np.ndarray] | None = None):
    y = np.asarray(target, dtype=np.uint8)
    p = np.clip(np.asarray(probabilities, dtype=np.float64), 1e-7, 1 - 1e-7)
    acc["n"] += len(y)
    acc["target_positive_count"] += int(y.sum())
    acc["brier_sum"] += float(np.square(p - y).sum())
    acc["logloss_sum"] += float((-(y * np.log(p) + (1 - y) * np.log(1 - p))).sum())
    bins = np.minimum((p * 10).astype(int), 9)
    for b in range(10):
        m = bins == b
        if np.any(m):
            acc["ece_bins"][b][0] += int(m.sum())
            acc["ece_bins"][b][1] += float(p[m].sum())
            acc["ece_bins"][b][2] += float(y[m].sum())
    for threshold in (0.25, 0.5, 0.75):
        predicted = (p >= threshold).astype(np.uint8) if final_predictions is None else final_predictions[threshold]
        c = acc["confusion_by_threshold"][str(threshold)]
        c["tn"] += int(np.count_nonzero((y == 0) & (predicted == 0)))
        c["fp"] += int(np.count_nonzero((y == 0) & (predicted == 1)))
        c["fn"] += int(np.count_nonzero((y == 1) & (predicted == 0)))
        c["tp"] += int(np.count_nonzero((y == 1) & (predicted == 1)))


def _finish_accumulator(acc: dict, is_residual: bool) -> dict:
    n = max(1, acc["n"])
    ece = 0.0
    for count, psum, ysum in acc["ece_bins"]:
        if count:
            ece += count / n * abs(psum / count - ysum / count)
    result = {"n": acc["n"], "target_positive_count": acc["target_positive_count"],
              "target_positive_rate": acc["target_positive_count"] / n,
              "brier_score": acc["brier_sum"] / n, "log_loss": acc["logloss_sum"] / n,
              "ece_10_equal_width_bins": ece, "thresholds": {}}
    for threshold, c in acc["confusion_by_threshold"].items():
        tp, fp, fn, tn = c["tp"], c["fp"], c["fn"], c["tn"]
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        result["thresholds"][threshold] = {**c, "target_prediction_error_rate": (fp + fn) / n,
                                           "predicted_positive_count": tp + fp,
                                           "predicted_positive_rate": (tp + fp) / n,
                                           "positive_precision": precision, "positive_recall": recall}
    return result


def evaluate_all(cfg: dict, envs: dict, inventory: dict, coords: dict, run_dir: Path,
                 device: torch.device, write_evidence: bool = True) -> dict:
    models = _clone_best_models(cfg, coords, run_dir, device)
    accum = {name: {r: _empty_accumulator() for r in REGIMES} for name in cfg["candidates"]}
    comparator_errors = {"identity": {r: 0 for r in REGIMES}, "pymatching": {r: 0 for r in REGIMES}}
    paired = {name: {r: {str(t): {"candidate_only": 0, "fixed_only": 0,
                                    "prediction_disagreements_with_pymatching": 0}
                                  for t in (0.25, 0.5, 0.75)} for r in REGIMES}
              for name in cfg["candidates"]}
    selected_thresholds: dict[str, float] = {}
    # First pass caches only scalar stats. It never accumulates the whole split.
    for regime in REGIMES:
        val_count = int(cfg["validation_shots_by_regime"][regime])
        for batch_index, start in enumerate(range(0, val_count, int(cfg["batch_size"]))):
            size = min(int(cfg["batch_size"]), val_count - start)
            d, y, fixed = stream_batch(envs, inventory, "validation", regime, batch_index, size)
            comparator_errors["identity"][regime] += int(np.count_nonzero(y))
            comparator_errors["pymatching"][regime] += int(np.count_nonzero(fixed ^ y))
            outputs: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
            for name, (model, spec, _) in models.items():
                p, _ = prediction_for(model, spec, d, fixed, device, 0.5,
                                      positive_weight=models[name][2].get("positive_weight"))
                target = np.bitwise_xor(fixed, y) if spec["kind"] == "residual" else y
                final_probs = p
                if spec["kind"] == "residual":
                    # For residual calibration reports, probabilities are for
                    # the correction target; final LER uses parity with fixed.
                    pass
                _accumulate(accum[name][regime], target, p)
                outputs[name] = (p, target, np.asarray(y, dtype=np.uint8))
                for threshold in (0.25, 0.5, 0.75):
                    pp = (p >= threshold).astype(np.uint8)
                    final_pred = np.bitwise_xor(fixed, pp) if spec["kind"] == "residual" else pp
                    wrong = final_pred ^ y
                    key = str(threshold)
                    c = accum[name][regime]["error_count_by_threshold"]
                    c[key] += int(wrong.sum())
                    fixed_wrong = fixed ^ y
                    paired[name][regime][key]["candidate_only"] += int(np.count_nonzero((wrong == 1) & (fixed_wrong == 0)))
                    paired[name][regime][key]["fixed_only"] += int(np.count_nonzero((wrong == 0) & (fixed_wrong == 1)))
                    paired[name][regime][key]["prediction_disagreements_with_pymatching"] += int(np.count_nonzero(final_pred != fixed))
            if write_evidence:
                evidence_dir = run_dir / "validation_evidence"
                evidence_dir.mkdir(parents=True, exist_ok=True)
                pred05 = {}
                prob = {}
                for name, (model, spec, _) in models.items():
                    p = outputs[name][0]
                    pred = (p >= 0.5).astype(np.uint8)
                    if spec["kind"] == "residual":
                        pred = np.bitwise_xor(fixed, pred)
                    pred05[name] = pred
                    prob[name] = p
                npzpath = evidence_dir / f"{regime}_batch_{batch_index:05d}.npz"
                temp = npzpath.with_suffix(".npz.tmp")
                payload = {"detectors": d, "observable": y, "pymatching": fixed,
                           "identity": np.zeros_like(y)}
                for name in cfg["candidates"]:
                    payload[f"prediction__{name}"] = pred05[name]
                    payload[f"probability__{name}"] = prob[name]
                with temp.open("wb") as f:
                    np.savez_compressed(f, **payload)
                os.replace(temp, npzpath)

    # Threshold selection occurs on validation only. For residual candidates,
    # threshold is evaluated on correction probability, then applied by XOR.
    result = {"comparators": {}, "candidates": {}, "paired_vs_pymatching": paired,
              "validation_split_only": True}
    equal_ler_by_threshold: dict[str, dict[str, float]] = {}
    for name in cfg["candidates"]:
        by_regime = {}
        threshold_lers = {str(t): [] for t in (0.25, 0.5, 0.75)}
        for regime in REGIMES:
            spec = candidate_spec(name)
            target_positive = None
            if spec["kind"] == "residual":
                # Error-prevalence summary refers to the actual correction target.
                target_positive = None
            m = _finish_accumulator(accum[name][regime], is_residual=spec["kind"] == "residual")
            for t in (0.25, 0.5, 0.75):
                threshold_lers[str(t)].append(accum[name][regime]["error_count_by_threshold"][str(t)] /
                                              max(1, accum[name][regime]["n"]))
            by_regime[regime] = m
            for threshold in (0.25, 0.5, 0.75):
                m["thresholds"][str(threshold)]["logical_errors"] = accum[name][regime]["error_count_by_threshold"][str(threshold)]
                m["thresholds"][str(threshold)]["logical_ler"] = (accum[name][regime]["error_count_by_threshold"][str(threshold)] /
                                                                      max(1, accum[name][regime]["n"]))
        avg = {t: float(np.mean(values)) for t, values in threshold_lers.items()}
        chosen = min(avg, key=lambda t: (avg[t], 0 if t == "0.5" else 1, float(t)))
        selected_thresholds[name] = float(chosen)
        result["candidates"][name] = {"per_regime": by_regime,
                                      "equal_regime_ler_by_threshold": avg,
                                      "selected_threshold_on_validation": float(chosen),
                                      "selected_equal_regime_ler": avg[chosen],
                                      "total_validation_shots": sum(int(cfg["validation_shots_by_regime"][r]) for r in REGIMES),
                                      "total_logical_errors_at_selected_threshold": sum(
                                          int(accum[name][r]["error_count_by_threshold"][chosen]) for r in REGIMES),
                                      "best_checkpoint_epoch": models[name][2]["best_epoch"],
                                      "paired_discordances_vs_pymatching": paired[name]}
    for comparer in ("identity", "pymatching"):
        per = {}
        rates = []
        for regime in REGIMES:
            n = int(cfg["validation_shots_by_regime"][regime])
            errors = comparator_errors[comparer][regime]
            per[regime] = {"n": n, "errors": errors, "ler": errors / n}
            rates.append(errors / n)
        result["comparators"][comparer] = {"per_regime": per, "equal_regime_ler": float(np.mean(rates))}
    result["selected_candidate"] = min(result["candidates"], key=lambda name:
                                       (result["candidates"][name]["selected_equal_regime_ler"],
                                        name))
    result["selected_thresholds"] = selected_thresholds
    result["selection_rule"] = "minimize equal-regime validation LER among 0.25/0.5/0.75; ties prefer 0.5 then lower threshold; candidate ties lexicographic. Validation is development-only and selection evidence, not independent evaluation."
    return result


def _resolve_run_config(raw: dict, mode: str, run_dir: Path, prior_allocations: list[dict] | None = None) -> tuple[dict, dict]:
    if mode == "official_100k":
        base, inventory = load_prepared_freeze()
        streams = inventory["streams"]
        # Re-screen every stream, including reserved test ranges, against any
        # dashboard allocations created since the original protocol freeze.
        screen = screen_inventory(inventory, prior_allocations, candidate_count=6)
        if not screen["passed"]:
            raise RuntimeError(f"Frozen 100K seed allocation failed re-screening: {screen['collisions'][:5]}")
        candidate_seeds = screen["candidate_model_rng_seeds"]
        inventory = dict(inventory)
        inventory["model_seeds"] = candidate_seeds
        inventory["diagnostic_seeds"] = screen["diagnostic_seeds"]
        train_counts = {r: int(base["shot_allocation"]["train"][r]) for r in REGIMES}
        val_counts = {r: int(base["shot_allocation"]["validation"][r]) for r in REGIMES}
        # Official train/validation roots are kept exactly as frozen. Test roots
        # are screened but never passed to stream_batch.
        cfg = {"experiment_id": base["experiment_id"], "mode": mode,
               "training_shots_by_regime": train_counts, "validation_shots_by_regime": val_counts,
               "batch_size": int(base["batch_size"]), "candidates": ["direct_mlp", "residual_mlp",
                   "structured_ch8_unweighted", "structured_ch8_weighted",
                   "structured_ch16_unweighted", "structured_ch16_weighted"],
               "learning_rate": 0.001, "weight_decay": 0.0001, "max_epochs": 2,
               "early_stopping_patience": 1, "checkpoint_frequency_steps": 8,
               "device": raw.get("device", "auto"),
               "max_wall_seconds_per_invocation": float(raw.get("max_wall_seconds_per_invocation", 0)),
               "train_seed_inventory": inventory,
               "reserved_test_seeds_sha256": hashlib.sha256(json.dumps([s for s in streams if s["split"] == "test"], sort_keys=True).encode()).hexdigest(),
               "test_access": "strictly disabled in this worker"}
        cfg["seed_screen"] = screen
        return cfg, inventory
    if mode == "development":
        cfg = dict(raw)
        train_counts = {r: int(cfg["training_shots_by_regime"][r]) for r in REGIMES}
        val_counts = {r: int(cfg["validation_shots_by_regime"][r]) for r in REGIMES}
        if not cfg.get("candidates"):
            raise ValueError("Development config must specify candidates.")
        inv = cfg["seed_inventory"]
        if not inv.get("passed"):
            raise ValueError("Development seed inventory failed collision screening.")
        screen = screen_inventory(inv, prior_allocations, candidate_count=len(cfg["candidates"]))
        if not screen["passed"]:
            raise ValueError(f"Development inventory failed current seed re-screening: {screen['collisions'][:5]}")
        cfg["seed_screen"] = screen
        return cfg, inv
    raise ValueError("mode must be 'development' or 'official_100k'.")


def run(config_path: Path, run_dir: Path, resume: bool = False, mode_override: str | None = None,
        prior_allocations: list[dict] | None = None, event_callback=None) -> dict:
    total_started = time.perf_counter()
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    mode = mode_override or raw.get("mode", "development")
    cfg, inventory = _resolve_run_config(raw, mode, run_dir, prior_allocations)
    cfg["training_shots_by_regime"] = {r: int(cfg["training_shots_by_regime"][r]) for r in REGIMES}
    cfg["validation_shots_by_regime"] = {r: int(cfg["validation_shots_by_regime"][r]) for r in REGIMES}
    if sum(cfg["training_shots_by_regime"].values()) <= 0 or sum(cfg["validation_shots_by_regime"].values()) <= 0:
        raise ValueError("Training and validation allocations must be positive.")
    if cfg["max_epochs"] < 1 or cfg["max_epochs"] > 20:
        raise ValueError("max_epochs must be between 1 and 20.")
    if cfg["batch_size"] < 32 or cfg["batch_size"] > 4096:
        raise ValueError("batch_size must be between 32 and 4096.")
    for name in cfg["candidates"]:
        candidate_spec(name)
    run_dir.mkdir(parents=True, exist_ok=True)
    config_hash_value = config_hash(cfg)
    config_path_out = run_dir / "structured_resolved_config.json"
    inventory_path_out = run_dir / "structured_seed_inventory.json"
    source_hashes = {name: sha256_file(HERE / name) for name in
                     ("structured_training.py", "structured_decoder.py", "simulator.py", "models.py", "seed_protocol.py")}
    freeze_path = run_dir / "structured_freeze.json"
    freeze_payload = {"status": "training protocol frozen before sampling; test stream excluded",
                      "config_sha256": config_hash_value, "source_sha256": source_hashes,
                      "prepared_protocol_freeze_sha256": sha256_file(PROTOCOL_FREEZE),
                      "seed_inventory_sha256": None}
    if resume and freeze_path.is_file():
        old_freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
        if old_freeze.get("config_sha256") != config_hash_value or old_freeze.get("source_sha256") != source_hashes:
            raise RuntimeError("Resume blocked: frozen structured source/config hashes changed.")
        if not config_path_out.is_file() or not inventory_path_out.is_file():
            raise RuntimeError("Resume blocked: frozen structured config or seed inventory is missing.")
        saved_inventory = json.loads(inventory_path_out.read_text(encoding="utf-8"))
        if saved_inventory != inventory:
            raise RuntimeError("Resume blocked: the frozen seed inventory differs from the requested allocation.")
        if sha256_file(inventory_path_out) != old_freeze.get("seed_inventory_sha256"):
            raise RuntimeError("Resume blocked: frozen seed inventory hash mismatch.")
    elif freeze_path.exists():
        raise RuntimeError("Run directory already has a freeze record; use --resume or choose a fresh directory.")
    else:
        if any(run_dir.iterdir()):
            allowed_preexisting = {"config.json", "seed_inventory.json"}
            unexpected = [p.name for p in run_dir.iterdir() if p.name not in allowed_preexisting]
            if unexpected:
                raise RuntimeError(f"Run directory contains preexisting artifacts: {unexpected[:5]}")
        atomic_json(cfg, config_path_out)
        atomic_json(inventory, inventory_path_out)
        atomic_json(cfg.get("seed_screen", {"passed": True}), run_dir / "structured_seed_screen.json")
        freeze_payload["seed_inventory_sha256"] = sha256_file(inventory_path_out)
        atomic_json(freeze_payload, freeze_path)

    requested_device = str(cfg.get("device", "auto"))
    if requested_device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable in this Python environment.")
    device = torch.device("cuda" if requested_device == "cuda" or (requested_device == "auto" and torch.cuda.is_available()) else "cpu")
    if device.type == "cuda":
        torch.cuda.set_device(0)
        torch.cuda.reset_peak_memory_stats(0)
    resource_monitor = ResourceMonitor(device).start()
    prepare_started = time.perf_counter()
    envs, coords, fingerprints = prepare_regimes(cfg, inventory["diagnostic_seeds"])
    prepare_seconds = time.perf_counter() - prepare_started
    train_counts = cfg["training_shots_by_regime"]
    val_counts = cfg["validation_shots_by_regime"]
    prevalence_path = run_dir / "training_prevalence.json"
    if prevalence_path.is_file():
        prevalence = json.loads(prevalence_path.read_text(encoding="utf-8"))
    else:
        t0 = time.perf_counter()
        prevalence = _training_positive_counts(envs, inventory, train_counts, int(cfg["batch_size"]))
        prevalence["scan_seconds"] = time.perf_counter() - t0
        atomic_json(prevalence, prevalence_path)
    results_path = run_dir / "candidate_results.json"
    results = json.loads(results_path.read_text(encoding="utf-8")) if resume and results_path.is_file() else {}
    fit_started = time.perf_counter()
    for candidate in cfg["candidates"]:
        if candidate in results and results[candidate].get("status") == "completed":
            continue
        configured_wall_limit = float(cfg.get("max_wall_seconds_per_invocation", 0))
        wall_remaining = None if configured_wall_limit <= 0 else max(
            0.0, configured_wall_limit - (time.perf_counter() - total_started))
        if wall_remaining is not None and wall_remaining <= 0:
            usage = resource_monitor.finish()
            atomic_json({"status": "paused", "candidate": candidate,
                         "completed_candidates": [k for k, v in results.items() if v.get("status") == "completed"],
                         "wall_limit_hit": True, "resource_usage": usage,
                         "resume_command": "rerun with --resume"},
                        run_dir / "structured_progress.json")
            return {"status": "paused", "results": results, "resource_usage": usage}
        fit = train_candidate(candidate, cfg, envs, coords, inventory, train_counts, val_counts,
                              prevalence, run_dir, device, resume=resume,
                              event_callback=event_callback, wall_seconds_remaining=wall_remaining)
        results[candidate] = fit
        atomic_json(results, results_path)
        if fit["status"] == "paused":
            usage = resource_monitor.finish()
            atomic_json({"status": "paused", "candidate_results": results,
                         "completed_candidates": [k for k, v in results.items() if v.get("status") == "completed"],
                         "resource_usage": usage},
                        run_dir / "structured_progress.json")
            return {"status": "paused", "results": results, "resource_usage": usage}

    final_validation_started = time.perf_counter()
    final = evaluate_all(cfg, envs, inventory, coords, run_dir, device, write_evidence=True)
    final_validation_seconds = time.perf_counter() - final_validation_started
    final["training_only_split_notice"] = "The report contains development validation metrics. No test samples were generated or accessed."
    final["training_prevalence"] = prevalence
    final["candidate_fits"] = results
    final["circuit_validation"] = fingerprints
    final["device"] = str(device)
    final["cuda_training_verified"] = bool(device.type == "cuda" and any(
        fit.get("cuda_training_verified", False) for fit in results.values()))
    final["cuda_device_name"] = torch.cuda.get_device_name(0) if device.type == "cuda" else None
    final["python_executable"] = sys.executable
    final["software"] = {"torch": torch.__version__, "numpy": np.__version__}
    final["timing_seconds"] = {"prepare_circuits_and_validation": prepare_seconds,
                               "positive_prevalence_scan": prevalence.get("scan_seconds", 0.0),
                               "candidate_fits": time.perf_counter() - fit_started - final_validation_seconds,
                               "final_validation_and_evidence": final_validation_seconds,
                               "end_to_end_total": time.perf_counter() - total_started}
    train_unique = sum(train_counts.values())
    validation_unique = sum(val_counts.values())
    train_presentations = train_unique + sum(int(v.get("training_shot_presentations", 0)) for v in results.values())
    validation_presentations = sum(int(v.get("validation_shot_presentations", 0)) for v in results.values()) + validation_unique
    all_presentations = train_presentations + validation_presentations
    elapsed_total = max(1e-9, final["timing_seconds"]["end_to_end_total"])
    final["throughput"] = {"unique_training_shots": train_unique, "unique_validation_shots": validation_unique,
                           "training_shot_presentations_including_prevalence_scan": train_presentations,
                           "validation_shot_presentations_including_final_evidence": validation_presentations,
                           "total_shot_presentations": all_presentations,
                           "end_to_end_shot_presentations_per_second": all_presentations / elapsed_total}
    fit_timing_totals = {key: sum(float(v.get("timings", {}).get(key, 0.0)) for v in results.values())
                         for key in ("stim_generation_and_matching_decode_seconds", "training_seconds",
                                     "validation_seconds", "checkpoint_seconds")}
    final["fit_timing_totals_seconds"] = fit_timing_totals
    final["resource_usage"] = resource_monitor.finish()
    final["gpu_peak_allocated_bytes"] = final["resource_usage"]["gpu_peak_allocated_bytes"]
    final["gpu_peak_reserved_bytes"] = final["resource_usage"]["gpu_peak_reserved_bytes"]
    atomic_json(final, run_dir / "structured_development_results.json")
    manifest = {"files": {}, "status": "complete; test stream not sampled"}
    for path in sorted(run_dir.rglob("*")):
        if path.is_file() and path.name not in {"structured_manifest.json"}:
            manifest["files"][str(path.relative_to(run_dir))] = sha256_file(path)
    atomic_json(manifest, run_dir / "structured_manifest.json")
    return final


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Streaming structured Q-SHIFT trainer; test split is disabled.")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--mode", choices=("development", "official_100k"))
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    run_id = run_dir.name
    def emit(event: dict) -> None:
        event.setdefault("run_id", run_id)
        print(json.dumps(event, separators=(",", ":"), allow_nan=False, default=str), flush=True)
    try:
        from manager import WorkerManager
        prior = WorkerManager().allocations(exclude_run_id=run_id)
        emit({"type": "progress", "status": "running", "phase": "preparing",
              "test_access": "disabled", "python_executable": sys.executable,
              "device": "cuda" if torch.cuda.is_available() else "cpu",
              "cuda_training_verified": False, "gpu_telemetry": device_snapshot()})
        result = run(args.config.resolve(), run_dir, args.resume, args.mode,
                     prior_allocations=prior, event_callback=emit)
        if result.get("status") == "paused":
            emit({"type": "paused", "status": "paused", "summary": result})
        else:
            total_n = sum(int(result["candidates"][result["selected_candidate"]]["per_regime"][r]["n"])
                          for r in REGIMES)
            metrics = {}
            for key, comparator in (("identity_no_decode", "identity"), ("pymatching", "pymatching")):
                errors = sum(int(result["comparators"][comparator]["per_regime"][r]["errors"]) for r in REGIMES)
                metrics[key] = {"errors": errors, "ler": errors / max(1, total_n)}
            for candidate_name, metric_key in (("direct_mlp", "direct_neural"),
                                                ("residual_mlp", "pymatching_neural_residual")):
                if candidate_name in result["candidates"]:
                    c = result["candidates"][candidate_name]
                    threshold = str(c["selected_threshold_on_validation"])
                    errors = sum(int(c["per_regime"][r]["thresholds"][threshold]["logical_errors"])
                                 for r in REGIMES)
                    metrics[metric_key] = {"errors": errors, "ler": errors / max(1, total_n),
                                           "threshold_selected_on_validation": float(threshold)}
            structured_names = [name for name in result["candidates"] if name.startswith("structured_")]
            if structured_names:
                best_structured = min(structured_names, key=lambda name:
                                      (result["candidates"][name]["selected_equal_regime_ler"], name))
                c = result["candidates"][best_structured]
                threshold = str(c["selected_threshold_on_validation"])
                errors = sum(int(c["per_regime"][r]["thresholds"][threshold]["logical_errors"])
                             for r in REGIMES)
                metrics["structured_neural"] = {"errors": errors, "ler": errors / max(1, total_n),
                                                 "candidate": best_structured,
                                                 "threshold_selected_on_validation": float(threshold)}
            emit({"type": "completed", "status": "completed",
                  "metrics": metrics,
                  "summary": {"selected_candidate": result["selected_candidate"],
                              "metrics": metrics,
                              "validation_equal_regime_ler": result["candidates"][result["selected_candidate"]]["selected_equal_regime_ler"],
                              "evaluation_split": "development validation only; final test was not sampled",
                              "device": result["device"],
                              "cuda_training_verified": result["cuda_training_verified"],
                              "cuda_device_name": result["cuda_device_name"],
                              "python_executable": result["python_executable"],
                              "results_path": str(run_dir / "structured_development_results.json"),
                              "validation_shots": total_n}})
    except Exception as exc:
        detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        emit({"type": "failed", "status": "failed", "error": str(exc), "traceback": detail[-16000:]})
        raise


if __name__ == "__main__":
    main()
