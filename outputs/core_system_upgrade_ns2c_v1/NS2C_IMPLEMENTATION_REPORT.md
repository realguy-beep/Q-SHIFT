# NS-2C — Decoder Integration and Paired Evaluation

## Scope and outcome

NS-2C adds a typed execution boundary for multiple decoder implementations on one NS-2B `DetectorBatch`. The work is engineering infrastructure only. It does not change the V1 PyMatching implementation, decoder algorithms, scientific protocols, or prior results. No Stim sampler, training job, benchmark study, or protected evaluation was run. No commit, push, merge, or PR was created.

**Outcome: PASS for the bounded engineering milestone.** The new deterministic tests and selected NS-2B/NS-1/core regression suites pass. This is not a decoder-performance result.

## Files added

- `qshift_core_v1/decoder_runtime_v2.py` — checked adapter protocol, compatibility-aware bank, paired evaluation, and deterministic parity fixture decoder.
- `dashboard/tests/test_decoder_runtime_v2.py` — deterministic adapter, real PyMatching, pairing, failure, mutation, opt-in, and label-isolation tests.
- `outputs/core_system_upgrade_ns2c_v1/NS2C_IMPLEMENTATION_REPORT.md` — this report.
- `outputs/core_system_upgrade_ns2c_v1/NS2C_VALIDATION_RESULTS.json` — machine-readable test and environment record.
- `outputs/core_system_upgrade_ns2c_v1/REPRODUCE_NS2C.md` — reproduction commands and integration example.
- `outputs/core_system_upgrade_ns2c_v1/NS2C_ENGINEERING_MANIFEST.json` — SHA-256 inventory of the NS-2C source, test, and report artifacts.

The existing NS-2B files and its manifest were left untouched. NS-2B remains uncommitted as received; this task adds to that worktree without committing it.

## Interface

`DecoderAdapter` exposes `name`, `version`, `model_identity`, `sampling_identity`, and `predict(DetectorBatch)`. `CheckedDecoderAdapter` wraps an implementation conforming to the existing `DecoderProtocol` and checks its `DecoderModelIdentity` against the exact `SamplingIdentity` before every call. Each call receives a fresh defensive detector copy. Returned type, metadata, binary values, observable dimensions, and shot count are validated; prediction storage is detached and marked read-only.

Each call returns a `DecoderExecution`: `ok` or `failed`, model identity and provenance, measured wall time, decoder-reported time, and either a validated prediction or failure type/message. Failed calls contain no predictions. Nothing substitutes the fixed decoder's output for a failed arm.

`CompatibilityAwareDecoderBank` rejects duplicate names, unsupported circuit identities, and experimental decoders unless that registration explicitly opts in. Its `selector()` delegates to the existing `SafeDecoderSelector`; callers still designate the strong fixed fallback. Distinct decoder-assumed noise models may share one sampling identity, while each model's own DEM and provenance remain separate.

`evaluate_paired_batch` sends the same immutable detector bytes to all requested decoders. It accepts optional observable labels only for `development` or `heldout-development`; labels are first read after all decoder calls and never enter decoder methods. It reports each successful arm's errors/LER when labels are supplied, prediction disagreements, candidate-only and baseline-only failures, and per-arm timing. If an arm fails, its failure remains visible and its paired result is unavailable. The development evaluator refuses `protected-test` scope.

Hashes identify the supplied arrays and model declarations; they do not prove upstream data provenance, authorization, or absence of leakage.

## Deterministic demonstration

The integration fixture manually creates four 40-detector rows: all-zero, detector 0 set, detector 1 set, and detectors 0+1 set. Two deterministic parity decoders predict from detector 0 and detector 1 respectively. With fixed fixture labels `[0, 1, 1, 0]`, the harness reports:

| Engineering fixture arm | Errors / shots | LER | Paired disagreement vs fixed | Candidate-only | Fixed-only |
|---|---:|---:|---:|---:|---:|
| Parity on detector 0 (fixed fixture) | 2 / 4 | 0.50 | — | — | — |
| Parity on detector 1 (candidate fixture) | 2 / 4 | 0.50 | 2 / 4 | 1 | 1 |

