"""Extend the Stage 4 seed-collision screen to safe development-only manifests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from outputs.stage4_noise_adaptive_development_v1.prepare_seeds import (
    HISTORICAL_SOURCES, REPO, collect_seed_values,
)

HERE = Path(__file__).resolve().parent
EXTRA_SOURCES = [
    "outputs/cnn_architecture_stage1_v1/seed_inventory.json",
    "outputs/neural_decoder_diagnostic/root_cause_analysis/seed_inventory.json",
    "outputs/neural_decoder_diagnostic/root_cause_analysis/position_preserving_cnn/seed_inventory.json",
    "outputs/neural_decoder_diagnostic/structured_seed_inventory.json",
    "outputs/neural_decoder_diagnostic/structured_integration/dev_run_6000/structured_seed_inventory.json",
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    inventory = json.loads((HERE / "seed_inventory.json").read_text(encoding="utf-8"))
    candidates = {int(s["seed"]) for s in inventory["streams"]}
    historical: set[int] = set()
    rows = []
    # Revisit the exact source list used by the initial screen to compute a union,
    # then add only manifests explicitly identified as development-only.
    for rel in HISTORICAL_SOURCES + EXTRA_SOURCES:
        path = REPO / rel
        payload = json.loads(path.read_text(encoding="utf-8"))
        found = collect_seed_values(payload)
        historical.update(found)
        rows.append({"path": rel, "sha256": sha(path), "unique_seed_values_extracted": len(found),
                     "scope": "development metadata only"})
    collisions = sorted(candidates & historical)
    if collisions:
        raise RuntimeError(f"Stage 4 allocation collides with recoverable development RNG values: {collisions}")
    result = {
        "status": "PASS_RECOVERABLE_DEVELOPMENT_METADATA",
        "stage4_candidate_count": len(candidates),
        "stage4_candidate_unique": len(candidates) == 82,
        "stage4_candidate_range": [min(candidates), max(candidates)],
        "recoverable_historical_development_seed_values_union": len(historical),
        "collisions": collisions,
        "files_examined": rows,
        "sealed_independent_test_accessed": False,
        "excluded_scope": "No independent-test, sealed-test, final-test, held-out sample arrays, or labels were opened, read, hashed, summarized, or used.",
        "access_note": "An initial broad filename-only search unintentionally displayed filenames under a historical independent-replication raw-data directory. No listed artifact was opened or used; subsequent seed screening read only the development metadata listed above.",
        "coverage_limit": "The audit can verify only seed values recorded in the listed development metadata. Unrecorded RNG use cannot be ruled out.",
    }
    (HERE / "additional_development_seed_audit.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    md = ["# Additional Development Seed Coverage", "", f"Result: **{result['status']}**.",
          f"Stage 4 candidate seeds: {len(candidates)} unique; recoverable historical values in union: {len(historical)}; collisions: {len(collisions)}.",
          "", "Files examined:"]
    md.extend(f"- `{r['path']}` — {r['unique_seed_values_extracted']} values; SHA-256 `{r['sha256']}`" for r in rows)
    md.extend(["", result["excluded_scope"], "", result["access_note"], "", result["coverage_limit"]])
    (HERE / "ADDITIONAL_SEED_COVERAGE.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("status", "stage4_candidate_count",
                                              "recoverable_historical_development_seed_values_union", "collisions")}, indent=2))


if __name__ == "__main__":
    main()
