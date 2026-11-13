"""Build the noncircular NS-4A V2 V5 source-identity manifest."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "outputs/ns4a_v2_integrated_runner_v1"))
from qshift_ns4a_v2_runner.benchmark_identity_v5 import (  # noqa: E402
    SOURCE_BASE_COMMIT,
    V4_MANIFEST_REL,
    V4_MANIFEST_SHA256,
    V5_ADDITIONAL_PATHS,
    _inside,
    sha256_file,
    source_tree_digest,
)

MANIFEST_REL = "outputs/ns4a_v2_final_readiness_v5/SOURCE_HASH_MANIFEST_V5.json"


def main() -> int:
    v4_path = _inside(ROOT, V4_MANIFEST_REL)
    if sha256_file(v4_path) != V4_MANIFEST_SHA256:
        raise SystemExit("historical V4 manifest hash mismatch; V5 build stopped")
    v4 = json.loads(v4_path.read_text(encoding="utf-8"))
    rows = {row["path"]: row["sha256"] for row in v4["files"]}
    for rel in sorted(V5_ADDITIONAL_PATHS):
        target = _inside(ROOT, rel)
        if not target.is_file():
            raise SystemExit(f"required V5 source/evidence file is missing: {rel}")
        rows[rel] = sha256_file(target)
    file_rows = [{"path": p, "sha256": rows[p]} for p in sorted(rows)]
    payload = {
        "schema": "qshift-ns4a-v2-source-manifest-v5",
        "readiness_revision": "NS-4A V2 exact source identity V5",
        "source_base_commit": SOURCE_BASE_COMMIT,
        "parent_v4_manifest_sha256": V4_MANIFEST_SHA256,
        "manifest_self_reference_excluded": True,
        "final_commit_sha": None,
        "commit_binding": "owner authorization source_commit must equal exact current Git HEAD",
        "file_count": len(file_rows),
        "files": file_rows,
        "source_tree_sha256": source_tree_digest(rows),
        "dependency_lock_path": "outputs/ns4a_v2_lockmatched_env_recovery_v1/requirements-ns3b.lock.txt",
        "dependency_lock_sha256": rows["outputs/ns4a_v2_lockmatched_env_recovery_v1/requirements-ns3b.lock.txt"],
        "untracked_policy": {
            "approved_seed_inventory_and_collision_evidence": "tracked and included in files",
            "only_pre_run_untracked_path": "outputs/ns4a_v2_final_readiness_v5/BENCHMARK_OWNER_APPROVAL_V5.json",
            "authorization_file": "validated by exact schema and hash bindings; excluded from source file set",
            "unexpected_untracked_or_any_tracked_changes": "reject",
            "benchmark_output_directory_must_be_absent_before_start": True,
        },
        "sampling_authorized": False,
        "sampling_performed": False,
        "numeric_production_seeds_allocated": False,
        "benchmark_seed_values_allocated": True,
    }
    out = _inside(ROOT, MANIFEST_REL)
    out.write_bytes(json.dumps(payload, sort_keys=True, indent=2, allow_nan=False).encode("utf-8") + b"\n")
    print(json.dumps({"status": "BUILT", "manifest_path": MANIFEST_REL,
                      "manifest_sha256": sha256_file(out), "verified_file_count": len(file_rows),
                      "source_tree_sha256": payload["source_tree_sha256"],
                      "sampling_performed": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
