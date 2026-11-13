"""Verify the NS-2B engineering allowlist manifest without modifying it."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(__file__).resolve().parent / "NS2B_ENGINEERING_MANIFEST.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    record = json.loads(MANIFEST.read_text(encoding="utf-8"))
    failures = []
    for rel, expected in record["files"].items():
        path = ROOT / rel
        if not path.is_file():
            failures.append(f"MISSING {rel}")
            continue
        actual = sha256(path)
        size = path.stat().st_size
        if actual != expected.get("sha256") or size != expected.get("bytes"):
            failures.append(f"MISMATCH {rel}: sha256={actual}, bytes={size}")
    if failures:
        print("NS-2B manifest verification FAILED")
        print("\n".join(failures))
        return 1
    print(f"NS-2B manifest verification PASS: {len(record['files'])} allowlisted files.")
    print("The manifest excludes itself; it does not establish upstream sample provenance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
