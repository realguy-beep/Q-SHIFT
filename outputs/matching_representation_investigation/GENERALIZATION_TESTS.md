# Preregistered deterministic generalization suite

The suite design and fixed seed list were saved in `CASE_PLAN.json` before decoder outcomes were generated. It uses exhaustive finite-state risk, not Monte Carlo: no confidence intervals or significance tests apply to these deterministic enumerations. The eight categorical cases use seeds 61001–61008 and two independent `PAULI_CHANNEL_2` categorical sites per case. The separate 4×4×4 parameter grid varies the event probability and two boundary-channel probabilities in a fixed two-detector graphlike motif. Surface fragments are truncated Phase 2B circuits at rounds 1 and 2; their reference is exact inference on the **independent DEM**, not the native categorical physical circuit.

## Independent categorical cases

Risk means the exact probability that the decoder's predicted observable correction is wrong under the categorical channel, summed over all syndromes. The separator-free column is included only because every complete event in these two-detector cases passes the graphlike validity checks.

| Case | exact_categorical_map | exact_independent_dem_map | pymatching_standard | pymatching_correlated | separator_free_standard | local_restricted_posterior |
|---|---:|---:|---:|---:|---:|---:|
| seed 61001 | 0.05331117 | 0.05331117 | 0.16578218 | 0.16578218 | 0.10321070 | 0.05331117 |
| seed 61002 | 0.04042791 | 0.04042791 | 0.15365118 | 0.15365118 | 0.06600347 | 0.04042791 |
| seed 61003 | 0.04525379 | 0.04525379 | 0.09844360 | 0.09844360 | 0.07444211 | 0.04525379 |
| seed 61004 | 0.03436708 | 0.03436708 | 0.12813083 | 0.12813083 | 0.04541970 | 0.03436708 |
| seed 61005 | 0.06289763 | 0.06289763 | 0.15094920 | 0.15094920 | 0.11039626 | 0.06289763 |
| seed 61006 | 0.06847653 | 0.06847653 | 0.11826997 | 0.11826997 | 0.07240594 | 0.06847653 |
| seed 61007 | 0.05699998 | 0.05699998 | 0.07358134 | 0.07358134 | 0.05699998 | 0.05699998 |
| seed 61008 | 0.04336790 | 0.04336790 | 0.12464667 | 0.12464667 | 0.04336790 | 0.04336790 |

Across these cases, exact categorical and exact independent-DEM MAP decisions agree on every syndrome despite joint-distribution total-variation distances of approximately 0.0040–0.0075. Standard and correlation-enabled PyMatching make identical predictions in all eight cases. The local restricted posterior matches exact categorical MAP in all eight 4-syndrome instances because its selected subproblem covers all relevant events there. These are bounded fixtures, not evidence of full-circuit equivalence.

## Fixed graphlike parameter grid

All 64 cells preserve the same complete independent event distribution between the separator and separator-free forms. The full per-cell result is retained below and in `SEPARATOR_GRID.csv`.

