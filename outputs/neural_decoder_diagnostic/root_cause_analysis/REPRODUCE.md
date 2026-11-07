# Reproduction and Evidence Map

Run from the repository root in the recorded Python/CUDA environment.

## Recheck the saved bounded diagnostic

```powershell
python outputs/neural_decoder_diagnostic/root_cause_analysis/reproduce_saved_diagnostics.py
```

This read-only verifier consumes the saved train/validation arrays, saved model checkpoints, and historical validation NPZ bundles. It re-decodes saved PyMatching predictions, recomputes the per-policy validation metrics, and writes `SAVED_EVIDENCE_RECOMPUTATION.json`. It generated no new Stim samples and accessed no test data. The original diagnostic run and its exact pre-sampling hashes are recorded in `pre_sampling_freeze.json` and `diagnostic_results.json`.

The original `diagnose.py` is retained as the record of the executed run. Its historical manifest guard is expected to reject the two later documented source changes; do not remove that guard or treat a regenerated run as the same frozen experiment.

## Verify the saved outputs

```powershell
python -m unittest discover -s dashboard/tests -v
python -m compileall -q dashboard outputs/neural_decoder_diagnostic/root_cause_analysis
node --check dashboard/static/app.js
python outputs/neural_decoder_diagnostic/root_cause_analysis/finalize_evidence.py
```

The development data are in `fresh_development_data.npz` (train and validation arrays only). `diagnostic_results.json` contains independent recounts of the earlier 24 saved validation batches, the tiny-set experiments, and paired fresh-development comparisons. `seed_inventory.json` records every proposed stimulus/model/diagnostic seed and collision checks. `pre_sampling_freeze.json` binds the config and source hashes used for the fresh samples.

`tiny_set_results.csv` records training-only memorization trials. `OLD_VALIDATION_RECOMPUTED.csv`, `FRESH_POLICY_COMPARISON.csv`, and `FRESH_POLICY_PER_REGIME.csv` are summary extracts from the saved JSON. `diagnostics.png` visualizes prediction distributions, tiny-set recalls, and paired validation LER.

## Decision and limitations

The selected candidate is a validation-only exploratory result using one validation RNG stream per regime and several compared policies. Shot-level paired bootstrap intervals and McNemar calculations do not replace seed-cluster inference. No model-selection or calibration decisions used the reserved test allocation. The prepared 100K protocol remains unexecuted; the present decision is NO-GO for that run.

`MANIFEST.json` hashes current scripts, tests, data, results, reports, and relevant historical evidence. The original structured integration `FINAL_MANIFEST.json` matched all 71 entries before the prospective weighted-logit correction. `HISTORICAL_PRESERVATION_AUDIT.json` records the current 69 matches and the two expected source/test hash changes. The historical manifest itself is unchanged.
