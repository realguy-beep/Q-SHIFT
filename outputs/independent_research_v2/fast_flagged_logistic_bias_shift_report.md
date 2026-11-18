# Frozen selector under a reduced Pauli-bias ratio

## Protocol

The six d3 models and nominal matchers were frozen at bias ratio 10, gate p=.003, and measurement p=.003. Physical X- and Z-biased channels were changed to ratio 5; the balanced channel is unaffected by this parameter and serves as a control. No training or calibration used shifted samples. Each stream used 500,000 main and 10,000 preflight shots per condition. A correlation-enabled matcher built using the shifted profile is included as a diagnostic only, not as an optimality bound. Both streams follow the fixed gate: >=10% macro LER reduction, no cell harmed >5%, full inference cost <2x.

## First fresh stream

Macro LER was .005377 for nominal correlated matching and .004412 for the frozen selector, a 17.95% reduction. The paired macro difference (selector minus nominal correlated matcher) was -.000965 (approximate 95% CI [-.001015,-.000916]); all six per-condition paired intervals favored the selector. Relative reductions by cell were 16.34%, 34.20%, 26.29%, 14.57%, 13.73%, and 6.25%. Full inference time was 1.347x. The gate passed. The profile-matched diagnostic macro LER was .005538.

## Independent fresh-seed replication

With identical coefficients, shift, and evaluation rule on new seeds, macro LER was .005291 versus .004349, a 17.81% reduction. Paired macro difference was -.000942 (approximate 95% CI [-.000992,-.000893]); all six per-condition intervals again favored the selector. Cell reductions were 15.69%, 35.47%, 22.41%, 14.01%, 14.57%, and 5.92%. Full inference cost was 1.364x. The gate passed. The profile-matched diagnostic macro LER was .005434.

The balanced profiles are not shifted by changing the ratio parameter; they are unchanged-profile controls. Results therefore include four biased cells under a real anisotropy shift and two unchanged controls.

## Interpretation and limits

The frozen d3 selector retained useful performance under this single-axis shift from bias ratio 10 to 5, independently replicated across the six basis/profile conditions. Together with the separate measurement-p shift, this supports two bounded synthetic robustness findings. It does not establish simultaneous-shift robustness, arbitrary bias direction/strength, unknown-profile adaptation, distance transfer, or hardware performance. In particular, the separate d5 method screen failed; do not describe this as scaling beyond d3. No confirmatory or sealed data were accessed.

## Reproduction

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_bias_shift.py
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_bias_shift_replication.py
```

Protocol and per-condition artifacts are in this directory as `fast_flagged_logistic_bias_shift_protocol.md` and the two `*_results.json` files.

## Run metadata

The two runs used the commands in the reproduction section from base revision `ce02eed`, with Python 3.12, NumPy 2.5.5, SciPy 1.18.1, Stim 1.16.0, and PyMatching 2.4.0. Each JSON records its runner, protocol, and frozen-model SHA-256 hashes. Peak RSS was not captured.
