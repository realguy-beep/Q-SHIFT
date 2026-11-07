"""Build a SHA-256 manifest of the delivered Phase 2A directory."""
import hashlib
import json
from pathlib import Path

P = Path(__file__).resolve().parent
target = P / "PHASE2A_MANIFEST.json"
records = {}
for path in sorted(P.rglob("*")):
    if not path.is_file() or path == target or "__pycache__" in path.parts:
        continue
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    records[path.relative_to(P).as_posix()] = {"sha256": digest, "bytes": path.stat().st_size}
manifest = {
    "study": "Q-SHIFT Phase 2A",
    "manifest_scope": "All delivered files under this directory except this manifest and Python cache files.",
    "file_count": len(records),
    "raw_root_bundle_count": sum(name.startswith("data/") and name.endswith(".npz") for name in records),
    "raw_test_shots": 600000,
    "files": records,
}
target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(f"Manifest written: {len(records)} files; {manifest['raw_root_bundle_count']} NPZ bundles")
