# Stage 3 pre-sampling implementation amendment

**Created 2026-11-07, after the first prospective freeze and before any Stage 3 sampling.** The first freeze is preserved byte-for-byte as `FREEZE_SUPERSEDED_001.json`; it recorded zero Stage 3 shots at supersession. Stage 3's simulator has not generated any samples as of this amendment. The earlier no-sampling validations built circuits/DEMs and ran unit tests only.

## Reason

Final runner review and Windows regression tests exposed implementation defects and hardening needs: checkpoint `fsync` used a read-only handle; disk telemetry depended on `shutil`; the partition counter omitted a `kind` field; dry-run initialization used the wrong reserved RNG purpose; the resume path could recompute and overwrite an already frozen policy; policy selection did not enforce an exact pre-final partition allowlist; resumed runs did not cumulatively account for wall/CUDA budgets; and the independent audit/reporting path needed to be completed.

## Changes

- Fixed Windows-safe atomic checkpoint writing and restored disk-space telemetry.
- Added explicit partition type metadata and recovery of an archive left without its atomic metadata commit by deterministically rebuilding its allocated stream.
- Tied the dry run to the root-00 training initialization seed and record the first 256 allocated training shots, five-update CUDA timing, and a conservative projected completion check before sampling the rest of the training partition.
- Made policy reuse idempotent on resume, with hash checks; final-development data cannot enter the selection-partition structure.
- Added cumulative wall-time accounting across resume and persisted CUDA time in epoch checkpoints; stale locks are preserved under a `.stale` name only after confirming their PID is not alive.
- Added independent rescoring from saved arrays/checkpoints, report generation, and an evidence manifest.

## Scientific decisions unchanged

No change was made to the hypothesis, circuit, noise model, decoder candidates, sample counts, roots, RNG inventory, training optimizer, epochs, patience, class-balancing rule, natural-prevalence correction, model-selection criteria, calibration/threshold partitions, threshold grid or tie breaks, primary estimand, Student-t interval, success gate, or 200,000-shot ceiling. The Stage 2 final-development data remain diagnostic history only. No independent-test material was opened or used.

## Freeze status

The initial freeze remains as a historical record. `FREEZE.json` is superseded before sampling and binds the amended implementation, tests, and this note. The superseding freeze records the hash of the preserved first freeze and zero sampled shots at supersession. The statistical protocol and prospective design remain those in `CNN_STAGE3_PROTOCOL.md` and `stage3_config.json`.

The resource projection is an execution-safety check, not a model-selection rule: estimate the maximum training duration from 3,350 updates; multiply that estimate by 2 for wall overhead and by 1.5 for the CUDA allowance; estimate simulator time by scaling the first-prefix sampler rate to 200,000 shots and multiplying by 3; then add a fixed 600-second wall allowance. Proceed past the 256-shot diagnostic only if the conservative wall estimate is below 14,400 seconds and the conservative CUDA estimate is below 9,000 seconds. The measured inputs and calculations are saved in `run_v1/dry_run_report.json`.
