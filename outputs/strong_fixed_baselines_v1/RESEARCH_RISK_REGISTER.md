# Research risk register — Strong fixed-baseline comparison v1

| Risk | Severity | Control / interpretation |
|---|---|---|
| Stage 5 nominal baseline is burst-blind and may inflate the 21.9% gain | High | Add pooled calibrated and safety-constrained static arms; retain nominal as historical baseline only |
| Pooled static uses a mixture calibration distribution | High | Freeze equal-condition calibration mixture; report sensitivity and p=0 safety explicitly |
| Static model selection uses development logical labels | Medium | Keep selection and validation independent from final development evaluation; disclose extra offline selection budget |
| Adaptive and static use calibration rows differently | Medium | Match total calibration shots, document pooling vs per-root adaptation; do not call information patterns identical |
| Profile templates and scalar parameter may be misspecified | Medium | Use independent templates; report estimation errors and decoder-level utility separately |
| DEM decomposition approximates categorical Pauli channels | High | Keep conversion identical and report limitation; no exact-categorical claim |
| Reused Stage 5 final evaluation in exploratory audit | High | Do not reuse Stage 5 arrays for tuning; new experiment uses fresh, collision-screened seeds |
| Root bootstrap is exploratory, not validated confirmatory inference | High | No confirmatory p-values; future study needs independent statistical operating-characteristic validation |
| One code distance, memory basis and burst pair | High | Restrict claims; generalization conditions remain separate follow-up studies |
| Historical v3.4.2 safety JSON hash mismatch | Medium | Preserve both expected/current hashes; does not alter Stage 5 scientific arrays but limits historical safety-byte verification |
| Audit folder missing from fresh clone | Medium | Use the accessible previous-workspace audit only by recorded path/hash; do not fabricate a tracked copy or claim external review |
| Resource, interrupted writes or storage failure | Medium | Exclusive run lock, atomic per-root archives, 2h/2GiB/5GiB guards, separate run directory; audit all checkpoints before summary |
