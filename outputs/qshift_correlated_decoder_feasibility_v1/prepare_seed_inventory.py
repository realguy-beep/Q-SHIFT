"""Create the frozen, domain-separated development seed inventory."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HISTORICAL = ROOT.parents[1] / "outputs" / "qshift_performance_sprint_v1" / "seed_inventory.json"
NAMESPACE = "qshift-correlated-decoder-feasibility-v1-2026-11-15"
PROBABILITIES = (0.0, 0.01, 0.02)


def collect_ints(obj):
    if isinstance(obj, bool):
        return []
    if isinstance(obj, int):
        return [obj]
    if isinstance(obj, dict):
        return [v for item in obj.values() for v in collect_ints(item)]
    if isinstance(obj, list):
        return [v for item in obj for v in collect_ints(item)]
    return []


def labels():
    out = [f"train:q{q:.2f}" for q in PROBABILITIES]
    out += [f"cal:q{q:.2f}:r{r:02d}" for q in PROBABILITIES for r in range(10)]
    out += [f"eval:q{q:.2f}:r{r:02d}" for q in PROBABILITIES for r in range(10)]
    out += ["statistics:primary-bootstrap", "statistics:zero-bootstrap"]
    return out


def main():
    previous_bytes = HISTORICAL.read_bytes()
    previous = json.loads(previous_bytes)
    previous_values = set(collect_ints(previous.get("seeds", {})))
    result = {}
    used = set(previous_values)
    collision_rejections = 0
    for label in labels():
        counter = 0
        while True:
            digest = hashlib.sha256(f"{NAMESPACE}:{label}:{counter}".encode()).digest()
            seed = (int.from_bytes(digest[:8], "big") % (2**31 - 1)) + 1
            if seed not in used:
                break
            collision_rejections += 1
            counter += 1
        result[label] = seed
        used.add(seed)
    inventory = {
        "schema": "qshift-correlated-decoder-seed-inventory-v1",
        "namespace": NAMESPACE,
        "derivation": "first 64 SHA-256 bits of namespace:label:counter reduced to [1,2^31-1]; increment counter on collision",
        "historical_screen": {
            "path": "outputs/qshift_performance_sprint_v1/seed_inventory.json",
            "sha256": hashlib.sha256(previous_bytes).hexdigest(),
            "numeric_seed_values_screened": len(previous_values),
            "collisions_rejected": collision_rejections,
            "scope": "this named V1 development inventory only; no Stage 5 or sealed inventory was accessed"
        },
        "seed_count": len(result),
        "internal_unique": len(set(result.values())) == len(result),
        "disjoint_from_screened_inventory": not (set(result.values()) & previous_values),
        "seeds": result,
    }
    if not inventory["internal_unique"] or not inventory["disjoint_from_screened_inventory"]:
        raise SystemExit("seed inventory collision check failed")
    target = ROOT / "seed_inventory.json"
    target.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in inventory.items() if k != "seeds"}, indent=2))


if __name__ == "__main__":
    main()
