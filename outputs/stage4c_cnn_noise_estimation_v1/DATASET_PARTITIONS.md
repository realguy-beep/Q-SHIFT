# Stage 4C Dataset Partitions

All samples are newly generated under Stage 4C's prospective seed inventory; no Stage 4B evaluation sample is reused.

| Partition | Burst probabilities | Independent detector batches / roots | Shots | Labels in estimator? |
|---|---|---:|---:|---|
| Training | 0, 0.01, 0.02 | 120 batches per p × 250 shots | 90,000 | Known p is supervised target only |
| Validation | 0.005, 0.015 | 60 batches per p × 250 shots | 30,000 | Known p may select Ridge alpha/CNN checkpoint only |
| Evaluation calibration | 0, 0.004, 0.008, 0.012, 0.016 | 7 roots per p × 2,000 shots | 70,000 | Detector bits only; separate from test shots |
| Paired evaluation | same five conditions | 7 roots per p × 2,500 shots | 87,500 | Labels used only after all predictions are produced |
| **Total** | | | **277,500** | Below the frozen 300,000 ceiling |

The seed inventory contains 554 unique values: 360 training sampling seeds, 120 validation sampling seeds, 35 calibration seeds, 35 paired-evaluation seeds, and four separate Torch/statistical RNG seeds. The namespace is disjoint from 3,254 seed values extracted from the explicitly listed, recoverable development-only metadata plus Stage 4B seed records. This finite audit cannot rule out undocumented historical RNG use. No independent-test path or sample is opened.

Raw detector/observable arrays and model weights stay locally under the ignored `run/` directory. Evaluation root archives store one shared detector matrix, its aligned observable vector, all five decoder predictions, and seed/model metadata. Deployable estimators receive only the independent calibration detector matrix. The privileged arm alone receives the generating probability and is nondeployable.
