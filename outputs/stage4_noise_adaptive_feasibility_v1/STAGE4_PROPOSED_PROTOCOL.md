# Proposed Stage 4 Development Protocol (Not Executed)

## Research question

For the declared distance-3, five-round Z-memory circuit, can an estimator fitted only on detector summaries use an independent 2,000-shot detector calibration batch to infer an unseen per-round synthetic burst probability well enough that rebuilding PyMatching reduces paired logical error relative to a fixed no-burst PyMatching model?

The hypothesis is limited to this stationary synthetic spatial-burst model. It does not claim time-varying tracking, hardware relevance, or a general adaptive-decoder advantage.

## Proposed allocation and seeds

The proposed full development allocation is capped at **180,000 unique shots** and has not been sampled. `STAGE4_PROPOSED_SEED_PLAN.json` reserves 79 distinct streams in a fresh namespace, 4,200,000,001–4,200,000,079, screened against the recoverable Stage 2, Stage 3, and Phase 3A seed metadata. The screen does not inspect sealed independent-test allocations, so that namespace must be checked against any permitted future allocation record before execution without opening test data.

- Estimator profile development: p `{0.0, 0.01, 0.02}`, three independent 2,000-shot detector-only batches per p (18,000 shots). Known p labels are available only to fit the profile map.
- Evaluation conditions: p `{0.0, 0.004, 0.008, 0.012, 0.016}`, seven independent roots per condition. Each root has a 2,000-shot calibration detector batch and a separate 2,500-shot paired evaluation batch (157,500 shots).
- Total proposed unique allocation: 175,500; hard cap: 180,000. No independent test is allocated by this proposal.

## Decoder arms

1. Fixed nominal PyMatching (p=0) on every condition.
2. Detector-profile-estimator-assisted PyMatching rebuilt from p-hat on each independent root.
3. Optional CNN probability estimator only if a predeclared development gate shows the scalar estimator is decoder-relevant but insufficient; this requires a separate prospective amendment and monitor/calibration separation. It is not part of the current frozen proposal.
4. Privileged true-p PyMatching, labeled oracle/reference only.

Every deployable arm receives the same development profiles and the same per-root calibration detectors; nominal fixed ignores the calibration batch. All arms decode the same evaluation detectors and use the same observable labels for scoring. A fixed probability grid is a sensitivity diagnostic only.

## Partitions and selection

Profile development, per-root calibration, paired evaluation, and any later independent confirmation use disjoint seeds. Profile fitting uses only detectors and known simulation probability labels from the designated profile-development partition. On each evaluation root, the deployed estimator sees only the 2,000 calibration detector rows and freezes p-hat before the 2,500 evaluation rows are decoded. No logical labels enter estimation, parameter selection, or decoder construction. Evaluation labels are opened only for scoring. No Stage 2/3 final-development sample is reused.

No architecture, feature, p range, calibration size, threshold, or analysis choice may be tuned on the paired evaluation labels. Since this is development, results may motivate a later frozen confirmatory protocol but cannot serve as independent confirmation.

## Endpoints and statistics

- Probability estimation: root-specific signed error, absolute error, interval width, and calibration interval coverage; report by p stratum.
- Decoder utility: paired logical error counts, rates, prediction disagreements, assisted-only and fixed-only failures, and LER difference (assisted minus fixed).
- Primary development estimand: equal-weight mean of the five condition-specific mean root-paired LER differences.
- Uncertainty: 20,000 regime-stratified root-cluster bootstrap resamples, resampling seven roots independently within each of the five p strata; 95% percentile interval. Shot-level resampling is not used as inferential replication.
- Test: two-sided root-cluster sign-flip Monte Carlo test, 100,000 assignments, applied to root paired differences after equal-stratum weighting. This relies on independent roots and approximate sign symmetry under the null; show raw root effects and do not interpret a p-value alone as practical value.
- Secondary comparisons: assisted versus privileged true-p and the five stratum-specific assisted-minus-fixed effects. Use Holm correction for the five stratum-specific comparisons; label them secondary.

## Prespecified development gate

Proceed to designing a fresh confirmatory study only if all hold:

1. On unseen nonzero p strata, estimator MAE ≤0.0025 absolute probability and absolute pooled bias ≤0.0015; each reported stratum has at least 5/7 estimates within 0.005 of its generating p.
2. Equal-stratum assisted-minus-fixed LER is ≤−0.0002, and the root-cluster 95% interval upper bound is below zero.
3. At least four of five p strata favor estimator-assisted matching; no stratum has a mean harm above +0.0002.
4. Median decoder reconstruction latency is <1 second on the reference CPU and peak process RSS stays below 2 GiB.

Failure of this gate means no useful estimator-assisted opportunity was established under the tested model; do not add a CNN or expand sampling to chase a favorable outcome. Passing is development evidence only and does not authorize test access.

## Resources and audit

Reference target: the existing Windows RTX 4050 laptop, but this protocol uses Stim/PyMatching on CPU and no neural training. Maximum wall time 30 minutes, RAM 2 GiB, unique shots 180,000. The runner must persist partition seed/hash/shape metadata and predictions; an independent scorer must rebuild each DEM/decoder and recompute paired counts from saved arrays. Freeze source/configuration/protocol/seed/statistical code before sampling. Stop on seed collisions, detector/observable shape changes, invalid DEM records, unmatched paired samples, resource breaches, or any evidence of label access in the estimator path.

This is a draft development plan. It is not an authorization to execute the full 180,000-shot Stage 4 experiment.
