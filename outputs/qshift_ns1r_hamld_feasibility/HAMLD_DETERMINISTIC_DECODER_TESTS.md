# Deterministic HAMLD inference tests

## Status: NOT RUN — BUILD BLOCKED

The conditional decoder tests were not run because the pinned package's compiled extension could not be built or imported in this environment. We did not call any decoder API. We did not create expected predictions from an alternate implementation and label them HAMLD. The pure source parser was independently exercised only as documented in `HAMLD_DEM_SEMANTICS_AUDIT.md`.

## Test fixtures required after a reproducible build

Use deterministic hand-authored Stim DEMs with one observable and compare predictions to an analytically enumerated set of Bernoulli mechanism assignments. Keep probabilities away from ties unless the fixture explicitly tests a tie. The input rows below are fixed and do not require sampling:

1. **Zero syndrome:** all-false detector row of width 40 for the Q-SHIFT DEM and width 1 for toy DEMs. Verify output shape and repeated-call equality. Expected logical prediction must be derived from the full fixture's logical-class mass; do not assume false without checking the model.
2. **Single mechanism:** toy `error(0.1) D0 L0`; input D0=1. The only nonzero single-fault assignment has logical parity 1, so the fixture's conditional logical class is analytically unambiguous. Add a no-fault branch and verify the decoder's selected class against exact Bernoulli weights.
3. **Boundary-only:** toy `error(0.1) D0`; input D0=1. Its unique explanation has L0=0. In Q-SHIFT, exercise each of the 28 D-only one-detector edges individually after confirming no competing same-syndrome logical class creates a tie.
4. **Observable-only:** toy `error(0.1) L0`; detector input all-zero. Verify whether the implementation's observable-only mechanism contributes to L0 class mass; document rather than assume API semantics.
5. **Multi-detector hyperedge:** use a toy `error(0.1) D0 D1 D2` and row `[1,1,1]`; verify the exact target set and logical parity. Also test one actual Q-SHIFT degree-4 event after toy semantics pass.
6. **Logical-class distinction:** include two mechanisms with the same detector syndrome and different L0 parity, with unequal probabilities (for example `error(0.01) D0` and `error(0.03) D0 L0`). Enumerate every mechanism subset and compare the predicted class with the larger summed posterior mass. Add an equal-mass fixture only to record the tie convention.
7. **Batch and determinism:** send multiple fixed rows together; compare batched results to row-wise calls; repeat all rows and require identical predictions.

The normal Python source validator uses the strict comparison `p(L0=True) > p(L0=False)`, so its source-level exact-tie choice is False. This is only a static observation about that Python path; the unbuilt C++ extension may use another convention. The tie fixture must be run against the actual selected executable and reported explicitly.

Only after all toy cases pass should the exact 40-detector/one-observable Q-SHIFT DEM be passed to HAMLD. Then verify zero, selected single-mechanism, boundary and burst pair syndromes and all output dimensions. Retain parser and inference test outputs, build hashes and environment lock. None of these decoder checks has been executed in NS-1R.
