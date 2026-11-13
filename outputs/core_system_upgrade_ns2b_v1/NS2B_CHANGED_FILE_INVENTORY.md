# NS-2B Changed-File Inventory

## Base and publication state

- Base commit: `e015a18e22de653b479cc206026d520e7dc71b5d`
- Branch: `codex/ns2b-sampling-model-identity`
- Current HEAD remains the base commit; implementation is uncommitted for review.
- No commit, push, merge, or PR was made.

## Implementation/test changes

1. `qshift_core_v1/sampling_model_identity.py` — new versioned SamplingIdentity, DecoderModelIdentity, DEM records/settings, trusted batch adapter, checked decoder, registry wrapper, and paired evaluator.
2. `qshift_core_v1/contracts.py` — strict DecoderPrediction metadata and elapsed-time validation.
3. `qshift_core_v1/circuit_identity.py` — hardening of the existing NS-1 `decode_checked` boundary.
4. `qshift_core_v1/__init__.py` — additive public exports for v2 contracts.
5. `dashboard/tests/test_sampling_model_identity_v2.py` — deterministic NS-2B tests, with no sampling.

## New NS-2B evidence/documentation

- `outputs/core_system_upgrade_ns2b_v1/NS2B_SAMPLING_MODEL_IDENTITY_DESIGN.md`
- `outputs/core_system_upgrade_ns2b_v1/NS2B_MODEL_INFORMATION_PARITY_POLICY.md`
- `outputs/core_system_upgrade_ns2b_v1/NS2B_MIGRATION_COMPATIBILITY_REPORT.md`
- `outputs/core_system_upgrade_ns2b_v1/NS2B_LIMITATIONS_AND_UNRESOLVED.md`
- `outputs/core_system_upgrade_ns2b_v1/NS2B_IMPLEMENTATION_REPORT.md`
- `outputs/core_system_upgrade_ns2b_v1/NS2B_FAILURE_INVESTIGATION.md`
- `outputs/core_system_upgrade_ns2b_v1/NS2B_CHANGED_FILE_INVENTORY.md`
- `outputs/core_system_upgrade_ns2b_v1/NS2B_REVIEW_PACKAGE_CONTENTS.md`
- `outputs/core_system_upgrade_ns2b_v1/REPRODUCE_NS2B.md`
- `outputs/core_system_upgrade_ns2b_v1/NS2B_VALIDATION_RESULTS.json`
- `outputs/core_system_upgrade_ns2b_v1/NS2B_TEST_RESULTS.txt` — combined-suite failure preserved.
- `outputs/core_system_upgrade_ns2b_v1/NS2B_FOCUSED_REGRESSION_RESULTS.txt`
- `outputs/core_system_upgrade_ns2b_v1/NS2B_DASHBOARD_COMPATIBILITY_RESULTS.txt`
- `outputs/core_system_upgrade_ns2b_v1/NS2B_BASE_COMPARISON_TEST_RESULTS.txt`
- `outputs/core_system_upgrade_ns2b_v1/create_manifest.py`
- `outputs/core_system_upgrade_ns2b_v1/verify_manifest.py`
- `outputs/core_system_upgrade_ns2b_v1/create_review_package.py`
- `outputs/core_system_upgrade_ns2b_v1/NS2B_ENGINEERING_MANIFEST.json`

No dashboard implementation, frozen research source/configuration, protected result, raw dataset, checkpoint, dependency, cache, or unrelated repository file is included in the review package.
