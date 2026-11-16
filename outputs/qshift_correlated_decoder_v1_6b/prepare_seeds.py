"""Prepare V1.6b seed identities (no sampling); screened against all prior inventories."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from outputs.qshift_correlated_decoder_v1_6b import contract as K  # noqa: E402

NAMESPACE = "qshift-correlated-decoder-v1-6b-2026-11-16"
SCREENED = (
    "outputs/qshift_correlated_decoder_feasibility_v1/seed_inventory.json",
    "outputs/qshift_correlated_decoder_feasibility_v1_1/seed_inventory.json",
    "outputs/qshift_correlated_decoder_v1_2/seed_inventory.json",
    "outputs/qshift_correlated_decoder_v1_3/seed_inventory.json",
    "outputs/qshift_correlated_decoder_v1_4/GATE_SEEDS.json",
    "outputs/qshift_correlated_decoder_v1_5/seed_inventory.json",
    "outputs/qshift_performance_sprint_v1/seed_inventory.json",
)
OUT = ROOT / "seed_inventory.json"


def planned_labels() -> list[str]:
    labels = []
    for c in K.CONDITIONS:
        labels += [K.device_key(c, kind, q) for kind in ("detectors", "labeled") for q in K.QS]
        labels += [K.calibration_key(c, q, r) for q in K.QS for r in range(K.FROZEN_ALLOCATION.roots_per_q)]
        labels += [K.eval_key(c, q, r) for q in K.QS for r in range(K.FROZEN_ALLOCATION.roots_per_q)]
        labels += [K.stats_key(c, "primary"), K.stats_key(c, "zero")]
    return labels


def build_inventory() -> dict:
    screened, record = set(), {}
    for rel in SCREENED:
        raw = (REPO / rel).read_bytes()
        vals = set(json.loads(raw)["seeds"].values())
        screened |= vals
        record[rel] = {"sha256": hashlib.sha256(raw).hexdigest(), "distinct_numeric_values_screened": len(vals)}
    used, seeds, collisions = set(screened), {}, 0
    for label in planned_labels():
        counter = 0
        while True:
            v = int.from_bytes(hashlib.sha256(f"{NAMESPACE}:{label}:{counter}".encode()).digest()[:8], "big") % (2**31 - 1) + 1
            if v not in used:
                break
            counter += 1
            collisions += 1
        seeds[label] = v
        used.add(v)
    if set(seeds.values()) & screened or len(set(seeds.values())) != len(seeds):
        raise RuntimeError("V1.6b seed collision")
    return {"schema": "qshift-correlated-decoder-seed-inventory-v1.6b", "namespace": NAMESPACE,
            "derivation": "first 64 SHA-256 bits of namespace:label:counter reduced to [1,2^31-1]; increment counter on collision",
            "new_seed_count": len(seeds), "seeds": seeds,
            "collision_screen": {"inventories": record, "union_distinct_numeric_values_screened": len(screened),
                                 "rejected_hash_collisions": collisions, "collisions_with_screened_values": 0,
                                 "stage5_or_sealed_metadata_accessed": False},
            "internal_unique": True, "disjoint_from_screened_inventories": True,
            "purpose": "fresh V1.6b device, calibration and evaluation roots and bootstrap streams for both burst conditions"}


def main() -> None:
    inventory = build_inventory()
    OUT.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in inventory.items() if k != "seeds"}, indent=2))


if __name__ == "__main__":
    main()
