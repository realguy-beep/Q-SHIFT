"""Create a pre-simulation source/configuration freeze; output is immutable afterward."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    target = HERE / "DESIGN_FREEZE.json"
    if target.exists():
        raise RuntimeError("DESIGN_FREEZE.json already exists; refusing to replace it")
    inventory_path = HERE / "STAGE5_SECONDARY_REPAIR_SEED_INVENTORY.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    if inventory["collision_count"] or inventory["stage5_evaluation_shots_generated"]:
        raise RuntimeError("invalid seed inventory or unexpected sampling")
    source_paths = [
        "DESIGN_CONFIG.json", "PROSPECTIVE_METHOD.md", "stage5_secondary_stats.py",
        "simulate_secondary.py", "audit_secondary.py", "prepare_seed_inventory.py", "tests/test_secondary_stats.py",
        "STAGE5_SECONDARY_REPAIR_SEED_INVENTORY.json"
    ]
    source_hashes = {rel: sha(HERE / rel) for rel in source_paths}
    prior_paths = [x["path"] for x in inventory["historical_sources_checked"]]
    prior_hashes = {rel: sha(ROOT / rel) for rel in prior_paths}
    record = {
        "name": "Stage 5 secondary finite-envelope inference design freeze v1",
        "created_utc_before_simulation": datetime.now(timezone.utc).isoformat(),
        "supersedes": "No historical freeze; this is a prospective candidate. The prior Welch/Holm FAIL remains authoritative history.",
        "scope": "synthetic root-effect statistical design validation only; no Stage 5 runner or sample allocation",
        "stage5_evaluation_shots_generated": 0,
        "sealed_test_accessed": False,
        "source_and_config_sha256": source_hashes,
        "historical_metadata_sha256": prior_hashes,
        "seed_inventory_sha256": sha(inventory_path),
        "seed_count": len(inventory["streams"]),
        "configuration_summary": {
            "roots_per_condition": 1210,
            "planned_shots_if_later_authorized": 27225000,
            "dkw_delta_total": 0.001,
            "calibration_replicates_each_of_six_families": 1000000,
            "validation_replicates_each_family_scale": 200000,
            "marginal_size_cells": 192,
            "complete_partial_fwer_cells": 516,
            "holm_alpha": 0.05
        }
    }
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, target)
    print(f"PASS: pre-simulation freeze created; {len(source_hashes)} source/config hashes and {len(prior_hashes)} historical metadata hashes")


if __name__ == "__main__":
    main()
