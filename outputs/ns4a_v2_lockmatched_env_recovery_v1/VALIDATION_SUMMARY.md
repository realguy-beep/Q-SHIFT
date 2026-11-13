# Validation summary

**Outcome: deterministic compatibility preflight PASS.** This is not authorization to sample and not a scientific decoder comparison.

## Commands and results

All commands were run from the Q-SHIFT repository root in PowerShell using the isolated Python 3.12.10 environment.

```powershell
$py = 'C:\Users\LENOVO\Documents\Codex\2026-11-13\qshift-ns4a-v2-lockmatched-venv\Scripts\python.exe'
& $py -m py_compile `
  outputs/ns4a_v2_lockmatched_env_recovery_v1/record_source_inventory.py `
  outputs/ns4a_v2_lockmatched_env_recovery_v1/verify_lock_environment.py `
  outputs/ns4a_v2_lockmatched_env_recovery_v1/run_lockmatched_preflight.py `
  outputs/ns4a_v2_lockmatched_env_recovery_v1/verify_lockmatched_preflight.py
& $py outputs/ns4a_v2_lockmatched_env_recovery_v1/verify_lock_environment.py
& $py outputs/ns4a_v2_lockmatched_env_recovery_v1/record_source_inventory.py
& $py outputs/ns4a_v2_lockmatched_env_recovery_v1/run_lockmatched_preflight.py
& $py outputs/ns4a_v2_lockmatched_env_recovery_v1/verify_lockmatched_preflight.py
```

Results:

- Compilation: PASS.
- Locked environment and `pip check`: PASS.
- Source allowlist inventory: 20 local sources + 2 exact upstream Git-object inputs; all local source bytes match the base commit, and imported adapter source matches the published upstream source blob.
- Artifact manifest: 16 listed files verified using CRLF-to-LF normalized SHA-256/byte counts; self-hash excluded by design.
- Deterministic runner: PASS, 6 circuits, 6 DEMs, 12/12 candidate rows.
- Independent saved-artifact reconstruction: PASS, 12/12 rows, no failures; its separate failure-injection implementation also passed all three cases on every row.
- Deterministic contract and failure-isolation checks: 11/11 true; all three registration failure-injection cases were repeated across 12 candidate banks and aggregated conjunctively.
- Sampler calls: 0; sampled shots: 0; labels read: 0; model selections: 0.

The runner's single-fixture timing entries are diagnostic only. No throughput benchmark was run. The earlier package-index timeout was resolved by retrying the same lock; exact pins remained unchanged.

Single-call construction/decode diagnostics (not a throughput benchmark): PyMatching construction median 1.429 ms, decode median 0.313 ms; BeliefMatching construction median 20.709 ms, decode median 0.353 ms. Per-row ranges and full precision are retained in the compatibility matrix.

## Coverage and limitations

All six configured noise conditions were retained. There were no skipped rows. Matching and BeliefMatching each decoded the same deterministic synthetic fixture for a row; no outcome labels were provided. Successful construction establishes API/contract compatibility for these DEMs and the tested fixture only. It does not establish comparable decoding accuracy, physical fidelity, model identifiability, or adaptive utility.

No historical outcome, Stage 5, or sealed-test file was opened. No experimental sampling or training was performed.
