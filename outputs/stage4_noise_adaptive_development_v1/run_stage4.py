"""Restartable Stage 4 development execution; all partitions are paired and saved."""
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

from outputs.stage4_noise_adaptive_development_v1.freeze_stage4_dev_v2 import HERE, REPO, build as build_freeze
from outputs.stage4_noise_adaptive_feasibility_v1.prototype import (
    DetectorProfileEstimator, build_decoder, decode_prediction,
)

CONFIG_PATH = HERE / "stage4_development_config.json"
INVENTORY_PATH = HERE / "seed_inventory.json"
FREEZE_PATH = HERE / "STAGE4_DEVELOPMENT_FREEZE_V2.json"
RUN_DIR = HERE / "run_v1"
PROFILE_DIR = RUN_DIR / "profiles"
ROOT_DIR = RUN_DIR / "roots"
STATUS_PATH = RUN_DIR / "status.json"
LOG_PATH = RUN_DIR / "controller.log"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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


def log(message: str) -> None:
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"{stamp} {message}\n")
    print(message, flush=True)


def stream_map(inventory: dict) -> dict[tuple, dict]:
    out = {}
    for stream in inventory["streams"]:
        if stream["kind"] == "profile_development_detectors":
            key = ("profile", float(stream["probability"]), int(stream["root"]))
        elif stream["kind"] == "stage4_calibration_detectors":
            key = ("cal", float(stream["probability"]), int(stream["root"]))
        elif stream["kind"] == "stage4_paired_evaluation":
            key = ("eval", float(stream["probability"]), int(stream["root"]))
        else:
            continue
        if key in out:
            raise ValueError(f"duplicate stream key {key}")
        out[key] = stream
    return out


def validate_config(config: dict, inventory: dict) -> None:
    if config["total_unique_shots"] != 175500 or config["hard_shot_ceiling"] != 180000:
        raise ValueError("shot allocation differs from frozen configuration")
    if inventory["unique_seed_count"] != 82 or inventory["total_unique_seed_count"] != 82:
        raise ValueError("seed inventory size is not 82")
    seeds = [int(s["seed"]) for s in inventory["streams"]]
    if len(seeds) != len(set(seeds)) or any(s < 0 or s >= 2**32 for s in seeds):
        raise ValueError("seed inventory contains collision or out-of-range value")
    if not config["independent_test"]["allocated"] and config["independent_test"]["accessed"] is False:
        return
    raise ValueError("independent-test state must remain unallocated and unopened")


def diagnostic() -> dict:
    """No stochastic experiment data: construction, graph, and deterministic checks only."""
    build_seconds = []
    models = []
    for p in (0.0, 0.00637, 0.012):
        t0 = time.perf_counter()
        models.append(build_decoder(p))
        build_seconds.append(time.perf_counter() - t0)
    fixed, fixed_dem, fixed_matcher = models[0]
    est_circuit, est_dem, est_matcher = models[1]
    true_circuit, true_dem, true_matcher = models[2]
    for dem in (fixed_dem, est_dem, true_dem):
        assert (dem.num_detectors, dem.num_observables) == (40, 1)
    for matcher in (fixed_matcher, est_matcher, true_matcher):
        assert (matcher.num_detectors, matcher.num_fault_ids) == (40, 1)
    assert fixed.num_detectors == est_circuit.num_detectors == true_circuit.num_detectors == 40
    assert fixed.num_observables == 1
    assert str(fixed_dem) != str(true_dem), "burst probability did not alter reconstructed DEM"
    zeros = np.zeros((2500, 40), dtype=np.uint8)
    inference_seconds = []
    predictions = []
    for matcher in (fixed_matcher, est_matcher, true_matcher):
        t0 = time.perf_counter()
        predictions.append(decode_prediction(matcher, zeros))
        inference_seconds.append(time.perf_counter() - t0)
    assert all(np.array_equal(predictions[0], p) for p in predictions[1:])
    noiseless = fixed.without_noise()
    d, o = noiseless.compile_detector_sampler(seed=0).sample(8, separate_observables=True)
    assert d.shape == (8, 40) and o.shape == (8, 1)
    assert not d.any() and not o.any()
    return {"status": "PASS", "stim": stim.__version__, "pymatching": pymatching.__version__,
            "detectors": 40, "observables": 1, "stochastic_diagnostic_samples": 0,
            "deterministic_noiseless_shots": 8, "models_constructed": 3,
            "zero_syndrome_predictions_equal": True,
            "synthetic_2500_row_build_seconds": build_seconds,
            "synthetic_2500_row_inference_seconds": inference_seconds,
            "rss_bytes_after_diagnostic": psutil.Process().memory_info().rss,
            "dem_depends_on_burst_probability": True}


