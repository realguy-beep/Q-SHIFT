"""Create a one-time hash freeze for the v3.4.3 operational repair."""
from __future__ import annotations
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = "8c06750808582137f6a81e2170ad702a552594fb"
HISTORICAL = {
    "stage5_v2": (ROOT / "outputs/stage5_secondary_inference_repair_v1/STAGE5_PRETEST_FREEZE_V2.json", ROOT, 53),
    "stage5_v3_3": (ROOT / "outputs/stage5_execution_safety_v3_3/SAFETY_FREEZE.json", ROOT / "outputs/stage5_execution_safety_v3_3", 13),
    "stage5_v3_4_2": (ROOT / "outputs/stage5_execution_safety_v3_4_2/SAFETY_FREEZE_V4.json", ROOT / "outputs/stage5_execution_safety_v3_4_2", 14),
}
PRE = ROOT / "outputs/stage5_postfailure_forensics_v1/PRE_INVESTIGATION_SHA256.json"
FORENSIC = ROOT / "outputs/stage5_postfailure_forensics_v1/FORENSIC_MANIFEST.json"
FILES = [
    "atomic_safety_v43.py", "recovery_v43.py", "subprocess_fixture_v43.py",
    "test_recovery_v43.py", "run_tests_v43.py", "independent_audit_v43.py",
    "prepare_freeze_v43.py", "V43_SAFETY_CONFIG.json", "PROTOCOL_V43.md", "REPRODUCE_V43.md",
]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def verify_hash_map(path, base, expected_count):
    record = json.loads(path.read_text(encoding="utf-8"))
    rows = record.get("sha256")
    if not isinstance(rows, dict) or len(rows) != expected_count:
        raise RuntimeError(f"historical hash-count mismatch: {path}")
    for rel, expected in rows.items():
        candidate = base / rel
        if not candidate.is_file() or sha(candidate) != expected:
            raise RuntimeError(f"historical frozen hash mismatch: {path.name}/{rel}")
    return len(rows)


def verify_original_evidence():
    snapshot = json.loads(PRE.read_text(encoding="utf-8"))
    if snapshot.get("file_count") != 265 or len(snapshot.get("files", [])) != 265:
        raise RuntimeError("original pre-investigation inventory is not the expected 265 files")
    for item in snapshot["files"]:
        path = ROOT / item["path"]
        if not path.is_file() or path.stat().st_size != item["size_bytes"] or sha(path) != item["sha256"]:
            raise RuntimeError(f"original evidence changed: {item['path']}")
    manifest = json.loads(FORENSIC.read_text(encoding="utf-8"))
    if len(manifest.get("files", {})) != 56:
        raise RuntimeError("forensic manifest entry count mismatch")
    for rel, expected in manifest["files"].items():
        if sha(ROOT / rel) != expected:
            raise RuntimeError(f"forensic evidence hash mismatch: {rel}")
    return {"original_run_inventory_files_verified": 265,
            "forensic_manifest_entries_verified": 56,
            "preinvestigation_inventory_sha256": sha(PRE),
            "forensic_manifest_sha256": sha(FORENSIC)}


def main():
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if head != BASE:
        raise RuntimeError(f"freeze must be created at authorized base {BASE}; current HEAD is {head}")
    historic_counts = {}
    for name, (freeze_path, base, count) in HISTORICAL.items():
        historic_counts[name] = verify_hash_map(freeze_path, base, count)
    evidence = verify_original_evidence()
    superseded_freeze = HERE / "SAFETY_FREEZE_V43_1.json"
    if not superseded_freeze.is_file():
        raise RuntimeError("superseded freeze SAFETY_FREEZE_V43_1.json is missing; refusing to replace history")
    hashes = {}
    for rel in FILES:
        path = HERE / rel
        if not path.is_file():
            raise RuntimeError(f"required v3.4.3 file missing: {rel}")
        hashes[rel] = sha(path)
    record = {
        "revision": "Stage 5 Recovery Safety v3.4.3.2",
        "state": "FROZEN_FOR_BENCHMARK_ONLY_VALIDATION",
        "base_commit": BASE,
        "supersedes": "SAFETY_FREEZE_V43_1.json",
        "superseded_freeze_sha256": sha(superseded_freeze),
        "historical_freezes_verified": historic_counts,
        **evidence,
        "scientific_protocol_changed": False,
        "stage5_recovery_executed": False,
        "stage5_additional_sampling": 0,
        "sealed_outcomes_accessed": False,
        "new_sources_and_configuration_sha256": hashes,
    }
    out = HERE / "SAFETY_FREEZE_V43_2.json"
    out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"freeze": str(out), "source_count": len(hashes),
                      "historical_counts": historic_counts,
                      "original_files_verified": evidence["original_run_inventory_files_verified"],
                      "status": record["state"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
