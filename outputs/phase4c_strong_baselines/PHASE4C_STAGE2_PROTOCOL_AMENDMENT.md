# Phase 4C Stage 2 RNG protocol amendment (prospective)

Created after Stage 1 and before any Phase 4C Stage 2 sampling. This is a new prospective amendment; it is not part of and does not alter the original frozen Stage 1 protocol or Stage 2 frozen plan. Stage 2 has generated zero shots.

Regime indices are data-heavy=0, nominal=1, measurement-heavy=2. Root index i=0..19. `root=72000001+10000*(20*regime_index+i)`. Calibration seed=`root+101+regime_index`; validation=`root+201+regime_index`; test=`root+301+regime_index`. Template seeds are 73000001 through 73000009 inclusive. Diagnostic seed is 72000000. This yields 60 roots, 180 per-root streams, nine template streams, and one diagnostic stream: 190 derived seed values, all required to be unique.

The accompanying script validates every generated entry against the pre-existing `stage2/STAGE2_SEED_INVENTORY.json`, then screens recoverable historical seed values in Phase 4A, 4B, and 4C artifacts. Search coverage and limitations are recorded in the machine-readable audit. This amendment does not validate Stage 2 calibration code, statistical analysis, or runner. It does not constitute full experimental preflight authorization.
