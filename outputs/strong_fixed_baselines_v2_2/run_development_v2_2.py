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
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from outputs.strong_fixed_baselines_v2 import run_development_v2 as frozen_runner
from outputs.strong_fixed_baselines_v2_2 import authorization_v2_2 as authorization

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V2_DIR = ROOT / "outputs" / "strong_fixed_baselines_v2"
RUN_DIR = V2_DIR / "run_v2_2_token"
IDENTITY_NAME = "EXECUTION_IDENTITY_V2_2.json"
APPROVAL_RECEIPT_NAME = "OWNER_APPROVAL_RECEIPT_V2_2.json"


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


def launch(
    argv: list[str] | None = None,
    *,
    approval_path: Path = authorization.APPROVAL_PATH,
    run_dir: Path = RUN_DIR,
    dispatch: Callable[[Path], None] | None = None,
) -> None:
    """No CLI or environment switch can skip approval verification."""
    parser = argparse.ArgumentParser(description="Approval-gated frozen Q-SHIFT V2 development runner")
    parser.add_argument("--resume", action="store_true", help="resume the same identity-bound V2.2 run")
    args = parser.parse_args(argv)

    identity, approval_record = authorization.authorize_launch(approval_path)
    run_dir = run_dir.resolve()
    allowed_parent = RUN_DIR.parent.resolve()
    if run_dir != RUN_DIR.resolve():
        raise ValueError("V2.2 launch output is fixed; custom --run-dir is unsupported")
    if allowed_parent not in run_dir.parents:
        raise ValueError("run directory escapes the V2 output tree")
    status_path = run_dir / "status.json"
    if status_path.is_file():
        status = json.loads(status_path.read_text(encoding="utf-8"))
        if status.get("status") in {"complete", "completed"}:
            raise RuntimeError("this authorized run is already complete; duplicate launch refused")
    if run_dir.exists() and not args.resume:
        raise FileExistsError("V2.2 run directory exists; use --resume only with the same valid approval")
    if args.resume and run_dir.exists() and not (run_dir / IDENTITY_NAME).is_file():
        raise RuntimeError("resume state lacks an execution identity; fail closed")

    identity_record = build_execution_identity(identity, approval_record, identity["approval_record_sha256"])
    create_or_verify_run_provenance(run_dir, identity_record, approval_path)
    (dispatch or dispatch_frozen_runner)(run_dir)


def main() -> None:
    launch()


if __name__ == "__main__":
    main()

