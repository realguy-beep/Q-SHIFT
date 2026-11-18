# Shared relative-choice classifier for matcher disagreements

## Method

On flagged d3 syndromes where correlation-enabled and ordinary PyMatching disagree, a single logistic model predicts whether correlated matching is wrong. It uses only the 40 detector bits; the label is `correlated_prediction != observable` on flagged training samples. At inference it selects the ordinary prediction when the model predicts correlated is wrong, and otherwise retains the correlated prediction. No condition ID, matcher-output bit, or observable enters inference. The model is trained across all six nominal d3 CSS basis/profile conditions at p=.003, bias ratio 10. The ordinary and correlated matchers are both charged to inference cost.

The model was trained on 1M samples/condition and evaluated on an independent 1M/condition stream, with 10k preflight/condition. A fresh pooled fit and fresh validation were then run with unchanged method and gate. Fixed shared absolute-bit and per-condition logistic models were scored on the same validation streams as references.

## First stream

Macro LER was .005149 for correlated matching and .004534 for relative choice, a 11.96% reduction. Paired macro difference (relative choice minus correlated) was -.000616 (95% interval [-.000651,-.000581]). Mean inference cost was 1.378x. The fixed gate passed. Five cells improved by 5.7%–29.9%; X-memory/Z-bias was effectively tied and slightly worse by point estimate (-.22%), with paired interval crossing zero.

The shared absolute-bit reference had macro .004394 and specialized reference .004318. Relative choice was worse by .000139 (paired 95% CI [.000117,.000162]) and .000216 (CI [.000192,.000239]), respectively.

## Fresh-seed replication

Macro LER was .005193 correlated and .004558 relative choice, a 12.23% reduction; paired macro difference was -.000635 (95% CI [-.000671,-.000600]). Cost was 1.345x. The unchanged gate passed. Five cells improved; X-memory/Z-bias improved 0.24% and was effectively neutral, with paired interval crossing zero.

Shared absolute-bit and specialized references were .004424 and .004340. Relative choice was worse by .000134 (paired 95% CI [.000111,.000157]) and .000219 (CI [.000195,.000242]).

## Interpretation

The relative target is intuitive and uses a slightly smaller feature set, and it passes the baseline advancement gate on two independent streams. It is not the most accurate selector: the fixed shared absolute-bit and specialized models consistently do better by about .00014 and .00022 macro LER. Keep it as an interpretable compact alternative only where that accuracy tradeoff is acceptable. This is nominal d3 simulator evidence, not an unknown-profile, hardware, or distance-transfer result. No confirmatory or sealed data were accessed.

## Reproduction

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_relative_choice.py
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_relative_choice_replication.py
```


## Run metadata

Both runs used the listed reproduction commands from base revision `1d37830`, with Python 3.12, NumPy 2.5.5, SciPy 1.18.1, Stim 1.16.0, and PyMatching 2.4.0. Each result JSON records runner and protocol SHA-256 hashes. Peak RSS was not captured.
