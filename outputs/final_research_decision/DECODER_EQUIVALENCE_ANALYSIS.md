# Decoder equivalence analysis

## What the 95 pairs mean

The disagreement table contains 702 candidate-pair × generating-regime comparisons. In **95/702 (13.5%)**, two candidates predicted the same logical flip on every one of the 25,000 paired evaluation shots in that regime. The largest observed pairwise disagreement rate was 0.42%.

These 95 cases are **finite-sample prediction coincidences**, not established decoder equivalences:

- All 95 pairs have different saved DEM byte hashes.
- Rebuilding PyMatching from each saved DEM and canonicalizing detector count, logical fault IDs, boundary endpoints, edge weights, fault IDs, and correlation mode found **0/95 identical matching-graph signatures**.
- Thus none is structurally identical under the saved DEM/weighted-graph representation. The full details and hashes are in `DECODER_EQUIVALENCE_PAIRS.csv`.
- A graph difference does not prove that the two induced prediction functions differ on some physically reachable syndrome. No exhaustive syndrome-space equivalence proof was performed. The supported statement is only that these candidates agreed on the finite evaluated detector arrays while their decoder representations differed.

One of the 14 calibration-selected specialist-versus-pooled comparisons is such a finite-sample coincidence: native noise, distance 7, X-memory, measurement-heavy condition, specialist index 3 versus pooled index 2. Both made one logical error in 25,000 shots and disagreed on no evaluated shot. This is not a structural match and does not demonstrate useful specialization.

## Interpretation

The bank contains genuinely different DEMs and matching graphs, so its limited utility is not explained by 95 duplicate models. Instead, the tested syndrome distributions rarely drove those different graphs to different logical predictions. When predictions did differ, the number of affected shots was small relative to the evaluation batch and the resulting logical-error tradeoff was inconsistent.

The headroom audit does not show whether model differences matter on rare, unsampled syndromes, under other noise distributions, or for a different code circuit. Exact function equivalence would require an analytical proof or exhaustive/structured coverage of the relevant syndrome space; that is outside this saved-sample audit and no new sampling was done.
