# Phase 4A results

Status: **completed**.

Shot counts: `{'template': 450000, 'calibration': 400000, 'validation': 200000, 'test': 600000, 'noiseless_diagnostic': 256}`. Wall time 1.64 s; peak process memory 133.5 MiB.

Failures/stopping reasons: []

## Validation

| Condition | Shots | Raw | Fixed | Calibrated | Informed | Calibrated difference | Exact paired p |
|---|---:|---:|---:|---:|---:|---:|---:|
| measurement_heavy | 200000 | 6995 | 378 | 326 | 326 | -52 | 9.32258e-07 |

All rates, Wilson intervals, paired intervals, seed-bootstrap intervals, per-seed counts and secondary adjusted p-values (test only) are preserved in RESULTS.json. Validation outcomes are screening evidence, not independent confirmation.

## Test

| Condition | Shots | Raw | Fixed | Calibrated | Informed | Calibrated difference | Exact paired p |
|---|---:|---:|---:|---:|---:|---:|---:|
| measurement_heavy | 600000 | 21275 | 1165 | 1008 | 1008 | -157 | 3.73072e-17 |

All rates, Wilson intervals, paired intervals, seed-bootstrap intervals, per-seed counts and secondary adjusted p-values (test only) are preserved in RESULTS.json. Validation outcomes are screening evidence, not independent confirmation.

## Runtime boundaries

{
  "sampling_seconds": 0.09989439999935712,
  "decoding_seconds": {
    "fixed": 0.17409480000060285,
    "calibrated": 0.15262710000024526,
    "model_informed": 0.15079469999727735
  },
  "fit_seconds": 0.01792950000071869,
  "model_build_seconds": 0.15982100000019273
}

Decode times include all validation/test decoding for each model. Divide by the total completed validation/test shots for batched seconds/shot; this is not hardware latency. Calibration overhead is separately recorded. Model construction precedes fitting; specialists select from nine prebuilt models. Peak process working set includes Python and native allocations, but is not per-model memory.

Primary success gate: True.
