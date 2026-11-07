# Stage 5 Readiness Review

## Decision

**Ready for independent protocol review; not ready to sample.** The selected development candidate is the Stage 4B detector-profile estimator refitted on Stage 4C's fresh training batches, followed by PyMatching rebuilt from its estimated burst probability. Stage 4C dropped the CNN: on paired development evaluation it had 482 errors versus 478 for the profile estimator, while Ridge had 477. The one-error Ridge/profile gap did not demonstrate a reliable advantage for the more complex regression model, so the simpler profile estimator is retained for this candidate.

The candidate allocates 100 independent roots at each of five burst probabilities, 2,000 detector-only calibration shots and 2,500 paired evaluation shots per root: 2.25 million proposed shots. The primary endpoint is the equal-weight mean of four nonzero-condition root-paired LER differences. The 0-burst condition is a no-harm control. The practical improvement threshold, root-stratified bootstrap, Monte Carlo root sign-flip test, multiplicity family, seeds and resource limits are written before any Stage 5 sampling.

## Checks completed

- Stage 4C source/configuration freeze: 36 hashes verified; all ten focused tests passed.
- Stage 4C evidence manifest: 70 entries and 44 local raw files; all 70 hashes independently recalculated and matched.
- Stage 4C independent evidence audit: PASS; the saved CNN was retrained, estimators reconstructed from detector calibration data, and all five decoder predictions regenerated on all 35 evaluation roots.
- Stage 5 plan: 1,002 unique proposed seeds; zero collisions after independently re-extracting and expanding 4,171 distinct values from the explicitly enumerated recoverable development metadata. Phase 4A/4B root-offset-condition streams, template seeds, diagnostic seeds, and analysis seeds are expanded from their frozen configs. The plan checker verifies seed formulas, allocation totals, and candidate hashes.
- Profile model: Stage 4C profile file and copy match SHA-256; source training archive hash matches its Stage 4C provenance. No Stage 5 sample or sealed-test data was opened.

## Conditions before authorization

1. A separate reviewer must assess the Stage 5 power approximation, root-level sign-symmetry assumption, resampling streams, and interpretation of the all-four-condition success gate.
2. Implement a Stage 5 runner and a genuinely independent saved-array decoder/estimator audit; freeze both code paths and their source hashes before sampling.
3. Re-run deterministic circuit/DEM/graph checks and a resource benchmark without generating Stage 5 samples.
4. Obtain separate explicit authorization before any Stage 5 sampling.

Stage 4B's original calibration detector arrays are absent, so Stage 5 does not claim to reproduce its original fit. It instead freezes the Stage 4C profile refit, whose own training and audit evidence are retained. Historical seed screening cannot rule out undocumented RNG use. This is a simulation-only development project; no hardware validation is claimed.
