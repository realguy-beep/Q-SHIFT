"""Create a lightweight hash manifest; raw benchmark NPZ arrays stay local."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RAW_DIR = HERE / "benchmark_run/roots"

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()

files = []
for path in sorted(HERE.rglob("*")):
    if not path.is_file() or path.name == "VALIDATION_MANIFEST.json":
        continue
    rel = path.relative_to(HERE)
    if "__pycache__" in rel.parts or path.suffix in {".pyc", ".tmp"}:
        continue
    if rel.parts[:2] == ("benchmark_run", "roots") and path.suffix == ".npz":
        continue
    files.append({"path": path.relative_to(ROOT).as_posix(), "size_bytes": path.stat().st_size, "sha256": sha(path)})
raw_archives = sorted(RAW_DIR.glob("root_p*.npz"))
historical = [
    ROOT / "outputs/stage5_preexecution_v1/STAGE5_V2_FREEZE.json",
    ROOT / "outputs/stage5_preexecution_v1/FROZEN_PROFILE_ESTIMATOR.json",
    ROOT / "outputs/stage4c_cnn_noise_estimation_v1/FREEZE.json",
]
manifest = {
    "study": "Stage 5 Endpoint B design validation v1",
    "stage5_sampling": False,
    "sealed_test_access": False,
    "disposable_benchmark_raw_archives": {"count": len(raw_archives), "included_in_git_manifest": False,
        "bytes": sum(p.stat().st_size for p in raw_archives),
        "hash_manifest": "benchmark_run/ROOT_ARCHIVE_MANIFEST.json"},
    "historical_hashes_checked": [{"path": p.relative_to(ROOT).as_posix(), "sha256": sha(p)} for p in historical],
    "lightweight_review_and_result_files": files,
    "manifest_self_hash": "omitted by design",
}
(HERE / "VALIDATION_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(f"Wrote manifest for {len(files)} lightweight files; {len(raw_archives)} raw NPZ archives excluded")
