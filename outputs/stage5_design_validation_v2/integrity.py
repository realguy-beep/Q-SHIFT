from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def verify_freeze():
    p = HERE / "DESIGN_VALIDATION_FREEZE.json"
    if not p.is_file():
        raise RuntimeError("design validation freeze is missing")
    record = json.loads(p.read_text(encoding="utf-8"))
    if not record.get("created_before_design_monte_carlo"):
        raise RuntimeError("freeze does not establish prospective ordering")
    if record.get("stage5_evaluation_shots_generated") != 0 or record.get("sealed_historical_test_accessed") is not False:
        raise RuntimeError("freeze violates the no-sampling/no-sealed-data boundary")
    for rel, expected in record["source_config_protocol_and_inventory_sha256"].items():
        path = ROOT / rel
        if not path.is_file() or sha(path) != expected:
            raise RuntimeError(f"frozen design input changed: {rel}")
    for rel, expected in record["historical_freezes_preserved_sha256"].items():
        if sha(ROOT / rel) != expected:
            raise RuntimeError(f"historical frozen artifact changed: {rel}")
    return {**record, "freeze_sha256": sha(p)}
