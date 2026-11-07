# Feasibility results: observable-only gate audit

## Execution

No new simulation samples were generated. analyze_existing_gate_opportunity.py read the 24-root, 98,304-shot paired development record, recomputed detector-only calibration choices, and independently checked prediction/error arrays against UTILITY_PER_ROOT.csv. The gate models used leave-one-root-out predictions; generating regime was used only for reporting strata and not as a feature.

## Paired decoder opportunity

| Comparator | Errors | LER | Paired difference vs pooled |
|---|---:|---:|---:|
| Pooled fixed / no update | 681 | 0.0069275 | reference |
| Always-adaptive / calibration-selected (same policy here) | 672 | 0.0068359 | −9 errors; −0.0000916 |
| Calibration-confidence gate, LOO, cutoff 0.5 | 686 | 0.0069784 | +5 errors; +0.0000509 |
| Current-syndrome confidence gate, LOO-root, cutoff 0.5 | 684 | 0.0069580 | +3 errors; +0.0000305 |
| Simple current detector likelihood threshold | 672 | 0.0068359 | Same as always-adaptive; no fallback events |

The inherited paired estimate for always-adaptive minus pooled is **−0.0000916**, with a seed-stratified 95% interval **[−0.000417, +0.000234]**. It includes zero and is not independent validation of the gates.

## Does confidence predict helpful versus harmful updates?

- The calibration-prefix utility classifier had out-of-root AUC 0.570, barely above chance, and Brier 0.2371 versus a 0.2344 constant-prevalence score. Its 0.5 policy switched on 21/24 roots, fell back on 3, and the 6 harmful switches outweighed its utility enough to finish 5 errors worse than pooled.
- The current-shot disagreement classifier had out-of-root AUC 0.464 and Brier 0.2502 versus 0.2496 constant prevalence. It selected the candidate on 131/225 disagreements: 67 harmful and 64 helpful. It fell back on the other 94 disagreements, avoiding 41 candidate harms but missing 53 candidate wins. Net result: 3 more errors than pooled.
- The direct detector-likelihood threshold made no selective choices: all 225 disagreements favored the selected profile by this proxy, despite 108 candidate-only failures and 117 fixed-only failures. Better fit of detector marginals did not identify per-shot logical utility.

No confidence rule demonstrated useful discrimination of update utility. The per-shot disagreement itself is rare. It can only affect 0.229% of samples in this study, and computing it requires both decoders, at least doubling decoder calls for the affected policy path (or running both on all shots if disagreement is not otherwise known).

## Fallback, latency, and memory

| Gate | Fallback frequency | Harmful candidate decisions | Helpful candidate decisions | Measured cost |
|---|---:|---:|---:|---|
| Calibration-prefix gate | 3/24 roots (12.5%) | 6/21 selected roots were worse than pooled | 12/21 were better; 3 tied | 0.33 s total offline analysis process, not a per-shot latency measurement. A block gate can decode one model after deciding. |
| Current-syndrome gate | 94/225 disagreements (41.8%); 67 candidate selections were harmful, 64 helpful | 67/131 candidate selections (51.1%) | 64/131 | Requires both decoder outputs before choosing; decode overhead is at least one extra matcher pass relative to fixed-only. No native decoder latency was measured in this analysis. |

The analysis process working set was 150.2 MB before loading the NPZ, 158.4 MB after analysis, and 204.6 MB peak. These process-level figures include Python, NumPy, scikit-learn, and mapped arrays; they do not isolate PyMatching model memory. Per-decoder memory and real-time gate latency remain unmeasured. The measured 0.40 s is the total script runtime for feature construction and grouped cross-validation, not hardware or decoder timing. A separate small rebuild fixture in the preceding feasibility phase measured 2.291 ms median and 2.401 ms p95 for DEM-plus-PyMatching reconstruction; its 3.09 MiB process working-set increase covered multiple models and probes, not one gate. Those measurements are context, not a gated-policy benchmark.

## Evidence interpretation

The small apparent baseline gain is not reliable headroom for a gate. On the present development roots, both causal gates slightly worsened the pooled baseline. The current-syndrome classifier was no better than the base rate, and the likelihood-threshold rule simply reproduced unconditional adaptation. No independent roots remain in this saved evidence for a fresh confirmatory evaluation, so the data do not pass the requested authorization condition.
