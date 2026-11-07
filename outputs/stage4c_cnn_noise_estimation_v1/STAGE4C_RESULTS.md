# Q-SHIFT Stage 4C — Results

Exploratory development result only. No independent-test data were accessed.

Unique shots: **277,500** across 90,000 training, 30,000 validation, 70,000 calibration, and 87,500 paired evaluation shots.
The five decoder arms used identical held-out detector/observable arrays.

## Paired evaluation by decoder

| Decoder | Errors / shots | LER | Equal-weight nonzero-condition LER |
|---|---:|---:|---:|
| Fixed nominal PyMatching | 545 / 87,500 | 0.622857% | 0.622857% |
| Stage 4B profile estimator + PyMatching | 478 / 87,500 | 0.546286% | 0.527143% |
| Ridge estimator + PyMatching | 477 / 87,500 | 0.545143% | 0.524286% |
| CNN estimator + PyMatching | 482 / 87,500 | 0.550857% | 0.531429% |
| Privileged true-p PyMatching reference | 477 / 87,500 | 0.545143% | 0.525714% |

## Results by burst probability

| p | Fixed | Stage4B profile | Ridge | CNN | True-p reference |
|---:|---:|---:|---:|---:|---:|
| 0.000 | 109/17500 (0.6229%) | 109/17500 (0.6229%) | 110/17500 (0.6286%) | 110/17500 (0.6286%) | 109/17500 (0.6229%) |
| 0.004 | 83/17500 (0.4743%) | 79/17500 (0.4514%) | 77/17500 (0.4400%) | 82/17500 (0.4686%) | 78/17500 (0.4457%) |
| 0.008 | 113/17500 (0.6457%) | 100/17500 (0.5714%) | 100/17500 (0.5714%) | 100/17500 (0.5714%) | 100/17500 (0.5714%) |
| 0.012 | 122/17500 (0.6971%) | 102/17500 (0.5829%) | 102/17500 (0.5829%) | 102/17500 (0.5829%) | 102/17500 (0.5829%) |
| 0.016 | 118/17500 (0.6743%) | 88/17500 (0.5029%) | 88/17500 (0.5029%) | 88/17500 (0.5029%) | 88/17500 (0.5029%) |

## Primary paired comparison

Equal-weight CNN-minus-Stage4B-profile LER difference across nonzero conditions: **+0.004286%**.
Stratified root-bootstrap 95% CI: **[+0.000000%, +0.012857%]**; two-sided root sign-flip p=1.
The CNN favored 0/4 nonzero conditions. At p=0, its one-sided 95% upper difference bound is +0.017143%.

Noise-estimation MAE and signed bias by method are in `STAGE4C_RESULTS.json`; per-root paired outcomes are in `STAGE4C_PER_ROOT.csv`.
The true-p arm is privileged and is not a deployable method. DEM conversion approximates disjoint categorical errors; the burst model is synthetic.
