"""Bounded paired development pilot. Sampling is opt-in and freeze-gated."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import psutil
import stim
import pymatching

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from outputs.qshift_correlated_decoder_feasibility_v1.correlated_model import (
    BurstEnumerationDecoder, BurstRateEstimator, build_base_circuit,
    build_candidate_circuit, build_decomposed_dem, build_matching, extract_burst_events,
)
from outputs.qshift_correlated_decoder_feasibility_v1.analyze_saved import analyze_run

CONFIG_PATH = ROOT / "config.json"
INVENTORY_PATH = ROOT / "seed_inventory.json"
FREEZE_PATH = ROOT / "PRETEST_FREEZE.json"
RUNS_ROOT = ROOT / "pilot_runs"
RUN_ID = "attempt_001"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    except BaseException:
        try:
            os.unlink(name)
        except OSError:
            pass
        raise


def atomic_json(path: Path, value) -> None:
    atomic_bytes(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def atomic_npz(path: Path, **arrays) -> tuple[str, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            np.savez_compressed(f, **arrays)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    except BaseException:
        try:
            os.unlink(name)
        except OSError:
            pass
        raise
    raw = path.read_bytes()
    return hashlib.sha256(raw).hexdigest(), len(raw)


def source_hashes():
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    for relative, expected in freeze["files"].items():
        path = REPO / relative
        if not path.is_file() or sha256_file(path) != expected:
            raise RuntimeError(f"pretest freeze mismatch: {relative}")
    return freeze


def check_git_clean_and_branch():
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=REPO, text=True).strip()
    porcelain = subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO, text=True)
    if branch != "codex/qshift-correlated-decoder-feasibility-v1" or porcelain.strip():
        raise RuntimeError("execution requires the frozen branch and a clean worktree")
    return head, branch


class Guard:
    def __init__(self, config, run_dir=None):
        self.started = time.monotonic()
        self.max_wall = int(config["resource_limits"]["wall_seconds"])
        self.max_rss = int(config["resource_limits"]["sampled_peak_rss_bytes"])
        self.min_free = int(config["resource_limits"]["minimum_free_disk_bytes"])
        self.max_artifacts = int(config["resource_limits"]["maximum_run_artifact_bytes"])
        self.process = psutil.Process()
        self.peak_sampled_rss = 0
        self.run_dir = run_dir

    def check(self):
        elapsed = time.monotonic() - self.started
        rss = int(self.process.memory_info().rss)
        self.peak_sampled_rss = max(self.peak_sampled_rss, rss)
        free = int(shutil.disk_usage(ROOT).free)
        artifact_bytes = 0
        if self.run_dir and self.run_dir.exists():
            artifact_bytes = sum(p.stat().st_size for p in self.run_dir.rglob("*") if p.is_file())
        if elapsed >= self.max_wall:
            raise TimeoutError("600-second wall-clock deadline reached")
        if rss > self.max_rss:
            raise MemoryError("sampled process RSS exceeded configured cap")
        if free < self.min_free:
            raise OSError("free disk space fell below configured minimum")
        if artifact_bytes > self.max_artifacts:
            raise OSError("run artifacts exceeded configured cap")
        return {"elapsed_seconds": elapsed, "current_rss_bytes": rss,
                "sampled_peak_rss_bytes": self.peak_sampled_rss,
                "free_disk_bytes": free, "artifact_bytes": artifact_bytes}


def sample_partition(circuit: stim.Circuit, shots: int, seed: int):
    sampler = circuit.compile_detector_sampler(seed=int(seed))
    detectors, observables = sampler.sample(shots=int(shots), separate_observables=True)
    detectors = np.asarray(detectors, dtype=np.uint8)
    observables = np.asarray(observables, dtype=np.uint8)
    if detectors.shape != (shots, 40) or observables.shape != (shots, 1):
        raise RuntimeError("Stim returned unexpected detector/observable shape")
    if not np.isin(detectors, [0, 1]).all() or not np.isin(observables, [0, 1]).all():
        raise RuntimeError("Stim returned nonbinary samples")
    return detectors, observables


def sample_and_commit(circuit, shots, seed, phase, key, target, state, guard):
    guard.check()
    calls = len(state["sampler_calls_started"])
    if calls >= 63 or state["shots_started"] + shots > 78000:
        raise RuntimeError("frozen sampler-call or shot ceiling would be exceeded")
    call = {"sequence": calls + 1, "phase": phase, "key": key, "seed": int(seed),
            "shots": int(shots), "state": "started", "started_utc": datetime.now(timezone.utc).isoformat()}
    state["sampler_calls_started"].append(call)
    state["shots_started"] += int(shots)
    atomic_json(target.parent.parent / "status.json", state)
    sample_started = time.perf_counter()
    detectors, observables = sample_partition(circuit, shots, seed)
    call["sampling_seconds"] = time.perf_counter() - sample_started
    guard.check()
    write_started = time.perf_counter()
    digest, size = atomic_npz(target, detectors=detectors, observables=observables)
    call["archive_write_seconds"] = time.perf_counter() - write_started
    call["state"] = "committed"
    call["archive"] = str(target.relative_to(target.parents[2])).replace("\\", "/")
    call["archive_sha256"] = digest
    call["archive_bytes"] = size
    call["committed_utc"] = datetime.now(timezone.utc).isoformat()
    state["shots_committed"] += int(shots)
    state["archives"].append({"path": call["archive"], "sha256": digest,
                              "bytes": size, "shots": int(shots),
                              "sampling_seconds": call["sampling_seconds"],
                              "archive_write_seconds": call["archive_write_seconds"]})
    atomic_json(target.parent.parent / "status.json", state)
    guard.check()
    return detectors, observables


def build_prediction_models(config, estimator, train_x, calibration, q_values):
    construction = {"A": 0.0, "A2": 0.0, "B": 0.0, "C": 0.0}
    pooled_x = np.vstack([calibration[(qi, ri)] for qi in range(3) for ri in range(10)])
    global_q = estimator.estimate(pooled_x)
    t = time.perf_counter()
    base_matching = build_matching(build_decomposed_dem(build_base_circuit()))
    events = extract_burst_events()
    construction["B"] += time.perf_counter() - t
    t = time.perf_counter()
    a_matching = build_matching(build_decomposed_dem(build_candidate_circuit(global_q)))
    construction["A"] = time.perf_counter() - t
    models = {"A": a_matching}
    estimates = {"global_A_q": global_q, "root_q": {}}
    for qi, q in enumerate(q_values):
        for ri in range(10):
            qhat = estimator.estimate(calibration[(qi, ri)])
            estimates["root_q"][f"q{qi}_r{ri:02d}"] = qhat
            t = time.perf_counter()
            p_match = build_matching(build_decomposed_dem(build_candidate_circuit(qhat)))
            construction["A2"] += time.perf_counter() - t
            models[f"A2:{qi}:{ri}"] = p_match
            t = time.perf_counter()
            models[f"B:{qi}:{ri}"] = BurstEnumerationDecoder(base_matching, events, qhat)
            construction["B"] += time.perf_counter() - t
            t = time.perf_counter()
            models[f"C:{qi}:{ri}"] = BurstEnumerationDecoder(base_matching, events, q)
            construction["C"] += time.perf_counter() - t
    return models, estimates, construction

def dry_run(config, inventory):
    events = extract_burst_events()
    for q in config["candidate_noise"]["probabilities"]:
        c = build_candidate_circuit(q)
        dem = build_decomposed_dem(c)
        m = build_matching(dem)
        if c.num_detectors != 40 or c.num_observables != 1 or m.num_detectors != 40:
            raise RuntimeError("deterministic circuit/DEM/decoder preflight failed")
    seed_values = list(inventory["seeds"].values())
    if len(seed_values) != 65 or len(set(seed_values)) != 65:
        raise RuntimeError("seed inventory completeness/uniqueness failed")
    print(json.dumps({"mode": "dry-run", "sampler_calls": 0, "shots": 0,
                      "demonstrated_event_factors": len(events), "candidate_q_values": 3,
                      "planned_shots": 78000, "planned_sampler_calls": 63}, indent=2))


def execute(config, inventory, expected_head):
    if os.environ.get("QSHIFT_V1_WATCHDOG_ACTIVE") != "1":
        raise RuntimeError("execution is allowed only under the Windows wall-clock wrapper")
    parent = psutil.Process().parent()
    if parent is None:
        raise RuntimeError("execution supervisor parent is unavailable")
    parent_cmd = parent.cmdline()
    expected_wrapper = str(ROOT / "run_watchdog.py").casefold()
    if len(parent_cmd) < 2 or str(Path(parent_cmd[1]).resolve()).casefold() != expected_wrapper:
        raise RuntimeError("execution parent is not the versioned Windows wall-clock wrapper")
    freeze = source_hashes()
    head, branch = check_git_clean_and_branch()
    if head != expected_head:
        raise RuntimeError("current HEAD does not match the explicitly reviewed freeze commit")
    if stim.__version__ != config["environment"]["stim"] or pymatching.__version__ != config["environment"]["pymatching"] or np.__version__ != config["environment"]["numpy"] or psutil.__version__ != config["environment"]["psutil"]:
        raise RuntimeError("locked runtime version mismatch")
    if sys.version.split()[0] != config["environment"]["python"]:
        raise RuntimeError("Python version mismatch")
    run_dir = RUNS_ROOT / RUN_ID
    if run_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing attempt: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=False)
    for name in ("training", "calibration", "evaluation"):
        (run_dir / name).mkdir()
    guard = Guard(config, run_dir)
    state = {"schema": "qshift-correlated-pilot-status-v1", "run_id": RUN_ID,
             "state": "running", "phase": "initializing", "sampler_calls_started": [],
             "shots_started": 0, "shots_committed": 0, "archives": [],
             "started_utc": datetime.now(timezone.utc).isoformat(), "failure": None}
    atomic_json(run_dir / "status.json", state)
    try:
        atomic_json(run_dir / "execution_identity.json", {
            "git_head": head, "branch": branch, "pretest_freeze_sha256": sha256_file(FREEZE_PATH),
            "config_sha256": sha256_file(CONFIG_PATH), "protocol_sha256": sha256_file(ROOT / "EXPERIMENT_PROTOCOL.md"),
            "seed_inventory_sha256": sha256_file(INVENTORY_PATH), "python": sys.version,
            "stim": stim.__version__, "pymatching": pymatching.__version__, "numpy": np.__version__,
            "reference_commit": freeze["reference_commit"]})
        q_values = config["candidate_noise"]["probabilities"]
        seed_map = inventory["seeds"]
        train = {}
        for qi, q in enumerate(q_values):
            state["phase"] = "training"
            x, _ = sample_and_commit(build_candidate_circuit(q), 1000, seed_map[f"train:q{q:.2f}"],
                                     "training", f"q{q:.2f}", run_dir / "training" / f"train_q{qi}.npz", state, guard)
            train[q] = x
        train_x = np.vstack([train[q] for q in q_values])
        train_y = np.concatenate([np.full(len(train[q]), q, dtype=np.float64) for q in q_values])
        estimator = BurstRateEstimator(extract_burst_events()).fit(train_x, train_y)
        atomic_json(run_dir / "training" / "estimator.json", {
            "method": "training-only affine mean triple-cofire calibration", "intercept": estimator.intercept,
            "slope": estimator.slope, "training_condition_rates": estimator.training_condition_rates})
        calibration = {}
        calibration_estimates = {}
        for qi, q in enumerate(q_values):
            for ri in range(10):
                key = f"cal:q{q:.2f}:r{ri:02d}"
                x, _ = sample_and_commit(build_candidate_circuit(q), 500, seed_map[key],
                    "calibration", key, run_dir / "calibration" / f"cal_q{qi}_r{ri:02d}.npz", state, guard)
                calibration[(qi, ri)] = x
                calibration_estimates[f"q{qi}_r{ri:02d}"] = estimator.estimate(x)
        means = {str(q): float(np.mean([calibration_estimates[f"q{qi}_r{ri:02d}"] for ri in range(10)]))
                 for qi, q in enumerate(q_values)}
        ordered = means["0.0"] < means["0.01"] < means["0.02"]
        atomic_json(run_dir / "calibration" / "diagnostics.json", {
            "mean_qhat_by_condition": means, "condition_order_gate_passed": ordered,
            "per_root_qhat": calibration_estimates, "generating_q_metadata_for_scoring_only": q_values})
        state["phase"] = "calibration_gate"
        if not ordered:
            state["state"] = "inconclusive_calibration_gate"
            state["completed_utc"] = datetime.now(timezone.utc).isoformat()
            state["shots_committed"] = sum(x["shots"] for x in state["archives"])
            atomic_json(run_dir / "status.json", state)
            return run_dir
        models, estimates, construction_timing = build_prediction_models(config, estimator, train_x, calibration, q_values)
        atomic_json(run_dir / "models_frozen.json", {"global_A_q": estimates["global_A_q"],
            "root_q": estimates["root_q"], "candidate_q_values": q_values,
            "model_choice_frozen_before_evaluation": True,
            "A2_and_B_use_same_per_root_estimates": True,
            "C_privileged_true_q": True})
        timing = {"A": 0.0, "A2": 0.0, "B": 0.0, "C": 0.0}
        archive_write_seconds = 0.0
        eval_dir = run_dir / "evaluation"
        for qi, q in enumerate(q_values):
            for ri in range(10):
                guard.check()
                key = f"eval:q{q:.2f}:r{ri:02d}"
                detectors, labels = sample_and_commit(build_candidate_circuit(q), 2000, seed_map[key],
                    "evaluation", key, eval_dir / f"sample_q{qi}_r{ri:02d}.npz", state, guard)
                t = time.perf_counter(); pred_a = np.asarray(models["A"].decode_batch(detectors, enable_correlations=True), dtype=np.uint8).reshape(-1, 1); timing["A"] += time.perf_counter() - t
                t = time.perf_counter(); pred_a2 = np.asarray(models[f"A2:{qi}:{ri}"].decode_batch(detectors, enable_correlations=True), dtype=np.uint8).reshape(-1, 1); timing["A2"] += time.perf_counter() - t
                t = time.perf_counter(); pred_b = models[f"B:{qi}:{ri}"].decode_batch(detectors); timing["B"] += time.perf_counter() - t
                t = time.perf_counter(); pred_c = models[f"C:{qi}:{ri}"].decode_batch(detectors); timing["C"] += time.perf_counter() - t
                preds = {"A": pred_a, "A2": pred_a2, "B": pred_b, "C": pred_c}
                if any(p.shape != (2000, 1) or not np.isin(p, [0, 1]).all() for p in preds.values()):
                    raise RuntimeError("decoder returned invalid prediction shape or values")
                # Observable labels are first used here, after every decoder prediction is complete.
                target = eval_dir / f"eval_q{qi}_r{ri:02d}.npz"
                write_started = time.perf_counter()
                digest, size = atomic_npz(target, detectors=detectors, observables=labels,
                                          pred_A=pred_a, pred_A2=pred_a2, pred_B=pred_b, pred_C=pred_c)
                archive_write_seconds += time.perf_counter() - write_started
                state["archives"].append({"path": str(target.relative_to(run_dir)).replace("\\", "/"),
                    "sha256": digest, "bytes": size, "shots": 2000, "kind": "paired_predictions"})
                atomic_json(run_dir / "status.json", state)
                guard.check()
        state["phase"] = "analysis"
        atomic_json(run_dir / "status.json", state)
        result = analyze_run(run_dir, inventory)
        result["runtime_seconds_excluding_final_report"] = time.monotonic() - guard.started
        result["decoder_inference_seconds"] = timing
        result["decoder_construction_seconds"] = construction_timing
        result["paired_archive_write_seconds"] = archive_write_seconds
        result["sampler_seconds_by_partition"] = {phase: sum(x.get("sampling_seconds", 0.0) for x in state["sampler_calls_started"] if x["phase"] == phase) for phase in ("training", "calibration", "evaluation")}
        result["resource_observations"] = guard.check()
        atomic_json(run_dir / "analysis.json", result)
        state["state"] = "completed"
        state["phase"] = "complete"
        state["shots_committed"] = sum(x["shots"] for x in state["archives"] if x.get("kind") != "paired_predictions")
        state["completed_utc"] = datetime.now(timezone.utc).isoformat()
        state["runtime_seconds"] = time.monotonic() - guard.started
        state["sampled_peak_rss_bytes"] = guard.peak_sampled_rss
        state["artifact_bytes"] = sum(p.stat().st_size for p in run_dir.rglob("*") if p.is_file())
        atomic_json(run_dir / "status.json", state)
        manifest = {"run_id": RUN_ID, "state": state["state"], "shots_committed": state["shots_committed"],
                    "sampler_calls_started": len(state["sampler_calls_started"]), "archives": state["archives"],
                    "analysis_sha256": sha256_file(run_dir / "analysis.json"),
                    "runtime_seconds": state["runtime_seconds"], "sampled_peak_rss_bytes": state["sampled_peak_rss_bytes"]}
        atomic_json(run_dir / "run_manifest.json", manifest)
        guard.check()
        print(json.dumps({"run_dir": str(run_dir), "status": state["state"],
                          "shots": state["shots_committed"], "sampler_calls": len(state["sampler_calls_started"]),
                          "analysis": result["decision"], "runtime_seconds": state["runtime_seconds"],
                          "decoder_inference_seconds": timing}, indent=2))
        return run_dir
    except BaseException as exc:
        state["state"] = "failed"
        state["failure"] = {"type": type(exc).__name__, "message": str(exc),
                            "utc": datetime.now(timezone.utc).isoformat()}
        try:
            atomic_json(run_dir / "status.json", state)
        except BaseException:
            pass
        raise


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="sampler-free deterministic preflight (default)")
    mode.add_argument("--execute", action="store_true", help="run the frozen bounded development pilot")
    parser.add_argument("--expected-head", help="required exact commit SHA when --execute is used")
    args = parser.parse_args()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    if args.execute:
        if not args.expected_head or len(args.expected_head) != 40:
            raise SystemExit("--execute requires --expected-head <40-character commit SHA>")
        execute(config, inventory, args.expected_head)
    else:
        dry_run(config, inventory)

if __name__ == "__main__":
    main()
