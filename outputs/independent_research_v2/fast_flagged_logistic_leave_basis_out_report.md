# Leave-one-memory-basis-out transfer failed

## Design

Two folds trained the shared relative-choice classifier on all three regimes for one memory basis and evaluated the other basis, then reversed. Each fit used 3M training samples and was tested on 3M held-out samples; all six cells used 1M validation shots. Matching graphs remained profile-matched. The selector used 40 detector bits and the `correlated_wrong` target. The fixed gate required >=10% macro reduction, no cell harmed >5%, <2x cost, and positive direction in both held-out-basis folds.

## Result

Macro LER increased from .0051605 for correlated matching to .0052402 for leave-one-basis-out selection, a 1.54% worsening. The paired macro difference (candidate minus baseline) was +.0000797 (approximate 95% CI [.0000547,.0001047]). Cost was 1.366x, but the accuracy gate failed.

When Z-memory was held out, the fold had a slight 0.48% macro gain. When X-memory was held out, macro LER worsened 3.72%; all three X-memory cells were worse, and X-memory/balanced was harmed by 5.05%, exceeding the fixed per-cell limit. The all-profile relative and absolute references were .004531 and .004388, and specialized selectors were .004291. Thus the failure is specific to transferring the learned selector across memory basis, not a failure of the matching baseline.

No replication or tuning was launched after the frozen gate failed.

## Interpretation

The prior leave-one-regime-out transfer result depended on training examples from the target memory basis. The relative-choice classifier is not invariant across logical memory bases under this feature representation. Keep positive transfer claims limited to held-out regimes when both bases are represented in training. Do not describe the selector as basis-agnostic or universal. No confirmatory or sealed data were accessed.

## Reproduction

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_leave_basis_out.py
```


## Run metadata

Command used from base revision `d7c7f39` with Python 3.12, NumPy 2.5.5, SciPy 1.18.1, Stim 1.16.0, and PyMatching 2.4.0. The result JSON records runner and protocol SHA-256 hashes. Peak RSS was not captured.
