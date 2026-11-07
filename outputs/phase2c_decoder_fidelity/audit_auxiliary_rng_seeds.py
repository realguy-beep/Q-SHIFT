from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    original = json.loads((HERE / "SEED_COLLISION_AUDIT.json").read_text(encoding="utf-8"))
    historical = {int(x) for x in original["historical_seed_values"]}
    planned = set(int(x) for x in original["proposed_seeds"])
    model_seeds = [89011001, 89011002, 89011003, 89011004, 89011005, 89011006]
    report = {
        "status": "PASS_SUPPLEMENTAL_AUDIT",
        "reason": "The frozen runner uses a deterministic sklearn model random_state derived as development Stim seed + 1000. These six estimator RNG seeds were not included in the initial simulator/statistical seed inventory.",
        "derivation": "model_rng_seed = development_seed + 1000",
        "model_rng_seeds": model_seeds,
        "unique": len(set(model_seeds)) == len(model_seeds),
        "collisions_with_recoverable_historical_seeds": sorted(set(model_seeds) & historical),
        "collisions_with_initial_44_phase2c_seeds": sorted(set(model_seeds) & planned),
        "historical_seed_values_screened": len(historical),
        "historical_coverage_reference": "SEED_COLLISION_AUDIT.json (948 files examined; zero read failures)",
        "scope_note": "These are sklearn estimator-internal RNG initial states, not Stim sampling seeds. This supplemental post-sampling audit does not change any trained model or pilot sample; it documents an inventory omission in the pre-pilot record."
    }
    if not report["unique"] or report["collisions_with_recoverable_historical_seeds"] or report["collisions_with_initial_44_phase2c_seeds"]:
        report["status"] = "FAIL"
        raise RuntimeError(json.dumps(report, indent=2))
    (HERE / "AUXILIARY_RNG_AUDIT.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {len(model_seeds)} derived estimator seeds are unique and collision-free")


if __name__ == "__main__":
    main()
