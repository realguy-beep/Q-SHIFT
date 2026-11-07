# Reproduce the DEM feasibility gate

From this directory, run:

```powershell
python -m py_compile audit_dem_construction.py build_manifest.py
python audit_dem_construction.py
python build_manifest.py
```

The audit rebuilds the six circuits with the frozen Phase 2B `noise_model.py`, verifies the original pilot pre-test freeze hashes, tries conversion A and B, summarizes A's DEM and matching graphs, tests the correlation-enabled/disabled decode API on an all-zero deterministic syndrome, and saves exact B exceptions and tracebacks. It does not call a detector sampler or generate simulation shots.

Outputs are confined to `outputs/dem_feasibility_gate/`. B failures are preserved in `DEM_CONSTRUCTION_RESULTS.json`; the runner does not try a modified circuit, altered noise channel, approximation threshold, or ignored decomposition failure.
