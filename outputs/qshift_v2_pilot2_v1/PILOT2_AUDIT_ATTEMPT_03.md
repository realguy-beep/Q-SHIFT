# Independent-audit attempt 3 (preserved)

The audit found that shot-aligned predictions and error totals were correct, but the CSV paired contingency table was not: bitwise negation of `uint8` error masks made `neither_error` include all shots. The audit result that detected this is preserved as `PILOT2_AUDIT_ATTEMPT_03.json`. The raw aligned predictions and observables remain available in `PILOT2_PAIRED_OUTCOMES.npz`.

Correction: recompute every paired contingency column from the saved binary outcome archive using Boolean masks, preserve the pre-repair CSV, and add a regression test. This is a post-run summary repair; no shots were resampled and primary logical-error counts are unchanged.
