# Independent audit summary

## Audit performed

The v3.4.4 auditor (`outputs/stage5_execution_safety_v3_4_4/audit_saved_run_v44.py`) operated on the recovery copy after all roots were complete. It independently read the saved arrays and reconstructed the required decoder instances. It did not rely on the runner's aggregate counters for its audit result.

For every expected condition/root archive, it checked the committed archive hash and marker, phase, detector/observable/prediction dimensions, binary values, probability/root identity, calibration estimate, frozen calibration/evaluation seed mapping, and all three stored predictions by decoding the saved detectors again. It then recomputed per-root logical errors and paired discordances.

## Results

- Audit status: `PASS_INDEPENDENT_AUDIT`.
- Expected roots and audited roots: 6,050 / 6,050.
- Checkpoint/archive hashes verified: 6,050 / 6,050.
- Unique shots independently recomputed: 27,225,000.
- Stored predictions matched independent re-decoding for all roots.
- Independent-test access recorded by the run: 0.
- The post-audit package verifier matched all 6,050 per-root audit rows against the runner summary and reproduced the frozen inferential output.

The full `INDEPENDENT_AUDIT.json` is included unchanged. Its per-root entries let reviewers recompute the reported error counts and paired effects without access to raw shot arrays.

## Independence and limits

“Independent audit” here means a separate saved-array audit implementation/process from the sampling/reporting code, followed by a separate package-level reconciliation. It is **not** an external third-party audit. Raw `.npz` archives are intentionally not published, so an external reviewer can recompute the per-root aggregates from the included audit records but cannot independently re-decode the original detector arrays using this GitHub package alone.

The original failed-run evidence remains available locally and unchanged. The historic expected hash for the v3.4.2 raw safety-test JSON could not be recovered; its discrepancy is disclosed in this package and its original/current hashes are retained in the manifests and limitations.
