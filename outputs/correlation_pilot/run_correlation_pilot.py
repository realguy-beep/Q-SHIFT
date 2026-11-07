"""Execute the frozen 720,000-shot paired correlation-matching pilot."""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pymatching
import stim

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CFG = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
PHASE2B = (HERE / CFG["phase2b_source_dir"]).resolve()
sys.path.insert(0, str(PHASE2B))
noise_model = importlib.import_module("noise_model")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def verify_freeze() -> dict:
    freeze_path = HERE / "PRETEST_FREEZE.json"
    if not freeze_path.is_file():
        raise RuntimeError("PRETEST_FREEZE.json is missing; no full sampling is permitted")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze.get("status") != "FROZEN_BEFORE_FULL_SAMPLING":
        raise RuntimeError("Pre-test freeze status is not active")
    changed = []
    for rel, expected in freeze["sha256"].items():
        path = ROOT / Path(rel)
        if not path.is_file() or sha256_file(path) != expected:
            changed.append(rel)
    if changed:
        raise RuntimeError(f"Frozen input hash mismatch: {changed}")
    if freeze["protocol_decisions"]["primary_margin_absolute_ler"] != 0.0002:
        raise RuntimeError("Frozen practical margin does not equal 0.0002")
    return freeze


def make_models():
    models = {}
    build_start = time.perf_counter()
    for basis in CFG["memory_bases"]:
        for index, regime in enumerate(CFG["regimes"]):
            circuit = noise_model.build_circuit(
                basis, regime, distance=CFG["distance"], rounds=CFG["rounds"],
                gate_p=CFG["gate_fault_probability_1q"],
                measurement_p=CFG["measurement_flip_probability"], bias_ratio=CFG["bias_ratio"])
            dem = circuit.detector_error_model(**CFG["dem_conversion"])
            if dem.num_detectors != 40 or dem.num_observables != 1:
                raise RuntimeError(f"Unexpected DEM shape for {basis}/{regime}")
            dem_sha = hashlib.sha256(str(dem).encode("utf-8")).hexdigest()
            matchers = {}
            for correlated in (False, True):
                matcher = pymatching.Matching.from_detector_error_model(
                    dem, enable_correlations=correlated)
                if matcher.num_detectors != 40 or matcher.num_fault_ids != 1:
                    raise RuntimeError(f"Matcher shape/fault-ID failure for {basis}/{regime}/{correlated}")
                matchers[correlated] = matcher
            # Same DEM input must produce the same graph and weights in both modes.
            def sig(m):
                return sorted(((-1 if u is None else int(u)), (-1 if v is None else int(v)),
                               float(a["weight"]).hex(),
                               tuple(sorted(int(q) for q in a.get("fault_ids", set()))))
                              for u, v, a in m.edges())
            if sig(matchers[False]) != sig(matchers[True]):
                raise RuntimeError(f"Graph/weight mismatch for correlation toggle: {basis}/{regime}")
            models[(basis, index)] = {
                "dem_sha256": dem_sha, "correlation_off": matchers[False],
                "correlation_on": matchers[True]
            }
    return models, time.perf_counter() - build_start


def atomic_npz(path: Path, **arrays) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("wb") as f:
        np.savez_compressed(f, **arrays)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def checkpoint_path(stratum_index: int, root_index: int) -> Path:
    return HERE / "checkpoints" / f"stratum_{stratum_index:02d}_root_{root_index:02d}.npz"


def check_existing_checkpoint(path: Path, stratum_index: int, root_index: int, seed: int) -> None:
    with np.load(path, allow_pickle=False) as z:
        if int(z["stratum_index"]) != stratum_index or int(z["root_index"]) != root_index:
            raise RuntimeError(f"Checkpoint metadata does not match its path: {path}")
        if int(z["root_seed"]) != seed:
            raise RuntimeError(f"Checkpoint seed mismatch: {path}")
        if z["detectors"].shape != (CFG["shots_per_root"], 5):
            raise RuntimeError(f"Checkpoint detector schema mismatch: {path}")
        if z["observable"].shape != (CFG["shots_per_root"],):
            raise RuntimeError(f"Checkpoint observable schema mismatch: {path}")
        if z["predictions"].shape != (4, CFG["shots_per_root"]):
            raise RuntimeError(f"Checkpoint prediction schema mismatch: {path}")


