"""Build the explicit SHA-256 manifest for this deterministic-only package."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE_COMMIT = "7e99b1495dbec401257d85d0436b4c30f25c310f"
LOCK = "outputs/ns4a_v2_lockmatched_env_recovery_v1/requirements-ns3b.lock.txt"

# Explicit allowlist only. This script never enumerates result or experiment directories.
FILES = (
    "outputs/qshift_ns4a_pilot_protocol_v2/NS4A_PROTOCOL_REVISION_V2.md",
    "outputs/qshift_ns4a_pilot_protocol_v2/proposed_config_v2.json",
    "outputs/qshift_ns4a_pilot_protocol/NS4A_STATISTICAL_DESIGN.md",
    "outputs/ns4a_v2_execution_readiness_v1/SOURCE_AND_DEPENDENCY_MANIFEST.json",
    "outputs/ns4a_v2_lockmatched_env_recovery_v1/requirements-ns3b.lock.txt",
    "outputs/ns4a_v2_lockmatched_env_recovery_v1/DEPENDENCY_VERIFICATION.json",
    "qshift_core_v1/contracts.py",
    "outputs/ns4a_v2_deterministic_implementation_v1/NS4A_STATISTICAL_ADDENDUM_V1.md",
    "outputs/ns4a_v2_deterministic_implementation_v1/UNRESOLVED_BLOCKERS.md",
    "outputs/ns4a_v2_deterministic_implementation_v1/SUPERVISOR_HANDOFF.md",
    "outputs/ns4a_v2_deterministic_implementation_v1/seed_inventory_template.json",
    "outputs/ns4a_v2_deterministic_implementation_v1/REPRODUCE.md",
    "outputs/ns4a_v2_deterministic_implementation_v1/TEST_RESULTS.md",
    "outputs/ns4a_v2_deterministic_implementation_v1/build_source_manifest.py",
    "outputs/ns4a_v2_deterministic_implementation_v1/verify_source_manifest.py",
    "outputs/ns4a_v2_deterministic_implementation_v1/qshift_ns4a_v2_deterministic/__init__.py",
    "outputs/ns4a_v2_deterministic_implementation_v1/qshift_ns4a_v2_deterministic/protocol.py",
    "outputs/ns4a_v2_deterministic_implementation_v1/qshift_ns4a_v2_deterministic/sample_schema.py",
    "outputs/ns4a_v2_deterministic_implementation_v1/qshift_ns4a_v2_deterministic/selection.py",
    "outputs/ns4a_v2_deterministic_implementation_v1/qshift_ns4a_v2_deterministic/selection_rank.py",
    "outputs/ns4a_v2_deterministic_implementation_v1/qshift_ns4a_v2_deterministic/statistics.py",
    "outputs/ns4a_v2_deterministic_implementation_v1/qshift_ns4a_v2_deterministic/paired_evaluation.py",
    "outputs/ns4a_v2_deterministic_implementation_v1/qshift_ns4a_v2_deterministic/seed_plan.py",
    "outputs/ns4a_v2_deterministic_implementation_v1/qshift_ns4a_v2_deterministic/checkpoint.py",
    "outputs/ns4a_v2_deterministic_implementation_v1/qshift_ns4a_v2_deterministic/audit_saved_arrays.py",
    "outputs/ns4a_v2_deterministic_implementation_v1/qshift_ns4a_v2_deterministic/sampling_guard.py",
    "outputs/ns4a_v2_deterministic_implementation_v1/tests/__init__.py",
    "outputs/ns4a_v2_deterministic_implementation_v1/tests/helpers.py",
    "outputs/ns4a_v2_deterministic_implementation_v1/tests/test_protocol_selection.py",
    "outputs/ns4a_v2_deterministic_implementation_v1/tests/test_statistics.py",
    "outputs/ns4a_v2_deterministic_implementation_v1/tests/test_paired_and_archive.py",
    "outputs/ns4a_v2_deterministic_implementation_v1/tests/test_selection_rank_seed_guard.py",
    "outputs/ns4a_v2_deterministic_implementation_v1/tests/test_checkpoint_resume.py",
)


def main() -> None:
    entries = []
    for rel in FILES:
        path = ROOT / rel
        if not path.is_file():
            raise SystemExit(f"allowlisted source missing: {rel}")
        content = path.read_bytes()
        entries.append({"path": rel, "bytes": len(content),
                        "sha256": hashlib.sha256(content).hexdigest()})
    lock = next(entry for entry in entries if entry["path"] == LOCK)
    manifest = {
        "schema": "ns4a-v2-deterministic-only-source-hash-manifest-v1",
        "base_commit": BASE_COMMIT,
        "branch": "codex/ns4a-v2-statistical-implementation",
        "status": "PROSPECTIVE_DETERMINISTIC_ONLY_NOT_FROZEN",
        "sampling_authorized": False,
        "sampling_performed": False,
        "production_seed_allocation": False,
        "sealed_or_stage5_outcomes_accessed": False,
        "synthetic_test_rng_seeds_are_production_seeds": False,
        "manifest_self_hash": "EXCLUDED",
        "dependency_lock": {
            "path": LOCK,
            "sha256": lock["sha256"],
            "upstream_beliefmatching_commit": "4458c278bbec273c8c1a26411dadccc49222f8ef",
            "upstream_beliefmatching_core_sha256": "03229b09559f7059aa6bd7bd6ce80ee1190b41e702f49625ef511074ff42238f",
            "test_environment_versions": {
                "python": "3.12.10", "numpy": "2.2.6", "scipy": "1.18.1",
                "pytest": "9.2.0", "stim": "1.16.0", "pymatching": "2.4.0",
            },
            "note": "Tests use only NumPy, SciPy, and qshift_core_v1 contracts. The pinned lock is preserved; no Stim sampling or PyMatching decoding was invoked.",
        },
        "files": entries,
    }
    out = HERE / "SOURCE_HASH_MANIFEST.json"
    with out.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {out.relative_to(ROOT)} with {len(entries)} explicit file hashes.")


if __name__ == "__main__":
    main()
