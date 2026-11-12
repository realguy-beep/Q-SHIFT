"""V2.4 audit adapter: verify execution approval identity, then run V2 audit.

The underlying V2 auditor still verifies the original immutable freeze and
recomputes saved-array results. This adapter adds launch approval provenance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime

from outputs.strong_fixed_baselines_v2 import audit_saved_arrays_v2 as base_audit
from outputs.strong_fixed_baselines_v2_4 import authorization_v2_4 as authorization
from outputs.strong_fixed_baselines_v2_4 import run_development_v2_4 as launcher
from outputs.strong_fixed_baselines_v2_4.candidate_freeze_v2_4 import verify_candidate_freeze

IDENTITY_NAME = launcher.IDENTITY_NAME
APPROVAL_RECEIPT_NAME = launcher.APPROVAL_RECEIPT_NAME


def verify_execution_identity(run_dir: Path) -> dict:
    run_dir = run_dir.resolve()
    if base_audit.HERE.resolve() not in run_dir.parents:
        raise ValueError("V2.4 audit accepts only run data under the V2 output tree")
    identity_path = run_dir / IDENTITY_NAME
    receipt_path = run_dir / APPROVAL_RECEIPT_NAME
    if not identity_path.is_file() or not receipt_path.is_file():
        raise RuntimeError("authorized execution identity or owner approval receipt is missing")
    identity = json.loads(identity_path.read_text(encoding="utf-8"))
    receipt = authorization.read_json(receipt_path)
    authorization.validate_approval_preamble(
        receipt,
        validation_time=datetime.fromisoformat(
            str(identity.get("authorization_checked_at_utc", "")).replace("Z", "+00:00")
        ),
    )
    freeze = verify_candidate_freeze()
    expected = authorization.expected_pre_inventory_identity(
        commit_sha=receipt["approved_commit_sha"]
    )
    expected["seed_inventory_sha256"] = authorization.validate_inventory_binding(receipt)
    expected["approval_record_sha256"] = authorization.sha256(receipt_path)
    authorization.validate_pre_inventory_bindings(receipt, expected)
    if identity.get("identity_status") != "OWNER_AUTHORIZED_EXECUTION_IDENTITY":
        raise RuntimeError("run identity has an unexpected status")
    required = {
        "approved_commit_sha": expected["commit_sha"],
        "candidate_freeze_sha256": expected["candidate_freeze_sha256"],
        "original_freeze_sha256": expected["original_freeze_sha256"],
        "configuration_sha256": expected["configuration_sha256"],
        "seed_inventory_sha256": expected["seed_inventory_sha256"],
        "frozen_runner_sha256": expected["frozen_runner_sha256"],
        "authorized_launcher_sha256": expected["authorized_launcher_sha256"],
        "authorization_validator_sha256": expected["authorization_validator_sha256"],
        "candidate_freeze_verifier_sha256": expected["candidate_freeze_verifier_sha256"],
        "runtime_environment_sha256": expected["runtime_environment_sha256"],
        "approval_record_sha256": expected["approval_record_sha256"],
        "approved_by": receipt["approved_by"],
        "approved_at_utc": receipt["approved_at_utc"],
        "approval_expires_at_utc": receipt["expires_at_utc"],
    }
    for key, value in required.items():
        if identity.get(key) != value:
            raise RuntimeError(f"run execution identity mismatch: {key}")
    if identity.get("experiment_id") != authorization.EXPERIMENT_ID:
        raise RuntimeError("run execution identity belongs to another experiment")
    if identity.get("authorization_checked_at_utc") is None:
        raise RuntimeError("run identity lacks the authorization-time record")
    if identity.get("runtime_environment", {}).get("stim") is None or identity.get("runtime_environment", {}).get("pymatching") is None:
        raise RuntimeError("run identity lacks simulator/decoder version provenance")
    recorded_environment_hash = hashlib.sha256(
        json.dumps(identity["runtime_environment"], sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if recorded_environment_hash != identity.get("runtime_environment_sha256"):
        raise RuntimeError("recorded runtime environment hash does not match its dependency versions")
    if freeze.get("sampling_authorized") is not False:
        raise RuntimeError("V2.4 candidate freeze was altered to authorize sampling")
    return {
        "identity": identity,
        "identity_sha256": hashlib.sha256(identity_path.read_bytes()).hexdigest(),
        "approval_receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        "candidate_freeze_sha256": expected["candidate_freeze_sha256"],
        "original_freeze_sha256": expected["original_freeze_sha256"],
    }


def audit_run(run_dir: Path, output_path: Path) -> dict:
    provenance = verify_execution_identity(run_dir)
    # The original independent array audit remains the sole metric recomputer.
    result = base_audit.audit_run(run_dir.resolve(), output_path.resolve())
    result["approved_execution_identity"] = {
        "identity_sha256": provenance["identity_sha256"],
        "approval_receipt_sha256": provenance["approval_receipt_sha256"],
        "candidate_freeze_sha256": provenance["candidate_freeze_sha256"],
        "original_freeze_sha256": provenance["original_freeze_sha256"],
        "approved_commit_sha": provenance["identity"]["approved_commit_sha"],
        "approved_by": provenance["identity"]["approved_by"],
        "runtime_environment": provenance["identity"]["runtime_environment"],
    }
    output_path = output_path.resolve()
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit saved arrays and approved V2.4 run identity; read-only")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit_run(args.run_dir, args.output)
    print(json.dumps({"audit_status": result["audit_status"],
                      "approved_commit_sha": result["approved_execution_identity"]["approved_commit_sha"]}, indent=2))


if __name__ == "__main__":
    main()

