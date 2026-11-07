# Fixed-baseline hierarchy

## Definitions

1. **Nominal fixed:** a single model using the nominal physical-noise assumption (for example, the `(0.003, 0.003)` matching model or fixed model 0 in the relevant bank). It is a useful reference but may be weaker than a calibrated fixed model.
2. **Globally calibrated fixed:** a candidate chosen using independent development/calibration data pooled across the declared operating conditions, then kept unchanged for all test conditions.
3. **Calibration-selected fixed:** the study’s strongest eligible fixed candidate under its prespecified calibration objective. In Phase 4C, Stage 1 selected the pooled fixed model on development labels; Stage 2 froze and tested it. This is the primary comparator for adaptive claims.
4. **Minimax fixed:** a single candidate selected to minimize worst-regime development loss. It is fixed at inference and should be reported separately from pooled-average selection.
5. **Correlation-aware fixed:** standard weights with a PyMatching correlation option enabled, compared on identical samples. This is a decoder mechanism ablation; it is not adaptation.
6. **Model-informed / regime-matched:** a decoder selected from the true simulator condition or the known regime. This uses privileged information unless deployment has an equivalent observable signal. It is an informed reference, not an online adaptive policy.
7. **Hindsight oracle:** a model selected after seeing each test shot’s true logical outcome. It is an optimistic diagnostic only and is not an eligible baseline or estimate of deployable performance.

These categories are study-specific. LERs from different distances, circuits, noise laws, or observable conventions are not pooled.

## Which baseline is primary?

For the adaptive-headroom question, the primary fixed baseline is the strongest fixed decoder chosen without test labels. The Phase 4C Stage 1 selection is the cleanest such baseline for the shared Phase 4C experiment. Its Stage 2 paired test gives 12,407 pooled-fixed errors in 1,800,000 shots (LER 0.00689278), compared with 12,435 calibrated errors (LER 0.00690833). The calibrated-minus-pooled difference is +0.00001556 (worse by 28 errors). The root-cluster 95% CI is [-0.00004889, +0.00007667], and the frozen two-sided test gives p=0.66658.

Phase 4A and 4B improvements are real for their stated static calibration versus **nominal** fixed comparison, but those studies did not include the Phase 4C pooled-selected baseline. Therefore their gains do not establish adaptive headroom over the strongest fixed decoder.

## Baseline by experiment

| Study | Eligible fixed comparator | Selection source | Result relevant to this audit |
|---|---|---|---|
| Phase 2A | Global decoder index 1 | Saved calibration arrays | Per-regime calibration also selected index 1 in all 3 regimes; same test predictions/errors. |
| Phase 2B | Basis-specific fixed: X-memory index 0, Z-memory index 2 | Independent calibration within each basis | The regime-conditioned calibration selection returned the same model for every regime within each basis; primary paired effect 0. |
| Phase 4A/4B | Nominal fixed in the respective frozen protocols | Nominal model, with separate detector-marginal calibrated candidate | Calibration improved the measurement-heavy cell, but the reference is weaker than the later pooled-selected fixed decoder. These are static-calibration results. |
| Phase 4C Stage 1/2 | Pooled fixed index selected on Stage 1 development | Logical-label losses on shared Stage 1 development samples; selection frozen before Stage 2 | Primary fixed baseline for current adaptive feasibility. Stage 2 shows no calibrated advantage. |
| Correlation pilot | Pooled uncorrelated PyMatching | Frozen nominal/pooled weights | Correlation-enabled matching reduced equal-stratum LER by 0.0002542, but did not clear the practical margin and harmed two conditions. This is a fixed decoder comparison. |
| Headroom feasibility | Per-bank calibration-selected pooled candidate | Independent calibration arrays | Calibration selections exactly recomputed in all 12 banks. The regime-specialist gate failed across distances. |
| Phase 5 dynamics | Pooled fixed plus nominal/static comparators | Separate development utility data where present | Small exploratory schedules only; no independent confirmatory evidence or matched periodic-recalibration comparison. |

## Fairness qualifications

Calibration sample sizes, template banks, number of candidate models, and selection objectives differ among phases. For example, Phase 4B’s runner generated fresh templates despite a protocol specifying reuse; Phase 4C Stage 2 used fresh templates and saved no calibration arrays. The studies should remain separate. The online-weight pilot did not execute an equal-resource periodic-recalibration comparison that matched syndrome-history access, estimator evaluations, decoder rebuild work, CPU, memory, and activation latency. Therefore it cannot support a claim that online adaptation beats periodic recalibration.

