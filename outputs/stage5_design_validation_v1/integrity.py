"""Hash guard for this prospective design-validation package."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FREEZE_PATH = HERE / "DESIGN_VALIDATION_FREEZE.json"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_preexecution_freeze() -> dict:
    if not FREEZE_PATH.is_file():
        raise RuntimeError("design validation freeze is missing")
    record = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    if record.get("stage5_evaluation_shots_generated") != 0 or record.get("sealed_historical_test_accessed") is not False:
        raise RuntimeError("freeze does not assert the authorized no-sampling/no-sealed-data boundary")
    for rel, expected in record["sha256"].items():
        path = ROOT / rel
        if not path.is_file() or digest(path) != expected:
            raise RuntimeError(f"frozen validation input/source hash mismatch: {rel}")
    if digest(ROOT / "outputs/stage5_preexecution_v1/STAGE5_V2_FREEZE.json") != record["stage5_v2_freeze_preserved_sha256"]:
        raise RuntimeError("historical Stage 5 v2 freeze changed")
    return record
