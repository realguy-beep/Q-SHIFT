# Reproduction instructions for the published research worktree

Base checkout: Q-SHIFT engineering commit `d66346d8c7ad54b9567ecdd190e0d54ee7b93f0f`. The NS-3 package is isolated under `outputs/qshift_ns3_decoder_research/`. The deterministic circuit-builder dependencies remain the exact source files already present in that base checkout; their SHA-256 values are recorded in `SOURCE_MANIFEST.json`.

## NS-3A deterministic tests

From this directory, with Python 3.12, NumPy, and Stim available:

```powershell
python -m unittest -v test_decoder_prototypes
```

The saved deterministic benchmark can be regenerated with:

```powershell
python benchmark_fixed_fixtures.py > benchmark_results_ns3a_reproduction.json
```

That script uses fixed syndrome fixtures and does not call a Stim sampler. Its reproduction output is a new file; the recorded `benchmark_results_ns3a*.json` and `.partial` files are historical results and should not be overwritten.

## NS-3B BeliefMatching adapter tests

Use the exact pinned upstream implementation in `ns3b_beliefmatching/requirements-ns3b.lock.txt`, preferably in a dedicated Python 3.12 virtual environment. From `ns3b_beliefmatching`:

```powershell
$env:QSHIFT_NS2B_ROOT = (Resolve-Path ..\..\..).Path
python -m unittest -v test_beliefmatching_adapter
```

The test suite uses saved deterministic fixtures and exact small DEM fixtures. It does not generate stochastic circuit data. The lock file pins BeliefMatching to commit `4458c278bbec273c8c1a26411dadccc49222f8ef` (tag `v0.2.0`) and records the tested Python dependencies. The adapter verifies the installed upstream version and implementation-source hash before construction.

The fixed-fixture resource benchmark can be regenerated with:

```powershell
python benchmark_beliefmatching.py > benchmark_results_ns3b_reproduction.json
```

This is a deterministic timing harness, not a scientific performance evaluation. Existing benchmark outputs, including intermediate historical records, must not be redirected over.

No stochastic experiment, training, seed generation, or protected-evaluation access is part of these reproduction commands.
