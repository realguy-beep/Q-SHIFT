"""Create a create-only, review-only authorization-layer freeze for V2.4."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone

from outputs.strong_fixed_baselines_v2.freeze_pretest_v2 import (
    CONFIG_PATH,
    INVENTORY_PATH,
    ROOT,
    verify_freeze as verify_v2_freeze,
)
from outputs.strong_fixed_baselines_v2_4.candidate_freeze_v2_4 import (
    FILES_TO_HASH,
    FREEZE_PATH,
    ORIGINAL_FREEZE_PATH,
    sha256,
)
from outputs.strong_fixed_baselines_v2_3.candidate_freeze_v2_3 import (
    FREEZE_PATH as PREVIOUS_CANDIDATE_FREEZE_PATH,
    verify_candidate_freeze as verify_previous_candidate_freeze,
)


def main() -> None:
    original = verify_v2_freeze()
    previous = verify_previous_candidate_freeze()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    if config["execution"].get("sampling_authorized") is not False:
        raise RuntimeError("V2.4 cannot change the original sampling-disabled config")
    if inventory.get("sampling_performed") is not False or inventory.get("sealed_test_access") is not False:
        raise RuntimeError("V2.4 requires the preserved no-sampling/no-test-access inventory")
    missing = [path for path in sorted(FILES_TO_HASH) if not (ROOT / path).is_file()]
    if missing:
        raise FileNotFoundError(f"V2.4 freeze inputs are missing: {missing}")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
                            capture_output=True, text=True).stdout.strip()
    record = {
        "schema_version": 1,
        "freeze_status": "AUTHORIZATION_CANDIDATE_REVIEW_ONLY",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_revision_before_candidate_commit": commit,
        "sampling_authorized": False,
        "sampling_performed": False,
        "sealed_test_access": False,
        "purpose": "separately versioned launch-authorization and provenance layer; no scientific protocol changes",
        "original_v2_freeze_sha256": sha256(ORIGINAL_FREEZE_PATH),
        "previous_v2_3_freeze_sha256": sha256(PREVIOUS_CANDIDATE_FREEZE_PATH),
        "previous_v2_3_freeze_status": previous["freeze_status"],
        "scientific_configuration_sha256": sha256(CONFIG_PATH),
        "seed_inventory_sha256": sha256(INVENTORY_PATH),
        "primary_contrast": original["primary_contrast"],
        "approval_binding_fields": [
            "approved_commit_sha", "candidate_freeze_sha256", "original_freeze_sha256",
            "configuration_sha256", "seed_inventory_sha256", "frozen_runner_sha256",
            "authorized_launcher_sha256", "authorization_validator_sha256",
            "candidate_freeze_verifier_sha256", "runtime_environment_sha256",
        ],
        "runtime_provenance": "each authorized run must persist a content-hashed execution identity and owner-approval receipt before the frozen runner is dispatched",
        "sha256": {path: sha256(ROOT / path) for path in sorted(FILES_TO_HASH)},
    }
    payload = json.dumps(record, indent=2, sort_keys=True) + "\n"
    if FREEZE_PATH.exists():
        raise FileExistsError("V2.4 freeze already exists; never overwrite or regenerate it")
    FREEZE_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(FREEZE_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise FileExistsError("V2.4 freeze creation raced; preserve it and inspect") from error
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    print(f"created review-only freeze: {FREEZE_PATH.relative_to(ROOT)}")
    print(json.dumps({
        "freeze_status": record["freeze_status"],
        "sampling_authorized": record["sampling_authorized"],
        "hashes": len(record["sha256"]),
        "candidate_freeze_sha256": sha256(FREEZE_PATH),
    }, indent=2))


if __name__ == "__main__":
    main()

