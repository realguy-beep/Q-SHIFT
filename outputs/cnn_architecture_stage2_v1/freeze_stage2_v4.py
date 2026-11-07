"""Create a superseding V4 pre-sampling freeze; never rewrite prior freezes."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
ORIGINAL = HERE / "FREEZE.json"
V2 = HERE / "FREEZE_IMPLEMENTATION_V2.json"
V3 = HERE / "FREEZE_IMPLEMENTATION_V3.json"
NEW = HERE / "FREEZE_IMPLEMENTATION_V4.json"
EXPECTED_ORIGINAL_SHA = "045213b7906a06c0e4499f20cc6c5c74a8aa27f4abac1a3e5f9bb572e62dedd6"
MAX_STIM_SEED = 2_147_483_647


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    if sha(ORIGINAL) != EXPECTED_ORIGINAL_SHA:
        raise RuntimeError("Historical original freeze hash mismatch")
    original = json.loads(ORIGINAL.read_text(encoding="utf-8"))
    for row in original["source_and_protocol_files"]:
        path = ROOT / row["path"]
        if not path.is_file() or path.stat().st_size != row["bytes"] or sha(path) != row["sha256"]:
            raise RuntimeError(f"Original frozen input mismatch: {row['path']}")
    prior_files = []
    for path in (V2, V3):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("shots_generated") != 0 or data.get("training_started") is not False:
            raise RuntimeError(f"{path.name} does not record a zero-sample, zero-training preflight")
        prior_files.append(path)

    cfg = json.loads((HERE / "stage2_config.json").read_text(encoding="utf-8"))
    inventory = json.loads((HERE / "seed_inventory.json").read_text(encoding="utf-8"))
    seed_audit = json.loads((HERE / "seed_audit.json").read_text(encoding="utf-8"))
    seeds = [int(row["seed"]) for row in inventory["streams"]]
    planned = int(cfg["roots"]["count"]) * int(cfg["conditions_per_root"]) * sum(
        int(value) for value in cfg["shots_per_root_condition"].values())
    if len(seeds) != 95 or len(set(seeds)) != 95 or not all(1 <= x <= MAX_STIM_SEED for x in seeds):
        raise RuntimeError("Frozen seed allocation must remain 95 unique supported Stim seeds")
    if seed_audit.get("status") != "PASS" or any(seed_audit.get(key) for key in (
            "within_allocation_collisions", "historical_collisions", "phase3a_collisions",
            "stage1_diagnostic_collisions")):
        raise RuntimeError("Frozen seed collision audit failed")
    if planned != 260000 or planned != int(cfg["total_unique_shot_ceiling"]):
        raise RuntimeError("Frozen scientific shot allocation changed")

    additional = [
        "outputs/cnn_architecture_stage2_v1/FREEZE_IMPLEMENTATION_V2.json",
        "outputs/cnn_architecture_stage2_v1/FREEZE_IMPLEMENTATION_V3.json",
        "outputs/cnn_architecture_stage2_v1/freeze_stage2_v2.py",
        "outputs/cnn_architecture_stage2_v1/freeze_stage2_v3.py",
        "outputs/cnn_architecture_stage2_v1/freeze_stage2_v4.py",
        "outputs/cnn_architecture_stage2_v1/STAGE2_FREEZE_SUPERSESSION.md",
        "outputs/cnn_architecture_stage2_v1/STAGE2_FREEZE_SUPERSESSION_V3.md",
        "outputs/cnn_architecture_stage2_v1/STAGE2_FREEZE_SUPERSESSION_V4.md",
        "outputs/cnn_architecture_stage2_v1/CNN_STAGE2_IMPLEMENTATION_READINESS.md",
        "outputs/cnn_architecture_stage2_v1/CNN_STAGE2_IMPLEMENTATION_READINESS_V3.md",
        "outputs/cnn_architecture_stage2_v1/CNN_STAGE2_IMPLEMENTATION_READINESS_V4.md",
        "outputs/cnn_architecture_stage2_v1/run_stage2.py",
        "outputs/cnn_architecture_stage2_v1/audit_stage2.py",
        "outputs/cnn_architecture_stage2_v1/tests/test_stage2_runner.py",
    ]
    paths = [row["path"] for row in original["source_and_protocol_files"]] + additional
    records = []
    for rel in paths:
        path = ROOT / rel
        if not path.is_file():
            raise FileNotFoundError(f"V4 freeze input missing: {rel}")
        records.append({"path": rel, "bytes": path.stat().st_size, "sha256": sha(path)})
    superseded = list(original.get("superseded_freeze_sha256s", []))
    superseded.extend([sha(ORIGINAL), sha(V2), sha(V3)])
    if len(superseded) != 7:
        raise RuntimeError(f"Expected four draft, original, V2 and V3 hashes; got {len(superseded)}")
    body = {
        "protocol_version": "1.0-prospective-freeze",
        "implementation_revision": "v4",
        "status": "FROZEN_IMPLEMENTATION_V4_NOT_EXECUTED",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "supersedes_freeze_file_sha256": sha(V3),
        "historical_original_freeze_sha256": sha(ORIGINAL),
        "prior_superseded_hash_count": 6,
        "superseded_freeze_sha256s": superseded,
        "protocol_id_sha256": hashlib.sha256(json.dumps(
            {"files": records, "inventory": inventory}, sort_keys=True,
            separators=(",", ":")).encode("utf-8")).hexdigest(),
        "seed_count": len(seeds),
        "unique_seed_count": len(set(seeds)),
        "seed_collision_audit": seed_audit["status"],
        "planned_unique_shot_ceiling": planned,
        "shots_generated": 0,
        "training_started": False,
        "final_development_data_accessed": False,
        "independent_test_seed_allocated": False,
        "independent_test_accessed": False,
        "source_and_protocol_files": records,
    }
    if NEW.exists():
        if json.loads(NEW.read_text(encoding="utf-8")) != body:
            raise RuntimeError("V4 freeze exists and differs; do not overwrite it")
    else:
        tmp = NEW.with_suffix(".json.tmp")
        with tmp.open("wb") as f:
            f.write((json.dumps(body, indent=2, sort_keys=True) + "\n").encode())
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, NEW)
    print(json.dumps({"freeze": NEW.relative_to(ROOT).as_posix(),
                      "status": body["status"], "protocol_id_sha256": body["protocol_id_sha256"],
                      "superseded_hash_count": len(superseded), "seed_count": len(seeds),
                      "shots_generated": 0, "training_started": False,
                      "files_hashed": len(records)}, indent=2))


if __name__ == "__main__":
    main()
