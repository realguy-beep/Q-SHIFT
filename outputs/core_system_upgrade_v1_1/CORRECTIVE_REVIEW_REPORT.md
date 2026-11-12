# Core Upgrade v1.1 — Corrective Review

**Reviewed milestone:** `feb8c23715f0270e9c9ce1bb6444e414a26976bc`
**Branch:** `codex/core-system-upgrade`
**Scope:** decoder prediction integrity, causal index validation, paired-evidence identity, and NS-0 engineering handoff. No experiments or hardware work.

## Corrections

1. `qshift_core_v1/evaluation.py` now requires each registered candidate to expose typed `DecoderMetadata` and a callable `decode`. It requires a `DecoderPrediction` result, verifies its metadata exactly equals the metadata captured at registration, detects metadata mutation during evaluation, and checks the prediction's dimensions and optional elapsed-time value. Dataclass equality checks identity, implementation/version, detector and observable dimensions, noise-model identity, correlation mode, experimental status, and construction provenance.
2. `qshift_core_v1/controller.py` now accepts only nonnegative, strictly increasing integer current-block indices. A proposal's `based_on_through_block` must be a nonnegative integer strictly earlier than the block being selected. Block zero therefore cannot be selected from a fabricated negative sentinel. Invalid proposal timing falls back to the registered fixed decoder. Hysteresis, dwell, confidence checks and the fallback path remain in place.
3. The paired-evaluation record retains existing schema version 1 and the existing top-level `sample_sha256` behavior for consumers. It additively records source and canonical shape/dtype, binary and column-order conventions, the complete registered decoder metadata, and `sample_identity.evidence_sha256`. The output states that hashes identify content and metadata only; they do not prove upstream provenance, authorization, or absence of leakage.

## Validation

Deterministic checks passed:

- `python -m unittest dashboard.tests.test_core_system_v1 -v` — 35 tests passed.
- `python -m unittest dashboard.tests.test_dashboard.SeedAndConfigTests dashboard.tests.test_dashboard.MetricAndStorageTests -v` — 11 passed.
- `python -m unittest dashboard.tests.test_dashboard.StructuredDecoderTests.test_qshift_stim_coordinates_make_expected_round_geometry dashboard.tests.test_dashboard.StructuredDecoderTests.test_residual_target_and_xor_correction_convention -v` — 2 passed.
- `python -m compileall -q qshift_core_v1 dashboard\configuration.py dashboard\seed_protocol.py dashboard\simulator.py dashboard\tests\test_core_system_v1.py outputs\core_system_upgrade_v1_1` — passed.
- `node --check dashboard\static\app.js` and Python HTML parsing — passed.
- `python outputs\core_system_upgrade_v1_1\audit_v2_4_hold.py` — 17 entries checked; 13 expected-hash mismatches retained and reported; all entries match base content after newline normalization; authorization flags remain false.

The PyMatching checks cover both explicit correlation modes on deterministic supplied detector rows. The legacy Phase 2B compatibility call still constructs/uses correlation-enabled matching and returns its original one-dimensional single-observable output. The test suite does not call Stim's sampler: one test constructs the configured circuit/DEM and decodes an explicitly supplied zero syndrome; other sampling-path tests use fake sampler objects or reject input before any sampler invocation.

## Integrity and boundary

No frozen scientific source, seed inventory, protocol, result, prediction archive, Stage 5 evidence, protected-test material, or exhibition files were changed or read for outcomes. No Stim sampling, training, benchmark, or hardware interaction occurred. V2.4 remains HOLD. Its pre-existing 13-of-17 expected-hash discrepancy is not described as a successful historical freeze verification; see `V2_4_HOLD_CONFIRMATION.md`.

This is source-level and deterministic contract validation, not an independent performance audit and not evidence that a future decoder improves on fixed PyMatching.

The original `outputs/core_system_upgrade_v1/MANIFEST.json` is retained as the accepted v1 snapshot. The v1.1 manifest separately hashes the corrected shared source, regression tests, new audit output, and v1.1 reports; the earlier manifest is not rewritten to conceal that those shared source files have since changed.
