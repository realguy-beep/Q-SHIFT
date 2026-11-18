# Frozen selector at physical bias ratio 2

## Protocol

The six logistic coefficients and correlated/ordinary matching graphs were frozen from nominal ratio-10 training at gate/measurement p=.003. Evaluation used physical ratio 2, with no retraining, calibration, or graph updates. Balanced channels are unchanged-profile controls. Each stream used 500k main and 10k preflight samples per condition. The actual-ratio-2 matcher is reported only as a profile-matched diagnostic, not an optimality bound.

## First stream

Macro LER was .005660 for nominal correlated matching and .004677 for the frozen selector, a 17.38% reduction. Paired macro difference (selector minus baseline) was -.000984 (95% CI [-.001037,-.000930]); all six cell intervals favored the selector. Per-cell reductions ranged from 3.70% to 34.90%. Full inference cost was 1.324x. The gate passed. The profile-matched diagnostic macro LER was .006012.

## Independent replication

On a fresh stream with the same coefficients and settings, macro LER was .005616 versus .004611, a 17.90% reduction. Paired macro difference was -.001005 (95% CI [-.001058,-.000952]); all six cell intervals again favored the selector. Per-cell reductions ranged from 5.22% to 34.37%. Full inference cost was 1.374x. The gate passed. The diagnostic macro LER was .005978.

## Interpretation

The nominal ratio-10 selector retained a strong gain when physical bias was reduced to 2:1, across the six d3 conditions. This adds a separately replicated static bias shift to the ratio-5 and combined-shift evidence. It remains one family of stationary simulator channels; it does not establish time-varying noise, unknown-profile graph selection, cross-basis transfer, hardware performance, or distance scaling. The leave-one-basis-out and d5 screens were negative. No confirmatory/sealed data were accessed.

## Reproduction

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_bias_ratio2.py
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_bias_ratio2_replication.py
```


## Run metadata

Both runs used the reproduction commands from base revision `0090de7`, with Python 3.12, NumPy 2.5.5, SciPy 1.18.1, Stim 1.16.0, and PyMatching 2.4.0. Each result JSON records runner and protocol SHA-256 hashes. Peak RSS was not captured.
