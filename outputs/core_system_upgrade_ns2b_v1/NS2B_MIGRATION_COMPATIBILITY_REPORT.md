# NS-2B Migration and Compatibility Report

## Summary

NS-1 combined the generating circuit and one DEM in `CircuitIdentity`, placed that digest in `DetectorBatch`, and required the decoder noise identity to equal the generating-noise identity. That is safe for one model but prevents clean pairing of different DEM models on the same detector samples and rejects a legitimate nominal-fixed decoder when the generating noise differs.

NS-2B adds `SamplingIdentity` for the actual Stim data source and `DecoderModelIdentity` per decoder. The batch carries only sampling/circuit ordering identity. Each model carries its own optional DEM and assumptions. Distinct DEM digests are retained. No DEM equivalence is inferred.

## Migration

1. Existing NS-1 callers may remain on `CircuitIdentity` and `decode_checked`; their original exact-noise compatibility rule is retained.
2. New paired evaluations involving distinct decoder models should create one `SamplingIdentity` from the actual generating circuit/noise record.
3. Build each decoder's own `DEMConstructionRecord` with explicit `DEMConstructionSettingsV2`, or use `dem_record=None` for a non-DEM decoder.
4. Create a `DecoderModelIdentity` for each decoder, explicitly naming its supported sampling identity, assumed-noise provenance, correlation semantics, input representation, and resources.
5. At the trusted sampling boundary, use `TrustedDetectorBatchAdapter`, passing the source circuit, detector samples, and ordered IDs from the sampler's documented output.
6. Register candidates through `IdentityAwareDecoderRegistry`. Keep the existing fixed PyMatching instance as the fallback and use the existing opt-in selector for experimental models.
7. Evaluate only development scopes through `evaluate_identity_aware_paired`; keep protected evaluation on its separately authorized frozen workflow.

## Baseline preservation

No changes were made to `PyMatchingDecoder` construction/decode semantics, its correlation-mode flag, `dashboard/simulator.py`, dashboard configuration, or dashboard endpoints. Existing deterministic core tests still verify both explicit PyMatching correlation modes and the distance-3/five-round dashboard zero-syndrome behavior. The v2 registry wraps the existing registry rather than replacing it.

## Deterministic compatibility evidence

The tests construct Stim circuits and DEMs without invoking any sampler. They verify that decomposed and undecomposed/nominal DEM records remain distinct while their models can target the same sampling identity; a nominal assumed noise ID can differ from the generating noise ID; wrong circuit/order/observable semantics fail; mutable metadata and arrays are detected or isolated; labels are not passed to decoders; and fixed fallback/experimental opt-in continue to work.

## Explicit non-claims

This work does not integrate HAMLD. Research Codex reports its parser structure verified but compiled decoder inference unverified. It does not establish decoder compatibility with HAMLD, performance, scientific generalization, DEM distributional equivalence, physical hardware operation, or any Q-SHIFT improvement.
