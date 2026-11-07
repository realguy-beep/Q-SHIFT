# Final decision

## Outcome: **NO-GO for another adaptive-headroom experiment with the current Q-SHIFT candidate bank and policies**

This is not a conclusion that adaptive quantum decoding can never help. It is a decision that the existing project does not establish a credible, deployable benefit over the strongest properly calibrated fixed baseline, and does not justify another confirmatory adaptation study using this bank.

## Evidence in one view

- Phase 4A/4B detector calibration reduced errors versus **nominal fixed** in the measurement-heavy condition (1,118→940/600k and 1,165→1,008/600k). These are verified static-calibration comparisons. Phase 4B is an independent replication of the static result but has a fresh-template deviation. Neither compares against a strong pooled-selected fixed baseline.
- Phase 4C Stage 2 supplies that stronger comparison: 12,435 calibrated versus 12,407 pooled-fixed errors over 1.8M paired shots; equal-regime ΔLER +0.00001556, 95% root-cluster CI [-0.00004889,+0.00007667], p=.66658. It does not show calibration improves the selected pooled baseline.
- Existing banks have hindsight complementarity. The Phase 4C five-policy per-shot oracle is 0.0054706 LER versus 0.0068928 pooled fixed (0.0014222 absolute / 20.63% relative), but it chooses using each shot’s true label. It is not deployable and not an upper bound on new decoder families.
- Calibration-selected specialization is weak and unstable: across 36 headroom regime cells, 14 specialists differed from pooled; 7 improved evaluation LER, 6 worsened, 1 tied. The prespecified cross-distance gate failed. Distinct graph signatures and finite-sample disagreements are not the same as useful utility.
- Detector-only gating/adaptation did not recover reliable value. Out-of-root gates did not beat pooled fixed; the online utility interval included zero; dynamic prototype behavior often retained pooled fixed, and Phase 5E ML/utility policies matched pooled errors on all four small schedule families.
- A more faithful reference decoder is not ready: exact categorical toys work, but the Phase 2C forest was substantially worse and full-circuit exact/structured inference has unresolved scaling.

## Best fixed baseline

For the main adaptive question, use the Phase 4C Stage 1 pooled model, frozen before Stage 2, as the strongest eligible fixed comparator. It made 12,407 errors / 1,800,000 paired shots (LER 0.00689278). Phase 4C calibrated made 12,435 errors (LER 0.00690833). Do not substitute the weaker nominal baseline when making an adaptive-superiority claim.

## Main scientific obstacle

Decoder predictions can be complementary, but detector-only features have not been shown to predict *which model will correct the next block more successfully* with useful accuracy, confidence, and lead time. Where calibration did identify candidate differences, their utility was often small, unstable across roots, or lost against the pooled-selected baseline. The available dynamic results also lack a fair equal-resource periodic-recalibration comparator.

## Next experiment

None is justified now. Direction C (structured/correlation-aware decoder representation, adaptation later) is the most informative future research question, but only after a candidate passes a development-only utility and resource gate. No adaptive experiment, simulator run, or historical modification was performed for this audit.

