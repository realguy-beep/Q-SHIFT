"""Fixture-tested, sampler-free Stage 5 recovery primitives for safety v3.4.3.

This module accepts explicit seed mappings and decoder callbacks. It contains no
Stim sampler construction and cannot generate samples. Callers must direct all
recovery writes to a new recovery directory.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import time
from pathlib import Path

import numpy as np

from atomic_safety_v44 import (
    ConcurrentStateError,
    UncommittedCheckpointError,
    atomic_write_bytes,
    atomic_write_json,
    recover_npz_commit,
    sha256_bytes,
    sha256_file,
    verify_committed_npz,
    write_committed_npz,
)


ROOT_NAME = re.compile(r"root_p([0-9]+\.[0-9]{3})_r([0-9]{3})\.npz\Z")
ACTIVE_LOCK_NAMES = {
    ".stage5-auditor-owner.json", ".stage5-auditor.lock",
    ".stage5-finalizer-owner.json", ".stage5-finalizer.lock",
    ".stage5-intent-owner.json", ".stage5-intent.lock",
    ".stage5-launcher-owner.json", ".stage5-launcher.lock",
    ".stage5-worker-owner.json", ".stage5-worker.lock",
}


class RecoveryValidationError(RuntimeError):
    """A source checkpoint or recovered state is incomplete or inconsistent."""


def require_recovery_workspace(run_dir: Path) -> dict:
    """Refuse all recovery mutations outside a provenance-marked new directory."""
    run_dir = Path(run_dir).resolve()
    marker = run_dir / "RECOVERY_PROVENANCE.json"
    if not marker.is_file():
        raise RecoveryValidationError("recovery provenance marker missing; refusing mutation")
    try:
        provenance = json.loads(marker.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RecoveryValidationError("recovery provenance marker is unreadable") from exc
    if provenance.get("format") != "qshift-stage5-v43-recovery-copy-provenance":
        raise RecoveryValidationError("unrecognized recovery provenance format")
    source = Path(provenance.get("source_run_directory", "")).resolve()
    if source == run_dir or not provenance.get("source_inventory_sha256"):
        raise RecoveryValidationError("recovery provenance does not identify a distinct source")
    return provenance


def root_filename(probability: float, root: int) -> str:
    return f"root_p{float(probability):.3f}_r{int(root):03d}.npz"


def _scalar(archive, key):
    value = np.asarray(archive[key])
    if value.ndim != 0:
        raise RecoveryValidationError(f"metadata field is not scalar: {key}")
    return value.item()


def _binary(array, name):
    if array.dtype != np.uint8 or not np.isin(array, (0, 1)).all():
        raise RecoveryValidationError(f"{name} must be binary uint8")


def _seed_pair(expected_seeds, probability, root):
    try:
        pair = expected_seeds[(float(probability), int(root))]
    except KeyError as exc:
        raise RecoveryValidationError(f"root is not present in explicit seed map: {probability}/{root}") from exc
    if set(pair) != {"calibration", "evaluation"}:
        raise RecoveryValidationError("seed map entry must contain calibration and evaluation")
    return int(pair["calibration"]), int(pair["evaluation"])


def validate_checkpoint(path: Path, *, expected_seeds, detector_count=40,
                        calibration_shots=2000, evaluation_shots=2500,
                        prediction_arms=3, prediction_verifier=None,
                        estimator_verifier=None, checkpoint_verifier=None) -> dict:
    """Validate one committed archive, including prediction recomputation.

    `prediction_verifier(detectors, predictions)` must independently rebuild
    the frozen decoders and return True. It is mandatory for `complete` roots.
    """
    path = Path(path)
    match = ROOT_NAME.fullmatch(path.name)
    if not match:
        raise RecoveryValidationError(f"noncanonical root archive filename: {path.name}")
    probability, root = float(match.group(1)), int(match.group(2))
    cal_seed, eval_seed = _seed_pair(expected_seeds, probability, root)
    digest = verify_committed_npz(path)
    with np.load(path, allow_pickle=False) as z:
        fields = set(z.files)
        required = {"phase", "calibration_detectors", "probability", "root", "seed_calibration"}
        if not required <= fields:
            raise RecoveryValidationError(f"missing archive fields: {sorted(required - fields)}")
        phase = str(_scalar(z, "phase"))
        if phase not in {"calibration_complete", "evaluation_complete", "complete"}:
            raise RecoveryValidationError(f"unsupported checkpoint phase: {phase}")
        expected_fields = {
            "calibration_complete": {"phase", "calibration_detectors", "probability", "root", "seed_calibration"},
            "evaluation_complete": {"phase", "calibration_detectors", "evaluation_detectors", "observables",
                                   "probability", "root", "seed_calibration", "seed_evaluation"},
            "complete": {"phase", "calibration_detectors", "evaluation_detectors", "observables", "predictions",
                         "p_hat", "probability", "root", "seed_calibration", "seed_evaluation"},
        }[phase]
        if fields != expected_fields:
            raise RecoveryValidationError(f"checkpoint fields differ from frozen {phase} schema")
        if float(_scalar(z, "probability")) != probability or int(_scalar(z, "root")) != root:
            raise RecoveryValidationError("filename and archive identity differ")
        if int(_scalar(z, "seed_calibration")) != cal_seed:
            raise RecoveryValidationError("calibration seed differs from explicit frozen mapping")
        calibration = np.asarray(z["calibration_detectors"])
        if calibration.shape != (calibration_shots, detector_count):
            raise RecoveryValidationError("calibration detector shape mismatch")
        _binary(calibration, "calibration_detectors")
        result = {"path": path, "probability": probability, "root": root, "phase": phase,
                  "sha256": digest, "calibration_rows": int(calibration.shape[0]),
                  "evaluation_rows": 0, "complete": phase == "complete"}
        if phase in {"evaluation_complete", "complete"}:
            needed = {"evaluation_detectors", "observables", "seed_evaluation"}
            if not needed <= fields:
                raise RecoveryValidationError(f"missing evaluation fields: {sorted(needed - fields)}")
            if int(_scalar(z, "seed_evaluation")) != eval_seed:
                raise RecoveryValidationError("evaluation seed differs from explicit frozen mapping")
            detectors = np.asarray(z["evaluation_detectors"])
            observables = np.asarray(z["observables"])
            if detectors.shape != (evaluation_shots, detector_count) or observables.shape != (evaluation_shots,):
                raise RecoveryValidationError("evaluation detector/observable shape mismatch")
            _binary(detectors, "evaluation_detectors")
            _binary(observables, "observables")
            result["evaluation_rows"] = int(detectors.shape[0])
            if phase == "evaluation_complete":
                forbidden = {"predictions", "p_hat"} & fields
                if forbidden:
                    raise RecoveryValidationError("evaluation_complete archive unexpectedly has result fields")
            else:
                if not {"predictions", "p_hat"} <= fields:
                    raise RecoveryValidationError("complete archive lacks predictions or p_hat")
                predictions = np.asarray(z["predictions"])
                if predictions.shape != (prediction_arms, evaluation_shots):
                    raise RecoveryValidationError("prediction shape mismatch")
                _binary(predictions, "predictions")
                if np.asarray(z["p_hat"]).ndim != 0 or not np.isfinite(float(_scalar(z, "p_hat"))):
                    raise RecoveryValidationError("invalid p_hat")
                if estimator_verifier is None or not bool(estimator_verifier(calibration, float(_scalar(z, "p_hat")))):
                    raise RecoveryValidationError("saved p_hat does not independently reproduce from calibration detectors")
                if checkpoint_verifier is not None:
                    valid_prediction = checkpoint_verifier(
                        path, detectors, predictions, float(_scalar(z, "p_hat")),
                        probability, root)
                else:
                    valid_prediction = (prediction_verifier is not None and
                                        bool(prediction_verifier(detectors, predictions)))
                if not bool(valid_prediction):
                    raise RecoveryValidationError("independent prediction verification failed or omitted")
        return result


def scan_archive_ledger(run_dir: Path, *, expected_seeds, expected_roots,
                        detector_count=40, calibration_shots=2000,
                        evaluation_shots=2500, prediction_arms=3,
                        prediction_verifier=None, estimator_verifier=None,
                        checkpoint_verifier=None) -> dict:
    """Rebuild shot/root counts solely from committed, validated archives."""
    run_dir = Path(run_dir)
    root_dir = run_dir / "roots"
    if not root_dir.is_dir():
        raise RecoveryValidationError("root archive directory is missing")
    orphan_temps = list(run_dir.rglob(".qtmp-v43-*.tmp"))
    if orphan_temps:
        raise RecoveryValidationError("unresolved atomic-write temporary exists; recovery must reconcile it first")
    transaction_dir = run_dir / ".stage5-v43-transactions" / "writes"
    if transaction_dir.exists():
        unresolved = [p for p in transaction_dir.glob("*.json")
                      if not p.name.endswith(".applied.json") and not p.with_suffix(".applied.json").exists()]
        if unresolved:
            raise RecoveryValidationError("unapplied write intent exists; recovery must reconcile it first")
    expected_roots = list(expected_roots)
    expected_ids = {(float(p), int(r)) for p, r in expected_roots}
    if len(expected_ids) != len(expected_roots):
        raise RecoveryValidationError("expected root identity list contains duplicates")
    derived = [int(v) for pair in expected_seeds.values() for v in pair.values()]
    if len(derived) != len(set(derived)):
        raise RecoveryValidationError("explicit calibration/evaluation seed mapping contains collisions")
    records, identities, seen_seeds = [], set(), set()
    for path in sorted(root_dir.glob("*.npz")):
        record = validate_checkpoint(path, expected_seeds=expected_seeds,
            detector_count=detector_count, calibration_shots=calibration_shots,
            evaluation_shots=evaluation_shots, prediction_arms=prediction_arms,
            prediction_verifier=prediction_verifier,
            estimator_verifier=estimator_verifier,
            checkpoint_verifier=checkpoint_verifier)
        identity = (record["probability"], record["root"])
        if identity in identities:
            raise RecoveryValidationError(f"duplicate condition/root identity: {identity}")
        identities.add(identity)
        with np.load(path, allow_pickle=False) as z:
            phase = str(_scalar(z, "phase"))
            seeds = [int(_scalar(z, "seed_calibration"))]
            if phase in {"evaluation_complete", "complete"}:
                seeds.append(int(_scalar(z, "seed_evaluation")))
        for seed in seeds:
            if seed in seen_seeds:
                raise RecoveryValidationError("a persisted RNG seed is reused across archives")
            seen_seeds.add(seed)
        records.append({"file": path.name, "probability": record["probability"],
                        "root": record["root"], "phase": record["phase"],
                        "sha256": record["sha256"], "calibration_rows": record["calibration_rows"],
                        "evaluation_rows": record["evaluation_rows"]})
    extra = identities - expected_ids
    if extra:
        raise RecoveryValidationError(f"unexpected root identities: {sorted(extra)}")
    cal_rows = sum(row["calibration_rows"] for row in records)
    eval_rows = sum(row["evaluation_rows"] for row in records)
    complete_roots = sum(row["phase"] == "complete" for row in records)
    pending = [{"probability": row["probability"], "root": row["root"]}
               for row in records if row["phase"] == "evaluation_complete"]
    payload = {"records": records, "calibration_shots_generated": cal_rows,
               "evaluation_shots_generated": eval_rows,
               "unique_shots_generated": cal_rows + eval_rows,
               "completed_roots": complete_roots, "archive_count": len(records),
               "recoverable_evaluation_complete_roots": pending}
    payload["ledger_sha256"] = sha256_bytes(json.dumps(payload, sort_keys=True,
        separators=(",", ":")).encode("utf-8"))
    return payload


def reconstruct_status(status: dict, ledger: dict) -> dict:
    """Idempotently replace counters with validated ledger totals, never add."""
    inflight = status.get("in_flight")
    if inflight:
        key = (float(inflight.get("p")), int(inflight.get("root")))
        checkpoint = next((row for row in ledger["records"]
                           if (row["probability"], row["root"]) == key), None)
        phase = checkpoint["phase"] if checkpoint else None
        kind = inflight.get("kind")
        if kind == "calibration":
            durable = phase in {"calibration_complete", "evaluation_complete", "complete"}
        elif kind == "evaluation":
            durable = phase in {"evaluation_complete", "complete"}
        else:
            durable = False
        if not durable:
            raise RecoveryValidationError(
                f"in-flight {kind!r} stream has no corresponding durable checkpoint; fail closed"
            )
    updated = dict(status)
    for key in ("calibration_shots_generated", "evaluation_shots_generated",
                "unique_shots_generated", "completed_roots"):
        updated[key] = int(ledger[key])
    updated["in_flight"] = None
    updated["status"] = "recovery_reconciled"
    updated["reconciliation"] = {"method": "hash_verified_archive_ledger_v43",
                                 "ledger_sha256": ledger["ledger_sha256"],
                                 "recoverable_evaluation_complete_roots": ledger["recoverable_evaluation_complete_roots"]}
    return updated


def persist_reconstructed_status(status_path: Path, status: dict, ledger: dict, *, run_dir: Path,
                                 deadline_monotonic: float) -> dict:
    """CAS-persist a reconstructed status in a recovery copy only."""
    status_path, run_dir = Path(status_path), Path(run_dir)
    require_recovery_workspace(run_dir)
    try:
        status_path.resolve().relative_to(run_dir.resolve())
    except ValueError as exc:
        raise ValueError("status path must be inside the recovery run directory") from exc
    old_hash = sha256_file(status_path)
    updated = reconstruct_status(status, ledger)
    return atomic_write_json(status_path, updated, run_dir=run_dir,
                             expected_old_sha256=old_hash,
                             deadline_monotonic=deadline_monotonic)


def complete_evaluation_checkpoint(path: Path, *, run_dir: Path, expected_seeds,
                                   estimate_fn, decode_fn, prediction_verifier,
                                   deadline_monotonic: float, detector_count=40,
                                   calibration_shots=2000, evaluation_shots=2500,
                                   prediction_arms=3, checkpoint_verifier=None,
                                   fault=None) -> dict:
    """Finish a saved evaluation batch. This API has no sampler argument."""
    path, run_dir = Path(path), Path(run_dir)
    require_recovery_workspace(run_dir)
    try:
        path.resolve().relative_to(run_dir.resolve())
    except ValueError as exc:
        raise RecoveryValidationError("checkpoint must be inside the recovery copy") from exc
    path = Path(path)
    try:
        verify_committed_npz(path)
    except UncommittedCheckpointError:
        recover_npz_commit(path, run_dir=run_dir, deadline_monotonic=deadline_monotonic)
    current = validate_checkpoint(path, expected_seeds=expected_seeds,
        detector_count=detector_count, calibration_shots=calibration_shots,
        evaluation_shots=evaluation_shots, prediction_arms=prediction_arms,
        prediction_verifier=prediction_verifier,
        estimator_verifier=lambda cal, value: abs(float(estimate_fn(cal)) - value) <= 1e-12,
        checkpoint_verifier=checkpoint_verifier)
    with np.load(path, allow_pickle=False) as z:
        phase = str(_scalar(z, "phase"))
        if phase == "complete":
            p_hat_saved = float(_scalar(z, "p_hat"))
            p_hat_rebuilt = float(estimate_fn(np.asarray(z["calibration_detectors"])))
            if not np.isfinite(p_hat_rebuilt) or abs(p_hat_saved - p_hat_rebuilt) > 1e-12:
                raise RecoveryValidationError("saved p_hat does not reproduce from calibration detectors")
            return {"state": "already_complete", "archive_sha256": current["sha256"],
                    "p_hat": p_hat_saved, "calibration_rows_reused": calibration_shots,
                    "evaluation_rows_reused": evaluation_shots, "additional_samples_generated": 0}
        if phase != "evaluation_complete":
            raise RecoveryValidationError("only evaluation_complete checkpoints can be finished")
        arrays = {key: np.asarray(z[key]).copy() for key in z.files}
    p_hat = float(estimate_fn(arrays["calibration_detectors"]))
    if not np.isfinite(p_hat):
        raise RecoveryValidationError("detector-only estimator returned a non-finite value")
    predictions = np.asarray(decode_fn(p_hat, arrays["evaluation_detectors"]))
    if predictions.shape != (prediction_arms, evaluation_shots):
        raise RecoveryValidationError("decoder returned unexpected prediction dimensions")
    _binary(predictions, "predictions")
    if not bool(prediction_verifier(arrays["evaluation_detectors"], predictions)):
        raise RecoveryValidationError("independent prediction verification failed")
    arrays["phase"] = np.asarray("complete")
    arrays["p_hat"] = np.asarray(p_hat)
    arrays["predictions"] = predictions.astype(np.uint8, copy=False)
    archive_hash = sha256_file(path)
    marker_path = Path(str(path) + ".commit.json")
    marker_hash = sha256_file(marker_path)
    write_committed_npz(path, arrays, run_dir=run_dir,
        expected_archive_sha256=archive_hash, expected_marker_sha256=marker_hash,
        deadline_monotonic=deadline_monotonic, fault=fault)
    result = validate_checkpoint(path, expected_seeds=expected_seeds,
        detector_count=detector_count, calibration_shots=calibration_shots,
        evaluation_shots=evaluation_shots, prediction_arms=prediction_arms,
        prediction_verifier=prediction_verifier,
        estimator_verifier=lambda cal, value: abs(float(estimate_fn(cal)) - value) <= 1e-12,
        checkpoint_verifier=checkpoint_verifier)
    return {"state": "complete", "archive_sha256": result["sha256"], "p_hat": p_hat,
            "calibration_rows_reused": calibration_shots,
            "evaluation_rows_reused": evaluation_shots,
            "additional_samples_generated": 0}


def create_recovery_copy(source_dir: Path, destination_dir: Path, *, source_inventory_path: Path,
                         source_repository_root: Path,
                         destination_provenance_path: Path | None = None) -> dict:
    """Create a verified new recovery copy; source files are read-only inputs.

    Validates every inventory entry before copying a narrow allowlist: status,
    root NPZs and their commit markers. Lock/owner files are recorded as omitted.
    """
    source_dir = Path(source_dir).resolve()
    destination_dir = Path(destination_dir).resolve()
    source_repository_root = Path(source_repository_root).resolve()
    if destination_dir.exists():
        raise FileExistsError(f"recovery destination already exists: {destination_dir}")
    try:
        destination_dir.relative_to(source_dir)
    except ValueError:
        pass
    else:
        raise ValueError("recovery destination must not be nested within the original run")
    try:
        source_dir.relative_to(destination_dir)
    except ValueError:
        pass
    else:
        raise ValueError("recovery destination must not contain the original run")
    inventory_path = Path(source_inventory_path).resolve()
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    entries = inventory.get("files")
    if not isinstance(entries, list) or inventory.get("file_count") != len(entries):
        raise RecoveryValidationError("source inventory schema/count invalid")
    if inventory.get("base_commit") != "8c06750808582137f6a81e2170ad702a552594fb":
        raise RecoveryValidationError("source inventory does not identify the authorized failed-run base commit")
    if len({row.get("path") for row in entries}) != len(entries):
        raise RecoveryValidationError("source inventory contains duplicate file paths")
    inventory_sha = sha256_file(inventory_path)
    checked = {}
    for row in entries:
        rel = row["path"]
        path = Path(rel)
        if path.is_absolute() or ".." in path.parts:
            raise RecoveryValidationError("inventory path escapes repository")
        file_path = source_repository_root / path
        if not file_path.is_file() or sha256_file(file_path) != row["sha256"]:
            raise RecoveryValidationError(f"source inventory mismatch: {rel}")
        checked[rel.replace("\\", "/")] = row["sha256"]
    try:
        source_repo_rel = source_dir.relative_to(source_repository_root).as_posix()
    except ValueError as exc:
        raise RecoveryValidationError("source run is outside the inventory repository root") from exc
    source_inventory_hashes = {row["path"].replace("\\", "/"): row["sha256"] for row in entries}
    root_candidates = []
    for path in sorted((source_dir / "roots").glob("root_p*.npz")):
        rel_npz = path.relative_to(source_dir).as_posix()
        marker = Path(str(path) + ".commit.json")
        rel_marker = marker.relative_to(source_dir).as_posix()
        try:
            path.resolve().relative_to(source_dir)
            marker.resolve().relative_to(source_dir)
        except ValueError as exc:
            raise RecoveryValidationError("root archive symlink escapes source run") from exc
        root_candidates.extend([(path, rel_npz), (marker, rel_marker)])
    status = source_dir / "status.json"
    if not status.is_file():
        raise RecoveryValidationError("source status.json missing")
    root_candidates.append((status, "status.json"))
    copied = {}
    destination_dir.mkdir(parents=True)
    try:
        for src, rel in root_candidates:
            digest = sha256_file(src)
            if src.name in ACTIVE_LOCK_NAMES or src.name.startswith(".stage5-"):
                continue
            repo_rel = f"{source_repo_rel}/{rel}"
            if source_inventory_hashes.get(repo_rel) != digest:
                raise RecoveryValidationError(f"copy candidate is absent from or differs from source inventory: {repo_rel}")
            target = destination_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, target)
            if sha256_file(target) != digest:
                raise RecoveryValidationError(f"copy hash mismatch: {rel}")
            copied[rel] = digest
        provenance = {
            "format": "qshift-stage5-v43-recovery-copy-provenance",
            "source_run_directory": str(source_dir),
            "source_inventory_path": str(inventory_path),
            "source_inventory_sha256": inventory_sha,
            "source_manifest_hashes": source_inventory_hashes,
            "source_run_relative_path": source_repo_rel,
            "source_inventory_file_count_verified": len(entries),
            "copied_files": copied,
            "copied_file_count": len(copied),
            "omitted_active_lock_and_owner_files": sorted(
                p.name for p in source_dir.iterdir() if p.name in ACTIVE_LOCK_NAMES or p.name.startswith(".stage5-")
            ),
            "recovery_sampling_performed": False,
        }
        prov_path = destination_provenance_path or destination_dir / "RECOVERY_PROVENANCE.json"
        prov_path = Path(prov_path)
        try:
            prov_path.resolve(strict=False).relative_to(destination_dir)
        except ValueError as exc:
            raise ValueError("recovery provenance must be written within the new recovery directory") from exc
        prov_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(prov_path, provenance, run_dir=destination_dir,
                          expected_old_sha256=None, deadline_monotonic=time.monotonic() + 60)
        return provenance
    except BaseException:
        # The caller owns destination cleanup; never touch source evidence.
        raise
