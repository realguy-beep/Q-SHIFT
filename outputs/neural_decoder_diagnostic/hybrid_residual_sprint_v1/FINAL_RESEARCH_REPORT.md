# Q-SHIFT Hybrid Residual Sprint — Development Report

**Status:** development-only; independent test access = 0.

Unique new simulation shots: 1,665,000 (plus 384 preflight diagnostics).
The reported intervals use five independent roots and are descriptive; the experiment is not confirmatory.

## Candidate summary

| Strategy | Training shots/regime | Policy | Pooled LER | Root mean LER (95% t interval) | PM mean LER | Mean paired delta | Root bootstrap 95% delta CI | Candidate-only / PM-only | Roots win/loss/tie | Helpful/harmful corrections | Holm-adjusted root sign-flip p |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| balanced_minibatch | 10,000 | confidence_gate | 0.5018% | 0.5018% [0.4773%, 0.5263%] | 0.5018% | 0.0000% [0.0000%, 0.0000%] | [0.0000%, 0.0000%] | 0 / 0 | 0/0/5 | 0 / 0 | 1 |
| balanced_minibatch | 10,000 | min_ler | 0.5053% | 0.5053% [0.4808%, 0.5298%] | 0.5018% | 0.0036% [-0.0106%, 0.0177%] | [-0.0044%, 0.0138%] | 28 / 20 | 1/3/1 | 20 / 28 | 1 |
| balanced_minibatch | 30,000 | confidence_gate | 0.5018% | 0.5018% [0.4773%, 0.5263%] | 0.5018% | 0.0000% [0.0000%, 0.0000%] | [0.0000%, 0.0000%] | 0 / 0 | 0/0/5 | 0 / 0 | 1 |
| balanced_minibatch | 30,000 | min_ler | 0.5018% | 0.5018% [0.4762%, 0.5273%] | 0.5018% | 0.0000% [-0.0128%, 0.0128%] | [-0.0093%, 0.0062%] | 23 / 23 | 1/4/0 | 23 / 23 | 1 |
| balanced_minibatch | 60,000 | confidence_gate | 0.5018% | 0.5018% [0.4773%, 0.5263%] | 0.5018% | 0.0000% [0.0000%, 0.0000%] | [0.0000%, 0.0000%] | 0 / 0 | 0/0/5 | 0 / 0 | 1 |
| balanced_minibatch | 60,000 | min_ler | 0.5053% | 0.5053% [0.4792%, 0.5315%] | 0.5018% | 0.0036% [-0.0087%, 0.0158%] | [-0.0044%, 0.0102%] | 56 / 48 | 1/4/0 | 48 / 56 | 1 |
| natural_inverse_prevalence_weighted | 10,000 | min_ler | 0.5027% | 0.5027% [0.4752%, 0.5301%] | 0.5018% | 0.0009% [-0.0023%, 0.0040%] | [-0.0009%, 0.0031%] | 4 / 2 | 1/2/2 | 2 / 4 | 1 |
| natural_inverse_prevalence_weighted | 30,000 | min_ler | 0.5040% | 0.5040% [0.4788%, 0.5292%] | 0.5018% | 0.0022% [-0.0021%, 0.0066%] | [-0.0004%, 0.0049%] | 21 / 16 | 1/3/1 | 16 / 21 | 1 |
| natural_inverse_prevalence_weighted | 60,000 | min_ler | 0.5018% | 0.5018% [0.4764%, 0.5272%] | 0.5018% | 0.0000% [-0.0020%, 0.0020%] | [-0.0013%, 0.0013%] | 20 / 20 | 1/1/3 | 20 / 20 | 1 |

## Interpretation

These are exploratory development comparisons. Thresholds and temperatures were frozen using calibration/threshold-selection partitions before final-development scoring. The same final shots were used for all strategies within a root/regime. Holm-adjusted exact sign-flip values are exploratory with five root clusters; the sign-flip symmetry/exchangeability assumption is limited at this sample size. No result is an independent-test conclusion.

A later study is justified only if one policy lowers paired LER consistently across roots, has useful correction precision, and does not rely on a single regime/root. Otherwise retain PyMatching and do not scale. See `NEXT_EXPERIMENT_DECISION.md` and `RESULTS.json` for all root and regime records.
