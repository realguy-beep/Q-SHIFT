# Experiment accounting

## Frozen allocation

| Condition | Roots | Calibration shots/root | Evaluation shots/root | Calibration total | Evaluation total |
|---:|---:|---:|---:|---:|---:|
| p = 0.000 | 1,210 | 2,000 | 2,500 | 2,420,000 | 3,025,000 |
| p = 0.004 | 1,210 | 2,000 | 2,500 | 2,420,000 | 3,025,000 |
| p = 0.008 | 1,210 | 2,000 | 2,500 | 2,420,000 | 3,025,000 |
| p = 0.012 | 1,210 | 2,000 | 2,500 | 2,420,000 | 3,025,000 |
| p = 0.016 | 1,210 | 2,000 | 2,500 | 2,420,000 | 3,025,000 |
| **Total** | **6,050** |  |  | **12,100,000** | **15,125,000** |

Total unique allocation: **27,225,000 shots**.

## Recovery accounting

The original failed run had 124 archives containing 558,000 committed detector/observable rows. Its status counters accounted for only 555,500 rows because the last 2,500-row evaluation sample had been committed before the status update failed. The 124th archive contained 2,000 calibration rows and 2,500 evaluation rows but no saved estimate or predictions.

The v3.4.4 recovery copy reused all 558,000 committed rows, including the incomplete root's existing calibration and evaluation arrays. It reconstructed that root's profile estimate and decoder predictions without calling Stim again for either stream. The remaining 5,926 roots contributed 26,667,000 newly generated samples. The final status is 6,050 complete roots, 12,100,000 calibration shots, 15,125,000 evaluation shots, and 27,225,000 unique allocated shots.

## Uniqueness and pairing checks

The independent auditor checked all 6,050 expected condition/root pairs against the frozen seed inventory, verified every archive and commit marker, and independently re-decoded each saved prediction array. The 6,050 archive hashes are recorded in `ROOT_ARCHIVE_MANIFEST.json` and `FINALIZATION_MANIFEST.json`. All three decoder arms within each evaluation batch share the same detector samples and observable labels; there is no per-decoder resampling.

The original failed-run directory remains unchanged with status `worker_failed`; its 265-file forensic inventory still matches. Recovery artifacts and the completed status live in a separate directory.

The seed inventory is not duplicated in this evidence package. Its relative repository path and SHA-256 are in `EVIDENCE_MANIFEST.json`; the frozen repository commit provides the source inventory. No seed values are printed in this package.
