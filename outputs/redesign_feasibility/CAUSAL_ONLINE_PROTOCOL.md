# Causal online-calibration protocol

This is a prospective design only. No simulations or new samples were run.

## Unit of adaptation and information boundary

Use a **block** as a fixed, predeclared batch of independent memory-circuit shots under a slowly changing operating condition. For an initial software pilot, use **256 complete shots per block**, matching the existing Phase 5E schedule batching; this is an experimental unit, not 256 hardware QEC rounds. The simulator may change the generating noise parameters between blocks; within each shot's circuit they remain fixed in this first study. This represents drift between repeated executions. It does not claim to simulate within-shot mid-circuit drift. The current Q-SHIFT generator builds static circuits per regime, so within-circuit drift would require a separate circuit-construction and validation extension.

For block `t`, freeze the decoder before any detector from `t` is read. After each completed block, update sufficient statistics from the trailing `W` complete blocks, where the development-only window candidates are **W ∈ {4, 8, 16} blocks** (1,024, 2,048, or 4,096 detector/observable shots at the above block size). Select one window on independent development roots and freeze it. The estimator checks for a change at every block boundary; the online controller may activate at most one reconstructed decoder per four blocks, with an update budget no greater than the periodic baseline. Any accepted update is used starting at the next block. Model-version timestamps, data cutoffs, update completion times and the decoder used per block must be saved.

Permitted online inputs: completed earlier detector vectors and any predeclared runtime telemetry that would actually be available on deployment hardware. The primary condition is detector-only. Forbidden inputs: generating-regime labels, simulator parameters, observables/logical outcomes, decoder failures defined from those labels, future blocks, and calibration/test identifiers that leak conditions.

## Estimation and model update

1. Define a parameterized physical noise family in advance, with explicit parameter-to-gate/readout insertion maps and a fixed circuit topology. Treat physical parameters as latent truth in simulation and keep them out of the estimator API.
2. From the most recent `W` completed detector rounds/blocks, compute the established local syndrome-correlation sufficient statistics used by a validated estimator, or use a published likelihood/Bayesian estimator matched to the actual noise family. Do not use the current Phase 4/5 per-detector Bernoulli marginals as if they identified all DEM parameters; they are composite marginal scores and discard cross-detector structure.
3. Produce parameter estimates with uncertainty, including covariance or posterior intervals. Map those estimates through the same channel-to-DEM conversion used to construct the candidate decoder. Convert independent graphlike mechanism probabilities to matching log-odds using the documented convention; explicitly handle merged mechanisms, boundaries and correlated fault hints. Do not estimate one edge weight and silently leave related probabilities or correlation metadata at stale values.
4. Accept an update only if (a) the observation model is identifiable/well-conditioned in its decoder-relevant directions, (b) a **95% simultaneous interval** for each decoder-relevant changed parameter/weight excludes its currently active value in the same direction on **two consecutive boundary checks**, and (c) the candidate model remains within structural validity checks. Calibrate interval coverage and false-alarm frequency on independent stationary development roots. Apply bounded weight steps and a four-block minimum dwell/update interval to prevent noise-driven oscillation. Otherwise retain the pooled-fixed model.
5. Construct the new decoder as an immutable model version, validate graph schema and fault IDs, then atomically swap it at a block boundary. Never mutate a graph while any batch is being decoded.

The exact estimator, window, confidence test, cadence and thresholds must be selected on development-only streams, then frozen. The nearest published starting points are [Spitz et al. (2018)](https://doi.org/10.1002/qute.201800012) and [Bhardwaj et al. (2026)](https://doi.org/10.1103/z1hc-nqw5); this proposal does not claim a new estimator.

## Noise schedule and controls

Keep detector extraction, memory basis, circuit structure and shot evaluation paired across decoder policies. Include stationary conditions; abrupt changes in both directions; gradual ramps/drift; and return-to-earlier-condition schedules. Choose schedule dwell times spanning shorter than, comparable to and longer than the estimator's calibration window, using development-only latency/variance to set actual values. Keep schedule boundaries hidden from the estimator and controller. Record simulator state for analysis only.

Distinguish **physical drift** (which changes the sampled circuit channel) from **decoder updates** (which change only the classical inference graph). Do not let decoder choices alter the generated sample or noise. If a future hardware-control experiment changes physical operation parameters, it is a separate intervention with a different paired-design limitation.

## Calibration uncertainty and latency

Measure estimation bias, interval coverage and tracking lag against hidden simulator truth only after predictions are frozen. Report estimator detection delay separately from decoder activation delay. Once the estimator has accumulated enough evidence and accepted a change after completed block `t`, activation may occur no earlier than `t+1`; require estimator plus graph construction to finish before that next block deadline. The end-to-end criterion is **p95 update completion within one 256-shot block duration after an accepted change**. Report the longer data-acquisition delay separately. Transitions not followed by a correct update before the schedule ends are censored, not dropped. If dwell periods shorter than the W window cannot be tracked, that is a feasibility limit and must remain in the primary full-schedule score.

Count window acquisition in shots/rounds, estimator CPU, graph/DEM reconstruction, memory, queue time and decoding. A decoder update may not defer a test block beyond its declared decision deadline. Specify a target block duration for simulation timing; a real hardware deadline cannot be certified without a named platform and cycle-time budget.

## Separation and audit trail

Use disjoint template, development, policy-selection, validation and final-evaluation roots. Calibration and online histories contain detector arrays only for selection. Save raw detector arrays, observable labels and all comparator predictions for paired evaluation; the controller process should not have observable-label access. Freeze code, dependency versions, seeds, thresholds, update rules and primary endpoint before final samples. Save the estimator input cutoffs and selected model version for every block.
