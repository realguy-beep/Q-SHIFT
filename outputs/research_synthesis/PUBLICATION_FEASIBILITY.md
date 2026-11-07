# Publication feasibility decision

## Decision

**Additional experiments are required before a novel research paper is defensible.** The repository supports an honest project synopsis and a pilot/negative-results manuscript draft, but it does not yet establish a novel adaptive-decoding method or reliable adaptive improvement over conventional decoding. Continue only with a narrower benchmark question and independent experiments.

## What the current evidence does support

1. A working Stim/PyMatching simulation and paired-evaluation framework, including circuit checks, seed separation, saved predictions and independent prediction re-decoding.
2. Negative evidence that regime recognition alone does not yield decoder utility: Phase 1 recognizes regimes but guarded lookup adaptation does not switch; Phases 2A/2B choose the same model across generating regimes; Phase 4C shows no improvement over a stronger pooled fixed baseline; the audited Phase 5 prototype falls back and ties pooled fixed.
3. A conditional static-calibration result: for the specified measurement-heavy distance-3 circuit, calibrated matching beats nominal fixed matching in Phase 4A and Phase 4B. Phase 4B had a template-protocol deviation, and neither result is adaptive.
4. A basis-dependent fixed-model choice under Phase 2B Pauli bias that merits broader testing.

These results are useful, but novelty must be assessed against existing adaptive, biased-noise, calibrated, correlated and learned decoders, not only a nominal matching baseline.

## Recommended paper scope

**Working direction:** *Calibration headroom and causal decoder selection under changing surface-code noise: a multi-distance benchmark.*

Test the conditional hypothesis that detector-only adaptation helps only when independent calibration shows reproducible specialist utility differences large enough to exceed estimator uncertainty, transition delay and switching cost. A null finding could be publishable if a powered, multi-distance design rules out practically important gains within an explicit domain.

Primary endpoint: adaptive minus strongest development-selected pooled fixed LER on paired held-out dynamic schedules. Keep nominal fixed, static per-regime selection, identity/no-flip, and hidden-state or hindsight oracles as secondary/contextual comparators. The oracle is not deployable. Freeze policy and analysis before test.

## Publication risks

- **Novelty: high risk.** Noise-aware adaptation, calibrated matching, biased-noise tailoring and learned decoders are established. A precise added contribution is required.
- **External validity: high risk.** Most adaptation studies are distance-3 synthetic simulations.
- **Effect: high risk.** Stronger pooled fixed matching removes the calibration gain in Phase 4C; adaptive results are null or schedule-dependent.
- **Provenance: moderate risk.** Phase 4B used fresh templates against protocol text; Phase 4C lacks calibration arrays and used prospective RNG amendments; Phase 2C's first seed inventory omitted derived estimator seeds. Independent audits help but do not make every protocol claim equally strong.
- **Scope: high risk.** Combining repetition-code lookup tests, surface-code matching, Pauli channels, RF surrogates and adaptive schedules without one causal question would read as a project log.
- **Hardware: no claim available.** There is no hardware integration, latency measurement or on-device control.

## Recommendation

Proceed only toward a **new, narrowly scoped benchmark study** after the minimum plan is executed. Do not submit an adaptive-superiority paper based on current results. If multi-distance evaluation and a fresh frozen dynamic test are not feasible, publish a transparent technical/educational prototype report with narrow claims rather than assert a new decoder method.
