# Recommended next step

## Do not launch the proposed test

Keep the correlation pilot, its raw bundles, and its pre-test freeze unchanged. The 9-million-shot plan depends on a B DEM that Stim cannot construct for the frozen `PAULI_CHANNEL_2` channel when approximation is disabled. Do not substitute independent Pauli errors, `ignore_decomposition_failures=True`, a probability threshold, or another changed circuit under the same hypothesis; each would change the model being compared.

## Resolve the model question first

The most direct next development step is a small, deterministic decoder-feasibility prototype that keeps the Phase 2B categorical channel intact and represents its mutually exclusive Pauli-pair outcomes as categorical factors rather than independent DEM mechanisms. Validate probability normalization, detector/observable mapping, and posterior decisions on analytically enumerable toy circuits before applying it to the distance-3 circuit. A factor-graph / belief-propagation or likelihood-sampling approximation may be considered only if it reports approximation error and is checked against a small exact reference.

If a native categorical decoder is not feasible, a separate sensitivity study could use Stim's documented probability-threshold setting for `approximate_disjoint_errors`. Such a study must be called a **thresholded approximation sensitivity analysis**, not an exact-vs-approximate comparison, and must freeze the thresholds and selection rules before any evaluation shots. It would answer a narrower question than the current follow-up.

## Statistical corrections before any later confirmatory run

If two model families become available:

1. Keep the paired root-level `gₛ,r` definition and six fixed interaction coefficients.
2. Use a Welch–Satterthwaite cluster-level test for G, with paired stratified studentized-bootstrap intervals; treat sign-flipping as sensitivity analysis unless its symmetry assumption is justified.
3. Estimate the variance/covariance of G from independent calibration/validation roots and freeze sample size before final test access. Do not carry forward the old “94% power” claim.
4. Keep six condition-specific family contrasts secondary with a single Holm family; do not reinterpret the previous post-hoc same-name pattern as confirmatory.

No decoder prototype, sensitivity simulation, or confirmatory sampling was executed in this gate.
