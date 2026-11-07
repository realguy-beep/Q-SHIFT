# Scientific recomputation

Read-only verifier loaded all 120 saved validation/test NPZ files with pickle disabled, recomputed residuals as observable XOR saved prediction, checked detector shape and raw counts, recomputed paired-only wrong counts, aggregate/per-seed sums, exact two-sided McNemar values, and seed-bootstrap intervals from seed differences. It reconciled JSON and CSV aggregates. No simulator or decoder was rerun.

Primary measurement-heavy test: 600,000 shots, fixed 1,118, calibrated 940; candidate-only 80; fixed-only 258; net 178 fewer. Exact paired McNemar p=5.600789e-23. Calibration recovered the generating grid pair 20/20 for each condition. Other test results: data-heavy 8,577 fixed vs 8,599 calibrated; nominal 2,912 vs 2,912. The informed reference matched calibrated counts in all conditions.

The calibration algorithm's finite shared templates and on-grid conditions constrain generalization; the reported calibration success does not establish off-grid calibration. Test labels are not fitting features. No critical Phase 4A integrity defect found.
