# Stage 4C Estimation and Resource Diagnostics

All values are from the frozen development partitions. Seven evaluation roots were used per condition; intervals are descriptive root-cluster bootstrap summaries, not independent confirmation.

## Burst-probability estimation on held-out evaluation calibration batches

| Estimator | Nonzero-p MAE | 95% root-bootstrap CI | Signed bias | Validation MAE on p={0.005,0.015} | Median inference time / 2,000 detector rows |
|---|---:|---:|---:|---:|---:|
| Stage 4B detector profile, refit on Stage 4C training batches | 0.0006643 | [0.0004611, 0.0008668] | −0.0002221 | 0.0022502 | 1.30 ms |
| Ridge regression | 0.0005454 | [0.0003995, 0.0006993] | +0.0000016 | 0.0021943 | 0.041 ms |
| 3D CNN | 0.0008653 | [0.0006830, 0.0010424] | −0.0005948 | 0.0022682 | 4.24 ms |

The Stage 4B profile estimator has exactly 40 per-detector marginal rates plus five pair-cofire rates and a fixed 0.00001 grid. Ridge uses the same 45 empirical features. The CNN receives the time-space detector grid, the five pair-cofire rates at their actual endpoint coordinates, and the occupancy mask. CNN estimates shrink toward the middle: it overestimated p at zero and underestimated p=0.004/0.008 on average. Ridge had the lowest calibration MAE in this sample; the CNN did not.

## Held-out calibration summaries by p

| True p | Profile MAE | Ridge MAE | CNN MAE | Profile bias | Ridge bias | CNN bias |
|---:|---:|---:|---:|---:|---:|---:|
| 0.000 | 0.000389 | 0.001505 | 0.001391 | +0.000389 | +0.001505 | +0.001391 |
| 0.004 | 0.000736 | 0.000430 | 0.000968 | −0.000681 | +0.000231 | −0.000968 |
| 0.008 | 0.000543 | 0.000442 | 0.000978 | −0.000080 | +0.000323 | −0.000900 |
| 0.012 | 0.000657 | 0.000492 | 0.000618 | +0.000020 | +0.000087 | +0.000059 |
| 0.016 | 0.000721 | 0.000818 | 0.000896 | −0.000147 | −0.000635 | −0.000570 |

## Training and compute

- CNN: 6,941 parameters; one CPU model; best validation-MAE checkpoint at epoch 49 of 79 epochs run; training time 4.84 seconds.
- Peak runner process RSS: 783,056,896 bytes; total sampling/runtime record: 10.27 seconds. Independent re-training and evidence audit took 9.71 seconds.
- Median decoder reconstruction time was about 6.5 ms for each estimator-specific PyMatching graph. The CNN's calibration inference was slower than Ridge and the Stage 4B profile estimator, while still small in absolute time.
- Runtime values are from this Windows CPU execution; they are not a GPU speed claim or a hardware latency benchmark.

## Prediction utility

At p=0 and p=0.004, CNN and profile-assisted PyMatching disagreed on six shots total; CNN changed four more correct logical decisions into failures than it corrected. At p=0.008, 0.012, and 0.016, their final predictions were identical on all 52,500 evaluated shots. Thus the CNN's lower or higher p estimate often did not change the matching decision. The observed LER difference is not explained by a broad decoder-bank separation: the outputs were identical for most nonzero evaluation shots.

See `STAGE4C_RESULTS.json`, `STAGE4C_PER_ROOT.csv`, and `STAGE4C_PER_CONDITION.csv` for exact counts and per-root details.
