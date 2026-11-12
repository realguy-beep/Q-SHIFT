# NS-1 Circuit Identity Contract

**Status:** engineering compatibility contract; no decoder-performance claim.
**Parent:** accepted core v1.1 milestone `022588c7e9513d923da0b7f342a6199e34873b38`.

## Purpose

Equal detector counts do not establish that two arrays mean the same thing. NS-1 adds an explicit, versioned identity for the Stim circuit, its detector error model (DEM), detector order, observable convention, noise provenance, and DEM-conversion settings. It does not change sampling, decoder algorithms, the dashboard baseline, or any research protocol.

## Identity fields

`qshift_core_v1.circuit_identity.CircuitIdentity` uses schema `qshift-circuit-identity-v1` and records:

- SHA-256 of UTF-8 `str(circuit)` and UTF-8 `str(dem)` independently.
- Stim version; exact supported-model identity hashes therefore also distinguish serialization/runtime versions.
- Explicit code family, distance, rounds, and memory basis. A caller must supply each field or explicitly use `None`; an unknown is preserved and prevents compatibility from being asserted.
- Stim detector IDs in declared order (`0..num_detectors-1`), circuit coordinates and DEM coordinates per ID, with `None` retained when a coordinate is not present.
- Detector-order fingerprint over the ordered IDs and both coordinate maps.
- Stim observable IDs in declared order and caller-supplied interpretation for each observable. Missing interpretation remains `None` and fails compatibility.
- Explicit noise-model identity and SHA-256 of the caller-supplied JSON-compatible construction record. The record itself is not embedded in the identity object.
- Explicit `decompose_errors`, `approximate_disjoint_errors`, and a construction note in `DEMConstructionSettings`.

The full `identity_sha256` is a canonical JSON hash over these fields. Circuit and DEM hashes remain separately inspectable; decoder implementation/version is deliberately not part of circuit identity.

## Array and decoder compatibility

`DetectorBatch` requires unpacked binary `uint8`-compatible `[shots, detectors]` data, a circuit identity hash, a detector ID for every column, and an expected detector-order fingerprint. `validate_detector_batch` checks dimensions, declared identity, IDs, and fingerprint. A declared permutation is rejected even if the number of columns is unchanged.

`ExternalDecoderSpec` separately declares the decoder implementation metadata, accepted representation, exact supported circuit-identity hashes, detector-order hash, observable IDs and convention, noise assumption, correlation mode, provenance, resource requirements, and whether coordinates are required. `assert_decoder_compatible` fails closed on unknown required semantics or any mismatch. `decode_checked` checks both the registration contract and the returned `DecoderPrediction` before returning it.

The adapter requires exact supported identity hashes. It does not silently translate packed bits, reorder detector columns, infer a memory basis, convert observables, or convert a neural output into matching weights.

## Provenance limits

These are consistency checks on the declarations supplied by a caller. A hash does not prove who generated a circuit or array, whether calibration was authorized, whether data leaked, or whether a column declaration is truthful. Upstream data provenance and experiment authorization remain separate responsibilities. A decoder must still be independently validated and explicitly selected; the identity contract never activates a decoder automatically.

## Current dashboard fixture

The deterministic test builds the existing rotated surface-code Z-memory, distance-3, five-round Stim circuit and its configured DEM without sampling. Stim reports 40 detector IDs and one observable. Coordinates are retained as returned, including six time-coordinate slices (initial slice plus five measurement-round slices). These observed coordinates are not generalized into a claim that every circuit uses the same coordinate convention.
