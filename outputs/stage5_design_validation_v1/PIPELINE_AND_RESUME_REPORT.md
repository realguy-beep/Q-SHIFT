# Stim/PyMatching pipeline benchmark and resume validation

**Purpose:** engineering feasibility only. These are disposable development samples, not Stage 5 evaluation shots and not evidence of adaptive decoding benefit. No independent-test data were accessed.

## Run and audit

- Conditions: p={0,.004,.008,.012,.016}; rotated Z-memory, d=3, r=5; gate and measurement p=.003; Stage 4C frozen detector-profile estimator; fixed, profile-adaptive, and privileged true-p PyMatching arms.
- Allocation: 10 roots/condition; 2,000 calibration shots/root plus 2,500 paired evaluation shots/root; 50 roots, 100,000 calibration + 125,000 evaluation = 225,000 unique disposable shots.
- Seeds: `VALIDATION_SEED_INVENTORY.json`; separate 8.62B benchmark namespace. 4,741 recoverable integer values from the enumerated historical seed metadata were screened, zero collisions. The earlier 8.61B one-shot Stim seed-acceptance fixture is documented separately and was not reused for benchmark sampling.
- Software: Python 3.12.10, NumPy 2.5.3, SciPy 1.18.1, Stim 1.16.0, PyMatching 2.4.0.
- Resume: invocation 1 paused after 7 complete roots (31,500 shots). Invocation 2 resumed and completed all 50 roots (225,000 shots). Before skipping existing roots, the runner checked each file against its durable SHA-256 journal; the first seven hashes remained in the final archive manifest.
- Independent verification: `audit_dynamic.py` independently reconstructed the detector-profile estimate, rebuilt the three matching arms, re-decoded every stored evaluation detector matrix, and checked labels, seeds, dimensions, root coverage, and hashes. Result: PASS, 50/50 roots, 225,000 shots.

## Measured resources

| Measurement | Result |
|---|---:|
| First paused command wall time | 2.595 s |
| Resume/completion command wall time | 3.883 s |
| Combined end-to-end wall time | 6.478 s |
| Runner-internal component timer | 1.781 s (does not include interpreter startup; not used for conservative projection) |
| Conservative measured throughput from combined wall time | 34,733 unique shots/s |
| Peak RSS | 85,737,472 bytes (about 81.8 MiB) |
| Compressed archive bytes, 50 roots | 479,697 bytes; 9,594 bytes/root |
| Projected compressed archives for 1,280 roots | about 12.3 MB |
| Conservative uncompressed detector/label/prediction payload | about 243.2 MB |
| C: free space at check | about 271 GB |

Linear extrapolation from the conservative 6.478 s total for 225k shots projects ~166 seconds (2.8 minutes) for 5.76M shots. This is a local engineering estimate, not an execution guarantee; it omits possible audit cost, machine contention, filesystem differences, and the larger run's distribution of calibrated decoder graphs. The measured RSS is far below 2 GiB, and storage appears ample, but the 5.76M proposal exceeds the v2 2.5M shot ceiling and cannot use its frozen runner unchanged.

The benchmark's small sample count is adequate to exercise all pipeline phases and a checkpoint/resume transition, not to characterize worst-case throughput or all 1,280 future root models. The archived per-root LER values are explicitly engineering outputs and must not be interpreted as Stage 5 evidence.
