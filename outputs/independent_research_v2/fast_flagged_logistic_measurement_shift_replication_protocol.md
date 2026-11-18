# Fresh-seed replication: frozen selector under measurement shift

## Question

Does the nominally trained per-condition logistic selector retain its benefit on an independent sample stream when measurement-flip probability is doubled from .003 to .006?

## Fixed design

- Reuse the exact coefficients from the independent nominal train/validation replication; no retraining, recalibration, threshold change, or adaptation.
- Repeat the original six d3 basis/profile conditions at gate p=.003, measurement p=.006, bias ratio 10.
- Preserve the original sample counts and scoring: 500,000 main samples and 10,000 preflight samples per condition; paired comparison against the nominal p_measure=.003 correlation-enabled matcher.
- Fresh seeds: preflight 2026114691–2026114696; main 2026114701–2026114706. These are distinct from the original shift stream.
- Use the p_measure=.006 correlation-enabled matcher only as a profile-matched diagnostic, not as an optimality bound.
- Apply the already recorded gate unchanged: at least 10% macro LER improvement, no condition harmed by more than 5%, and full policy inference cost below 2x.

## Stop rules

Retain the original geometry, noiselessness, scalar/batch, and 300-second projected-runtime checks. This is a fresh-stream development replication; do not inspect confirmatory or sealed data.
