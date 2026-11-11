# Statistical analysis plan — v1

## Study status

Development/feasibility only. The held-out partition is independent of selection and validation roots but is not a final confirmatory test. Do not use it to tune or decide a later final evaluation.

## Unit, estimands and pairing

For each root and decoder, compute the number of residual logical errors `sum(prediction XOR observable)` and divide by 2,500 shots. The independent unit is the Stim root; the per-shot paired predictions are not treated as independent replicates for root-generalization uncertainty.

Primary descriptive estimand:

`mean_{p in {.004,.008,.012,.016}} mean_root( LER_adaptive(root,p) - LER_safe_static(root,p) )`.

Additional paired contrasts: adaptive minus pooled detector-calibrated static; adaptive minus nominal fixed; pooled static minus nominal; safe static minus nominal; adaptive minus privileged reference. The oracle contrast is diagnostic only.

For each contrast, preserve root pairing by forming a per-root LER difference first, then resample root IDs within each condition and apply the same selected root indices to both decoder arms. Estimate the equal-weight mean of the condition-specific resampled root means in each replicate. Use PCG64 with `bootstrap_results` in `seed_inventory.json`, 100,000 replicates, and percentile 2.5/97.5 bounds. For selection validation, separately use `bootstrap_validation`, 100,000 root resamples of p=0 selected-static-minus-nominal differences, and the one-sided 95th percentile upper bound. At final p=0, report the mean excess over nominal and a one-sided 95th percentile bootstrap upper bound. The fixed practical benchmarks are |benefit|=0.0002 absolute LER and p=0 harm=+0.0002.

## Multiplicity and claims

There is one primary development contrast and one separate p=0 safety diagnostic; all other comparisons are exploratory. No confirmatory p-value or familywise claim is planned. Condition-specific values and multiple decoder contrasts are descriptive; their intervals are labeled exploratory. Do not interpret a percentile interval excluding zero as a confirmatory discovery. The finite-family Stage 5 test procedure is not automatically transferable to a different comparator and is not reused here.

## Integrity checks

The saved-array auditor independently rebuilds the circuit and every matcher, verifies the final decoder-selection freeze predates final evaluation sampling, verifies exact detector/observable pairing, independently reimplements the frozen profile estimator, recomputes selection and validation/fallback from their saved predictions, compares final predictions byte-for-byte, recomputes each root count and hashes every raw archive. Missing calibration arrays or mismatch in any one root makes the overall numerical audit fail; do not silently drop roots. The bootstrap describes a five-condition development dataset and is not a power-validated confirmatory procedure.
