# Frozen selector under halved gate noise

## Protocol

The six selectors and nominal matchers trained at gate/measurement p=.003 and bias ratio 10 were frozen. Physical gate p was changed to .0015; measurement p=.003 and bias ratio 10 stayed fixed. No retraining or nominal graph update occurred. Each stream used 500k main and 10k preflight samples per condition. The actual-profile matcher is diagnostic only.

## First stream

Macro LER was .001973 for nominal correlated matching and .001491 for the frozen selector, a 24.42% reduction. Paired macro difference (selector minus baseline) was -.000482 (95% CI [-.000512,-.000452]); all six cell intervals favored the selector. Full policy cost was 1.368x. The frozen gate passed.

## Independent replication

Macro LER was .001965 versus .001506, a 23.36% reduction. Paired macro difference was -.000459 (95% CI [-.000489,-.000429]); all six intervals again favored the selector. Cost was 1.357x. The gate passed.

## Interpretation

The frozen selector works well when gate noise is halved. Together with the doubled-gate result, the rate axis is asymmetric in practical utility: half-rate shift passed strongly, while double-rate shift achieved paired error reduction but narrowly missed the 10% macro advancement threshold on replication. Do not hide the latter behind aggregate statistical significance. This remains d3 stationary simulator evidence, not a hardware or time-varying noise claim.

## Reproduction

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_gate_half_shift.py
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_gate_half_shift_replication.py
```


## Run metadata

Both runs used the reproduction commands from base revision `307a101`, with Python 3.12, NumPy 2.5.5, SciPy 1.18.1, Stim 1.16.0, and PyMatching 2.4.0. Result JSONs record runner and protocol SHA-256 hashes. Peak RSS was not captured.
