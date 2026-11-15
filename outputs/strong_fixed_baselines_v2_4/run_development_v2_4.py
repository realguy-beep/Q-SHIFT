"""Approval-gated entrypoint for the frozen V2 development runner.

This wrapper never changes the on-disk scientific configuration. It validates
an owner-created, identity-bound approval record, persists its provenance, then
provides the original runner a short-lived in-memory copy with only the
sampling guard set true. Running V2's original entrypoint directly remains
fail-closed because its frozen config still says false.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Callable

from outputs.strong_fixed_baselines_v2 import run_development_v2 as frozen_runner
from outputs.strong_fixed_baselines_v2_4 import authorization_v2_4 as authorization

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V2_DIR = ROOT / "outputs" / "strong_fixed_baselines_v2"
RUN_DIR = V2_DIR / "run_v2_4_token"
IDENTITY_NAME = "EXECUTION_IDENTITY_V2_4.json"
APPROVAL_RECEIPT_NAME = "OWNER_APPROVAL_RECEIPT_V2_4.json"


def canonical_json(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def package_versions() -> dict[str, str]:
    return authorization.runtime_environment()


def build_execution_identity(identity: dict, approval_record: dict, approval_sha256: str) -> dict:
    validated_at = datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": 1,
        "identity_status": "OWNER_AUTHORIZED_EXECUTION_IDENTITY",
        "experiment_id": authorization.EXPERIMENT_ID,
        "approved_by": approval_record["approved_by"],
        "approved_at_utc": approval_record["approved_at_utc"],
        "approval_expires_at_utc": approval_record["expires_at_utc"],
        "approval_record_sha256": approval_sha256,
        "authorization_checked_at_utc": validated_at,
        "approved_commit_sha": identity["commit_sha"],
        "candidate_freeze_sha256": identity["candidate_freeze_sha256"],
        "original_freeze_sha256": identity["original_freeze_sha256"],
        "configuration_sha256": identity["configuration_sha256"],
        "seed_inventory_sha256": identity["seed_inventory_sha256"],
        "frozen_runner_sha256": identity["frozen_runner_sha256"],
        "authorized_launcher_sha256": identity["authorized_launcher_sha256"],
        "authorization_validator_sha256": identity["authorization_validator_sha256"],
        "candidate_freeze_verifier_sha256": identity["candidate_freeze_verifier_sha256"],
        "runtime_environment": package_versions(),
        "runtime_environment_sha256": identity["runtime_environment_sha256"],
        "authorization_semantics": (
            "sampling_authorized is changed only in an in-memory config copy after all approval and freeze checks; "
            "the frozen on-disk V2 config and PRETEST_FREEZE_V2 remain sampling-disabled"
        ),
    }


def create_exclusive_json(path: Path, value: dict) -> None:
    """Create provenance once; never replace an existing file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json(value)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        existing = path.read_bytes()
        if existing != payload:
            raise RuntimeError(f"existing run provenance differs; refusing overwrite: {path}")
        return
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def create_or_verify_run_provenance(run_dir: Path, identity_record: dict, approval_path: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    identity_path = run_dir / IDENTITY_NAME
    receipt_path = run_dir / APPROVAL_RECEIPT_NAME
    receipt_bytes = approval_path.read_bytes()
    if hashlib.sha256(receipt_bytes).hexdigest() != identity_record["approval_record_sha256"]:
        raise RuntimeError("approval record changed after validation")
    if receipt_path.exists():
        if receipt_path.read_bytes() != receipt_bytes:
            raise RuntimeError("stored owner approval receipt differs; refusing resume")
    else:
        try:
            descriptor = os.open(receipt_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as error:
            raise RuntimeError("approval receipt creation raced; inspect run state") from error
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(receipt_bytes)
            stream.flush()
            os.fsync(stream.fileno())
    if identity_path.exists():
        current = json.loads(identity_path.read_text(encoding="utf-8"))
        expected = dict(identity_record)
        expected["authorization_checked_at_utc"] = current.get("authorization_checked_at_utc")
        if current != expected:
            raise RuntimeError("stored execution identity differs; refusing resume")
        authorization.validate_approval_preamble(
            json.loads(receipt_bytes.decode("utf-8")),
            validation_time=datetime.fromisoformat(
                str(current["authorization_checked_at_utc"]).replace("Z", "+00:00")
            ),
        )
    else:
        create_exclusive_json(identity_path, identity_record)


def dispatch_frozen_runner(run_dir: Path) -> None:
    """Run the hashed V2 implementation after the outer authorization gate."""
    original_reader = frozen_runner.read_json
    original_argv = sys.argv[:]

    def authorized_reader(path: Path) -> dict:
        value = original_reader(path)
        if Path(path).resolve() == frozen_runner.CONFIG_PATH.resolve():
            value = copy.deepcopy(value)
            value.setdefault("execution", {})["sampling_authorized"] = True
        return value

    frozen_runner.read_json = authorized_reader
    sys.argv = [
        str(frozen_runner.__file__),
        "--run-dir", str(run_dir),
        "--resume",  # identity was just validated/created; approval is never skipped.
    ]
    try:
        frozen_runner.main()
    finally:
        frozen_runner.read_json = original_reader
        sys.argv = original_argv


TERMINAL_SUCCESS_STATES = {"sampling_completed", "complete", "completed", "success", "succeeded", "done", "finished"}
RESUMABLE_STATES = {"running", "running_final_evaluation", "failed"}
STATUS_REQUIRED_KEYS = {
    "schema_version", "status", "pid", "started_unix", "updated_unix",
    "completed_archives", "allocated_unique_shots", "sampled_partition_shots",
    "final_evaluation_shots",
}
STATUS_ALLOWED_KEYS = STATUS_REQUIRED_KEYS | {
    "sampling_complete", "phase", "current_condition_probability", "current_root",
    "latest_committed_checkpoint", "latest_committed_checkpoint_sha256", "elapsed_seconds",
    "pooled_p", "safe_static_p", "completed_evaluation_roots",
    "final_evaluation_shots_committed", "error_type", "error",
}
RESUMABLE_PHASES = {"selection", "validation", "heldout_development_calibration"}


class ResumeStateError(RuntimeError):
    """Existing run state is not a recognized, safely resumable V2 state."""


def _strict_int(value: object, field: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ResumeStateError(f"status field {field} is malformed")
    return value


def _strict_finite_number(value: object, field: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ResumeStateError(f"status field {field} is malformed")
    number = float(value)
    if minimum is not None and number < minimum:
        raise ResumeStateError(f"status field {field} is outside its valid range")
    return number


def validate_incomplete_status(status: object, cfg: dict, *, now: float | None = None) -> dict:
    """Validate only states the frozen V2 runner can safely resume.

    The allowlist comes from V2's actual write_status/record_latest_checkpoint
    transitions. Unknown keys or contradictory terminal/progress metadata fail
    closed; this function never changes the supplied status record.
    """
    if not isinstance(status, dict):
        raise ResumeStateError("status record must be a JSON object")
    state = status.get("status")
    if status.get("sampling_complete") is True:
        raise ResumeStateError("completed sampling state cannot be resumed")
    if not isinstance(state, str):
        raise ResumeStateError("status field status is missing or malformed")
    if state in TERMINAL_SUCCESS_STATES:
        raise ResumeStateError("completed sampling state cannot be resumed")
    if state not in RESUMABLE_STATES:
        raise ResumeStateError(f"unrecognized or non-resumable status state: {state!r}")
    unknown = set(status) - STATUS_ALLOWED_KEYS
    missing = STATUS_REQUIRED_KEYS - set(status)
    if unknown or missing:
        raise ResumeStateError(f"status schema mismatch; unknown={sorted(unknown)}, missing={sorted(missing)}")
    if status.get("sampling_complete", False) is not False:
        raise ResumeStateError("sampling_complete must be boolean false for an incomplete state")
    if isinstance(status.get("schema_version"), bool) or not isinstance(status.get("schema_version"), int) or status.get("schema_version") != 1:
        raise ResumeStateError("unsupported status schema version")
    _strict_int(status["pid"], "pid", minimum=1)
    started = _strict_finite_number(status["started_unix"], "started_unix", minimum=0)
    updated = _strict_finite_number(status["updated_unix"], "updated_unix", minimum=0)
    if updated < started:
        raise ResumeStateError("status updated_unix precedes started_unix")
    allocated = _strict_int(status["allocated_unique_shots"], "allocated_unique_shots")
    if allocated != int(cfg["allocation"]["unique_shots"]):
        raise ResumeStateError("status allocation differs from the frozen V2 allocation")
    # These three counters are initialized to zero by the actual V2 runner and
    # are never incremented. They must not be interpreted as sampled progress.
    for field in ("completed_archives", "sampled_partition_shots", "final_evaluation_shots"):
        if _strict_int(status[field], field) != 0:
            raise ResumeStateError(f"status field {field} contradicts the frozen V2 writer")
    wall_limit = float(cfg["resources"]["wall_seconds_max"])
    instant = time.time() if now is None else float(now)
    if not math.isfinite(instant) or instant < started or instant - started > wall_limit:
        raise ResumeStateError("run is outside the frozen wall-clock resume window")

    phase = status.get("phase")
    if phase is not None and (not isinstance(phase, str) or phase not in RESUMABLE_PHASES):
        raise ResumeStateError("status phase is not emitted by the frozen V2 runner")
    has_condition = "current_condition_probability" in status
    has_root = "current_root" in status
    if has_condition != has_root:
        raise ResumeStateError("status condition/root fields are inconsistent")
    if has_condition:
        probability = _strict_finite_number(status["current_condition_probability"], "current_condition_probability", minimum=0)
        allowed = [float(x) for x in cfg["circuit"]["probabilities"]]
        root = _strict_int(status["current_root"], "current_root")
        if probability not in allowed or root >= int(cfg["partitions"]["evaluation_roots_per_condition"]):
            raise ResumeStateError("status condition/root is outside the frozen allocation")
    has_checkpoint = "latest_committed_checkpoint" in status
    has_checkpoint_hash = "latest_committed_checkpoint_sha256" in status
    if has_checkpoint != has_checkpoint_hash:
        raise ResumeStateError("checkpoint path/hash fields are inconsistent")
    if has_checkpoint:
        relative = status["latest_committed_checkpoint"]
        digest = status["latest_committed_checkpoint_sha256"]
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
            raise ResumeStateError("latest checkpoint path is malformed")
        if ".." in PurePosixPath(relative.replace("\\", "/")).parts:
            raise ResumeStateError("latest checkpoint path escapes the run directory")
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ResumeStateError("latest checkpoint hash is malformed")
    if "elapsed_seconds" in status:
        _strict_finite_number(status["elapsed_seconds"], "elapsed_seconds", minimum=0)

    for field in ("pooled_p", "safe_static_p"):
        if field in status:
            probability = _strict_finite_number(status[field], field, minimum=0)
            if probability > max(map(float, cfg["circuit"]["probabilities"])):
                raise ResumeStateError(f"status field {field} is outside the frozen probability range")
    has_eval_roots = "completed_evaluation_roots" in status
    has_eval_shots = "final_evaluation_shots_committed" in status
    if has_eval_roots != has_eval_shots:
        raise ResumeStateError("evaluation progress fields are inconsistent")
    if has_eval_roots:
        roots = _strict_int(status["completed_evaluation_roots"], "completed_evaluation_roots")
        shots = _strict_int(status["final_evaluation_shots_committed"], "final_evaluation_shots_committed")
        total_roots = len(cfg["circuit"]["probabilities"]) * int(cfg["partitions"]["evaluation_roots_per_condition"])
        shots_per_root = int(cfg["decoders"]["evaluation_shots_per_root"])
        total_shots = total_roots * shots_per_root
        if shots != roots * shots_per_root or roots >= total_roots or shots >= total_shots:
            raise ResumeStateError("evaluation counters are complete or inconsistent; refuse resume")
        if roots % 10 != 0:
            raise ResumeStateError("evaluation checkpoint counter is not a persisted V2 progress boundary")
    if state == "running_final_evaluation":
        if "pooled_p" not in status or "safe_static_p" not in status:
            raise ResumeStateError("final-evaluation status lacks frozen calibration values")
    elif state == "running" and (has_eval_roots or "pooled_p" in status or "safe_static_p" in status):
        raise ResumeStateError("running status contains final-evaluation fields")
    if state == "failed":
        if not isinstance(status.get("error_type"), str) or not status["error_type"] or not isinstance(status.get("error"), str):
            raise ResumeStateError("failed status lacks a valid frozen-runner error record")
    elif "error_type" in status or "error" in status:
        raise ResumeStateError("nonfailed status contains failure fields")
    return status


def read_resume_status(run_dir: Path, cfg: dict) -> dict:
    path = run_dir / "status.json"
    if not path.is_file():
        raise ResumeStateError("existing run directory has no status record; state is ambiguous")
    try:
        status = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ResumeStateError("existing status record is unreadable or malformed") from error
    return validate_incomplete_status(status, cfg)


def verify_existing_run_provenance(run_dir: Path, identity_record: dict, approval_path: Path) -> None:
    """Read-only verification for resume; missing provenance is never repaired."""
    identity_path = run_dir / IDENTITY_NAME
    receipt_path = run_dir / APPROVAL_RECEIPT_NAME
    if not identity_path.is_file() or not receipt_path.is_file():
        raise RuntimeError("resume requires an existing execution identity and approval receipt")
    approval_bytes = approval_path.read_bytes()
    if hashlib.sha256(approval_bytes).hexdigest() != identity_record.get("approval_record_sha256"):
        raise RuntimeError("current approval bytes do not match the run identity")
    if receipt_path.read_bytes() != approval_bytes:
        raise RuntimeError("stored approval receipt does not match the current approval")
    try:
        current = json.loads(identity_path.read_text(encoding="utf-8"))
        checked_at = datetime.fromisoformat(str(current.get("authorization_checked_at_utc", "")).replace("Z", "+00:00"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, ValueError) as error:
        raise RuntimeError("existing run identity is unreadable or malformed") from error
    expected = dict(identity_record)
    expected["authorization_checked_at_utc"] = current.get("authorization_checked_at_utc")
    if current != expected:
        raise RuntimeError("existing run identity does not match the current approved execution")
    authorization.validate_approval_preamble(
        json.loads(approval_bytes.decode("utf-8")), validation_time=checked_at
    )


def launch(
    argv: list[str] | None = None,
    *,
    approval_path: Path = authorization.APPROVAL_PATH,
    run_dir: Path = RUN_DIR,
    dispatch: Callable[[Path], None] | None = None,
) -> None:
    """Fail closed on terminal/ambiguous state before provenance writes or dispatch."""
    parser = argparse.ArgumentParser(description="Approval-gated frozen Q-SHIFT V2 development runner")
    parser.add_argument("--resume", action="store_true", help="resume the same identity-bound V2.4 run")
    args = parser.parse_args(argv)

    identity, approval_record = authorization.authorize_launch(approval_path)
    run_dir = run_dir.resolve()
    if run_dir != RUN_DIR.resolve():
        raise ValueError("V2.4 launch output is fixed; custom --run-dir is unsupported")
    if RUN_DIR.parent.resolve() not in run_dir.parents:
        raise ValueError("run directory escapes the V2 output tree")

    existing = run_dir.exists()
    if existing:
        status = read_resume_status(run_dir, json.loads(authorization.CONFIG_PATH.read_text(encoding="utf-8")))
        if not args.resume:
            raise FileExistsError("V2.4 run directory exists; only a valid incomplete state may use --resume")
    elif args.resume:
        raise ResumeStateError("--resume requested but no prior run directory exists")

    identity_record = build_execution_identity(identity, approval_record, identity["approval_record_sha256"])
    if existing:
        verify_existing_run_provenance(run_dir, identity_record, approval_path)
    else:
        create_or_verify_run_provenance(run_dir, identity_record, approval_path)
    (dispatch or dispatch_frozen_runner)(run_dir)


def main() -> None:
    launch()


if __name__ == "__main__":
    main()


