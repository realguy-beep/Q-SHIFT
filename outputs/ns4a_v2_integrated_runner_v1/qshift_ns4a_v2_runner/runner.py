"""NS-4A V2 integrated runner; all production sampling is authorization-gated."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any, Mapping, Protocol

import numpy as np

from qshift_core_v1.contracts import DecoderPrediction
from qshift_core_v1.sampling_model_identity import TrustedDetectorBatchAdapter
from qshift_core_v1.decoder_runtime_v2 import CheckedDecoderAdapter

from qshift_ns4a_v2_deterministic.protocol import (
    CANDIDATE_IDS, CONDITIONS, EVALUATION_ARMS, SELECTION_UNIQUE_SHOTS,
    TOTAL_UNIQUE_SHOTS, make_root_id, selection_shots, shots_for_root,
)
from qshift_ns4a_v2_deterministic.selection import (
    SelectionRootScore, choose_global_candidate, run_and_score_selection_batch,
)
from qshift_ns4a_v2_deterministic.paired_evaluation import run_paired_evaluation_batch
from qshift_ns4a_v2_deterministic.checkpoint import atomic_write_json
from qshift_ns4a_v2_deterministic.sample_schema import load_validated_archive, make_sample_ids

from .analysis import analyze_verified_archives
from .archive_store import build_archive_arrays, commit_root_archive, archive_path
from .audit import audit_run_directory
from .integrity import (
    AuthorizedExecution, IntegrityError, execution_output_path, load_authorized_execution,
    runtime_fingerprint, sha256_file,
)
from .models import CONFIG_PATH, ModelCatalog, build_evaluation_bank, build_model_catalog, evaluation_decoder_views
from .protocol import validate_allocation
from .resource_guard import ResourceGuard
from .run_state import RunDirectoryLock, RunStateError, RunStateStore


class ProductionExecutionError(RuntimeError):
    """Production execution cannot proceed without a valid frozen approval."""


class RootSampler(Protocol):
    def sample(self, circuit: Any, *, shots: int, seed: int) -> tuple[np.ndarray, np.ndarray]: ...


class StimRootSampler:
    """The only Stim sampling call site; constructed only after owner approval."""

    def __init__(self, permit: "_SamplingPermit"):
        if not isinstance(permit, _SamplingPermit) or permit._nonce is not _SAMPLING_NONCE:
            raise PermissionError("Stim sampling requires the capability produced by validated owner authorization.")
        self._permit = permit

    def sample(self, circuit: Any, *, shots: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
        if self._permit._nonce is not _SAMPLING_NONCE:
            raise PermissionError("Stim sampling capability is invalid.")
        if type(seed) is not int or not 0 <= seed <= 2**63 - 1:
            raise ProductionExecutionError("Stim root seed is invalid.")
        sampler = circuit.compile_detector_sampler(seed=seed)
        detectors, observables = sampler.sample(shots=shots, separate_observables=True)
        det = np.asarray(detectors, dtype=np.uint8)
        obs = np.asarray(observables, dtype=np.uint8)
        if det.shape != (shots, 40) or obs.shape != (shots, 1):
            raise ProductionExecutionError("Stim returned arrays outside the frozen [shots,40]/[shots,1] contract.")
        if np.any(det > 1) or np.any(obs > 1):
            raise ProductionExecutionError("Stim returned nonbinary detector/observable values.")
        return det, obs


_SAMPLING_NONCE = object()


@dataclass(frozen=True)
class _SamplingPermit:
    execution_manifest_sha256: str
    seed_inventory_sha256: str
    _nonce: object


def _sampling_permit(execution: AuthorizedExecution) -> _SamplingPermit:
    if (not isinstance(execution, AuthorizedExecution)
            or execution.manifest.get("sampling_authorized") is not True
            or len(execution.execution_manifest_sha256) != 64
            or len(execution.seed_inventory_sha256) != 64):
        raise PermissionError("Validated final owner authorization is required to create a sampler capability.")
    return _SamplingPermit(execution.execution_manifest_sha256, execution.seed_inventory_sha256, _SAMPLING_NONCE)


class _CheckedDecoderView:
    """Adapts the NS-2C checked boundary to the accepted raw batch protocol."""

    def __init__(self, adapter: CheckedDecoderAdapter, circuit: Any):
        self.adapter = adapter
        self.circuit = circuit
        self.metadata = adapter.model_identity.metadata
        self._trusted = TrustedDetectorBatchAdapter(adapter.sampling_identity)

    def decode(self, detectors: np.ndarray) -> DecoderPrediction:
        batch = self._trusted.from_stim_detector_samples(
            self.circuit, detectors, column_detector_ids=self.adapter.sampling_identity.detector_ids,
        )
        execution = self.adapter.predict(batch)
        if execution.status != "ok" or execution.prediction is None:
            raise RuntimeError(
                f"decoder {self.adapter.name!r} failed: {execution.failure_type}: {execution.failure_message}"
            )
        bits = np.array(execution.prediction.bits, dtype=np.uint8, order="C", copy=True)
        return DecoderPrediction(bits, self.metadata, execution.decoder_reported_seconds)


def _root_seed_ref(inventory_sha256: str, partition: str, condition: str, index: int) -> str:
    return f"seed-inventory:{inventory_sha256}:{partition}:{condition}:r{index:02d}"


def _checkpoint_records_from_archives(run_dir: Path, partition: str) -> list[Any]:
    from qshift_ns4a_v2_deterministic.statistics import EvaluationRootCounts
    from qshift_ns4a_v2_deterministic.selection import SelectionRootScore

    count = 8 if partition == "selection" else 10
    rows = []
    for condition in CONDITIONS:
        for root_i in range(count):
            path = archive_path(run_dir, partition, condition, make_root_id(partition, condition, root_i))
            archive, _ = load_validated_archive(path)
            errors = {
                name: int(np.count_nonzero(archive.predictions[i] != archive.observables))
                for i, name in enumerate(archive.candidate_ids)
            }
            if partition == "selection":
                rows.append(SelectionRootScore(condition, root_i, archive.root_id, len(archive.sample_ids), errors))
            else:
                rows.append(EvaluationRootCounts(condition, root_i, archive.root_id, len(archive.sample_ids), errors))
    return rows


def _root_paths(run_dir: Path, partition: str) -> list[Path]:
    n = 8 if partition == "selection" else 10
    return [
        archive_path(run_dir, partition, condition, make_root_id(partition, condition, i))
        for condition in CONDITIONS for i in range(n)
    ]


def _write_once_json(path: Path, payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"
    if path.exists():
        existing = path.read_bytes()
        if existing != encoded:
            raise ProductionExecutionError(f"refusing to overwrite different final artifact {path.name}.")
        return hashlib.sha256(existing).hexdigest()
    return atomic_write_json(path, payload)


def _verify_git_commit(repo_root: Path, expected: str) -> None:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=False,
    )
    if completed.returncode != 0 or completed.stdout.strip() != expected:
        raise IntegrityError("Current Git HEAD differs from the frozen execution manifest.")
    status = subprocess.run(
        ["git", "-C", str(repo_root), "status", "--porcelain"],
        capture_output=True, text=True, check=False,
    )
    if status.returncode != 0 or status.stdout.strip():
        raise IntegrityError("Production sampling requires a clean worktree at the authorized commit.")


def _verify_checkpoint_seed_bindings(state: RunStateStore, execution: AuthorizedExecution) -> None:
    payload = state.read()
    for row in payload["committed_roots"]:
        key = (row["partition"], row["condition_id"], int(row["root_id"][-2:]))
        expected_seed = execution.root_seeds.get(key)
        expected_ref = _root_seed_ref(execution.seed_inventory_sha256, *key)
        if row.get("seed") != expected_seed or row.get("root_seed_ref") != expected_ref:
            raise ProductionExecutionError(f"checkpoint seed/root identity differs from frozen inventory: {key}.")
    inflight = payload.get("in_flight_root")
    if inflight is not None:
        key = (inflight["partition"], inflight["condition_id"], int(inflight["root_id"][-2:]))
        if (inflight.get("seed") != execution.root_seeds.get(key)
                or inflight.get("root_seed_ref") != _root_seed_ref(execution.seed_inventory_sha256, *key)):
            raise ProductionExecutionError("in-flight root seed does not match the immutable inventory.")


def _begin_state(run_dir: Path, protocol_sha: str, source_sha: str,
                 execution: AuthorizedExecution, wall_clock_seconds: float) -> tuple[RunStateStore, bool]:
    state = RunStateStore(
        run_dir, protocol_sha256=protocol_sha, source_manifest_sha256=source_sha,
        execution_manifest_sha256=execution.execution_manifest_sha256,
        seed_inventory_sha256=execution.seed_inventory_sha256,
        wall_clock_seconds=wall_clock_seconds,
    )
    if state.checkpoint_path.exists():
        state.recover_committed_inflight()
        payload = state.read()
        if payload["state"] == "in_progress" and payload.get("in_flight_root") is None:
            state.pause_at_boundary()
        state.validate_resume(protocol_sha256=protocol_sha, source_manifest_sha256=source_sha)
        return state, True
    if any(run_dir.iterdir()):
        raise RunStateError("run directory contains files but no valid checkpoint; refusing to adopt or overwrite.")
    state.initialize()
    return state, False


def _commit_selection_root(
    *, run_dir: Path, state: RunStateStore, catalog: ModelCatalog,
    condition_id: str, root_index: int, execution: AuthorizedExecution,
    sampler: RootSampler, guard: ResourceGuard,
) -> None:
    condition = catalog.conditions[condition_id]
    root_id = make_root_id("selection", condition_id, root_index)
    shots = selection_shots(CONDITIONS.index(condition_id), root_index)
    seed_key = ("selection", condition_id, root_index)
    seed = execution.root_seeds[seed_key]
    seed_ref = _root_seed_ref(execution.seed_inventory_sha256, *seed_key)
    state.begin_root(partition="selection", condition_id=condition_id, root_index=root_index,
                     shots=shots, seed=seed, root_seed_ref=seed_ref)
    guard.check("before_selection_sampling")
    detectors, labels = sampler.sample(condition.circuit, shots=shots, seed=seed)
    # Complete an already-returned root transaction before checking deadline
    # again; this closes the sampler/checkpoint data-loss gap without allowing
    # another root to start after expiry.
    detectors = np.asarray(detectors, dtype=np.uint8)
    labels = np.asarray(labels, dtype=np.uint8)
    ids = make_sample_ids("selection", condition_id, root_id, shots)
    result = run_and_score_selection_batch(
        condition_id=condition_id, root_index=root_index, root_id=root_id,
        detectors=detectors, detector_sample_ids=ids, labels=labels,
        label_sample_ids=ids, prediction_sample_ids=ids,
        decoders=catalog.selection_decoders,
    )
    prediction_stack = np.stack([result.predictions_by_candidate[c] for c in CANDIDATE_IDS], axis=0)
    model_ids = catalog.selection_model_identities_by_condition[condition_id]
    arrays = build_archive_arrays(
        partition="selection", condition_id=condition_id, root_id=root_id,
        detectors=detectors, observables=labels, predictions=prediction_stack,
        model_identity_sha256_by_candidate={c: model_ids[c].identity_sha256 for c in CANDIDATE_IDS},
        sampling_identity_sha256=condition.sampling_identity.identity_sha256,
        root_seed_ref=seed_ref,
        extra_metadata={"execution_manifest_sha256": execution.execution_manifest_sha256,
                        "synthetic_fixture": False},
    )
    marker = commit_root_archive(run_dir, arrays, root_seed_ref=seed_ref)
    state.commit_root(marker, seed=seed)
    guard.check("selection_root_committed")


def _commit_evaluation_root(
    *, run_dir: Path, state: RunStateStore, catalog: ModelCatalog,
    condition_id: str, root_index: int, selected_candidate: str,
    execution: AuthorizedExecution, sampler: RootSampler, guard: ResourceGuard,
    bank: Any, circuit: Any,
) -> None:
    condition = catalog.conditions[condition_id]
    root_id = make_root_id("evaluation", condition_id, root_index)
    shots = shots_for_root("evaluation", condition_id, root_index)
    seed_key = ("evaluation", condition_id, root_index)
    seed = execution.root_seeds[seed_key]
    seed_ref = _root_seed_ref(execution.seed_inventory_sha256, *seed_key)
    frozen_selected, _ = state.require_frozen_selection()
    if frozen_selected != selected_candidate:
        raise ProductionExecutionError("evaluation attempted to change the globally selected fixed model.")
    state.begin_root(partition="evaluation", condition_id=condition_id, root_index=root_index,
                     shots=shots, seed=seed, root_seed_ref=seed_ref)
    guard.check("before_evaluation_sampling")
    detectors, labels = sampler.sample(condition.circuit, shots=shots, seed=seed)
    detectors = np.asarray(detectors, dtype=np.uint8)
    labels = np.asarray(labels, dtype=np.uint8)
    ids = make_sample_ids("evaluation", condition_id, root_id, shots)
    views = evaluation_decoder_views(bank, circuit)
    result = run_paired_evaluation_batch(
        condition_id=condition_id, root_index=root_index, root_id=root_id,
        detectors=detectors, detector_sample_ids=ids, labels=labels,
        label_sample_ids=ids, prediction_sample_ids=ids, decoders=views,
    )
    stack = np.stack([result["predictions_by_arm"][arm] for arm in EVALUATION_ARMS], axis=0)
    registered_by_arm = {
        "nominal_ordinary_pymatching": "nominal_ordinary_pymatching",
        "nominal_correlation_enabled_pymatching": "nominal_correlation_enabled_pymatching",
        "pooled_selected_fixed_pymatching": "pooled_selected_fixed_pymatching",
        "matched_selected_dem_pymatching_other_mode_control": "matched_selected_dem_pymatching_other_mode_control",
        "beliefmatching_same_selected_dem": "beliefmatching",
    }
    model_ids = {arm: bank.adapter(registered).model_identity.identity_sha256
                 for arm, registered in registered_by_arm.items()}
    arrays = build_archive_arrays(
        partition="evaluation", condition_id=condition_id, root_id=root_id,
        detectors=detectors, observables=labels, predictions=stack,
        model_identity_sha256_by_candidate=model_ids,
        sampling_identity_sha256=condition.sampling_identity.identity_sha256,
        root_seed_ref=seed_ref,
        extra_metadata={"execution_manifest_sha256": execution.execution_manifest_sha256,
                        "selected_candidate": selected_candidate,
                        "synthetic_fixture": False},
    )
    marker = commit_root_archive(run_dir, arrays, root_seed_ref=seed_ref)
    state.commit_root(marker, seed=seed)
    guard.check("evaluation_root_committed")


def execute_authorized(
    execution_manifest_path: str | Path,
    authorization_path: str | Path,
    *, repository_root: str | Path,
) -> dict[str, Any]:
    """Run only after final immutable-manifest and separate-owner-approval checks."""
    root = Path(repository_root).resolve()
    # Everything below remains unreachable without both files and all hash checks.
    execution = load_authorized_execution(execution_manifest_path, authorization_path, repository_root=root)
    _verify_git_commit(root, execution.manifest["git_commit"])
    allocation = validate_allocation()
    if allocation != {"selection": 64_000, "evaluation": 240_000, "total": 304_000}:
        raise IntegrityError("Frozen allocation arithmetic failed.")
    protocol_path = root / execution.manifest["protocol_path"]
    protocol_sha = sha256_file(protocol_path)
    source_manifest_sha = execution.manifest["source_manifest_sha256"]
    output_relative = execution.manifest["output_directory"]
    run_dir = execution_output_path(root, output_relative)
    run_dir.mkdir(parents=True, exist_ok=True)
    limits = execution.manifest["resource_limits"]
    guard = ResourceGuard(
        run_dir,
        wall_clock_seconds=limits["wall_clock_seconds"],
        peak_rss_bytes=limits["peak_rss_bytes"],
        free_disk_reserve_bytes=limits["free_disk_reserve_bytes"],
    )
    guard.start()
    with RunDirectoryLock(run_dir):
        state, resuming = _begin_state(run_dir, protocol_sha, source_manifest_sha, execution,
                                       limits["wall_clock_seconds"])
        guard.bind_persisted_deadline(state.read()["run_deadline_epoch_utc"])
        guard.check("checkpoint_and_seed_preflight")
        _verify_checkpoint_seed_bindings(state, execution)
        catalog = build_model_catalog(protocol_path)
        if catalog.dem_identity_manifest() != execution.dem_identity_manifest:
            raise IntegrityError("Reconstructed circuit/DEM identities differ from the immutable DEM manifest.")
        guard.check("six_DEM_and_twelve_candidate_construction")
        sampler: RootSampler = StimRootSampler(_sampling_permit(execution))

        for condition in CONDITIONS:
            for root_index in range(8):
                key = ("selection", condition, make_root_id("selection", condition, root_index))
                if key not in {
                    (row["partition"], row["condition_id"], row["root_id"])
                    for row in state.read()["committed_roots"]
                }:
                    _commit_selection_root(
                        run_dir=run_dir, state=state, catalog=catalog,
                        condition_id=condition, root_index=root_index,
                        execution=execution, sampler=sampler, guard=guard,
                    )

        selection_rows = _checkpoint_records_from_archives(run_dir, "selection")
        recomputed_winner = choose_global_candidate(selection_rows)
        if state.read().get("selection_frozen"):
            selected, saved_winner = state.require_frozen_selection()
            if saved_winner["selected_candidate"] != recomputed_winner["selected_candidate"]:
                raise ProductionExecutionError("Saved winner differs from resumed selection archive recomputation.")
            recomputed_winner = saved_winner
        else:
            selection_hashes = {
                path.name: sha256_file(path) for path in _root_paths(run_dir, "selection")
            }
            recomputed_winner["selection_archive_sha256"] = selection_hashes
            selected = str(recomputed_winner["selected_candidate"])
            state.freeze_selection(recomputed_winner)
        selected, _winner = state.require_frozen_selection()

        committed = {
            (row["partition"], row["condition_id"], row["root_id"])
            for row in state.read()["committed_roots"]
        }
        for condition in CONDITIONS:
            guard.check("evaluation_decoder_bank_construction_start")
            bank, _registration = build_evaluation_bank(catalog, condition, selected)
            guard.check("evaluation_decoder_bank_construction_complete")
            try:
                for root_index in range(10):
                    root_id = make_root_id("evaluation", condition, root_index)
                    if ("evaluation", condition, root_id) not in committed:
                        _commit_evaluation_root(
                            run_dir=run_dir, state=state, catalog=catalog,
                            condition_id=condition, root_index=root_index,
                            selected_candidate=selected, execution=execution,
                            sampler=sampler, guard=guard, bank=bank,
                            circuit=catalog.conditions[condition].circuit,
                        )
                        committed.add(("evaluation", condition, root_id))
            finally:
                try:
                    bank.adapter("beliefmatching")._implementation.close()
                except Exception:
                    pass
            guard.check("evaluation_condition_complete")

        checkpoint = state.read()
        guard.check("before_independent_saved_array_audit")
        independent = audit_run_directory(run_dir, checkpoint)
        audit_path = run_dir / "INDEPENDENT_AUDIT.json"
        audit_hash = _write_once_json(audit_path, independent)
        state.record_independent_audit(audit_hash)
        guard.check("after_independent_saved_array_audit")
        if state.read()["state"] != "completed":
            selected_mode = selected.split("::", 1)[1]
            guard.check("before_statistical_analysis")
            analysis = analyze_verified_archives(
                independent,
                selected_candidate=selected,
                analysis_seeds=execution.analysis_seeds,
            )
            summary_path = run_dir / "STATISTICAL_SUMMARY.json"
            _write_once_json(summary_path, analysis)
            guard.check("after_statistical_analysis")
            guard.check("before_final_completion_commit")
            state.mark_completed()
            try:
                guard.check("after_final_completion_commit")
            except Exception as exc:
                # Never leave a success status if the deadline/resource check
                # fails during the final state write itself.
                state.mark_failed(type(exc).__name__, str(exc))
                raise
        return {
            "status": state.read()["state"],
            "resumed": resuming,
            "run_directory": str(run_dir),
            "independent_audit_sha256": audit_hash,
            "total_unique_shots": independent["total_shots"],
            "selected_candidate": selected,
            "resource_snapshot": guard.check("completed"),
        }
