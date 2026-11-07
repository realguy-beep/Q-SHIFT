"""Verify the delivered Phase 2B directory against SHA256_MANIFEST.json."""
import hashlib
import json
from pathlib import Path

P = Path(__file__).resolve().parent
m = json.loads((P / "SHA256_MANIFEST.json").read_text(encoding="utf-8"))
bad = []
for rel, rec in m["files"].items():
    path = P / rel
    if not path.is_file():
        bad.append({"file": rel, "reason": "missing"})
        continue
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != rec["sha256"] or path.stat().st_size != rec["bytes"]:
        bad.append({"file": rel, "expected": rec["sha256"], "actual": actual,
                    "expected_bytes": rec["bytes"], "actual_bytes": path.stat().st_size})
actual_files = {p.relative_to(P).as_posix() for p in P.rglob("*") if p.is_file()
                and p != P / "SHA256_MANIFEST.json" and "__pycache__" not in p.parts and p.suffix != ".pyc"}
extra = sorted(actual_files - set(m["files"]))
missing = sorted(set(m["files"]) - actual_files)
if bad or extra or missing:
    raise SystemExit(json.dumps({"hash_or_size_failures": bad, "extra_files": extra, "missing_files": missing}, indent=2))
print(f"PASS: {m['file_count']} manifested files; raw heldout bundles={m['evidence_counts']['heldout_npz']}; no hash, size, or inventory mismatches")
