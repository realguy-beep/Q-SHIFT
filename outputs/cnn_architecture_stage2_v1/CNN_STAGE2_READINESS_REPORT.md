# Q-SHIFT CNN Architecture Stage 2 — Readiness Report

## Status

**Protocol and allocation are frozen; execution is NOT READY and was not started.** No Stage 2 training, Stim sampling, final-development evaluation, or independent-test access occurred during this preparation. The 260,000-shot ceiling from the Stage 1 proposal is preserved exactly.

## Repository synchronization

- Local `main` was clean before synchronization; no Python/Pythonw/Uvicorn experiment process was running.
- `git fetch origin main` fetched remote `8608c0a3633826e6dd871dd294a0721902fd918c`.
- Local Stage 1 commit `129b2cea5a3c33f6ef7455e3aa9fca8c679c6b55` and remote commit had identical tree `c9faf85fb0b092c3291b6dd4433cf1ef648256d6`, and both had historical parent `82a32b43ebba400cb588d99b25d978778fc22d5a`.
- Backup branch `backup/local-stage1-129b2cea` preserves the original local commit. `main` is now at the remote commit and tracks `origin/main`.

## Evidence reviewed

Read the Stage 1 architecture audit, improvement design, preflight results, and proposed experiment protocol; inspected the historical residual CNN and its train/monitor/calibration/threshold/final-development logic; inspected the Phase 2B noise generator and Phase 3A burst simulator; reviewed Stage 1 model tests, parameter counts, seed inventory, saved preflight metadata, and manifest. No historical files were edited.

## Frozen items created

- Exact circuit/noise conditions, decoder information access, model order, residual-target convention, partitions, shot counts, seed formula and inventory, calibration and threshold rules, primary endpoint, development-only gate, resource caps, and independent-test prohibition are frozen in `CNN_STAGE2_FROZEN_PROTOCOL.md` and `stage2_config.json`.
- The 95 derived seeds are unique, below the repository's Stim seed maximum, disjoint from 2,076 recoverable historical seed values, nine explicit Phase 3A values, and four Stage 1 diagnostic values. This is a collision screen over available metadata, not proof that every historical RNG use is recoverable.
- `FREEZE.json` contains SHA-256 records for the protocol, readiness report, configuration, inventory/audit, freeze builder, and referenced source/evidence files.
- The prospective freeze is reproducible with `python outputs/cnn_architecture_stage2_v1/build_freeze.py`; it records 23 hashed inputs. Before sampling, any revised freeze records the superseded freeze SHA-256 chain; after any sampling, training, final-development access, or independent-test access, the builder refuses changes.

## Why the run is not ready

There is no Stage 2 training runner in this directory. The current historical trainer does not register both new Stage 1 candidates, and the Stage 1 preflight was deliberately diagnostic-only. No end-to-end Stage 2 path has yet demonstrated that it can generate every split, persist paired data, restore the best checkpoint, select temperature/threshold without reading final-development labels, and independently rescore all predictions. Runtime and sustained throughput for the 15 model/root jobs are therefore unknown. Starting now would be premature and would not meet the frozen evidence standard.

The preflight must also stop before fitting if either condition has fewer than 20 unique residual-positive training cases in a root. Given the historical 0.58% residual-positive prevalence in one audited training sample, class-balanced resampling may repeat rare examples heavily. This risk is frozen as a reporting and stop condition; no top-up or silent reweighting is allowed.

## Non-sampling validation performed

Command:

```powershell
python -m unittest discover -s outputs/cnn_architecture_stage1_v1/tests -v
```

Result: **6/6 tests passed** (actual detector-coordinate mapping, both candidate forward/gradient paths, deterministic initialization, residual/XOR convention, parameter bounds, and input/factory validation). These tests build the fixed circuit and use synthetic tensors; they do not call Stim sampling, train a model, or touch independent-test data. No Stage 1 sample-generating preflight script was rerun.

## Required checks before a separately authorized execution

1. Run `python outputs/cnn_architecture_stage2_v1/build_freeze.py`; require a byte-for-byte matching freeze. If source or protocol hashes differ before sampling, the builder records a superseding SHA-256 chain; stop and review that new freeze instead of starting a run. Seed inventory/audit changes are rejected. After any sampling, training, or evaluation, all freeze changes are rejected.
2. Implement a runner without changing the frozen scientific choices; add tests for label/XOR semantics, geometry, paired sample identity, split isolation, monitor checkpoint restoration, threshold/calibration isolation, atomic outputs, and restart determinism.
3. Conduct deterministic non-sampling checks first. If a sample-based dry run is separately authorized, reuse the first 256 rows from the already allocated root-00 nominal training stream and count/reuse them within its 10,000-shot partition; do not allocate an extra diagnostic stream.
4. Verify actual environment versions and hardware, storage, memory, and elapsed-time estimates; benchmark end-to-end throughput before full sampling.
5. Recompute result counts from saved arrays and produce a manifest. Stop on collisions, insufficient positive cases, invalid labels, resource breach, or any final-development access before selection is frozen.

## Research limits

This is a five-root, distance-3 Z-memory development comparison under one synthetic burst mechanism. The burst-informed matcher is privileged. Stim-to-DEM conversion approximates disjoint categorical errors, and the burst is not hardware-calibrated. A positive gate would motivate a separately frozen independent evaluation; it would not establish adaptive or general decoder superiority.
