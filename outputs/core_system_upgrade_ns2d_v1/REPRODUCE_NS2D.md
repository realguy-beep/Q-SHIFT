# Reproduce NS-2D Deterministic Validation

Run from the root of the isolated `codex/ns2d-beliefmatching-integration` worktree. The commands below do not call a Stim sampler.

## Environment

The validated environment is `.venv` created from `outputs/core_system_upgrade_ns2d_v1/requirements-ns3b.lock.txt`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r outputs\core_system_upgrade_ns2d_v1\requirements-ns3b.lock.txt
```

The lockfile pins the upstream Git repository commit. The recorded adapter SHA checks the exact imported adapter file only; it is not a whole-repository digest. See `NS2D_DEPENDENCY_PROVENANCE.md`. Do not change the pin without separate authorization.

## NS-2D plus NS-2B/NS-2C regressions

```powershell
.\.venv\Scripts\python.exe -m unittest `
  dashboard.tests.test_beliefmatching_ns2c_integration `
  dashboard.tests.test_decoder_runtime_v2 `
  dashboard.tests.test_sampling_model_identity_v2 `
  dashboard.tests.test_circuit_identity_v1 `
  dashboard.tests.test_core_system_v1 -q
```

Expected result: 80 tests, `OK`.

## Published NS-3B adapter tests

The research worktree is a sibling named `qshift-ns3b-beliefmatching-research`:

```powershell
$integration = (Get-Location).Path
$env:QSHIFT_NS2B_ROOT = $integration
$env:PYTHONDONTWRITEBYTECODE = '1'
$researchTests = Resolve-Path '..\qshift-ns3b-beliefmatching-research\outputs\qshift_ns3_decoder_research\ns3b_beliefmatching'
Push-Location $researchTests
& "$integration\.venv\Scripts\python.exe" -m unittest -q test_beliefmatching_adapter
$testExit = $LASTEXITCODE
Pop-Location
Remove-Item Env:QSHIFT_NS2B_ROOT -ErrorAction SilentlyContinue
Remove-Item Env:PYTHONDONTWRITEBYTECODE -ErrorAction SilentlyContinue
if ($testExit -ne 0) { exit $testExit }
```

Expected result: 14 tests, `OK`.

## Fixed fixture

```powershell
.\.venv\Scripts\python.exe outputs\core_system_upgrade_ns2d_v1\run_fixed_fixture_demo.py
```

This constructs one deterministic circuit and DEM, supplies five manually specified 40-bit detector rows, and decodes them using ordinary PyMatching, correlation-enabled PyMatching, and opt-in BeliefMatching. It writes `outputs/core_system_upgrade_ns2d_v1/FIXED_FIXTURE_COMPARISON.json`. It has no observable labels and therefore reports no LER.

## Integrity

Verify the local engineering manifest and the published NS-3B provenance records (the source manifest, unchanged base dependencies, documented publication-copy hashes, adapter SHA, and copied lock) with:

```powershell
.\.venv\Scripts\python.exe outputs\core_system_upgrade_ns2d_v1\verify_ns2d_manifest.py `
  --research-root ..\qshift-ns3b-beliefmatching-research
```

The engineering manifest intentionally excludes its own hash; all other listed new files are covered.
