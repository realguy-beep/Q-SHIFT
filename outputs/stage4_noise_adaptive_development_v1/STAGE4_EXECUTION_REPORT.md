# Stage 4 Development Execution Report

Status: **completed**; independent evidence audit: **PASS**; development gate: **PASS**.

The frozen development allocation completed 175,500 unique shots: 18,000 detector-only profile shots, 70,000 calibration shots, and 87,500 paired evaluation shots across 35 root-condition checkpoints. The three decoders used the same 87,500 evaluation detector/observable pairs. No independent-test samples were allocated, accessed, or evaluated.

The complete execution took 59.24 seconds; observed peak RSS was 86,413,312 bytes. Limits were 1,800 seconds and 2 GiB. Environment: Stim 1.16.0, PyMatching 2.4.0, NumPy 2.5.3.

## Reproduction and audit

The original frozen commands are preserved in [REPRODUCE.md](REPRODUCE.md); use [REPRODUCE_AFTER_RECOVERY.md](REPRODUCE_AFTER_RECOVERY.md) for the verified audit command. The frozen `audit_stage4.py` entry point had two audit-only guard defects; the separate `audit_stage4_recovery.py` corrected its V2 freeze path and sample-stream count check, then independently rebuilt the profile estimator and decoder models and exact-redecoded every saved prediction array. The pre-sampling freeze, sampler, statistical calculations, and criteria remained unchanged. See [STAGE4_AUDIT_RECOVERY_NOTE.md](STAGE4_AUDIT_RECOVERY_NOTE.md). Raw detector, observable, calibration, and prediction arrays are preserved in `run_v1/` locally and listed in `EVIDENCE_MANIFEST.json`.

See [STAGE4_RESULTS.md](STAGE4_RESULTS.md), [STAGE4_INDEPENDENT_AUDIT.md](STAGE4_INDEPENDENT_AUDIT.md), and [STAGE4_COMPETITION_EVIDENCE.md](STAGE4_COMPETITION_EVIDENCE.md). Stage 4 is synthetic development evidence only; it is not hardware validation or independent confirmation.
