# Baseline reproduction and evidence audit

## Scope and result

The deterministic runner reproduced the historical two-qubit categorical toy: exact categorical MAP risk **0.0600**, exact independent-DEM MAP risk scored on the categorical distribution **0.0600**, separator-bearing PyMatching **0.1128**, and separator-free PyMatching **0.0600**. The categorical and independent-DEM MAP decisions agree on all four syndromes. This confirms the prior finite example.

The new independent rescoring script checked **17** exact cases and all **64** grid cells, with **0 numerical mismatches**. The main suite records 8 fixed-seed categorical channel instances, a 64-cell exhaustive parameter grid, four reduced surface fragments, and structural-only regeneration of six Phase 2B circuit/DEM conditions. It generated **0 stochastic Phase 2B evaluation shots** and did not read Phase 2B full-test labels.

## Historical artifacts checked

`verify_inputs.py` reports PASS for 1,313 direct historical hash checks: categorical decoder feasibility (20), categorical inference (59), Phase 2B frozen manifest entries (182), Phase 2B pretest freeze hashes (47), and decoder evidence manifests (1,005). It found no hash failures. Separately, all 151 DEM-gate reference/output hashes checked; 9 current hashes agree with a manifest-recorded `actual_sha256` rather than a separate original expected hash. They are consistent with that record, but provenance is weaker than a preexisting expected hash.

The Phase 2B manifest contains 182 listed files and is not an exact current inventory: `config - Copy.json` is an extra unmanifested copy with the same size and SHA-256 as `config.json`. No listed Phase 2B hash failed. The copy is an inventory caveat, not evidence of altered experiment data.

## Preserved implementation failures and corrections

The first full-syndrome decoder pass tried to match syndromes having exactly zero probability under a finite model; PyMatching correctly had no perfect matching for such off-support syndromes. The scorer was corrected to evaluate only syndromes with positive reference mass, and the independent rescoring check now passes. The first four-detector alternate-decomposition fixture also used mismatched anchor mechanisms; it is retained in `DIAGNOSTIC_RESULTS_BEFORE_FIXTURE_CORRECTION.json` and is excluded from the preregistered comparison. The corrected paired fixtures use identical anchors. Finally, a zero-detector/nonzero-logical DEM event cannot be represented as a graph edge, so Candidate A was tightened to reject it; this safeguard is documented in `REPRESENTATION_RULE_CLARIFICATION.md` and covered by a regression test.

One provenance caveat: an earlier execution in this task invoked the historical categorical-feasibility manifest builder with a verify-looking argument; that script rewrites the manifest deterministically. Its listed scientific artifacts subsequently verify, but the byte-for-byte pre-invocation serialization of that manifest cannot be proven. No historical result, dataset, or source file was changed by this investigation.

## Reproduction commands

From the repository root, run `python -B -m unittest discover -s outputs/matching_representation_investigation -v`, then `python -B outputs/matching_representation_investigation/matching_investigation.py`, `python -B outputs/matching_representation_investigation/verify_results.py`, and `python -B outputs/matching_representation_investigation/verify_inputs.py`. The last check is read-only with respect to historical inputs and writes only its local `PHASE0_VERIFICATION.json` report.

## Environment and resources

Python 3.12.10, Stim 1.16.0, PyMatching 2.4.0, NumPy 2.5.3. Latest deterministic suite execution: 4.525 seconds; process peak working set 98.0 MiB. These measurements cover this bounded analysis job only.
