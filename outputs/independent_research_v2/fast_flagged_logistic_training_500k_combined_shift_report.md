# Half-budget selector retained gains under the combined shift

## Question

The 500k training budget passed nominal d3 tests. This study challenged it under the previously tested joint mismatch: measurement p doubled from .003 to .006 while physical bias ratio moved from 10 to 5. Both 500k and 1M models were trained on fresh nominal streams; no shifted data entered fitting. Validation used nominal ratio-10 matching graphs and the same shifted samples for both models. A matcher built from the actual shifted profile was diagnostic only.

## Results

| Stream | Nominal correlated macro LER | 500k model | 1M model | 500k reduction | Gain retained | Cost |
|---|---:|---:|---:|---:|---:|---:|
| Initial | .0069543 | .0059633 | .0059443 | 14.25% | 98.1% | 1.336x |
| Fresh replication | .0069120 | .0060000 | .0059790 | 13.19% | 97.7% | 1.343x |

Both streams passed the fixed 80% retention, >=10% macro improvement, <=5% cell harm, and <2x cost gates. All six cells improved; the smallest 500k point gains were 4.93% and 4.39%. The actual-profile matcher remains a diagnostic and is not used to support the advancement claim.

## Scope

The result supports halving training samples for the d3 flagged selector under this one combined simulated shift, alongside nominal evidence. It does not establish distance scaling, hardware utility, or arbitrary noise robustness. Across both streams there were 18.06M unique samples (60k preflight, 12M nominal training, 6M shifted validation). No confirmatory or sealed data were accessed.

## Reproduction

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_training_500k_combined_shift.py
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_training_500k_combined_shift_replication.py
```
