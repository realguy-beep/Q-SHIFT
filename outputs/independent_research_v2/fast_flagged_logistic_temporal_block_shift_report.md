# Frozen selector under blockwise temporal gate rates

## Design

This screen uses a new shape of temporal variation, with per-round two-qubit gate-rate factors `[.25,.25,1.75,1.75,1]` and its reversal. The mean remains one. One-qubit and measurement noise are fixed at .003; Pauli composition, circuit geometry, and total gate count stay unchanged. The stationary z-memory/X-biased ratio-10 selector and nominal matcher graphs were frozen. An exact temporal-map matcher is diagnostic only.

Each stream used 500k samples/profile and 10k preflight/profile. The frozen gate required >=10% macro reduction, no profile harmed >5%, and full inference <2x.

## First stream

Macro LER was .009438 for nominal correlated matching and .008266 for the selector, a 12.42% reduction. Paired macro difference was -.001172 (95% CI [-.001264,-.001080]). Block A/B reductions were 12.55%/12.27%. Cost was 1.360x. The gate passed.

## Independent replication

Macro LER was .009404 versus .008298, an 11.76% reduction. Paired macro difference was -.001106 (95% CI [-.001197,-.001015]); profile gains were 11.15%/12.41%. Cost was 1.361x. The gate passed again.

## Interpretation

The frozen selector transferred to a second, blockwise temporal shape, independently of the earlier alternating pattern. Evidence remains limited to Z-memory/X-bias d3, two specified five-round maps, and simulator noise. It does not establish online adaptation, arbitrary temporal noise, other tasks, hardware, or distance scaling. No confirmatory/sealed data were accessed.

## Reproduction

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_temporal_block_shift.py
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_temporal_block_shift_replication.py
```


## Run metadata

Both runs used the listed commands from base revision `6fe5201`, with Python 3.12, NumPy 2.5.5, SciPy 1.18.1, Stim 1.16.0, and PyMatching 2.4.0. Result JSONs record runner, protocol, and temporal-builder SHA-256 hashes. Peak RSS was not captured.
