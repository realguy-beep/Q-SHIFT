# Reproduce the lock-matched deterministic preflight

Run only in the isolated environment recorded in `ENVIRONMENT_PROVENANCE.md`. The commands below perform dependency/source checks, construct six circuits and DEMs, and decode only the source-defined deterministic fixture. They do not call a Stim sampler.

From the repository root in PowerShell:

```powershell
$py = 'C:\Users\LENOVO\Documents\Codex\2026-11-13\qshift-ns4a-v2-lockmatched-venv\Scripts\python.exe'
& $py outputs/ns4a_v2_lockmatched_env_recovery_v1/verify_lock_environment.py
if ($LASTEXITCODE -ne 0) { throw 'Lock-matched environment verification failed' }
& $py outputs/ns4a_v2_lockmatched_env_recovery_v1/record_source_inventory.py
if ($LASTEXITCODE -ne 0) { throw 'Source inventory verification failed' }
& $py outputs/ns4a_v2_lockmatched_env_recovery_v1/run_lockmatched_preflight.py
if ($LASTEXITCODE -ne 0) { throw 'Deterministic preflight failed' }
& $py outputs/ns4a_v2_lockmatched_env_recovery_v1/verify_lockmatched_preflight.py
if ($LASTEXITCODE -ne 0) { throw 'Independent deterministic audit failed' }
& $py outputs/ns4a_v2_lockmatched_env_recovery_v1/build_artifact_manifest.py
if ($LASTEXITCODE -ne 0) { throw 'Artifact manifest generation failed' }
& $py outputs/ns4a_v2_lockmatched_env_recovery_v1/verify_artifact_manifest.py
if ($LASTEXITCODE -ne 0) { throw 'Artifact integrity check failed' }
```

To create the isolated environment from scratch, use the pinned lockfile at the source commit stated in `ENVIRONMENT_PROVENANCE.md`; do not edit it or substitute dependency versions. Package installation is not part of the test commands above. The environment directory is outside the repository.

Expected outputs: `DEPENDENCY_VERIFICATION.json`, `SOURCE_INPUT_INVENTORY.json`, `BELIEFMATCHING_COMPATIBILITY_MATRIX.json`, `LOCKMATCHED_PREFLIGHT_SUMMARY.json`, and `INDEPENDENT_PREFLIGHT_VERIFICATION.json`.

The earlier blocked preflight directory is historical and must not be overwritten.
