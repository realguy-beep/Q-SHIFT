# Paired-metric repair attempt 1 (preserved)

The first repair pass still failed the independent contingency audit: its repair script counted the row's error mask across all eight policies instead of selecting the current policy, multiplying some cells by eight. The resulting intermediate CSV is preserved as `PILOT2_RESULTS_REPAIR_ATTEMPT_01.csv` and the audit failure as `PILOT2_AUDIT_ATTEMPT_04.json`.

Correction: select the current policy index before calculating pairwise cells. The final repaired CSV will be regenerated from the unchanged shot-level archive and independently re-audited.
