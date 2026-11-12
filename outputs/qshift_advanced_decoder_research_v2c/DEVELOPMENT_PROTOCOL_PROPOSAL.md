# Proposed next development protocol (not authorized)

## Recommendation

**Do not request a bounded development study yet.** The joint standardized population fit (candidate B) is an interpretable candidate and resolves the demonstrated fixed-measurement projection bias under the exact two-parameter model. But finite-history behavior, causal window/update rules, mismatch guard size/power, calibration reuse, and boundary handling are not fixed. Candidate C is a secondary method; its local asymptotic gain does not justify leading with a more complex covariance fit. Candidate D is only a proposed fail-safe guard, not a validated alarm.

After the owner resolves the items below, a separate request could propose a small, development-only methods study. This document is not an authorization or frozen protocol.

## Conservative candidate architecture for future review

1. **Inputs:** only the 45 chronological detector features. Do not pass observables, logical labels, scripted scenario labels, true probabilities, or future rows to an estimator or controller.
2. **Templates:** use a prespecified finite `p_b×p_m` grid on the declared rectangle. Keep the 45 feature definitions fixed. Record exact-categorical and approximate-DEM template families as distinct arms/diagnostics; do not combine them silently.
3. **Primary estimator:** candidate B, minimize the fixed diagonal standardized residual. Freeze feature scales from an independent development/calibration allocation, floor variances, use deterministic lower-parameter tie-breaking, and use only detector rows strictly earlier than the scored block. A small coarse grid with checked interpolation is preferable to an unexamined fine search.
4. **Model-adequacy guard:** candidate D computes a covariance-whitened residual against the fixed-`p_m=.003` profile. If the predeclared finite-history alarm triggers, do not attribute the change to burst p and retain the last accepted decoder setting. Report the alarm and no-change action. Do not automatically claim that the cause is measurement probability.
5. **Optional C arm:** only if covariance is estimated or constructed from an independent template allocation, with a frozen reference point and regularization rule. Report sensitivity to ridge strength and covariance misspecification. It cannot replace B based on this population calculation alone.
6. **Causal use:** update after block `b` using rows through `b`; the resulting estimate may first affect block `b+1`. Freeze minimum history, update block length, reset/forgetting rule, hysteresis and dwell before the study. No same-block correction.
7. **Decoder separation:** treat parameter estimation, graph selection and logical risk as distinct. A better `(p_b,p_m)` fit is not evidence of better matching decisions or lower LER. Any decoder comparison needs a separate authorization and matched decoder/cache costs.

## Proposed bounded study outline if later approved

The study should be an estimator-methods development exercise, not a decoder efficacy claim. Use newly authorized development roots, separated from all historical and protected evaluation material. Include stationary nominal noise, the Phase 2B `.006` measurement mismatch, several owner-selected burst/readout changes, boundary cases, and a separately declared readout-mismatch stress only if the physical mechanism is explicitly specified. Give A, B, C and D the same detector histories and calibration/template opportunities. Report joint parameter bias/RMSE, profile residuals, alarm false-positive and miss rates, boundary hits, update delay, graph switches, CPU/RSS and calibration overhead. Preserve failed runs. Do not select features, threshold, grid, or window using a future test/evaluation set.

This outline deliberately does not choose new physical mechanisms, thresholds or sample sizes. Such choices require pre-data owner/supervisor review. It does not alter the Phase 2 logical-risk estimand or authorize outcomes.

## Decisions needed before a request

- Is `p_m` an estimand to track, a nuisance constrained to `.003`, or only a mismatch alarm target?
- Which exact static and joint template family is operationally available: categorical circuit algebra, approximate DEM, or both as model sensitivity?
- What `p_b,p_m` bounds and out-of-range response are acceptable? How should the estimator behave at boundaries?
- What minimum detector-history length and update-block size are acceptable given bias/latency tradeoffs?
- What finite-history guard statistic, covariance source, threshold, and fallback state are to be prespecified? Require independent deterministic/null calibration and later finite-sample validation.
- What finite calibration/template budget and separation from tuning histories are allowed?
- Is C's covariance gain worth the added estimation and regularization burden? If so, what fixed-reference and ridge sensitivity range will be evaluated?
- Which drift, transient and measurement-mismatch schedules are scientifically justified, and who selects them before data access?
- What resource ceilings and study stopping rules apply?

Until these items are decided, no estimator is sufficiently specified to justify requesting a bounded study. No experiment, sampling, seed generation, or protocol freeze is authorized here.
