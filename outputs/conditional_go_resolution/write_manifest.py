"""Write a SHA-256 inventory for this feasibility directory (excluding itself)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
records = []
for path in sorted(ROOT.rglob("*")):
    if not path.is_file() or path.name == "MANIFEST.json" or "__pycache__" in path.parts or path.suffix == ".pyc":
        continue
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    records.append({
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "size_bytes": path.stat().st_size,
        "sha256": h.hexdigest(),
    })
manifest = {
    "created_utc": datetime.now(timezone.utc).isoformat(),
    "scope": "outputs/conditional_go_resolution",
    "manifest_excludes_itself": True,
    "files": records,
}
(ROOT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(f"wrote MANIFEST.json for {len(records)} files")
