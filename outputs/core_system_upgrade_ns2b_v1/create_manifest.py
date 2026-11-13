"""Create the explicit NS-2B engineering allowlist hash manifest."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
MANIFEST = OUT / "NS2B_ENGINEERING_MANIFEST.json"
ALLOWLIST = (
    "qshift_core_v1/__init__.py",
    "qshift_core_v1/contracts.py",
    "qshift_core_v1/circuit_identity.py",
    "qshift_core_v1/sampling_model_identity.py",
    "dashboard/tests/test_sampling_model_identity_v2.py",
    "outputs/core_system_upgrade_ns2b_v1/NS2B_SAMPLING_MODEL_IDENTITY_DESIGN.md",
    "outputs/core_system_upgrade_ns2b_v1/NS2B_MODEL_INFORMATION_PARITY_POLICY.md",
    "outputs/core_system_upgrade_ns2b_v1/NS2B_MIGRATION_COMPATIBILITY_REPORT.md",
    "outputs/core_system_upgrade_ns2b_v1/NS2B_LIMITATIONS_AND_UNRESOLVED.md",
    "outputs/core_system_upgrade_ns2b_v1/NS2B_IMPLEMENTATION_REPORT.md",
    "outputs/core_system_upgrade_ns2b_v1/NS2B_FAILURE_INVESTIGATION.md",
    "outputs/core_system_upgrade_ns2b_v1/NS2B_CHANGED_FILE_INVENTORY.md",
    "outputs/core_system_upgrade_ns2b_v1/NS2B_REVIEW_PACKAGE_CONTENTS.md",
    "outputs/core_system_upgrade_ns2b_v1/REPRODUCE_NS2B.md",
    "outputs/core_system_upgrade_ns2b_v1/NS2B_FOCUSED_REGRESSION_RESULTS.txt",
    "outputs/core_system_upgrade_ns2b_v1/NS2B_DASHBOARD_COMPATIBILITY_RESULTS.txt",
    "outputs/core_system_upgrade_ns2b_v1/NS2B_BASE_COMPARISON_TEST_RESULTS.txt",
    "outputs/core_system_upgrade_ns2b_v1/NS2B_TEST_RESULTS.txt",
    "outputs/core_system_upgrade_ns2b_v1/NS2B_VALIDATION_RESULTS.json",
    "outputs/core_system_upgrade_ns2b_v1/create_manifest.py",
    "outputs/core_system_upgrade_ns2b_v1/verify_manifest.py",
    "outputs/core_system_upgrade_ns2b_v1/create_review_package.py",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    entries = {}
    for rel in ALLOWLIST:
        path = ROOT / rel
        if not path.is_file():
            raise FileNotFoundError(f"Allowlisted file missing: {rel}")
        entries[rel] = {"sha256": sha256(path), "bytes": path.stat().st_size}
    try:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        head, branch = None, None
    payload = {
        "schema_version": 1,
        "manifest_scope": "explicit NS-2B engineering allowlist; manifest does not hash itself",
        "base_commit": "e015a18e22de653b479cc206026d520e7dc71b5d",
        "observed_head": head,
        "observed_branch": branch,
        "sampling_performed": False,
        "protected_outcomes_accessed": False,
        "files": entries,
    }
    MANIFEST.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {MANIFEST} with {len(entries)} allowlisted files.")


if __name__ == "__main__":
    main()
