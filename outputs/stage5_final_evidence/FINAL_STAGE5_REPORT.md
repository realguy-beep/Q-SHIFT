# Q-SHIFT Stage 5 — Final Recovery and Evaluation Report

**Status: COMPLETED.** The authorized recovery finished the frozen Stage 5 simulation and passed the v3.4.4 saved-array audit. The recovery used a separate copy of the failed run, reused its committed samples, and preserved the original failed-run directory.

## Study question and design

Stage 5 evaluated whether detector-only calibration of a PyMatching decoder could improve logical-observable prediction under the project's simulated spatially correlated burst-noise model. The circuit was a Stim rotated surface-code Z-memory circuit, distance 3, five rounds, with 40 detectors and one logical observable. The frozen base gate and measurement probabilities were 0.003; the tested burst probabilities were 0, 0.004, 0.008, 0.012, and 0.016.

Each of the five conditions used 1,210 independent roots. Each root allocated 2,000 calibration shots and 2,500 paired evaluation shots. The fixed nominal PyMatching decoder, detector-profile-adaptive PyMatching decoder, and privileged true-probability reference were evaluated on the same detector and observable samples. The privileged reference receives the generating burst probability and is not deployable.

## Recovery and evidence accounting

The original failed execution stopped after 123 complete prediction archives and one `evaluation_complete` archive lacking the estimated parameter and predictions. The 124 archives contained 558,000 committed calibration/evaluation rows, while the old status counters accounted for 555,500. Recovery copied verified source artifacts to a new directory. It completed the missing root from its saved detector and observable arrays without resampling, then processed the remaining roots with the original frozen seed allocation.

The final recovery contains 6,050 roots and 27,225,000 unique allocated shots: 12,100,000 calibration and 15,125,000 evaluation. It reused the original 558,000 committed rows and generated 26,667,000 new unique samples. The original run remains in `worker_failed` status and its 265-file forensic inventory still matches. No independent-test material was accessed.

## Results

| Burst probability | Fixed PyMatching errors / LER | Profile-adaptive errors / LER | Privileged reference errors / LER | Adaptive − fixed LER |
|---:|---:|---:|---:|---:|
| 0.000 | 14,825 / 0.490083% | 14,837 / 0.490479% | 14,825 / 0.490083% | +0.000397 percentage points |
| 0.004 | 17,558 / 0.580430% | 16,323 / 0.539603% | 16,306 / 0.539041% | −0.040826 percentage points |
| 0.008 | 20,017 / 0.661719% | 16,587 / 0.548331% | 16,562 / 0.547504% | −0.113388 percentage points |
| 0.012 | 22,929 / 0.757983% | 17,039 / 0.563273% | 17,040 / 0.563306% | −0.194711 percentage points |
| 0.016 | 25,063 / 0.828529% | 16,912 / 0.559074% | 16,940 / 0.560000% | −0.269455 percentage points |

Across the four nonzero conditions, the equal-weight LER was 0.707165% for fixed PyMatching, 0.552570% for profile-adaptive PyMatching, and 0.552463% for the privileged reference. The adaptive-minus-fixed primary estimate was −0.00154595, an absolute reduction of 0.154595 percentage points.

## Frozen decisions

The primary Endpoint B upper bound was −0.00152107, below the predeclared −0.0002 practical-benefit boundary; **Endpoint B passed**. Its prespecified central interval was [−0.00157580, −0.00151813]. The separate zero-burst no-harm estimate was +0.00000397, with upper bound +0.00000744 against the +0.0002 harm boundary; **the no-harm gate passed**. All four secondary finite-envelope tests had Holm-adjusted p = 0.00866841. These secondary results are conditional on the six predeclared root-effect families and are not distribution-free. Full details are in [STATISTICAL_DECISIONS.md](STATISTICAL_DECISIONS.md).

## Interpretation

For these simulated conditions and this decoder configuration, detector-profile adaptation improved on the nominal fixed decoder across the four nonzero burst settings and met the frozen primary decision rule while passing the zero-burst no-harm gate. At zero burst, the adaptive decoder had 12 net additional errors (25 adaptive-only versus 13 fixed-only failures), but the measured effect remained inside the predeclared tolerance.

This experiment does not show that adaptive decoding is generally superior, does not compare against every possible static burst-aware decoder, and does not establish a hardware result. The privileged true-probability reference is a comparison arm, not a mathematically optimal decoder. The study models correlated bursts in simulation; it does not demonstrate that real devices have this noise distribution.

## Audit and remaining deviation

The v3.4.4 internal independent auditor verified all 6,050 committed archives, checked the frozen root and seed mapping, recomputed the 27,225,000-shot allocation, reconstructed the detector-profile estimates, and independently re-decoded the saved predictions. A separate post-audit reconciliation matched all 6,050 per-root records and reproduced the frozen statistical output. This was an internal independent implementation, not an external third-party audit.

The historical v3.4.2 raw safety-test JSON remains unrecovered. Its expected SHA-256 is `d191d48d999bf169cbcaa5a9e42fb604e8241f387bee84e19c598402dc319a4c`; the current named v3.4.2 copy hashes to `3d0aa61720a2f7258da661d48163d02bdaba3cc3e22457c97799c69c30b3f64c`. No bytes were fabricated or altered to force a match. The deviation concerns an earlier safety-test output; it did not change the Stage 5 run archives or the completed audit. See [LIMITATIONS.md](LIMITATIONS.md).

The full original `.npz` detector/observable/prediction archives remain local and are intentionally excluded from this publication package. Their committed hashes and the derived per-root audit records are included.
