"""Read-only verification of this engineering manifest and V2.4 freeze hashes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalized_text_hash(data: bytes) -> str:
    """Compare tracked text across Git's LF blobs and Windows CRLF worktrees."""
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def verify() -> dict:
    manifest = json.loads((HERE / "MANIFEST.json").read_text(encoding="utf-8"))
    mismatches = []
    for item in manifest["files"]:
        path = ROOT / item["path"]
        if not path.is_file() or sha256(path) != item["sha256"]:
            mismatches.append(item["path"])
    freeze_path = ROOT / "outputs/strong_fixed_baselines_v2_4/PRETEST_FREEZE_V2_4.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    historical_hash_rows = []
    for relative, expected in freeze.get("sha256", {}).items():
        path = ROOT / relative
        current = sha256(path) if path.is_file() else None
        result = subprocess.run(
            ["git", "show", f"{manifest['base_commit']}:{relative}"],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
        base_hash = hashlib.sha256(result.stdout).hexdigest() if result.returncode == 0 else None
        normalized_equal = (
            path.is_file()
            and result.returncode == 0
            and normalized_text_hash(path.read_bytes()) == normalized_text_hash(result.stdout)
        )
        historical_hash_rows.append({
            "path": relative,
            "expected_frozen_sha256": expected,
            "current_sha256": current,
            "base_commit_sha256": base_hash,
            "matches_frozen_hash": current == expected,
            "normalized_content_unchanged_since_base_commit": normalized_equal,
        })
    frozen_mismatches = [
        row["path"] for row in historical_hash_rows
        if not row["normalized_content_unchanged_since_base_commit"]
    ]
    expected_hash_mismatches = [
        row["path"] for row in historical_hash_rows
        if not row["matches_frozen_hash"]
    ]
    flags = {
        "sampling_authorized": freeze.get("sampling_authorized"),
        "sampling_performed": freeze.get("sampling_performed"),
        "sealed_test_access": freeze.get("sealed_test_access"),
    }
    if flags != {
        "sampling_authorized": False,
        "sampling_performed": False,
        "sealed_test_access": False,
    }:
        frozen_mismatches.append("V2.4 authorization flags are not all false")
    return {
        "engineering_manifest_passed": not mismatches,
        "engineering_mismatches": mismatches,
        "frozen_v2_4_hashes_checked": len(freeze.get("sha256", {})),
        "frozen_v2_4_hash_audit_status": (
            "PASS" if not expected_hash_mismatches else "PRE-EXISTING_HASH_MISMATCH"
        ),
        "frozen_v2_4_expected_hash_mismatch_count": len(expected_hash_mismatches),
        "frozen_v2_4_expected_hash_mismatches": expected_hash_mismatches,
        "frozen_v2_4_changed_since_base_commit": frozen_mismatches,
        "frozen_v2_4_hash_rows": historical_hash_rows,
        "v2_4_authorization_flags": flags,
        "passed": not mismatches and not frozen_mismatches and flags == {
            "sampling_authorized": False,
            "sampling_performed": False,
            "sealed_test_access": False,
        },
    }


def main() -> None:
    result = verify()
    print(json.dumps(result, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
