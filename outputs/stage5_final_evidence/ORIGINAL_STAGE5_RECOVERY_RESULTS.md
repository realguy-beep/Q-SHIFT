# Q-SHIFT Stage 5 recovery results

**Status: COMPLETED — independent audit passed.** The recovery used the audited v3.4.4 copy workflow. The original failed run was preserved; its 124 committed archives were copied and reused, including root 123's committed calibration/evaluation arrays, without resampling.

- Roots: 6,050/6,050; unique allocated shots: 27,225,000.
- Calibration/evaluation shots: 12,100,000 / 15,125,000.
- Cumulative worker/aggregation time: 1519.781s; total supervisor time through independent audit and finalization: 1595.516s.
- Independent test access: 0.

## Primary Endpoint B

Equal-weight mean of the four nonzero-condition root-paired adaptive-minus-fixed LER differences.

- Fixed equal-weight nonzero LER: 0.00707165.
- Profile-adaptive equal-weight nonzero LER: 0.00552570.
- Privileged oracle/reference equal-weight nonzero LER: 0.00552463.
- Difference: -0.00154595; standard error 0.00001396.
- Frozen practical boundary: -0.00020000; calibrated one-sided upper bound -0.00152107; candidate central interval [-0.001575796174072954, -0.0015181269300308198].
- Endpoint B: **PASS** (upper bound is below the frozen boundary).

## Per-condition results

| Burst probability | Fixed errors / LER | Adaptive errors / LER | Oracle errors / LER | Adaptive − fixed | Simultaneous upper bound | Adaptive-only / fixed-only failures | Holm-adjusted p |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.000 | 14,825 / 0.490083% | 14,837 / 0.490479% | 14,825 / 0.490083% | +0.000397% | — | 25 / 13 | — |
| 0.004 | 17,558 / 0.580430% | 16,323 / 0.539603% | 16,306 / 0.539041% | -0.040826% | -0.00036368 | 701 / 1,936 | 0.00866841 |
| 0.008 | 20,017 / 0.661719% | 16,587 / 0.548331% | 16,562 / 0.547504% | -0.113388% | -0.00106631 | 1,467 / 4,897 | 0.00866841 |
| 0.012 | 22,929 / 0.757983% | 17,039 / 0.563273% | 17,040 / 0.563306% | -0.194711% | -0.00186466 | 1,514 / 7,404 | 0.00866841 |
| 0.016 | 25,063 / 0.828529% | 16,912 / 0.559074% | 16,940 / 0.560000% | -0.269455% | -0.00260046 | 1,626 / 9,777 | 0.00866841 |

## Zero-noise no-harm gate

Fixed LER 0.490083%; adaptive LER 0.490479%; difference +0.00000397; one-sided upper bound 0.00000744; boundary +0.00020000. **PASS**.

## Secondary family and audit

All four prespecified nonzero-condition finite-envelope tests have Holm-adjusted p = 0.00866841; each is below 0.05. The familywise procedure is conditional on the six frozen root-effect distributions and is not distribution-free.
The v3.4.4 auditor verified 6,050 checkpoint/archive hashes, re-decoded all saved predictions, and recomputed 27,225,000 unique shots. The post-audit reconciliation matched all 6,050 per-root rows and reproduced the frozen summary statistics.

## Interpretation and limitations

Under this frozen simulation study, detector-profile-adaptive PyMatching met Endpoint B and the separate zero-noise no-harm gate. This is evidence for these simulated conditions and decoder configurations; it is not a hardware result or a universal claim. The privileged decoder uses true burst probability and is an upper-reference arm, not a deployable policy.

The recovery reused the original 558,000 committed shot rows and generated 26,667,000 new unique samples. Root 123 reused its 2,000 calibration and 2,500 evaluation rows with zero new samples. The original Stage 5 run remains unchanged at `worker_failed`. The unresolved v3.4.2 safety-test JSON hash deviation remains documented (expected `d191d48d…`; current named copy `3d0aa617…`); it was not recreated or overwritten. No additional recovery was attempted after this completed run.

## Evidence paths

- Recovery run: `outputs/stage5_secondary_inference_repair_v1/run_recovery_v3_4_4/`.
- Runner status and recovery journal: `status.json`, `RECOVERY_JOURNAL_V44.json`.
- Independent archive/prediction audit: `INDEPENDENT_AUDIT.json`.
- Runner results: `roots/RUNNER_SUMMARY.json`.
- Root hash inventories: `ROOT_ARCHIVE_MANIFEST.json`, `FINALIZATION_MANIFEST.json`.
- Post-audit results: `outputs/stage5_recovery_execution_v1/RESULTS.json`.
- Reproducible reconciliation: `outputs/stage5_recovery_execution_v1/verify_and_report.py`.
