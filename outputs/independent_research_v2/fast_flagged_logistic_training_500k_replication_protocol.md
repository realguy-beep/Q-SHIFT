# Independent replication: fixed 500k training budget

Use the exact runner, model family, features, fit objective, gates, and 500k/1M paired validation comparison from `fast_flagged_logistic_training_500k_protocol.md`. Change only all preflight, training, and validation seeds to the fresh lists below. The advancement gate remains: >=80% absolute-gain retention, >=10% macro reduction, no cell >5% harmed, and <2x inference cost. The replication must pass independently; no retraining, threshold changes, or condition exclusions.

- Preflight: 2026122001–2006.
- Training: 2026122011–2016.
- Validation: 2026122021–2026.
- Counts remain 5k preflight, 1M training, and 500k validation per condition. All six training readiness checks precede validation.
