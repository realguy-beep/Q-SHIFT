# Frozen logistic selector under measurement-noise shift

## Protocol

The six existing d3 conditions used gate p=.003, measurement p=.006, and bias ratio 10. The logistic coefficients were frozen from the independent nominal p_measure=.003 train/validation replication. No shifted samples were used for training or calibration. Each condition used 10,000 preflight and 500,000 main samples. The selector used nominal correlated matching as fallback and its disagreement flag/features; inference cost includes both nominal matchers and the classifier. The additional matcher built from the actual shifted circuit is a profile-matched diagnostic, not an optimality bound.

## First fresh stream

Equal-weight macro LER was .006657 for nominal correlated matching and .005789 for the frozen selector, a 13.03% reduction. The paired macro difference (selector minus baseline) was -.000868 (normal paired 95% CI [-.000915,-.000820]); all six per-condition paired intervals excluded zero in favor of the selector. Per-cell reductions were 9.44%, 27.75%, 18.61%, 13.30%, 11.46%, and 3.96%. The mean full policy time ratio was 1.351x. The predeclared gate (>=10% macro reduction, no cell harmed >5%, cost <2x) passed. The profile-matched diagnostic macro LER was .006447.

## Independent fresh-seed replication

With the same coefficients, conditions, and sample counts on distinct seeds, macro LER was .006649 for nominal correlated matching and .005778 for the frozen selector, a 13.11% reduction. Paired macro difference was -.000872 (95% CI [-.000919,-.000824]); all six per-condition intervals excluded zero. Per-cell reductions were 9.97%, 28.56%, 19.02%, 10.67%, 10.96%, and 3.83%. Full policy inference cost was 1.349x. The same gate passed. The profile-matched diagnostic macro LER was .006415.

## Interpretation and limits

This independently replicates a useful frozen-policy result under a twofold measurement-flip shift. The policy generalizes across these six fixed d3 simulator conditions and this specific shift, despite having been trained at nominal measurement p=.003. It remains a supervised, condition-specific research result; it does not establish robustness to other shifts, unknown profiles, distance transfer, hardware noise, or online learning. The actual-profile matcher is a diagnostic rather than an optimal decoder bound. No confirmatory or sealed data were used.

## Reproduction

Run:

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_measurement_shift.py
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_measurement_shift_replication.py
```

The frozen designs are in the corresponding `*_protocol.md` files. Each script preserves its own JSON result.
