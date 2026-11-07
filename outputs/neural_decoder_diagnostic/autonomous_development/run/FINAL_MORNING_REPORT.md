# Q-SHIFT Autonomous Development Morning Report

**Status:** completed

Development-only experiment. No independent test stream was allocated, generated, or accessed.

## Completed job summary

| Model | Train shots/regime | Roots | Mean LER | LER 95% root-t interval | Mean PM LER | Mean paired difference | Paired-difference 95% root-t interval | Candidate-only / PM-only |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| balanced_mlp | 3,000 | 5 | 1.33133% | [1.19748%, 1.46519%] | 0.43533% | +0.89600% | [+0.77119%, +1.02081%] | 1602 / 258 |
| balanced_mlp | 10,000 | 5 | 1.22933% | [1.08765%, 1.37102%] | 0.43533% | +0.79400% | [+0.63827%, +0.94973%] | 1457 / 266 |
| balanced_mlp | 30,000 | 5 | 0.87333% | [0.77449%, 0.97218%] | 0.43533% | +0.43800% | [+0.32869%, +0.54731%] | 902 / 245 |
| pooled_cnn16_capacity_control | 3,000 | 5 | 5.41400% | [5.24523%, 5.58277%] | 0.43533% | +4.97867% | [+4.82121%, +5.13613%] | 7788 / 320 |
| pooled_cnn16_capacity_control | 10,000 | 5 | 2.06467% | [1.47765%, 2.65169%] | 0.43533% | +1.62933% | [+1.04672%, +2.21195%] | 2709 / 265 |
| pooled_cnn16_capacity_control | 30,000 | 5 | 1.09267% | [0.89303%, 1.29230%] | 0.43533% | +0.65733% | [+0.46360%, +0.85107%] | 1223 / 237 |
| position_flat_cnn | 3,000 | 5 | 2.70533% | [1.19265%, 4.21802%] | 0.43533% | +2.27000% | [+0.76486%, +3.77514%] | 3690 / 285 |
| position_flat_cnn | 10,000 | 5 | 1.28333% | [1.22416%, 1.34251%] | 0.43533% | +0.84800% | [+0.78987%, +0.90613%] | 1532 / 260 |
| position_flat_cnn | 30,000 | 5 | 1.04000% | [0.87999%, 1.20001%] | 0.43533% | +0.60467% | [+0.42884%, +0.78049%] | 1152 / 245 |
| residual_position_cnn | 10,000 | 5 | 0.45933% | [0.40803%, 0.51064%] | 0.43533% | +0.02400% | [-0.00107%, +0.04907%] | 49 / 13 |

## Root-level results

