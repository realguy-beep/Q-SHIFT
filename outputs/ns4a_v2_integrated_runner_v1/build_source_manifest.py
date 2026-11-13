"""Build the allowlisted NS-4A integrated-runner source hash inventory."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


PACKAGE_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_DIR.parents[1]
sys.path.insert(0, str(PACKAGE_DIR))
from qshift_ns4a_v2_runner.integrity import runtime_fingerprint  # noqa: E402


DETERMINISTIC_MODULES = (
    "__init__.py", "audit_saved_arrays.py", "checkpoint.py", "paired_evaluation.py",
    "protocol.py", "sample_schema.py", "sampling_guard.py", "seed_plan.py",
    "selection_rank.py", "selection.py", "statistics.py",
)
DETERMINISTIC_TESTS = (
    "helpers.py", "test_checkpoint_resume.py", "test_paired_and_archive.py",
    "test_protocol_selection.py", "test_selection_rank_seed_guard.py", "test_statistics.py",
)
INTEGRATED_MODULES = (
    "__init__.py", "analysis.py", "archive_store.py", "audit.py",
    "cli.py", "dry_rehearsal.py", "integrity.py", "models.py", "protocol.py",
    "resource_guard.py", "run_state.py", "runner.py",
)
INTEGRATED_TESTS = (
    "test_authorization_resource_and_rehearsal.py", "test_integration_catalog.py",
    "test_state_and_transactions.py",
)
FIXED_FILES = (
    "run_ns4a_v2.py",
    "outputs/qshift_ns4a_pilot_protocol_v2/proposed_config_v2.json",
    "outputs/phase2b_pauli_bias/noise_model.py",
    "outputs/phase3a_correlated_noise_preflight/simulator.py",
    "outputs/ns4a_v2_lockmatched_env_recovery_v1/requirements-ns3b.lock.txt",
    "outputs/ns4a_v2_deterministic_implementation_v1/NS4A_STATISTICAL_ADDENDUM_V1.md",
    "outputs/ns4a_v2_deterministic_implementation_v1/REPRODUCE.md",
    "outputs/ns4a_v2_deterministic_implementation_v1/seed_inventory_template.json",
    "outputs/ns4a_v2_integrated_runner_v1/build_source_manifest.py",
    "outputs/ns4a_v2_integrated_runner_v1/verify_source_manifest.py",
    "qshift_core_v1/contracts.py",
    "qshift_core_v1/controller.py",
    "qshift_core_v1/evaluation.py",
    "qshift_core_v1/pymatching_adapter.py",
    "qshift_core_v1/sampling_model_identity.py",
    "qshift_core_v1/decoder_runtime_v2.py",
    "qshift_core_v1/research_adapters/beliefmatching_adapter_ns3b.py",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    paths = list(FIXED_FILES)
    paths.extend(
        f"outputs/ns4a_v2_deterministic_implementation_v1/qshift_ns4a_v2_deterministic/{name}"
        for name in DETERMINISTIC_MODULES
    )
    paths.extend(
        f"outputs/ns4a_v2_deterministic_implementation_v1/tests/{name}"
        for name in DETERMINISTIC_TESTS
    )
    paths.extend(
        f"outputs/ns4a_v2_integrated_runner_v1/qshift_ns4a_v2_runner/{name}"
        for name in INTEGRATED_MODULES
    )
    paths.extend(
        f"outputs/ns4a_v2_integrated_runner_v1/tests/{name}"
        for name in INTEGRATED_TESTS
    )
    if len(paths) != len(set(paths)):
        raise SystemExit("allowlist contains duplicate paths")
    rows = []
    for relative in sorted(paths):
        target = (REPOSITORY_ROOT / relative).resolve()
        if REPOSITORY_ROOT not in target.parents or not target.is_file():
            raise SystemExit(f"allowlisted source is missing or outside repository: {relative}")
        rows.append({"path": relative.replace("\\", "/"), "sha256": sha256(target)})
    environment = runtime_fingerprint()
    lock_path = REPOSITORY_ROOT / "outputs/ns4a_v2_lockmatched_env_recovery_v1/requirements-ns3b.lock.txt"
    output = {
        "schema": "qshift-ns4a-v2-integrated-source-manifest-v1",
        "purpose": "implementation provenance only; no production seed inventory or sampling authorization",
        "sampling_authorized": False,
        "sampling_performed": False,
        "source_base_commit": "9c70afa992c8b50b976c95eeb86689c428e73965",
        "file_count": len(rows),
        "files": rows,
        "environment": {
            "python": environment["python"],
            "locked_distribution_count": environment["locked_distribution_count"],
            "distributions": environment["distributions"],
            "dependency_lock_sha256": environment["dependency_lock_sha256"],
            "beliefmatching_upstream_commit": environment["beliefmatching_upstream_commit"],
            "beliefmatching_provenance_kind": environment["beliefmatching_provenance_kind"],
            "beliefmatching_core_source_sha256_lf": environment["beliefmatching_core_source_sha256_lf"],
        },
        "manifest_self_hash": "excluded by design",
    }
    manifest_path = PACKAGE_DIR / "SOURCE_HASH_MANIFEST_V2.json"
    encoded = json.dumps(output, sort_keys=True, indent=2, allow_nan=False).encode("utf-8") + b"\n"
    if manifest_path.exists():
        raise SystemExit("manifest already exists; use a new versioned output path rather than overwrite")
    manifest_path.write_bytes(encoded)
    print(json.dumps({"manifest": str(manifest_path), "sha256": hashlib.sha256(encoded).hexdigest(),
                      "files": len(rows)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
