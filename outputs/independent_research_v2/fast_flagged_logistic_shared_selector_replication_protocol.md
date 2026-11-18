# Fresh-stream replication of the pooled d3 selector

The initial pooled shared model passed its frozen advancement gate. This protocol repeats the same one-model method with fresh independent training and validation streams; it does not change the pooled objective, features, gate, baseline, or condition weighting.

- Preflight: 10,000/condition, seeds 2026118591–8596.
- Pooled training: 1,000,000/condition, seeds 2026118601–8606.
- Validation: 1,000,000/condition, seeds 2026118611–8616.
- All six conditions, nominal gate/measurement p=.003 and bias ratio 10. Fit one shared L2 logistic selector on all flagged training rows. Compare with correlated matching and the previous specialized coefficients as a same-stream reference.
- Apply the original advancement gate without changes: >=10% macro LER reduction, no condition harmed >5%, total inference cost <2x. No retuning or post-validation choice.
