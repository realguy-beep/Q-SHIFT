from __future__ import annotations
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "MANIFEST.json"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    rows = []
    for path in sorted(HERE.rglob("*")):
        if not path.is_file() or path == MANIFEST or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        rows.append({"path": path.relative_to(HERE).as_posix(), "size_bytes": path.stat().st_size,
                     "sha256": digest(path)})
    data = {"manifest_scope": "all Phase 2C deliverables and evidence files; excludes MANIFEST.json itself and Python cache files",
            "files_count": len(rows), "files": rows}
    MANIFEST.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {MANIFEST.name}: {len(rows)} files")


if __name__ == "__main__":
    main()
