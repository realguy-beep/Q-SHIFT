# Reproduce the Stage 5 statistical repair and no-sampling readiness checks

Run these commands from the repository root in the already installed project Python environment. Do not install dependencies. The commands below generate synthetic statistical design replicates and preflight circuit/decoder construction; none generates Stage 5 evaluation shots.

## Frozen statistical evidence

The full synthetic design simulation and raw outputs already exist. To independently replay the full design (about ten minutes on the recorded machine):

```powershell
python outputs/stage5_secondary_inference_repair_v1/audit_secondary_v4.py
python outputs/stage5_secondary_inference_repair_v1/audit_reporting_bounds.py
python -m unittest discover -s outputs/stage5_secondary_inference_repair_v1/tests -v
```

`audit_secondary_v4.py` independently replays the six million calibration statistics and all 744 family/scale validation cells from the frozen seed streams, then compares counts and reference fingerprints. `audit_reporting_bounds.py` independently recomputes the Wilson intervals and gate flags from the saved counts. The prior failed audit attempts V1–V3 are retained and explained in the independent audit failure notes.

To reproduce the candidate statistical simulation from scratch, first review `DESIGN_FREEZE.json` and then run:

```powershell
python outputs/stage5_secondary_inference_repair_v1/simulate_secondary.py --full
```

The full simulation writes to its own versioned evidence files and refuses to overwrite existing results. It simulates root-effect statistics only; it does not sample the Stim circuit. The corrected result file is a separate reporting reanalysis and the original result file remains unchanged.

## Verify the Stage 5 pre-test freeze

The pre-test freeze is created only after the historical freezes, primary audit, secondary simulation audit, reporting audit, seed inventory, and implementation files have been checked:

```powershell
python outputs/stage5_secondary_inference_repair_v1/freeze_stage5_pretest.py
```

The script is one-shot and refuses to overwrite an existing freeze. It hashes protocol, configuration, methods, implementation, tests, sample seed inventory, design results, independent audits, and the original Stage 5/primary design records. It confirms the endpoint, allocation, zero-collision seed screen, and no-sampling boundaries.

## No-sampling preflight

After the freeze exists, run:

```powershell
python outputs/stage5_secondary_inference_repair_v1/run_no_sampling_preflight.py
```

This checks the freeze hashes, recoverable historical seed-source hashes, the 12,100 prospective seed allocation, circuit detector/observable counts, PyMatching graph construction for all five burst probabilities, the six secondary reference distributions, and current RAM/disk limits. It saves `STAGE5_NO_SAMPLING_PREFLIGHT.json`. It does not call a detector sampler.

## Stage 5 sampling boundary

The Stage 5 runner has a no-flag guard and an explicit `--preflight` mode. Sampling requires both `--run` and `--authorize-stage5-sampling`. Those flags are intentionally omitted from this reproduction guide. The freeze and preflight are readiness evidence only; Stage 5 must not be sampled until the user separately authorizes the frozen experiment.

The eventual read-only auditor is `stage5_saved_array_audit.py`. It requires the later saved root-archive directory as an explicit argument, verifies the freeze and per-root hashes, re-estimates the detector-only parameter, independently reconstructs all decoder predictions, recomputes paired counts and statistics, and compares its aggregates to the runner's persisted summary. No Stage 5 archive exists from this readiness work.
