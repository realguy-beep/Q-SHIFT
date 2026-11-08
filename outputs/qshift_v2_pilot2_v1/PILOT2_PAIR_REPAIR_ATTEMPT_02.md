# Paired/runtime repair attempt 2 (preserved)

The second review found that the first repaired CSV's per-row `end_to_end_cpu_s` did not add the correlation-aware static arm's alternate graph decode time, although `decoder_cpu_s` did include it. The intermediate file is preserved as `PILOT2_RESULTS_REPAIR_ATTEMPT_02.csv`.

Correction: the final repair recomputes end-to-end CPU from the five reported components (decoder, shared initial calibration, estimator, change detection, graph selection) for every row. It continues to rebuild pair cells from the aligned outcome archive. No sampled outcomes or primary LER counts change.
