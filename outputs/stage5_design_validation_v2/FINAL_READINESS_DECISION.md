# Final readiness decision — Stage 5 candidate v2

## Decision

**NO-GO for Stage 5 sampling under the 13–15M-shot candidate allocations.** The scenario-envelope calibrated studentized mean passed the prespecified finite-envelope type-I and interval-coverage checks, but none of 578, 640, or 666 roots per condition met the predeclared minimum power rule for the target Δ=−0.0003 across the required 1.5× normal, skewed, and tied/zero-inflated conditions. The 666-root allocation's worst required lower power bound was 77.86% (right-skew lognormal), and the tied-asymmetric lower bound was 78.95%.

## Evidence

- The previous Welch method remains rejected: worst observed type-I error was 6.67–6.77% at n=578–666 under right skew.
- Candidate calibrated method: maximum observed type-I was 4.93%, largest 95% Wilson upper endpoint 5.07%; lowest one-sided upper-bound coverage lower endpoint 94.93%; lowest central 95% coverage lower endpoint 95.91%.
- p=0 no-harm boundary: worst observed type-I 4.925%, Wilson upper 5.061%, lower bound coverage 94.939%.
- For 666 roots, power at Δ=−0.0003 was 78.12–80.49% across required 1.5× scenarios; no allocation met the Wilson-lower-bound ≥80% rule. At 2× variability, power was only about 57%.
- Statistical Monte Carlo runtime 789.64 s; Stage 5 shots generated 0; sealed historical test access false.

## Conditions for reconsideration

1. Resolve the power gap without changing the endpoint or choosing a larger target effect after these results. Obtain an independently justified target alternative and variance model from more development roots or external scientific rationale.
2. Any new allocation requires an explicit resource-budget decision and a new versioned amendment; the old v2 2.5M cap and files remain unchanged.
3. Validate the chosen procedure and all required secondary/multiplicity analyses against the final prespecified scenario envelope with independent simulations and a complete independent audit.
4. A review-only candidate package for the largest proposed allocation is available at `outputs/stage5_candidate_v3_n666/` (6,660 screened streams; candidate freeze SHA-256 `c4df4b557907bbb5c07557ddb2c27dd924cf37d067b114d438ce10a1180d25a2`). Its no-shot preflight passed, but it is not authorized or recommended for sampling. It also leaves the secondary Holm procedure as descriptive pending separate calibration.
5. Any redesigned and adequately powered plan needs a new versioned runner/auditor/seed inventory/freeze and separate explicit sampling authorization.

No Stage 5 simulation shots or evaluation samples were generated. Stage 4C evidence and the website worktree were not modified. The prior Stage 5 v2 protocol and freeze remain unchanged. No independent-test data were opened.
