from __future__ import annotations
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    manifest = json.loads((HERE / "MANIFEST.json").read_text(encoding="utf-8"))
    expected = {row["path"]: row for row in manifest["files"]}
    errors = []
    for rel, row in expected.items():
        path = HERE / Path(rel)
        if not path.is_file():
            errors.append(f"missing: {rel}")
        elif path.stat().st_size != row["size_bytes"]:
            errors.append(f"size mismatch: {rel}")
        elif digest(path) != row["sha256"]:
            errors.append(f"hash mismatch: {rel}")
    actual = {p.relative_to(HERE).as_posix() for p in HERE.rglob("*") if p.is_file()
              and p.name != "MANIFEST.json" and "__pycache__" not in p.parts and p.suffix != ".pyc"}
    for rel in sorted(actual - set(expected)):
        errors.append(f"unmanifested: {rel}")
    for rel in sorted(set(expected) - actual):
        errors.append(f"missing from inventory: {rel}")
    if errors:
        raise SystemExit("FAIL: " + "; ".join(errors[:20]))
    print(f"PASS: {len(expected)} files hash and inventory verified")


if __name__ == "__main__":
    main()
