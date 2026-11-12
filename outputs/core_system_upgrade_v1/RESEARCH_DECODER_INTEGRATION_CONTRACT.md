# Research Decoder Integration Contract — Q-SHIFT Core v1

**Status:** infrastructure contract only. A decoder connected through this API is experimental until independent, paired evaluation supports its claims.

## Python interface

Implement DecoderProtocol from qshift_core_v1.contracts:

    metadata: DecoderMetadata
    decode(detectors: numpy.ndarray) -> DecoderPrediction

### Input and output

- Input is an unpacked numeric binary matrix with shape [shots, detectors]; packed bytes, soft probabilities, observable labels, hidden regime IDs, and future blocks are not accepted as decoder input by the shared evaluator.
- Output is an unpacked binary matrix with shape [shots, observables]. A scalar logical observable is still represented as [shots, 1] in the core API.
- dashboard.simulator.decode_matching retains its legacy [shots] result shape for the current one-observable dashboard callers.
- Nonbinary values, nonfinite values, wrong dimensions, changed shot count, and malformed estimates fail with descriptive errors.
- Optional runtime is seconds spent in the decoder call; it is not total end-to-end experiment time.

## Required metadata

DecoderMetadata records a stable decoder name, implementation/version, detector and observable counts, assumed noise-model identifier, PyMatching correlation mode (or None for non-matching decoders), experimental status, and construction provenance. A new implementation must not call itself a replacement for PyMatching by merely satisfying the API.

For PyMatching, construct through PyMatchingDecoder.from_detector_error_model(dem, correlation_mode=...). The adapter passes the same boolean at graph construction and decode_batch. A legacy instance may be wrapped only when the caller can identify its construction setting; the adapter records that it is a caller-verified model. Current Phase 2B code constructs its bank with correlations enabled and decodes with enable_correlations=True; the adapter preserves this behavior.

## Noise assumptions and supported scope

- The existing dashboard pilot is locked to Stim rotated surface-code X/Z memory, distance 3, five rounds, 40 detectors, one logical observable. Its actual source is the Phase 2B categorical Pauli generator.
- Its matching DEM is generated with decompose_errors=True, approximate_disjoint_errors=True. Correlated matching consumes decomposition metadata that survives this conversion; it does not make the approximation exact.
- Other distances, rounds, code families, observable counts, DEM decompositions, or correlated-noise mechanisms require their own detector/observable compatibility tests and a separately reviewed protocol.
- An alternative decoder must declare the physical/noise model it assumes. A detector-profile estimate cannot be silently promoted to a true circuit-noise model.

## Calibration and adaptive selection

- Any deployable NoiseEstimate must be detector-only, identify its calibration-shot count and parameter values, and come from data available before the block it influences.
- Each estimator/DEM builder must validate parameter-specific physical ranges; the shared estimate container only enforces finite numeric values because quantities such as a Pauli bias ratio are not probabilities and can exceed one.
- It must not include logical labels, true injected fault flags, hidden generating regime, or current/future evaluation data.
- The controller proposal identifies a target decoder, confidence and last block used. based_on_through_block >= current_block fails closed.
- The current controller requires confidence, hysteresis and dwell for specialist selection and returns to the registered fixed baseline on low confidence, missing estimates, unsupported decoder names or noncausal proposals.
- Selection logs retain both estimated and configured noise mappings so they cannot be conflated.
- Experimental decoders require explicit opt-in in the selector. The fixed fallback must be registered and marked nonexperimental.

## Evaluation and activation gate

evaluate_paired consumes one supplied detector/observable pair and runs every candidate on the same detector rows. Labels are used after decoding only to calculate residual logical errors. It stores sample ID/hash, raw error counts/rates, runtime and shot-level paired discordances. It allows development and held-out-development scopes and refuses protected-test; a frozen study’s separately authorized runner/auditor must own that boundary.

Before a research decoder is activated outside an engineering fixture, require:

1. Deterministic input/output, detector ordering, observable convention, and noise-model compatibility tests.
2. Frozen source/configuration/seed hashes and leakage review.
3. Independent roots with paired detector/observable samples across all candidates.
4. A predeclared analysis, practical-effect criterion, uncertainty method and stopping rule.
5. Independent saved-array rescoring and a passed audit.
6. A reported fixed-PyMatching fallback and no-harm assessment.

This release does not run those experiments and makes no performance claim.
