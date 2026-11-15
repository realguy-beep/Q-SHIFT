# Correlated decoder feasibility pilot protocol — frozen candidate

**Status:** prospective development-only pilot. No independent confirmation, Stage 5 use, hardware validation or superiority claim is authorized by this protocol.

## Hypothesis

For the specified synthetic per-round three-data-qubit common-cause burst, the five-factor enumeration decoder B can use detector-only calibration to reduce logical error relative to the pooled-fixed PyMatching baseline A, while preserving the zero-burst safety condition. The proposal is motivated by deterministic three-detector event support and decoder decision differences on constructed valid syndromes; neither finding predicts an LER benefit.

## Frozen noise and decoder arms

Use the single candidate in `MATHEMATICAL_MODEL.md`: balanced rotated Z-memory, distance 3, five rounds, gate and measurement probabilities 0.003, with independent `CORRELATED_ERROR(q) X8 X12 X15` events after each `MR` boundary. Conditions are `q={0,0.01,0.02}`.

Arms are A pooled-fixed PyMatching, A2 per-root profile PyMatching, B per-root calibrated five-factor enumeration with background PyMatching, and C privileged true-q five-factor enumeration. A is the primary comparator; A2 separates parameter adaptation from representation changes; C is a privileged reference. All arms receive byte-identical evaluation detector arrays. No decoder receives observable labels.

The detector-only estimator is fixed before sampling: fit an affine map from mean five-triple-cofire rate to q using only 1,000 training detector rows at each of the three q settings and their known simulation parameters. At inference it receives only one calibration batch's detector bits. Clip estimates to `[0,0.02]`. No hyperparameter search or evaluation-set selection is performed. A uses one estimator fitted on training data and applies it once to all 15,000 calibration detector rows pooled across all three conditions, producing a single q and one fixed PyMatching model for every evaluation condition. A2 and B use the same matched root-specific 500-row calibration batch to produce q-hat for that root. Thus A receives more pooled calibration observations for its single global profile; A2 and B receive identical per-root information. C alone sees true q.

## Allocation and pairing

- Training: 1,000 shots at each of three q values = 3,000.
- Calibration: 500 detector-only shots per root, 10 roots per q, three q values = 15,000.
- Evaluation: 2,000 paired shots per root, 10 roots per q, three q values = 60,000.
- Total maximum: 78,000 unique Stim shots, 63 sampler calls.
- Training, calibration and evaluation use separate deterministic seed domains. Each root's calibration and evaluation seeds differ. A new seed inventory is screened against the prior V1 development inventory only; no Stage 5 seed or content is read.
- Each evaluation circuit/root is sampled once. The resulting detector rows are passed unchanged to A, A2, B and C. Prediction arrays are completed before the paired scorer reads evaluation observables.

If training produces a nonpositive fitted q slope, or calibration mean estimates are not ordered `q=0 < 0.01 < 0.02`, stop before evaluation sampling and report a failed feasibility gate. Do not alter the model, conditions or seeds after observing calibration.

## Endpoints and inference

Primary estimand: equal-weight mean across `q=0.01` and `q=0.02` of root-paired `LER(B)-LER(A)`. Negative favors B. Use 20,000 root-stratified paired bootstrap replicates, resampling the ten root clusters with replacement within each q condition, equal-weighting the two condition means, and reporting a two-sided percentile 95% interval. Ten roots per condition are few; the percentile interval is exploratory and may have poor small-cluster coverage. The bootstrap RNG seeds are frozen in `seed_inventory.json`; quantiles use NumPy method `linear`.

Zero-burst safety: at `q=0`, report the one-sided 95th bootstrap percentile for `LER(B)-LER(A)` against the +0.0005 no-harm tolerance. Also report per-condition root results, paired disagreements, B-only/A-only errors, estimator bias/MAE, A2 contrasts, and C oracle results. A2/C and each single-condition result are secondary/descriptive; no multiplicity-adjusted confirmatory claim is made.

Decision labels:

- **GO (development evidence only):** A has at least 100 logical errors pooled over nonzero conditions; the primary 95% interval is entirely below zero; B has a lower point LER than A in both nonzero conditions; and the q=0 one-sided upper bound is below +0.0005. Relative reduction is reported but no 50% effect is promised.
- **NO-GO:** the primary 95% interval is entirely at or above zero, or the q=0 one-sided lower bound exceeds +0.0005.
- **INCONCLUSIVE:** all other cases, including fewer than 100 A errors, an interval crossing zero, calibration gate failure, or incomplete data.

No outcome permits automatic follow-up sampling or a confirmatory claim.

## Execution and stopping controls

Maximum 600 seconds end-to-end, 2 GiB sampled current-RSS high-water (a measurement, not a hard OS limit), 256 MiB generated artifacts, and at least 1 GiB free disk. Check time/resources before and after each sampler call, root job, artifact commit and analysis stage; preserve partial state and stop on any cap, hash, shape, seed, pairing or completeness failure. No automatic retry or seed substitution.

Before the first sampler call, freeze the exact source/protocol/config/seed hashes in `PRETEST_FREEZE.json`, commit that freeze and source on this isolated branch, verify the checkout is clean, then invoke the runner with the exact resulting commit SHA. The runner checks the explicit SHA and all frozen file hashes. The execution records the resulting commit separately; the freeze does not contain its own commit SHA. Raw shot archives remain local/ignored. This pilot does not read Stage 5 or any sealed outcome.
