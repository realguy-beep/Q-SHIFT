# Independent evidence audit

## Decision scope

This audit checks the saved `outputs/headroom_feasibility/` development pilot and the evidence underlying its **NO-GO** decision. It does not run Stim sampling, create test shots, or modify the pilot or earlier research artifacts.

## Data and integrity checks

- The pilot contains 180 calibration bundles and 180 independent development-evaluation bundles: 5 roots × 5,000 shots in each of 36 family × distance × memory × regime cells.
- Each NPZ stores one packed detector array, one observable vector, and predictions from every candidate. Residuals were recomputed as observable XOR prediction from those saved arrays; all candidate comparisons are shot-paired.
- The preceding independent pilot audit reports PASS: 360/360 bundles were independently re-decoded from the stored detector arrays, covering 10,800,000 prediction-shot checks; 72 template profiles and all calibration selections were independently recomputed.
- This audit re-read the raw arrays, recomputed calibration-selected pooled and specialist indices, bootstrap selection frequencies, paired errors, root-cluster intervals, and the gate. The 36-cell and 702-pair totals match the saved evidence. See `INDEPENDENT_RECOMPUTATION.json`, `SPECIALIST_SELECTIONS_RECOMPUTED.csv`, and `DECODER_EQUIVALENCE_PAIRS.csv`.
- The new pilot manifest contains 623 entries with no hash mismatches. The pre-test freeze source/configuration hashes match. Its filesystem timestamp precedes the first saved calibration bundle; that ordering supports, but does not cryptographically prove, freeze chronology.
- The proposed 516 RNG seeds are unique and disjoint from 2,076 recoverable historical seed values across 1,231 historical files examined outside the pilot directory. Historical seed coverage is limited to values recorded in the available artifacts; unrecorded streams cannot be ruled out.
- The pilot records that Phase 4/5 historical artifact hashes were unchanged. No historical file was edited for this audit.

## Independent NO-GO recomputation

The gate requires, within a family/basis/distance, at least two calibration-selected specialists that differ from pooled fixed and from each other; each must have calibration bootstrap selection frequency ≥0.80, at least 5% and 0.0001 absolute evaluation LER reduction, at least four of five evaluation roots favoring it, and a root-bootstrap 95% interval wholly below zero. The same regime pair must pass at two or more distances.

Reapplying these rules to the saved calibration and evaluation arrays gives:

- Calibration specialist differs from pooled fixed in 14/36 cells.
- Independent evaluation LER is lower in 7/36 cells, higher in 6/36, and equal in 23/36 (22 cells selected the pooled decoder itself; one different-index pair made identical predictions on its evaluation samples).
- Only one individual regime cell passes all per-regime numerical thresholds: Pauli-biased family, Z-memory, distance 5, X-biased generating regime. No second regime in that bank passes.
- No family/basis has a qualifying pair of regimes at two distances. The overall gate is therefore **NO-GO**.

The gate is a prespecified development screen, not a confirmatory significance test. It is not multiplicity-adjusted; its repeated-distance, multi-regime requirements are a conservative feasibility criterion. No p-value or universal equivalence claim is inferred.

## Historical gaps and deviations

- Phase 4C Stage 2 has independently re-decoded test predictions, but its calibration detector arrays and fitting score traces were not saved; its calibrated-model fitting cannot be reconstructed from raw calibration evidence.
- Phase 4B generated fresh calibration templates despite protocol text specifying reuse. Its audit is PASS WITH DEVIATION.
- Phase 4C Stage 2 used prospective RNG amendments after its original plan. This affects claims about original preregistration.
- Phase 2C's forest surrogate was not an exact or bounded approximation to the circuit posterior. Phase 3A corrected versions reuse the same three raw bundles. Superseded Phase 5 v1 metrics had policy-label errors; corrected versioned outputs are the relevant evidence.
- The combined Phase 2–5 history mixes code families, noise models, decoder-selection methods, baselines, and evidence strength. It must not be pooled into one treatment effect.

## Audit conclusion

The NO-GO is numerically reproducible from the stored headroom arrays. It means this tested bank did not show the prespecified replicated utility headroom needed to justify a new adaptive benchmark. It does not prove that every decoder bank, noise process, or adaptive architecture must fail.
