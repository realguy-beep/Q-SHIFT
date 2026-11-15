"""Fail-closed owner-approval validation for the V2.3 launch path.

The approval file is deliberately not shipped as a valid record. It is a
manual, out-of-band owner action bound to a clean Git commit and frozen inputs.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from outputs.strong_fixed_baselines_v2.freeze_pretest_v2 import (
    CONFIG_PATH,
    INVENTORY_PATH,
    ROOT,
    verify_freeze as verify_v2_freeze,
)
from outputs.strong_fixed_baselines_v2_3.candidate_freeze_v2_3 import (
    FREEZE_PATH as CANDIDATE_FREEZE_PATH,
    ORIGINAL_FREEZE_PATH,
    sha256,
    verify_candidate_freeze,
)

HERE = Path(__file__).resolve().parent
RUNNER_PATH = HERE / "run_development_v2_3.py"
FROZEN_RUNNER_PATH = CONFIG_PATH.parent / "run_development_v2.py"
APPROVAL_PATH = HERE / "OWNER_APPROVAL_V2_3_TOKEN.json"
OWNER_ID = "realguy-beep"
EXPERIMENT_ID = "qshift-strong-fixed-baselines-v2"
REQUIRED_APPROVAL_KEYS = {
    "schema_version", "approval_status", "approved_by", "approved_at_utc", "expires_at_utc",
    "approval_statement", "experiment_id", "approved_commit_sha",
    "candidate_freeze_sha256", "original_freeze_sha256",
    "configuration_sha256", "seed_inventory_sha256",
    "frozen_runner_sha256", "authorized_launcher_sha256",
    "authorization_validator_sha256", "candidate_freeze_verifier_sha256",
    "runtime_environment_sha256",
}
PRE_INVENTORY_BINDINGS = {
    "approved_commit_sha": "commit_sha",
    "candidate_freeze_sha256": "candidate_freeze_sha256",
    "original_freeze_sha256": "original_freeze_sha256",
    "configuration_sha256": "configuration_sha256",
    "frozen_runner_sha256": "frozen_runner_sha256",
    "authorized_launcher_sha256": "authorized_launcher_sha256",
    "authorization_validator_sha256": "authorization_validator_sha256",
    "candidate_freeze_verifier_sha256": "candidate_freeze_verifier_sha256",
    "runtime_environment_sha256": "runtime_environment_sha256",
}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError(f"malformed JSON authorization/evidence file: {path}") from error


def current_git_identity(root: Path = ROOT) -> tuple[str, bool]:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True,
                            capture_output=True, text=True).stdout.strip()
    status = subprocess.run(["git", "status", "--porcelain"], cwd=root, check=True,
                            capture_output=True, text=True).stdout
    return commit, not bool(status.strip())


def runtime_environment() -> dict[str, str]:
    environment = {"python": sys.version.split()[0], "platform": platform.platform()}
    for distribution in ("stim", "pymatching", "numpy"):
        try:
            environment[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError as error:
            raise RuntimeError(f"required runtime dependency is unavailable: {distribution}") from error
    return environment


def expected_pre_inventory_identity(*, root: Path = ROOT, commit_sha: str | None = None) -> dict[str, str]:
    """Hash everything except the inventory so denied launches never read it."""
    actual_commit, clean = current_git_identity(root)
    if not clean:
        raise PermissionError("authorization requires a clean working tree")
    if commit_sha is not None and commit_sha != actual_commit:
        raise PermissionError("approved commit is not the current HEAD")
    if not re.fullmatch(r"[0-9a-f]{40}", actual_commit):
        raise PermissionError("current Git commit identity is malformed")
    runtime = json.dumps(runtime_environment(), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "commit_sha": actual_commit,
        "candidate_freeze_sha256": sha256(CANDIDATE_FREEZE_PATH),
        "original_freeze_sha256": sha256(ORIGINAL_FREEZE_PATH),
        "configuration_sha256": sha256(CONFIG_PATH),
        "frozen_runner_sha256": sha256(FROZEN_RUNNER_PATH),
        "authorized_launcher_sha256": sha256(RUNNER_PATH),
        "authorization_validator_sha256": sha256(HERE / "authorization_v2_3.py"),
        "candidate_freeze_verifier_sha256": sha256(HERE / "candidate_freeze_v2_3.py"),
        "runtime_environment_sha256": hashlib.sha256(runtime).hexdigest(),
    }


def validate_approval_preamble(record: dict, *, validation_time: datetime | None = None) -> None:
    if not isinstance(record, dict) or set(record) != REQUIRED_APPROVAL_KEYS:
        raise PermissionError("approval record has missing or unexpected fields")
    if record.get("schema_version") != 1 or record.get("approval_status") != "OWNER_AUTHORIZED":
        raise PermissionError("approval record is not explicitly owner-authorized")
    if record.get("approved_by") != OWNER_ID or record.get("experiment_id") != EXPERIMENT_ID:
        raise PermissionError("approval owner or experiment identity mismatch")
    expected_statement = (
        "I explicitly authorize the frozen Q-SHIFT V2 development experiment "
        "identified by the exact commit, freeze, configuration, seed inventory, and runner hashes in this record."
    )
    if record.get("approval_statement") != expected_statement:
        raise PermissionError("approval statement does not contain the required explicit authorization")
    try:
        approved_at = datetime.fromisoformat(str(record["approved_at_utc"]).replace("Z", "+00:00"))
        expires_at = datetime.fromisoformat(str(record["expires_at_utc"]).replace("Z", "+00:00"))
    except ValueError as error:
        raise PermissionError("approval timestamp is malformed") from error
    if approved_at.tzinfo is None or expires_at.tzinfo is None:
        raise PermissionError("approval timestamps must include a UTC offset")
    now = validation_time or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise PermissionError("approval validation time must include a UTC offset")
    now = now.astimezone(timezone.utc)
    if approved_at > now.replace(microsecond=0) or expires_at <= now:
        raise PermissionError("approval is not yet valid or has expired")
    if expires_at <= approved_at or (expires_at - approved_at).total_seconds() > 24 * 60 * 60:
        raise PermissionError("approval validity window must be positive and no longer than 24 hours")
    for key in REQUIRED_APPROVAL_KEYS - {
        "schema_version", "approval_status", "approved_by", "approved_at_utc", "expires_at_utc",
        "approval_statement", "experiment_id",
        "approved_commit_sha",
    }:
        if not isinstance(record.get(key), str) or not re.fullmatch(r"[0-9a-f]{64}", record[key]):
            raise PermissionError(f"approval binding is missing or malformed: {key}")
    if not isinstance(record.get("approved_commit_sha"), str) or not re.fullmatch(r"[0-9a-f]{40}", record["approved_commit_sha"]):
        raise PermissionError("approval binding is missing or malformed: approved_commit_sha")


def validate_pre_inventory_bindings(record: dict, expected: dict[str, str]) -> None:
    for approval_key, identity_key in PRE_INVENTORY_BINDINGS.items():
        if record[approval_key] != expected[identity_key]:
            raise PermissionError(f"approval is stale or bound to a different {approval_key}")


def validate_inventory_binding(record: dict, inventory_path: Path = INVENTORY_PATH) -> str:
    digest = sha256(inventory_path)
    if record.get("seed_inventory_sha256") != digest:
        raise PermissionError("approved seed inventory hash does not match")
    return digest


def validate_inventory(inventory: dict, expected_sha256: str, inventory_path: Path = INVENTORY_PATH) -> None:
    if inventory.get("sampling_performed") is not False or inventory.get("sealed_test_access") is not False:
        raise PermissionError("seed inventory provenance is not no-sampling/no-test-access")
    if inventory.get("historical_collisions") or inventory.get("candidate_internal_collisions"):
        raise PermissionError("seed inventory contains recorded collisions")
    seeds = [int(row["seed"]) for row in inventory.get("streams", [])]
    if len(seeds) != len(set(seeds)) or len(seeds) != int(inventory.get("candidate_unique_seed_count", -1)):
        raise PermissionError("seed inventory streams are not unique")
    if sha256(inventory_path) != expected_sha256:
        raise PermissionError("seed inventory hash differs from owner approval")


def authorize_launch(approval_path: Path = APPROVAL_PATH) -> tuple[dict, dict]:
    """Validate in stages: absent/invalid approval fails before inventory I/O."""
    if not approval_path.is_file():
        raise PermissionError("owner approval record is missing")
    record = read_json(approval_path)
    validate_approval_preamble(record)
    expected = expected_pre_inventory_identity(commit_sha=record["approved_commit_sha"])
    validate_pre_inventory_bindings(record, expected)

    # Only after a well-formed, explicitly authorized record matches the live
    # commit/freeze/config/runner do we hash and parse the inventory.
    inventory_digest = validate_inventory_binding(record)
    verify_v2_freeze()
    verify_candidate_freeze()
    inventory = read_json(INVENTORY_PATH)
    validate_inventory(inventory, inventory_digest)
    identity = {
        **expected,
        "seed_inventory_sha256": inventory_digest,
        "approval_record_sha256": sha256(approval_path),
        "approved_by": record["approved_by"],
        "approved_at_utc": record["approved_at_utc"],
    }
    return identity, record

