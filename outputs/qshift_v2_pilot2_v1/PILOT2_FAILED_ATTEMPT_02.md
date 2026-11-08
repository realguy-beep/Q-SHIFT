# Failed attempt 2 (preserved)

On 2026-11-08, a second Pilot 2 execution completed the deterministic calibration/tuning phase and selected a candidate, then failed while writing per-stream metrics because `static_patch_cpu` was undefined when both decoder modes selected the same static p. It stopped on the first evaluation stream after its common detectors/observables had been generated and decoded in memory. No Pilot 2 result CSV or paired archive was written.

The attempt used the same 58,500 profile/static-selection/calibration/tuning shots from Attempt 1 plus the first 1,500-shot evaluation stream, for 60,000 unique planned observations in total. Those seeds are all part of the frozen inventory; corrected execution regenerates the exact same samples. The completed tuning artifact was preserved as `PILOT2_TUNING_CANDIDATES_ATTEMPT_02.json` (SHA-256 `FAF233E074D623A014CA164B949B0D7CBB078CE72282959A6EBE00F88F89018F`). No Stage 5 data or evaluation seeds were opened.

Correction: initialize the static-mode timing adjustment to zero before the conditional mode-specific decode. The corrected runner also records that adjustment when the static choices differ.
