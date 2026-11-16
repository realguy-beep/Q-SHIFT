"""Single V1.6b paired evaluation runner (two burst conditions). Freeze- and watchdog-gated.

`run_pipeline` is the one code path for both the real evaluation and the sampler-free
rehearsal; only the sampler, allocation and condition supports differ.
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
from scipy.stats import chi2

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m  # noqa: E402
from outputs.qshift_correlated_decoder_v1_6 import learner as L  # noqa: E402
from outputs.qshift_correlated_decoder_v1_6b import contract as K  # noqa: E402
from outputs.qshift_correlated_decoder_v1_6b.analyze_saved import analyze  # noqa: E402
from outputs.qshift_correlated_decoder_v1_6b.common import (  # noqa: E402
    COMMITMENT_PATH, CONFIG_PATH, SEALED_DEFAULT, atomic_json, atomic_npz, load_json, open_hidden_support, sha256_file)
from outputs.qshift_v1_4b_decoder_optimality.mld import ExactLogicalDecoder  # noqa: E402

INVENTORY_PATH = ROOT / "seed_inventory.json"
FREEZE_PATH = ROOT / "PRETEST_FREEZE.json"
PREFLIGHT_PATH = ROOT / "PREFLIGHT.json"
PROTOCOL_PATH = ROOT / "EXPERIMENT_PROTOCOL.md"
RUN_DIR = ROOT / "pilot_runs/attempt_001"
WATCHDOG_ENV = "QSHIFT_V1_6B_WATCHDOG_ACTIVE"
BRANCH = "codex/qshift-correlated-decoder-v1-6"
FREEZE_SCHEMA = "qshift-correlated-decoder-v1.6b-pretest-freeze-v1"
SPEC = m.CodeSpec()
THRESHOLD = float(chi2.ppf(1 - K.LEARNER_THRESHOLD_ALPHA / 15, df=1))

# sampler(condition, qi, shots, seed) -> (detectors uint8 [shots,40], observables [shots,1])
Sampler = Callable[[str, int, int, int], tuple[np.ndarray, np.ndarray]]


def stim_sampler(supports: dict[str, tuple[int, ...]]) -> Sampler:
    circuits = {(c, qi): m.build_candidate_circuit(SPEC, q, supports[c]) for c in K.CONDITIONS for qi, q in enumerate(K.QS)}

    def sample(c: str, qi: int, shots: int, seed: int):
        det, obs = circuits[(c, qi)].compile_detector_sampler(seed=int(seed)).sample(shots=shots, separate_observables=True)
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
            raise TimeoutError("V1.6b end-to-end wall deadline reached")
        if current > self.max_rss:
            raise MemoryError("sampled current-process RSS exceeded the frozen ceiling")
        if free < self.min_free:
            raise OSError("free disk space fell below the frozen minimum")
        if artifact_bytes > self.max_artifacts:
            raise OSError("run artifacts exceeded the frozen cap")
        return {"current_rss_bytes": current, "sampled_current_rss_high_water_bytes": self.peak_rss,
                "free_disk_bytes": free, "run_artifact_bytes": artifact_bytes}


def _validate(det: np.ndarray, shots: int) -> np.ndarray:
    det = np.asarray(det, dtype=np.uint8)
    if det.shape != (shots, K.DETECTORS) or not np.isin(det, [0, 1]).all():
        raise RuntimeError("sampler returned invalid detector samples")
    return det


def _exact(support: tuple[int, ...] | None, q: float) -> ExactLogicalDecoder:
    circuit = m.build_base_circuit(SPEC) if (support is None or q <= 0) else m.build_candidate_circuit(SPEC, q, support)
    return ExactLogicalDecoder(circuit.detector_error_model(decompose_errors=False, approximate_disjoint_errors=True))


def _matcher(support: tuple[int, ...] | None, q: float):
    circuit = m.build_base_circuit(SPEC) if support is None else m.build_candidate_circuit(SPEC, q, support)
    return m.build_matching(m.build_decomposed_dem(circuit))


def run_pipeline(run_dir: Path, *, allocation: K.Allocation, sampler: Sampler, supports: dict[str, tuple[int, ...]],
                 inventory: dict, identity: dict, guard: ResourceGuard, inventory_path: Path = INVENTORY_PATH) -> dict:
    n = allocation.roots_per_q
    classes = L.signature_classes()
    learner = L.ParityLearner(classes, L.base_dem(), THRESHOLD)
    base_matching = _matcher(None, 0.0)
    state = {"schema": "qshift-correlated-decoder-v1.6b-run-status-v1", "run_id": run_dir.name,
             "state": K.STATE_RUNNING, "phase": "initialization", "allocation": allocation.as_dict(),
             "sampler_calls_started": [], "shots_committed": 0, "eval_shots_committed": {c: 0 for c in K.CONDITIONS},
             "archives": [], "failure": None, "started_utc": datetime.now(timezone.utc).isoformat()}
    started = time.monotonic()
    atomic_json(run_dir / K.FILE_STATUS, state)
    try:
        atomic_json(run_dir / K.FILE_IDENTITY, {**identity, K.KEY_LABELS_EXPOSED: False,
                                                "device_labeled_partition_labels_read": True,
                                                "calibration_observables_read": False})

        def call(phase: str, key: str, c: str, qi: int, shots: int) -> tuple[dict, np.ndarray, np.ndarray]:
            if len(state["sampler_calls_started"]) >= allocation.sampler_calls:
                raise RuntimeError("frozen sampler-call allocation would be exceeded")
            seed = int(inventory["seeds"][key])
            rec = {"sequence": len(state["sampler_calls_started"]) + 1, "phase": phase, "key": key,
                   "condition": c, "q": K.QS[qi], "seed": seed, "shots": shots, "state": "started",
                   "sample_id": hashlib.sha256(f"qshift-v1.6b:{key}:{seed}".encode()).hexdigest()}
            state["sampler_calls_started"].append(rec)
            atomic_json(run_dir / K.FILE_STATUS, state)
            det, obs = sampler(c, qi, shots, seed)
            return rec, _validate(det, shots), obs

        def commit(rec: dict, path: Path, **arrays) -> None:
            digest, size = atomic_npz(path, **arrays)
            rec.update({"state": "committed", "archive": str(path.relative_to(run_dir).as_posix()),
                        "archive_sha256": digest, "archive_bytes": size})
            state["archives"].append({"path": rec["archive"], "sha256": digest, "bytes": size})
            state["shots_committed"] += rec["shots"]
            atomic_json(run_dir / K.FILE_STATUS, state)

        timings = {"exact": 0.0, "five_factor": 0.0, "matching": 0.0, "learning": 0.0}
        for c in K.CONDITIONS:
            cdir = run_dir / c
            true_support = tuple(supports[c])
            true_events = m.extract_burst_events(SPEC, true_support)
            true_idx = next(i for i, cl in enumerate(classes)
                            if true_support in cl.supports_flip0 + cl.supports_flip1)

            # ---- device calibration: detector-only partition (observables discarded unread) ----
            state["phase"] = f"{c}:device_calibration"
            dev_x = []
            for qi, q in enumerate(K.QS):
                rec, det, obs = call("device_detectors", K.device_key(c, "detectors", q), c, qi,
                                     allocation.device_detector_shots_per_q)
                del obs
                commit(rec, cdir / "device" / f"device_det_q{qi}.npz", detectors=det)
                dev_x.append(det)
            # ---- device labeled partition (labels used for the flip bit only) ----
            lab_x, lab_y = [], []
            for qi, q in enumerate(K.QS):
                rec, det, obs = call("device_labeled", K.device_key(c, "labeled", q), c, qi,
                                     allocation.device_labeled_shots_per_q)
                obs = np.asarray(obs, dtype=np.uint8)
                commit(rec, cdir / "device" / f"device_lab_q{qi}.npz", detectors=det, observables=obs)
                lab_x.append(det)
                lab_y.append(obs[:, 0])
            t = time.perf_counter()
            sel = learner.select(np.vstack(dev_x))
            learned_idx = sel["class_index"]
            flip_rec = None
            learned_rep = None
            if learned_idx is not None:
                flip_rec = L.learn_flip(SPEC, classes[learned_idx], sel["q_hat"], np.vstack(lab_x), np.concatenate(lab_y))
                learned_rep = classes[learned_idx].representative(flip_rec["flip"])
            timings["learning"] += time.perf_counter() - t
            atomic_json(cdir / K.FILE_DEVICE, {
                "learned_class_index": learned_idx, "device_q_hat": sel["q_hat"], "delta": sel["delta"],
                "all_deltas": sel["all_deltas"], "threshold": THRESHOLD,
                "flip": None if flip_rec is None else flip_rec["flip"],
                "flip_log_likelihood_ratio_1_minus_0": None if flip_rec is None else flip_rec["log_likelihood_ratio_1_minus_0"],
                "learned_representative_support": None if learned_rep is None else list(learned_rep)})

            # ---- per-root detector-only calibration -> q-hat ----
            state["phase"] = f"{c}:root_calibration"
            qhat_learned, qhat_true = {}, {}
            for qi, q in enumerate(K.QS):
                for r in range(n):
                    guard.check()
                    rec, det, obs = call("calibration", K.calibration_key(c, q, r), c, qi, allocation.calibration_shots_per_root)
                    del obs
                    commit(rec, cdir / K.DIR_CALIBRATION / K.calibration_archive_name(qi, r), detectors=det)
                    rid = K.root_id(qi, r)
                    qhat_true[rid] = learner.fit_class(det, true_idx)[0]
                    qhat_learned[rid] = 0.0 if learned_idx is None else learner.fit_class(det, learned_idx)[0]

            # ---- freeze models before any evaluation sample exists ----
            state["phase"] = f"{c}:construct_and_freeze_models"
            astar_oracle = _matcher(true_support, K.STATIC_MATCHING_Q)
            astar_learned = _matcher(learned_rep, K.STATIC_MATCHING_Q)
            five = m.FiveFactorDecoder(m.build_matching(m.build_decomposed_dem(m.build_base_circuit(SPEC))),
                                       true_events, SPEC.detectors, correlations=False)
            exact_oracle = {rid: _exact(true_support, v) for rid, v in qhat_true.items()}
            exact_learned = {rid: _exact(learned_rep, v) for rid, v in qhat_learned.items()}
            atomic_json(cdir / K.FILE_MODELS, {
                "schema": "qshift-correlated-decoder-v1.6b-frozen-models-v1", "condition": c,
                "model_choice_frozen_before_evaluation": True,
                K.KEY_TRUE_SUPPORT: list(true_support), K.KEY_LEARNED_CLASS: learned_idx,
                K.KEY_LEARNED_FLIP: None if flip_rec is None else flip_rec["flip"],
                K.KEY_LEARNED_REPRESENTATIVE: None if learned_rep is None else list(learned_rep),
                K.KEY_ROOT_QHAT_LEARNED: qhat_learned, K.KEY_ROOT_QHAT_TRUE: qhat_true,
                "true_class_index": true_idx, "true_flip": true_events[0].observable_flip,
                "exact_widths": sorted({d.max_width for d in list(exact_oracle.values()) + list(exact_learned.values())}),
                "arms": K.ARM_DESCRIPTIONS})
            guard.check()

            # ---- paired evaluation ----
            state["phase"] = f"{c}:evaluation"
            for qi, q in enumerate(K.QS):
                for r in range(n):
                    guard.check()
                    rid = K.root_id(qi, r)
                    rec, det, labels = call("evaluation", K.eval_key(c, q, r), c, qi, allocation.eval_shots_per_root)
                    t = time.perf_counter()
                    col = lambda a: np.asarray(a, dtype=np.uint8).reshape(-1, 1)  # noqa: E731
                    preds = {"A_nominal": col(base_matching.decode_batch(det, enable_correlations=False)),
                             "Astar_oracle": col(astar_oracle.decode_batch(det, enable_correlations=True)),
                             "Astar_learned": col(astar_learned.decode_batch(det, enable_correlations=True))}
                    timings["matching"] += time.perf_counter() - t
                    t = time.perf_counter()
                    preds["BoffStatic_oracle"] = five.decode_rows(det, {"x": K.BOFFSTATIC_Q})["x"]
                    timings["five_factor"] += time.perf_counter() - t
                    t = time.perf_counter()
                    preds["Bexact_oracle"] = exact_oracle[rid].decode(det, batch=256)[0].astype(np.uint8)
                    preds["Blearn"] = exact_learned[rid].decode(det, batch=256)[0].astype(np.uint8)
                    timings["exact"] += time.perf_counter() - t
                    if set(preds) != set(K.ARMS) or any(p.shape != (rec["shots"], 1) for p in preds.values()):
                        raise RuntimeError("decoder prediction contract failed")
                    labels = np.asarray(labels, dtype=np.uint8)  # only now are observables inspected
                    if labels.shape != (rec["shots"], 1) or not np.isin(labels, [0, 1]).all():
                        raise RuntimeError("invalid observables after prediction completion")
                    commit(rec, cdir / K.DIR_EVALUATION / K.eval_archive_name(qi, r), detectors=det,
                           observables=labels, **{K.pred_member(a): preds[a] for a in K.ARMS})
                    state["eval_shots_committed"][c] += rec["shots"]
            atomic_json(run_dir / K.FILE_STATUS, state)

        if any(v != allocation.eval_shots_per_condition for v in state["eval_shots_committed"].values()):
            raise RuntimeError("evaluation allocation is incomplete")
        state["state"], state["phase"] = K.STATE_READY_FOR_ANALYSIS, "independent_saved_array_analysis"
        state["timings_seconds"] = timings
        atomic_json(run_dir / K.FILE_STATUS, state)
        result = analyze(run_dir, allocation=allocation, inventory_path=inventory_path)
        manifest = {"schema": "qshift-correlated-decoder-v1.6b-run-manifest-v1", "source_commit": identity.get("git_head"),
                    "allocation": allocation.as_dict(), "sampler_calls": len(state["sampler_calls_started"]),
                    "analysis_sha256": sha256_file(run_dir / K.FILE_ANALYSIS),
                    "paired_results_sha256": sha256_file(run_dir / K.FILE_PAIRED_CSV),
                    "archive_manifest": state["archives"], "decision": result["decision"],
                    "target": result["target_endpoint"]["status"]}
        atomic_json(run_dir / K.FILE_MANIFEST, manifest)
        state["run_manifest_sha256"] = sha256_file(run_dir / K.FILE_MANIFEST)
        state["resource_observations"] = guard.check()
        state["runtime_seconds"] = time.monotonic() - started
        state["state"], state["phase"] = K.STATE_COMPLETED, "complete"
        state["completed_utc"] = datetime.now(timezone.utc).isoformat()
        atomic_json(run_dir / K.FILE_STATUS, state)
        return result
    except BaseException as exc:
        state["state"] = K.STATE_FAILED
        state["failure"] = {"type": type(exc).__name__, "message": str(exc), "utc": datetime.now(timezone.utc).isoformat()}
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
        raise RuntimeError("missing or unsupported V1.6b pretest freeze")
    for relative, expected in freeze["files"].items():
        path = REPO / relative
        if not path.is_file() or sha256_file(path) != expected:
            raise RuntimeError(f"pretest source/configuration hash mismatch: {relative}")
    return freeze


def check_environment(config: dict) -> dict:
    actual = {"python": sys.version.split()[0], "stim": stim.__version__, "pymatching": pymatching.__version__,
              "numpy": np.__version__, "psutil": psutil.__version__}
    if actual != config["environment"]:
        raise RuntimeError(f"runtime environment mismatch: {actual}")
    return actual


def check_inventory(inventory: dict) -> None:
    from outputs.qshift_correlated_decoder_v1_6b.prepare_seeds import planned_labels
    if set(inventory.get("seeds", {})) != set(planned_labels()) or not inventory.get("disjoint_from_screened_inventories"):
        raise RuntimeError("V1.6b seed inventory is incomplete or collision screening failed")


def check_watchdog_parent() -> None:
    if os.name != "nt" or os.environ.get(WATCHDOG_ENV) != "1":
        raise RuntimeError("execution is allowed only under the V1.6b Windows watchdog")
    parent = psutil.Process().parent()
    command = parent.cmdline() if parent else []
    expected = str((ROOT / "run_watchdog.py").resolve()).casefold()
    if len(command) < 2 or str(Path(command[1]).resolve()).casefold() != expected:
        raise RuntimeError("execution parent is not the versioned V1.6b watchdog")


def common_gates() -> tuple[dict, dict, dict, dict]:
    config = load_json(CONFIG_PATH)
    freeze = verify_freeze()
    env = check_environment(config)
    inventory = load_json(INVENTORY_PATH)
    check_inventory(inventory)
    preflight = load_json(PREFLIGHT_PATH)
    if preflight.get("status") != "PASS" or not preflight.get("runtime_projection", {}).get("within_cap"):
        raise RuntimeError("frozen sampler-free preflight did not pass")
    return config, freeze, inventory, env


def execute(expected_head: str, sealed_path: Path) -> None:
    check_watchdog_parent()
    config, freeze, inventory, env = common_gates()
    head = check_git(expected_head)
    if RUN_DIR.exists():
        raise FileExistsError(f"refusing to overwrite or retry existing V1.6b run directory {RUN_DIR}")
    hidden = open_hidden_support(sealed_path)  # verified against the committed hash before use
    RUN_DIR.mkdir(parents=True)
    identity = {"schema": "qshift-correlated-decoder-v1.6b-execution-identity-v1", "git_head": head, "branch": BRANCH,
                "pretest_freeze_sha256": sha256_file(FREEZE_PATH), "config_sha256": sha256_file(CONFIG_PATH),
                "protocol_sha256": sha256_file(PROTOCOL_PATH), "seed_inventory_sha256": sha256_file(INVENTORY_PATH),
                "preflight_sha256": sha256_file(PREFLIGHT_PATH), "environment": env,
                "hidden_burst_commitment_sha256": sha256_file(COMMITMENT_PATH),
                "hidden_burst_opened_after_freeze_and_hash_verified": True,
                "labels_access_order": "per evaluation root, all six predictions are computed before observables are inspected"}
    supports = {"known": K.KNOWN_SUPPORT, "hidden": hidden}
    result = run_pipeline(RUN_DIR, allocation=K.FROZEN_ALLOCATION, sampler=stim_sampler(supports), supports=supports,
                          inventory=inventory, identity=identity, guard=ResourceGuard(config["resource_limits"], RUN_DIR))
    print(json.dumps({"status": "completed", "decision": result["decision"], "target": result["target_endpoint"]}, indent=2))


def dry_run(expected_head: str | None) -> None:
    config, freeze, inventory, env = common_gates()
    if expected_head:
        check_git(expected_head)
    print(json.dumps({"mode": "dry-run", "sampler_calls": 0, "shots": 0, "hidden_burst_opened": False,
                      "authorized_allocation": K.FROZEN_ALLOCATION.as_dict(),
                      "frozen_file_count": len(freeze["files"]), "environment": env,
                      "run_dir_exists": RUN_DIR.exists()}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true", help="sampler-free validation (default)")
    modes.add_argument("--execute", action="store_true", help="single frozen V1.6b evaluation")
    parser.add_argument("--expected-head", help="exact committed V1.6b source SHA")
    parser.add_argument("--sealed", type=Path, default=SEALED_DEFAULT)
    args = parser.parse_args()
    if args.execute:
        if not args.expected_head or len(args.expected_head) != 40:
            raise SystemExit("--execute requires --expected-head <exact 40-character commit SHA>")
        execute(args.expected_head, args.sealed)
    else:
        dry_run(args.expected_head)


if __name__ == "__main__":
    main()
