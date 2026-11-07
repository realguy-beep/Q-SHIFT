# Reproduce Stage 4 Feasibility

Run commands from the repository root in the existing project Python environment. No package installation is required.

```powershell
python -m outputs.stage4_noise_adaptive_feasibility_v1.prepare_stage4
python -m unittest outputs.stage4_noise_adaptive_feasibility_v1.tests.test_prototype -v
python outputs/stage4_noise_adaptive_feasibility_v1/freeze_stage4.py --create
python outputs/stage4_noise_adaptive_feasibility_v1/freeze_stage4.py --verify
python -m outputs.stage4_noise_adaptive_feasibility_v1.run_identifiability_pilot
```

The last command is the **only** command that samples shots. It is bounded by the frozen 48,000-unique-shot allocation and refuses to run if `run_v1/` already exists. The raw detector/observable bundles and run status are kept locally under ignored `outputs/stage4_noise_adaptive_feasibility_v1/run_v1/`. The top-level results and small per-root table contain summaries, not raw samples.

The pilot run must be audited from saved bundles before interpretation. It is not the full Stage 4 study. `STAGE4_FEASIBILITY_FREEZE.json` records the input hashes fixed before sampling; `STAGE4_FEASIBILITY_MANIFEST.json` records hashes after pilot completion.

Independent-test data are not used, listed, or accessed by these commands.
