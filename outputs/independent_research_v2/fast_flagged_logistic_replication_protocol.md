# Independent train/validation replication of the flagged logistic selector

## Purpose

The initial learned selector passed its held-out LER and cost gates and beat the BP+LSD hybrid on a same-validation-stream reanalysis. Test whether the result survives an entirely fresh train/validation split and compare against BP+LSD on the same new validation stream.

## Frozen replication

- Repeat the exact six d3 Phase 2B conditions, flag definition, 42-feature logistic model, sum-log-loss plus .5 L2 penalty, L-BFGS-B maxiter300, per-condition fit, and decision threshold from `fast_flagged_logistic_protocol.md`. No tuning.
- Training: 1,000,000/condition, seeds 2026114501–4506. Independent validation: 1,000,000/condition, seeds 2026114511–4516. Preflight: 10,000/condition, seeds 2026114491–4496.
- Primary test policy uses correlated matching when decoders agree and the trained logistic selector otherwise. On the same validation syndromes, also run fixed BP+LSD `LSD_CS` on flagged cases as a stronger, slower baseline. Only training observables enter model fitting; validation observables are used only for scoring.
- Replication requires >=10% macro LER reduction versus fixed correlation-enabled matching, no cell harmed by >5%, full inference cost <2x correlated matching, and optimizer convergence. Report BP+LSD same-stream utility and runtime separately.

## Stop rules

Stop before main if circuit/noiseless/decoder checks or five-minute projection fail; stop after training if a flagged training set has only one logical class or optimizer fails. This remains development-only; no confirmatory/sealed data are accessed.
