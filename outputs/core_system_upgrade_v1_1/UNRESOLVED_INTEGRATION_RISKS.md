# Unresolved Integration Risks — Core Upgrade v1.1

1. **Detector ordering is positional.** The evaluator identifies caller-provided column order but has no circuit detector-coordinate/order fingerprint. Equal detector counts do not prove equivalent syndromes.
2. **Observable semantics are under-specified for broader code families.** Current use is one Stim logical-observable flip; metadata records only a count, not observable IDs, memory basis, or circuit identity.
3. **Noise-model metadata is declarative.** `noise_model_id` and construction provenance are caller-supplied labels, not cryptographic proof of the DEM or calibration source.
4. **Causality is interface-level.** The selector verifies integer block ordering and `based_on_through_block < current_block`; it cannot prove that the estimate was actually calculated only from persisted completed blocks or that a caller did not use hidden labels.
5. **Content identity is not provenance.** `sample_sha256` preserves the existing canonical byte hash. `sample_identity.evidence_sha256` additionally binds shape/dtype/convention and decoder metadata. Neither hash proves sample origin, authorization, seed independence, or leakage-free preparation.
6. **Alternative input representations need a new adapter.** Soft syndromes, event histories, coordinate tensors, or streaming rounds do not fit the current flat `[shots, detectors]` API. A conversion must declare and test its mapping rather than silently reshaping.
7. **No performance evidence is added.** These corrections do not demonstrate decoder improvement, adaptation benefit, or hardware compatibility. Fixed PyMatching remains the validated conventional baseline in the repository.
8. **Historical V2.4 evidence gap remains.** Thirteen of 17 recorded expected hashes differ from the files in the base commit. Files are unchanged from base after newline normalization, but provenance before that commit is not established; V2.4 remains HOLD.
