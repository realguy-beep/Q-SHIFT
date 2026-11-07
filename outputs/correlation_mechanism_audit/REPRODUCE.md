# Reproduce the saved-data audit

From this directory, run:

```powershell
python -m py_compile analyze_saved_pilot.py build_manifest.py
python analyze_saved_pilot.py
python build_manifest.py
```

The analysis script is read-only with respect to `outputs/correlation_pilot/`: it opens the 72 saved `.npz` checkpoints, the saved Phase 2B DEM/circuit files, the pilot config and results, then writes only CSV/JSON outputs in this directory. It does not generate Stim samples or import the pilot runner/reporting functions. The manifest hashes all audit outputs and the listed source, protocol, model, result, and checkpoint inputs.

The pilot's original freeze and independent prediction re-decode record remain the provenance for the saved model predictions. This audit recomputes residuals and condition patterns from those predictions; it cannot recover latent gate-level Pauli events or matching paths that were not saved.
