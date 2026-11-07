# Post-run CSV export recovery

All 30 fits completed and `results.json`, best-checkpoint files, detector/observable arrays, and per-shot prediction archives were written. The runner then raised `KeyError: 'paired_ler_difference'` in its final `write_csv` step because that derived value was not a top-level field in its result rows. The run's model results were not lost.

The header-only output was preserved as `RUNNER_PARTIAL_PER_ROOT.csv`. `audit_saved_run.py` independently reloaded and rescored the saved checkpoints on the saved threshold-validation samples, verified the calibration and threshold choices, checked prediction/sample alignment, and reconstructed all CSVs and the report. It did not regenerate Stim shots or alter the frozen `results.json`, raw data, prediction arrays, checkpoints, configuration, seed inventory, or pre-sampling freeze.

The exact pre-sampling runner was copied to `run_experiment_frozen.py` and verified against the hash in `freeze.json`. The current `run_experiment.py` received a documented post-run, export-only fix adding the missing paired-difference field; the unified diff and before/after hashes are recorded in `REPORTING_ONLY_DIFF.txt` and `POSTRUN_REPORTING_PATCH.json`. The independent audit verifies the frozen snapshot and this post-run patch. Sampling, model fitting, checkpoint selection, and historical outputs were not changed.
