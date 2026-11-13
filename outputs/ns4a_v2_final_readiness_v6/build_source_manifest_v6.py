"""Build the non-circular V6 source manifest before commit; never binds HEAD."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "outputs" / "ns4a_v2_integrated_runner_v1"))
from qshift_ns4a_v2_runner.benchmark_identity_v6 import (  # noqa: E402
    SOURCE_BASE_COMMIT,
    V5_MANIFEST_REL,
    V5_MANIFEST_SHA256,
    V6_MANIFEST_REL,
    V6_RECOVERY_RECORD_REL,
    _canonical_source_tree,
    _relpath,
    _manifest_rows,
)

V6_FILES = (
    "outputs/ns4a_v2_final_readiness_v6/STOPPED_ATTEMPT_RECORD_V6.json",
    "outputs/ns4a_v2_final_readiness_v6/RECOVERY_PROTOCOL_V6.md",
    "outputs/ns4a_v2_final_readiness_v6/SOURCE_IDENTITY_BINDING_V6.md",
    "outputs/ns4a_v2_final_readiness_v6/WINDOWS_MEMORY_DIAGNOSTIC_V6.json",
    "outputs/ns4a_v2_final_readiness_v6/MEMORY_GUARD_REPAIR_REPORT_V6.md",
    "outputs/ns4a_v2_final_readiness_v6/build_source_manifest_v6.py",
    "outputs/ns4a_v2_final_readiness_v6/verify_source_manifest_v6.py",
    "outputs/ns4a_v2_final_readiness_v6/diagnose_windows_peak_working_set_v6.py",
    "outputs/ns4a_v2_final_readiness_v6/test_resource_guard_v6.py",
    "outputs/ns4a_v2_final_readiness_v6/test_recovery_identity_v6.py",
    "outputs/ns4a_v2_final_readiness_v6/test_benchmark_v6_protocol.py",
    "outputs/ns4a_v2_final_readiness_v6/run_benchmark_v6.py",
    "outputs/ns4a_v2_integrated_runner_v1/qshift_ns4a_v2_runner/resource_guard_v6.py",
    "outputs/ns4a_v2_integrated_runner_v1/qshift_ns4a_v2_runner/benchmark_identity_v6.py",
    "outputs/ns4a_v2_integrated_runner_v1/qshift_ns4a_v2_runner/benchmark_v6.py",
)


def main() -> int:
    v5_path = _relpath(ROOT, V5_MANIFEST_REL)
    if hashlib.sha256(v5_path.read_bytes()).hexdigest() != V5_MANIFEST_SHA256:
        raise SystemExit("accepted V5 manifest hash mismatch")
    v5 = json.loads(v5_path.read_text(encoding="utf-8"))
    rows = _manifest_rows(v5)
    rows[V5_MANIFEST_REL] = V5_MANIFEST_SHA256
    for rel in V6_FILES:
        path = _relpath(ROOT, rel)
        if not path.is_file():
            raise SystemExit(f"required V6 source file is missing: {rel}")
        rows[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    if V6_MANIFEST_REL in rows:
        raise SystemExit("manifest must not hash itself")
    manifest = {
        "schema": "qshift-ns4a-v2-source-manifest-v6",
        "source_base_commit": SOURCE_BASE_COMMIT,
        "parent_v5_manifest_sha256": V5_MANIFEST_SHA256,
        "commit_binding": "V6 owner authorization source_commit equals exact current Git HEAD",
        "commit_sha_embedded": False,
        "recovery_record_sha256": rows[V6_RECOVERY_RECORD_REL],
        "dependency_lock_path": "outputs/ns4a_v2_lockmatched_env_recovery_v1/requirements-ns3b.lock.txt",
        "dependency_lock_sha256": rows["outputs/ns4a_v2_lockmatched_env_recovery_v1/requirements-ns3b.lock.txt"],
        "protocol_path": "outputs/ns4a_v2_final_readiness_v1/BENCHMARK_PROTOCOL.json",
        "protocol_sha256": rows["outputs/ns4a_v2_final_readiness_v1/BENCHMARK_PROTOCOL.json"],
        "seed_inventory_path": "outputs/ns4a_v2_final_readiness_v1/BENCHMARK_SEED_INVENTORY_V1.json",
        "seed_inventory_sha256": rows["outputs/ns4a_v2_final_readiness_v1/BENCHMARK_SEED_INVENTORY_V1.json"],
        "collision_screen_path": "outputs/ns4a_v2_final_readiness_v1/BENCHMARK_SEED_COLLISION_SCREEN_V1_FINAL.json",
        "collision_screen_sha256": rows["outputs/ns4a_v2_final_readiness_v1/BENCHMARK_SEED_COLLISION_SCREEN_V1_FINAL.json"],
        "v6_files": list(V6_FILES),
        "files": [{"path": path, "sha256": digest} for path, digest in sorted(rows.items())],
        "file_count": len(rows),
        "source_tree_sha256": _canonical_source_tree(rows),
    }
    target = _relpath(ROOT, V6_MANIFEST_REL)
    target.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"manifest_path": V6_MANIFEST_REL,
                      "manifest_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                      "file_count": len(rows),
                      "source_tree_sha256": manifest["source_tree_sha256"],
                      "embedded_final_commit": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
