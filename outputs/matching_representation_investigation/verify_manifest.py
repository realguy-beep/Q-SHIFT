"""Independently verify the local investigation manifest and exact inventory."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "MANIFEST.json"

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

m = json.loads(MANIFEST.read_text(encoding="utf-8"))
failures = []
for rel, rec in m["files"].items():
    p = HERE / rel
    if not p.is_file():
        failures.append({"path": rel, "reason": "missing"})
        continue
    actual = digest(p)
    if actual != rec["sha256"] or p.stat().st_size != rec["bytes"]:
        failures.append({"path": rel, "reason": "hash_or_size_mismatch", "expected": rec, "actual": {"sha256": actual, "bytes": p.stat().st_size}})
actual_files = {p.relative_to(HERE).as_posix() for p in HERE.rglob("*") if p.is_file() and p != MANIFEST and "__pycache__" not in p.parts and p.suffix != ".pyc"}
missing = sorted(set(m["files"]) - actual_files)
extra = sorted(actual_files - set(m["files"]))
if missing or extra:
    failures.append({"reason": "inventory_mismatch", "missing": missing, "extra": extra})
out = {"status": "PASS" if not failures else "FAIL", "listed_files": len(m["files"]), "actual_files": len(actual_files), "failures": failures}
print(json.dumps(out, indent=2))
if failures:
    raise SystemExit(1)
