"""Single V1.1 paired evaluation runner. Sampling is explicitly freeze-gated."""
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
import pymatching
import stim

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from outputs.qshift_correlated_decoder_feasibility_v1_1.analyze_saved import analyze
from outputs.qshift_correlated_decoder_feasibility_v1_1.model import (
    BurstEnumerationDecoder,
    BurstRateEstimator,
    build_base_circuit,
    build_candidate_circuit,
    build_decomposed_dem,
    build_matching,
    extract_burst_events,
)
from outputs.qshift_correlated_decoder_feasibility_v1_1.verify_reuse import verify as verify_reuse


CONFIG_PATH = ROOT / "config.json"
INVENTORY_PATH = ROOT / "seed_inventory.json"
FREEZE_PATH = ROOT / "PRETEST_FREEZE.json"
REUSE_PATH = ROOT / "REUSE_VERIFICATION.json"
PREFLIGHT_PATH = ROOT / "REUSE_CALIBRATION_PREFLIGHT.json"
RUN_DIR = ROOT / "pilot_runs/attempt_001"
QS = (0.0, 0.01, 0.02)
N_ROOTS = 10
SHOTS_PER_ROOT = 2000
MAX_SHOTS = 60000
MAX_CALLS = 30
WATCHDOG_ENV = "QSHIFT_V1_1_WATCHDOG_ACTIVE"
BRANCH = "codex/qshift-correlated-decoder-feasibility-v1-1"
V1_ROOT_DEFAULT = REPO.parent / "qshift-correlated-decoder-feasibility-v1"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def atomic_json(path: Path, value) -> None:
    atomic_bytes(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def atomic_npz(path: Path, **arrays) -> tuple[str, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            np.savez_compressed(stream, **arrays)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise
    raw = path.read_bytes()
    return hashlib.sha256(raw).hexdigest(), len(raw)


def git_output(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


def check_git(expected_head: str) -> tuple[str, str]:
    head = git_output("rev-parse", "HEAD")
    branch = git_output("branch", "--show-current")
    status = git_output("status", "--porcelain", "--untracked-files=normal")
    if head != expected_head:
        raise RuntimeError("current HEAD does not match the authorized frozen source commit")
    if branch != BRANCH:
        raise RuntimeError(f"execution requires branch {BRANCH}")
    if status:
        raise RuntimeError("execution requires a clean worktree")
    return head, branch


def verify_freeze() -> dict:
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    if freeze.get("schema") != "qshift-correlated-decoder-v1.1-pretest-freeze-v1":
        raise RuntimeError("unsupported V1.1 source-freeze schema")
    for relative, expected in freeze.get("files", {}).items():
        path = REPO / relative
        if not path.is_file() or sha256_file(path) != expected:
            raise RuntimeError(f"pretest source/configuration hash mismatch: {relative}")
    if not freeze.get("files"):
        raise RuntimeError("empty pretest source freeze")
    return freeze


def check_environment(config: dict) -> dict:
    actual = {
        "python": sys.version.split()[0],
        "stim": stim.__version__,
        "pymatching": pymatching.__version__,
        "numpy": np.__version__,
        "psutil": psutil.__version__,
    }
    if actual != config["environment"]:
        raise RuntimeError(f"runtime environment mismatch: {actual}")
    return actual


def check_reuse(v1_repo: Path) -> dict:
    verified = verify_reuse(v1_repo.resolve())
    recorded = json.loads(REUSE_PATH.read_text(encoding="utf-8"))
    if verified != recorded:
        raise RuntimeError("V1 archive reuse verification no longer matches the frozen record")
    return verified


def load_detector(path: Path, expected_rows: int) -> np.ndarray:
    # The observable member is intentionally never accessed in V1.1 setup.
    with np.load(path, allow_pickle=False) as archive:
        x = np.asarray(archive["detectors"])
    if x.shape != (expected_rows, 40) or not np.isin(x, [0, 1]).all():
        raise ValueError(f"invalid reused detector array: {path.name}")
    return x.astype(np.uint8, copy=False)


def load_training_and_calibration(v1_repo: Path):
    old_run = v1_repo / "outputs/qshift_correlated_decoder_feasibility_v1/pilot_runs/attempt_001"
    xparts, yparts, calibration = [], [], {}
    for qi, q in enumerate(QS):
        x = load_detector(old_run / f"training/train_q{qi}.npz", 1000)
        xparts.append(x)
        yparts.append(np.full(1000, q, dtype=np.float64))
        for ri in range(N_ROOTS):
            calibration[(qi, ri)] = load_detector(old_run / f"calibration/cal_q{qi}_r{ri:02d}.npz", 500)
    return np.vstack(xparts), np.concatenate(yparts), calibration


class ResourceGuard:
    def __init__(self, config: dict, run_dir: Path):
        limits = config["resource_limits"]
        self.deadline = time.monotonic() + int(limits["wall_seconds"])
        self.max_rss = int(limits["sampled_peak_rss_bytes"])
        self.min_free = int(limits["minimum_free_disk_bytes"])
        self.max_artifacts = int(limits["maximum_run_artifact_bytes"])
        self.process = psutil.Process()
        self.run_dir = run_dir
        self.peak_rss = 0

    def check(self) -> dict:
        now = time.monotonic()
        current = int(self.process.memory_info().rss)
        self.peak_rss = max(self.peak_rss, current)
        free = int(shutil.disk_usage(str(REPO)).free)
        artifact_bytes = sum(p.stat().st_size for p in self.run_dir.rglob("*") if p.is_file()) if self.run_dir.exists() else 0
        if now >= self.deadline:
            raise TimeoutError("V1.1 600-second end-to-end deadline reached")
        if current > self.max_rss:
            raise MemoryError("sampled current-process RSS exceeded the frozen 2-GiB ceiling")
        if free < self.min_free:
            raise OSError("free disk space fell below the frozen 1-GiB minimum")
        if artifact_bytes > self.max_artifacts:
            raise OSError("run artifacts exceeded the frozen 256-MiB cap")
        return {"elapsed_seconds": None, "current_rss_bytes": current,
                "sampled_current_rss_high_water_bytes": self.peak_rss,
                "free_disk_bytes": free, "run_artifact_bytes": artifact_bytes}


def check_watchdog_parent() -> None:
    if os.name != "nt" or os.environ.get(WATCHDOG_ENV) != "1":
        raise RuntimeError("execution is allowed only under the V1.1 Windows watchdog")
    parent = psutil.Process().parent()
    if parent is None:
        raise RuntimeError("execution supervisor process is unavailable")
    command = parent.cmdline()
    expected = str((ROOT / "run_watchdog.py").resolve()).casefold()
    if len(command) < 2 or str(Path(command[1]).resolve()).casefold() != expected:
        raise RuntimeError("execution parent is not the versioned V1.1 watchdog")


def record_calibration(estimator, calibration, q_values: tuple[float, ...]) -> tuple[dict, float]:
    by_root = {f"q{qi}_r{ri:02d}": float(estimator.estimate(calibration[(qi, ri)]))
               for qi in range(3) for ri in range(N_ROOTS)}
    means = {str(q): float(np.mean([by_root[f"q{qi}_r{ri:02d}"] for ri in range(N_ROOTS)]))
             for qi, q in enumerate(q_values)}
    ordered = means["0.0"] < means["0.01"] < means["0.02"]
    pooled = np.vstack([calibration[(qi, ri)] for qi in range(3) for ri in range(N_ROOTS)])
    global_q = float(estimator.estimate(pooled))
    return {"per_root_qhat": by_root, "mean_qhat_by_condition": means,
            "condition_order_gate_passed": ordered}, global_q


def construct_models(estimator, calibration, global_q: float):
    events = extract_burst_events()
    construction_started = time.perf_counter()
    model_a = build_matching(build_decomposed_dem(build_candidate_circuit(global_q)))
    base_matching = build_matching(build_decomposed_dem(build_base_circuit()))
    models = {}
    for qi, q in enumerate(QS):
        for ri in range(N_ROOTS):
            qhat = float(estimator.estimate(calibration[(qi, ri)]))
            model_a2 = build_matching(build_decomposed_dem(build_candidate_circuit(qhat)))
            model_b = BurstEnumerationDecoder(base_matching, events, qhat)
            model_c = BurstEnumerationDecoder(base_matching, events, q)
            models[(qi, ri)] = (model_a2, model_b, model_c)
    return model_a, models, time.perf_counter() - construction_started


def sample_one(circuit: stim.Circuit, shots: int, seed: int):
    sampler = circuit.compile_detector_sampler(seed=int(seed))
    # The labels are held but not examined or passed to decoders until all four predictions exist.
    detectors, labels = sampler.sample(shots=shots, separate_observables=True)
    detectors = np.asarray(detectors, dtype=np.uint8)
    if detectors.shape != (shots, 40) or not np.isin(detectors, [0, 1]).all():
        raise RuntimeError("Stim returned invalid detector samples")
    return detectors, labels


def execute(expected_head: str, v1_repo: Path) -> Path:
    check_watchdog_parent()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    freeze = verify_freeze()
    head, branch = check_git(expected_head)
    environment = check_environment(config)
    reuse = check_reuse(v1_repo)
    preflight = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))
    if preflight.get("status") != "CALIBRATION_GATE_PASS" or not preflight.get("runtime_projection", {}).get("within_cap"):
        raise RuntimeError("frozen sampler-free preflight did not pass the calibration and runtime gates")
    if RUN_DIR.exists():
        raise FileExistsError(f"refusing to overwrite or retry existing V1.1 run directory {RUN_DIR}")
    if len(inventory.get("seeds", {})) != 32 or not inventory.get("disjoint_from_screened_inventories"):
        raise RuntimeError("V1.1 seed inventory is incomplete or collision screening failed")
    eval_seed_labels = {f"evaluation:q{q:.2f}:root{ri:02d}" for q in QS for ri in range(N_ROOTS)}
    if not eval_seed_labels.issubset(inventory["seeds"]):
        raise RuntimeError("V1.1 evaluation seed mapping is incomplete")

    RUN_DIR.mkdir(parents=True, exist_ok=False)
    (RUN_DIR / "evaluation").mkdir()
    guard = ResourceGuard(config, RUN_DIR)
    started = time.monotonic()
    state = {
        "schema": "qshift-correlated-decoder-v1.1-run-status-v1",
        "run_id": "attempt_001",
        "state": "running",
        "phase": "initialization",
        "sampler_calls_started": [],
        "shots_started": 0,
        "shots_committed": 0,
        "archives": [],
        "failure": None,
        "started_utc": datetime.now(timezone.utc).isoformat(),
    }
    atomic_json(RUN_DIR / "status.json", state)
    try:
        identity = {
            "schema": "qshift-correlated-decoder-v1.1-execution-identity-v1",
            "git_head": head,
            "branch": branch,
            "pretest_freeze_sha256": sha256_file(FREEZE_PATH),
            "config_sha256": sha256_file(CONFIG_PATH),
            "protocol_sha256": sha256_file(ROOT / "EXPERIMENT_PROTOCOL.md"),
            "seed_inventory_sha256": sha256_file(INVENTORY_PATH),
            "reuse_verification_sha256": sha256_file(REUSE_PATH),
            "preflight_sha256": sha256_file(PREFLIGHT_PATH),
            "v1_source_commit": reuse["source_v1_completed_commit"],
            "v1_attempt_source_commit": reuse["source_v1_attempt_commit"],
            "python": sys.version,
            "stim": stim.__version__,
            "pymatching": pymatching.__version__,
            "numpy": np.__version__,
            "psutil": psutil.__version__,
            "evaluation_labels_exposed_to_decoders": False,
            "labels_access_order": "for each root, all four predictions are computed before label shape/value validation or scoring",
        }
        atomic_json(RUN_DIR / "execution_identity.json", identity)
        guard.check()

        state["phase"] = "load_reused_detector_arrays"
        atomic_json(RUN_DIR / "status.json", state)
        train_x, train_y, calibration = load_training_and_calibration(v1_repo.resolve())
        estimator = BurstRateEstimator(extract_burst_events()).fit(train_x, train_y)
        train_summary = {
            "coefficient_order": "slope, intercept",
            "slope": estimator.slope,
            "intercept": estimator.intercept,
            "training_condition_feature_rates": estimator.training_condition_rates,
            "training_detector_rows_reused": int(len(train_y)),
            "training_observable_arrays_read": False,
        }
        calibration_diag, global_q = record_calibration(estimator, calibration, QS)
        if not calibration_diag["condition_order_gate_passed"]:
            raise RuntimeError("corrected calibration condition-order gate failed before evaluation")
        if estimator.slope <= 0:
            raise RuntimeError("corrected training slope is not positive")
        cal_summary = {
            **calibration_diag,
            "estimation_summary": {
                str(q): {
                    "mean_qhat": float(np.mean([calibration_diag["per_root_qhat"][f"q{qi}_r{ri:02d}"] for ri in range(N_ROOTS)])),
                    "bias": float(np.mean([calibration_diag["per_root_qhat"][f"q{qi}_r{ri:02d}"] for ri in range(N_ROOTS)]) - q),
                    "mae": float(np.mean([abs(calibration_diag["per_root_qhat"][f"q{qi}_r{ri:02d}"] - q) for ri in range(N_ROOTS)])),
                } for qi, q in enumerate(QS)
            },
            "calibration_detector_rows_reused": 15000,
            "calibration_observable_arrays_read": False,
        }
        atomic_json(RUN_DIR / "training_summary.json", train_summary)
        atomic_json(RUN_DIR / "calibration_diagnostics.json", cal_summary)
        guard.check()

        state["phase"] = "construct_and_freeze_models"
        atomic_json(RUN_DIR / "status.json", state)
        construction_started = time.perf_counter()
        model_a, models, explicit_construction = construct_models(estimator, calibration, global_q)
        construction_seconds = time.perf_counter() - construction_started
        models_frozen = {
            "schema": "qshift-correlated-decoder-v1.1-frozen-models-v1",
            "model_choice_frozen_before_evaluation": True,
            "A_global_qhat": global_q,
            "root_qhat": calibration_diag["per_root_qhat"],
            "A2_B_same_per_root_qhat": True,
            "C_privileged_true_q": {f"q{qi}": q for qi, q in enumerate(QS)},
            "B_C_shared_residual_decode_optimization": "exact reuse only; tested bit-identical to separate calls",
            "model_construction_seconds": construction_seconds,
            "explicit_build_seconds": explicit_construction,
        }
        atomic_json(RUN_DIR / "models_frozen.json", models_frozen)
        guard.check()

        circuits = {qi: build_candidate_circuit(q) for qi, q in enumerate(QS)}
        eval_dir = RUN_DIR / "evaluation"
        inference_seconds = {arm: 0.0 for arm in ("A", "A2", "B_C_shared")}
        sampling_seconds = 0.0
        archive_seconds = 0.0
        for qi, q in enumerate(QS):
            for ri in range(N_ROOTS):
                guard.check()
                if len(state["sampler_calls_started"]) >= MAX_CALLS or state["shots_started"] + SHOTS_PER_ROOT > MAX_SHOTS:
                    raise RuntimeError("frozen evaluation call/shot allocation would be exceeded")
                key = f"evaluation:q{q:.2f}:root{ri:02d}"
                seed = int(inventory["seeds"][key])
                if not 0 < seed < 2**31:
                    raise RuntimeError(f"invalid frozen Stim seed for {key}")
                sample_id = hashlib.sha256(f"qshift-v1.1:{key}:{seed}".encode("utf-8")).hexdigest()
                call = {"sequence": len(state["sampler_calls_started"]) + 1,
                        "phase": "evaluation", "key": key, "condition_q": q, "root": ri,
                        "seed": seed, "sample_id": sample_id, "shots": SHOTS_PER_ROOT, "state": "started",
                        "started_utc": datetime.now(timezone.utc).isoformat()}
                state["sampler_calls_started"].append(call)
                state["shots_started"] += SHOTS_PER_ROOT
                atomic_json(RUN_DIR / "status.json", state)
                guard.check()
                sample_started = time.perf_counter()
                detectors, labels = sample_one(circuits[qi], SHOTS_PER_ROOT, seed)
                call["sampling_seconds"] = time.perf_counter() - sample_started
                sampling_seconds += call["sampling_seconds"]
                guard.check()

                a2, b, c = models[(qi, ri)]
                pred_started = time.perf_counter()
                pred_a = np.asarray(model_a.decode_batch(detectors, enable_correlations=True), dtype=np.uint8).reshape(-1, 1)
                inference_seconds["A"] += time.perf_counter() - pred_started
                pred_started = time.perf_counter()
                pred_a2 = np.asarray(a2.decode_batch(detectors, enable_correlations=True), dtype=np.uint8).reshape(-1, 1)
                inference_seconds["A2"] += time.perf_counter() - pred_started
                pred_started = time.perf_counter()
                pred_b, pred_c = b.decode_pair_batch(detectors, c)
                inference_seconds["B_C_shared"] += time.perf_counter() - pred_started
                predictions = {"A": pred_a, "A2": pred_a2, "B": pred_b, "C": pred_c}
                if any(p.shape != (SHOTS_PER_ROOT, 1) or p.dtype != np.uint8 or not np.isin(p, [0, 1]).all()
                       for p in predictions.values()):
                    raise RuntimeError("decoder prediction contract failed")

                # Only now may the corresponding logical-observable array be inspected.
                labels = np.asarray(labels, dtype=np.uint8)
                if labels.shape != (SHOTS_PER_ROOT, 1) or not np.isin(labels, [0, 1]).all():
                    raise RuntimeError("Stim returned invalid observable labels after prediction completion")
                target = eval_dir / f"eval_q{qi}_r{ri:02d}.npz"
                archive_started = time.perf_counter()
                archive_hash, archive_bytes = atomic_npz(
                    target, detectors=detectors, observables=labels,
                    pred_A=pred_a, pred_A2=pred_a2, pred_B=pred_b, pred_C=pred_c,
                )
                archive_seconds += time.perf_counter() - archive_started
                call.update({"state": "committed", "archive": f"evaluation/{target.name}",
                             "archive_sha256": archive_hash, "archive_bytes": archive_bytes,
                             "committed_utc": datetime.now(timezone.utc).isoformat()})
                state["archives"].append({"path": call["archive"], "sha256": archive_hash,
                                          "bytes": archive_bytes, "shots": SHOTS_PER_ROOT})
                state["shots_committed"] += SHOTS_PER_ROOT
                state["completed_roots"] = state.get("completed_roots", 0) + 1
                atomic_json(RUN_DIR / "status.json", state)
                guard.check()

        if state["shots_committed"] != MAX_SHOTS or state.get("completed_roots") != 30:
            raise RuntimeError("evaluation allocation is incomplete")
        state["phase"] = "independent_saved_array_analysis"
        state["state"] = "evaluation_complete_pending_independent_analysis"
        state["timings"] = {"sampling_seconds": sampling_seconds,
                            "inference_seconds": inference_seconds,
                            "archive_write_seconds": archive_seconds,
                            "model_construction_seconds": construction_seconds}
        atomic_json(RUN_DIR / "status.json", state)
        guard.check()

        analysis_started = time.perf_counter()
        result = analyze(RUN_DIR)
        analysis_seconds = time.perf_counter() - analysis_started
        guard.check()
        state["phase"] = "finalization"
        state["independent_analysis_seconds"] = analysis_seconds
        state["analysis_sha256"] = sha256_file(RUN_DIR / "analysis.json")
        state["paired_results_sha256"] = sha256_file(RUN_DIR / "paired_results.csv")
        state["resource_observations"] = guard.check()
        state["runtime_seconds_before_final_status"] = time.monotonic() - started
        state["sampled_current_rss_high_water_bytes"] = guard.peak_rss
        state["state"] = "completed"
        state["phase"] = "complete"
        state["completed_utc"] = datetime.now(timezone.utc).isoformat()
        manifest = {
            "schema": "qshift-correlated-decoder-v1.1-run-manifest-v1",
            "source_commit": head,
            "pretest_freeze_sha256": sha256_file(FREEZE_PATH),
            "total_shots": state["shots_committed"],
            "sampler_calls": len(state["sampler_calls_started"]),
            "roots": state.get("completed_roots"),
            "analysis_sha256": state["analysis_sha256"],
            "paired_results_sha256": state["paired_results_sha256"],
            "archive_manifest": state["archives"],
            "decision": result["decision"],
            "runtime_seconds": state["runtime_seconds_before_final_status"],
        }
        atomic_json(RUN_DIR / "run_manifest.json", manifest)
        state["run_manifest_sha256"] = sha256_file(RUN_DIR / "run_manifest.json")
        atomic_json(RUN_DIR / "status.json", state)
        guard.check()
        print(json.dumps({"status": state["state"], "shots": state["shots_committed"],
                          "sampler_calls": len(state["sampler_calls_started"]),
                          "decision": result["decision"],
                          "runtime_seconds": time.monotonic() - started,
                          "inference_seconds": inference_seconds}, indent=2))
        return RUN_DIR
    except BaseException as exc:
        state["state"] = "failed"
        state["failure"] = {"type": type(exc).__name__, "message": str(exc),
                            "utc": datetime.now(timezone.utc).isoformat()}
        try:
            atomic_json(RUN_DIR / "status.json", state)
        except BaseException:
            pass
        raise


def dry_run(expected_head: str | None, v1_repo: Path) -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    freeze = verify_freeze()
    if expected_head:
        check_git(expected_head)
    environment = check_environment(config)
    reuse = check_reuse(v1_repo)
    preflight = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))
    if preflight.get("status") != "CALIBRATION_GATE_PASS":
        raise RuntimeError("frozen corrected-calibration gate is not passing")
    if len(inventory.get("seeds", {})) != 32 or len(freeze.get("files", {})) < 10:
        raise RuntimeError("seed inventory or source freeze is incomplete")
    print(json.dumps({"mode": "dry-run", "sampler_calls": 0, "shots": 0,
                      "new_evaluation_shots_authorized": 60000,
                      "v1_reuse_archive_count": reuse["archive_count"],
                      "calibration_gate": preflight["status"],
                      "runtime_projection": preflight["runtime_projection"],
                      "environment": environment,
                      "frozen_file_count": len(freeze["files"])}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true", help="sampler-free validation (default)")
    modes.add_argument("--execute", action="store_true", help="single frozen V1.1 evaluation")
    parser.add_argument("--expected-head", help="exact committed V1.1 source SHA")
    parser.add_argument("--v1-repo", type=Path, default=V1_ROOT_DEFAULT)
    args = parser.parse_args()
    if args.execute:
        if not args.expected_head or len(args.expected_head) != 40:
            raise SystemExit("--execute requires --expected-head <exact 40-character commit SHA>")
        execute(args.expected_head, args.v1_repo)
    else:
        dry_run(args.expected_head, args.v1_repo)


if __name__ == "__main__":
    main()
