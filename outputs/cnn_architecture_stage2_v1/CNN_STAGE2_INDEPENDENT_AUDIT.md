# Q-SHIFT CNN Stage 2 Independent Audit

**Status: PASS**

- Roots: 5/5; model/root jobs: 15/15.
- Unique shots independently accounted: 260,000 / 260,000.
- Split totals: {'training': 100000, 'monitor': 20000, 'probability_calibration': 20000, 'threshold_selection': 20000, 'final_development_evaluation': 100000}.
- Independent test accessed: false.
- Both matching models were rebuilt and rescored against saved detectors for each split.
- CNN logits, probabilities, and predictions were independently recomputed from saved detector arrays and frozen model weights.
- Monitor checkpoint selection, calibration temperatures, thresholds, residual-positive counts, seed metadata, hashes, shapes, binary values, and paired sample identity were checked.
- Runner totals were compared with an independent reduction; root-level intervals are descriptive.
