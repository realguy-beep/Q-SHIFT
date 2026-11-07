"""Hash all lightweight Stage 1 source, reports, and diagnostic metadata."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = HERE / "MANIFEST.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


records = []
for path in sorted(HERE.rglob("*")):
    if not path.is_file() or path == OUT or "__pycache__" in path.parts:
        continue
    records.append({"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size,
                    "sha256": sha256(path)})
payload = {
    "phase": "CNN architecture improvement Stage 1",
    "scope": "development-only architecture preflight; no model training; no independent-test access",
    "file_count": len(records),
    "files": records,
}
OUT.write_bytes((json.dumps(payload, indent=2) + "\n").encode("utf-8"))
print(json.dumps({"manifest": str(OUT.relative_to(ROOT)), "files": len(records)}, indent=2))