These values are deliberately constructed interface-test outputs, not sampled shots or QEC performance evidence. A separate deterministic test builds an actual PyMatching decoder from a frozen fixture DEM and verifies that adapter predictions exactly match direct `PyMatchingDecoder.decode` predictions for the same four manually supplied detector rows. It confirms output shape `(4, 1)` and preserves the declared correlation mode. No Stim sampling API is called.

## Validation

Command:

```powershell
python -m unittest dashboard.tests.test_decoder_runtime_v2 dashboard.tests.test_sampling_model_identity_v2 dashboard.tests.test_circuit_identity_v1 dashboard.tests.test_core_system_v1 -v
```

**Result: 70 tests passed, 0 failed** (8 NS-2C test methods, plus the selected NS-2B, NS-1, and core V1 regression suites). Also passed:

```powershell
python -m compileall -q qshift_core_v1\decoder_runtime_v2.py dashboard\tests\test_decoder_runtime_v2.py
```

Environment: Python 3.12.10, Stim 1.16.0, PyMatching 2.4.0, NumPy 2.5.3, FastAPI 0.162.0, Starlette 1.10.0. The existing test `test_existing_correlation_modes_construct_and_decode_without_sampling` passed for both explicit modes. The actual PyMatching adapter test passed with correlation mode disabled and output identity matching direct decode.

The known broader structured-training freeze-integrity failure remains classified as **baseline-preexisting**, reproduced on accepted NS-1 base `e015a18e22de653b479cc206026d520e7dc71b5d`; it was not changed or rebaselined here. The existing [NS-2B failure investigation](../core_system_upgrade_ns2b_v1/NS2B_FAILURE_INVESTIGATION.md) records that `structured_diagnostic_config.json` expected `1ef0e84b7a2ede6968e6e09f3f8095dd1413b52d7a5142d410afff1d0e975799` but was `35ea9d9b9c5031f624f4fee5c5796afa4ce1c2c322f7694854d59f3ad2d7d7b0`, and `structured_seed_inventory.json` expected `ce044c465f9dea959f4b5c34f92fc256433b224d2bfc3f76f9a2e040a7eaec7d` but was `559cca69f74a847aa6c4096e2935b39a519575f53118cfe9080ce5d22025db58`. The broad suite containing that known failing check was not rerun.

## Research Codex integration steps

1. Build a `SamplingIdentity` for the exact generated circuit and a `StimDEMArtifact` for each decoder's assumed model. Do not conflate generating-noise identity with decoder-model identity.
2. Construct the research decoder with the existing detector-in/observable-prediction-out contract, then create a matching `DecoderModelIdentity` with explicit assumed-noise provenance, DEM settings/digest when applicable, detector ordering, observable semantics, and resources.
3. Wrap it with `CheckedDecoderAdapter`; register it in `CompatibilityAwareDecoderBank`. Set `metadata.experimental=True` during development and pass `experimental_opt_in=True` only in an explicitly experimental integration run.
4. Register the unchanged PyMatching baseline as the declared fixed fallback in the existing selector. Submit `SelectionProposal` only through the existing causal controller contract; this runtime layer does not select algorithms.
5. Call `evaluate_paired_batch` once with the shared `DetectorBatch`, all decoder names, declared baseline, a development-only scope, and labels only when authorized for scoring. Inspect each arm's status before interpreting pairwise results.
6. For graph, hypergraph, or alternative detector representations, add a separately versioned input adapter and explicit circuit-compatibility contract. This NS-2C implementation supports only the NS-2B unpacked binary `[shots, detectors]` representation; it does not claim generic graph/hypergraph compatibility.

## Remaining blockers and boundaries

- No external Research Codex decoder is available or integrated here; its exact model requirements remain unknown.
- The NS-2C boundary validates declared identity and array semantics, not the truth of a decoder's claimed provenance or physical model.
- The deterministic parity decoder exists solely as an integration fixture and is not a quantum decoder.
- Protected-test scoring remains intentionally unavailable in this development API.
- This milestone establishes compatibility and failure-reporting mechanics only. No decoder improvement or scientific superiority is established.