| p | q | r | Standard separated | Standard separator-free | Difference |
|---:|---:|---:|---:|---:|---:|
| 0.01 | 0.01 | 0.01 | 0.010000 | 0.000298 | -0.009702 |
| 0.01 | 0.01 | 0.03 | 0.010000 | 0.000694 | -0.009306 |
| 0.01 | 0.01 | 0.10 | 0.010000 | 0.002080 | -0.007920 |
| 0.01 | 0.01 | 0.20 | 0.010000 | 0.004060 | -0.005940 |
| 0.01 | 0.03 | 0.01 | 0.030000 | 0.000694 | -0.029306 |
| 0.01 | 0.03 | 0.03 | 0.030000 | 0.001482 | -0.028518 |
| 0.01 | 0.03 | 0.10 | 0.030000 | 0.004240 | -0.025760 |
| 0.01 | 0.03 | 0.20 | 0.030000 | 0.008180 | -0.021820 |
| 0.01 | 0.10 | 0.01 | 0.100000 | 0.002080 | -0.097920 |
| 0.01 | 0.10 | 0.03 | 0.100000 | 0.004240 | -0.095760 |
| 0.01 | 0.10 | 0.10 | 0.100000 | 0.010000 | -0.090000 |
| 0.01 | 0.10 | 0.20 | 0.100000 | 0.010000 | -0.090000 |
| 0.01 | 0.20 | 0.01 | 0.200000 | 0.004060 | -0.195940 |
| 0.01 | 0.20 | 0.03 | 0.200000 | 0.008180 | -0.191820 |
| 0.01 | 0.20 | 0.10 | 0.200000 | 0.010000 | -0.190000 |
| 0.01 | 0.20 | 0.20 | 0.200000 | 0.010000 | -0.190000 |
| 0.03 | 0.01 | 0.01 | 0.010000 | 0.000694 | -0.009306 |
| 0.03 | 0.01 | 0.03 | 0.010000 | 0.001482 | -0.008518 |
| 0.03 | 0.01 | 0.10 | 0.010000 | 0.004240 | -0.005760 |
| 0.03 | 0.01 | 0.20 | 0.010000 | 0.008180 | -0.001820 |
| 0.03 | 0.03 | 0.01 | 0.030000 | 0.001482 | -0.028518 |
| 0.03 | 0.03 | 0.03 | 0.030000 | 0.002646 | -0.027354 |
| 0.03 | 0.03 | 0.10 | 0.030000 | 0.006720 | -0.023280 |
| 0.03 | 0.03 | 0.20 | 0.030000 | 0.012540 | -0.017460 |
| 0.03 | 0.10 | 0.01 | 0.100000 | 0.004240 | -0.095760 |
| 0.03 | 0.10 | 0.03 | 0.100000 | 0.006720 | -0.093280 |
| 0.03 | 0.10 | 0.10 | 0.100000 | 0.015400 | -0.084600 |
| 0.03 | 0.10 | 0.20 | 0.100000 | 0.027800 | -0.072200 |
| 0.03 | 0.20 | 0.01 | 0.200000 | 0.008180 | -0.191820 |
| 0.03 | 0.20 | 0.03 | 0.200000 | 0.012540 | -0.187460 |
| 0.03 | 0.20 | 0.10 | 0.200000 | 0.027800 | -0.172200 |
| 0.03 | 0.20 | 0.20 | 0.200000 | 0.030000 | -0.170000 |
| 0.10 | 0.01 | 0.01 | 0.010000 | 0.002080 | -0.007920 |
| 0.10 | 0.01 | 0.03 | 0.010000 | 0.004240 | -0.005760 |
| 0.10 | 0.01 | 0.10 | 0.010000 | 0.010000 | +0.000000 |
| 0.10 | 0.01 | 0.20 | 0.010000 | 0.010000 | +0.000000 |
| 0.10 | 0.03 | 0.01 | 0.030000 | 0.004240 | -0.025760 |
| 0.10 | 0.03 | 0.03 | 0.030000 | 0.006720 | -0.023280 |
| 0.10 | 0.03 | 0.10 | 0.030000 | 0.015400 | -0.014600 |
| 0.10 | 0.03 | 0.20 | 0.030000 | 0.027800 | -0.002200 |
| 0.10 | 0.10 | 0.01 | 0.100000 | 0.010000 | -0.090000 |
| 0.10 | 0.10 | 0.03 | 0.100000 | 0.015400 | -0.084600 |
| 0.10 | 0.10 | 0.10 | 0.100000 | 0.028000 | -0.072000 |
| 0.10 | 0.10 | 0.20 | 0.100000 | 0.046000 | -0.054000 |
| 0.10 | 0.20 | 0.01 | 0.200000 | 0.010000 | -0.190000 |
| 0.10 | 0.20 | 0.03 | 0.200000 | 0.027800 | -0.172200 |
| 0.10 | 0.20 | 0.10 | 0.200000 | 0.046000 | -0.154000 |
| 0.10 | 0.20 | 0.20 | 0.200000 | 0.072000 | -0.128000 |
| 0.20 | 0.01 | 0.01 | 0.010000 | 0.004060 | -0.005940 |
| 0.20 | 0.01 | 0.03 | 0.010000 | 0.008180 | -0.001820 |
| 0.20 | 0.01 | 0.10 | 0.010000 | 0.010000 | +0.000000 |
| 0.20 | 0.01 | 0.20 | 0.010000 | 0.010000 | +0.000000 |
| 0.20 | 0.03 | 0.01 | 0.030000 | 0.008180 | -0.021820 |
| 0.20 | 0.03 | 0.03 | 0.030000 | 0.012540 | -0.017460 |
| 0.20 | 0.03 | 0.10 | 0.030000 | 0.027800 | -0.002200 |
| 0.20 | 0.03 | 0.20 | 0.030000 | 0.030000 | +0.000000 |
| 0.20 | 0.10 | 0.01 | 0.100000 | 0.010000 | -0.090000 |
| 0.20 | 0.10 | 0.03 | 0.100000 | 0.027800 | -0.072200 |
| 0.20 | 0.10 | 0.10 | 0.100000 | 0.046000 | -0.054000 |
| 0.20 | 0.10 | 0.20 | 0.100000 | 0.072000 | -0.028000 |
| 0.20 | 0.20 | 0.01 | 0.200000 | 0.010000 | -0.190000 |
| 0.20 | 0.20 | 0.03 | 0.200000 | 0.030000 | -0.170000 |
| 0.20 | 0.20 | 0.10 | 0.200000 | 0.072000 | -0.128000 |
| 0.20 | 0.20 | 0.20 | 0.200000 | 0.104000 | -0.096000 |

