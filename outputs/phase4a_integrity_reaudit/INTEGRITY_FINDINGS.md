# Integrity findings

Independent inspection found the source/config/method hashes recorded in `FREEZE.json` still match. The 120 validation/test NPZ bundles exist and their detector/observable labels and saved predictions independently reproduce reported residual and discordance counts. The initial and final manifest agree on all scientific artifacts; current hashes of all entries in the final manifest match.

Templates, calibration, validation and test use disjoint seed ranges. The Phase 4A runner's calibration fitting code reads detector arrays and marginal profiles; labels are retained for audit but not used by the fitting expression. Test labels are read only after calibration/validation and frozen model selection. The fixed model uses the nominal DEM; calibrated model uses the selected grid DEM; model-informed model uses generating-pair DEM. Models use generated native DEPOLARIZE1/2 and measurement errors and ordinary PyMatching. Test data are paired.

Protocol freeze timing is supported by the `FREEZE.json` timestamp preceding final `RESULTS.json`, `PER_SEED_RESULTS.csv`, and test checkpoints, plus the runner's hash checks before test sampling. This supports, but cannot cryptographically prove, that no unrecorded test inspection occurred before freeze. Stage 0 scientific result status: PASS with this provenance caveat.
