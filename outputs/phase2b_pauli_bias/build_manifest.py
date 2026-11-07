"""Create a SHA-256 and size manifest for delivered Phase 2B evidence."""
import hashlib
import json
from pathlib import Path

P = Path(__file__).resolve().parent
target = P / "SHA256_MANIFEST.json"
files = {}
counts = {"development_validation_npz": 0, "calibration_npz": 0, "heldout_npz": 0,
          "dem_text": 0, "circuit_text": 0}
for path in sorted(P.rglob("*")):
    if not path.is_file() or path == target or "__pycache__" in path.parts or path.suffix == ".pyc":
        continue
    rel = path.relative_to(P).as_posix()
    files[rel] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}
    if rel.startswith("data/development_validation/") and rel.endswith(".npz"):
        counts["development_validation_npz"] += 1
    elif rel.startswith("data/calibration/") and rel.endswith(".npz"):
        counts["calibration_npz"] += 1
    elif rel.startswith("data/heldout/") and rel.endswith(".npz"):
        counts["heldout_npz"] += 1
    elif rel.startswith("dems/") and rel.endswith(".dem"):
        counts["dem_text"] += 1
    elif rel.startswith("dems/") and rel.endswith(".stim"):
        counts["circuit_text"] += 1
manifest = {
    "study": "Q-SHIFT Phase 2B Pauli-biased decoder specialization",
    "manifest_scope": "All delivered files below this directory except this manifest and Python cache files.",
    "file_count": len(files), "evidence_counts": counts,
    "heldout_shots": 1_200_000, "files": files,
}
target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(f"Wrote {target.name}: {len(files)} files; {counts['heldout_npz']} heldout roots")
