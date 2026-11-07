# Independent saved-evidence audit

**Status: PASS** (0 failures).

- Raw calibration/evaluation bundles: 360 expected, 360 independently re-decoded.
- Prediction shot checks: 10,800,000; template profiles checked: 72.
- Unique proposed seeds: 516/516; historical collisions: 0.
- Historical files examined excluding this pilot directory: 1231; recovered seed values: 2076.
- Calibration choices were recomputed from saved calibration arrays. Evaluation labels were used only to calculate residual metrics.
- Per-root saved detector/observable arrays pair every decoder prediction on identical shots.

## Outcome

The runner’s aggregate counts were recomputed from saved NPZ evidence and compared field-by-field. Model outputs were independently regenerated from the saved DEM files. Raw file hashes are recorded in EVIDENCE_AUDIT.json.

## Limitations

- Historical RNG coverage is limited to recorded artifacts; unrecorded streams cannot be excluded.
- Phase 4C Stage 2 calibration arrays were not preserved, limiting reconstruction of that historical fit.
- This is development feasibility evidence, not a confirmatory adaptive test.


The historical scanner's `files_scanned` summary field counts the full outputs tree, including files under the excluded pilot directory; the exclusion-aware historical file count is 1231. Seed extraction itself excluded the pilot directory.

FREEZE.json mtime preceded the first saved calibration/evaluation bundle mtime: True. This timestamp sequence supports freeze-before-sampling, but is not cryptographic proof of the full authoring chronology.