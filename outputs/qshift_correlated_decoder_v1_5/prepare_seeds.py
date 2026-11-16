"""Prepare V1.5 calibration, evaluation and bootstrap seed identities (no sampling)."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from outputs.qshift_correlated_decoder_v1_5.contract import (  # noqa: E402
    FROZEN_ALLOCATION,
    QS,
    SEED_STATS_PRIMARY,
    SEED_STATS_ZERO,
    calibration_key,
    eval_key,
)

NAMESPACE = "qshift-correlated-decoder-v1-5-2026-11-16"
SCREENED = (
    "outputs/qshift_correlated_decoder_feasibility_v1/seed_inventory.json",
    "outputs/qshift_correlated_decoder_feasibility_v1_1/seed_inventory.json",
    "outputs/qshift_correlated_decoder_v1_2/seed_inventory.json",
    "outputs/qshift_correlated_decoder_v1_3/seed_inventory.json",
    "outputs/qshift_correlated_decoder_v1_4/GATE_SEEDS.json",
    "outputs/qshift_performance_sprint_v1/seed_inventory.json",
)
OUT = ROOT / "seed_inventory.json"


def seed_values(path: Path) -> tuple[bytes, set[int]]:
    raw = path.read_bytes()
    seeds = json.loads(raw).get("seeds")
    if not isinstance(seeds, dict):
        raise ValueError(f"no explicit seeds object in {path}")
    values = set()
    for value in seeds.values():
        if isinstance(value, bool) or not isinstance(value, int) or not 0 < value < 2**31:
            raise ValueError(f"invalid seed value in {path}")
        values.add(value)
    return raw, values


def planned_labels() -> list[str]:
    n = FROZEN_ALLOCATION.roots_per_q
    labels = [calibration_key(q, r) for q in QS for r in range(n)]
    labels += [eval_key(q, r) for q in QS for r in range(n)]
    return labels + [SEED_STATS_PRIMARY, SEED_STATS_ZERO]


def build_inventory() -> dict:
    screened: set[int] = set()
    screen_record = {}
    for relative in SCREENED:
        raw, values = seed_values(REPO / relative)
        screened |= values
        screen_record[relative] = {"sha256": hashlib.sha256(raw).hexdigest(),
                                   "distinct_numeric_values_screened": len(values)}
    used = set(screened)
    generated: dict[str, int] = {}
    collisions = 0
    for label in planned_labels():
        counter = 0
        while True:
            digest = hashlib.sha256(f"{NAMESPACE}:{label}:{counter}".encode("utf-8")).digest()
            value = int.from_bytes(digest[:8], "big") % (2**31 - 1) + 1
            if value not in used:
                break
            counter += 1
            collisions += 1
        generated[label] = value
        used.add(value)
    expected = len(planned_labels())
    if len(generated) != expected or len(set(generated.values())) != expected:
        raise RuntimeError("V1.5 seed allocation is incomplete or internally colliding")
    if set(generated.values()) & screened:
        raise RuntimeError("V1.5 seed allocation collided with screened inventories")
    return {
        "schema": "qshift-correlated-decoder-seed-inventory-v1.5",
        "namespace": NAMESPACE,
        "derivation": "first 64 SHA-256 bits of namespace:label:counter reduced to [1,2^31-1]; increment counter on collision",
        "new_seed_count": len(generated),
        "seeds": generated,
        "collision_screen": {
            "inventories": screen_record,
            "union_distinct_numeric_values_screened": len(screened),
            "rejected_hash_collisions": collisions,
            "collisions_with_screened_values": 0,
            "stage5_or_sealed_metadata_accessed": False,
        },
        "internal_unique": True,
        "disjoint_from_screened_inventories": True,
        "purpose": "fresh V1.5 calibration and evaluation roots and analysis bootstrap streams; V1, V1.1, V1.2, V1.3, V1.4 gate and performance-sprint seeds are screened, never reused",
    }


def main() -> None:
    inventory = build_inventory()
    OUT.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in inventory.items() if k != "seeds"}, indent=2))


if __name__ == "__main__":
    main()