Separator-free standard matching improves exact risk in **59/64** cells, ties **5/64**, and worsens in none; the improvement range is 0 to 0.19594 absolute in this purposely small toy family. This does not prove safe generality beyond the admissible graphlike motif.

## Reduced surface fragments: exact independent-DEM inference

| Fragment | Exact DEM MAP | Standard PM | Correlated PM | Valid separator-free PM | Local posterior | PM standard/correlated syndrome disagreements |
|---|---:|---:|---:|---:|---:|---:|
| phase2b z memory r1 balanced | 0.00091043 | 0.00094767 | 0.00094767 | 0.00091733 | 0.00092636 | 0 |
| phase2b z memory r2 balanced | 0.00168340 | 0.00195711 | 0.00192241 | — | — | 12048 |
| phase2b x memory r1 balanced | 0.00094925 | 0.00097326 | 0.00097326 | 0.00094939 | 0.00095120 | 0 |
| phase2b x memory r2 balanced | 0.00177524 | 0.00221278 | 0.00280800 | — | — | 18122 |

The one-round fragments have eight detectors and 256 possible syndromes. The two-round fragments have sixteen detectors and 65,536 syndromes, including many zero-mass syndromes. Decoder risks are weighted by exact positive-mass syndrome probability.

## Full Phase 2B structure-only regeneration

These six rows regenerate circuit and DEM structure only: no shots were generated and no Phase 2B test labels were read. Text contents match the saved circuit/DEM files; the historical Phase 2B manifest independently checks their raw file hashes.

| Basis | Regime | Detectors | Mechanisms | Separator mechanisms | Support 3 or 4 | Matching graph nodes / edges |
|---|---|---:|---:|---:|---:|---:|
| Z | x_biased | 40 | 586 | 444 | 317 | 40 / 142 |
| Z | balanced | 40 | 586 | 444 | 317 | 40 / 142 |
| Z | z_biased | 40 | 586 | 444 | 317 | 40 / 142 |
| X | x_biased | 40 | 578 | 436 | 315 | 40 / 142 |
| X | balanced | 40 | 578 | 436 | 315 | 40 / 142 |
| X | z_biased | 40 | 578 | 436 | 315 | 40 / 142 |

For all six conditions the full event detector support includes four-detector hyperedges, so Candidate A rejects them. The 121 events with support 3 or 4 per condition are not eligible for the simple safe graphlike rewrite.