| Root | Model | Train shots/regime | Equal-regime LER | PyMatching LER | Paired difference | Candidate-only / PM-only |
|---:|---|---:|---:|---:|---:|---:|
| 0 | balanced_mlp | 10,000 | 1.33000% | 0.41667% | +0.91333% | 319 / 45 |
| 0 | balanced_mlp | 3,000 | 1.25000% | 0.41667% | +0.83333% | 304 / 54 |
| 0 | balanced_mlp | 30,000 | 0.78333% | 0.41667% | +0.36667% | 158 / 48 |
| 0 | pooled_cnn16_capacity_control | 10,000 | 2.63667% | 0.41667% | +2.22000% | 713 / 47 |
| 0 | pooled_cnn16_capacity_control | 3,000 | 5.54000% | 0.41667% | +5.12333% | 1600 / 63 |
| 0 | pooled_cnn16_capacity_control | 30,000 | 1.25667% | 0.41667% | +0.84000% | 301 / 49 |
| 0 | position_flat_cnn | 10,000 | 1.28333% | 0.41667% | +0.86667% | 314 / 54 |
| 0 | position_flat_cnn | 3,000 | 2.90667% | 0.41667% | +2.49000% | 804 / 57 |
| 0 | position_flat_cnn | 30,000 | 0.89000% | 0.41667% | +0.47333% | 191 / 49 |
| 0 | residual_position_cnn | 10,000 | 0.41333% | 0.41667% | -0.00333% | 0 / 1 |
| 1 | balanced_mlp | 10,000 | 1.29333% | 0.44667% | +0.84667% | 304 / 50 |
| 1 | balanced_mlp | 3,000 | 1.26333% | 0.44667% | +0.81667% | 294 / 49 |
| 1 | balanced_mlp | 30,000 | 0.95333% | 0.44667% | +0.50667% | 203 / 51 |
| 1 | pooled_cnn16_capacity_control | 10,000 | 2.17000% | 0.44667% | +1.72333% | 578 / 61 |
| 1 | pooled_cnn16_capacity_control | 3,000 | 5.30000% | 0.44667% | +4.85333% | 1516 / 60 |
| 1 | pooled_cnn16_capacity_control | 30,000 | 1.04333% | 0.44667% | +0.59667% | 231 / 52 |
| 1 | position_flat_cnn | 10,000 | 1.22333% | 0.44667% | +0.77667% | 283 / 50 |
| 1 | position_flat_cnn | 3,000 | 4.71667% | 0.44667% | +4.27000% | 1335 / 54 |
| 1 | position_flat_cnn | 30,000 | 0.99667% | 0.44667% | +0.55000% | 216 / 51 |
| 1 | residual_position_cnn | 10,000 | 0.50000% | 0.44667% | +0.05333% | 18 / 2 |
| 2 | balanced_mlp | 10,000 | 1.25667% | 0.46333% | +0.79333% | 307 / 69 |
| 2 | balanced_mlp | 3,000 | 1.51333% | 0.46333% | +1.05000% | 371 / 56 |
| 2 | balanced_mlp | 30,000 | 0.88333% | 0.46333% | +0.42000% | 180 / 54 |
| 2 | pooled_cnn16_capacity_control | 10,000 | 1.70333% | 0.46333% | +1.24000% | 426 / 54 |
| 2 | pooled_cnn16_capacity_control | 3,000 | 5.56000% | 0.46333% | +5.09667% | 1603 / 74 |
| 2 | pooled_cnn16_capacity_control | 30,000 | 1.27000% | 0.46333% | +0.80667% | 296 / 54 |
| 2 | position_flat_cnn | 10,000 | 1.35667% | 0.46333% | +0.89333% | 330 / 62 |
| 2 | position_flat_cnn | 3,000 | 2.34667% | 0.46333% | +1.88333% | 629 / 64 |
| 2 | position_flat_cnn | 30,000 | 0.98333% | 0.46333% | +0.52000% | 209 / 53 |
| 2 | residual_position_cnn | 10,000 | 0.49000% | 0.46333% | +0.02667% | 16 / 8 |
| 3 | balanced_mlp | 10,000 | 1.03667% | 0.45333% | +0.58333% | 230 / 55 |
| 3 | balanced_mlp | 3,000 | 1.28667% | 0.45333% | +0.83333% | 303 / 53 |
| 3 | balanced_mlp | 30,000 | 0.80000% | 0.45333% | +0.34667% | 152 / 48 |
| 3 | pooled_cnn16_capacity_control | 10,000 | 2.34000% | 0.45333% | +1.88667% | 619 / 53 |
| 3 | pooled_cnn16_capacity_control | 3,000 | 5.41000% | 0.45333% | +4.95667% | 1551 / 64 |
| 3 | pooled_cnn16_capacity_control | 30,000 | 0.95000% | 0.45333% | +0.49667% | 186 / 37 |
| 3 | position_flat_cnn | 10,000 | 1.28000% | 0.45333% | +0.82667% | 298 / 50 |
| 3 | position_flat_cnn | 3,000 | 1.83000% | 0.45333% | +1.37667% | 471 / 58 |
| 3 | position_flat_cnn | 30,000 | 1.10333% | 0.45333% | +0.65000% | 241 / 46 |
| 3 | residual_position_cnn | 10,000 | 0.47667% | 0.45333% | +0.02333% | 9 / 2 |
| 4 | balanced_mlp | 10,000 | 1.23000% | 0.39667% | +0.83333% | 297 / 47 |
| 4 | balanced_mlp | 3,000 | 1.34333% | 0.39667% | +0.94667% | 330 / 46 |
| 4 | balanced_mlp | 30,000 | 0.94667% | 0.39667% | +0.55000% | 209 / 44 |
| 4 | pooled_cnn16_capacity_control | 10,000 | 1.47333% | 0.39667% | +1.07667% | 373 / 50 |
| 4 | pooled_cnn16_capacity_control | 3,000 | 5.26000% | 0.39667% | +4.86333% | 1518 / 59 |
| 4 | pooled_cnn16_capacity_control | 30,000 | 0.94333% | 0.39667% | +0.54667% | 209 / 45 |
| 4 | position_flat_cnn | 10,000 | 1.27333% | 0.39667% | +0.87667% | 307 / 44 |
| 4 | position_flat_cnn | 3,000 | 1.72667% | 0.39667% | +1.33000% | 451 / 52 |
| 4 | position_flat_cnn | 30,000 | 1.22667% | 0.39667% | +0.83000% | 295 / 46 |
| 4 | residual_position_cnn | 10,000 | 0.41667% | 0.39667% | +0.02000% | 6 / 0 |

