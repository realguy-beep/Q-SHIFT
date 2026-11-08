# Reproduce Stage 5 v2 readiness checks

Run from the repository root with the existing installed Python environment. These commands do not generate Stage 5 shots.

    python -m unittest discover -s outputs/stage5_secondary_inference_repair_v1/tests -v
    python -m unittest outputs.stage5_secondary_inference_repair_v1.tests.test_stage5_repair_preflight_v2 -v
    python outputs/stage5_secondary_inference_repair_v1/audit_reporting_bounds.py
    python outputs/stage5_secondary_inference_repair_v1/audit_secondary_v4.py
    python outputs/stage5_secondary_inference_repair_v1/stage5_sampling_runner_v2.py --preflight

The Stage 5 v2 freeze is STAGE5_PRETEST_FREEZE_V2.json. Its 53 hashes include the active runner, independent saved-array auditor, configuration, profile, statistical methods, seed inventory, source dependencies, tests, historical freeze records, and simulation/audit evidence. The runner preflight checks those hashes and builds circuits/DEMs/matching graphs without calling a Stim sampler. The persisted measured run is STAGE5_NO_SAMPLING_PREFLIGHT_V2.json.

The independent audit takes about ten minutes on the recorded Python 3.12.10 / NumPy 2.5.3 / SciPy 1.18.1 Windows environment and independently replays the synthetic reference statistics and 744 design-validation cells. The interval audit independently recalculates Wilson bounds and saved gate flags.

Freeze builders are one-shot and refuse to overwrite an existing freeze. The no-sampling wrapper similarly refuses to overwrite its output. The original v1 candidate and its blocked status remain preserved. The active runner's sampling path requires --run plus --authorize-stage5-sampling; do not supply those flags until the user separately authorizes sampling. The independent saved-array auditor is prepared but has not read any Stage 5 archive because no Stage 5 archive exists.
