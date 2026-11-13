"""Create an explicit V3 implementation/input manifest; never overwrite V2."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

PACKAGE_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_DIR.parents[1]
BASE_MANIFEST = REPOSITORY_ROOT / "outputs/ns4a_v2_integrated_runner_v1/SOURCE_HASH_MANIFEST_V2.json"
OUTPUT = PACKAGE_DIR / "SOURCE_HASH_MANIFEST_V3.json"
EXPECTED_V2_MANIFEST_SHA256 = "897ba2e57622be52c93c2a73859ef087688aea3472f86c7feb42b91a4c1e7f49"
ADDITIONAL_PATHS = (
    "outputs/ns4a_v2_integrated_runner_v1/qshift_ns4a_v2_runner/benchmark.py",
    "outputs/ns4a_v2_integrated_runner_v1/tests/test_benchmark_readiness.py",
    "outputs/ns4a_v2_final_readiness_v1/BENCHMARK_PROTOCOL.json",
    "outputs/ns4a_v2_final_readiness_v1/BENCHMARK_SEED_INVENTORY_TEMPLATE.json",
    "outputs/ns4a_v2_final_readiness_v1/CANDIDATE_EXECUTION_MANIFEST_SCHEMA_V1.json",
    "outputs/ns4a_v2_final_readiness_v1/DETERMINISTIC_REHEARSAL_VALIDATION.json",
    "outputs/ns4a_v2_final_readiness_v1/SEED_AND_COLLISION_SCREENING.md",
    "outputs/ns4a_v2_final_readiness_v1/build_source_manifest_v3.py",
    "outputs/ns4a_v2_final_readiness_v1/verify_source_manifest_v3.py",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("V3 manifest already exists; do not overwrite evidence; create a new version instead")
    try:
        base = json.loads(BASE_MANIFEST.read_text(encoding="utf-8"))
        base_hash = sha256(BASE_MANIFEST)
    except Exception as exc:
        raise SystemExit(f"historical V2 manifest is unavailable: {exc}")
    if base_hash != EXPECTED_V2_MANIFEST_SHA256:
        raise SystemExit("historical V2 manifest differs from the verified PR #10 base; refusing to derive V3")
    if base.get("schema") != "qshift-ns4a-v2-integrated-source-manifest-v1" or not isinstance(base.get("files"), list):
        raise SystemExit("historical V2 source manifest schema is unsupported")
    paths = {row["path"] for row in base["files"] if isinstance(row, dict) and isinstance(row.get("path"), str)}
    if len(paths) != len(base["files"]):
        raise SystemExit("historical V2 manifest paths are malformed or duplicated")
    paths.update(ADDITIONAL_PATHS)
    if len(paths) != len(set(paths)):
        raise SystemExit("V3 source allowlist contains duplicates")
    rows = []
    for relative in sorted(paths):
        target = (REPOSITORY_ROOT / relative).resolve()
        if REPOSITORY_ROOT not in target.parents or not target.is_file():
            raise SystemExit(f"V3 allowlisted file missing or outside repository: {relative}")
        rows.append({"path": relative.replace("\\", "/"), "sha256": sha256(target)})

    sys.path.insert(0, str(REPOSITORY_ROOT / "outputs/ns4a_v2_integrated_runner_v1"))
    from qshift_ns4a_v2_runner.integrity import runtime_fingerprint

    payload = {
        # The production integrity verifier accepts this stable v1 envelope;
        # the readiness revision remains a separate descriptive field.
        "schema": "qshift-ns4a-v2-source-manifest-v1",
        "readiness_revision": "NS-4A V2 final-readiness V3",
        "purpose": "versioned implementation, benchmark protocol, and deterministic validation provenance only",
        "source_base_commit": "79ac849dc0295cfd702c3e53f131e30f1e306425",
        "supersedes_source_manifest_v2_sha256": base_hash,
        "file_count": len(rows),
        "files": rows,
        "environment": runtime_fingerprint(),
        "sampling_authorized": False,
        "sampling_performed": False,
        "numeric_production_seeds_allocated": False,
        "benchmark_seed_values_allocated": False,
        "manifest_self_hash": "excluded by design",
        "final_readiness_report": "excluded by design; report records this manifest digest after construction",
    }
    encoded = json.dumps(payload, sort_keys=True, indent=2, allow_nan=False).encode("utf-8") + b"\n"
    OUTPUT.write_bytes(encoded)
    print(json.dumps({"status": "PASS", "path": str(OUTPUT), "sha256": hashlib.sha256(encoded).hexdigest(),
                      "verified_input_files": len(rows), "sampling_performed": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
