# Q-SHIFT Autonomous Development Readiness

**Readiness: READY FOR EXPLICIT USER AUTHORIZATION. The full experiment has not started.**

## What is prepared

The controller is frozen to compare the flattened position-preserving CNN, balanced MLP, and pooled CNN16 capacity control at nested budgets of 3k, 10k, and 30k training shots per regime. A separate PyMatching-assisted residual CNN uses the 10k/regime prefix and targets `observable XOR PyMatching prediction`. All use the same saved detector/observable samples within each root. PyMatching is the frozen Phase 2B Z-memory baseline.

The experiment is limited to five development roots, three generating regimes, and 50 total model jobs. The split plan is 450,000 training shots plus 300,000 monitoring/calibration/threshold/final-development shots, for 750,000 full-run shots. The final-development stream is sampled and loaded only after a job's checkpoint, calibration temperature, and threshold have been saved. There is no independent-test seed stream or sampling code.

## Preflight and restart verification

- Active freeze: `FREEZE_FINAL_V3.json`, created before any full-run samples; it hashes 20 source/config/protocol files and records the Python/GPU/software environment.
- Seed inventory: 924/924 unique derived seeds; no duplicates, historical collisions, prepared-100K collisions, or Stim-range violations. It screened 2,076 recoverable historical seed values and 397 prepared-100K seed values. Historical coverage is limited to those recorded inventories.
- Circuit preparation checks the frozen Phase 2B regime order, 40-detector/one-observable structure, identical detector coordinates, and 16-shot noiseless behavior per regime.
- Controller tests: 5/5 passed, including seed accounting, prohibited test split, balanced batch counts, residual XOR labels, and checkpoint hash fallback.
- Clean v4 dry run: forced pause after two optimizer batches; resumed to 48 steps; saved detector/observable arrays, selected weights, and paired predictions exactly matched an uninterrupted replay. No test data were generated or accessed.
- Independent readiness audit: all 20 frozen source hashes and all 16 v4 run-manifest file hashes verified; 924/924 seeds are unique; no quarantine files remain in v4; stored predictions were independently rescored and matched all per-regime error/discordance totals.
- Environment: Python 3.12.10 at the path recorded in the freeze; PyTorch 2.14.1+cu126, CUDA available, Stim 1.16.0, PyMatching 2.4.0, NumPy 2.5.3, psutil 7.2.2; NVIDIA GeForce RTX 4050 Laptop GPU.
- Dry-run resource observation: 1.35 GiB process RSS, 0.063 GiB CUDA allocated, and 253.3 GiB free disk. These are observations from the short run, not peak guarantees for every model.

## Dry-run interpretation

The smoke job used 1,024 training shots per regime and 256 shots in each validation role. The persisted resumed fit used 1.15 CUDA seconds. Its tiny final-development partition produced 52 neural errors versus 4 PyMatching errors over 768 paired shots (19/256 X-biased, 24/256 balanced, 9/256 Z-biased; neural positive recall was 0%). This is a plumbing/resume check with only 256 shots per regime, not a model-performance result or a reason to alter the frozen protocol. The uninterrupted replay exactly matched the sample and prediction arrays. The independent recomputation confirms those counts.

Three earlier dry-run directories and freezes are retained as history. They exposed a validator that incorrectly expected final-evaluation fields in the pre-selection archive; those files were quarantined and deterministically regenerated. The corrected v4 dry run completed without quarantine, and its manifest excludes transient lock files.

## Runtime and safety

The frozen hard limits are six active wall-clock hours, four measured CUDA training/validation/inference hours, 2 GiB minimum free disk, 3 GiB process RSS, and 4 GiB CUDA allocation. Progress is checkpointed every ten training batches; checkpoints alternate between SHA-256-verified slots and include model, optimizer, StepLR scheduler, CPU/CUDA/Python/NumPy RNG state, batch order, epoch, and early-stopping state. A valid older slot is used if the newest is corrupted; execution stops if neither is verifiable. Root sample archives and prediction outputs are atomic and hashed.

Estimated full-run duration is **about 1–3 hours** on the frozen RTX 4050 environment. This is an estimate from the dry-run batch timing and the frozen maximum workload of 82,500 optimizer steps plus 750,000 Stim/PyMatching shots; architecture widths and thermal throttling may change it. The hard limits remain active, and the controller will pause at a checkpoint when reached. No scale-up or overnight extension is automatic.

## Decision

**Safe to launch after explicit approval. Not launched here.** A trial-level dry-run result is not evidence that the neural decoder improves on PyMatching. The full output will report root-level paired estimates and uncertainty by model, training size, and regime; it cannot establish confirmatory superiority.
