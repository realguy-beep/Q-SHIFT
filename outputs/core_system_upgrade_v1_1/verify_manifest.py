"""Read-only v1.1 manifest and expected historical HOLD-state verification."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify() -> dict:
    manifest = json.loads((HERE / "MANIFEST.json").read_text(encoding="utf-8"))
    mismatches = []
    for item in manifest["files"]:
        path = ROOT / item["path"]
        if not path.is_file() or sha256(path) != item["sha256"]:
            mismatches.append(item["path"])
    hold_audit = json.loads((HERE / "V2_4_HOLD_AUDIT.json").read_text(encoding="utf-8"))
    expected_hold = (
        hold_audit.get("frozen_entries_checked") == 17
        and hold_audit.get("expected_hash_mismatch_count") == 13
        and hold_audit.get("changed_from_base_after_newline_normalization") == []
        and hold_audit.get("authorization_flags") == {
            "sampling_authorized": False,
            "sampling_performed": False,
            "sealed_test_access": False,
        }
        and hold_audit.get("checks_passed_for_documented_historical_state") is True
        and hold_audit.get("sampling_performed_by_this_audit") is False
        and hold_audit.get("protected_outcomes_accessed_by_this_audit") is False
    )
    return {
        "v1_1_manifest_passed": not mismatches,
        "v1_1_manifest_mismatches": mismatches,
        "historical_v2_4_expected_hash_audit": hold_audit.get("status"),
        "v2_4_expected_hash_mismatches": hold_audit.get("expected_hash_mismatch_count"),
        "v2_4_historical_hold_state_verified": expected_hold,
        "sampling_performed": False,
        "protected_outcomes_accessed": False,
        "passed": not mismatches and expected_hold,
    }


def main() -> None:
    result = verify()
    print(json.dumps(result, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
