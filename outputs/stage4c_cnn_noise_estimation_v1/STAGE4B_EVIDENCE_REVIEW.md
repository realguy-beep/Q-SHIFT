# Stage 4B Evidence Review for Stage 4C

## Files inspected

- `outputs/stage4_noise_adaptive_development_v1/STAGE4_DEVELOPMENT_PROTOCOL.md`
- `outputs/stage4_noise_adaptive_development_v1/stage4_development_config.json`
- `outputs/stage4_noise_adaptive_development_v1/STAGE4_DEVELOPMENT_FREEZE_V2.json`
- `outputs/stage4_noise_adaptive_development_v1/run_stage4.py`
- `outputs/stage4_noise_adaptive_feasibility_v1/prototype.py`
- `outputs/phase3a_correlated_noise_preflight/simulator.py`
- `outputs/phase2b_pauli_bias/noise_model.py`
- `outputs/stage4_noise_adaptive_development_v1/STAGE4_RESULTS.md`
- `outputs/stage4_noise_adaptive_development_v1/STAGE4_INDEPENDENT_AUDIT.md`
- `outputs/stage4_noise_adaptive_development_v1/STAGE4_AUDIT_RECOVERY_NOTE.md`
- `outputs/stage4_noise_adaptive_development_v1/REPRODUCE_AFTER_RECOVERY.md`
- Stage 4B `RESULTS.json`, `AUDIT_RESULTS.json`, `EVIDENCE_MANIFEST.json`, `seed_inventory.json`, and `additional_development_seed_audit.json`

All of these records remain unchanged. Their SHA-256 values are included in the Stage 4C pre-sampling `FREEZE.json`; the Stage 4C auditor verified those hashes after sampling.

## Mechanism and method

The Phase 2B circuit builder supplies the rotated distance-3, five-round Z-memory circuit with balanced categorical Pauli gate noise, measurement noise, and one logical observable. The Phase 3A extension inserts a synthetic `CORRELATED_ERROR(p) X8 X10` after each of five MR boundaries. These are independent Bernoulli draws by round. This models a controlled spatial common-cause event between data qubits 8 and 10; it is not hardware-calibrated crosstalk.

The shared DEM path uses Stim `decompose_errors=True, approximate_disjoint_errors=True`; PyMatching uses `enable_correlations=True`. Categorical `PAULI_CHANNEL_2` conversion remains an approximation shared by the matching arms. The injected burst creates graphlike detector-pair mechanisms whose probabilities depend on p while detector count/order and observable ID remain fixed.

`DetectorProfileEstimator` consumes only 40 detector marginal rates and five detector-pair cofire rates. It fits profile means at burst p={0,0.01,0.02}, standardizes by pooled feature variability, interpolates means between knots, and chooses p on a 0.00001 grid. The p estimate is inserted into the same circuit/DEM/PyMatching builder used by the fixed and privileged reference models.

## Stage 4B verified result

The recovered run contains 18,000 profile shots, 70,000 calibration shots, and 87,500 paired test shots (175,500 total); 79 simulation seeds plus three analysis seeds were checked. Its independent audit rebuilt the estimator and all decoder outputs from saved arrays, verified all 35 roots, and passed. Fixed nominal PyMatching made 590 errors; the Stage 4B detector-profile adaptive decoder made 474; the privileged true-p reference made 476. The primary equal-weight nonzero-condition effect was −0.1643 percentage points with root-bootstrap 95% CI [−0.1971,−0.1329] percentage points and a sign-flip Monte Carlo p at the 1/100001 floor. This was development evidence in one synthetic model, not independent confirmation.

Stage 4B's first audit program had two guard defects; the separate recovery auditor corrected them without changing estimator fitting, decoder rebuilding, predictions, or statistical calculations. A later manifest path normalization is also documented as reporting-only. The original failed auditor source and recovery note remain preserved.

## Stage 4C separation

Stage 4C refits the same Stage 4B estimator implementation from a new 90,000-shot development training partition. The CNN and Ridge receive these same detector batches. Fresh validation, per-root calibration, and paired evaluation streams use the 554-seed namespace in the Stage 4C inventory. No Stage 4B evaluation arrays or labels are used for training, tuning, or scoring.
