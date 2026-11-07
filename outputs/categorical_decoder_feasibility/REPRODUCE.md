# Reproduction

Run from `outputs/categorical_decoder_feasibility/` in the repository.

## Requirements

- Python 3.12 (tested on 3.12.10)
- NumPy 2.5.3
- Stim 1.16.0
- PyMatching 2.4.0

## Commands

```powershell
python -m py_compile categorical_reference.py toy_circuits.py run_toy_comparisons.py test_categorical_reference.py
python -m unittest -v
python run_toy_comparisons.py
python build_manifest.py
```

The runner performs exhaustive enumeration of the two toy models, validates the separately derived masks through deterministic Stim circuits for every categorical configuration, constructs the approximate toy DEMs, decodes each possible syndrome in standard and correlation-enabled modes, and writes `TOY_RESULTS.json`. It generates no stochastic evaluation dataset and does not sample any Phase 2B circuit.

`test_categorical_reference.py` contains eight deterministic tests. `MANIFEST.json` records SHA-256 hashes for the new deliverables and selected read-only source/provenance references from Phase 2B and the earlier DEM feasibility audit. Rebuilding the manifest changes only this new directory.

