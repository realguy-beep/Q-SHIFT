"""Integrated, sampler-free Stage 5 recovery-copy preparation and repair.

This module never opens a Stim sampler and has no code path that samples new
shots. It copies the historical failed run only after validating its complete
forensic inventory, then repairs committed checkpoints in a separate,
provenance-marked recovery directory.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import time
import os
import shutil
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FORENSIC = ROOT / "outputs/stage5_postfailure_forensics_v1"
SOURCE_RUN = ROOT / "outputs/stage5_secondary_inference_repair_v1/run"
SOURCE_INVENTORY = FORENSIC / "PRE_INVESTIGATION_SHA256.json"
FROZEN_RUNNER = ROOT / "outputs/stage5_secondary_inference_repair_v1/stage5_sampling_runner_v2.py"
STAGE5_FREEZE = ROOT / "outputs/stage5_secondary_inference_repair_v1/STAGE5_PRETEST_FREEZE_V2.json"

sys.path.insert(0, str(HERE))
from atomic_safety_v44 import (  # noqa: E402
    ConcurrentStateError, InterProcessFileLock, UncommittedCheckpointError, atomic_write_json,
    recover_write_intent, sha256_file, verify_committed_npz,
)
import recovery_core_v44 as core  # noqa: E402


class RecoveryServiceError(RuntimeError):
    """Recovery refused because source evidence or destination state is unsafe."""


@dataclass(frozen=True)
class FrozenContext:
    probabilities: tuple[float, ...]
    roots_per_condition: int
    seeds: dict
    estimator: object
    build_decoder: Callable
    decode_prediction: Callable
    calibration_shots: int = 2000
    evaluation_shots: int = 2500
    detector_count: int = 40
    prediction_arms: int = 3

    @property
    def expected_roots(self):
        return [(p, r) for p in self.probabilities for r in range(self.roots_per_condition)]

    @property
    def expected_seeds(self):
        converted = {}
        for p, r in self.expected_roots:
            converted[(float(p), int(r))] = {
                "calibration": int(self.seeds[("calibration_detector_only", float(p), int(r))]),
                "evaluation": int(self.seeds[("paired_evaluation_detector_observable", float(p), int(r))]),
            }
        values = [seed for pair in converted.values() for seed in pair.values()]
        if len(values) != len(set(values)):
            raise RecoveryServiceError("frozen calibration/evaluation seed allocation collides")
        return converted


def _load_frozen_runner():
    spec = importlib.util.spec_from_file_location("stage5_frozen_v2_v44", FROZEN_RUNNER)
    if spec is None or spec.loader is None:
        raise RecoveryServiceError("cannot load frozen Stage 5 runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_frozen_context() -> FrozenContext:
    """Load only frozen configuration, estimator and decoder constructors."""
    module = _load_frozen_runner()
    freeze = module.verify_freeze()
    module.verify_candidate_screen()
    seeds, _inventory = module.seed_map()
    profile = module.load_profile()
    return FrozenContext(tuple(module.PROBS), int(module.ROOTS), seeds, profile,
                         module.build_decoder, module.decode_prediction,
                         int(module.CAL_SHOTS), int(module.EVAL_SHOTS), 40, 3)


def _check_source_inventory(source_run: Path, inventory_path: Path) -> dict:
    source_run = Path(source_run).resolve()
    inventory_path = Path(inventory_path).resolve()
    if source_run != SOURCE_RUN.resolve() or inventory_path != SOURCE_INVENTORY.resolve():
        raise RecoveryServiceError("only the named historical failed run and its frozen forensic inventory are permitted")
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    if inventory.get("base_commit") != "8c06750808582137f6a81e2170ad702a552594fb" or inventory.get("file_count") != 265:
        raise RecoveryServiceError("forensic inventory does not match the frozen 265-file base evidence")
    checked = 0
    for row in inventory["files"]:
        path = ROOT / row["path"]
        if not path.is_file() or sha256_file(path) != row["sha256"]:
            raise RecoveryServiceError(f"historical source evidence hash mismatch: {row['path']}")
        checked += 1
    if checked != 265:
        raise RecoveryServiceError("incomplete forensic source inventory verification")
    return {"file_count": checked, "inventory_sha256": sha256_file(inventory_path),
            "source_manifest_hashes": {row["path"].replace("\\", "/"): row["sha256"]
                                       for row in inventory["files"]}}


@contextmanager
def _read_only_source_quiescence(source_run: Path):
    """Hold existing kernel locks without writing source lock/owner files."""
    source_run = Path(source_run).resolve()
    paths = [source_run / f".stage5-{role}.lock"
             for role in ("launcher", "worker", "auditor", "finalizer", "intent")]
    handles = []
    try:
        for path in paths:
            if not path.is_file() or path.stat().st_size < 1:
                raise RecoveryServiceError(f"source ownership lock is missing or malformed: {path.name}")
            handle = path.open("r+b")
            handle.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                handle.close()
                raise RecoveryServiceError(f"historical source still has an active {path.name} lock") from exc
            handles.append((handle, os.name == "nt"))

        intent_path = source_run / ".stage5-child-intent.json"
        if intent_path.exists():
            intent = json.loads(intent_path.read_text(encoding="utf-8"))
            sys.path.insert(0, str(ROOT / "outputs/stage5_execution_safety_v3_4_2"))
            from ownership_runtime_v4 import _find_token_process
            live = _find_token_process(intent)
            if live is not None:
                raise RecoveryServiceError(
                    f"historical owner-token process remains alive (pid={live['pid']})")
        yield
    finally:
        for handle, windows in reversed(handles):
            try:
                handle.seek(0)
                if windows:
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            finally:
                handle.close()


def prepare_recovery_copy(destination: Path) -> dict:
    """Prepare a new copy. Never repairs or writes to the failed source run."""
    verified = _check_source_inventory(SOURCE_RUN, SOURCE_INVENTORY)
    with _read_only_source_quiescence(SOURCE_RUN):
        source_status = json.loads((SOURCE_RUN / "status.json").read_text(encoding="utf-8"))
        if source_status.get("status") != "worker_failed":
            raise RecoveryServiceError("historical source status is not the documented worker_failed state")
        destination = Path(destination).resolve()
        if destination.exists():
            raise FileExistsError(f"recovery destination already exists: {destination}")
        if destination == SOURCE_RUN.resolve() or SOURCE_RUN.resolve() in destination.parents:
            raise RecoveryServiceError("recovery destination must be separate from the original run")
        source_repo_rel = SOURCE_RUN.relative_to(ROOT).as_posix()
        candidates = []
        for archive in sorted((SOURCE_RUN / "roots").glob("root_p*.npz")):
            candidates.append(archive)
            candidates.append(Path(str(archive) + ".commit.json"))
        candidates.append(SOURCE_RUN / "status.json")
        copied = {}
        destination.mkdir(parents=True)
        for source in candidates:
            if not source.is_file():
                raise RecoveryServiceError(f"recovery source artifact is missing: {source}")
            relative = source.relative_to(SOURCE_RUN).as_posix()
            inventory_rel = f"{source_repo_rel}/{relative}"
            expected = verified["source_manifest_hashes"].get(inventory_rel)
            actual = sha256_file(source)
            if expected is None or expected != actual:
                raise RecoveryServiceError(f"copy candidate differs from verified source manifest: {inventory_rel}")
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            if sha256_file(target) != actual:
                raise RecoveryServiceError(f"recovery copy hash mismatch: {relative}")
            copied[relative] = actual
        provenance = {
            "format": "qshift-stage5-v43-recovery-copy-provenance",
            "source_run_directory": str(SOURCE_RUN.resolve()),
            "source_inventory_path": str(SOURCE_INVENTORY.resolve()),
            "source_inventory_sha256": verified["inventory_sha256"],
            "source_manifest_hashes": verified["source_manifest_hashes"],
            "source_run_relative_path": source_repo_rel,
            "source_inventory_file_count_verified": verified["file_count"],
            "copied_files": copied,
            "copied_file_count": len(copied),
            "omitted_active_lock_and_owner_files": sorted(
                p.name for p in SOURCE_RUN.iterdir()
                if p.name.startswith(".stage5-")
            ),
            "recovery_sampling_performed": False,
        }
        core.atomic_write_json(destination / "RECOVERY_PROVENANCE.json", provenance,
                               run_dir=destination, expected_old_sha256=None,
                               deadline_monotonic=time.monotonic()+60)
    # The copied recovery directory must itself preserve the source manifest
    # identity before any repair operation is permitted.
    check_recovery_provenance(Path(destination))
    return provenance


def check_recovery_provenance(run_dir: Path) -> dict:
    run_dir = Path(run_dir).resolve()
    provenance = core.require_recovery_workspace(run_dir)
    if Path(provenance["source_run_directory"]).resolve() != SOURCE_RUN.resolve():
        raise RecoveryServiceError("recovery copy provenance names an unexpected source run")
    if Path(provenance["source_inventory_path"]).resolve() != SOURCE_INVENTORY.resolve():
        raise RecoveryServiceError("recovery copy provenance names an unexpected inventory")
    expected_inventory_sha = sha256_file(SOURCE_INVENTORY)
    if provenance.get("source_inventory_sha256") != expected_inventory_sha:
        raise RecoveryServiceError("recovery provenance inventory hash differs from the historical manifest")
    inventory = json.loads(SOURCE_INVENTORY.read_text(encoding="utf-8"))
    manifest_hashes = {row["path"].replace("\\", "/"): row["sha256"] for row in inventory["files"]}
    if provenance.get("source_manifest_hashes") != manifest_hashes:
        raise RecoveryServiceError("recovery provenance source hash map differs from the original inventory")
    copied = provenance.get("copied_files", {})
    if copied.get("status.json") is None:
        raise RecoveryServiceError("recovery copy lacks the source status record")
    transaction_dir = run_dir / ".stage5-v43-transactions" / "writes"
    transactions = []
    if transaction_dir.exists():
        for event_path in transaction_dir.glob("*.json"):
            if event_path.name.endswith(".applied.json"):
                continue
            event = json.loads(event_path.read_text(encoding="utf-8"))
            applied_path = event_path.with_suffix(".applied.json")
            if not applied_path.is_file():
                continue
            applied = json.loads(applied_path.read_text(encoding="utf-8"))
            if applied != {"transaction_id": event.get("transaction_id"),
                           "payload_sha256": event.get("payload_sha256")}:
                raise RecoveryServiceError(f"write transaction marker mismatch: {event_path.name}")
            transactions.append(event)
    for rel, digest in copied.items():
        source_rel = f"{provenance.get('source_run_relative_path', '').rstrip('/')}/{Path(rel).as_posix()}"
        if manifest_hashes.get(source_rel) != digest:
            raise RecoveryServiceError(f"copied source hash is not recorded by the original inventory: {rel}")
        path = run_dir / rel
        if not path.is_file():
            raise RecoveryServiceError(f"recovery copy artifact is missing: {rel}")
        actual = sha256_file(path)
        if actual == digest:
            continue
        # A legitimate recovery-copy mutation must be the end of one unique,
        # fully applied CAS chain starting from the copied source hash.
        current = digest
        used = set()
        while current != actual:
            matches = [(i, event) for i, event in enumerate(transactions)
                       if i not in used and event.get("target_rel") == Path(rel).as_posix()
                       and event.get("expected_old_sha256") == current
                       and event.get("payload_sha256") != current]
            if len(matches) != 1:
                raise RecoveryServiceError(f"recovery copy artifact hash is not explained by a unique CAS chain: {rel}")
            index, event = matches[0]
            used.add(index)
            current = event["payload_sha256"]
            if len(used) > len(transactions):
                raise RecoveryServiceError(f"recovery transaction chain loops: {rel}")
        if current != actual:
            raise RecoveryServiceError(f"recovery copy artifact hash mismatch: {rel}")
    return provenance


def _decoder_cache(context: FrozenContext):
    fixed = context.build_decoder(0.0)[2]
    oracle = {p: context.build_decoder(p)[2] for p in context.probabilities}
    adaptive = {}

    def decode_fn(p_hat, detectors, p):
        p_hat = float(p_hat)
        if p_hat not in adaptive:
            adaptive[p_hat] = context.build_decoder(p_hat)[2]
        return np.stack([
            context.decode_prediction(fixed, detectors),
            context.decode_prediction(adaptive[p_hat], detectors),
            context.decode_prediction(oracle[float(p)], detectors),
        ]).astype(np.uint8, copy=False)

    def checkpoint_verifier(path, detectors, predictions, p_hat, p, _root):
        expected = decode_fn(p_hat, detectors, p)
        return np.array_equal(expected, predictions)

    return decode_fn, checkpoint_verifier


def _read_journal(path: Path) -> dict:
    if not path.exists():
        return {"format": "qshift-stage5-v44-recovery-journal", "events": []}
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("format") != "qshift-stage5-v44-recovery-journal" or not isinstance(value.get("events"), list):
        raise RecoveryServiceError("recovery journal schema is invalid")
    return value


def _append_event(run_dir: Path, event: dict, deadline: float) -> None:
    path = run_dir / "RECOVERY_JOURNAL_V44.json"
    journal = _read_journal(path)
    if any(x.get("event_id") == event["event_id"] for x in journal["events"]):
        return
    journal["events"].append(event)
    atomic_write_json(path, journal, run_dir=run_dir,
                      expected_old_sha256=sha256_file(path), deadline_monotonic=deadline)


def _reconcile_write_intents(run_dir: Path, deadline: float) -> list[dict]:
    writes = run_dir / ".stage5-v43-transactions" / "writes"
    if not writes.exists():
        return []
    recovered = []
    for event_path in sorted(writes.glob("*.json")):
        if event_path.name.endswith(".applied.json") or event_path.with_suffix(".applied.json").exists():
            continue
        recovered.append(recover_write_intent(event_path, run_dir=run_dir,
                                               deadline_monotonic=deadline))
    return recovered


def _reconcile_checkpoint_markers(run_dir: Path, deadline: float) -> list[dict]:
    repaired = []
    for archive in sorted((run_dir / "roots").glob("root_p*.npz")):
        try:
            digest = verify_committed_npz(archive)
        except UncommittedCheckpointError:
            # Only an exact, unique journaled archive write may justify
            # reconstructing its sidecar. The core refuses missing/ambiguous
            # archive intents and uses CAS for the marker replacement.
            result = core.recover_npz_commit(archive, run_dir=run_dir,
                                             deadline_monotonic=deadline)
            repaired.append({"file": archive.name, **result})
        else:
            repaired.append({"file": archive.name, "state": "already_committed", "sha256": digest})
    return repaired


def reconcile_recovery_copy(run_dir: Path, context: FrozenContext | None = None,
                            *, deadline_monotonic: float | None = None,
                            _benchmark_fault=None) -> dict:
    """Reconcile archive counters and finish saved evaluation batches only.

    This function has no sampler argument and never calls Stim. It rejects the
    historical source path and requires a manifest-verified recovery copy.
    """
    run_dir = Path(run_dir).resolve()
    if _benchmark_fault is not None and os.environ.get("QSHIFT_STAGE5_V44_TEST_MODE") != "1":
        raise RecoveryServiceError("failure injection is restricted to explicit benchmark test mode")
    if run_dir == SOURCE_RUN.resolve():
        raise RecoveryServiceError("refusing all writes to the original failed Stage 5 run")
    provenance = check_recovery_provenance(run_dir)
    context = context or load_frozen_context()
    deadline = deadline_monotonic or (time.monotonic() + 7200.0)
    if deadline <= time.monotonic():
        raise TimeoutError("recovery deadline expired before reconciliation")
    lock_path = run_dir / ".qshift-stage5-v44-recovery.lock"
    with InterProcessFileLock(lock_path, deadline_monotonic=deadline):
        check_recovery_provenance(run_dir)
        intent_results = _reconcile_write_intents(run_dir, deadline)
        marker_results = _reconcile_checkpoint_markers(run_dir, deadline)
        decode_for_path, verify_prediction = _decoder_cache(context)

        def scan():
            return core.scan_archive_ledger(
                run_dir, expected_seeds=context.expected_seeds,
                expected_roots=context.expected_roots,
                detector_count=context.detector_count,
                calibration_shots=context.calibration_shots,
                evaluation_shots=context.evaluation_shots,
                prediction_arms=context.prediction_arms,
                estimator_verifier=lambda cal, value: abs(float(context.estimator.estimate(cal)) - value) <= 1e-12,
                checkpoint_verifier=verify_prediction,
            )

        status_path = run_dir / "status.json"
        if not status_path.is_file():
            raise RecoveryServiceError("recovery copy status.json is missing")
        status = json.loads(status_path.read_text(encoding="utf-8"))
        ledger = scan()
        updated = core.reconstruct_status(status, ledger)
        updated["status"] = "recovery_reconciling"
        updated["recovery_sampling_performed"] = False
        atomic_write_json(status_path, updated, run_dir=run_dir,
                          expected_old_sha256=sha256_file(status_path), deadline_monotonic=deadline)
        _append_event(run_dir, {
            "event_id": f"ledger-{ledger['ledger_sha256']}",
            "type": "archive_ledger_reconstructed",
            "ledger_sha256": ledger["ledger_sha256"],
            "roots": ledger["archive_count"],
            "calibration_rows": ledger["calibration_shots_generated"],
            "evaluation_rows": ledger["evaluation_shots_generated"],
            "completed_comparisons": ledger["completed_roots"],
            "timestamp_unix": time.time(),
            "source_inventory_sha256": provenance["source_inventory_sha256"],
        }, deadline)

        finished = []
        for pending in list(ledger["recoverable_evaluation_complete_roots"]):
            if time.monotonic() >= deadline:
                raise TimeoutError("recovery deadline expired before saved-array completion")
            p, root = float(pending["probability"]), int(pending["root"])
            checkpoint = run_dir / "roots" / core.root_filename(p, root)
            before_sha = sha256_file(checkpoint)
            _append_event(run_dir, {
                "event_id": f"checkpoint-start-{before_sha}",
                "type": "saved_evaluation_checkpoint_completion_started",
                "probability": p, "root": root, "checkpoint_sha256_before": before_sha,
                "calibration_rows_reused": context.calibration_shots,
                "evaluation_rows_reused": context.evaluation_shots,
                "new_samples": 0,
                "source_inventory_sha256": provenance["source_inventory_sha256"],
            }, deadline)

            # The core decoder callback accepts p_hat and detectors. Bind p to
            # this already-identified archive; no hidden labels are passed.
            decode_fn = lambda p_hat, detectors, p=p: decode_for_path(p_hat, detectors, p)
            result = core.complete_evaluation_checkpoint(
                checkpoint, run_dir=run_dir, expected_seeds=context.expected_seeds,
                estimate_fn=context.estimator.estimate, decode_fn=decode_fn,
                prediction_verifier=lambda _det, _pred: True,
                checkpoint_verifier=verify_prediction,
                deadline_monotonic=deadline,
                detector_count=context.detector_count,
                calibration_shots=context.calibration_shots,
                evaluation_shots=context.evaluation_shots,
                prediction_arms=context.prediction_arms,
                fault=_benchmark_fault,
            )
            finished.append({"probability": p, "root": root, **result})
            _append_event(run_dir, {
                "event_id": f"checkpoint-complete-{result['archive_sha256']}",
                "type": "saved_evaluation_checkpoint_completed",
                "probability": p, "root": root,
                "archive_sha256": result["archive_sha256"],
                "calibration_rows_reused": result["calibration_rows_reused"],
                "evaluation_rows_reused": result["evaluation_rows_reused"],
                "new_samples": result["additional_samples_generated"],
                "source_inventory_sha256": provenance["source_inventory_sha256"],
            }, deadline)

        ledger = scan()
        old_status = json.loads(status_path.read_text(encoding="utf-8"))
        final_status = core.reconstruct_status(old_status, ledger)
        final_status["status"] = "recovery_ready_no_sampling"
        final_status["recovery_sampling_performed"] = False
        final_status["recovery_ledger_sha256"] = ledger["ledger_sha256"]
        atomic_write_json(status_path, final_status, run_dir=run_dir,
                          expected_old_sha256=sha256_file(status_path), deadline_monotonic=deadline)
        _append_event(run_dir, {
            "event_id": f"reconciled-{ledger['ledger_sha256']}",
            "type": "recovery_copy_reconciled",
            "ledger_sha256": ledger["ledger_sha256"],
            "completed_roots": ledger["completed_roots"],
            "archive_count": ledger["archive_count"],
            "calibration_rows": ledger["calibration_shots_generated"],
            "evaluation_rows": ledger["evaluation_shots_generated"],
            "new_samples": 0,
            "timestamp_unix": time.time(),
            "source_inventory_sha256": provenance["source_inventory_sha256"],
        }, deadline)
        return {"status": "recovery_ready_no_sampling", "ledger": ledger,
                "finished_saved_checkpoints": finished,
                "write_intents_recovered": intent_results,
                "checkpoint_markers_reconciled": marker_results,
                "new_samples": 0, "recovery_copy": str(run_dir)}


def frozen_input_hashes() -> dict:
    """Return the unchanged scientific-freeze hashes required by this repair."""
    record = json.loads(STAGE5_FREEZE.read_text(encoding="utf-8"))
    if record.get("status") != "PRETEST_FROZEN_NOT_AUTHORIZED" or record.get("stage5_evaluation_shots_generated") != 0:
        raise RecoveryServiceError("Stage 5 frozen authorization boundary changed")
    for rel, expected in record["sha256"].items():
        path = ROOT / rel
        if not path.is_file() or sha256_file(path) != expected:
            raise RecoveryServiceError(f"frozen Stage 5 artifact changed: {rel}")
    return record["sha256"]


if __name__ == "__main__":
    raise SystemExit("This module exposes recovery-copy primitives only; no CLI or sampling entry point is provided.")
