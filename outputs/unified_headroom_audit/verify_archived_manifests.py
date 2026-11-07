"""Read-only verification of checksum entries in archived JSON manifests.

Run from the repository root. The verifier never writes to an archived study;
it reports hash/size matches, mismatches, missing paths, and manifest coverage.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path.cwd().resolve()
OUT = ROOT / "outputs" / "unified_headroom_audit"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def file_records(obj: Any, where: str = "$"):
    """Yield dict records that bind a file path to a SHA-256 digest."""
    if isinstance(obj, dict):
        path_key = next((k for k in ("path", "file", "name") if isinstance(obj.get(k), str)), None)
        digest_key = next((k for k in ("sha256", "expected_sha256")
                           if isinstance(obj.get(k), str) and len(obj[k]) == 64), None)
        if path_key and digest_key:
            yield where, obj[path_key], obj[digest_key], obj.get("bytes", obj.get("size_bytes"))
        for k, v in obj.items():
            # Older manifests store {relative_filename: {sha256, bytes}} or
            # {relative_filename: sha256} instead of a list of path records.
            if isinstance(v, dict) and isinstance(v.get("sha256"), str) and len(v["sha256"]) == 64:
                if any(t in k for t in (".", "/", "\\")):
                    yield f"{where}.{k}", k, v["sha256"], v.get("bytes", v.get("size_bytes"))
            elif isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdefABCDEF" for c in v):
                if any(t in k for t in (".", "/", "\\")):
                    yield f"{where}.{k}", k, v, None
            yield from file_records(v, f"{where}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from file_records(v, f"{where}[{i}]")


def resolve_record(manifest: Path, raw: str) -> Path | None:
    s = raw.strip().replace("\\", os.sep).replace("/", os.sep)
    p = Path(s)
    candidates = [p] if p.is_absolute() else [manifest.parent / p,
                                               manifest.parent / "raw_data" / p,
                                               manifest.parent / "raw" / p,
                                               ROOT / p, ROOT / "outputs" / p]
    seen = set()
    for q in candidates:
        try:
            resolved = q.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.is_file():
            return resolved
    # Some historical manifests record only a basename while storing files in
    # a nested folder. Accept a unique match under the manifest's directory.
    if not p.is_absolute() and p.name:
        matches = list(manifest.parent.rglob(p.name))
        matches = [m.resolve() for m in matches if m.is_file()]
        unique = sorted(set(matches))
        if len(unique) == 1:
            return unique[0]
    return None


def main() -> int:
    manifests = sorted(p for p in (ROOT / "outputs").rglob("*.json")
                       if "manifest" in p.name.lower() and OUT not in p.parents)
    rows = []
    for mp in manifests:
        try:
            data = json.loads(mp.read_text(encoding="utf-8"))
        except Exception as e:
            rows.append({"manifest": mp.relative_to(ROOT).as_posix(), "status": "INVALID_JSON",
                         "error": repr(e), "entries": []})
            continue
        entries = []
        for where, raw, expected, size in file_records(data):
            path = resolve_record(mp, raw)
            if path is None:
                entries.append({"record": where, "path": raw, "expected_sha256": expected,
                                "status": "MISSING", "expected_size": size})
                continue
            actual = sha256(path)
            actual_size = path.stat().st_size
            hash_ok = actual.lower() == expected.lower()
            size_ok = size is None or int(size) == actual_size
            entries.append({"record": where, "path": raw,
                            "resolved_path": path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path),
                            "expected_sha256": expected, "actual_sha256": actual,
                            "hash_match": hash_ok, "expected_size": size,
                            "actual_size": actual_size, "size_match": size_ok,
                            "status": "PASS" if hash_ok and size_ok else "MISMATCH"})
        statuses = [e["status"] for e in entries]
        if not entries:
            status = "NO_CHECKSUM_ENTRIES"
        elif all(s == "PASS" for s in statuses):
            status = "PASS"
        elif any(s == "MISMATCH" for s in statuses):
            status = "MISMATCH"
        elif any(s == "MISSING" for s in statuses):
            status = "INCOMPLETE_MISSING"
        else:
            status = "REVIEW"
        rows.append({"manifest": mp.relative_to(ROOT).as_posix(), "status": status,
                     "checksum_entries": len(entries),
                     "passed": sum(e["status"] == "PASS" for e in entries),
                     "mismatched": sum(e["status"] == "MISMATCH" for e in entries),
                     "missing": sum(e["status"] == "MISSING" for e in entries),
                     "entries": entries})
    result = {"scope": "all JSON files with 'manifest' in filename under outputs",
              "read_only": True, "manifest_count": len(rows), "results": rows}
    out_json = OUT / "MANIFEST_VERIFICATION.json"
    out_json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    lines = ["# Archived manifest verification", "",
             f"Scanned {len(rows)} JSON manifest files under `outputs/`. The check is read-only. "
             "A file is PASS only when both its recorded SHA-256 and (if present) byte size match.", "",
             "| Manifest | Status | Entries | Pass | Mismatch | Missing |", "|---|---:|---:|---:|---:|---:|"]
    for row in rows:
        lines.append(f"| `{row['manifest']}` | {row['status']} | {row.get('checksum_entries', 0)} | "
                     f"{row.get('passed', 0)} | {row.get('mismatched', 0)} | {row.get('missing', 0)} |")
    lines += ["", "## Non-passing entries", ""]
    found = False
    for row in rows:
        for e in row.get("entries", []):
            if e["status"] != "PASS":
                found = True
                lines.append(f"- `{row['manifest']}` — `{e['path']}` ({e['status']}); "
                             f"record at `{e['record']}`; expected SHA-256 `{e.get('expected_sha256')}`, "
                             f"actual `{e.get('actual_sha256', 'unavailable')}`.")
    if not found:
        lines.append("None.")
    (OUT / "MANIFEST_VERIFICATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"manifest_count": len(rows),
                      "statuses": {s: sum(r["status"] == s for r in rows)
                                   for s in sorted(set(r["status"] for r in rows))},
                      "entries": sum(r.get("checksum_entries", 0) for r in rows),
                      "mismatches": sum(r.get("mismatched", 0) for r in rows),
                      "missing": sum(r.get("missing", 0) for r in rows),
                      "report": str(out_json)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
