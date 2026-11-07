# Reproduction

Run commands from the repository root.

## Verify saved experiment (no simulation)

```powershell
python outputs/neural_decoder_diagnostic/root_cause_analysis/position_preserving_cnn/audit_saved_run.py
```

This loads the saved train/validation arrays and all 30 best checkpoints. It independently recalculates natural-logit corrections, validation temperature and threshold choices, per-regime confusion counts, paired failures, and root-cluster summaries. It verifies all saved prediction arrays and sample alignment. It does not call Stim sampling.

## Run regression tests and syntax checks

```powershell
python -m unittest discover -s dashboard/tests -v
python -m compileall -q dashboard outputs/neural_decoder_diagnostic/root_cause_analysis/position_preserving_cnn
```

The final full-suite result was 48 tests passed (47 passed before the sampling run; one additional exact-coordinate regression was added afterward). The dashboard continues to use its existing `StructuredConv3DDecoder`; the two new models are available for research but were not wired into dashboard worker selection.

## Exact experiment replay

`run_experiment.py` freezes its config, inventory, and source hashes before sampling, and refuses to overwrite an existing run. For an exact deterministic replay, use a clean copy of the repository at the same relative path structure and run:

```powershell
python outputs/neural_decoder_diagnostic/root_cause_analysis/position_preserving_cnn/run_experiment.py
```

This reuses the same development seed inventory and is a reproducibility replay, not independent replication. A new independent study requires a new screened seed inventory and a new pre-sampling freeze. The script contains no test-stream sampler. The exact runner used for the completed run is retained as `run_experiment_frozen.py`; `run_experiment.py` differs only by the documented post-run CSV export fix.

## Data inventory

- `development_samples.npz`: fresh training and validation detector, observable, and frozen PyMatching arrays, plus validation partition indices.
- `predictions_rep0.npz` through `predictions_rep2.npz`: paired threshold-validation samples and probabilities/predictions from each model/strategy.
- `checkpoints/`: validation-selected best weights for each of 30 fits.
- `VERIFIED_RESULTS.json`, `per_root_results.csv`, `per_regime_results.csv`, `aggregate_results.csv`: independently recomputed results.
- `freeze.json`, `seed_inventory.json`, `MANIFEST.json`: provenance, pre-sampling hashes, collision screen, and integrity manifest.
