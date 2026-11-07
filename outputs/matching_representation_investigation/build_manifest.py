"""Build a deterministic SHA-256 inventory for this investigation only."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "MANIFEST.json"

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

files = {}
for path in sorted(HERE.rglob("*")):
    if not path.is_file() or path == MANIFEST or "__pycache__" in path.parts or path.suffix == ".pyc":
        continue
    rel = path.relative_to(HERE).as_posix()
    files[rel] = {"sha256": digest(path), "bytes": path.stat().st_size}

phase0 = json.loads((HERE / "PHASE0_VERIFICATION.json").read_text(encoding="utf-8"))
phase0_summary = phase0["summary"]
manifest = {
    "scope": "outputs/matching_representation_investigation; manifest excludes itself",
    "file_count": len(files),
    "files": files,
    "historical_audit": {
        "decision": phase0_summary["decision"],
        "direct_manifest_file_checks": phase0_summary["direct_manifest_file_checks"],
        "direct_manifest_failures": phase0_summary["direct_manifest_failures"],
        "phase2b_inventory_exact": phase0_summary["phase2b_inventory_exact"],
        "phase2b_unmanifested_duplicate_identical_to_config": phase0_summary["phase2b_unmanifested_duplicate_identical_to_config"],
        "dem_gate_missing_expected_hashes": phase0_summary["dem_gate_missing_expected_hashes"],
    },
    "experiment_scope": {
        "new_stochastic_phase2b_shots": 0,
        "phase2b_full_test_labels_read": False,
        "independent_exact_rescoring_failures": json.loads((HERE / "INDEPENDENT_AUDIT.json").read_text(encoding="utf-8"))["failures"],
    },
}
MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"manifest": str(MANIFEST), "file_count": len(files), "decision": phase0_summary["decision"]}, indent=2))
