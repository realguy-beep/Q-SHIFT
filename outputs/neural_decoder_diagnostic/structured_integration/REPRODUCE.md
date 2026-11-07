# Reproduction Instructions

Run from the repository root with the same Python environment used by the dashboard. The recorded environment was Python 3.12.10, PyTorch 2.14.1+cu126, NumPy 2.5.3, CUDA enabled, NVIDIA GeForce RTX 4050 Laptop GPU.

## Small development training run

The exact development configuration and seed inventory are saved alongside this file under `dev_run_6000/` and at the integration directory level.

```powershell
python dashboard/structured_worker.py --config outputs/neural_decoder_diagnostic/structured_integration/development_config.json --run-dir outputs/neural_decoder_diagnostic/structured_integration/dev_run_6000
```

The existing run directory contains checkpoints and evidence. Do not rerun into it unless intentionally resuming that same development run. To prepare a fresh configuration without sampling data:

```powershell
python dashboard/prepare_structured_run.py --mode development --train-per-regime 2000 --validation-per-regime 1000 --output outputs/neural_decoder_diagnostic/structured_integration/new_development_config.json
```

## Prepared 100K configuration (not executed)

The generated `official_100k_config.json` and `official_100k_config_seed_inventory.json` are prospective artifacts only. The config allocates 70K training and 15K validation shots; 15K held-out test shots are reserved. It is included for review, but the current readiness decision is NO-GO and this instruction does not authorize starting it.

To regenerate only the config and its collision-screened inventory:

```powershell
python dashboard/prepare_structured_run.py --mode budget --budget 100000 --output outputs/neural_decoder_diagnostic/structured_integration/official_100k_config.json
```

## Audits and tests

```powershell
python dashboard/audit_structured_development.py outputs/neural_decoder_diagnostic/structured_integration/dev_run_6000
python dashboard/verify_structured_resume.py
python -m unittest discover -s dashboard/tests -v
python -m compileall -q dashboard
node --check dashboard/static/app.js
python dashboard/verify_run.py dashboard/run_data/runs/18ca68def80946838b26aaea7f59ff3e
```

The independent development auditor regenerates detector/observable batches from their saved seeds, re-decodes PyMatching, and recomputes neural outputs from best-validation weights. It does not reproduce training calibration from saved training detector arrays; those arrays are streamed and not retained. This is why the audit supports deterministic evidence integrity, not a complete training-process replay. The resume check is a tiny CPU-only equivalence test. Neither audit opens or generates the test allocation.

## Outputs

- `dev_run_6000/structured_development_results.json`: metrics, model-selection record, environment, timings, resource usage, and circuit/DEM metadata.
- `dev_run_6000/independent_evidence_audit.json`: independent validation evidence audit.
- `resume_equivalence_audit.json`: pause/resume equivalence result.
- `structured_development_diagnostics.png`: validation diagnostic chart.
- `official_100k_config.json` and `official_100k_config_seed_inventory.json`: prepared but unexecuted scale-up configuration and seed screen.

Historical smoke runs remain in `dashboard/run_data/runs/`; the structured run is separate.
