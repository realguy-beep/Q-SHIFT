# Redesigned research question

## Question

**Under what measurable noise-drift conditions, if any, does a causal syndrome-only estimator that updates a PyMatching model reduce logical-observable error beyond both a calibration-selected pooled fixed decoder and an equally resourced periodic recalibration policy?**

The question concerns the *incremental operational value* of event-driven/continuous model updates, not whether syndrome statistics can estimate noise in principle. That general ability, including sliding-window weight updates, already has substantial prior work (see [LITERATURE_NOVELTY_GAP.md](LITERATURE_NOVELTY_GAP.md)).

## Hypothesis and null

- **H1, bounded:** for at least one predeclared drift family and dwell-time range where the selected model parameters are identifiable, an online update policy reduces paired logical-error rate by at least the frozen practical margin versus the strongest pooled fixed decoder, and also beats the equal-budget periodic recalibration policy after counting warm-up and update costs.
- **H0:** any gain is smaller than the practical margin, does not survive root-level uncertainty, is explained by a stronger static/periodic model, or costs more latency/compute than the prespecified cap.

The hypothesis is conditional on *decoder utility headroom*. A statistically identifiable physical parameter is not useful for decoding if varying it does not change the likelihood ordering of recovery hypotheses or the selected corrections. Conversely, a decoder-relevant weight combination may be estimable even when individual physical parameters are not.

## Deliberate scope

Study one change at a time: this phase would adapt decoder weights while the simulated physical circuit/noise schedule changes. Do not combine RL-driven hardware controls with decoder learning. First use rotated surface-code memory and a specified circuit-level Pauli/depolarizing family; expand to correlated or non-Pauli noise only after the initial estimator and DEM mapping are validated. Evaluate both stationary controls and changing noise, including abrupt steps and gradual drift.

## Novelty boundary

Do not claim a new syndrome estimator, first adaptive decoder, first time-varying matching decoder, or a general decoder improvement. The potentially distinct contribution is a **fair, causal, equal-information/equal-compute comparison** of event-driven online weight updates against a strong pooled fixed baseline and periodic recalibration, with identifiability, uncertainty, end-to-end latency and error-rate consequences reported together. Before pre-registration, check the full methods and supplements of the nearest 2026 papers for this exact comparison. If it is already covered, report no novelty and stop or redesign around a genuinely open technical limitation.

## Estimand

For each independent root/schedule, evaluate the same held-out detector and observable shots under all policies. The primary estimand is the equal-weight mean over frozen dynamic schedule strata of:

`LER(online weight update) − LER(strongest pooled fixed)`.

The periodic baseline is a prespecified key comparator. Report the online-minus-periodic paired effect as a separate co-primary gate or multiplicity-controlled secondary endpoint, as fixed before sampling. Include the entire schedule—including warm-up and delayed transitions—in the operational endpoint; post-transition and settled windows are descriptive secondary views.

No test outcome, label, hidden regime identifier, or future detector sample may alter model estimation or selection. The target is a measured operating envelope, including regimes where adaptation should not be used.
