# NS-1 External Decoder Interface

## Registration boundary

The existing `DecoderProtocol` remains the execution interface:

```python
metadata: DecoderMetadata
decode(detectors: numpy.ndarray) -> DecoderPrediction
```

The NS-1 gate wraps this interface with `ExternalDecoderSpec` and a `CircuitIdentity`. An experimental candidate remains separately registered and opt-in. The existing fixed PyMatching instance remains the baseline and is not replaced or mutated.

## Required declaration

An external candidate must provide:

1. Implementation name/version and current `DecoderMetadata`.
2. Required input representation; v1 currently supports unpacked binary `[shots, detectors]` only.
3. Exact supported `CircuitIdentity.identity_sha256` values and detector-order fingerprint.
4. Observable IDs, their ordering, and the meaning/polarity of predicted observable flips.
5. Assumed noise-model ID and any matching correlation mode.
6. Construction/source provenance and runtime/resource requirements.
7. Whether it requires detector coordinates. The identity includes coordinates when Stim defines them; unsupported/missing required geometry fails closed.

`decode_checked` validates the input `DetectorBatch`, decoder registration, return type, metadata equality, and `[shots, observables]` output shape. It does not run selection or scoring and receives no logical labels.

## No premature model-specific adapter

No CNN, transformer, hypergraph, tensor-network, HAMLD, or other decoder-specific adapter is introduced here. A research method needing soft data, syndrome history, graph edits, correlated factors, or another code distance must propose a versioned representation and prove deterministic mapping before integration. No such requirement is inferred for HAMLD in this change.

## Compatibility is not evidence of performance

Passing this gate establishes only that declared circuit and array semantics match and that the prediction contract is followed. It does not establish model fidelity, physical validity, runtime suitability, or improvement. Paired evaluation, independent roots, predeclared statistics, and a separate audit would be required for performance claims.
