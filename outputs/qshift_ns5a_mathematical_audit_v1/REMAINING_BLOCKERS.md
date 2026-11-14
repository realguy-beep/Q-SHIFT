# Remaining blockers

## Mathematical and evidence blockers

1. Checkpoint 133's historical threshold predicate and reported crossing count are wrong for `alpha=.05`; the new audit corrects the short abstract enumeration but does not alter the old package. Any downstream citation must use the corrected result and disclose the original error.
2. The tested recurrence's intermediate product reached 199 bits upward; a 128-bit multiplication is not safe even for this short fixture. No fixed-width production arithmetic is implemented or proven.
3. The full exact-circuit Bernstein coefficient calculation was reviewed but not independently reimplemented end-to-end in this audit. Existing source assumes the mapped fault-support set and parameter-affine channel probabilities remain valid throughout each rectangle.
4. Three-parameter identifiability is numerical local rank, not an exact proof or finite-sample estimator guarantee.
5. The finite DEM transfer screen has a high-alternative envelope violation; no continuous DEM certificate exists. A decoder graph built from an approximate DEM cannot inherit exact-circuit e-factor guarantees without additional analysis.
6. The delay tables were not fully regenerated here, and they are sufficient concentration quantiles under conditional laws—not expected/observed latency.
7. The exact synthetic burst may be detector-identifiable but same-mask correlated readout or another nuisance prevents physical cause attribution.

## Controller blockers

1. No repeated-switch or state-transition false-alarm guarantee.
2. No owner-selected operational error metric (ARL, finite-horizon false alarm, or expected false switch count).
3. No trusted post-alarm reset protocol; no automatic opposite-direction test.
4. No statistical rule for the entire intermediate burst band; fallback/abstention must cover it.
5. No causal end-to-end latency evidence for calibration, DEM reconstruction, decoder replacement, and activation.
6. No decoder logical-error benefit has been demonstrated.
7. Exact circuit vs approximate DEM mismatch blocks direct transfer to a deployed PyMatching configuration.

## Publication and experiment gates

- Do not claim a novel adaptive decoder or performance gain.
- A narrow deterministic methods paper needs full independent reproduction and a targeted literature comparison; it is not ready on the current audit alone.
- Any estimator or adaptive decoder study requires a separately approved protocol, new disjoint development seeds, explicit selection/monitoring/calibration partitions, causal input checks, and a predeclared fallback.
- Preserve BeliefMatching as a separate track; this audit does not authorize its pilot.
- No Stage 5, sealed-test, or frozen outcome access is authorized by this package.
