# NS-2B Supervisor Review Package Contents

The package generator uses this explicit file list and preserves repository-relative paths beneath `Q-SHIFT/`.

- `qshift_core_v1/__init__.py`
- `qshift_core_v1/contracts.py`
- `qshift_core_v1/circuit_identity.py`
- `qshift_core_v1/sampling_model_identity.py`
- `dashboard/tests/test_sampling_model_identity_v2.py`
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
- `outputs/core_system_upgrade_ns2b_v1/NS2B_TEST_RESULTS.txt`
- `outputs/core_system_upgrade_ns2b_v1/NS2B_FOCUSED_REGRESSION_RESULTS.txt`
- `outputs/core_system_upgrade_ns2b_v1/NS2B_DASHBOARD_COMPATIBILITY_RESULTS.txt`
- `outputs/core_system_upgrade_ns2b_v1/NS2B_BASE_COMPARISON_TEST_RESULTS.txt`
- `outputs/core_system_upgrade_ns2b_v1/NS2B_ENGINEERING_MANIFEST.json`
- `outputs/core_system_upgrade_ns2b_v1/create_manifest.py`
- `outputs/core_system_upgrade_ns2b_v1/verify_manifest.py`
- `outputs/core_system_upgrade_ns2b_v1/create_review_package.py`

The package excludes the archive itself, all other `outputs/` content, research or protected evaluation results, independent-test material, raw data, model weights, checkpoints, caches, virtual environments, installed dependencies, secrets, and unrelated website/presentation files. It is constrained to less than 32 MiB and validates its internal ZIP CRC before reporting success.

Create it with:

```powershell
python outputs/core_system_upgrade_ns2b_v1/create_review_package.py --output "C:\Users\LENOVO\Documents\Codex\2026-11-12\QSHIFT_NS2B_Supervisor_Review.zip"
```
