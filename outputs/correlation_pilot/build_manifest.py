"""Build a post-run integrity manifest without changing frozen experiment inputs."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MANIFEST = HERE / "MANIFEST.json"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    freeze_path = HERE / "PRETEST_FREEZE.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    frozen_dependencies = []
    for rel, expected in freeze["sha256"].items():
        path = ROOT / rel
        actual = digest(path) if path.is_file() else None
        frozen_dependencies.append({"path_from_project_root": rel, "expected_sha256": expected,
                                    "actual_sha256": actual, "matches": actual == expected})
    mismatches = [x["path_from_project_root"] for x in frozen_dependencies if not x["matches"]]
    files = []
    for path in sorted(HERE.rglob("*")):
        if not path.is_file() or path == MANIFEST or "__pycache__" in path.parts:
            continue
        if path.name.endswith(".tmp"):
            continue
        files.append({"path": path.relative_to(HERE).as_posix(),
                      "size_bytes": path.stat().st_size, "sha256": digest(path)})
    data = {
        "manifest_type": "post_run_evidence_integrity_manifest",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "study_status": "development_feasibility_only",
        "pretest_freeze_status": freeze.get("status"),
        "frozen_inputs_rechecked": len(frozen_dependencies),
        "frozen_input_mismatches": mismatches,
        "frozen_dependencies": frozen_dependencies,
        "file_count_excluding_manifest_and_pycache": len(files),
        "total_bytes_excluding_manifest_and_pycache": sum(x["size_bytes"] for x in files),
        "files": files,
        "manifest_self_hash": "excluded by definition; all other files in this directory are hashed",
        "scope_note": "This manifest records file integrity after execution; it does not establish availability of unrecorded historical RNG use, exactness of approximate DEMs, hardware validity, or confirmatory status."
    }
    tmp = MANIFEST.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(MANIFEST)
    print(json.dumps({"status": "PASS" if not mismatches else "FAIL",
                      "files": len(files), "frozen_dependencies": len(frozen_dependencies),
                      "mismatches": mismatches,
                      "total_bytes": data["total_bytes_excluding_manifest_and_pycache"]}, indent=2))
    if mismatches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
