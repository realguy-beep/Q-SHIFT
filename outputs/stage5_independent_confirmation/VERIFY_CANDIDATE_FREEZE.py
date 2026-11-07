"""Read-only check of the Stage 5 candidate hashes and allocation, no sampling."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    freeze = json.loads((HERE / "STAGE5_CANDIDATE_FREEZE.json").read_text(encoding="utf-8"))
    mismatches = [rel for rel, expected in freeze["files_sha256"].items()
                  if not (ROOT / rel).is_file() or sha(ROOT / rel) != expected]
    inv = json.loads((HERE / "seed_inventory.json").read_text(encoding="utf-8"))
    audit = json.loads((HERE / "seed_audit.json").read_text(encoding="utf-8"))
    assert not mismatches, f"candidate hash mismatch: {mismatches}"
    assert inv["seed_count"] == 1002 and inv["shot_count"] == 2_250_000
    assert audit["stage5_candidate_collisions"] == []
    assert freeze["sampling_started"] is False
    expected_probabilities = [0.0, 0.004, 0.008, 0.012, 0.016]
    expected_streams = []
    seed = 4_240_000_001
    for kind, shots in (("calibration_detector_only", 2000),
                        ("paired_evaluation_detector_observable", 2500)):
        for probability in expected_probabilities:
            for root in range(100):
                expected_streams.append({"kind": kind, "probability": probability,
                                         "root": root, "shots": shots, "seed": seed})
                seed += 1
    assert inv["streams"] == expected_streams, "seed inventory differs from specified allocation"
    assert inv["analysis_rngs"] == {"bootstrap": seed, "primary_signflip": seed + 1}
    proposed = [row["seed"] for row in inv["streams"]] + list(inv["analysis_rngs"].values())
    assert len(proposed) == len(set(proposed)) == 1002
    historical_values = set()
    for record in audit["historical_files_examined"]:
        assert sha(ROOT / record["path"]) == record["sha256"], f"historical metadata changed: {record['path']}"
        historical_values.update(record["extracted_values"])
    assert len(historical_values) == audit["historical_seed_values_union"]
    assert not historical_values.intersection(proposed), "historical seed collision"
    assert not (HERE / "run").exists(), "Stage 5 run directory exists; candidate cannot assert no sampling"
    print(f"PASS candidate hashes={len(freeze['files_sha256'])}; historical seed values={len(historical_values)}; "
          f"proposed seeds={len(proposed)}; shots planned={inv['shot_count']}; no samples generated")


if __name__ == "__main__":
    main()
