# Phase 2B Pretest Freeze Changelog

## Revision 1 — superseded before held-out sampling

`PRETEST_FREEZE.json` revision 1 was written after the development/validation and calibration partitions and before any held-out sample. It froze the noise model, model selection, data, and statistical plan. The held-out directory contained zero NPZ files.

During a final source review, a non-scientific runtime metadata bug was found: the runner reported every verified root as “resumed,” including newly sampled roots. No samples had yet been generated. The runner was corrected to separately record roots newly generated in the current invocation and pre-existing roots resumed and independently re-decoded.

## Revision 2 — active pretest freeze

Revision 2 supersedes revision 1 only for this reporting-field correction. It preserves the exact seed inventory, calibration arrays, development/validation arrays, calibration-selected model indices, noise channels, statistical estimand, and test plan. No held-out shots existed at supersession time. The prior freeze is retained byte-for-byte as `PRETEST_FREEZE_SUPERSEDED_1.json`; the active freeze hashes the corrected runner and unchanged pretest evidence.
