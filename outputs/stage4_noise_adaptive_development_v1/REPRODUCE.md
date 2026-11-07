# Reproduce Stage 4 Development

Run from the repository root in the installed Python environment. No dependency installation is required.

```powershell
python -m unittest outputs.stage4_noise_adaptive_development_v1.tests.test_stage4 -v
python outputs/stage4_noise_adaptive_development_v1/freeze_stage4_dev_v2.py --create
python -m outputs.stage4_noise_adaptive_development_v1.run_stage4 --validate-only
python outputs/stage4_noise_adaptive_development_v1/freeze_stage4_dev_v2.py --verify
python -m outputs.stage4_noise_adaptive_development_v1.run_stage4 --run
python -m outputs.stage4_noise_adaptive_development_v1.audit_stage4
```

`prepare_seeds.py` was run once to create the committed inventory and collision audit. It refuses to overwrite them. Re-run it only when making a separate new allocation directory, never to regenerate this frozen inventory.

`STAGE4_DEVELOPMENT_FREEZE_V2.json` supersedes the initial freeze only for the Windows `psutil.disk_usage` path conversion. The original freeze and the pre-sampling failure log are retained.

The runner checkpoints profile batches and each root-condition file under ignored `outputs/stage4_noise_adaptive_development_v1/run_v1/`. It refuses to overwrite existing evidence and resumes only after verifying the pre-sampling freeze and completed partition hashes. The audit independently rebuilds decoders and rescales saved paired arrays. No independent-test allocation or file is accessed.
