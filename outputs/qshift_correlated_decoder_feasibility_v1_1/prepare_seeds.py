"""Prepare V1.1-only evaluation and bootstrap seed identities (no sampling)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
V1_INVENTORY = REPO / "outputs/qshift_correlated_decoder_feasibility_v1/seed_inventory.json"
EARLIER_INVENTORY = REPO / "outputs/qshift_performance_sprint_v1/seed_inventory.json"
NAMESPACE = "qshift-correlated-decoder-feasibility-v1-1-2026-11-15"
QS = (0.0, 0.01, 0.02)


def seed_values(path: Path) -> tuple[bytes, set[int]]:
    raw = path.read_bytes()
    data = json.loads(raw)
    seeds = data.get("seeds")
    if not isinstance(seeds, dict):
        raise ValueError(f"no explicit seeds object in {path.name}")
    values = set()
    for value in seeds.values():
        if isinstance(value, bool) or not isinstance(value, int) or not 0 < value < 2**31:
            raise ValueError(f"invalid seed value in {path.name}")
        values.add(value)
    if len(values) != len(seeds):
        raise ValueError(f"duplicate seeds in {path.name}")
    return raw, values


def planned_labels() -> list[str]:
    labels = [f"evaluation:q{q:.2f}:root{root:02d}" for q in QS for root in range(10)]
    labels += ["statistics:primary-bootstrap", "statistics:zero-bootstrap"]
    return labels


def main() -> None:
    v1_bytes, v1_values = seed_values(V1_INVENTORY)
    prior_bytes, prior_values = seed_values(EARLIER_INVENTORY)
    screened = v1_values | prior_values
    generated: dict[str, int] = {}
    used = set(screened)
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
    if len(generated) != 32 or len(set(generated.values())) != 32:
        raise RuntimeError("V1.1 seed allocation is incomplete or internally colliding")
    if set(generated.values()) & screened:
        raise RuntimeError("V1.1 seed allocation collided with screened development metadata")
    inventory = {
        "schema": "qshift-correlated-decoder-seed-inventory-v1.1",
        "namespace": NAMESPACE,
        "derivation": "first 64 SHA-256 bits of namespace:label:counter reduced to [1,2^31-1]; increment counter on collision",
        "new_seed_count": len(generated),
        "seeds": generated,
        "collision_screen": {
            "v1_inventory": {
                "path": "outputs/qshift_correlated_decoder_feasibility_v1/seed_inventory.json",
                "sha256": hashlib.sha256(v1_bytes).hexdigest(),
                "distinct_numeric_values_screened": len(v1_values),
            },
            "earlier_development_inventory": {
                "path": "outputs/qshift_performance_sprint_v1/seed_inventory.json",
                "sha256": hashlib.sha256(prior_bytes).hexdigest(),
                "distinct_numeric_values_screened": len(prior_values),
            },
            "union_distinct_numeric_values_screened": len(screened),
            "rejected_hash_collisions": collisions,
            "collisions_with_screened_values": 0,
            "stage5_or_sealed_metadata_accessed": False,
        },
        "internal_unique": True,
        "disjoint_from_screened_inventories": True,
        "purpose": "fresh V1.1 evaluation roots and analysis bootstrap streams only; V1 training/calibration seeds are reused by verified archive identity",
    }
    out = ROOT / "seed_inventory.json"
    out.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({key: value for key, value in inventory.items() if key != "seeds"}, indent=2))


if __name__ == "__main__":
    main()
