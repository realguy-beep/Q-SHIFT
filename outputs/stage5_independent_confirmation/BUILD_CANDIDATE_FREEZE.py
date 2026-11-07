"""Hash the prospective Stage 5 candidate package; does not generate samples."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FILES = [
    "outputs/stage5_independent_confirmation/STAGE5_PROTOCOL_CANDIDATE.md",
    "outputs/stage5_independent_confirmation/STAGE5_CONFIG.json",
    "outputs/stage5_independent_confirmation/seed_inventory.json",
    "outputs/stage5_independent_confirmation/seed_audit.json",
    "outputs/stage5_independent_confirmation/FROZEN_PROFILE_ESTIMATOR.json",
    "outputs/stage5_independent_confirmation/PROFILE_PROVENANCE.json",
    "outputs/stage5_independent_confirmation/prepare_stage5.py",
    "outputs/stage5_independent_confirmation/BUILD_CANDIDATE_FREEZE.py",
    "outputs/stage5_independent_confirmation/VERIFY_CANDIDATE_FREEZE.py",
    "outputs/stage5_independent_confirmation/README.md",
    "outputs/stage5_independent_confirmation/INDEPENDENT_CANDIDATE_AUDIT.py",
    "outputs/stage5_independent_confirmation/STAGE5_READINESS_REVIEW.md",
    "outputs/stage4c_cnn_noise_estimation_v1/FREEZE.json",
    "outputs/stage4c_cnn_noise_estimation_v1/STAGE4C_AUDIT_RESULTS.json",
]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    hashes = {}
    for rel in FILES:
        path = ROOT / rel
        if not path.is_file():
            raise FileNotFoundError(rel)
        hashes[rel] = sha(path)
    inventory = json.loads((HERE / "seed_inventory.json").read_text(encoding="utf-8"))
    audit = json.loads((HERE / "seed_audit.json").read_text(encoding="utf-8"))
    if inventory["seed_count"] != 1002 or inventory["shot_count"] != 2_250_000:
        raise RuntimeError("candidate allocation does not match the written protocol")
    if audit["status"] != "PASS_RECOVERABLE_DEVELOPMENT_METADATA" or audit["stage5_candidate_collisions"]:
        raise RuntimeError("candidate seed audit did not pass")
    record = {
        "status": "CANDIDATE_PROTOCOL_HASHED_NOT_AUTHORIZED_TO_SAMPLE",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "sampling_started": False,
        "independent_test_accessed": False,
        "unique_shots_planned": inventory["shot_count"],
        "seed_count": inventory["seed_count"],
        "historical_seed_collision_status": audit["status"],
        "files_sha256": hashes,
        "scope_limit": "This is a candidate-plan integrity record, not a complete runner/statistics freeze. A runner and full independent audit implementation remain to be reviewed and frozen before any separately authorized Stage 5 sampling.",
    }
    out = HERE / "STAGE5_CANDIDATE_FREEZE.json"
    out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"freeze": str(out.relative_to(ROOT)), "files": len(hashes),
                      "status": record["status"], "sampling_started": False,
                      "sha256": sha(out)}, indent=2))


if __name__ == "__main__":
    main()
