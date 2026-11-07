"""Prepare/screen Stage 5 seeds and copy the frozen profile model; no sampling."""
from __future__ import annotations

import hashlib
import csv
import json
import shutil
from pathlib import Path

from outputs.stage4c_cnn_noise_estimation_v1.prepare_inventory import (
    HISTORICAL_FILES, STAGE4B_FILES, extract_seed_values,
)

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BASE = 4_240_000_001
STAGE4C_INVENTORY = "outputs/stage4c_cnn_noise_estimation_v1/seed_inventory.json"
STAGE4C_PROFILE = "outputs/stage4c_cnn_noise_estimation_v1/run/profile_estimator.json"
EXTRA_HISTORICAL_METADATA = [
    "outputs/phase4a_model_adequacy/config.json",
    "outputs/phase4a_model_adequacy/TEMPLATES.json",
    "outputs/phase4a_model_adequacy/DEVELOPMENT_CHECKPOINT.json",
    "outputs/phase4a_model_adequacy/VALIDATION_CHECKPOINT.json",
    "outputs/phase4a_model_adequacy/TEST_CHECKPOINT.json",
    "outputs/phase4a_model_adequacy/FREEZE.json",
    "outputs/phase4a_model_adequacy/PER_SEED_RESULTS.csv",
    "outputs/phase4b_replication/config.json",
    "outputs/phase4b_replication/TEMPLATES.json",
    "outputs/phase4b_replication/DEVELOPMENT_CHECKPOINT.json",
    "outputs/phase4b_replication/VALIDATION_CHECKPOINT.json",
    "outputs/phase4b_replication/TEST_CHECKPOINT.json",
    "outputs/phase4b_replication/FREEZE.json",
    "outputs/phase4b_replication/PER_SEED_RESULTS.csv",
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    streams=[]
    seed=BASE
    for kind, shots in (("calibration_detector_only",2000),("paired_evaluation_detector_observable",2500)):
        for p in (0.0,0.004,0.008,0.012,0.016):
            for root in range(100):
                streams.append({"kind":kind,"probability":p,"root":root,"shots":shots,"seed":seed})
                seed+=1
    rngs={"bootstrap":seed,"primary_signflip":seed+1}
    proposed=[int(x["seed"]) for x in streams]+list(rngs.values())
    if len(proposed)!=1002 or len(set(proposed))!=1002 or max(proposed)>=2**32:
        raise RuntimeError("invalid Stage 5 seed inventory")
    historical=set()
    records=[]
    paths=HISTORICAL_FILES+STAGE4B_FILES+[STAGE4C_INVENTORY]+EXTRA_HISTORICAL_METADATA
    for rel in paths:
        path=REPO/rel
        if not path.is_file():
            raise FileNotFoundError(rel)
        if path.suffix.lower() == ".csv":
            with path.open("r", encoding="utf-8-sig", newline="") as f:
                reader=csv.DictReader(f)
                seed_columns=[name for name in (reader.fieldnames or [])
                              if "seed" in name.lower() or "rng" in name.lower()]
                values=[]
                for row in reader:
                    for column in seed_columns:
                        try:
                            number=int(row[column])
                            if 0 <= number < 2**32:
                                values.append(number)
                        except (TypeError, ValueError):
                            pass
        else:
            values=extract_seed_values(json.loads(path.read_text(encoding="utf-8")))
        historical.update(values)
        records.append({"path":rel,"sha256":sha(path),"unique_seed_values_extracted":len(set(values)),
                        "extracted_values":sorted(set(values)),"scope":"explicit development seed metadata only; no current sealed-test files or sample arrays"})
    expanded=[]
    for rel in ("outputs/phase4a_model_adequacy/config.json", "outputs/phase4b_replication/config.json"):
        cfg=json.loads((REPO/rel).read_text(encoding="utf-8"))
        root_cfg=cfg["seed_roots"]
        roots=[int(root_cfg["start"])+i*int(root_cfg["step"]) for i in range(int(root_cfg["count"]))]
        offsets=[int(v) for v in cfg["seed_offsets"].values()]
        # Expand the frozen historical runner's actual root + stage offset + condition index formula.
        derived=set(roots)
        derived.update(root+off+ci for root in roots for off in offsets for ci in range(3))
        derived.update(int(cfg["template_seed_start"])+i for i in range(9))
        derived.update((int(cfg["noiseless_seed"]), int(cfg["bootstrap_seed"])))
        historical.update(derived)
        expanded.append({"config_path":rel,"config_sha256":sha(REPO/rel),
            "formula":"root=start+root_index*step; sampling=root+stage_offset+condition_index for condition_index 0..2; plus nine template seeds, noiseless seed, bootstrap seed, and root IDs",
            "expanded_seed_values":sorted(derived),"unique_count":len(derived)})
    collisions=sorted(historical.intersection(proposed))
    if collisions:
        raise RuntimeError(f"Stage 5 candidate seed collision: {collisions}")
    inventory={"status":"PROSPECTIVE_SCREENED_NO_SAMPLES_GENERATED","base_seed":BASE,
        "seed_count":1002,"seed_min":min(proposed),"seed_max":max(proposed),"analysis_rngs":rngs,
        "shot_count":sum(x["shots"] for x in streams),"streams":streams}
    audit={"status":"PASS_RECOVERABLE_DEVELOPMENT_METADATA","historical_seed_values_union":len(historical),
        "stage4c_seed_count_included":554,"stage5_candidate_seed_count":len(proposed),
        "stage5_candidate_collisions":collisions,"historical_files_examined":records,
        "derived_phase4a_phase4b_seed_expansions":expanded,
        "coverage_limit":"Only explicitly listed development seed metadata were read, including recorded Phase 4A/4B configs, checkpoint metadata and per-seed summaries. No current sealed-test files or sample arrays were enumerated/opened. Unrecorded RNG use cannot be ruled out.",
        "sampling_started":False}
    (HERE/"seed_inventory.json").write_text(json.dumps(inventory,indent=2)+"\n",encoding="utf-8")
    (HERE/"seed_audit.json").write_text(json.dumps(audit,indent=2)+"\n",encoding="utf-8")
    profile_path=REPO/STAGE4C_PROFILE
    if not profile_path.is_file():
        raise FileNotFoundError("audited Stage 4C profile estimator is missing")
    frozen=HERE/"FROZEN_PROFILE_ESTIMATOR.json"
    shutil.copyfile(profile_path,frozen)
    provenance={"source_path":STAGE4C_PROFILE,"source_sha256":sha(profile_path),
        "copied_sha256":sha(frozen),"stage4c_training_archive_sha256":sha(REPO/"outputs/stage4c_cnn_noise_estimation_v1/run/training_batches.npz"),
        "stage4c_independent_audit_status":json.loads((REPO/"outputs/stage4c_cnn_noise_estimation_v1/STAGE4C_AUDIT_RESULTS.json").read_text())["status"],
        "interpretation":"Small fitted detector-profile parameters copied for the Stage 5 protocol candidate; no evaluation samples copied."}
    (HERE/"PROFILE_PROVENANCE.json").write_text(json.dumps(provenance,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"seed_audit":audit["status"],"historical_seed_values_union":len(historical),
        "stage5_seeds":len(proposed),"seed_range":[min(proposed),max(proposed)],"collisions":collisions,
        "profile_sha256":sha(frozen),"samples_generated":0},indent=2))


if __name__=="__main__":
    main()
