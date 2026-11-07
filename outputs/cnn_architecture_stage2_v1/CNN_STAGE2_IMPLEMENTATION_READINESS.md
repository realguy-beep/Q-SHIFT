# Q-SHIFT CNN Stage 2 — Implementation Readiness

**State before sampling:** implementation and deterministic preflight are ready for the protocol-permitted 256-shot dry run. No Stage 2 sample, training job, or final-development sample has been generated. The original `FREEZE.json`, configuration, seed inventory, Stage 1 evidence, and historical runs remain unchanged.

## Frozen protocol retained

The runner reads the frozen `stage2_config.json` and 95-entry seed inventory. It preserves the 260,000 unique-shot ceiling: five roots, two conditions, and 10,000/2,000/2,000/2,000/10,000 shots per root-condition across training, monitor, probability calibration, threshold selection, and final development. Model order, architectures, balanced minibatch schedule, natural-prevalence correction, optimizer, early stopping, temperature grid, threshold grid, primary endpoint, development gate, and resource limits remain unchanged.

The 256-shot diagnostic is taken only from the allocated `dev-root-00` nominal training stream. The runner continues that exact Stim sampler for the remainder of the existing 10,000-shot allocation and checks the prefix against the saved first 256 rows. The diagnostic cannot add shots to the budget.

## Implementation safeguards

- Root partitions are generated once and reused for all three CNNs; per-selection records carry hashes for every shared training/monitor/calibration/threshold array.
- Training, monitor, probability-calibration, and threshold-selection data are separate. The best monitor checkpoint is restored before calibration and threshold selection.
- A global barrier requires all 15 root/model selections and selected-weight hashes to be persisted before any final-development sampler is opened. Each final partition records the full pre-sampling selection manifest.
- Stim samples, JSON status/metadata, NPZ archives, and PyTorch checkpoints use atomic replacement. Checkpoints preserve optimizer, scheduler, training epoch, best weights, history, and RNG states; resume starts from a verified epoch checkpoint.
- Resource checks enforce the frozen six-hour wall, four-hour measured CUDA, 2-GiB free-disk, 3-GiB RSS, and 4-GiB CUDA-allocation limits. CUDA is required; no CPU fallback is allowed.
- A separate auditor rebuilds both matching models; checks all split and final archive hashes, seeds, shapes, labels, matching predictions, training/calibration/threshold selection rules, and paired sample identity; recomputes CNN outputs from frozen weights; and independently derives all logical-error and paired-correction metrics.
- The independent-test allocation remains absent and sealed. No code path samples it.

## Validation performed (no simulation sampling)

Commands:

```powershell
python -m py_compile outputs/cnn_architecture_stage2_v1/run_stage2.py outputs/cnn_architecture_stage2_v1/audit_stage2.py outputs/cnn_architecture_stage2_v1/freeze_stage2_v2.py outputs/cnn_architecture_stage2_v1/tests/test_stage2_runner.py
python -m unittest discover -s outputs/cnn_architecture_stage2_v1/tests -v
python -m unittest discover -s outputs/cnn_architecture_stage1_v1/tests -v
```

Results: Python compilation passed; Stage 2 regression suite **12/12 passed**; Stage 1 architecture suite **6/6 passed**. Stage 2 tests exercise partition/label dimensions, residual XOR, seed uniqueness and split isolation, shared paired inputs, best-state restoration, pre-final selection barrier, deterministic minibatch RNG replay, checkpoint hash rejection, useful/harmful correction accounting, resource-limit rejection, and persisted state behavior. The frozen circuits and DEMs for both conditions construct with 40 detectors and one observable; this test constructs no shots.

## Runtime environment and resource preflight

Verified in the repository environment: Python 3.12.10; PyTorch 2.14.1+cu126; Stim 1.16.0; PyMatching 2.4.0; CUDA 12.6; CUDA available; NVIDIA GeForce RTX 4050 Laptop GPU detected. At preflight, process RSS was 0.544 GiB and free disk was 254.33 GiB. No Python, Pythonw, or TorchRun experiment process was found. Local `main` and `origin/main` were both at `ed52ca3d36ff64eb800d4adc7652b127eb594ad6` before these new changes.

## Remaining gate before full execution

`FREEZE_IMPLEMENTATION_V2.json` must be created and hash-verified before the first sample. Then the runner may sample the allocated 256-shot prefix, benchmark end-to-end costs, and compare the conservative estimate with the frozen caps. Full execution proceeds only if that dry run passes and all resource checks remain satisfied. It stops without reducing the design if the estimate fails, a condition has fewer than 20 unique training residual positives, or any integrity/validation check fails.

## Historical freeze-count reconciliation

The committed original `FREEZE.json` lists four superseded pre-sampling draft hashes. The prior progress note saying three described the immediately preceding draft, not the final committed freeze. The implementation supersession adds the original freeze SHA as a fifth superseded snapshot. This reconciles metadata only; the original freeze and all scientific choices are preserved.
