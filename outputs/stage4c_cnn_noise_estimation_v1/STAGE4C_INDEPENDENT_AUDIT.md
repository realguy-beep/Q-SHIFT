# Stage 4C Independent Evidence Audit

**Status: PASS.**

- Frozen source/configuration hashes verified: 36
- Unique Stage 4C seeds: 554; recoverable historical collisions: 0
- Fresh unique samples: 277,500 (training 90,000; validation 30,000; calibration 70,000; paired evaluation 87,500)
- Evaluation roots independently checked: 35/35; all five decoder predictions re-decoded exactly.
- CNN checkpoint independently retrained: best epoch 49; validation MAE 0.0022682; 6,941 parameters.
- Stage4B profile, Ridge and CNN estimates were recomputed from calibration detector arrays only.
- Paired evaluation detector/observable arrays are shared across all five decoder arms.
- Independent-test access: **none**.

Per-method aggregate errors independently reconstructed:

- fixed_nominal: 545/87,500
- stage4b_profile: 478/87,500
- ridge: 477/87,500
- cnn: 482/87,500
- privileged_true_p: 477/87,500

Raw local arrays remain in the ignored `run/` directory. SHA-256 values are in `STAGE4C_AUDIT_RESULTS.json` and `EVIDENCE_MANIFEST.json`.
Finite recoverable seed records do not establish the absence of unrecorded historical RNG use. This audit verifies saved development evidence, not hardware behavior or independent confirmation.
