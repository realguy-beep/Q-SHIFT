"""Create the frozen deterministic seed inventory; does not sample."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))


def labels() -> list[str]:
    n = CONFIG["allocation"]["roots_per_probability"]
    out = [f"train:p{i}" for i in range(5)]
    out += [f"cal:p{i}:r{r:02d}" for i in range(5) for r in range(n)]
    out += [f"eval:p{i}:r{r:02d}" for i in range(5) for r in range(n)]
    out += ["statistics:primary-bootstrap", "statistics:condition-bootstrap", "statistics:zero-gate"]
    return out


def build_inventory() -> dict:
    namespace = CONFIG["seed_namespace"]
    seeds = {}
    for label in labels():
        raw = hashlib.sha256(f"{namespace}:{label}".encode("utf-8")).digest()
        seeds[label] = int.from_bytes(raw[:4], "big") % (2**31 - 1) + 1
    if len(set(seeds.values())) != len(seeds):
        raise RuntimeError("seed collision inside sprint inventory")
    return {
        "schema": "qshift-performance-seed-inventory-v1",
        "namespace": namespace,
        "derivation": "first 32 SHA-256 bits of namespace:partition-label, reduced to [1,2^31-1]",
        "internal_unique": True,
        "global_historical_collision_screen": False,
        "seed_count_including_statistics_stream": len(seeds),
        "seeds": seeds,
    }


if __name__ == "__main__":
    path = ROOT / "seed_inventory.json"
    data = json.dumps(build_inventory(), indent=2, sort_keys=True) + "\n"
    path.write_text(data, encoding="utf-8")
    print(f"wrote {path} ({len(json.loads(data)['seeds'])} unique entries)")