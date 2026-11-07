# Reproducing Stage 4 Results After Audit Recovery

The original pre-sampling `REPRODUCE.md` is preserved in the V2 source freeze. Its final audit command targets the frozen `audit_stage4.py`, whose two audit-only guard defects are described in `STAGE4_AUDIT_RECOVERY_NOTE.md`. Use the recovery command below for the verified saved-data audit.

## Verify this completed run

From the repository root:

```powershell
python outputs/stage4_noise_adaptive_development_v1/freeze_stage4_dev_v2.py --verify
python -m unittest outputs.stage4_noise_adaptive_development_v1.tests.test_stage4 -v
python -m outputs.stage4_noise_adaptive_development_v1.audit_stage4_recovery
```

The recovery auditor reads the locally preserved `run_v1/` NPZ evidence, independently reconstructs the profile estimator and decoder models, rescales all predictions, and regenerates the reports and manifest. It does not generate shots. Re-running it is read-only with respect to sample/checkpoint files, but it refreshes derived reports and audit metadata.

## Reproducing sampling from a clean working copy

Use a clean copy of the repository where `outputs/stage4_noise_adaptive_development_v1/run_v1/` contains no profile or root NPZ files:

```powershell
python outputs/stage4_noise_adaptive_development_v1/freeze_stage4_dev_v2.py --verify
python -m unittest outputs.stage4_noise_adaptive_development_v1.tests.test_stage4 -v
python -m outputs.stage4_noise_adaptive_development_v1.run_stage4 --validate-only
python -m outputs.stage4_noise_adaptive_development_v1.run_stage4 --run
python -m outputs.stage4_noise_adaptive_development_v1.audit_stage4_recovery
```

The recorded allocation is fixed at 175,500 shots. Do not run the sampling command in the completed workspace merely to repeat the analysis; checkpoints there are the preserved evidence for this experiment. The V2 freeze supersedes the initial implementation freeze only for the documented Windows path conversion.
