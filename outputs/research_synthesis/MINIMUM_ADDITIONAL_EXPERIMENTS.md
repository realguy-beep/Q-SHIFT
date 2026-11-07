# Minimum additional experiment plan

This is a proposed future protocol, not an authorization to execute. No new simulations were run for this synthesis.

## Question and hypotheses

**Question:** Does a causal detector-only policy lower logical-observable error relative to the strongest fixed decoder selected without final test outcomes when noise changes between circuit-shot blocks?

- **H0:** The reduction is smaller than the predeclared practical margin: adaptive-minus-pooled-fixed is greater than -5% of pooled-fixed LER.
- **H1:** Adaptive-minus-pooled-fixed is at most -5% of pooled-fixed LER. Require the upper endpoint of a two-sided 95% root-cluster interval to be below this margin and a prespecified one-sided cluster test of the margin to pass.
- **Opportunity gate:** Independent calibration must show at least one specialist has stable paired utility beyond calibration uncertainty. If not, stop adaptive testing and conclude that the tested bank has no established headroom.

The 5% margin is a proposal, not derived from current data. Define it against the equal-regime pooled-fixed LER, not by looking at test results. A blinded development pilot must estimate paired root variance and show at least 80% power at the frozen test size. If power is inadequate, change sample size before freeze or stop. A nonsignificant superiority test is not evidence of equivalence; to conclude that the result rules out a practically important benefit, use a separately prespecified equivalence interval and adequate power.

## Circuits and distances

- Use Stim rotated surface-code memory in both X and Z bases at distances **3, 5 and 7**, with rounds **r=d**. Retain a d=3, r=5 bridge cell only as secondary if needed to compare with existing work.
- Verify noiseless output, detector/observable indexing, circuit structure, probability insertion, DEM, and prediction pairing for every circuit.
- Keep logical-frame prediction distinct from applying physical corrections to a state.

## Noise regimes and schedules

Use two separately reported factors. First, native single-/two-qubit depolarizing gate error plus separate measurement/readout error at data-heavy, nominal and measurement-heavy settings. Second, fixed total local nonidentity fault probability with balanced, X-biased and Z-biased X/Y/Z composition plus one held-out intermediate bias. Record gate, data, reset, measurement and final-readout channels separately. Stim should sample categorical channels exactly; any DEM approximation and its consequences must be independently characterized.

Static cells quantify available decoder utility. Dynamic schedules include stationary controls; data-heavy→measurement-heavy and reverse; nominal→measurement-heavy→nominal; randomized piecewise-stationary transitions; and short/long dwell times. Transition times remain hidden from the adaptive algorithm. Decoder for block t may use completed earlier blocks only.

## Baselines

1. Identity/no correction (predict zero logical flip; scoring reference only).
2. Nominal fixed PyMatching.
3. Strongest pooled fixed PyMatching selected on independent development calibration.
4. Static per-regime calibrated PyMatching (known regime; information-rich diagnostic).
5. Causal detector-only adaptive controller with confidence calibration, hysteresis, minimum dwell and pooled-fixed fallback.
6. Hidden-regime and hindsight per-shot oracle diagnostics, explicitly infeasible.
7. Add a channel-faithful or near-ML reference only after validation on tractable examples. Do not call the Phase 2C forest exact.

## Separation and compute envelope

Reserve disjoint streams for templates, calibration, estimator training, development, validation and final test. Save calibration detector/observable arrays and selection traces, as well as final test arrays and predictions. Freeze source, config, seed list, statistical plan and policy before test generation.

Proposed minimum test size: **20 independent roots per distance×memory×schedule family and 30,000 paired test shots/root/cell**, increased up to a prespecified 100,000/root when development error rates require more precision. Do not replace independent roots with more shots. An initial cap of **24 CPU-hours and 20 million test shots** is a planning bound; benchmark d=7 and decoder-bank costs first.

A full static factorial of 3 distances × 2 memories × 3 main conditions × 20 roots × 30,000 shots is 10.8 million shots before dynamic schedules. Stage the work: calibration/utility gate first; freeze only supported candidates; then run a powered primary dynamic study with minimum static controls. If the test cannot fit the cap with adequate power, stop before confirmatory sampling instead of silently reducing conditions.

## Analysis and stopping

- Primary: equal-weight mean over prespecified dynamic schedule strata of (adaptive LER − strongest pooled-fixed LER) on identical shots. Negative favors adaptive. Use a two-sided root-cluster sign-flip or studentized cluster permutation at α=.05; report a schedule-stratified root-bootstrap 95% CI and relative effect.
- Secondary: paired shot-level error discordances/McNemar for three frozen comparator contrasts, Holm corrected. Report decoder disagreement separately from errors.
- Dynamic metrics: regime-estimator calibration/confusion, estimator delay, decoder-switch delay, false switches, censored transitions, switches per schedule and LER by time since transition.
- Resource metrics: decoder throughput and controller overhead separately; memory must include native graph objects and model arrays, not only wrapper objects.
- No unblinded interim efficacy looks, no test-driven model selection, and no post-hoc schedule removal. Stop for circuit/DEM errors, seed collision, leakage, invalid calibration or corrupt evidence. Stop the adaptive branch for futility if independent calibration shows no utility headroom.

## Minimum paper gate

Proceed only with a single preregistered primary question; independent calibration/test; a materially strong fixed baseline; both memories and multiple distances; correct correction semantics; and complete source/data/hash evidence. A null result can be the conclusion, but the design must rule out practically important gains in the stated domain.
