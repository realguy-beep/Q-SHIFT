"""Read-only recheck of V2.4 historical hashes and HOLD authorization flags.

This script reads only the freeze, its listed source/configuration files, and
their Git blobs at the documented base commit. It does not import Stim, sample,
read run directories, or inspect evaluation outcomes.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE_COMMIT = "0ff77c70e38a7e6c2ff547958aee00b0ae5c1fe5"
FREEZE = ROOT / "outputs/strong_fixed_baselines_v2_4/PRETEST_FREEZE_V2_4.json"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str | None:
    return sha256_bytes(path.read_bytes()) if path.is_file() else None


def normalized_text(value: bytes) -> bytes:
    return value.replace(b"\r\n", b"\n")


def audit() -> dict:
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    rows = []
    for relative, expected in freeze.get("sha256", {}).items():
        path = ROOT / relative
        current = sha256_file(path)
        result = subprocess.run(
            ["git", "show", f"{BASE_COMMIT}:{relative}"],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
        base = result.stdout if result.returncode == 0 else None
        current_bytes = path.read_bytes() if path.is_file() else None
        rows.append({
            "path": relative,
            "expected_frozen_sha256": expected,
            "current_sha256": current,
            "base_commit_sha256": sha256_bytes(base) if base is not None else None,
            "matches_expected_frozen_hash": current == expected,
            "matches_base_commit_bytes": current_bytes == base if base is not None else False,
            "matches_base_commit_newline_normalized": (
                normalized_text(current_bytes) == normalized_text(base)
                if current_bytes is not None and base is not None else False
            ),
            "base_blob_available": base is not None,
        })

    flags = {
        "sampling_authorized": freeze.get("sampling_authorized"),
        "sampling_performed": freeze.get("sampling_performed"),
        "sealed_test_access": freeze.get("sealed_test_access"),
    }
    mismatches = [row["path"] for row in rows if not row["matches_expected_frozen_hash"]]
    changed = [row["path"] for row in rows
               if not row["matches_base_commit_newline_normalized"]]
    hold_flags = {
        "sampling_authorized": False,
        "sampling_performed": False,
        "sealed_test_access": False,
    }
    status = "PREEXISTING_EXPECTED_HASH_MISMATCH_HOLD"
    checks_pass = (
        len(rows) == 17
        and len(mismatches) == 13
        and not changed
        and flags == hold_flags
    )
    if not checks_pass:
        status = "AUDIT_CHECK_FAILED_REMAINS_ON_HOLD"
    return {
        "schema_version": 1,
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_commit": BASE_COMMIT,
        "freeze_path": str(FREEZE.relative_to(ROOT)),
        "freeze_sha256": sha256_file(FREEZE),
        "frozen_entries_checked": len(rows),
        "expected_hash_mismatch_count": len(mismatches),
        "expected_hash_mismatches": mismatches,
        "changed_from_base_after_newline_normalization": changed,
        "authorization_flags": flags,
        "status": status,
        "historical_expected_hash_audit_passed": False if mismatches else True,
        "checks_passed_for_documented_historical_state": checks_pass,
        "rows": rows,
        "sampling_performed_by_this_audit": False,
        "protected_outcomes_accessed_by_this_audit": False,
    }


def main() -> None:
    result = audit()
    target = OUT / "V2_4_HOLD_AUDIT.json"
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, indent=2))
    if not result["checks_passed_for_documented_historical_state"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
