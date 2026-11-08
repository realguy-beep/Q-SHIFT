"""Screen new design-simulation streams against recoverable, nonsealed metadata only."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIOR = ROOT / "outputs/stage5_design_validation_v3_n1210/secondary_holm"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def large_ints(value):
    if isinstance(value, bool):
        return
    if isinstance(value, int) and value >= 1_000_000:
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from large_ints(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from large_ints(item)


def main() -> None:
    if (HERE / "STAGE5_SECONDARY_REPAIR_SEED_INVENTORY.json").exists():
        raise RuntimeError("refusing to overwrite seed inventory")
    previous = json.loads((PRIOR / "SECONDARY_HOLM_SEED_INVENTORY.json").read_text(encoding="utf-8"))
    expected_hashes = {x["path"]: x["sha256"] for x in previous["historical_sources_checked"]}
    paths = list(expected_hashes)
    paths.extend([
        "outputs/stage5_design_validation_v3_n1210/secondary_holm/SECONDARY_HOLM_CONFIG.json",
        "outputs/stage5_design_validation_v3_n1210/secondary_holm/SECONDARY_HOLM_SEED_INVENTORY.json",
        "outputs/stage5_design_validation_v3_n1210/secondary_holm/SECONDARY_HOLM_RESULTS_REPAIR_V1.json",
        "outputs/stage5_design_validation_v3_n1210/secondary_holm/SECONDARY_HOLM_AUDIT_REPAIR_V2.json",
        "outputs/stage5_design_validation_v3_n1210/DESIGN_SEED_INVENTORY.json",
        "outputs/stage5_design_validation_v3_n1210/DESIGN_MC_RESULTS.json",
        "outputs/stage5_candidate_v3_n666/STAGE5_V3_SEED_INVENTORY.json",
        "outputs/stage5_final_decision_v1/ALLOCATION_ESTIMATES.json",
        "outputs/stage5_preexecution_v1/seed_inventory.json",
        "outputs/stage5_preexecution_v1/STAGE5_V2_CONFIG.json"
    ])
    paths = list(dict.fromkeys(paths))
    recovered: set[int] = set()
    checked = []
    for rel in paths:
        path = ROOT / rel
        if not path.is_file():
            raise FileNotFoundError(f"recoverable nonsealed metadata missing: {rel}")
        actual_hash = sha256(path)
        if rel in expected_hashes and actual_hash != expected_hashes[rel]:
            raise RuntimeError(f"historical source hash changed: {rel}")
        parsed = json.loads(path.read_text(encoding="utf-8"))
        values = list(large_ints(parsed))
        recovered.update(values)
        checked.append({"path": rel, "sha256": actual_hash, "large_integer_values_screened": len(values),
                        "previously_audited_hash_reverified": rel in expected_hashes})
    cfg = json.loads((HERE / "DESIGN_CONFIG.json").read_text(encoding="utf-8"))
    first = int(cfg["rng"]["namespace_start"])
    streams = []
    for family in cfg["families"]:
        streams.append({"role": f"calibration:{family['name']}", "seed": first + len(streams)})
    for family in cfg["families"]:
        for q in cfg["variability_multipliers"]:
            scenario = f"{family['name']}_q{str(q).replace('.', '_')}"
            streams.append({"role": f"validation:{scenario}", "seed": first + len(streams)})
    seeds = [x["seed"] for x in streams]
    collisions = sorted(set(seeds) & recovered)
    if len(seeds) != len(set(seeds)):
        raise RuntimeError("duplicate proposed seeds")
    if collisions:
        raise RuntimeError(f"proposed seed collision with recoverable historical metadata: {collisions}")
    if len(streams) != 18 or len(seeds) != 18:
        raise AssertionError("frozen stream allocation should contain six calibrators and twelve validation streams")
    end = max(seeds)
    output = {
        "purpose": "secondary statistical design validation only; not Stage 5 evaluation allocation",
        "created_before_simulation": True,
        "stage5_evaluation_seeds_allocated": False,
        "stage5_evaluation_shots_generated": 0,
        "sealed_test_accessed": False,
        "historical_coverage": "Rehashed and rescanned the exact prior secondary-HOLM nonsealed metadata allowlist plus Stage 5 v2 seed/config metadata, n=666 candidate inventory, n=1210 design inventory/results, and the local final-decision allocation metadata. No sealed data paths or sample archives were accessed.",
        "historical_sources_checked": checked,
        "distinct_recoverable_large_integer_values": len(recovered),
        "collision_count": 0,
        "stream_count": len(streams),
        "streams": streams,
        "rng": {"bit_generator": "PCG64", "namespace_start": first, "namespace_end": end}
    }
    target = HERE / "STAGE5_SECONDARY_REPAIR_SEED_INVENTORY.json"
    target.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {len(streams)} unique validation streams; {len(recovered)} distinct historical metadata integers screened; 0 collisions")


if __name__ == "__main__":
    main()
