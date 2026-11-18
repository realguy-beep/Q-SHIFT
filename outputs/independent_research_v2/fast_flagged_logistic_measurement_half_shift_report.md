# Frozen selector under halved measurement noise

## Protocol

The six per-condition selectors and nominal matcher graphs were frozen at gate/measurement p=.003 and bias ratio 10. Physical measurement p was changed to .0015; gate p=.003 and bias ratio 10 stayed fixed. No retraining or nominal graph update occurred. Each stream used 500k main and 10k preflight samples/condition. The actual-profile matcher is diagnostic only.

## First stream

Macro LER was .004550 for nominal correlated matching and .003691 for the frozen selector, an 18.89% reduction. Paired macro difference (selector minus baseline) was -.000859 (95% CI [-.000904,-.000814]); all six per-cell intervals favored the selector. Full inference cost was 1.365x. The gate passed.

## Independent replication

Macro LER was .004613 versus .003783, a 18.00% reduction. Paired macro difference was -.000830 (95% CI [-.000875,-.000786]); all six cell intervals again favored candidate. Cost was 1.370x. The gate passed.

## Interpretation

The frozen model works under a halved measurement rate. Together with the doubled-measurement result, both directions pass the fixed utility gate on independent streams. This remains stationary d3 simulator evidence; it does not establish temporal drift, unknown matcher graphs, cross-basis transfer, hardware performance, or distance scaling. No confirmatory/sealed data were accessed.

## Reproduction

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_measurement_half_shift.py
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_measurement_half_shift_replication.py
```


## Run metadata

Both runs used the listed commands from base revision `fa51c3e`, with Python 3.12, NumPy 2.5.5, SciPy 1.18.1, Stim 1.16.0, and PyMatching 2.4.0. Each JSON records runner and protocol SHA-256 hashes. Peak RSS was not captured.
