# Fresh-stream replication of the relative matcher-choice classifier

The initial one-model relative-choice classifier passed its frozen advancement gate. Repeat the identical method and metrics with independent preflight, training, and validation samples. Do not alter features, labels, optimizer, threshold, or advancement gate.

- Preflight: 10,000/condition, seeds 2026118791–8796.
- Training: 1,000,000/condition, seeds 2026118801–8806.
- Validation: 1,000,000/condition, seeds 2026118811–8816.
- Keep nominal p=.003 and bias ratio 10. Train on flagged 40-bit detector vectors with target `correlated_wrong`; switch to ordinary matching only when predicted true.
- Compare with correlated matching, the fixed shared absolute-bit selector, and the fixed per-condition selector on identical validation streams. All reference coefficients come from existing training-only development fits.
- Advancement gate unchanged: >=10% macro reduction, no cell harmed >5%, full inference <2x.
