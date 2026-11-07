# Reproducibility checklist

## Current synthesis scope

- [x] Preserve historical phase outputs. This synthesis creates only new Markdown files under outputs/research_synthesis/.
- [x] Use audited later versions where Phase 3/5 outputs were corrected or superseded.
- [x] Distinguish Phase 4A integrity reaudit, Phase 4B PASS WITH DEVIATION, and missing Phase 4C calibration arrays.
- [x] Do not run new simulations or claim new results.
- [ ] Re-hash every historical file during this synthesis. Not performed; prior audits are referenced.
- [ ] Independently parse every phase's raw arrays. Not performed; this is not a second raw-data audit.
- [ ] Inspect Git history. The working directory is not a Git checkout, so this evidence was unavailable.

## Required evidence archive for a paper

- [ ] Hash exact source, config, circuit, DEM and analysis files before held-out generation.
- [ ] Save SHA-256 for every generated bundle, prediction array and per-root result.
- [ ] Preserve original manifests; write new audit manifests rather than rewriting historical hashes.
- [ ] Record full seed derivations and a collision report, distinguishing unknown historical coverage.
- [ ] Save calibration detector arrays, labels and score traces. Phase 4C Stage 2 lacks these.
- [ ] Keep template, calibration, training, validation, diagnostic and test RNG streams disjoint.
- [ ] Freeze protocol, implementation, analysis and seed list before final test; record timestamp and hashes.
- [ ] Record deviations prospectively while preserving original frozen files. Phase 4B template generation deviated.

## Scientific validation

- [ ] Check noiseless detector/observable behavior for every circuit configuration.
- [ ] Verify detector/observable counts, noise instructions, probabilities and physical insertion locations.
- [ ] Verify DEM logical-observable index, graph metadata, edge weights and approximation settings.
- [ ] Independently decode saved detector arrays and match every stored prediction exactly.
- [ ] Recompute residuals as sampled observable XOR predicted logical correction.
- [ ] Prove same sample identities across all paired policies.
- [ ] State when categorical channels are approximated by independent DEM mechanisms.
- [ ] Distinguish logical-frame prediction from physical state correction.
- [ ] Show that only calibration/validation labels select models; test labels are scoring-only.

## Statistics and computational reporting

- [ ] Freeze primary estimand, cluster unit, direction, practical margin and stopping rule.
- [ ] Use independent roots/schedules for generalization; report paired shot-level McNemar as secondary.
- [ ] Include per-root/per-condition counts, discordances, intervals and exact test definitions.
- [ ] Correct prespecified secondary comparisons; label retrospective and oracle results as descriptive.
- [ ] Report calibration sample size and selection uncertainty.
- [ ] Separate decoding time from estimator/controller overhead and include native memory where possible.
- [ ] Justify power at target distances and rare logical-error rates.
- [ ] Preserve negative findings, failed gates, deviations and superseded analyses.

## Real-hardware boundary

- [ ] Call the work simulation-based unless a device evaluation is performed.
- [ ] A hardware claim would require device/circuit compilation, syndrome data path, latency/throughput, trigger availability, calibration, feedforward and state-correction validation.
- [ ] Do not infer within-circuit adaptation from block changes between independent simulations.
- [ ] Do not infer threshold scaling from distance-3 results.

This checklist identifies requirements and known gaps; it does not recertify each historical experiment.
