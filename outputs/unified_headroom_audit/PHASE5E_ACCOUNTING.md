# Phase 5E accounting reconciliation

This is a static reconciliation from the archived Phase 5E configuration, runner source, result JSON, and experiment log. No simulation was rerun.

## Reconciled counts

- Dynamic schedules: **4** families (stationary, slow, rapid, random), **12** replicates, **144** saved blocks, **36,864** shots.
- Calibration: **45,000** shots.
- Stationary evaluation: **90,000** shots.
- Pairwise disagreement sampling: **90,000** shots.
- Reconstructed total simulator shots for Phase 5E: **261,864**.
- The saved seed log has 18 entries for 90,000 shots, and is limited to pairwise disagreement batches; it is not the full seed manifest.

## Discrepancy

`PHASE5E_EXPERIMENT_LOG.md` says “seven schedule families × four replicates × 12 blocks × 256 shots.” The Phase 5E config says 3 dynamic repeats, the executed runner iterates over four kinds, and the saved JSON has four keys with three entries each. The auditable Phase 5E count is therefore **four families × three repeats × 12 blocks × 256 = 36,864 dynamic shots**, not the log’s seven-by-four count. The seven-by-four statement aligns with the separate earlier v3 development results, not this Phase 5E runner. No historical log was changed.

Counts and source hashes are in `PHASE5E_ACCOUNTING.json`.