## By generating regime

| Model | Size/regime | Regime | Roots | Mean neural LER | Mean PyMatching LER | Paired difference and 95% root-t interval | Positive recall |
|---|---:|---|---:|---:|---:|---:|---:|
| balanced_mlp | 3,000 | balanced | 5 | 1.50800% | 0.50000% | +1.00800% ([+0.77287%, +1.24313%]) | mean recall 80.634% |
| balanced_mlp | 3,000 | x_biased | 5 | 2.00800% | 0.67600% | +1.33200% ([+1.23770%, +1.42630%]) | mean recall 77.037% |
| balanced_mlp | 3,000 | z_biased | 5 | 0.47800% | 0.13000% | +0.34800% ([+0.18723%, +0.50877%]) | mean recall 87.807% |
| balanced_mlp | 10,000 | balanced | 5 | 1.42000% | 0.50000% | +0.92000% ([+0.59543%, +1.24457%]) | mean recall 83.713% |
| balanced_mlp | 10,000 | x_biased | 5 | 1.89200% | 0.67600% | +1.21600% ([+0.99979%, +1.43221%]) | mean recall 82.085% |
| balanced_mlp | 10,000 | z_biased | 5 | 0.37600% | 0.13000% | +0.24600% ([+0.15162%, +0.34038%]) | mean recall 91.515% |
| balanced_mlp | 30,000 | balanced | 5 | 0.94800% | 0.50000% | +0.44800% ([+0.30153%, +0.59447%]) | mean recall 92.096% |
| balanced_mlp | 30,000 | x_biased | 5 | 1.40200% | 0.67600% | +0.72600% ([+0.53924%, +0.91276%]) | mean recall 89.234% |
| balanced_mlp | 30,000 | z_biased | 5 | 0.27000% | 0.13000% | +0.14000% ([+0.06708%, +0.21292%]) | mean recall 96.128% |
| pooled_cnn16_capacity_control | 3,000 | balanced | 5 | 5.99200% | 0.50000% | +5.49200% ([+5.04220%, +5.94180%]) | mean recall 4.293% |
| pooled_cnn16_capacity_control | 3,000 | x_biased | 5 | 7.40000% | 0.67600% | +6.72400% ([+6.49803%, +6.94997%]) | mean recall 2.927% |
| pooled_cnn16_capacity_control | 3,000 | z_biased | 5 | 2.85000% | 0.13000% | +2.72000% ([+2.60896%, +2.83104%]) | mean recall 3.308% |
| pooled_cnn16_capacity_control | 10,000 | balanced | 5 | 2.47000% | 0.50000% | +1.97000% ([+1.24958%, +2.69042%]) | mean recall 76.188% |
| pooled_cnn16_capacity_control | 10,000 | x_biased | 5 | 2.65600% | 0.67600% | +1.98000% ([+1.28990%, +2.67010%]) | mean recall 77.597% |
| pooled_cnn16_capacity_control | 10,000 | z_biased | 5 | 1.06800% | 0.13000% | +0.93800% ([+0.52064%, +1.35536%]) | mean recall 79.118% |
| pooled_cnn16_capacity_control | 30,000 | balanced | 5 | 1.26800% | 0.50000% | +0.76800% ([+0.46347%, +1.07253%]) | mean recall 86.292% |
| pooled_cnn16_capacity_control | 30,000 | x_biased | 5 | 1.59000% | 0.67600% | +0.91400% ([+0.75104%, +1.07696%]) | mean recall 84.885% |
| pooled_cnn16_capacity_control | 30,000 | z_biased | 5 | 0.42000% | 0.13000% | +0.29000% ([+0.15891%, +0.42109%]) | mean recall 90.259% |
| position_flat_cnn | 3,000 | balanced | 5 | 3.06000% | 0.50000% | +2.56000% ([+1.00956%, +4.11044%]) | mean recall 66.924% |
| position_flat_cnn | 3,000 | x_biased | 5 | 3.66200% | 0.67600% | +2.98600% ([+1.01945%, +4.95255%]) | mean recall 61.979% |
| position_flat_cnn | 3,000 | z_biased | 5 | 1.39400% | 0.13000% | +1.26400% ([+0.25060%, +2.27740%]) | mean recall 77.022% |
| position_flat_cnn | 10,000 | balanced | 5 | 1.47800% | 0.50000% | +0.97800% ([+0.72841%, +1.22759%]) | mean recall 79.327% |
| position_flat_cnn | 10,000 | x_biased | 5 | 1.95000% | 0.67600% | +1.27400% ([+1.16241%, +1.38559%]) | mean recall 77.786% |
| position_flat_cnn | 10,000 | z_biased | 5 | 0.42200% | 0.13000% | +0.29200% ([+0.22210%, +0.36190%]) | mean recall 87.996% |
| position_flat_cnn | 30,000 | balanced | 5 | 1.18800% | 0.50000% | +0.68800% ([+0.42197%, +0.95403%]) | mean recall 84.843% |
| position_flat_cnn | 30,000 | x_biased | 5 | 1.60600% | 0.67600% | +0.93000% ([+0.67107%, +1.18893%]) | mean recall 83.180% |
| position_flat_cnn | 30,000 | z_biased | 5 | 0.32600% | 0.13000% | +0.19600% ([+0.08067%, +0.31133%]) | mean recall 91.156% |
| residual_position_cnn | 10,000 | balanced | 5 | 0.53000% | 0.50000% | +0.03000% ([-0.00041%, +0.06041%]) | mean recall 96.127% |
| residual_position_cnn | 10,000 | x_biased | 5 | 0.71000% | 0.67600% | +0.03400% ([-0.01535%, +0.08335%]) | mean recall 94.048% |
| residual_position_cnn | 10,000 | z_biased | 5 | 0.13800% | 0.13000% | +0.00800% ([-0.01240%, +0.02840%]) | mean recall 98.194% |

## Interpretation and gate

These are development estimates. Thresholds were frozen using separate threshold-selection streams before final-development evaluation; they are not independent confirmatory results.
A GO decision for a larger supervised study requires a reproducible, practically meaningful paired benefit across independent roots. This report does not authorize opening or generating an independent test set.
