"""Detector-only V1.1 gate and deterministic decoder/resource preflight."""
from __future__ import annotations

import argparse
import hashlib
import re
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import psutil
import pymatching
import stim

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from outputs.qshift_correlated_decoder_feasibility_v1_1.model import (
    BurstEnumerationDecoder,
    BurstRateEstimator,
    build_base_circuit,
    build_candidate_circuit,
    build_decomposed_dem,
    build_matching,
    extract_burst_events,
)
from outputs.qshift_correlated_decoder_feasibility_v1_1.verify_reuse import verify


V1_QS = (0.0, 0.01, 0.02)
ROOTS = 10
SHOTS_PER_ROOT = 2000
BOOTSTRAPS = 20000


def load_detectors(path: Path, expected_rows: int) -> np.ndarray:
    # Do not access the observable member. It remains present in historical V1 archives.
    with np.load(path, allow_pickle=False) as archive:
        x = np.asarray(archive["detectors"])
    if x.shape != (expected_rows, 40) or not np.isin(x, [0, 1]).all():
        raise ValueError(f"invalid detector-only archive: {path.name}")
    return x.astype(np.uint8, copy=False)


def load_reused(v1_repo: Path) -> tuple[np.ndarray, np.ndarray, dict[tuple[int, int], np.ndarray]]:
    run = v1_repo / "outputs/qshift_correlated_decoder_feasibility_v1/pilot_runs/attempt_001"
    train_x = []
    train_y = []
    calibration = {}
    for qi, q in enumerate(V1_QS):
        x = load_detectors(run / f"training/train_q{qi}.npz", 1000)
        train_x.append(x)
        train_y.append(np.full(1000, q, dtype=np.float64))
        for root in range(ROOTS):
            calibration[(qi, root)] = load_detectors(
                run / f"calibration/cal_q{qi}_r{root:02d}.npz", 500
            )
    return np.vstack(train_x), np.concatenate(train_y), calibration


def deterministic_valid_fault_fixtures(background_dem, events) -> tuple[np.ndarray, dict]:
    burst_only = []
    for mask in range(1 << len(events)):
        syndrome = np.zeros(40, dtype=np.uint8)
        for index, event in enumerate(events):
            if (mask >> index) & 1:
                syndrome[list(event.detector_ids)] ^= 1
        burst_only.append(syndrome)
    background_signatures = []
    for line in (line for line in str(background_dem).splitlines() if line.startswith("error(")):
        detector_ids = [int(value) for value in re.findall(r"D(\d+)", line)]
        if detector_ids:
            syndrome = np.zeros(40, dtype=np.uint8)
            for detector in detector_ids:
                syndrome[detector] ^= 1
            background_signatures.append(syndrome)
    if len(background_signatures) < 100:
        raise RuntimeError("background DEM has fewer than 100 deterministic fault signatures")
    background_signatures = background_signatures[:100]
    composite = []
    for base in background_signatures:
        for mask in (0,) + tuple(1 << index for index in range(len(events))):
            syndrome = base.copy()
            for index, event in enumerate(events):
                if (mask >> index) & 1:
                    syndrome[list(event.detector_ids)] ^= 1
            composite.append(syndrome)
    return np.asarray(burst_only + composite, dtype=np.uint8), {
        "burst_only_patterns": len(burst_only),
        "background_fault_plus_single_burst_patterns": len(composite),
        "background_signatures_used": len(background_signatures),
    }


