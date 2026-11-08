# Stage 5 allocation validation v3 — 1,210 roots per condition

**Status:** prospective statistical-design validation only. This does not amend or supersede the frozen Stage 5 v2 protocol, authorize Stage 5 sampling, access sealed evaluation data, or generate Stim shots. The Stage 5 final decision memo is prior evidence and is not repeated here.

## Question and allocation

Validate the proposed Endpoint B allocation of 1,210 independent roots in each of five conditions (p=0 and four nonzero burst probabilities). If eventually authorized under a new protocol, each root would have 2,000 detector-only calibration shots and 2,500 separate paired evaluation shots: 27,225,000 total shots. The only samples generated in this directory are synthetic root-level statistical effects used to evaluate inference operating characteristics.

The primary estimand remains the equally weighted mean of the four nonzero condition means of root-level paired adaptive-minus-fixed LER differences. The practical boundary is −0.0002 and the planning alternative is −0.0003. No effect, endpoint, alpha, or acceptance rule is changed.

## Inference method under review

For four independent condition strata, each with n root-paired differences, use the equal-weight estimator and studentize with \(\widehat V=\sum_{j=1}^4 s_j^2/(16n)\). The one-sided rejection rule at the practical boundary is `T < -c`, where `c` is the maximum, across the prespecified null envelope, of the empirical 0.952 quantile of `-T` from a separate 100,000-replicate calibration stream per scenario. Central interval lower and upper critical values use the envelope maxima of the 0.976 quantiles of `-T` and `T`. Critical values are fixed before independent null validation and power streams are evaluated.

The p=0 no-harm endpoint is separately studentized against +0.0002, with a one-sided critical value calibrated over its four frozen scenarios. Its validation uses distinct streams. This procedure is finite-envelope calibrated, not distribution-free. Validation is limited to the explicit families and moment assumptions below.

## Frozen operating-characteristic rules

Use 100,000 Monte Carlo replicates per calibration, validation, and power cell. Apply the previously frozen requirements:

1. Each primary boundary-null scenario: 95% Wilson upper endpoint for one-sided rejection probability ≤0.052.
2. Each primary one-sided upper-bound coverage Wilson lower endpoint ≥0.94.
3. Each primary central 95% interval coverage Wilson lower endpoint ≥0.94.
4. Each p=0 no-harm null scenario: same type-I Wilson upper endpoint ≤0.052 and upper-bound coverage Wilson lower endpoint ≥0.94.
5. At the planning alternative −0.0003, every previously designated 1.5× primary-power scenario must have a 95% Wilson lower endpoint ≥0.80. This is the formal power gate stated in the frozen candidate. The 2× scenarios are fully simulated and reported as sensitivity analyses; the prior protocol explicitly did not make them a separate formal gate. Results will not be reclassified after inspection.

The −0.0004 power rows and p=0 pass probabilities at true effects 0 and +0.0001 are sensitivity/descriptive outputs; no new acceptance threshold is imposed.

## Scenario envelope and variability

Use the Stage 5 v2 frozen condition SD estimates (provisional, based on seven development roots): `[0.0008141603913585719, 0.0009641181512261915, 0.0010690449676496975, 0.001969288002831287]`. Preserve the exact normal, Student-t, lognormal, zero-inflated 65%-zero, tied/asymmetric 65%-zero, balanced-offset, and p=0 constructions in the v2 candidate. Null validation includes all 1.5× and 2× scenarios. Primary power includes the frozen 1.5× families and the previously frozen 2× families, now explicitly adding `zero_inflated65_q2`; both −0.0003 and −0.0004 effects are evaluated. The q2 zero-inflated cell is reported as a sensitivity unless it is named in the frozen formal gate; it is not silently substituted for a q1.5 gate cell.

## Multiplicity limitation

The Stage 5 v2 protocol prespecified four condition-level tests as one Holm family. The later candidate v3 report explicitly made the current Welch/Holm outputs descriptive because their operating characteristics were not validated, and the new primary envelope simulation does not itself validate condition-specific Holm p-values. This design-validation package will not present those secondary tests as confirmatory and will not invent a new test. A complete sampling-ready protocol remains blocked unless the secondary family is either validly specified and independently validated under the scenario envelope, or the protocol is prospectively amended to limit formal claims to the primary endpoint and safety gate. This issue is not resolved by primary power results.

## Reproducibility and boundaries

All Monte Carlo seeds are allocated in `DESIGN_SEED_INVENTORY.json`, screened against explicit recoverable nonsealed seed metadata, and frozen with source/configuration hashes in `DESIGN_VALIDATION_FREEZE.json` before the full design simulation. An independently written auditor regenerates the statistical cells from those seeds, recomputes critical values, Wilson intervals, and gate decisions. The simulation has no Stim sampler, Stage 5 shot output, independent-test path, or API capable of opening sealed outcomes. Resource ceilings: 2 GiB peak RSS and two hours for the production simulation; independent replay may require a separate two-hour ceiling. A failed gate yields NO-GO; no allocation escalation or acceptance-rule change is permitted within this version.
