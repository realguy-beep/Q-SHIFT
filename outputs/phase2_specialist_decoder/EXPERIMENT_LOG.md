# Phase 2 experiment log

## Audit and preregistered gate

- Reused the exact Phase 1 circuit builder; verified all six compositions keep 5 qubits, 8 detectors, and one observable.
- Fixed pMatching is the depolarizing specialist at p=0.01. Four specialist DEM families are X-dominant, Z-dominant, depolarizing, and measurement-only.
- Calibration probability is estimated from detector-pattern likelihood over p={0.006, 0.008, 0.010, 0.012, 0.014}. Composition family is known from the calibration source; logical labels are saved for audit but not read by the fit.
- Usefulness gate: at least one specialist must reduce paired test errors, pass exact McNemar after Bonferroni over 24 comparisons, and have a seed-bootstrap interval below zero. Test data never selects models.

## Completed cross-evaluation

`results/specialist_results_v1.json` contains 10 independent seeds, 30,000 calibration shots per specialist, 10,000 validation shots per condition, and 30,000 paired test shots per condition per seed. The 4×6 specialist-condition matrix, fixed model, true-noise oracle model, validation-selected oracle specialist, correction disagreement, runtime, graph metadata, and statistical tests are retained.

All 40 fitted p values were 0.010. X, Z, and depolarizing specialists made identical corrections to fixed matching on all test conditions. Measurement-only specialists disagreed on fewer than 0.1% of shots and usually increased errors. The validation-selected oracle chose fixed matching in all 60 condition-by-seed cases. No model passed the predeclared usefulness gate; Experiment D was stopped without implementing a selector.

## Preserved development failures

- `results/smoke.json` contains a completed one-seed smoke evaluation but plotting initially failed when a zero-error interval produced a negative floating-point error-bar extent. The plot code clamps error bars at zero; `results/smoke_v2.json` and its figure verify the corrected path. Neither smoke run contributes to claims.
- The calibration-fit implementation superseded the earlier direct-known-p-only smoke path. Both files are preserved.
- The Phase 1 failed rate-only selector and guarded no-switch result remain in the sibling phase directory; this phase does not rewrite or combine them.

## Next-step decision

Because no specialist demonstrated a credible benefit, no detector-only selector or unfamiliar-mixture classifier was built in Phase 2. The useful follow-up is to change the code geometry or introduce nonuniform/correlated fault mechanisms that can alter the matching correction boundary, then repeat this paired cross-evaluation. Further selector complexity on the current eight-detector model would add overhead without a validated gain.
