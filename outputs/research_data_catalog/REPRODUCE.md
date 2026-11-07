# Reproducing Q-SHIFT Dataset Summaries Safely

This document reproduces metadata checks and audited development summaries. It does not resimulate historical samples, retrain models, or access the current sealed independent-test allocation.

## Repository and environment

Run from the Q-SHIFT repository root using its existing Python environment. Historical study dependencies and versions are recorded in each study's report/config. Do not install packages as part of this procedure.

## Read-only metadata checks

Validate the inventory JSON and the Stage 5 candidate seed/freeze metadata:

```powershell
python -m json.tool outputs/research_data_catalog/DATASET_INVENTORY.json > $null
python outputs/research_data_catalog/verify_stage4c_manifest.py
python -m outputs.stage5_independent_confirmation.VERIFY_CANDIDATE_FREEZE
python -m outputs.stage5_independent_confirmation.INDEPENDENT_CANDIDATE_AUDIT
```

For Stage 4C, verify its original source freeze and run the focused tests:

```powershell
python outputs/stage4c_cnn_noise_estimation_v1/build_freeze.py --verify
python -m unittest discover -s outputs/stage4c_cnn_noise_estimation_v1/tests -v
```

`verify_stage4c_manifest.py` checks SHA-256 against the Stage 4C manifest without writing files; the raw entries remain in the local ignored `run/` directory. `build_manifest.py` is a writer and should not be used as a read-only verifier when preserving its timestamped manifest is required.

## Per-study reproduction

Use the `REPRODUCE.md` or `REPRODUCE_AFTER_RECOVERY.md` linked from each study's metadata. Do not issue a historical run/training command merely to regenerate a report: first determine whether the run is complete and whether the command would overwrite or duplicate samples. Prefer the study's independent audit script, which rescales saved development arrays without sampling. Some source README commands are historical and include runners; treat them as documentation, not authorization to rerun.

## Evidence interpretation

The inventory records sample allocations reported by each study, not globally deduplicated rows. Phase 4B's calibration detector arrays were not retained; its calibration fitting is not reproducible from the remaining test archives. The current sealed independent-test material is outside the inventory and was not enumerated, hashed, opened, or summarized.
