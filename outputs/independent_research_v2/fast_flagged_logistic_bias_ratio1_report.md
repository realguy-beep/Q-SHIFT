# Frozen selector under isotropic Pauli noise (ratio 1)

## Protocol

The six d3 logistic models and correlated/ordinary matcher graphs were frozen from nominal ratio-10 training at gate/measurement p=.003. Physical biased channels were made isotropic (ratio 1). Balanced profiles remain unchanged controls. No retraining or graph update occurred. Each stream used 500k main and 10k preflight samples/condition. The ratio-1 matcher is a profile-matched diagnostic only.

## First stream

Macro LER was .005714 for nominal correlated matching and .004775 for the frozen selector, a 16.43% reduction. Paired macro difference (selector minus baseline) was -.000939 (95% CI [-.000993,-.000885]). All six point estimates improved; five per-cell paired intervals excluded zero and one included parity. Full inference cost was 1.345x. The gate passed. Profile-matched diagnostic macro LER was .006231.

## Independent replication

With fresh seeds, macro LER was .005706 versus .004749, a 16.77% reduction. Paired macro difference was -.000957 (95% CI [-.001011,-.000903]); all six per-cell intervals favored the selector. Cost was 1.327x. The gate passed. Diagnostic macro LER was .006207.

## Interpretation

The ratio-10 frozen selector retained a ~16% gain when physical biased profiles became isotropic. This extends the static stationary-composition range tested at ratios 1, 2, and 5; it does not prove arbitrary noise robustness, unknown-profile matching, temporal variation, cross-basis transfer, hardware performance, or distance scaling. The leave-one-basis-out and d5 screens remain negative. No confirmatory/sealed data were accessed.

## Reproduction

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_bias_ratio1.py
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_bias_ratio1_replication.py
```


## Run metadata

Both runs used the listed commands from base revision `e7e6f4a`, with Python 3.12, NumPy 2.5.5, SciPy 1.18.1, Stim 1.16.0, and PyMatching 2.4.0. Each result JSON records runner and protocol SHA-256 hashes. Peak RSS was not captured.
