"""Create a SHA-256 inventory of Stage 4C source, summaries, and local raw evidence."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    run = HERE / "run"
    if not (run / "status.json").is_file():
        raise FileNotFoundError("Stage 4C run status missing")
    status = json.loads((run / "status.json").read_text(encoding="utf-8"))
    if status.get("status") != "completed" or status.get("independent_test_accessed") != 0:
        raise RuntimeError("cannot manifest incomplete or seal-violating run")
    summaries = sorted(p for p in HERE.iterdir() if p.is_file() and p.name != "EVIDENCE_MANIFEST.json")
    raw = sorted(p for p in run.rglob("*") if p.is_file())
    all_files = summaries + raw
    records = {p.relative_to(REPO).as_posix(): digest(p) for p in all_files}
    manifest = {
        "status": "COMPLETED_DEVELOPMENT_EVIDENCE",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "freeze_sha256": digest(HERE / "FREEZE.json"),
        "audit_status": json.loads((HERE / "STAGE4C_AUDIT_RESULTS.json").read_text(encoding="utf-8"))["status"],
        "independent_test_accessed": False,
        "total_unique_shots": status["completed_shots"],
        "completed_evaluation_roots": status["completed_jobs"],
        "tracked_lightweight_and_local_evidence_file_count": len(records),
        "raw_evidence_files_local_ignored": [p.relative_to(REPO).as_posix() for p in raw],
        "files_sha256": records,
        "exclusions": ["No independent-test paths or artifacts were enumerated or read.",
                       "All Stage 4B and earlier outputs are outside this manifest's Stage 4C scope."]
    }
    out = HERE / "EVIDENCE_MANIFEST.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(out.relative_to(REPO)), "files": len(records),
                      "raw_files_local": len(raw), "sha256": digest(out)}, indent=2))


if __name__ == "__main__":
    main()
