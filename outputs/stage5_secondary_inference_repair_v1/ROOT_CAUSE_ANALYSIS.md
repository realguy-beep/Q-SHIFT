# Root-cause analysis: Stage 5 secondary inference

## Observed defect

The former Stage 5 analysis used a one-sided Student-t/Welch-reference p-value for each condition-level mean of root-paired logical-error-rate differences, then applied Holm to the four p-values. At 1,210 roots, the procedure produced complete-null familywise error of 9.3815% for right-skew lognormal root effects and 6.836%-6.930% for the tied/asymmetric family, exceeding the prespecified 5.2% Wilson-upper gate. An independent replay reproduced every reported marginal and familywise rejection count.

## Cause and what is not the cause

The Student-t reference is exact under normal root differences, but it was extrapolated to materially skewed and discrete distributions without a validity argument. Right skew changes the finite-sample lower-tail behavior of the studentized mean; a point mass and tied values also violate the smooth continuous reference approximation. Welch-style variance estimation does not remove these distributional effects. Holm controls multiplicity only when its marginal p-values are valid, so it cannot repair the anti-conservatism.

The rejection-count failure is not explained by the later report-interval serialization mismatch: the raw rejection counts, seeds and statistics were unchanged, and independent replay reproduced them. A separate serializer defect used stale numbers of cells for some Wilson bounds after the matrix grew; it affected uncertainty intervals and gate flags, not the simulated rejections. SIMULATION_RESULTS_REANALYZED_V2.json corrects those reporting bounds only, and an independent interval audit recomputed every saved interval.

## Replacement and scope

The candidate secondary procedure uses root-level studentized means and a conservative empirical-CDF envelope over six fixed, centered unit-variance location-scale families. A six-way DKW band with total failure probability 0.001 is added to each empirical lower-tail CDF; right-continuous tie handling is conservative. The maximum envelope p-value is valid for a member of the specified family under a nonnegative mean shift on the DKW event. Holm then controls strong familywise error across the four condition tests. The unconditional finite-envelope bound is at most 0.051.

This guarantee depends on independent roots and the six specified shape families. The validation cannot prove that future Stage 5 root effects belong to that finite set, and the method is not distribution-free. The lower-risk alternative of a bounded-outcome distribution-free interval is too wide for the 0.0002 practical boundary at 1,210 roots. Sign-flip and bootstrap approaches need symmetry/exchangeability or additional approximation assumptions that the available evidence does not establish.

## Preserved evidence

The prior failed Welch/Holm reports and independent audit remain unchanged. Failures in secondary audit implementations V1-V3 are retained with exact notes; the V4 replay passed. The initial pre-test freeze candidate remains on disk and is explicitly marked blocked/superseded. The active v2 freeze and runner are separate files.
