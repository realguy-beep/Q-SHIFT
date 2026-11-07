# Independent Auditor Recovery Note

The independent audit entry point had two implementation defects that prevented its first executions from reaching analysis. They were repaired in a separate `audit_stage4_recovery.py`; the frozen `audit_stage4.py`, pre-sampling V2 freeze, experiment configuration, sampling runner, saved samples, and statistical analysis rules were not modified.

1. The frozen audit entry point attempted to read `STAGE4_DEVELOPMENT_FREEZE.json` instead of the active `STAGE4_DEVELOPMENT_FREEZE_V2.json`. The recovery copy points to V2.
2. The seed inventory correctly contains 82 values, including 3 analysis-only RNG streams. The audit's sample-stream count check initially counted all 82 as simulation streams. The recovery copy checks uniqueness over all 82 and separately checks the 79 sample streams.

The recovery auditor is a copy of the frozen auditor with those two guard corrections. A source diff confirms no estimator fitting, decoder construction, prediction recomputation, residual scoring, bootstrap, sign-flip, or gate calculation changed. After the audit completed, a third reporting-only edit normalized manifest paths to forward slashes for cross-platform use; it did not alter any scientific calculation or sample. The recovery audit passed; no samples were regenerated and no test data were accessed.

## Hashes

- Frozen pre-recovery auditor (`audit_stage4.py`): `31cccf759c2d44866b6c92078916b06d461d853b900777f9de6dbf590d2551b5`
- Recovery auditor at analysis execution (`audit_stage4_recovery.py`): `193f050bf5cd7dfa7dd502ea087b98dbf7b738ed1675814a816eb7b029e45103`
- Final recovery/reporting source after path normalization: `99bfc490e3ed512891cc186429fcf61099f41e3ad71d4772f893480c9acb6d85`
- Active pre-sampling freeze (`STAGE4_DEVELOPMENT_FREEZE_V2.json`): `7e4ece4147e412cf788e69de2359abc16f1d255406e0fcd680c2f1d5c18ace88`

The original pre-repair freeze and its hash remain preserved. The V2 freeze differs only for the documented Windows path conversion and records the three expected source/document changes since the original freeze. Statistical methods and success criteria remained frozen before sampling.

## Interpretation

The result is a valid development result with an audit-code recovery deviation transparently recorded. It is not confirmatory evidence. The primary sign-flip p-value reached the Monte Carlo plus-one floor of 1/100001; none of the four condition-level tests is below 0.05 after Holm correction. Proceed only to design a separately frozen independent confirmation; do not claim general or hardware superiority.
