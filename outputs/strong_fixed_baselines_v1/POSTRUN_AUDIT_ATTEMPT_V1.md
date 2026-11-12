# Independent audit attempt v1 — failed closed

Command: `python -B audit_saved_run_v2.py --run-dir run_recovery_v5`.

The auditor verified the V14 frozen source/configuration hashes, sample inventories, selection/validation partitions, and the final calibration archive mapping before stopping at its pooled-estimate check. It raised `ValueError: pooled detector-only calibration does not reproduce` before reading the final evaluation archive loop. Thus this attempt did not examine final evaluation observable labels or calculate any final logical-error counts.

Independent recomputation from the 1,200,000 saved calibration detector rows with the separately generated p={0, 0.01, 0.02} template profiles gives `p_pool=0.00804`. The runner's `POOLED_CALIBRATION_FREEZE.json` records `0.00831`. Inspection of the runner source showed it fitted the profile estimator on `(generating_probability, calibration_detectors)` tuples from the final calibration partition, contrary to the frozen protocol's requirement to pass only the concatenated detector matrix to the estimator after fitting on independent templates. This is a confirmed implementation deviation; its physical cause is not inferred from the observed outcome.

No original run archive, prediction, freeze, or Stage 5 artifact was modified. The subsequent protocol-consistent reconstruction is frozen separately in `POSTRUN_RECONSTRUCTION_FREEZE_V1.json` before the final evaluation outcomes are opened. Legacy pooled records remain preserved and will be reported separately.
