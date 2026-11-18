# Frozen selector under simultaneous measurement and bias shift

## Protocol

The six per-condition logistic coefficients and nominal correlated/ordinary matching graphs were frozen at gate/measurement p=.003 and bias ratio 10. Evaluation circuits changed measurement p to .006 and biased-channel ratio to 5 simultaneously. No shifted samples were used to fit or calibrate. Each stream used 500,000 main and 10,000 preflight samples per condition. A matcher built from the actual shifted profile is included only as a diagnostic, not an optimality bound. The fixed gate required >=10% macro LER reduction, no condition harmed >5%, and full inference cost <2x.

## First fresh stream

Macro LER was .006924 for nominal correlated matching and .005912 for the frozen selector, a 14.62% reduction. Paired macro difference (selector minus nominal matcher) was -.001013 (approximate 95% CI [-.001065,-.000961]); all six per-condition intervals favored the selector. Per-cell reductions were 13.26%, 29.15%, 17.42%, 10.15%, 11.71%, and 5.63%. Full inference time was 1.345x; the gate passed. The actual-shift matcher diagnostic macro LER was .006866.

## Independent fresh-seed replication

With identical coefficients and conditions on new seeds, macro LER was .006835 versus .005877, a 14.02% reduction. Paired macro difference was -.000958 (approximate 95% CI [-.001010,-.000906]); all six cell intervals again favored the selector. Per-cell reductions were 12.51%, 27.92%, 16.68%, 9.14%, 12.14%, and 4.74%. Full inference time was 1.362x; the gate passed. The diagnostic macro LER was .006835.

## Interpretation and limits

The frozen policy's separate measurement and bias shift results persisted under this simultaneous shift, on two d3 development streams. This is meaningful evidence for the tested joint composition only. It does not establish arbitrary distributional robustness, online adaptation, distance transfer, or hardware performance. The d5-specific transfer screen was negative, so scope remains d3. The balanced channel has no bias anisotropy to change but does receive the measurement shift. No confirmatory or sealed data were accessed.

## Reproduction

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_combined_shift.py
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_combined_shift_replication.py
```

## Run metadata

The two runs used the reproduction commands from base revision `41c8d73`, with Python 3.12, NumPy 2.5.5, SciPy 1.18.1, Stim 1.16.0, and PyMatching 2.4.0. Each JSON records the runner, protocol, and frozen-model SHA-256 hashes. Peak RSS was not captured.
