"""Disposable full Stim/profile-estimator/PyMatching throughput and resume check.

The 225k benchmark shots use a separately collision-screened development seed
namespace. This program never imports or invokes the Stage 5 runner.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import psutil
import stim
import pymatching

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUN = HERE / "benchmark_run"
sys.path.insert(0, str(ROOT))
from outputs.phase3a_correlated_noise_preflight.simulator import build_spatial_burst_circuit, build_matching
from outputs.stage4_noise_adaptive_feasibility_v1.prototype import DetectorProfileEstimator, decode_prediction, build_decoder
from integrity import verify_preexecution_freeze

CONFIG_PATH = HERE / "BENCHMARK_CONFIG.json"
INVENTORY_PATH = HERE / "VALIDATION_SEED_INVENTORY.json"
PROFILE_PATH = ROOT / "outputs/stage5_preexecution_v1/FROZEN_PROFILE_ESTIMATOR.json"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def atomic_npz(path: Path, **arrays) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as stream:
        np.savez_compressed(stream, **arrays)
    os.replace(tmp, path)


def filename(p: float, root: int) -> str:
    return f"root_p{p:.3f}_r{root:03d}.npz"


def load_profile() -> DetectorProfileEstimator:
    d = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    return DetectorProfileEstimator(np.asarray(d["probabilities"], float), np.asarray(d["means"], float),
                                    np.asarray(d["scales"], float), float(d.get("grid_step", 1e-5)))


def load_seeds(config: dict, inventory: dict) -> dict:
    out = {}
    for row in inventory["benchmark_streams"]:
        key = (row["kind"], float(row["probability"]), int(row["root"]))
        if key in out:
            raise ValueError(f"duplicate benchmark stream {key}")
        out[key] = int(row["seed"])
    probs = [float(x) for x in config["probabilities"]]
    roots = int(config["roots_per_probability"])
    expected = {(kind, p, r) for kind in ("calibration_detector_only", "paired_evaluation_detector_observable")
                for p in probs for r in range(roots)}
    if set(out) != expected or len(set(out.values())) != len(expected):
        raise ValueError("benchmark inventory has incomplete or colliding streams")
    return out


def validate_existing(path: Path, p: float, root: int, cal_seed: int, eval_seed: int, hashes: dict) -> None:
    if path.name not in hashes or digest(path) != hashes[path.name]:
        raise ValueError(f"existing checkpoint missing from hash journal or changed: {path.name}")
    with np.load(path, allow_pickle=False) as z:
        if str(np.asarray(z["phase"]).item()) != "complete":
            raise ValueError(f"incomplete checkpoint cannot be resumed: {path.name}")
        if float(np.asarray(z["probability"]).item()) != p or int(np.asarray(z["root"]).item()) != root:
            raise ValueError(f"checkpoint identity mismatch: {path.name}")
        if int(np.asarray(z["seed_calibration"]).item()) != cal_seed or int(np.asarray(z["seed_evaluation"]).item()) != eval_seed:
            raise ValueError(f"checkpoint seed mismatch: {path.name}")
        if np.asarray(z["calibration_detectors"]).shape != (2000, 40):
            raise ValueError(f"calibration shape mismatch: {path.name}")
        if np.asarray(z["evaluation_detectors"]).shape != (2500, 40) or np.asarray(z["observables"]).shape != (2500,):
            raise ValueError(f"evaluation shape mismatch: {path.name}")
        if np.asarray(z["predictions"]).shape != (3, 2500):
            raise ValueError(f"prediction shape mismatch: {path.name}")


def execute(limit_new_roots: int | None = None) -> dict:
    verify_preexecution_freeze()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    seeds = load_seeds(config, inventory)
    profile = load_profile()
    RUN.mkdir(parents=True, exist_ok=True)
    root_dir = RUN / "roots"
    root_dir.mkdir(parents=True, exist_ok=True)
    status_path = RUN / "BENCHMARK_STATUS.json"
    journal_path = RUN / "checkpoint_hashes.json"
    old_status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
    hashes = json.loads(journal_path.read_text(encoding="utf-8")) if journal_path.exists() else {}
    proc = psutil.Process()
    start = time.perf_counter()
    timing = {k: float(old_status.get("timing_seconds", {}).get(k, 0.0)) for k in
              ("calibration_sampling", "estimation", "graph_construction", "evaluation_sampling", "decoding", "checkpoint_write")}
    peak_rss = max(int(old_status.get("peak_rss_bytes", 0)), proc.memory_info().rss)
    roots_done = set(hashes)
    unjournaled = {p.name for p in root_dir.glob("root_p*.npz")} - roots_done
    if unjournaled:
        raise RuntimeError(f"unjournaled checkpoint archive(s) found; refusing to overwrite: {sorted(unjournaled)}")
    created_this_call = 0
    elapsed_before = float(old_status.get("elapsed_before_resume", 0.0))
    status = {"status": "benchmark_running", "completed_roots": len(roots_done),
              "total_roots": len(config["probabilities"]) * int(config["roots_per_probability"]),
              "stage5_sampling": False, "independent_test_access": 0,
              "unique_shots_generated": len(roots_done) * (2000 + 2500),
              "timing_seconds": timing, "peak_rss_bytes": peak_rss,
              "start_time_unix": old_status.get("start_time_unix", time.time())}
    atomic_json(status_path, status)
    probs = [float(x) for x in config["probabilities"]]
    nroots = int(config["roots_per_probability"])
    fixed_graph = time.perf_counter()
    fixed = build_decoder(0.0)[2]
    oracle = {p: build_decoder(p)[2] for p in probs}
    timing["graph_construction"] += time.perf_counter() - fixed_graph

    for p in probs:
        circuit = build_spatial_burst_circuit(memory_basis="z", regime="balanced", distance=3, rounds=5,
                    gate_p=.003, measurement_p=.003, bias_ratio=10.0, burst_probability=p,
                    burst_pair=tuple(config["circuit"]["burst_pair"]))
        if (circuit.num_detectors, circuit.num_observables) != (40, 1):
            raise RuntimeError(f"unexpected circuit dimensions at p={p}")
        for root in range(nroots):
            f = root_dir / filename(p, root)
            if f.name in roots_done:
                sc = seeds[("calibration_detector_only", p, root)]
                se = seeds[("paired_evaluation_detector_observable", p, root)]
                validate_existing(f, p, root, sc, se, hashes)
                continue
            if limit_new_roots is not None and created_this_call >= limit_new_roots:
                status.update({"status": "paused_benchmark_limit", "completed_roots": len(roots_done),
                    "unique_shots_generated": len(roots_done) * 4500, "timing_seconds": timing,
                    "peak_rss_bytes": max(peak_rss, proc.memory_info().rss),
                    "elapsed_before_resume": elapsed_before + time.perf_counter() - start,
                    "last_update_unix": time.time()})
                atomic_json(status_path, status)
                return status
            if shutil.disk_usage(RUN).free < int(config["resources"]["disk_min_free_bytes"]):
                raise RuntimeError("benchmark disk-space guard reached")
            sc = seeds[("calibration_detector_only", p, root)]
            se = seeds[("paired_evaluation_detector_observable", p, root)]
            tic = time.perf_counter()
            cal = circuit.compile_detector_sampler(seed=sc).sample(int(config["calibration_shots_per_root"]))
            cal = np.asarray(cal, dtype=np.uint8)
            timing["calibration_sampling"] += time.perf_counter() - tic
            tic = time.perf_counter()
            p_hat = float(profile.estimate(cal))
            timing["estimation"] += time.perf_counter() - tic
            tic = time.perf_counter()
            adaptive = build_decoder(p_hat)[2]
            timing["graph_construction"] += time.perf_counter() - tic
            tic = time.perf_counter()
            det, obs = circuit.compile_detector_sampler(seed=se).sample(
                int(config["paired_evaluation_shots_per_root"]), separate_observables=True)
            det = np.asarray(det, dtype=np.uint8)
            obs = np.asarray(obs, dtype=np.uint8).reshape(-1)
            timing["evaluation_sampling"] += time.perf_counter() - tic
            if cal.shape != (2000, 40) or det.shape != (2500, 40) or obs.shape != (2500,):
                raise RuntimeError("sample shape validation failed")
            tic = time.perf_counter()
            predictions = np.stack([decode_prediction(fixed, det), decode_prediction(adaptive, det),
                                    decode_prediction(oracle[p], det)])
            timing["decoding"] += time.perf_counter() - tic
            if not np.isin(predictions, (0, 1)).all() or not np.isin(obs, (0, 1)).all():
                raise RuntimeError("nonbinary prediction/observable found")
            tic = time.perf_counter()
            atomic_npz(f, phase=np.asarray("complete"), calibration_detectors=cal,
                evaluation_detectors=det, observables=obs, predictions=predictions,
                p_hat=np.asarray(p_hat), probability=np.asarray(p), root=np.asarray(root),
                seed_calibration=np.asarray(sc), seed_evaluation=np.asarray(se))
            hashes[f.name] = digest(f)
            atomic_json(journal_path, hashes)
            timing["checkpoint_write"] += time.perf_counter() - tic
            roots_done.add(f.name)
            created_this_call += 1
            peak_rss = max(peak_rss, proc.memory_info().rss)
            status.update({"completed_roots": len(roots_done), "unique_shots_generated": len(roots_done) * 4500,
                "timing_seconds": timing, "peak_rss_bytes": peak_rss,
                "elapsed_before_resume": elapsed_before + time.perf_counter() - start,
                "last_update_unix": time.time()})
            atomic_json(status_path, status)

    rows = []
    for p in probs:
        for root in range(nroots):
            with np.load(root_dir / filename(p, root), allow_pickle=False) as z:
                obs = np.asarray(z["observables"], dtype=np.uint8)
                pred = np.asarray(z["predictions"], dtype=np.uint8)
                errors = np.count_nonzero(pred ^ obs[None, :], axis=1)
                rows.append({"probability": p, "root": root, "shots": len(obs),
                    "p_hat": float(np.asarray(z["p_hat"]).item()),
                    "fixed_errors": int(errors[0]), "adaptive_errors": int(errors[1]),
                    "oracle_errors": int(errors[2]),
                    "adaptive_only_wrong": int(np.count_nonzero((pred[1] != obs) & (pred[0] == obs))),
                    "fixed_only_wrong": int(np.count_nonzero((pred[1] == obs) & (pred[0] != obs))),
                    "prediction_disagreements": int(np.count_nonzero(pred[1] != pred[0]))})
    csv_path = RUN / "BENCHMARK_PER_ROOT.csv"
    tmp_csv = csv_path.with_suffix(".csv.tmp")
    with tmp_csv.open("w", newline="", encoding="utf-8") as fcsv:
        writer = csv.DictWriter(fcsv, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    os.replace(tmp_csv, csv_path)
    archive_bytes = sum((root_dir / name).stat().st_size for name in hashes)
    summary = {
        "status": "completed; engineering benchmark only", "stage5_sampling": False,
        "independent_test_access": 0, "roots": len(rows), "roots_per_probability": nroots,
        "calibration_shots": len(rows) * 2000, "evaluation_shots": len(rows) * 2500,
        "unique_shots": len(rows) * 4500, "probabilities": probs,
        "decoder_arms": ["fixed_nominal", "profile_adaptive", "privileged_true_probability_reference"],
        "timing_seconds": timing, "wall_seconds_total_including_resume": elapsed_before + time.perf_counter() - start,
        "peak_rss_bytes": max(peak_rss, proc.memory_info().rss),
        "archive_bytes": archive_bytes, "archive_bytes_per_root": archive_bytes / len(rows),
        "estimated_archive_bytes_for_256_roots_per_probability": archive_bytes / len(rows) * 256 * len(probs),
        "unique_shots_per_second": len(rows) * 4500 / (elapsed_before + time.perf_counter() - start),
        "metrics_scope": "functional checks only; no decoder efficacy inference or Stage 5 result",
        "root_archive_hash_count": len(hashes),
    }
    atomic_json(RUN / "BENCHMARK_SUMMARY.json", summary)
    atomic_json(RUN / "ROOT_ARCHIVE_MANIFEST.json", {"root_count": len(rows), "sha256": hashes})
    status.update({"status": "benchmark_completed", "completed_roots": len(rows),
        "unique_shots_generated": len(rows) * 4500, "timing_seconds": timing,
        "peak_rss_bytes": summary["peak_rss_bytes"], "completed_unix": time.time()})
    atomic_json(status_path, status)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-new-roots", type=int, default=None)
    args = parser.parse_args()
    if args.limit_new_roots is not None and args.limit_new_roots <= 0:
        parser.error("--limit-new-roots must be positive")
    result = execute(args.limit_new_roots)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