def check_completed(path: Path, expected_seed_pair: tuple[int, int], p: float, root: int) -> dict | None:
    if not path.exists():
        return None
    with np.load(path, allow_pickle=False) as z:
        required = {"calibration_detectors", "evaluation_detectors", "observables", "pred_fixed",
                    "pred_estimated", "pred_oracle", "metadata_json"}
        if not required.issubset(z.files):
            raise RuntimeError(f"existing checkpoint schema mismatch: {path}")
        cal = z["calibration_detectors"]
        det = z["evaluation_detectors"]
        obs = z["observables"]
        preds = [z[k] for k in ("pred_fixed", "pred_estimated", "pred_oracle")]
        meta = json.loads(str(z["metadata_json"].item()))
    if (cal.shape != (2000, 40) or det.shape != (2500, 40) or obs.shape != (2500, 1)
            or any(q.shape != (2500,) for q in preds)):
        raise RuntimeError(f"existing checkpoint shape mismatch: {path}")
    if meta["seeds"] != list(expected_seed_pair) or meta["probability"] != p or meta["root"] != root:
        raise RuntimeError(f"existing checkpoint provenance mismatch: {path}")
    return {"path": str(path.relative_to(REPO)), "sha256": sha256_file(path),
            "calibration_shots": 2000, "evaluation_shots": 2500, "root": root, "probability": p}


