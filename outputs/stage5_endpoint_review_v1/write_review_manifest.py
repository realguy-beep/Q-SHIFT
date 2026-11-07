"""Hash this proposed review without changing frozen Stage 5 evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FILES = [
    "analyze_power.py",
    "verify_review_outputs.py",
    "write_review_manifest.py",
    "ENDPOINT_REVIEW_DECISION.md",
    "PROPOSED_STAGE5_STATISTICAL_AMENDMENT_V1.md",
    "PUSH_READINESS.md",
    "STAGE5_ENDPOINT_COMPARISON.md",
    "POWER_SENSITIVITY.json",
    "../stage5_preexecution_v1/POWER_RECOMPUTATION.json",
    "../stage5_preexecution_v1/STAGE5_V2_FREEZE.json",
]

def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

records = []
for rel in FILES:
    path = (HERE / rel).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    records.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path)})

manifest = {
    "review": "stage5_endpoint_review_v1",
    "classification": "proposed; pending user approval; not a sampling freeze",
    "stage5_sampling_performed": False,
    "sealed_test_accessed": False,
    "historical_stage5_v2_freeze_sha256": next(
        r["sha256"] for r in records if r["path"].endswith("STAGE5_V2_FREEZE.json")
    ),
    "files": records,
    "manifest_self_hash": "omitted by design",
}
(HERE / "REVIEW_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(f"Wrote {HERE / 'REVIEW_MANIFEST.json'} with {len(records)} file hashes")
