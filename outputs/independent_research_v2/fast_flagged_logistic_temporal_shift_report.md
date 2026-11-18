# Frozen selector under alternating per-round gate rates

## Design

The nominal z-memory/X-biased ratio-10 selector and matchers were frozen from stationary p=.003 training. Two temporal profiles scale total two-qubit error probability by `[.25, 1.75, 1, .25, 1.75]` and its reversal across five rounds; each has mean factor one. One-qubit noise, measurement p=.003, and two-qubit Pauli composition remain fixed. The test uses Z-memory/X-bias d3 only. An exact temporal-map matcher is reported as a diagnostic, not an optimality bound.

Each stream used 500k shots/profile and 10k preflight/profile. The gate required >=10% equal-profile macro reduction, no profile harmed >5%, and full nominal two-matcher-plus-classifier cost <2x.

## First stream

Macro LER was .007970 for nominal correlated matching and .006976 for the frozen selector, a 12.47% reduction. Paired macro difference was -.000994 (95% CI [-.001077,-.000911]). Phase A reduction was 12.05%; phase B was 12.92%. Full policy cost was 1.364x. The gate passed. The exact-map diagnostic macro LER was .007787.

## Independent replication

Macro LER was .008003 versus .007068, an 11.68% reduction. Paired macro difference was -.000935 (95% CI [-.001018,-.000852]); phase-specific gains were 11.78% and 11.58%. Cost was 1.361x. The gate passed again. Exact-map diagnostic macro LER was .007774.

## Interpretation

The stationary-trained selector's benefit transferred to these two alternating temporal profiles, without retraining. This is a positive time-varying simulator result for one memory basis/profile and a fixed five-round pattern. It does not establish online rate estimation, arbitrary temporal changes, other tasks, hardware performance, or distance scaling. Cross-basis and d5 screens remain negative; doubled gate-rate stationary stress remains borderline. No confirmatory/sealed data were accessed.

## Reproduction

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_temporal_shift.py
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_temporal_shift_replication.py
```


## Run metadata

Both runs used the reproduction commands from base revision `72cf88b`, with Python 3.12, NumPy 2.5.5, SciPy 1.18.1, Stim 1.16.0, and PyMatching 2.4.0. The result JSONs record runner, protocol, and temporal-builder SHA-256 hashes. Peak RSS was not captured.
