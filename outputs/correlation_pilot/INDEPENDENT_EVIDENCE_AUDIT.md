# Independent evidence audit

## Decision

PASS: all expected per-root raw bundles are present, each stored prediction was regenerated from its stored unpacked detector samples using independently rebuilt PyMatching instances, and every aggregate in `RESULTS.json` was recomputed from the raw labels and predictions by this script.

Evidence coverage: 72 checkpoints, 720,000 paired shots, 2,880,000 prediction bits independently matched.

## Checks

- Filename-to-stratum/root mapping and seed formula checked for all 72 files.
- Packed detector arrays checked as uint8 `(10000, 5)` and unpacked little-endian to `(10000, 40)`.
- Observable and prediction arrays checked for shape and binary values.
- All four predictions per shot were recomputed from the saved detectors; mismatch count was zero.
- Logical residuals were recomputed as observable XOR predicted logical flip.
- Per-root, per-stratum and aggregate counts were calculated from arrays, not the runner’s counters.
- Each checkpoint SHA-256 is recorded in `CHECKPOINT_HASHES.json`.

## Scope limitation

This audit verifies test-array alignment and decoder predictions. It does not make the approximate DEM an exact representation of the categorical Stim channel and does not establish hardware validity or confirmatory status.