def execute() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--validate-only", action="store_true")
    group.add_argument("--run", action="store_true")
    args = parser.parse_args()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    validate_config(config, inventory)
    # --run and --validate-only both demand the pre-sampling hash freeze.
    frozen = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    now = build_freeze()
    if frozen["files_sha256"] != now["files_sha256"]:
        raise RuntimeError("frozen file hashes changed; refusing to sample/resume")
    diag = diagnostic()
    if args.validate_only:
        print(json.dumps(diag, indent=2))
        return

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    ROOT_DIR.mkdir(parents=True, exist_ok=True)
    expected_profile_names = {f"profile_p{int(round(p*1000)):03d}_r{r}.npz"
                              for p in (0.0, 0.01, 0.02) for r in range(3)}
    expected_root_names = {f"p{int(round(p*1000)):03d}_root{r:02d}.npz"
                           for p in (0.0, 0.004, 0.008, 0.012, 0.016) for r in range(7)}
    extras = ({p.name for p in PROFILE_DIR.glob("*.npz")} - expected_profile_names) | \
             ({p.name for p in ROOT_DIR.glob("*.npz")} - expected_root_names)
    if extras:
        raise RuntimeError(f"unexpected preexisting sample checkpoint files: {sorted(extras)}")
    prior_status = json.loads(STATUS_PATH.read_text(encoding="utf-8")) if STATUS_PATH.exists() else {}
    started = float(prior_status.get("started_unix", time.time()))
    proc = psutil.Process()
    if proc.memory_info().rss > config["resources"]["peak_rss_bytes_max"]:
        raise MemoryError("RSS limit exceeded before sampling")
    disk = psutil.disk_usage(str(RUN_DIR))
    if disk.free < 2 * 1024**3:
        raise OSError(f"less than 2 GiB free disk space: {disk.free}")
    status = {"status": "running", "started_unix": started, "pid": os.getpid(),
              "working_directory": str(REPO), "completed_roots": [], "completed_shots": 0,
              "peak_rss_bytes": int(prior_status.get("peak_rss_bytes", 0)),
              "unique_shot_budget": 175500, "independent_test_accessed": 0,
              "software": {"python": platform.python_version(), "numpy": np.__version__,
                           "stim": stim.__version__, "pymatching": pymatching.__version__},
              "preflight": diag}
    atomic_json(STATUS_PATH, status)
    log("Stage 4 run started; 175500-shot ceiling, 35 paired root-condition checkpoints.")
    seeds = stream_map(inventory)

    # Generate detector-only profiles once; retain exact batches for audit.
    profile_batches = []
    for p in (0.0, 0.01, 0.02):
        for rep in range(3):
            item = seeds[("profile", p, rep)]
            path = PROFILE_DIR / f"profile_p{int(round(p*1000)):03d}_r{rep}.npz"
            if path.exists():
                with np.load(path, allow_pickle=False) as z:
                    if int(z["seed"].item()) != int(item["seed"]):
                        raise RuntimeError(f"profile checkpoint seed mismatch: {path}")
                    det = z["detectors"]
            else:
                circuit, _, _ = build_decoder(p)
                det = circuit.compile_detector_sampler(seed=int(item["seed"])).sample(int(item["shots"]))
                if det.shape != (2000, 40):
                    raise RuntimeError("invalid profile detector dimensions")
                atomic_npz(path, detectors=det.astype(np.uint8), seed=np.int64(item["seed"]),
                           probability=np.float64(p), root=np.int64(rep))
            profile_batches.append((p, det))
            status["completed_shots"] = 2000 * len(profile_batches)
            status["completed_profile_batches"] = len(profile_batches)
            status["active_runtime_seconds"] = time.time() - started
            atomic_json(STATUS_PATH, status)
            log(f"profile p={p:.3f} replicate={rep} shots={len(det)}")
    estimator = DetectorProfileEstimator.fit(profile_batches)
    ci_seed = int(config["statistical_plan"]["calibration_interval"]["seed"])
    ci_rng = np.random.default_rng(ci_seed)

    root_records = []
    for p in (0.0, 0.004, 0.008, 0.012, 0.016):
        for root in range(7):
            out = ROOT_DIR / f"p{int(round(p*1000)):03d}_root{root:02d}.npz"
            cal_stream = seeds[("cal", p, root)]
            eval_stream = seeds[("eval", p, root)]
            existing = check_completed(out, (int(cal_stream["seed"]), int(eval_stream["seed"])), p, root)
            if existing:
                root_records.append(existing)
                status["completed_roots"].append(existing)
                status["completed_shots"] += 4500
                atomic_json(STATUS_PATH, status)
                log(f"resume accepted {out.name}")
                continue
            circuit, _, _ = build_decoder(p)
            cal_det = circuit.compile_detector_sampler(seed=int(cal_stream["seed"])).sample(
                int(cal_stream["shots"]))
            if cal_det.shape != (2000, 40):
                raise RuntimeError("invalid calibration detector dimensions")
            p_hat = estimator.estimate(cal_det)
            # One analysis stream is advanced deterministically across roots.
            ci = estimator.bootstrap_interval(cal_det, rng=ci_rng, replicates=500)
            decoder_build_seconds = []
            matchers = []
            for decoder_p in (0.0, p_hat, p):
                rebuild_start = time.perf_counter()
                _, _, matcher = build_decoder(decoder_p)
                decoder_build_seconds.append(time.perf_counter() - rebuild_start)
                matchers.append(matcher)
            # Generate evaluation samples only after estimate and all decoder choices are frozen.
            eval_det, obs = circuit.compile_detector_sampler(seed=int(eval_stream["seed"]))\
                .sample(int(eval_stream["shots"]), separate_observables=True)
            if eval_det.shape != (2500, 40) or obs.shape != (2500, 1):
                raise RuntimeError("invalid paired evaluation dimensions")
            decode_times = []
            predictions = []
            for matcher in matchers:
                t0 = time.perf_counter()
                predictions.append(decode_prediction(matcher, eval_det))
                decode_times.append(time.perf_counter() - t0)
            meta = {"probability": p, "root": root,
                    "seeds": [int(cal_stream["seed"]), int(eval_stream["seed"])],
                    "shots": {"calibration": 2000, "evaluation": 2500},
                    "p_hat": p_hat, "p_hat_ci_95": list(ci),
                    "decoder_burst_probabilities": [0.0, p_hat, p],
                    "decoder_rebuild_seconds": decoder_build_seconds,
                    "rebuild_seconds_all_3": float(sum(decoder_build_seconds)),
                    "decode_seconds": decode_times,
                    "detector_sha256": sha256_bytes(eval_det.tobytes()),
                    "observable_sha256": sha256_bytes(obs.tobytes()),
                    "calibration_detector_sha256": sha256_bytes(cal_det.tobytes())}
            atomic_npz(out, calibration_detectors=cal_det.astype(np.uint8),
                       evaluation_detectors=eval_det.astype(np.uint8), observables=obs.astype(np.uint8),
                       pred_fixed=predictions[0], pred_estimated=predictions[1], pred_oracle=predictions[2],
                       metadata_json=np.asarray(json.dumps(meta, sort_keys=True)))
            rec = {"path": str(out.relative_to(REPO)), "sha256": sha256_file(out),
                   "calibration_shots": 2000, "evaluation_shots": 2500, "root": root, "probability": p}
            root_records.append(rec)
            status["completed_roots"].append(rec)
            status["completed_shots"] += 4500
            status["active_runtime_seconds"] = time.time() - started
            status["peak_rss_bytes"] = max(status["peak_rss_bytes"], proc.memory_info().rss)
            if status["peak_rss_bytes"] >= config["resources"]["peak_rss_bytes_max"]:
                status["status"] = "failed_resource_limit"
                atomic_json(STATUS_PATH, status)
                raise MemoryError("RSS limit exceeded during execution")
            if status["active_runtime_seconds"] >= config["resources"]["wall_seconds_max"]:
                status["status"] = "failed_wall_limit"
                atomic_json(STATUS_PATH, status)
                raise TimeoutError("wall-time limit exceeded")
            atomic_json(STATUS_PATH, status)
            log(f"completed p={p:.3f} root={root} p_hat={p_hat:.5f} shots=4500")

    profile_hashes = [{"path": str(p.relative_to(REPO)), "sha256": sha256_file(p)}
                      for p in sorted(PROFILE_DIR.glob("*.npz"))]
    status.update({"status": "finalizing", "sampling_status": "all_allocated_samples_saved",
                   "completed_shot_count": 175500,
                   "completed_root_condition_count": len(root_records),
                   "active_runtime_seconds": time.time() - started,
                   "peak_rss_bytes": max(status["peak_rss_bytes"], proc.memory_info().rss),
                   "profile_files": profile_hashes,
                   "root_files": root_records, "finished_unix": time.time()})
    status["status"] = "finalizing"
    status["root_files"] = root_records
    atomic_json(STATUS_PATH, status)
    log("Stage 4 sampling complete; awaiting independent evidence audit before terminal completion.")


def main() -> None:
    try:
        execute()
    except BaseException as exc:
        if STATUS_PATH.exists():
            try:
                state = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
                state["status"] = "failed"
                state["failure"] = f"{type(exc).__name__}: {exc}"
                state["failed_unix"] = time.time()
                atomic_json(STATUS_PATH, state)
            except Exception:
                pass
        log(f"FAILED: {type(exc).__name__}: {exc}")
        raise


if __name__ == "__main__":
    main()
