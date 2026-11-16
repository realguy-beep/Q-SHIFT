# Calibration reconstruction plan
☑ Preserve 900-shot replay evidence and frozen run.
◐ Verify frozen identities and all calibration archive hashes; independently compute parity-moment class and root rates, and recompute labeled logical likelihoods using the frozen exact decoder.
☐ Compare all recorded metadata with absolute tolerance 1e-10 (likelihood 1e-8); record discrepancies and provenance limits.
☐ Commit only verified replay and reconstruction evidence.
No sampler, new shots, full decoder replay, sealed-file access, or parameter changes. Maximum 900 seconds.

Checkpoint: ☑ 38 frozen files and 300 archive hashes verified; ☑ 340 calibration checks passed; ☑ replay evidence checked; ☑ scoped staged diff and whitespace reviewed. Local commit pending; final commit identity is reported in chat.
