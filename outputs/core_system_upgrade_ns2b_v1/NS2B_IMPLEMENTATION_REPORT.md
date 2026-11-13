# NS-2B Implementation and Validation Report

## Result

The NS-2B v2 contract is implemented additively on branch `codex/ns2b-sampling-model-identity`, based on accepted NS-1 commit `e015a18e22de653b479cc206026d520e7dc71b5d`. This is engineering validation only. No decoder research implementation was integrated, and no sampling/training/benchmark/protected evaluation was run.

## Changed files

- `qshift_core_v1/sampling_model_identity.py` — v2 sampling/model identities, complete Stim DEM construction record, immutable detector batch adapter, checked inference, compatibility-aware registry, and paired evaluator wrapper.
- `qshift_core_v1/circuit_identity.py` — hardening of the existing v1 `decode_checked` boundary for metadata mutation, strict time values, output validation, copied input, and detached output.
- `qshift_core_v1/contracts.py` — `DecoderPrediction` now validates metadata type and requires elapsed time to be a finite nonnegative real value; booleans are rejected.
- `qshift_core_v1/__init__.py` — additive exports for v2 contracts.
- `dashboard/tests/test_sampling_model_identity_v2.py` — deterministic v2 and v1-boundary regression tests.
- `outputs/core_system_upgrade_ns2b_v1/` — design, migration, information-parity, limitations, reproduction, test evidence, and allowlisted manifest tooling.

No dashboard source, research protocol, Stage 5 file, protected result, old manifest, freeze, or NS-1 historical report was modified.

## Validation

Commands and exact results are saved in `NS2B_FOCUSED_REGRESSION_RESULTS.txt`, `NS2B_DASHBOARD_COMPATIBILITY_RESULTS.txt`, `NS2B_TEST_RESULTS.txt`, `NS2B_BASE_COMPARISON_TEST_RESULTS.txt`, and `NS2B_VALIDATION_RESULTS.json`. The focused NS-1/core suites passed 62/62, and direct local dashboard health/control and IPv6 WebSocket checks passed 2/2. A broader 92-test combined run had one error: an existing structured-training API test stopped when `load_prepared_freeze()` rejected `structured_diagnostic_config.json` integrity. I reran that exact test on a clean detached worktree at accepted NS-1 base `e015a18e22de653b479cc206026d520e7dc71b5d`; it failed at the same integrity check. The failure is therefore classified **baseline-preexisting**, not NS-2B-introduced. No structured-training source/configuration/freeze was changed or rebaselined. Tests construct Stim circuits and DEMs, create fixed in-memory detector matrices, and run deterministic decoder calls on those matrices; no sampler method is invoked. The dashboard's distance-3/five-round decode path also passes the existing deterministic zero-syndrome regression.

## Assessment

The contract now allows multiple decoder models with different DEM and assumed-noise identities to consume one detector batch when each explicitly supports the exact sampling identity and its detector/observable semantics match. A nominal model can differ from the generator's noise record. No DEM equivalence or decoder performance claim is made. The previous fixed PyMatching adapter and SafeDecoderSelector remain the operational baseline/fallback.

## Remaining limits

Metadata and hashes cannot prove that arbitrary arrays came from the claimed sampler or that an external decoder used its declared model. The adapter reduces accidental relabeling/permutation and mutable-buffer risks; upstream provenance and process-level information-flow assurance still need controlled sampler code, independent review, and future experiment design. No HAMLD inference dependency/API is available or verified.
