"""Measure the real runner workload on separately seeded disposable data."""
from __future__ import annotations

import json
import shutil
import tempfile
import threading
import time
from pathlib import Path

import numpy as np
import psutil
import pymatching
import scipy
import stim

from experiment_core import atomic_json, atomic_npz, build_models, detector_profile_estimator, sample_arrays, sha256
from freeze_pretest import HERE, verify_freeze


def main() -> None:
    verify_freeze()
    cfg = json.loads((HERE / "experiment_config.json").read_text(encoding="utf-8"))
    inv = json.loads((HERE / "seed_inventory.json").read_text(encoding="utf-8"))
    bench = [s for s in inv["streams"] if s["split"] == "benchmark_only_v4"]
    if len(bench) != 5 or sum(int(s["shots"]) for s in bench) != 3500:
        raise RuntimeError("expected five fresh benchmark-v4 seeds and exactly 3,500 shots")
    expected_roles = {"benchmark_v4_template": 3, "benchmark_v4_calibration": 1,
                      "benchmark_v4_evaluation": 1}
    if {role: sum(s["role"] == role for s in bench) for role in expected_roles} != expected_roles:
        raise RuntimeError("benchmark-v4 role inventory mismatch; refusing before sampling")
    seeds = [int(s["seed"]) for s in inv["streams"]]
    if len(seeds) != len(set(seeds)) or inv.get("collisions"):
        raise RuntimeError("seed collision/uniqueness check failed; refusing before sampling")
    study_shots_preflight = sum(int(s["shots"]) for s in inv["streams"] if s["included_in_allocation"])
    if study_shots_preflight != int(cfg["allocation"]["unique_shots"]):
        raise RuntimeError("study allocation shot count mismatch; refusing before benchmark sampling")

    proc = psutil.Process()
    stop_monitor = threading.Event()
    peak_rss = [proc.memory_info().rss]

    def monitor():
        while not stop_monitor.wait(.01):
            try:
                peak_rss[0] = max(peak_rss[0], proc.memory_info().rss)
            except psutil.Error:
                pass

    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
    t_all = time.perf_counter()
    stages: dict[str, float] = {}
    template_batches = []
    for s in [x for x in bench if x["role"] == "benchmark_v4_template"]:
        t = time.perf_counter()
        d = sample_arrays(float(s["probability"]), int(s["seed"]), int(s["shots"]), cfg, labels=False)
        stages[f"sample_template_p{s['probability']}"] = time.perf_counter() - t
        template_batches.append((float(s["probability"]), d))
    estimator = detector_profile_estimator(template_batches)

    cal_stream = next(s for s in bench if s["role"] == "benchmark_v4_calibration")
    t = time.perf_counter()
    cal = sample_arrays(float(cal_stream["probability"]), int(cal_stream["seed"]), int(cal_stream["shots"]), cfg, labels=False)
    stages["calibration_sampling"] = time.perf_counter() - t
    t = time.perf_counter()
    p_hat = estimator.estimate(cal)
    stages["single_root_profile_estimation"] = time.perf_counter() - t

    # Mimic the 1.2M-row pooled calibration feature matrix to measure time and peak working set.
    t = time.perf_counter()
    pooled_cal = np.tile(cal, (1200, 1))
    pooled_p = estimator.estimate(pooled_cal)
    stages["pooled_1p2m_detector_estimation"] = time.perf_counter() - t
    del pooled_cal

    eval_stream = next(s for s in bench if s["role"] == "benchmark_v4_evaluation")
    t = time.perf_counter()
    detectors, observables = sample_arrays(float(eval_stream["probability"]), int(eval_stream["seed"]), int(eval_stream["shots"]), cfg, labels=True)
    stages["evaluation_sampling"] = time.perf_counter() - t

    grid = list(map(float, cfg["decoders"]["static_candidate_grid"]))
    candidates_and_arms = list(dict.fromkeys(grid + [0.0, p_hat, float(eval_stream["probability"])]))
    t = time.perf_counter()
    matchers = build_models(candidates_and_arms)
    stages["candidate_and_final_matcher_build"] = time.perf_counter() - t
    t = time.perf_counter()
    grid_predictions = np.stack([matchers[p].decode_batch(detectors).reshape(-1).astype(np.uint8) for p in grid])
    stages["nine_candidate_grid_decode"] = time.perf_counter() - t
    final_probs = [0.0, pooled_p, 0.008, p_hat, float(eval_stream["probability"])]
    t = time.perf_counter()
    final_predictions = np.stack([matchers[float(p)].decode_batch(detectors).reshape(-1).astype(np.uint8) for p in final_probs])
    stages["five_final_arm_decode"] = time.perf_counter() - t
    if grid_predictions.shape != (9, 1000) or final_predictions.shape != (5, 1000):
        raise RuntimeError("benchmark paired decoding produced an invalid shape")

    # Representative 2,500-shot compressed artifacts for the archive families used by the runner.
    reps_det = np.resize(detectors, (2500, 40)).astype(np.uint8)
    reps_obs = np.resize(observables, (2500,)).astype(np.uint8)
    reps_grid = np.resize(grid_predictions, (9, 2500)).astype(np.uint8)
    reps_final = np.resize(final_predictions, (5, 2500)).astype(np.uint8)
    cal_det = np.resize(cal, (2000, 40)).astype(np.uint8)
    temp_det = np.resize(template_batches[1][1], (20000, 40)).astype(np.uint8)
    io_seconds = {}
    io_bytes = {}
    with tempfile.TemporaryDirectory(prefix="qshift_stage1_benchmark_", dir=HERE) as td:
        for name, arrays in {
            "template": {"detectors": temp_det},
            "calibration": {"detectors": cal_det},
            "scoring": {"detectors": reps_det, "observable": reps_obs},
            "candidate_predictions": {"detectors": reps_det, "observable": reps_obs, "candidate_predictions": reps_grid},
            "final_evaluation": {"detectors": reps_det, "observable": reps_obs, "predictions": reps_final, "p_hat": np.asarray(p_hat)},
        }.items():
            path = Path(td) / f"{name}.npz"
            t = time.perf_counter()
            atomic_npz(path, **arrays)
            io_seconds[name] = time.perf_counter() - t
            io_bytes[name] = path.stat().st_size

    # Required 100k root-cluster bootstrap analysis, using synthetic root vectors only.
    seed = next(int(s["seed"]) for s in inv["streams"] if s["role"] == "bootstrap_results")
    rng = np.random.Generator(np.random.PCG64(seed))
    synthetic_diffs = [rng.normal(0, .001, 120) for _ in range(4)]
    t = time.perf_counter()
    for _ in range(6):
        out = np.empty(100_000)
        for start in range(0, len(out), 2000):
            n = min(2000, len(out) - start)
            condition_means = []
            for x in synthetic_diffs:
                idx = rng.integers(0, len(x), size=(n, len(x)))
                condition_means.append(x[idx].mean(axis=1))
            out[start:start+n] = np.mean(condition_means, axis=0)
    stages["six_100k_stratified_bootstrap_contrasts"] = time.perf_counter() - t

    # Project all unique study shots plus decoder-build, estimate, archive and analysis work.
    template_rate = sum(int(s["shots"]) for s in bench if s["role"] == "benchmark_v4_template") / sum(v for k, v in stages.items() if k.startswith("sample_template_"))
    cal_rate = int(cal_stream["shots"]) / max(stages["calibration_sampling"], 1e-9)
    eval_rate = int(eval_stream["shots"]) / max(stages["evaluation_sampling"], 1e-9)
    # Per-arm per-shot decoding rates; use the lower of grid and final measurements.
    grid_decode_rate = 9 * len(detectors) / max(stages["nine_candidate_grid_decode"], 1e-9)
    final_decode_rate = 5 * len(detectors) / max(stages["five_final_arm_decode"], 1e-9)
    decode_rate = min(grid_decode_rate, final_decode_rate)
    sample_projection = 60_000 / template_rate + 1_600_000 / cal_rate + 2_000_000 / eval_rate
    decode_projection = (4_500_000 + 7_500_000) / decode_rate
    model_build_seconds = stages["candidate_and_final_matcher_build"] / max(1, len(matchers))
    model_projection = (9 + 600) * model_build_seconds
    estimate_projection = (600 * 2 * stages["single_root_profile_estimation"] + stages["pooled_1p2m_detector_estimation"])
    write_projection = (3 * io_seconds["template"] + 800 * io_seconds["calibration"] +
                        200 * io_seconds["scoring"] + 200 * io_seconds["candidate_predictions"] +
                        600 * io_seconds["final_evaluation"])
    storage_projection = (3 * io_bytes["template"] + 800 * io_bytes["calibration"] +
                          200 * io_bytes["scoring"] + 200 * io_bytes["candidate_predictions"] +
                          600 * io_bytes["final_evaluation"] + 1803 * 2048)
    stats_projection = stages["six_100k_stratified_bootstrap_contrasts"] * (7 / 6)
    total_projection = 2.0 * (sample_projection + decode_projection + model_projection + estimate_projection + write_projection + stats_projection)
    stop_monitor.set()
    thread.join(timeout=1)
    wall = time.perf_counter() - t_all
    allocation = int(cfg["allocation"]["unique_shots"])
    study_shots = sum(int(x["shots"]) for x in inv["streams"] if x["included_in_allocation"])
    if study_shots != allocation:
        raise RuntimeError("seed inventory sampling shots do not match configured allocation")
    report = {
        "status": "BENCHMARK_ONLY_NO_STUDY_SAMPLING",
        "benchmark_revision": 3,
        "supersedes_benchmark_file": "BENCHMARK_RESULTS.json; BENCHMARK_FAILURE_V2.md and BENCHMARK_FAILURE_V3.md document failed attempts on retired benchmark seeds",
        "pretest_freeze_path": "PRETEST_FREEZE_V5.json",
        "pretest_freeze_sha256": sha256(HERE / "PRETEST_FREEZE_V5.json"),
        "benchmark_streams": [{k: s[k] for k in ("role", "split", "probability", "seed", "shots", "included_in_allocation")} for s in bench],
        "benchmark_samples": 3500,
        "prior_benchmark_samples_preserved": 10500,
        "study_unique_shots_generated": 0,
        "study_unique_shots_planned": study_shots_preflight,
        "estimated_single_root_p": float(p_hat),
        "estimated_pooled_p": float(pooled_p),
        "paired_candidate_predictions": list(grid_predictions.shape),
        "paired_final_predictions": list(final_predictions.shape),
        "stage_seconds": stages,
        "compressed_artifact_bytes": io_bytes,
        "compressed_artifact_write_seconds": io_seconds,
        "projected_study_archive_storage_bytes": int(storage_projection),
        "configured_free_disk_reserve_bytes": int(cfg["resources"]["free_disk_min_bytes"]),
        "wall_seconds": wall,
        "peak_observed_rss_bytes": int(peak_rss[0]),
        "available_memory_bytes": int(psutil.virtual_memory().available),
        "available_disk_bytes": int(shutil.disk_usage(HERE.anchor).free),
        "software_versions": {"stim": stim.__version__, "pymatching": pymatching.__version__,
                              "numpy": np.__version__, "scipy": scipy.__version__},
        "estimated_full_allocation_seconds_conservative_2x": float(total_projection),
        "projection_components_seconds": {"sampling": sample_projection, "decoder_inference": decode_projection,
                                            "matcher_construction": model_projection, "calibration_estimation": estimate_projection,
                                            "compressed_io": write_projection, "bootstrap": stats_projection},
        "projection_assumptions": ["2x multiplier applied to complete component sum", "decode throughput from the slower 9-arm or 5-arm paired benchmark", "600 per-root adaptive matcher rebuilds conservatively assumed", "archive mix uses representative compressed detector/prediction arrays", "small benchmark cannot capture long-run thermal throttling or filesystem variability"],
        "independent_test_access": False,
        "stage5_evaluation_sampling": 0,
    }
    out = HERE / "BENCHMARK_RESULTS_V4.json"
    atomic_json(out, report)
    print(json.dumps({"status": report["status"], "benchmark_samples": report["benchmark_samples"],
                      "study_shots": report["study_unique_shots_generated"],
                      "runtime_projection_seconds": report["estimated_full_allocation_seconds_conservative_2x"],
                      "peak_rss_bytes": report["peak_observed_rss_bytes"],
                      "output": str(out)}, indent=2))


if __name__ == "__main__":
    main()
