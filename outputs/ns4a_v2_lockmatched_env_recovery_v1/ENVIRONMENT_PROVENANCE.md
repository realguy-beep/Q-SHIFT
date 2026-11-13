# NS-4A V2 lock-matched environment recovery

## Result

The dependency discrepancy was resolved in a new isolated virtual environment. The existing NS-3B lockfile was read from its exact recorded Git object and copied without edits. The lock-matched install and environment verifier passed; no packages were installed into or removed from the existing global/project Python environment.

This is deterministic compatibility evidence only. It is not a sampling, accuracy, or performance experiment.

## Environment identity

- Repository branch: `codex/ns4a-v2-lockmatched-env`
- Base/HEAD before publication: `2ba57e83e262ca32afe4cb58063d2e3e63605e3b`
- Isolated environment: `C:\Users\LENOVO\Documents\Codex\2026-11-13\qshift-ns4a-v2-lockmatched-venv`
- Python executable: `C:\Users\LENOVO\Documents\Codex\2026-11-13\qshift-ns4a-v2-lockmatched-venv\Scripts\python.exe`
- Python: 3.12.10; `include-system-site-packages=false`
- NumPy discrepancy resolved: the earlier blocked preflight reported 2.5.3; this isolated environment uses the lock-required 2.2.6.
- Lockfile SHA-256: `403d567f1063e5406fac93e9292ddb43a5524c274992b9dff29d14ddf06a3fac`
- Lock source: exact commit `e4ff201e3db18a2d18e7474bef4a83542eaa3da8`, `outputs/qshift_ns3_decoder_research/ns3b_beliefmatching/requirements-ns3b.lock.txt`
- BeliefMatching: 0.2.0, upstream `https://github.com/oscarhiggott/BeliefMatching.git`, checkout commit `4458c278bbec273c8c1a26411dadccc49222f8ef`
- Imported `belief_matching.py` LF-normalized SHA-256: `03229b09559f7059aa6bd7bd6ce80ee1190b41e702f49625ef511074ff42238f`

## Locked distributions

| Distribution | Version |
|---|---:|
| Stim | 1.16.0 |
| PyMatching | 2.4.0 |
| NumPy | 2.2.6 |
| BeliefMatching | 0.2.0 at the commit above |
| ldpc | 2.4.1 |
| SciPy | 1.18.1 |
| Sinter | 1.16.0 |
| Matplotlib | 3.11.2 |
| pytest | 9.2.0 |
| Remaining locked packages | All exact pins verified in `DEPENDENCY_VERIFICATION.json` |

All 24 lock entries (including the VCS dependency) matched. `pip check` reported no broken requirements and there were no unpinned installed distributions other than the venv bootstrap `pip`.

## Installation scope and provenance limits

The venv, editable BeliefMatching checkout, pip cache, and temporary install files are outside the repository and inside the new venv directory. Before/after global Python inventories both had 82 distributions and SHA-256 `f4570507bc9ffdf9f57111b3ab13354c50c32df36499de50d016c70f2ce52383`. The environment verifier confirms package locations remain under the venv.

The lock pins the complete upstream repository commit. The imported source-file digest additionally checks the specific `belief_matching.py` implementation copied by the adapter. That single-file digest is not an independent digest of every file in the upstream repository; repository identity is established here by the installed checkout's Git `HEAD` and `origin` plus the exact lock pin.

The first package-install attempt hit a transient package-index timeout; a longer-timeout retry also timed out. A final retry using the same lock with the venv-local cache and longer timeout succeeded. No pin or lock text was relaxed.

Successful install command (PowerShell; run only if recreating this venv):

```powershell
$venv = 'C:\Users\LENOVO\Documents\Codex\2026-11-13\qshift-ns4a-v2-lockmatched-venv'
$env:TEMP = Join-Path $venv 'tmp'
$env:TMP = $env:TEMP
& (Join-Path $venv 'Scripts\python.exe') -m pip --isolated install `
  --cache-dir (Join-Path $venv 'pip-cache') --disable-pip-version-check `
  --timeout 300 --retries 2 `
  -r outputs/ns4a_v2_lockmatched_env_recovery_v1/requirements-ns3b.lock.txt
```

The complete per-package list is in `DEPENDENCY_VERIFICATION.json`; it records all 23 registry distributions plus the exact VCS-pinned BeliefMatching checkout.

See `DEPENDENCY_VERIFICATION.json` for the full version map, source checkout, installed-file digest, package locations, pip check, and before/after global inventory.
