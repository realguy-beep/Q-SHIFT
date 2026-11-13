# NS-2B Sampling and Decoder-Model Identity Design

## Scope and status

This is a deterministic engineering-contract revision based on accepted NS-1 commit `e015a18e22de653b479cc206026d520e7dc71b5d`. It does not register HAMLD or another research decoder, sample shots, train models, or claim performance. V2.4 remains HOLD. The NS-1 API remains available; the new v2 contracts are additive.

## Two identities

`SamplingIdentity` in `qshift_core_v1/sampling_model_identity.py` identifies the actual data-generating Stim circuit: serialized circuit SHA-256, Stim version, declared generating-noise ID and canonical provenance record plus digest, code family/distance/rounds/basis, detector IDs/coordinates/order digest, and observable IDs/interpretations/polarities/semantic digest. Noise provenance is retained as canonical JSON so a reviewer can inspect the record as well as its hash.

Observable polarity is descriptive: `+1` records Stim's declared flip bit as-is; `-1` records a convention where the external decoder's reported bit is inverted relative to that canonical flip bit. The current evaluator performs no implicit inversion. A decoder or upstream label adapter must normalize outputs to the explicitly declared convention before comparison.

`DecoderModelIdentity` identifies one decoding model: the exact supported sampling-identity digest; decoder implementation/version and output metadata; detector input representation; detector-order and observable-semantic digests; optional concrete DEM digest and full construction record; decoder-assumed noise identity and visible provenance record/hash; correlation flag plus its implementation semantics; coordinate requirements; and hashes/note for static resources. It does **not** require assumed noise to equal generating noise.

The sampling identity deliberately contains no DEM digest. The model identity deliberately retains each decoder's own DEM identity. Therefore, a decomposed PyMatching DEM and an undecomposed research DEM can be declared against the same sampling identity without being normalized or described as equivalent. The model's DEM record also records the circuit from which that DEM was built; this may be a nominal model circuit different from the evaluated generating circuit. Such a decoder must explicitly declare support for the target sampling identity.

## Exact DEM construction

`DEMConstructionSettingsV2` captures Stim 1.16.0's complete `Circuit.detector_error_model` option set: `decompose_errors`, `flatten_loops`, `allow_gauge_detectors`, `approximate_disjoint_errors` (bool or threshold), `ignore_decomposition_failures`, and `block_decomposition_from_introducing_remnant_edges`, plus a human-readable note. `StimDEMArtifact.build` passes all options explicitly and hashes exact DEM text. It also records the DEM's detector-order/coordinate fingerprint and requires explicit source observable meanings and polarity; compatibility checks compare both with the target sampling identity. It records declared arguments and the resulting digest; the record does not establish mathematical equivalence or physical fidelity.

## Batch boundary

`TrustedDetectorBatchAdapter.from_stim_detector_samples` requires the exact source circuit and explicit ordered detector IDs. It checks circuit text hash, current Stim version, binary shape/width, and exact detector ordering, then stores immutable detector bytes, shape, order, source-circuit digest, and content digest. Its read-only `detector_bits` view is backed by immutable bytes. Each decoder receives a fresh writable copy; inference cannot mutate the shared batch or another decoder's input. Batch metadata is a software boundary only: it cannot prove that a caller did not misrepresent arbitrary external bytes as Stim output. A trusted sampler adapter and its run provenance remain necessary in any future experiment.

## Compatibility and execution

`assert_model_compatible` checks the model's explicit target sampling digest, detector and observable dimensions, ordered detector fingerprint, observable interpretation and polarity, and any required coordinates. Unknown sampling fields are rejected by construction; coordinates can be explicitly absent only if the decoder does not require them. The assumed-noise identity is compared only with the decoder metadata, never with the generating-noise identity.

`decode_model_checked` snapshots metadata values before inference; validates the decoder metadata again afterward; validates prediction type, binary values, exact `[shots, observables]` shape, and elapsed time; rejects booleans, NaN, infinity, and negative time; passes an isolated detector copy; and returns output storage detached from decoder-owned memory.

`IdentityAwareDecoderRegistry` wraps the accepted `DecoderRegistry`. It delegates registration and retrieval to the original registry, while binding each name to its model and sampling identity. Its selector uses the existing `SafeDecoderSelector`, retaining the fixed nonexperimental fallback and explicit experimental opt-in. `evaluate_identity_aware_paired` runs every decoder on the same immutable detector batch before scoring the labels and then delegates scoring/statistics record construction to the existing paired evaluator. Protected-test scope is rejected before decoder execution.

## Compatibility statement

The accepted NS-1 `CircuitIdentity`, `ExternalDecoderSpec`, `DetectorBatch`, and `decode_checked` remain source-compatible. The v1 compatibility check intentionally retains its original strict noise-equality rule for existing callers. New multi-model comparisons must use the v2 API; migration must be explicit. The v1 `decode_checked` implementation was narrowly hardened for metadata mutation, return validation, elapsed-time typing, and array isolation without relaxing its compatibility rule.

The dashboard remains on its existing distance-3/five-round PyMatching pathway and was not wired to the new registry. No website behavior or decoder selection algorithm changed.
