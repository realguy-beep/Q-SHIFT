"""Single V1.3 paired evaluation runner. Sampling is freeze- and watchdog-gated.

`run_pipeline` is the one code path for both the real evaluation and the
sampler-free rehearsal: only the sampler callable and allocation differ.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import numpy as np
import psutil
import pymatching
import stim

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from outputs.qshift_correlated_decoder_feasibility_v1_1.model import (  # noqa: E402
    build_base_circuit,
    build_candidate_circuit,
    build_decomposed_dem,
    build_matching,
    extract_burst_events,
)
from outputs.qshift_correlated_decoder_feasibility_v1_1.verify_reuse import verify as verify_v1_reuse  # noqa: E402
from outputs.qshift_correlated_decoder_v1_3 import contract as K  # noqa: E402
from outputs.qshift_correlated_decoder_v1_3.analyze_saved import analyze  # noqa: E402
from outputs.qshift_correlated_decoder_v1_3.common import (  # noqa: E402
    CONFIG_PATH,
    V1_1_PACKAGE,
    atomic_json,
    atomic_npz,
    fit_frozen_estimator,
    load_json,
    sha256_file,
)
from outputs.qshift_correlated_decoder_v1_3.multi_prior import ModeAwareFiveFactor  # noqa: E402

INVENTORY_PATH = ROOT / "seed_inventory.json"
FREEZE_PATH = ROOT / "PRETEST_FREEZE.json"
SELECTION_PATH = ROOT / "STATIC_SELECTION.json"
PREFLIGHT_PATH = ROOT / "PREFLIGHT.json"
PROTOCOL_PATH = ROOT / "EXPERIMENT_PROTOCOL.md"
RUN_DIR = ROOT / "pilot_runs/attempt_001"
WATCHDOG_ENV = "QSHIFT_V1_3_WATCHDOG_ACTIVE"
BRANCH = "codex/qshift-correlated-decoder-v1-3"
FREEZE_SCHEMA = "qshift-correlated-decoder-v1.3-pretest-freeze-v1"
V1_ROOT_DEFAULT = REPO.parent / "qshift-correlated-decoder-feasibility-v1"

# sampler(condition_index, shots, seed) -> (detectors uint8 [shots,40], observables [shots,1])
Sampler = Callable[[int, int, int], tuple[np.ndarray, np.ndarray]]


def stim_sampler() -> Sampler:
    circuits = {qi: build_candidate_circuit(q) for qi, q in enumerate(K.QS)}

    def sample(qi: int, shots: int, seed: int):
        det, obs = circuits[qi].compile_detector_sampler(seed=int(seed)).sample(
            shots=shots, separate_observables=True)
        return np.asarray(det, dtype=np.uint8), obs
    return sample


class ResourceGuard:
    def __init__(self, limits: dict, run_dir: Path):
        self.deadline = time.monotonic() + int(limits["wall_seconds"])
        self.max_rss = int(limits["sampled_peak_rss_bytes"])
        self.min_free = int(limits["minimum_free_disk_bytes"])
        self.max_artifacts = int(limits["maximum_run_artifact_bytes"])
        self.process = psutil.Process()
        self.run_dir = run_dir
        self.peak_rss = 0

    def check(self) -> dict:
        current = int(self.process.memory_info().rss)
        self.peak_rss = max(self.peak_rss, current)
        free = int(shutil.disk_usage(str(self.run_dir)).free)
        artifact_bytes = sum(p.stat().st_size for p in self.run_dir.rglob("*") if p.is_file())
        if time.monotonic() >= self.deadline:
            raise TimeoutError("V1.3 end-to-end wall deadline reached")
        if current > self.max_rss:
            raise MemoryError("sampled current-process RSS exceeded the frozen ceiling")
        if free < self.min_free:
            raise OSError("free disk space fell below the frozen minimum")
        if artifact_bytes > self.max_artifacts:
            raise OSError("run artifacts exceeded the frozen cap")
        return {"current_rss_bytes": current, "sampled_current_rss_high_water_bytes": self.peak_rss,
                "free_disk_bytes": free, "run_artifact_bytes": artifact_bytes}


def _sample_id(key: str, seed: int) -> str:
    return hashlib.sha256(f"qshift-v1.3:{key}:{seed}".encode("utf-8")).hexdigest()


def _validate_detectors(det: np.ndarray, shots: int) -> np.ndarray:
    det = np.asarray(det, dtype=np.uint8)
    if det.shape != (shots, K.DETECTORS) or not np.isin(det, [0, 1]).all():
        raise RuntimeError("sampler returned invalid detector samples")
    return det


def run_pipeline(run_dir: Path, *, allocation: K.Allocation, sampler: Sampler, inventory: dict,
                 estimator, selection: dict, selection_sha256: str, identity: dict,
                 guard: ResourceGuard, inventory_path: Path = INVENTORY_PATH) -> dict:
    """Calibrate, freeze models, evaluate, then run the independent analyzer."""
    n = allocation.roots_per_q
    started = time.monotonic()
    state = {"schema": "qshift-correlated-decoder-v1.3-run-status-v1", "run_id": run_dir.name,
             "state": K.STATE_RUNNING, "phase": "initialization", K.KEY_ALLOCATION: allocation.as_dict(),
             "sampler_calls_started": [], "calibration_shots_committed": 0, "eval_shots_committed": 0,
             "archives": [], "failure": None, "started_utc": datetime.now(timezone.utc).isoformat()}
    atomic_json(run_dir / K.FILE_STATUS, state)
    try:
        atomic_json(run_dir / K.FILE_IDENTITY, {**identity, K.KEY_LABELS_EXPOSED: False})
        atomic_json(run_dir / K.FILE_TRAINING, {"slope": estimator.slope, "intercept": estimator.intercept,
                                                "training_condition_feature_rates": estimator.training_condition_rates,
                                                "training_observable_arrays_read": False})
        guard.check()

        def start_call(phase: str, key: str, q: float, r: int, shots: int) -> dict:
            if len(state["sampler_calls_started"]) >= allocation.sampler_calls:
                raise RuntimeError("frozen sampler-call allocation would be exceeded")
            seed = int(inventory["seeds"][key])
            if not 0 < seed < 2**31:
                raise RuntimeError(f"invalid frozen seed for {key}")
            call = {"sequence": len(state["sampler_calls_started"]) + 1, "phase": phase, "key": key,
                    "condition_q": q, "root": r, "seed": seed, "sample_id": _sample_id(key, seed),
                    "shots": shots, "state": "started", "started_utc": datetime.now(timezone.utc).isoformat()}
            state["sampler_calls_started"].append(call)
            atomic_json(run_dir / K.FILE_STATUS, state)
            return call

        # ---- calibration: detector-only; observables are discarded unread ----
        state["phase"] = "calibration"
        cal_dir = run_dir / K.DIR_CALIBRATION
        qhat = {}
        pooled_parts = []
        for qi, q in enumerate(K.QS):
            for r in range(n):
                guard.check()
                call = start_call("calibration", K.calibration_key(q, r), q, r,
                                  allocation.calibration_shots_per_root)
                det, obs = sampler(qi, call["shots"], call["seed"])
                del obs  # never inspected or persisted
                det = _validate_detectors(det, call["shots"])
                digest, size = atomic_npz(cal_dir / K.calibration_archive_name(qi, r), detectors=det)
                call.update({"state": "committed", "archive": f"{K.DIR_CALIBRATION}/{K.calibration_archive_name(qi, r)}",
                             "archive_sha256": digest, "archive_bytes": size})
                state["calibration_shots_committed"] += call["shots"]
                qhat[K.root_id(qi, r)] = float(estimator.estimate(det))
                pooled_parts.append(det)
                atomic_json(run_dir / K.FILE_STATUS, state)
        pooled_qhat = float(estimator.estimate(np.vstack(pooled_parts)))
        means = {str(q): float(np.mean([qhat[K.root_id(qi, r)] for r in range(n)])) for qi, q in enumerate(K.QS)}
        ordered = means["0.0"] < means["0.01"] < means["0.02"]
        atomic_json(run_dir / K.FILE_CALIBRATION, {
            "per_root_qhat": qhat, "mean_qhat_by_condition": means, K.KEY_ORDER_GATE: ordered,
            "pooled_qhat_informational": pooled_qhat,
            K.KEY_ESTIMATION_SUMMARY: {str(q): {
                "mean_qhat": means[str(q)], "bias": means[str(q)] - q,
                "mae": float(np.mean([abs(qhat[K.root_id(qi, r)] - q) for r in range(n)]))}
                for qi, q in enumerate(K.QS)},
            "calibration_observable_arrays_read": False})
        if not ordered:
            raise RuntimeError("calibration condition-order gate failed before evaluation")
        guard.check()

        # ---- construct and freeze models before any evaluation sample exists ----
        state["phase"] = "construct_and_freeze_models"
        atomic_json(run_dir / K.FILE_STATUS, state)
        t0 = time.perf_counter()
        sel = selection["selected"]
        astar = {"correlations": bool(sel[K.SEL_ASTAR]["correlations"]), "q": float(sel[K.SEL_ASTAR]["q"])}
        alt = {"correlations": bool(sel[K.SEL_ASTAR_ALT]["correlations"]), "q": float(sel[K.SEL_ASTAR_ALT]["q"])}
        if astar["correlations"] == alt["correlations"]:
            raise RuntimeError("AstarAlt must use the other correlation mode")
        tau = float(sel[K.SEL_TAU])
        boff_q = float(sel[K.SEL_BOFFSTATIC_Q])
        base = build_matching(build_decomposed_dem(build_base_circuit()))

        def matcher(q: float):
            return build_matching(build_decomposed_dem(build_candidate_circuit(q)))

        # (matching object, enable_correlations) per static matching arm.
        fixed = {"Astar": (matcher(astar["q"]), astar["correlations"]),
                 "AstarAlt": (matcher(alt["q"]), alt["correlations"])}
        a2sw = {rid: ((base, False) if v < tau else (matcher(v), True)) for rid, v in qhat.items()}
        events = extract_burst_events()
        five_on = ModeAwareFiveFactor(base, events, correlations=True)
        five_off = ModeAwareFiveFactor(base, events, correlations=False)
        construction_seconds = time.perf_counter() - t0
        atomic_json(run_dir / K.FILE_MODELS, {
            K.KEY_SCHEMA: "qshift-correlated-decoder-v1.3-frozen-models-v1",
            "model_choice_frozen_before_evaluation": True,
            K.KEY_ASTAR: astar, K.KEY_ASTAR_ALT: alt, K.KEY_TAU: tau,
            K.KEY_BSTATIC_Q: K.V1_2_BSTATIC_Q, K.KEY_BOFFSTATIC_Q: boff_q,
            K.KEY_ROOT_QHAT: qhat, K.KEY_TRUE_Q: {str(qi): q for qi, q in enumerate(K.QS)},
            K.KEY_SELECTION_SHA: selection_sha256,
            "A2sw_mode_by_root": {rid: ("OFF_base" if v < tau else "ON_qhat") for rid, v in qhat.items()},
            "arms": K.ARM_DESCRIPTIONS, "model_construction_seconds": construction_seconds})
        guard.check()

        # ---- paired evaluation ----
        state["phase"] = "evaluation"
        eval_dir = run_dir / K.DIR_EVALUATION
        timings = {"sampling": 0.0, "matching_arms": 0.0, "five_factor_arms": 0.0, "archive": 0.0}
        for qi, q in enumerate(K.QS):
            for r in range(n):
                guard.check()
                rid = K.root_id(qi, r)
                call = start_call("evaluation", K.eval_key(q, r), q, r, allocation.eval_shots_per_root)
                t = time.perf_counter()
                det, labels = sampler(qi, call["shots"], call["seed"])
                det = _validate_detectors(det, call["shots"])
                timings["sampling"] += time.perf_counter() - t
                t = time.perf_counter()
                preds = {arm: np.asarray(m.decode_batch(det, enable_correlations=c), dtype=np.uint8).reshape(-1, 1)
                         for arm, (m, c) in fixed.items()}
                m, c = a2sw[rid]
                preds["A2sw"] = np.asarray(m.decode_batch(det, enable_correlations=c), dtype=np.uint8).reshape(-1, 1)
                timings["matching_arms"] += time.perf_counter() - t
                t = time.perf_counter()
                preds.update(five_on.decode_rows(det, {"B": qhat[rid], "Bstatic": K.V1_2_BSTATIC_Q}))
                preds.update(five_off.decode_rows(det, {"Boff": qhat[rid], "BoffStatic": boff_q, "Coff": q}))
                timings["five_factor_arms"] += time.perf_counter() - t
                if set(preds) != set(K.ARMS) or any(
                        p.shape != (call["shots"], 1) or p.dtype != np.uint8 for p in preds.values()):
                    raise RuntimeError("decoder prediction contract failed")
                # Only now are the observables inspected.
                labels = np.asarray(labels, dtype=np.uint8)
                if labels.shape != (call["shots"], 1) or not np.isin(labels, [0, 1]).all():
                    raise RuntimeError("sampler returned invalid observables after prediction completion")
                t = time.perf_counter()
                name = K.eval_archive_name(qi, r)
                digest, size = atomic_npz(eval_dir / name, detectors=det, observables=labels,
                                          **{K.pred_member(a): preds[a] for a in K.ARMS})
                timings["archive"] += time.perf_counter() - t
                call.update({"state": "committed", "archive": f"{K.DIR_EVALUATION}/{name}",
                             "archive_sha256": digest, "archive_bytes": size,
                             "committed_utc": datetime.now(timezone.utc).isoformat()})
                state["archives"].append({"path": call["archive"], "sha256": digest, "bytes": size})
                state["eval_shots_committed"] += call["shots"]
                atomic_json(run_dir / K.FILE_STATUS, state)
        if (state["eval_shots_committed"] != allocation.eval_shots
                or state["calibration_shots_committed"] != allocation.calibration_shots):
            raise RuntimeError("evaluation or calibration allocation is incomplete")
        state["state"] = K.STATE_READY_FOR_ANALYSIS
        state["phase"] = "independent_saved_array_analysis"
        state["timings_seconds"] = {**timings, "model_construction": construction_seconds}
        atomic_json(run_dir / K.FILE_STATUS, state)
        guard.check()

        t = time.perf_counter()
        result = analyze(run_dir, allocation=allocation, inventory_path=inventory_path)
        state["timings_seconds"]["analysis"] = time.perf_counter() - t
        manifest = {"schema": "qshift-correlated-decoder-v1.3-run-manifest-v1",
                    "source_commit": identity.get("git_head"),
                    "allocation": allocation.as_dict(),
                    "sampler_calls": len(state["sampler_calls_started"]),
                    "analysis_sha256": sha256_file(run_dir / K.FILE_ANALYSIS),
                    "paired_results_sha256": sha256_file(run_dir / K.FILE_PAIRED_CSV),
                    "archive_manifest": state["archives"], "decision": result["decision"]}
        atomic_json(run_dir / K.FILE_MANIFEST, manifest)
        state["run_manifest_sha256"] = sha256_file(run_dir / K.FILE_MANIFEST)
        state["resource_observations"] = guard.check()
        state["runtime_seconds"] = time.monotonic() - started
        state["state"] = K.STATE_COMPLETED
        state["phase"] = "complete"
        state["completed_utc"] = datetime.now(timezone.utc).isoformat()
        atomic_json(run_dir / K.FILE_STATUS, state)
        return result
    except BaseException as exc:
        state["state"] = K.STATE_FAILED
        state["failure"] = {"type": type(exc).__name__, "message": str(exc),
                            "utc": datetime.now(timezone.utc).isoformat()}
        try:
            atomic_json(run_dir / K.FILE_STATUS, state)
        except BaseException:
            pass
        raise


# ---------------------------------------------------------------- gates

def git_output(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


def check_git(expected_head: str) -> str:
    if git_output("rev-parse", "HEAD") != expected_head:
        raise RuntimeError("current HEAD does not match the authorized frozen source commit")
    if git_output("branch", "--show-current") != BRANCH:
        raise RuntimeError(f"execution requires branch {BRANCH}")
    if git_output("status", "--porcelain", "--untracked-files=normal"):
        raise RuntimeError("execution requires a clean worktree")
    return expected_head


def verify_freeze() -> dict:
    freeze = load_json(FREEZE_PATH)
    if freeze.get("schema") != FREEZE_SCHEMA or not freeze.get("files"):
        raise RuntimeError("missing or unsupported V1.3 pretest freeze")
    for relative, expected in freeze["files"].items():
        path = REPO / relative
        if not path.is_file() or sha256_file(path) != expected:
            raise RuntimeError(f"pretest source/configuration hash mismatch: {relative}")
    return freeze


def check_environment(config: dict) -> dict:
    actual = {"python": sys.version.split()[0], "stim": stim.__version__,
              "pymatching": pymatching.__version__, "numpy": np.__version__, "psutil": psutil.__version__}
    if actual != config["environment"]:
        raise RuntimeError(f"runtime environment mismatch: {actual}")
    return actual


def check_v1_reuse(v1_repo: Path) -> dict:
    verified = verify_v1_reuse(v1_repo.resolve())
    if verified != load_json(V1_1_PACKAGE / "REUSE_VERIFICATION.json"):
        raise RuntimeError("V1 training-archive verification no longer matches the V1.1 record")
    return verified


def check_inventory(inventory: dict) -> None:
    from outputs.qshift_correlated_decoder_v1_3.prepare_seeds import planned_labels
    if set(inventory.get("seeds", {})) != set(planned_labels()) or not inventory.get("disjoint_from_screened_inventories"):
        raise RuntimeError("V1.3 seed inventory is incomplete or collision screening failed")


def check_watchdog_parent() -> None:
    if os.name != "nt" or os.environ.get(WATCHDOG_ENV) != "1":
        raise RuntimeError("execution is allowed only under the V1.3 Windows watchdog")
    parent = psutil.Process().parent()
    command = parent.cmdline() if parent else []
    expected = str((ROOT / "run_watchdog.py").resolve()).casefold()
    if len(command) < 2 or str(Path(command[1]).resolve()).casefold() != expected:
        raise RuntimeError("execution parent is not the versioned V1.3 watchdog")


def common_gates(v1_repo: Path) -> tuple[dict, dict, dict, object, dict]:
    config = load_json(CONFIG_PATH)
    freeze = verify_freeze()
    env = check_environment(config)
    check_v1_reuse(v1_repo)
    inventory = load_json(INVENTORY_PATH)
    check_inventory(inventory)
    estimator = fit_frozen_estimator(v1_repo, config)
    preflight = load_json(PREFLIGHT_PATH)
    if preflight.get("status") != "PASS" or not preflight.get("runtime_projection", {}).get("within_cap"):
        raise RuntimeError("frozen sampler-free preflight did not pass")
    return config, freeze, inventory, estimator, env


def execute(expected_head: str, v1_repo: Path) -> None:
    check_watchdog_parent()
    config, freeze, inventory, estimator, env = common_gates(v1_repo)
    head = check_git(expected_head)
    if RUN_DIR.exists():
        raise FileExistsError(f"refusing to overwrite or retry existing V1.3 run directory {RUN_DIR}")
    RUN_DIR.mkdir(parents=True)
    identity = {"schema": "qshift-correlated-decoder-v1.3-execution-identity-v1", "git_head": head,
                "branch": BRANCH, "pretest_freeze_sha256": sha256_file(FREEZE_PATH),
                "config_sha256": sha256_file(CONFIG_PATH), "protocol_sha256": sha256_file(PROTOCOL_PATH),
                "seed_inventory_sha256": sha256_file(INVENTORY_PATH),
                "static_selection_sha256": sha256_file(SELECTION_PATH),
                "preflight_sha256": sha256_file(PREFLIGHT_PATH), "environment": env,
                "labels_access_order": "per root, all eight predictions are computed before observables are inspected; calibration observables are discarded unread"}
    result = run_pipeline(RUN_DIR, allocation=K.FROZEN_ALLOCATION, sampler=stim_sampler(),
                          inventory=inventory, estimator=estimator, selection=load_json(SELECTION_PATH),
                          selection_sha256=sha256_file(SELECTION_PATH), identity=identity,
                          guard=ResourceGuard(config["resource_limits"], RUN_DIR))
    print(json.dumps({"status": "completed", "decision": result["decision"],
                      "co_primary": result["co_primary"]}, indent=2))


def dry_run(expected_head: str | None, v1_repo: Path) -> None:
    config, freeze, inventory, estimator, env = common_gates(v1_repo)
    if expected_head:
        check_git(expected_head)
    print(json.dumps({"mode": "dry-run", "sampler_calls": 0, "shots": 0,
                      "authorized_allocation": K.FROZEN_ALLOCATION.as_dict(),
                      "frozen_file_count": len(freeze["files"]), "environment": env,
                      "estimator": {"slope": estimator.slope, "intercept": estimator.intercept},
                      "run_dir_exists": RUN_DIR.exists()}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true", help="sampler-free validation (default)")
    modes.add_argument("--execute", action="store_true", help="single frozen V1.3 evaluation")
    parser.add_argument("--expected-head", help="exact committed V1.3 source SHA")
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
