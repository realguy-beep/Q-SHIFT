"""Create a new pre-sampling implementation freeze after the V2 preflight blocker."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
ORIGINAL_FREEZE = HERE / "FREEZE.json"
BLOCKED_V2_FREEZE = HERE / "FREEZE_IMPLEMENTATION_V2.json"
NEW_FREEZE = HERE / "FREEZE_IMPLEMENTATION_V3.json"
EXPECTED_ORIGINAL_FREEZE_SHA256 = "045213b7906a06c0e4499f20cc6c5c74a8aa27f4abac1a3e5f9bb572e62dedd6"
MAX_STIM_SEED = 2_147_483_647


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def main() -> None:
    if sha256_file(ORIGINAL_FREEZE) != EXPECTED_ORIGINAL_FREEZE_SHA256:
        raise RuntimeError("Historical original freeze hash mismatch; refusing V3")
    original = json.loads(ORIGINAL_FREEZE.read_text(encoding="utf-8"))
    for row in original["source_and_protocol_files"]:
        path = ROOT / row["path"]
        if not path.is_file() or path.stat().st_size != row["bytes"] or sha256_file(path) != row["sha256"]:
            raise RuntimeError(f"Historical frozen source/config mismatch: {row['path']}")

    if not BLOCKED_V2_FREEZE.is_file():
        raise FileNotFoundError(BLOCKED_V2_FREEZE)
    blocked = json.loads(BLOCKED_V2_FREEZE.read_text(encoding="utf-8"))
    if blocked.get("status") != "FROZEN_IMPLEMENTATION_V2_NOT_EXECUTED":
        raise RuntimeError("V2 record is not the expected pre-sampling implementation freeze")
    if blocked.get("shots_generated") != 0 or blocked.get("training_started") is not False:
        raise RuntimeError("V2 freeze does not record a zero-sample/zero-training state")

    cfg = json.loads((HERE / "stage2_config.json").read_text(encoding="utf-8"))
    inventory = json.loads((HERE / "seed_inventory.json").read_text(encoding="utf-8"))
    audit = json.loads((HERE / "seed_audit.json").read_text(encoding="utf-8"))
    seeds = [int(row["seed"]) for row in inventory["streams"]]
    planned = int(cfg["roots"]["count"]) * int(cfg["conditions_per_root"]) * sum(
        int(value) for value in cfg["shots_per_root_condition"].values())
    if len(seeds) != 95 or len(set(seeds)) != 95 or not all(1 <= x <= MAX_STIM_SEED for x in seeds):
        raise RuntimeError("Frozen seed inventory failed the 95 unique in-range seed check")
    if audit.get("status") != "PASS" or any(audit.get(key) for key in (
            "within_allocation_collisions", "historical_collisions", "phase3a_collisions",
            "stage1_diagnostic_collisions")):
        raise RuntimeError("Frozen historical collision audit no longer passes")
    if planned != 260_000 or planned != int(cfg["total_unique_shot_ceiling"]):
        raise RuntimeError("Frozen shot allocation changed")

    additional = [
        "outputs/cnn_architecture_stage2_v1/FREEZE_IMPLEMENTATION_V2.json",
        "outputs/cnn_architecture_stage2_v1/freeze_stage2_v2.py",
        "outputs/cnn_architecture_stage2_v1/STAGE2_FREEZE_SUPERSESSION.md",
        "outputs/cnn_architecture_stage2_v1/CNN_STAGE2_IMPLEMENTATION_READINESS.md",
        "outputs/cnn_architecture_stage2_v1/STAGE2_FREEZE_SUPERSESSION_V3.md",
        "outputs/cnn_architecture_stage2_v1/CNN_STAGE2_IMPLEMENTATION_READINESS_V3.md",
        "outputs/cnn_architecture_stage2_v1/freeze_stage2_v3.py",
        "outputs/cnn_architecture_stage2_v1/run_stage2.py",
        "outputs/cnn_architecture_stage2_v1/audit_stage2.py",
        "outputs/cnn_architecture_stage2_v1/tests/test_stage2_runner.py",
    ]
    source_paths = [row["path"] for row in original["source_and_protocol_files"]] + additional
    source_records = []
    for rel in source_paths:
        path = ROOT / rel
        if not path.is_file():
            raise FileNotFoundError(f"V3 freeze input missing: {rel}")
        source_records.append({"path": rel, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    superseded = list(original.get("superseded_freeze_sha256s", []))
    superseded.extend([sha256_file(ORIGINAL_FREEZE), sha256_file(BLOCKED_V2_FREEZE)])
    if len(superseded) != 6:
        raise RuntimeError(f"Expected four draft hashes plus original and blocked V2, found {len(superseded)}")
    body = {
        "protocol_version": "1.0-prospective-freeze",
        "implementation_revision": "v3",
        "status": "FROZEN_IMPLEMENTATION_V3_NOT_EXECUTED",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "supersedes_freeze_file_sha256": sha256_file(BLOCKED_V2_FREEZE),
        "historical_original_freeze_sha256": sha256_file(ORIGINAL_FREEZE),
        "prior_superseded_hash_count": 5,
        "superseded_freeze_sha256s": superseded,
        "protocol_id_sha256": hashlib.sha256(canonical_bytes({"files": source_records, "inventory": inventory})).hexdigest(),
        "seed_count": len(seeds),
        "unique_seed_count": len(set(seeds)),
        "seed_collision_audit": audit["status"],
        "planned_unique_shot_ceiling": planned,
        "shots_generated": 0,
        "training_started": False,
        "final_development_data_accessed": False,
        "independent_test_seed_allocated": False,
        "independent_test_accessed": False,
        "source_and_protocol_files": source_records,
    }
    if NEW_FREEZE.exists():
        if json.loads(NEW_FREEZE.read_text(encoding="utf-8")) != body:
            raise RuntimeError("V3 freeze already exists and differs; preserve it and investigate")
    else:
        tmp = NEW_FREEZE.with_suffix(".json.tmp")
        with tmp.open("wb") as f:
            data = (json.dumps(body, indent=2, sort_keys=True) + "\n").encode()
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, NEW_FREEZE)
    print(json.dumps({"freeze": NEW_FREEZE.relative_to(ROOT).as_posix(),
                      "status": body["status"], "protocol_id_sha256": body["protocol_id_sha256"],
                      "original_freeze_sha256": body["historical_original_freeze_sha256"],
                      "superseded_hash_count": len(superseded), "seed_count": len(seeds),
                      "shots_generated": 0, "training_started": False,
                      "files_hashed": len(source_records)}, indent=2))


if __name__ == "__main__":
    main()