def run() -> dict:
    freeze = verify_freeze()
    preflight = json.loads((HERE / "SMOKE_PREFLIGHT.json").read_text(encoding="utf-8"))
    if preflight.get("status") != "PASS" or not preflight.get("seed_collision_free"):
        raise RuntimeError("Smoke preflight is not passing")
    if preflight["planned_total_shots"] != 720000:
        raise RuntimeError("Preflight shot count differs from frozen target")

    try:
        import psutil
        process = psutil.Process()
        rss_start = int(process.memory_info().rss)
    except Exception:
        process = None
        rss_start = None

    models, model_build_seconds = make_models()
    rss_after_models = int(process.memory_info().rss) if process is not None else None
    started = time.perf_counter()
    expected_total = len(CFG["stratum_order"]) * CFG["roots_per_stratum"]
    completed = 0
    root_records = []
    inference_seconds_by_arm = {name: 0.0 for name in CFG["decoder_arms"]}
    sampler_seconds = 0.0
    peak_rss = max(x for x in (rss_start, rss_after_models) if x is not None) if process else None

    for si, label in enumerate(CFG["stratum_order"]):
        basis, regime = label.split("_", 1)
        regime_index = CFG["regimes"].index(regime)
        fixed_index = int(CFG["pooled_fixed_model_index_by_basis"][basis])
        circuit = noise_model.build_circuit(
            basis, regime, distance=CFG["distance"], rounds=CFG["rounds"],
            gate_p=CFG["gate_fault_probability_1q"],
            measurement_p=CFG["measurement_flip_probability"], bias_ratio=CFG["bias_ratio"])
        circuit_sha = hashlib.sha256(str(circuit).encode("utf-8")).hexdigest()
        for ri in range(CFG["roots_per_stratum"]):
            seed = int(CFG["seed_allocation"]["root_seed_base"] + 100 * si + ri)
            path = checkpoint_path(si, ri)
            if path.exists():
                check_existing_checkpoint(path, si, ri, seed)
                root_records.append({"stratum_index": si, "stratum": label, "root_index": ri,
                                     "seed": seed, "checkpoint": path.relative_to(HERE).as_posix(),
                                     "status": "resumed_existing_schema_validated"})
                completed += 1
                continue

            t0 = time.perf_counter()
            detectors, observables = circuit.compile_detector_sampler(seed=seed).sample(
                CFG["shots_per_root"], separate_observables=True)
            sampler_seconds += time.perf_counter() - t0
            detectors = np.asarray(detectors, dtype=np.uint8)
            observables = np.asarray(observables, dtype=np.uint8)
            if detectors.shape != (CFG["shots_per_root"], 40) or observables.shape != (CFG["shots_per_root"], 1):
                raise RuntimeError(f"Sampling shape mismatch at {label}/root {ri}")
            if not np.isin(detectors, [0, 1]).all() or not np.isin(observables, [0, 1]).all():
                raise RuntimeError(f"Nonbinary sample data at {label}/root {ri}")

            fixed = models[(basis, fixed_index)]
            regime_model = models[(basis, regime_index)]
            calls = [
                ("pooled_fixed_uncorrelated", fixed["correlation_off"], False),
                ("pooled_fixed_correlated", fixed["correlation_on"], True),
                ("regime_informed_uncorrelated", regime_model["correlation_off"], False),
                ("regime_informed_correlated", regime_model["correlation_on"], True),
            ]
            predictions = []
            root_decode_times = []
            for name, matcher, correlated in calls:
                td = time.perf_counter()
                pred = np.asarray(matcher.decode_batch(detectors, enable_correlations=correlated), dtype=np.uint8)
                elapsed = time.perf_counter() - td
                if pred.shape == (CFG["shots_per_root"], 1):
                    pred = pred[:, 0]
                if pred.shape != (CFG["shots_per_root"],) or not np.isin(pred, [0, 1]).all():
                    raise RuntimeError(f"Invalid decoder output from {name} at {label}/root {ri}")
                predictions.append(pred)
                root_decode_times.append(elapsed)
                inference_seconds_by_arm[name] += elapsed
            prediction_array = np.stack(predictions, axis=0).astype(np.uint8)
            if not np.array_equal(prediction_array[0], prediction_array[2]) and fixed_index == regime_index:
                raise RuntimeError("Same-model arm predictions differ unexpectedly when correlation modes match")
            packed = np.packbits(detectors, axis=1, bitorder="little")
            atomic_npz(
                path,
                schema_version=np.int16(1),
                detectors=packed,
                observable=observables[:, 0].astype(np.uint8),
                predictions=prediction_array,
                root_seed=np.int64(seed),
                stratum_index=np.int16(si),
                root_index=np.int16(ri),
                basis=np.asarray(basis),
                regime=np.asarray(regime),
                fixed_decoder_index=np.int16(fixed_index),
                regime_decoder_index=np.int16(regime_index),
                circuit_sha256=np.asarray(circuit_sha),
                pooled_dem_sha256=np.asarray(fixed["dem_sha256"]),
                regime_dem_sha256=np.asarray(regime_model["dem_sha256"]),
                sampler_seconds=np.float64(time.perf_counter() - t0 - sum(root_decode_times)),
                decode_seconds=np.asarray(root_decode_times, dtype=np.float64),
            )
            completed += 1
            rec = {"stratum_index": si, "stratum": label, "root_index": ri, "seed": seed,
                   "checkpoint": path.relative_to(HERE).as_posix(), "status": "generated"}
            root_records.append(rec)
            if process is not None:
                cur = int(process.memory_info().rss)
                peak_rss = max(peak_rss or cur, cur)
            progress = {
                "status": "RUNNING" if completed < expected_total else "SAMPLED_ALL_ROOTS",
                "completed_roots": completed, "expected_roots": expected_total,
                "completed_test_shots": completed * CFG["shots_per_root"],
                "elapsed_wall_seconds": round(time.perf_counter() - started, 4),
                "latest_checkpoint": rec,
            }
            atomic_json(HERE / "RUN_PROGRESS.json", progress)
            print(json.dumps(progress), flush=True)

    total_elapsed = time.perf_counter() - started
    metrics = {
        "status": "SAMPLED_ALL_ROOTS" if completed == expected_total else "INCOMPLETE",
        "completed_roots": completed,
        "expected_roots": expected_total,
        "completed_test_shots": completed * CFG["shots_per_root"],
        "target_test_shots": 720000,
        "sampling_wall_seconds": sampler_seconds,
        "decoder_construction_seconds": model_build_seconds,
        "inference_wall_seconds_by_arm": inference_seconds_by_arm,
        "sampling_and_decode_loop_wall_seconds": total_elapsed,
        "process_rss_bytes_start": rss_start,
        "process_rss_bytes_after_model_build": rss_after_models,
        "observed_peak_process_rss_bytes": peak_rss,
        "stim_version": stim.__version__,
        "pymatching_version": pymatching.__version__,
        "freeze_sha256": sha256_file(HERE / "PRETEST_FREEZE.json"),
        "root_records": root_records,
        "notes": "Per-root sampler/decode seconds are stored in NPZ evidence. Process RSS includes Python and native allocations and is sampled between roots; it is not an isolated native matcher allocation measurement."
    }
    atomic_json(HERE / "RUN_TIMINGS.json", metrics)
    if completed == expected_total:
        atomic_json(HERE / "RUN_PROGRESS.json", {
            "status": "SAMPLED_ALL_ROOTS", "completed_roots": completed,
            "expected_roots": expected_total, "completed_test_shots": completed * CFG["shots_per_root"],
            "elapsed_wall_seconds": round(total_elapsed, 4)
        })
    return metrics


if __name__ == "__main__":
    result = run()
    print(json.dumps({k: result[k] for k in ("status", "completed_roots", "completed_test_shots",
                                             "sampling_and_decode_loop_wall_seconds",
                                             "decoder_construction_seconds")}, indent=2))
