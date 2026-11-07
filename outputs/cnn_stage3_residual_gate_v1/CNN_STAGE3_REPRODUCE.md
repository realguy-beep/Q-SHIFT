# Reproducing the Q-SHIFT Stage 3 development run

Run commands from the repository root in the already configured Windows Python environment. No dependency installation is part of this protocol.

## Before sampling

```powershell
python -m unittest outputs.cnn_stage3_residual_gate_v1.tests.test_stage3 -v
python outputs/cnn_stage3_residual_gate_v1/freeze_stage3.py --verify
python outputs/cnn_stage3_residual_gate_v1/run_stage3.py --validate-only
```

`--validate-only` builds the frozen circuits and DEMs and exercises the model on synthetic in-memory zeros; it does not sample Stim shots. `FREEZE.json` must verify, CUDA must be available, and the model signature and resource limits must pass before proceeding.

## Execute or resume

```powershell
python outputs/cnn_stage3_residual_gate_v1/run_stage3.py --run
```

For a paused or recoverable interrupted run, inspect `run_v1/raw/status.json`, ensure no process holds `run_v1/raw/runner.lock`, then run:

```powershell
python outputs/cnn_stage3_residual_gate_v1/run_stage3.py --resume
```

The runner reuses committed seed-partition archives. The first 256 burst training rows are the permitted dry run and remain the first 256 rows of the 17,000-shot training allocation. It never samples an independent-test stream. The terminal record and evidence manifest are written only after independent rescoring passes.

## Evidence

After completion, read `CNN_STAGE3_RESULTS.md`, `CNN_STAGE3_RESULTS.json`, `CNN_STAGE3_INDEPENDENT_AUDIT.md`, `CNN_STAGE3_AUDIT_RESULTS.json`, `CNN_STAGE3_PER_ROOT.csv`, and `run_v1/raw/status.json`. Raw partitions, prediction arrays, checkpoints, and the runtime manifest stay local under ignored `run_v1/`.

Do not change `stage3_config.json`, `seed_inventory.json`, thresholds, architectures, or statistical definitions after the prospective freeze. A source/configuration hash mismatch is a stop condition, not an invitation to bypass validation.
