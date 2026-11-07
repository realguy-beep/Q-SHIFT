# Independent auditor compatibility for 256 roots/condition

The historical v2 auditor at `outputs/stage5_preexecution_v1/stage5_saved_array_audit.py` is frozen and hard-codes 100 roots/condition, 500 archives, and the 2.25M-shot totals. It is **not directly compatible** with the proposed 256-root allocation; do not use it unchanged on a 5.76M run.

This versioned validation package adds `audit_dynamic.py`. Its normalized config drives expected root keys, shots, archive coverage, and totals. Tests verify the proposed 256-root allocation expands to exactly 1,280 unique `(probability, root)` keys and totals of 2,560,000 calibration, 3,200,000 evaluation, and 5,760,000 unique shots. It was also run on the complete 10-root-per-condition disposable benchmark: it independently re-estimated p from calibration detector arrays, rebuilt and decoded all three PyMatching arms, matched every stored prediction, and checked all 50 archives and hashes.

**Compatibility scope:** dynamic root-count/cardinality and normalized archive-schema logic are tested; a full 1,280-archive run was deliberately not produced. The future Stage 5 v3 package must adapt the frozen seed inventory/status/manifest interface to this dynamic auditor, freeze both runner and audit source before sampling, and test the full saved-array audit on disposable fixtures. The existing v2 auditor and freeze remain unchanged.
