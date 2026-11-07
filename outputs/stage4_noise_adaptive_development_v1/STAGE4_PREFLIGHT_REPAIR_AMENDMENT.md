# Stage 4 Preflight Repair Amendment (Before Any Study Sampling)

This amendment records an implementation-only correction after the initial preflight launch attempt and before any profile, calibration, or evaluation shot was generated.

## Failure

Command: `python -m outputs.stage4_noise_adaptive_development_v1.run_stage4 --run`

The runner failed at its disk-space check with:

```text
TypeError: argument 1 must be str, not WindowsPath
```

The exact call was `psutil.disk_usage(RUN_DIR)` in `run_stage4.py::execute`, which reaches `psutil._pswindows.disk_usage`; its Windows extension requires a string path. The process had created the run/profile/root directories and appended the failure to `run_v1/controller.log`, but failed before status initialization or any Stim sampling call. The profile and root checkpoint directories contained no NPZ files. The preserved initial one-line failure log had SHA-256 `c83357ddbef623ade60f154e75b3f18789a1b870b5bcd021439616e4d648fc1d` before retry. The initial frozen protocol/configuration and seed inventory remain unchanged.

## Repair and freeze handling

The runner now calls `psutil.disk_usage(str(RUN_DIR))`. This changes only Windows path compatibility; it does not change circuits, probabilities, estimator features, seeds, allocations, decoders, statistics, gate criteria, or sample ordering.

The original `STAGE4_DEVELOPMENT_FREEZE.json` is preserved as the initial preflight freeze. Because its runner hash predates this fix, the new runner will not treat it as the active freeze. A superseding `STAGE4_DEVELOPMENT_FREEZE_V2.json` will hash the repaired runner and all protocol/configuration/analysis files, record the original freeze hash, and be created before any sampling. The original freeze is therefore superseded for implementation integrity only; the scientific protocol is unchanged.

The failure log is retained as historical preflight evidence. It is not included as an immutable source hash because the controller appends to that runtime log. No sample checkpoint exists from the failed attempt.
