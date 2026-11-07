# Q-SHIFT Stage 4 — Full Development Protocol

**Status:** frozen before Stage 4 development sampling. This experiment is development evidence only; it is not an independent confirmation and does not authorize access to the sealed test.

## Question

Can a detector-only estimate of the per-round synthetic spatial-burst probability configure Stim/PyMatching so that it reduces paired logical error relative to fixed nominal PyMatching on unseen probabilities, without causing practically important harm when burst probability is zero?

## Mechanism and circuit

Use the existing rotated Z-memory surface-code circuit at distance 3 with five rounds, 40 detectors, one observable, balanced categorical gate noise p=0.003, measurement noise p=0.003, and the fixed synthetic XX event on data qubits (8,10) after each of five `MR` boundaries. The burst probability is the Bernoulli probability at each event location; events are independent between rounds. This is a synthetic stress model, not calibrated hardware crosstalk.

Every decoder DEM uses `decompose_errors=True`, `approximate_disjoint_errors=True`, and PyMatching `enable_correlations=True`. The approximation for categorical `PAULI_CHANNEL_2` remains a modeling limitation. Burst probability changes the five graphlike edge probabilities/weights while detector IDs and observable definitions remain fixed.

## Estimator and leakage boundary

Use the already validated detector-profile estimator in `outputs/stage4_noise_adaptive_feasibility_v1/prototype.py` without modification. It uses 40 detector marginal rates plus five joint detector-pair features from independent profile development batches at p={0, 0.01, 0.02}; piecewise-linear profile interpolation and a fixed 0.00001 probability grid select p-hat. Its inference API accepts calibration detectors only. No CNN is trained.

For each probability/root, estimate p-hat from a separate 2,000-shot calibration detector batch and build the estimated decoder before generating evaluation samples. Evaluation observables are opened only by the scoring code after all three predictions exist. No observable, true p, or event flag enters the estimator. The true p is used only to construct the privileged true-p reference and for retrospective scoring.

## Allocation

Use the exact 79 simulation seeds in the prior proposed Stage 4 seed plan (4,200,000,001–4,200,000,079), plus three new analysis-only RNG seeds (4,200,000,080–4,200,000,082). The sample allocations are:

- Profile development: p={0, 0.01, 0.02}, three independent batches × 2,000 detector-only shots = 18,000.
- Evaluation probabilities: p={0, 0.004, 0.008, 0.012, 0.016}; seven independent roots per probability.
- Per root-condition: 2,000 calibration detector-only shots and 2,500 separate paired evaluation shots.
- Total: 18,000 + 70,000 + 87,500 = **175,500 unique shots**. Hard ceiling: **180,000**.

All allocation seeds are distinct and screened against recoverable Stage 2, Stage 3, Phase 3A, and Stage 4 feasibility metadata. The independent-test allocation is not opened or enumerated; unrecorded RNG use cannot be ruled out.

## Decoder arms

1. **Fixed nominal:** p-burst=0 DEM/PyMatching on every evaluation set. It receives the same calibration data allocation but ignores it.
2. **Detector-estimated:** one p-hat from the independent calibration batch, then a newly built Stim DEM/PyMatching decoder.
3. **Privileged true-p reference:** decoder built with the true generating probability. It is an oracle/model-informed diagnostic, not deployable.

All arms decode the same 2,500 evaluation detector rows and are scored against the same observable labels. Raw per-shot detector, label, prediction, seed, and hash evidence is saved locally. No Stage 2/3 final-development arrays are reused.

## Endpoints and statistics

Let `d[p,r]` be candidate LER minus fixed-nominal LER for probability p and independent root r. Negative favors the estimator-assisted decoder.

- **Primary effect:** equal-weight mean of the four nonzero-probability stratum means (p=0.004, 0.008, 0.012, 0.016). The zero-burst control is excluded from the improvement estimand.
- **Primary uncertainty:** 20,000 regime-stratified root-cluster bootstrap replicates, resampling seven roots within each p stratum; percentile 95% two-sided interval. The bootstrap RNG seed is 4,200,000,080. After drawing the primary interval, this same generator is advanced for the p=0 one-sided upper bound and then for descriptive 95% root-cluster intervals for each nonzero stratum in ascending p order. Percentiles use NumPy's default linear quantile rule. Shot-level resampling is not used for inference.
- **Primary test:** two-sided Monte Carlo sign-flip test over the 28 nonzero root-paired differences, 100,000 assignments, seed 4,200,000,081, plus-one p-value. Signs are flipped independently within p strata; ties count as extreme. This relies on independent roots and approximate symmetry of root-level differences under the null; report the raw roots and CI.
- **Secondary family:** exact two-sided sign-flip tests for each of the four nonzero p strata, enumerating all 2^7 assignments per stratum; Holm correction across the four p-specific tests.
- **Zero-burst control:** one-sided 95% upper bound from the same root-cluster bootstrap for the p=0 assisted-minus-fixed difference. The primary nonzero-strata interval is drawn first; the same bootstrap RNG stream is then advanced to draw the p=0 interval, avoiding reuse/reset of the analysis stream.
- **Estimation:** report signed error, absolute error, root-bootstrap percentile interval, and coverage descriptively. Calibration interval RNG seed 4,200,000,082; 500 resamples per calibration batch. These intervals condition on profile templates and do not include template uncertainty.
- Also report paired errors, LERs, candidate-only/fixed-only failures, prediction disagreements, per-root effects, per-condition effects, decoder construction/inference time, memory, and all hashes.

## Frozen development success gate

The practical margin 0.0002 absolute LER is retained from prior Stage 2/3 development gates, not selected from Stage 4 pilot evaluation labels. The gate is split so a no-burst control is not counted as a favorable burst condition. All conditions below must pass:

1. For nonzero p, pooled probability-estimation MAE ≤0.0025 and absolute mean bias ≤0.0015; within each nonzero p stratum at least 5/7 roots have absolute estimate error ≤0.005.
2. Across the four nonzero strata, primary mean d ≤−0.0002 and the root-cluster 95% CI upper endpoint is below zero.
3. All **4 of 4** nonzero probability strata have mean d<0, and no nonzero stratum has mean harm greater than +0.0002. This conservatively carries forward the prior requirement that at least four strata favor adaptation while preventing the p=0 no-burst control from counting as a favorable burst condition.
4. At p=0, the one-sided 95% root-cluster bootstrap upper bound for mean d is ≤+0.0002.
5. Median estimated-decoder rebuild latency is <1 second and peak process RSS <2 GiB.

PASS means eligible to design a separately frozen independent confirmation. It does not establish superiority or hardware validity. Any failed criterion means FAIL. Missing/corrupt data, seed/sample overlap, prediction mismatch, or leakage means INVALID.

## Resources, stopping, and audit

CPU Stim/PyMatching only; no neural training. Stop at 180,000 unique shots, 1,800 seconds, or 2 GiB process RSS. Check disk space before sampling. Checkpoint profile and each root-condition partition atomically; resume only after hashes and frozen protocol ID verify. The independent auditor rebuilds the profile estimator and all three decoder arms from saved detector arrays and recomputes all counts without importing runner aggregates. Never tune or change a rule after evaluation labels are scored.
