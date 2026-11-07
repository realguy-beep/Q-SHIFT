"""Hash this candidate-phase bundle and the immutable input evidence it references."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def record(path: Path, relative_to: Path) -> dict:
    data = path.read_bytes()
    return {
        "path": str(path.relative_to(relative_to)).replace("\\", "/"),
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


files = []
for path in sorted(HERE.rglob("*")):
    if not path.is_file() or path.name == "MANIFEST.json" or "__pycache__" in path.parts or path.suffix == ".pyc":
        continue
    files.append(record(path, HERE))

inputs = [
    REPO / "outputs" / "conditional_go_resolution" / "DEVELOPMENT_RAW_EVIDENCE.npz",
    REPO / "outputs" / "conditional_go_resolution" / "UTILITY_PER_ROOT.csv",
    REPO / "outputs" / "conditional_go_resolution" / "INDEPENDENT_VERIFICATION.json",
]
input_records = [record(path, REPO) for path in inputs]
manifest = {
    "created_utc": datetime.now(timezone.utc).isoformat(),
    "scope": "outputs/competition_pivot",
    "manifest_excludes_itself": True,
    "historical_outputs_modified": False,
    "input_evidence_references": input_records,
    "files": files,
}
(HERE / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(f"wrote MANIFEST.json for {len(files)} bundle files and {len(input_records)} input references")
