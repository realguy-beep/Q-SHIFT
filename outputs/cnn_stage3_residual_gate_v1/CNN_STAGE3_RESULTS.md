# Q-SHIFT Stage 3 Results

## Scope

Five-root development feasibility experiment; no independent test was accessed. The burst model is synthetic and is not hardware calibrated.

Controller status at audit: **failed**. Evidence was recovered with the separate module-invoked auditor after the frozen runner's path-based auditor launch failed; the original controller status remains unchanged.

## Paired development results

| Condition | Decoder | Errors / shots | LER | Equal-root mean LER |
|---|---|---:|---:|---:|
| nominal | nominal fixed pymatching | 116 / 25,000 | 0.004640 | 0.004640 |
| nominal | historical residual cnn | 117 / 25,000 | 0.004680 | 0.004680 |
| nominal | stage3 burst focused residual cnn | 116 / 25,000 | 0.004640 | 0.004640 |
| synthetic_spatial_burst | nominal fixed pymatching | 344 / 50,000 | 0.006880 | 0.006880 |
| synthetic_spatial_burst | historical residual cnn | 347 / 50,000 | 0.006940 | 0.006940 |
| synthetic_spatial_burst | stage3 burst focused residual cnn | 344 / 50,000 | 0.006880 | 0.006880 |
| synthetic_spatial_burst | burst informed pymatching privileged | 273 / 50,000 | 0.005460 | 0.005460 |

## Training and correction diagnostics

The Stage 3 model made zero prediction changes on the final paired evaluation arrays, so it had zero useful and zero harmful final corrections. Training residual positives remained rare; the class-balanced sampler repeatedly reused them.

| Root | Unique residual positives / 17,000 | Natural prevalence | Positive reuse | Best epoch / epochs run | Steps | Temperature | Global threshold |
|---|---:|---:|---:|---:|---:|---:|---:|
| stage3-root-00 | 119 | 0.7000% | 500.0× | 4 / 7 | 469 | 1.00 | 0.85 |
| stage3-root-01 | 106 | 0.6235% | 320.8× | 1 / 4 | 268 | 1.00 | 0.85 |
| stage3-root-02 | 123 | 0.7235% | 622.0× | 6 / 9 | 603 | 1.20 | 0.85 |
| stage3-root-03 | 139 | 0.8176% | 366.9× | 3 / 6 | 402 | 1.00 | 0.85 |
| stage3-root-04 | 122 | 0.7176% | 418.0× | 3 / 6 | 402 | 1.00 | 0.85 |

## Primary result and frozen development gate

Mean root-paired burst LER difference (candidate − nominal fixed PyMatching): **+0.000000**.
Descriptive 95% Student-t interval across five roots: **[+0.000000, +0.000000]**; favorable roots **0/5**.
Frozen development gate: **FAIL**. This is not confirmatory evidence.

## Evidence audit

Audit status: **PASS**. Verified 200,000 unique samples in 30 partitions; matching and neural predictions were recomputed from the saved detector arrays.

## Limitations

- Five-root development feasibility study; intervals are descriptive, not confirmatory.
- Synthetic spatial burst model at one distance, basis, location pair and probability.
- Burst-informed PyMatching receives privileged generating-model information.
- Matching DEM conversion inherits approximate_disjoint_errors=True.
- No independent test or hardware execution was performed.
