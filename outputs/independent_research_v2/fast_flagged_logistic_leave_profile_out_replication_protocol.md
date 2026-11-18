# Fresh-stream leave-one-regime-out replication

Repeat all three frozen leave-one-regime-out folds with distinct preflight, train, and held-out validation seeds. Keep the model target, features, per-profile matching graphs, fold assignments, comparators, and gate unchanged.

- Preflight 2026118951–8956; held-out validation in condition order 2026118991–8996.
- X-biased holdout training 2026118961–8964; balanced holdout 2026118971–8974; Z-biased holdout 2026118981–8984.
- 1M training shots per included condition per fold and 1M held-out shots per condition. Report per-fold directions, per-cell intervals, and comparators. No post-validation tuning.
