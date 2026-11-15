# Runner deviation and preserved execution history

This document records the original runner defect and the preserved attempts for the strong fixed-baseline development study. It supplements, and does not rewrite, the frozen protocol, freeze JSON files, failed-run records, or final reconstruction report.

## Confirmed deviation

The original pooled-static estimator was fitted with final calibration batches paired to their known generating probabilities. The frozen method required independent template profiles at p=0, .01 and .02, then one estimate from pooled final calibration detector rows only. The saved legacy value was `p=0.00831`. The deviation was detected before final evaluation labels were read by the first audit attempt.

A separate reconstruction protocol was then frozen before the final evaluation outcome audit. It estimated `p=0.00804` from the independent templates and pooled calibration detector rows, without condition tags, observables or event flags. The reconstruction re-decoded all 1.5 million final development shots and passed the numerical verifier. It happened to produce exactly the same predictions as the legacy pooled value. This matching output is not evidence that the method was followed: the calibration implementation still deviated.

## Attempt history

| Attempt | Outcome | Preserved evidence |
|---|---|---|
| Initial run | Reached complete sample generation, but its pooled estimator was label-conditioned contrary to protocol. | `run/`, `PRETEST_FREEZE_V1`–`V14`, `STUDY_FAILURE_V1.md`; all original files retained. |
| Recovery v2 | Stopped on candidate-grid/scorer mismatch. | `run_recovery_v2/`, `BENCHMARK_FAILURE_V2.md`. |
| Recovery v3 | Stopped on Windows status replacement permission failure. | `run_recovery_v3/`, `BENCHMARK_FAILURE_V3.md`. |
| Recovery v4 | Stopped before sampling on JSON numeric-key normalization during copy verification. | `run_recovery_v4/`. |
| Recovery v5 | Completed the frozen development allocations. | `run_recovery_v5/`, 600 evaluation roots and 1.5 million paired evaluation shots. |
| Reconstruction | Independently reconstructed the pooled arm from saved arrays and verified the predictions and aggregates. | `POSTRUN_RECONSTRUCTION_FREEZE_V1.json`, `run_recovery_v5/INDEPENDENT_AUDIT.json`, `POSTRUN_RECONSTRUCTION_VERIFICATION_V1.json`, `report_reconstruction_v1/`. |

The original run folders and result files are not overwritten by this report. Run folders and shot-level NPZ files remain local and ignored by Git.

## Integrity boundaries

- The development experiment did not access Stage 5 evaluation files or generate Stage 5 shots.
- The independent Stage 5 audit materials were absent from this fresh clone but were available in the prior workspace at `outputs/qshift_independent_audit_v1/`. The audit report and its listed hashes were inspected as historical documentation; no Stage 5 raw arrays were read as part of this development analysis. No additional access request was needed because the prior workspace copy was available.
- No confirmatory significance test was run for the new development comparison. Root-bootstrap intervals are descriptive.
- The V14 original pretest freeze and the later reconstruction freeze both remain historical records with separate purposes. The latter does not retroactively repair the former execution.
