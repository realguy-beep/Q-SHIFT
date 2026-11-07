"""Create or verify an implementation freeze without changing FREEZE.json."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OLD_FREEZE = HERE / "FREEZE.json"
NEW_FREEZE = HERE / "FREEZE_IMPLEMENTATION_V2.json"
EXPECTED_OLD_FREEZE_SHA256 = "045213b7906a06c0e4499f20cc6c5c74a8aa27f4abac1a3e5f9bb572e62dedd6"
MAX_STIM_SEED = 2_147_483_647


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def main() -> None:
    if not OLD_FREEZE.is_file():
        raise FileNotFoundError(OLD_FREEZE)
    old_sha = sha256_file(OLD_FREEZE)
    if old_sha != EXPECTED_OLD_FREEZE_SHA256:
        raise RuntimeError(f"Original freeze hash changed: expected {EXPECTED_OLD_FREEZE_SHA256}, got {old_sha}")
    old = json.loads(OLD_FREEZE.read_text(encoding="utf-8"))
    for record in old["source_and_protocol_files"]:
        path = ROOT / record["path"]
        if not path.is_file() or path.stat().st_size != record["bytes"] or sha256_file(path) != record["sha256"]:
            raise RuntimeError(f"Original frozen input mismatch: {record['path']}")

    cfg_path = HERE / "stage2_config.json"
    inventory_path = HERE / "seed_inventory.json"
    audit_path = HERE / "seed_audit.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    seeds = [int(x["seed"]) for x in inventory["streams"]]
    if len(seeds) != 95 or len(seeds) != len(set(seeds)):
        raise RuntimeError("Frozen seed inventory must contain 95 unique derived seeds")
    if not all(1 <= seed <= MAX_STIM_SEED for seed in seeds):
        raise RuntimeError("A frozen seed is outside the supported Stim range")
    if audit.get("status") != "PASS" or any(audit.get(k) for k in (
            "within_allocation_collisions", "historical_collisions", "phase3a_collisions",
            "stage1_diagnostic_collisions")):
        raise RuntimeError("Frozen seed audit no longer passes")
    planned = (int(cfg["roots"]["count"]) * int(cfg["conditions_per_root"])
               * sum(int(v) for v in cfg["shots_per_root_condition"].values()))
    if planned != 260_000 or planned != int(cfg["total_unique_shot_ceiling"]):
        raise RuntimeError("Stage 2 shot ceiling/allocation mismatch")

    additional_paths = [
        "outputs/cnn_architecture_stage2_v1/STAGE2_FREEZE_SUPERSESSION.md",
        "outputs/cnn_architecture_stage2_v1/CNN_STAGE2_IMPLEMENTATION_READINESS.md",
        "outputs/cnn_architecture_stage2_v1/run_stage2.py",
        "outputs/cnn_architecture_stage2_v1/audit_stage2.py",
        "outputs/cnn_architecture_stage2_v1/freeze_stage2_v2.py",
        "outputs/cnn_architecture_stage2_v1/tests/test_stage2_runner.py",
    ]
    paths = [r["path"] for r in old["source_and_protocol_files"]] + additional_paths
    files = []
    for rel in paths:
        path = ROOT / rel
        if not path.is_file():
            raise FileNotFoundError(f"Implementation freeze input missing: {rel}")
        files.append({"path": rel, "bytes": path.stat().st_size, "sha256": sha256_file(path)})

    superseded = list(old.get("superseded_freeze_sha256s", []))
    superseded.append(old_sha)
    core = {
        "protocol_version": "1.0-prospective-freeze",
        "implementation_revision": "v2",
        "status": "FROZEN_IMPLEMENTATION_V2_NOT_EXECUTED",
        "created_utc": (datetime.now(timezone.utc).isoformat() if not NEW_FREEZE.exists()
                        else json.loads(NEW_FREEZE.read_text(encoding="utf-8"))["created_utc"]),
        "supersedes_freeze_file_sha256": old_sha,
        "prior_superseded_hash_count": len(old.get("superseded_freeze_sha256s", [])),
        "superseded_freeze_sha256s": superseded,
        "protocol_id_sha256": hashlib.sha256(canonical_bytes({"files": files, "inventory": inventory})).hexdigest(),
        "seed_count": len(seeds),
        "unique_seed_count": len(set(seeds)),
        "seed_collision_audit": audit["status"],
        "planned_unique_shot_ceiling": planned,
        "shots_generated": 0,
        "training_started": False,
        "final_development_data_accessed": False,
        "independent_test_seed_allocated": False,
        "independent_test_accessed": False,
        "source_and_protocol_files": files,
    }
    if NEW_FREEZE.exists():
        if json.loads(NEW_FREEZE.read_text(encoding="utf-8")) != core:
            raise RuntimeError("Implementation freeze already exists but differs; preserve it and create a new version")
    else:
        NEW_FREEZE.write_text(json.dumps(core, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"freeze": NEW_FREEZE.relative_to(ROOT).as_posix(),
                      "original_freeze_sha256": old_sha,
                      "superseded_hash_count": len(superseded),
                      "files_hashed": len(files), "seeds": len(seeds),
                      "shots_generated": 0, "training_started": False,
                      "protocol_id_sha256": core["protocol_id_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
