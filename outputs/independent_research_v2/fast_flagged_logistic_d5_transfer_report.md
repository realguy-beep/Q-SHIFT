# Distance-5 transfer of the flagged logistic method

## Frozen question and design

Does the method that worked at d3 retain held-out value when its model is fitted specifically for d5? This tests transfer of the method, not d3 coefficients: the d5 model takes 216 detector bits plus two matcher outputs (218 features), rather than the 42 d3 features.

Six d5 CSS memory/profile conditions used the source probability model at gate and measurement p=.003, bias ratio 10, and nine rounds. Each condition had 10,000 preflight samples, 1,000,000 labeled training samples, and an independent 1,000,000 validation samples. The classifier used the same flagged-only L2 logistic objective and optimizer as d3. No validation labels were used for fitting. All six fits converged. Correlated matching remained the fallback and comparator; the full candidate cost included the ordinary matcher pass and classifier.

## Result

Equal-weight macro validation LER slightly worsened from .001959 for correlated matching to .0019855 for the selector, a 1.35% relative increase. The paired macro difference (selector minus correlated matching) was +.0000265 (approximate 95% CI [.0000133,.0000397]). Only two of six cell point estimates improved; four were worse. Per-cell relative reductions were -1.78%, -1.01%, +3.87%, +1.35%, -1.78%, and -1.22%. The mean total inference cost was 1.379x, so runtime passed but the >=10% accuracy gate failed. There is no d5 replication because the frozen advancement gate failed.

The preflight projected 101.7 seconds for train and validation sampling/matching; total elapsed time including graph setup and model fits was 180.7 seconds. Geometry, noiselessness, matcher scalar/batch agreement, feature dimension, and all model convergence checks passed. The high d5 base LER variation across aligned and misaligned conditions remains visible in the per-condition data and makes macro pooling a fixed equal-cell summary, not a universal workload expectation.

## Interpretation

The d3 method's positive result did not transfer to d5 under this distance-specific fit. This does not disprove selective decoding at d5 with different features, data, objective, or algorithm, but it gives no evidence to advance the current fixed method there. Do not tune on this held-out result or launch a replication of this failed candidate. The d3-only lead remains bounded to the previously tested profiles and measurement shift. No confirmatory or sealed data were accessed.

## Reproduction

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_d5_transfer.py
```

Protocol: `fast_flagged_logistic_d5_transfer_protocol.md`; complete per-cell and training outputs: `fast_flagged_logistic_d5_transfer_results.json`.

## Run metadata

Command: `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_d5_transfer.py`. Base revision `0acf0f9`; Python 3.12, NumPy 2.5.5, SciPy 1.18.1, Stim 1.16.0, PyMatching 2.4.0. The JSON records SHA-256 hashes for the protocol, runner, scaled circuit builder, and source noise model. Peak RSS was not captured in the original run and is explicitly left unknown.
