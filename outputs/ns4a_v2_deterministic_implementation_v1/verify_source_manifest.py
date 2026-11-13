"""Verify the explicit deterministic-package source/dependency hash list."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MANIFEST = HERE / "SOURCE_HASH_MANIFEST.json"


def verify() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if payload.get("manifest_self_hash") != "EXCLUDED":
        raise SystemExit("manifest must explicitly exclude its self-hash")
    files = payload.get("files")
    if not isinstance(files, list) or not files:
        raise SystemExit("manifest file list is empty or malformed")
    seen: set[str] = set()
    for entry in files:
        rel = entry.get("path")
        if not isinstance(rel, str) or rel in seen or rel.replace("\\", "/") == str(MANIFEST.relative_to(ROOT)).replace("\\", "/"):
            raise SystemExit(f"duplicate, invalid, or self-referential manifest entry: {rel!r}")
        seen.add(rel)
        path = (ROOT / rel).resolve()
        if ROOT.resolve() not in path.parents or not path.is_file():
            raise SystemExit(f"missing or out-of-repository manifest file: {rel}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != entry.get("sha256"):
            raise SystemExit(f"SHA-256 mismatch: {rel}")
        if path.stat().st_size != entry.get("bytes"):
            raise SystemExit(f"size mismatch: {rel}")
    print(f"PASS: {len(files)} explicit file hashes verified; manifest self-hash excluded.")


if __name__ == "__main__":
    verify()
