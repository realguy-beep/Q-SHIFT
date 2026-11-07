from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FILES = [
    "outputs/stage5_design_validation_v2/STAGE5_STATISTICAL_DESIGN_AMENDMENT_CANDIDATE_V2.md",
    "outputs/stage5_design_validation_v2/DESIGN_SIMULATION_CONFIG.json",
    "outputs/stage5_design_validation_v2/DESIGN_SEED_INVENTORY.json",
    "outputs/stage5_design_validation_v2/prepare_seed_inventory.py",
    "outputs/stage5_design_validation_v2/design_simulation.py",
    "outputs/stage5_design_validation_v2/independent_audit.py",
    "outputs/stage5_design_validation_v2/tests/test_design_method.py",
    "outputs/stage5_design_validation_v2/integrity.py",
    "outputs/stage5_design_validation_v2/freeze_candidate.py",
]
PRESERVE = [
    "outputs/stage5_preexecution_v1/STAGE5_V2_FREEZE.json",
    "outputs/stage4c_cnn_noise_estimation_v1/FREEZE.json",
]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


hashes = {rel: sha(ROOT / rel) for rel in FILES}
preserved = {rel: sha(ROOT / rel) for rel in PRESERVE}
record = {
    "name": "Stage 5 statistical design validation v2 candidate freeze",
    "created_before_design_monte_carlo": True,
    "stage5_evaluation_shots_generated": 0,
    "sealed_historical_test_accessed": False,
    "candidate_sampling_authorized": False,
    "source_config_protocol_and_inventory_sha256": hashes,
    "historical_freezes_preserved_sha256": preserved,
    "scope": "synthetic root-effect design simulation and prior disposable engineering benchmark only",
}
path = HERE / "DESIGN_VALIDATION_FREEZE.json"
tmp = path.with_suffix(".json.tmp")
tmp.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
os.replace(tmp, path)
record["freeze_sha256"] = sha(path)
print(json.dumps({"freeze": str(path), "freeze_sha256": record["freeze_sha256"], "hashed_files": len(hashes)}, indent=2))
