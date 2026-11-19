# Blockwise temporal selector transfer across two aligned d3 tasks

Use the frozen blockwise factors `[.25,.25,1.75,1.75,1]` and its reversal on two complementary tasks: Z-memory/X-biased and X-memory/Z-biased. Each task uses its own nominal per-condition selector and two matching graphs trained at gate/measurement p=.003, ratio 10. Change only per-round total two-qubit rate; retain mean p=.003, one-qubit/measurement noise, Pauli composition, geometry, and gate count. The exact temporal matcher is diagnostic only.

- 500k main and 10k preflight per task/profile (four cells per stream).
- First seeds in condition order (Z/X-biased block A/B, then X/Z-biased block A/B): preflight 2026121601–1604; main 2026121611–1614.
- Fresh replication, same frozen coefficients and settings: preflight 2026121691–1694; main 2026121701–1704.
- Gate: >=10% equal-cell macro reduction vs nominal correlated matching, no cell harmed >5%, full policy cost <2x.

Check geometry, five-round structure, mean rate, noiselessness, scalar/batch matching, 42 features, and projected runtime <=300s. No retraining, confirmatory/sealed data, or post-validation tuning.
