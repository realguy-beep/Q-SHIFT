# Frozen selector under doubled gate noise: borderline replication failure

## Protocol and preflight deviation

The six selector coefficients and nominal matchers were frozen at gate/measurement p=.003 and bias ratio 10. The physical circuits changed gate p to .006 while measurement p=.003 and bias ratio 10 stayed fixed. No model retraining or nominal graph update occurred. Each successful stream used 500k main and 10k preflight samples per condition.

The first attempt generated the 60k preflight samples, then stopped because the shifted-profile diagnostic DEM needed a larger decomposition threshold than .0018. The diagnostic alone was rebuilt at .004; nominal policy matchers remained unchanged. The preflight was replayed at the same seeds, so it counts once. The exact failure and correction are preserved in `fast_flagged_logistic_gate_shift_preflight_failure.md`.

## Initial stream

Macro LER was .015588 for nominal correlated matching and .014028 for the frozen selector, a 10.01% reduction. Paired macro difference (selector minus baseline) was -.001560 (95% CI [-.001635,-.001486]). All six cells improved; full policy cost was 1.337x. This narrowly passed the fixed gate.

## Fresh-seed replication

Macro LER was .015523 versus .013978, a 9.95% reduction. Paired macro difference was -.001545 (95% CI [-.001620,-.001470]); all six cell intervals favored the selector. Full policy cost was 1.351x. Despite the clear paired improvement, the frozen gate requires at least 10% macro reduction; 9.95% fails it. No additional shots or tuning were launched.

## Interpretation

This is a borderline result: the selector improves errors across all cells under doubled gate noise, but the two-stream gate did not replicate its >=10% utility threshold. Record as inconclusive for advancement, not as a replicated gate pass. It does not overturn the measurement, bias, and combined-shift results, but shows that the gate-noise challenge is weaker and threshold-sensitive. No confirmatory or sealed data were accessed.

## Reproduction

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_gate_shift.py
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_gate_shift_replication.py
```


## Run metadata

Runs used the listed commands from base revision `eb63ca5`, with Python 3.12, NumPy 2.5.5, SciPy 1.18.1, Stim 1.16.0, and PyMatching 2.4.0. Each JSON records runner, protocol, and preserved preflight-note SHA-256 hashes. Peak RSS was not captured.
