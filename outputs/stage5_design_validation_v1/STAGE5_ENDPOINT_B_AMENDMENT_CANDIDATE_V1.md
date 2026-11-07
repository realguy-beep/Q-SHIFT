# Stage 5 Endpoint B amendment candidate v1

**Candidate only; not active and not a Stage 5 sampling authorization.** Written after the Stage 5 v2 implementation freeze. The v2 protocol, code, seed inventory, frozen evidence, and Stage 4C records remain unchanged. No Stage 5 evaluation shots are generated or accessed in this validation phase.

## Proposed primary and decision

Use Endpoint B: equal-weight mean of the four nonzero-condition independent-root paired differences, `profile-adaptive LER − fixed nominal LER`. Test one-sided \(H_0:\Delta\ge -0.0002\) against \(H_1:\Delta<-0.0002\) at alpha .05. A practical-benefit claim requires the one-sided 95% upper confidence bound below −0.0002. The planning alternatives must be stated separately; the null boundary is not a power alternative.

Primary inference is Welch–Satterthwaite for the equal-weight mean of the four stratum means using root-level variances. The prespecified sensitivity is a paired, stratum-preserving root bootstrap-t. If these materially disagree, label the result inconclusive. A sign-flip test may be descriptive sensitivity only, explicitly conditional on root-effect symmetry; decoder arms were not randomized. The four nonzero condition tests remain a Holm-adjusted secondary family. The p=0 condition remains a separately evaluated no-harm gate at +0.0002. Preserve the existing point-direction consistency requirements; they are not separate superiority evidence.

## Candidate allocation under evaluation

256 roots in each of five probability strata, 2,000 detector-only calibration shots and 2,500 paired evaluation shots per root: 1,280 roots, 2,560,000 calibration shots, 3,200,000 evaluation shots, 5,760,000 unique shots. This is a design candidate; new seeds, configuration, runner, auditor, and freeze would be required after approval.

## Prespecified design simulations

The candidate design simulation in `DESIGN_SIMULATION_CONFIG.json` uses synthetic independent root-level paired effects, not simulated quantum shots. It evaluates the one-sided error/coverage and power of the Welch procedure under the saved condition-specific SDs, SD multipliers 1.0/1.5/2.0, normal, Student-t(5), right-skewed lognormal, 65% zero-inflated effects, and a null with nonzero stratum effects averaging to the global margin. It also checks a separate p=0 no-harm scenario. Monte Carlo intervals accompany simulated probabilities. The frozen bootstrap-t sensitivity is assessed separately at 256 roots with three adverse distribution shapes.

Existing variance inputs are only seven roots per Stage 4/4C cell. The nominal normal-theory planning requirement is 256 roots/stratum for 80% power to detect −0.0003 (a .0001 improvement beyond the margin), and 354 for 90%; 5.76M/7.965M total shots. At 1.5× heterogeneity, the 80% requirement rises to 575 roots/stratum (12.94M shots). Thus 256 is a nominal-variance 80% design for that alternative, not a robust guarantee. If this candidate is not feasible, Endpoint A would answer a narrower question (any improvement over zero), but it must be chosen before sampling and cannot be used as a fallback after a failed B test.

## Engineering benchmark and auditor compatibility

The non-Stage-5 benchmark uses 50 disposable development roots (225,000 shots), a seed namespace disjoint from available historical and Stage 5 allocations, paired detector/observable samples, and all three decoder arms. It exercises atomic root archives, pause/resume, independent re-decoding, and runtime/memory/storage measurement. Benchmark logical-error counts are engineering checks only.

The historical v2 independent auditor hard-codes 100 roots per condition and 500 archives. It is **not** directly compatible with a 256-root amendment. This candidate requires a separate versioned dynamic auditor that reads a frozen `roots_per_condition=256`, expects exactly 1,280 root archives and corresponding shot totals, rejects missing/extra roots, and independently re-decodes each archive. A benchmark fixture tests the same schema and dynamic cardinality logic. The v2 auditor is preserved unchanged.

## Approval conditions

No Stage 5 sampling until (1) the owner accepts Endpoint B and a target alternative, (2) resource budget and root count are accepted in light of heterogeneity sensitivity, (3) coverage/type-I simulations and benchmark pass, (4) the dynamic runner/auditor are frozen and tested, (5) all Stage 5 seeds are collision-screened in a new inventory, and (6) the owner separately authorizes sampling. This candidate does not satisfy item 6.
