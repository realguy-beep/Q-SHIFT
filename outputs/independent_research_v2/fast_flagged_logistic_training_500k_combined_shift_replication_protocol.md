# Fresh-seed replication: half-budget selector under combined shift

Repeat the exact frozen design and advancement gates in `fast_flagged_logistic_training_500k_combined_shift_protocol.md`, changing only preflight, nominal training, and shifted validation seeds:

- Preflight: 2026122601–2606.
- Training: 2026122611–2616.
- Validation: 2026122621–2626.

Train both nested 500k and 1M nominal models on one fresh 1M stream/condition; validate on the same new 500k shifted stream/condition. All training checks precede validation. No tuning or condition exclusions.