def sha256_json(value: dict) -> str:
    return hashlib.sha256((json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()).hexdigest()


def run(v1_repo: Path) -> dict:
    reuse = verify(v1_repo)
    started = time.perf_counter()
    train_x, train_y, calibration = load_reused(v1_repo)
    events = extract_burst_events()
    estimator = BurstRateEstimator(events).fit(train_x, train_y)
    q_by_root = {(qi, ri): estimator.estimate(calibration[(qi, ri)])
                 for qi in range(3) for ri in range(ROOTS)}
    condition_means = [float(np.mean([q_by_root[(qi, ri)] for ri in range(ROOTS)])) for qi in range(3)]
    gate_pass = condition_means[0] < condition_means[1] < condition_means[2]
    estimation_summary = {
        str(q): {
            "mean_qhat": float(np.mean([q_by_root[(qi, ri)] for ri in range(ROOTS)])),
            "bias": float(np.mean([q_by_root[(qi, ri)] for ri in range(ROOTS)]) - q),
            "mae": float(np.mean([abs(q_by_root[(qi, ri)] - q) for ri in range(ROOTS)])),
            "minimum_qhat": float(min(q_by_root[(qi, ri)] for ri in range(ROOTS))),
            "maximum_qhat": float(max(q_by_root[(qi, ri)] for ri in range(ROOTS))),
        } for qi, q in enumerate(V1_QS)
    }

    # Model construction uses only the V1 training/calibration detector arrays and fixed q metadata.
    construct_start = time.perf_counter()
    pooled_cal = np.vstack([calibration[(qi, ri)] for qi in range(3) for ri in range(ROOTS)])
    global_q = estimator.estimate(pooled_cal)
    model_a = build_matching(build_decomposed_dem(build_candidate_circuit(global_q)))
    base_matching = build_matching(build_decomposed_dem(build_base_circuit()))
    models_by_root = {}
    for qi, q in enumerate(V1_QS):
        for ri in range(ROOTS):
            qhat = q_by_root[(qi, ri)]
            a2 = build_matching(build_decomposed_dem(build_candidate_circuit(qhat)))
            b = BurstEnumerationDecoder(base_matching, events, qhat)
            c = BurstEnumerationDecoder(base_matching, events, q)
            models_by_root[(qi, ri)] = (a2, b, c)
    construction_seconds = time.perf_counter() - construct_start

    background_dem = build_decomposed_dem(build_base_circuit())
    fixture, fixture_inventory = deterministic_valid_fault_fixtures(background_dem, events)
    # Exercise a representative root for every condition on algebraic fault fixtures.
    arm_seconds = {arm: [] for arm in ("A", "A2", "B_C_shared")}
    difference_counts = {"B_vs_A": {}, "B_vs_A2": {}, "C_vs_A": {}}
    for qi, q in enumerate(V1_QS):
        a2, b, c = models_by_root[(qi, 0)]
        predictions = {}
        for arm, decoder in (("A", model_a), ("A2", a2)):
            t0 = time.perf_counter()
            pred = decoder.decode_batch(fixture, enable_correlations=True)
            arm_seconds[arm].append(time.perf_counter() - t0)
            if np.asarray(pred).shape != (len(fixture), 1) or not np.isin(pred, [0, 1]).all():
                raise RuntimeError(f"{arm} returned invalid fixture predictions")
            predictions[arm] = np.asarray(pred).reshape(-1)
        t0 = time.perf_counter()
        pred_b, pred_c = b.decode_pair_batch(fixture, c)
        arm_seconds["B_C_shared"].append(time.perf_counter() - t0)
        for arm, pred in (("B", pred_b), ("C", pred_c)):
            if np.asarray(pred).shape != (len(fixture), 1) or not np.isin(pred, [0, 1]).all():
                raise RuntimeError(f"{arm} returned invalid fixture predictions")
            predictions[arm] = np.asarray(pred).reshape(-1)
        difference_counts["B_vs_A"][str(q)] = int(np.count_nonzero(predictions["B"] != predictions["A"]))
        difference_counts["B_vs_A2"][str(q)] = int(np.count_nonzero(predictions["B"] != predictions["A2"]))
        difference_counts["C_vs_A"][str(q)] = int(np.count_nonzero(predictions["C"] != predictions["A"]))

    # Worst observed deterministic fixture cost per row, inflated 2x for a conservative screen.
    per_row = {arm: max(arm_seconds[arm]) / len(fixture) for arm in arm_seconds}
    total_inference_estimate = (per_row["A"] + per_row["A2"] + per_row["B_C_shared"]) * 60000 * 2.0
    # Reuse V1's recorded generation rate only as a rough lower-level projection; use 4x inflation.
    v1_sampling = reuse["v1_phase_sampling_seconds"]["calibration"]
    v1_rows = reuse["v1_phase_shots"]["calibration"]
    sampling_estimate = (60000 / max(v1_rows, 1)) * v1_sampling * 4.0
    analysis_allowance = 45.0
    estimated_total_seconds = construction_seconds + total_inference_estimate + sampling_estimate + analysis_allowance

    process = psutil.Process()
    mem = process.memory_info()
    peak_wset = getattr(mem, "peak_wset", None)
    if peak_wset is None:
        peak_wset = getattr(mem, "peak_wset_bytes", None)
    measured_wset = int(mem.rss if peak_wset is None else peak_wset)
    projected_process_peak = measured_wset * 2
    available_memory = int(psutil.virtual_memory().available)
    disk = psutil.disk_usage(str(REPO))
    env = {
        "python": sys.version.split()[0], "stim": stim.__version__,
        "pymatching": pymatching.__version__, "numpy": np.__version__, "psutil": psutil.__version__,
    }
    expected_env = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))["environment"]
    if env != expected_env:
        raise RuntimeError(f"environment differs from configuration: actual={env}, expected={expected_env}")

    output = {
        "schema": "qshift-correlated-decoder-v1.1-preflight-v1",
        "mode": "sampler-free detector-only reuse and deterministic fixture diagnostics",
        "sampler_calls": 0,
        "new_shots": 0,
        "reuse_verification_sha256": hashlib.sha256((ROOT / "REUSE_VERIFICATION.json").read_bytes()).hexdigest()
            if (ROOT / "REUSE_VERIFICATION.json").exists() else sha256_json(reuse),
        "v1_archive_count_verified": reuse["archive_count"],
        "reused_training_rows": int(len(train_y)),
        "reused_calibration_rows": int(sum(len(x) for x in calibration.values())),
        "reused_observable_values_read": False,
        "corrected_affine_fit": {
            "coefficient_order": "slope, intercept",
            "slope": estimator.slope,
            "intercept": estimator.intercept,
            "training_feature_rates_by_q": estimator.training_condition_rates,
        },
        "calibration_condition_mean_qhat": condition_means,
        "calibration_estimation_summary": estimation_summary,
        "calibration_condition_root_qhat": {
            str(q): [q_by_root[(qi, ri)] for ri in range(ROOTS)] for qi, q in enumerate(V1_QS)
        },
        "calibration_order_gate_pass": gate_pass,
        "pooled_global_A_qhat": global_q,
        "burst_event_signatures": [
            {"detectors": list(e.detector_ids), "observable_flip": e.observable_flip} for e in events
        ],
        "candidate_circuits": {
            str(q): {"detectors": build_candidate_circuit(q).num_detectors,
                     "observables": build_candidate_circuit(q).num_observables}
            for q in V1_QS
        },
        "models_constructed": 1 + 1 + 30 * 3,
        "deterministic_fixture_rows": len(fixture),
        "deterministic_fixture_inventory": fixture_inventory,
        "fixture_prediction_differences_only_not_accuracy_evidence": difference_counts,
        "model_construction_seconds": construction_seconds,
        "deterministic_fixture_total_seconds": {arm: float(sum(times)) for arm, times in arm_seconds.items()},
        "deterministic_fixture_max_seconds_per_row": per_row,
        "runtime_projection": {
            "evaluation_rows": 60000,
            "fixture_decoder_cost_inflation_factor": 2.0,
            "estimated_sampling_seconds_with_inflation": sampling_estimate,
            "analysis_allowance_seconds": analysis_allowance,
            "estimated_total_seconds": estimated_total_seconds,
            "wall_cap_seconds": 600,
            "within_cap": estimated_total_seconds < 600,
            "limitations": "fixture syndromes are not sampled or representative; projection has substantial uncertainty and is not an execution guarantee",
        },
        "resources": {
            "available_physical_memory_bytes": available_memory,
            "current_process_rss_bytes": int(mem.rss),
            "peak_working_set_bytes": None if peak_wset is None else int(peak_wset),
            "projected_peak_working_set_with_2x_margin_bytes": projected_process_peak,
            "projected_process_memory_fits_available_memory": available_memory >= projected_process_peak,
            "free_disk_bytes": int(disk.free),
            "minimum_free_disk_bytes": 1073741824,
            "artifact_limit_bytes": 268435456,
        },
        "environment": env,
        "preflight_elapsed_seconds": time.perf_counter() - started,
    }
    if gate_pass:
        output["status"] = "CALIBRATION_GATE_PASS"
    else:
        output["status"] = "CALIBRATION_GATE_FAIL_STOP_BEFORE_EVALUATION"
    out = ROOT / "REUSE_CALIBRATION_PREFLIGHT.json"
    out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: output[k] for k in (
        "status", "corrected_affine_fit", "calibration_condition_mean_qhat", "calibration_order_gate_pass",
        "pooled_global_A_qhat", "calibration_estimation_summary", "model_construction_seconds", "deterministic_fixture_max_seconds_per_row",
        "runtime_projection", "resources", "sampler_calls", "new_shots")}, indent=2))
    if not gate_pass:
        raise SystemExit("corrected calibration ordering gate failed; stop before evaluation")
    if estimated_total_seconds >= 600:
        raise SystemExit("deterministic preflight runtime projection exceeds 600-second cap; stop before evaluation")
    if disk.free < 1073741824:
        raise SystemExit("free disk below the frozen minimum; stop")
    if measured_wset >= 2147483648 or available_memory < projected_process_peak:
        raise SystemExit("measured/projected process working set is not feasible under current available memory")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v1-repo", type=Path, required=True)
    args = parser.parse_args()
    run(args.v1_repo.resolve())


if __name__ == "__main__":
    main()
