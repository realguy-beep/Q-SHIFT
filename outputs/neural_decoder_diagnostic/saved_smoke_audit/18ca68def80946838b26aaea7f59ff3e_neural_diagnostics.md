# Neural decoder audit — 18ca68def80946838b26aaea7f59ff3e

Read-only analysis. The test split was not used for model selection.

| Split | shots | observable positives | direct positives | direct errors | matching errors | residual targets | residual final errors |
|---|---:|---:|---:|---:|---:|---:|---:|
| train | 8000 | 491 | 0 | 491 | 40 | 40 | 40 |
| validation | 1000 | 61 | 0 | 61 | 4 | 4 | 4 |
| test | 1000 | 53 | 0 | 53 | 3 | 3 | 3 |

Test direct confusion matrix (true rows, predicted columns): `[[947, 0], [53, 0]]`.
Test direct Brier/log-loss/ECE: 0.097683 / 0.366946 / 0.207226.
Test direct probability histogram (10 equal-width bins): `[3, 102, 895, 0, 0, 0, 0, 0, 0, 0]`.

Only the saved balanced regime is available in this run. Other regimes are explicitly not measured.
The JSON contains split-specific confusion matrices, calibration bins, prediction histograms, and training-loss summaries.
