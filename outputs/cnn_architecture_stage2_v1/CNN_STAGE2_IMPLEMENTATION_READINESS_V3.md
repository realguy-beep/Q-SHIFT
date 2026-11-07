# Q-SHIFT CNN Stage 2 — V3 Readiness

**Pre-sampling status:** V2 was blocked at the first environment/resource check before any sampler call. V3 corrects only the resource-key implementation mismatch and is ready for V3 hash verification plus the already-authorized 256-shot bounded diagnostic. Full execution remains conditional on that diagnostic and all resource gates passing.

## V2 blocker and exact correction

The frozen stage2_config.json uses resources.minimum_free_disk_gib_before_sampling. The V2 runner incorrectly looked up minimum_free_disk_gib, causing the exact error:

    KeyError: 'minimum_free_disk_gib'

This occurred in check_environment before lock acquisition, status creation, or Stim sampling. FREEZE_IMPLEMENTATION_V2.json records zero generated shots and no training; the Stage 2 run_v1/ directory was absent. V2 is preserved and superseded by the new V3 record.

V3 updates the environment gate, runtime resource checks, dry-run resource checks, and the regression-test fixture to use the exact existing frozen key. No protocol value or configuration file changed.

## Verified environment

- Python 3.12.10
- PyTorch 2.14.1+cu126
- Stim 1.16.0
- PyMatching 2.4.0
- CUDA 12.6 available on NVIDIA GeForce RTX 4050 Laptop GPU
- Free disk: 254.33 GiB at the last check; current process RSS: 0.544 GiB
- No running Python/Pythonw/TorchRun experiment process was found.
- Local main and origin/main were at ed52ca3d36ff64eb800d4adc7652b127eb594ad6 before Stage 2 edits.

## Regression checks

Run before V3 freeze creation:

    python -m py_compile outputs/cnn_architecture_stage2_v1/run_stage2.py outputs/cnn_architecture_stage2_v1/audit_stage2.py outputs/cnn_architecture_stage2_v1/freeze_stage2_v2.py outputs/cnn_architecture_stage2_v1/freeze_stage2_v3.py outputs/cnn_architecture_stage2_v1/tests/test_stage2_runner.py
    python -m unittest discover -s outputs/cnn_architecture_stage2_v1/tests -v
    python -m unittest discover -s outputs/cnn_architecture_stage1_v1/tests -v

Results after the resource-key correction: compilation passed; Stage 2 regression tests **12/12 passed**; Stage 1 architecture tests **6/6 passed**. Tests include the frozen circuit and DEM dimension check without sampling, shape/binary validation, residual XOR, seed/partition isolation, shared paired inputs, best-state restoration, global 15-selection barrier, deterministic RNG replay, checkpoint hash corruption, useful/harmful corrections, resource-limit rejection, and persisted status behavior.

## Scientific and data safeguards

- The 260,000-shot ceiling, 95 reserved seeds, five roots, two conditions, all three CNNs, fixed baseline definitions, training recipe, model-selection rules, and root-level descriptive endpoint are unchanged.
- No final-development partition can be generated until all 15 model/root selections and weight hashes are persisted and verified in selection_manifest_before_final.json.
- Final partitions retain byte-identical detector/observable arrays for each model comparison. The independent auditor rebuilds both matchers and CNN outputs, checks every split and selection choice, then independently derives the per-shot and root-level metrics.
- Independent-test data and seed allocation are not opened.

## Next gate

Create/verify FREEZE_IMPLEMENTATION_V3.json, rerun the hash/environment/circuit checks, then execute the permitted 256-shot root-00 nominal training-prefix diagnostic. Proceed with the full frozen study only if its conservative wall/CUDA/memory/disk estimate passes. Otherwise preserve the prefix evidence and stop without reducing the design.
