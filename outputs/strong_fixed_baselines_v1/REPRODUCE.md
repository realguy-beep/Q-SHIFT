# Reproducing and checking the strong-baseline development study

## Scope

The sampled study is complete. Do not launch `run_development.py` or any recovery runner as a reproduction step: these commands generate samples. The raw NPZ archives and corrected per-shot predictions are local and ignored by Git. The final result is a development reconstruction with a disclosed pooled-calibration deviation, not a confirmatory evaluation.

## Environment recorded with the study

- Python: 3.12 series used by the run
- Stim: 1.16.0
- PyMatching: 2.4.0
- NumPy: 2.5.3
- Circuit: rotated distance-3 Z memory, five rounds, 40 detectors, one observable
- Execution: `run_recovery_v5/status.json` records 600 evaluation roots, 1,500,000 paired evaluation shots and 671.1 seconds. This file is local ignored evidence.

## Safe automated tests

From the repository root:

```powershell
python -m unittest outputs.strong_fixed_baselines_v1.test_experiment -v
```

The completed run passed all 16 tests. These tests exercise deterministic circuit and DEM checks, paired sample identity, candidate-grid order, seed/allocation validation, safety-static selection/fallback, immutable JSON resume handling and the bounded atomic-replacement retry behavior. They do not sample the experiment or access Stage 5.

## Saved-array verification

`POSTRUN_RECONSTRUCTION_VERIFICATION_V1.json` records a successful independent numerical verification of 600 roots and all 1,500,000 evaluation shots, including exact saved prediction bits, aggregate counts, shot-level paired discordances, the 100,000-resample root bootstrap and the p=0 upper bound. The script `verify_reconstruction_outputs_v1.py` re-reads and re-decodes the local archives. Its current implementation writes the verification JSON at a fixed path and would replace that file; therefore, do not run it in place if preserving the exact existing audit output is required. Verify its recorded SHA-256 and the archive manifest instead, or run a separately copied study tree with its local-only archives if an execution replay is needed.

The separate script `audit_saved_run_reconstruction_v1.py` also re-decodes all stored evaluation arrays. The machine-readable audit status is `PASS_WITH_PROTOCOL_DEVIATION_RECONSTRUCTION`. Its console summary in the original run printed a hard-coded `PASS`; use the JSON status field, not that console word. The deviation is explained in `RUNNER_DEVIATION_AND_RESULTS.md` and `FINAL_RESULTS_AND_INTERPRETATION.md`.

## Evidence to inspect

- Frozen method and configuration: `STRONG_BASELINE_PROTOCOL.md`, `experiment_config.json`, `PRETEST_FREEZE_V14.json`.
- Seeds: `seed_inventory.json`.
- Reconstruction protocol and freeze: `POSTRUN_RECONSTRUCTION_PROTOCOL_V1.md`, `POSTRUN_RECONSTRUCTION_FREEZE_V1.json`.
- Independent numerical output: `POSTRUN_RECONSTRUCTION_VERIFICATION_V1.json`.
- Summary: `report_reconstruction_v1/RESULTS.md`, `RESULTS.json`, `PER_CONDITION.csv`, `PER_ROOT.csv`.
- Interpretation and limitation: `FINAL_RESULTS_AND_INTERPRETATION.md`, `RUNNER_DEVIATION_AND_RESULTS.md`.

Do not copy raw arrays into Git or use final development outcomes to tune a later confirmatory method.
