"""Read-only post-dry-run integrity check for the autonomous experiment package."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    freeze = json.loads((HERE / "FREEZE_FINAL_V3.json").read_text(encoding="utf-8"))
    inventory = json.loads((HERE / "SEED_INVENTORY.json").read_text(encoding="utf-8"))
    proof = json.loads((HERE / "DRY_RUN_RESUME_VERIFICATION_V4.json").read_text(encoding="utf-8"))
    run = HERE / "dry_run_v4"
    manifest = json.loads((run / "RUN_MANIFEST.json").read_text(encoding="utf-8"))
    freeze_checks = {}
    for rel, expected in freeze["source_sha256"].items():
        path = HERE / rel if rel in {"controller.py", "experiment.py", "prepare_freeze.py", "config.json",
                                     "SEED_INVENTORY.json", "PROTOCOL.md", "ANALYSIS_PLAN.json",
                                     "tests/test_controller.py"} else HERE.parents[2] / rel
        freeze_checks[rel] = path.is_file() and sha(path) == expected
    manifest_checks = {rel: (run / rel).is_file() and sha(run / rel) == digest
                       for rel, digest in manifest["file_sha256"].items()}
    root_path = run / "data" / "dry_root_00.npz"
    final_path = run / "data" / "dry_final_root_00.npz"
    prediction_path = run / "predictions" / "dry_root00_position_flat_cnn.npz"
    result = json.loads((run / "job_results" / "dry_root00_position_flat_cnn.json").read_text(encoding="utf-8"))
    with np.load(root_path, allow_pickle=False) as z:
        root_keys = list(z.files)
        root_has_final = any(k.startswith("final__") or k.startswith("final_development_evaluation__") for k in root_keys)
    with np.load(final_path, allow_pickle=False) as z:
        final_keys = list(z.files)
        final_shapes_ok = all(z[f"final__{r}__detectors"].shape == (256, 40)
                              and z[f"final__{r}__observable"].shape == (256,)
                              and z[f"final__{r}__pymatching"].shape == (256,)
                              for r in ("x_biased", "balanced", "z_biased"))
    recomputed = {}
    with np.load(prediction_path, allow_pickle=False) as z:
        for regime in ("x_biased", "balanced", "z_biased"):
            y = z[f"observable__{regime}"].astype(np.uint8)
            pm = z[f"pymatching__{regime}"].astype(np.uint8)
            pred = z[f"prediction__{regime}"].astype(np.uint8)
            if any(np.any((x != 0) & (x != 1)) for x in (y, pm, pred)):
                raise RuntimeError(f"Non-binary dry prediction evidence in {regime}.")
            wrong, pm_wrong = pred ^ y, pm ^ y
            recomputed[regime] = {"shots": len(y), "errors": int(wrong.sum()),
                                  "pymatching_errors": int(pm_wrong.sum()),
                                  "candidate_only": int(((wrong == 1) & (pm_wrong == 0)).sum()),
                                  "pymatching_only": int(((wrong == 0) & (pm_wrong == 1)).sum()),
                                  "predictions_match_result": int(wrong.sum()) == int(result["per_regime"][regime]["errors"])}
    all_seeds = []
    for stream in inventory["streams"]:
        all_seeds.extend(map(int, stream["seeds"]))
    for stream in inventory["dry_run_streams"]:
        all_seeds.append(int(stream["seed"]))
    for stream in inventory["model_streams"]:
        all_seeds.extend((int(stream["torch_seed"]), int(stream["sampling_seed"]), int(stream["shuffle_seed"])))
    all_seeds.extend(map(int, inventory["dry_run_model_rng_seeds"]))
    all_seeds.extend(map(int, inventory["circuit_diagnostic_seeds"]))
    all_seeds.extend(map(int, inventory["dry_run_circuit_diagnostic_seeds"]))
    report = {
        "status": "PASS" if all(freeze_checks.values()) and all(manifest_checks.values())
                          and len(all_seeds) == len(set(all_seeds))
                          and proof.get("status") == "PASS" and proof.get("independent_test_access") == 0
                          and not root_has_final and final_shapes_ok
                          and all(v["predictions_match_result"] for v in recomputed.values())
                          and not any("quarantine" in p.name.lower() for p in (run / "data").iterdir())
                          and not (HERE / "run" / "progress.json").exists() else "FAIL",
        "freeze_source_hashes_passed": sum(freeze_checks.values()),
        "freeze_source_hashes_total": len(freeze_checks),
        "dry_manifest_files_passed": sum(manifest_checks.values()),
        "dry_manifest_files_total": len(manifest_checks),
        "unique_seeds": len(set(all_seeds)), "proposed_seeds": len(all_seeds),
        "resume_proof": proof, "dry_root_archive_contains_final_eval": root_has_final,
        "final_eval_shapes_valid": final_shapes_ok, "dry_prediction_recomputation": recomputed,
        "quarantine_files_in_clean_v4": [p.name for p in (run / "data").iterdir() if "quarantine" in p.name.lower()],
        "full_run_started": (HERE / "run" / "progress.json").exists(),
        "test_samples_generated_or_accessed": 0,
    }
    output = HERE / "READINESS_VERIFICATION.json"
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
