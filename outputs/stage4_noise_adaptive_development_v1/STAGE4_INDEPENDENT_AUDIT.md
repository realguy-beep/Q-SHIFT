# Stage 4 Independent Evidence Audit

**Audit result: PASS.** Independent-test access: **none**.

## Evidence coverage

- Profile data: 9 detector-only batches, 18,000 shots, exact seeds validated.
- Calibration data: 35 detector-only batches, 70,000 shots, saved for independent estimator reconstruction.
- Paired evaluation: 35 root files, 87,500 shots; each contains 40 detector bits, one observable, and three decoder predictions.
- Total: 175,500 unique allocated shots; 79 sampling seeds plus 3 analysis seeds, all unique.
- Partition payloads independently hashed: 114; duplicate complete partition payloads: zero.

## Scientific checks

- Every filename, probability, root ID, and calibration/evaluation seed matches the frozen inventory.
- Calibration p-hat and its conditional bootstrap interval reproduce from saved calibration detectors only.
- The auditor rebuilt Stim circuits/DEMs and PyMatching instances separately from runner predictions and re-decoded all held-out detector arrays; every stored prediction matched exactly.
- Observable labels were used only for residual scoring after model predictions were reconstructed.
- All three decoder arms were paired on each root's same evaluation detector and observable arrays.
- Seed collision screening: PASS against 2,994 recoverable historical development seed values. Unrecorded historical RNG use is not ruled out.
- No independent-test sample arrays or labels were opened, read, hashed, summarized, or used. An initial broad filename-only search unintentionally displayed names under a historical independent-replication raw-data directory; none of those files was opened or used. This is documented in `ADDITIONAL_SEED_COVERAGE.md`.

## Statistics and scope

Primary equal-weight nonzero-condition effect: -0.164286%; 95% stratified root-cluster bootstrap CI [-0.197143%, -0.132857%], two-sided sign-flip p=9.9999e-06. The inference unit is the independent root, not the shot. Seven roots per condition give limited resolution and rely on sign symmetry for the randomization test.

The audit confirms saved-data integrity and numerical reproducibility. It cannot establish external reproducibility or a hardware noise model. See `AUDIT_RESULTS.json`, `RESULTS.json`, and `EVIDENCE_MANIFEST.json` for structured values and SHA-256 digests.
