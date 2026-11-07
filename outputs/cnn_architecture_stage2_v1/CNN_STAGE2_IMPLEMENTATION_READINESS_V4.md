# Q-SHIFT CNN Stage 2 — V4 Readiness

**Pre-sampling state:** V2 and V3 were both blocked by implementation preflight issues before sampling. V4 fixes the supersession-chain verifier semantics. No Stage 2 samples, training, or final-development data have been generated or accessed.

## Superseded preflight records

- V2 used a nonexistent resource key and stopped with KeyError: 'minimum_free_disk_gib'. The frozen config key is minimum_free_disk_gib_before_sampling. This was corrected in V3.
- V3 then stopped because its verifier compared the original FREEZE.json hash against the V2 supersession field instead of the distinct historical_original_freeze_sha256 field. This is corrected in V4.
- Both V2 and V3 freeze files remain unchanged, each records zero samples and no training, and the Stage 2 run_v1/ directory was absent when checked.

## Current validation

The V4 implementation distinguishes the original historical FREEZE.json SHA-256 from the immediately superseded V3 freeze SHA-256. It also verifies the full source/config file inventory, canonical protocol ID, 95 unique in-range seeds, unchanged 260,000-shot total, and seven superseded pre-sampling snapshots (four draft hashes plus original, V2, V3).

The exact V4 freeze must be generated and verified before any sampler call. Then the bounded diagnostic is allowed to use only the first 256 shots of root-00 nominal training, which are included in and reused within its 10,000-shot training partition. Full execution requires that dry-run estimate and all resource checks pass.

## Fixed protocol and safeguards

The only code fix since V3 is verification-chain semantics. Science, seeds, split counts, model order, optimizer schedule, monitor/checkpoint selection, calibration, threshold selection, root-level endpoint, development gate, and all resource caps are unchanged.

The runner globally freezes all 15 model/root selections before opening any final-development stream. It saves atomically, resumes from integrity-checked epoch checkpoints, enforces disk/RAM/CUDA/wall limits, and stops for insufficient positives or invalid pairing. The independent auditor reconstructs matching predictions and CNN outputs from saved data and weights; independent-test access is prohibited.

## Exact validation commands

    python -m py_compile outputs/cnn_architecture_stage2_v1/run_stage2.py outputs/cnn_architecture_stage2_v1/audit_stage2.py outputs/cnn_architecture_stage2_v1/freeze_stage2_v2.py outputs/cnn_architecture_stage2_v1/freeze_stage2_v3.py outputs/cnn_architecture_stage2_v1/freeze_stage2_v4.py outputs/cnn_architecture_stage2_v1/tests/test_stage2_runner.py
    python -m unittest discover -s outputs/cnn_architecture_stage2_v1/tests -v
    python -m unittest discover -s outputs/cnn_architecture_stage1_v1/tests -v

After V4 code is frozen, repeat those tests and verify V4, CUDA, disk, circuit and DEM dimensions before starting the 256-shot dry run.
