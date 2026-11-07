# Stage 4 Feasibility Pilot Findings

**Scope:** 48,000-shot development-only detector-identifiability and decoder-rebuild pilot. This is not the full Stage 4 study and not confirmatory evidence.

## Audit

Independent saved-array audit: **PASS**; all 48,000 shots, six roots, estimator values, decoder predictions, and paired residual counts were recomputed. The independent test was not enumerated or accessed.

## Detector-only burst-probability estimation

Estimator templates used p=0.002, 0.010, 0.018. Evaluation probabilities 0.006 and 0.014 were not template knots and used independent calibration/evaluation seeds. Per-root calibration-batch bootstrap intervals condition on the fitted template profile and are diagnostic only.

| Generating p (analysis only) | Roots | Calibration shots | Paired evaluation shots | Mean p-hat | MAE | Bias | 95% calibration intervals covering p |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.006 | 3 | 6,000 | 12,000 | 0.00559 | 0.00050 | -0.00041 | 3/3 |
| 0.014 | 3 | 6,000 | 12,000 | 0.01334 | 0.00086 | -0.00066 | 3/3 |

## Paired decoder feasibility (descriptive)

The estimator-assisted arm and fixed nominal PyMatching decoded identical held-out arrays within each root. True p was used only to build the privileged reference and for offline error scoring.

| True p | Decoder | Errors / shots | LER | Assisted-minus-fixed LER | Candidate-only / fixed-only | Prediction disagreements | Root paired differences | Descriptive root t interval |
|---:|---|---:|---:|---:|---:|---:|---|---|
| 0.006 | Fixed nominal | 74/12,000 | 0.006167 | — | — | — | — | — |
| 0.006 | Detector-estimated model | 63/12,000 | 0.005250 | -0.000917 | 3/14 | 17 | [-0.001, -0.001, -0.00075] | [-0.001275225, -0.0005581083333333332] |
| 0.006 | Privileged true-p model | 62/12,000 | 0.005167 | diagnostic only | see audit JSON | — | — | — |
| 0.014 | Fixed nominal | 102/12,000 | 0.008500 | — | — | — | — | — |
| 0.014 | Detector-estimated model | 70/12,000 | 0.005833 | -0.002667 | 9/41 | 50 | [-0.00275, -0.003, -0.00225] | [-0.0036153228471764677, -0.0017180104861568653] |
| 0.014 | Privileged true-p model | 72/12,000 | 0.006000 | diagnostic only | see audit JSON | — | — | — |

These rates suggest that the detector profiles contain information about the held-out burst probability and that rebuilding matching at the estimate can change useful corrections. All six calibration bootstrap intervals cover the corresponding true p, but the intervals for the two p strata overlap; with only three roots per stratum this is suggestive, not a reliable separation test. The root-level LER intervals are also descriptive and unstable with df=2. The counts are a feasibility signal, not evidence of statistical superiority or generalization beyond the simulator. The true-p matcher is not a guaranteed performance lower bound: the hindsight mismatch grid at assumed p=0.010 had 58 errors versus 62 for true p=0.006, and assumed p=0.018 had 69 versus 72 for true p=0.014. This may reflect finite-distance/DEM approximation effects and shot variability; it shows that recovering physical p and minimizing matching LER are distinct objectives. The mismatch grid is not a deployable selection policy.

## Parameter-mismatch sensitivity

The following grid is an offline diagnostic; it uses assumed p values selected by the analyst, not an inference-time rule. Lower LER is not a calibrated estimate of a general optimum.

| Assumed p in matcher | LER at true p=0.006 | LER at true p=0.014 |
|---:|---:|---:|
| 0.0 | 0.006167 (74/12000) | 0.008500 (102/12000) |
| 0.002 | 0.005833 (70/12000) | 0.006833 (82/12000) |
| 0.006 | 0.005167 (62/12000) | 0.006250 (75/12000) |
| 0.01 | 0.004833 (58/12000) | 0.006000 (72/12000) |
| 0.014 | 0.004917 (59/12000) | 0.006000 (72/12000) |
| 0.018 | 0.004917 (59/12000) | 0.005750 (69/12000) |

## Compute and limits

The frozen pilot completed in 9.19 seconds in the installed CPU Stim/PyMatching environment. DEM records preserve 40 detectors and one observable across p; the five burst edges have error probabilities equal to p and weights `log((1-p)/p)`. Decoder construction is an explicit Stim DEM rebuild followed by PyMatching construction.

The proposed Stage 4 CNN estimator was not implemented: for one scalar noise parameter with fixed event geometry, the profile estimator is a more interpretable baseline. Reconsider a CNN only if a larger development study identifies a decoder-relevant deficiency in the scalar estimator.

## Recommendation

**CONDITIONAL GO for designing a bounded Stage 4 development study; NO authorization to execute it yet.** The pilot supports detector-level identifiability over two unseen probabilities and demonstrates valid decoder reconstruction, but small root counts, synthetic-noise assumptions, template uncertainty, and the very small pilot prevent a superiority claim. Before the 180,000-shot proposal, preflight estimation precision and rebuild costs using the frozen rules, and check its proposed seed namespace against any permitted future allocation records without opening sealed test material.
