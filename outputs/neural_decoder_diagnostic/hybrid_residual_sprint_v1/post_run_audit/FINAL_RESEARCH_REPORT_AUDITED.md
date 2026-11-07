# Q-SHIFT Hybrid Residual Sprint — Audited Final Research Report

**Study class:** development-only feasibility study; not confirmatory.  
**Controller state:** `failed` during finalization.  
**Scientific evidence status:** saved training/evaluation evidence independently recomputed and passed; no training restart was performed.  
**Independent-test access:** 0; the test allocation remains sealed.

## Executive finding

The frozen sprint completed all **30/30 training jobs** across five independent development roots and generated the planned **1,665,000 unique production shots**, plus **384 diagnostic shots**. It evaluated **225,000 paired final-development shots** (five roots × three regimes × 15,000). The independent read-only verifier re-decoded all 30 saved prediction archives, recomputed the selected-model probabilities and all 135 paired metric rows, and reproduced the aggregate and root-level statistics. The final evidence audit passes, with an important operational exception: the controller itself recorded `failed` because its verifier was called before the controller changed status from sampling to completed. The runner therefore did not create its own checkpoint manifest.

Frozen PyMatching made **1,129/225,000 errors (0.501778% LER)**. The predeclared primary candidate—balanced residual CNN, 60,000 training shots per regime/root, confidence-gated correction—also made **1,129 errors**, exactly matching PyMatching on every evaluated shot. Its paired LER difference was zero; all five root clusters tied. The gate selected no residual corrections in all five primary-root selections, so correction precision is not estimable. The predeclared development gate failed. **Recommendation: NO-GO for scaling this residual decoder to 10M or 60M shots.**

## Design and audit scope

The frozen task was Z-memory, rotated surface code, distance 3, five rounds, 40 detectors, one logical observable, with 0.003 gate and measurement probabilities and x-biased, balanced, and z-biased regimes. Each model was a residual 3-D CNN correcting the frozen Phase 2B PyMatching prediction. Final output followed the frozen convention: PyMatching prediction XOR predicted residual. The two training approaches were balanced minibatches and natural sampling with training-only inverse-prevalence weighting. Per-regime training budgets were 10k, 30k, and 60k; calibration, threshold selection, and final development evaluation used separate generated streams. No final-evaluation labels entered fitting, checkpoint choice, temperature selection, thresholds, or gate decisions according to the frozen protocol and audited source/data partitions.

The audit validated frozen configuration and source hashes; data archive hashes, seed maps, and partition sizes; all 30 model-weight and optimizer-state checkpoint hashes; all 30 prediction archive hashes and bindings to frozen selections; 135 paired evaluation rows; and independent PyMatching re-decoding / CNN prediction recomputation. The final-development samples were paired across each candidate and its PyMatching baseline. Five roots are the inferential clusters; shot counts do not replace the small root count.

## Frozen comparisons

LER differences below are candidate minus PyMatching; negative is favorable. Root-bootstrap intervals resample the five independent roots and are descriptive. All nine Holm-adjusted p-values equal 1.0. See the source JSON and `AUDITED_PER_ROOT.csv` for root values.

| Training strategy | Samples / regime / root | Policy | Errors / 225,000 | LER | Paired Δ vs PM (95% root bootstrap CI) | Candidate-only / PM-only | Root wins/losses/ties | Sign-flip p | Holm p |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| balanced_minibatch | 10,000 | confidence_gate | 1,129 | 0.501778% | 0.000000 pp [0.000000 pp, 0.000000 pp] | 0 / 0 | 0/0/5 | 1 | 1 |
| balanced_minibatch | 10,000 | min_ler | 1,137 | 0.505333% | 0.003556 pp [-0.004444 pp, 0.013778 pp] | 28 / 20 | 1/3/1 | 0.625 | 1 |
| balanced_minibatch | 30,000 | confidence_gate | 1,129 | 0.501778% | 0.000000 pp [0.000000 pp, 0.000000 pp] | 0 / 0 | 0/0/5 | 1 | 1 |
| balanced_minibatch | 30,000 | min_ler | 1,129 | 0.501778% | 0.000000 pp [-0.009333 pp, 0.006222 pp] | 23 / 23 | 1/4/0 | 1 | 1 |
| balanced_minibatch | 60,000 | confidence_gate | 1,129 | 0.501778% | 0.000000 pp [0.000000 pp, 0.000000 pp] | 0 / 0 | 0/0/5 | 1 | 1 |
| balanced_minibatch | 60,000 | min_ler | 1,137 | 0.505333% | 0.003556 pp [-0.004444 pp, 0.010222 pp] | 56 / 48 | 1/4/0 | 0.5 | 1 |
| natural_inverse_prevalence_weighted | 10,000 | min_ler | 1,131 | 0.502667% | 0.000889 pp [-0.000889 pp, 0.003111 pp] | 4 / 2 | 1/2/2 | 0.75 | 1 |
| natural_inverse_prevalence_weighted | 30,000 | min_ler | 1,134 | 0.504000% | 0.002222 pp [-0.000444 pp, 0.004889 pp] | 21 / 16 | 1/3/1 | 0.375 | 1 |
| natural_inverse_prevalence_weighted | 60,000 | min_ler | 1,129 | 0.501778% | 0.000000 pp [-0.001333 pp, 0.001333 pp] | 20 / 20 | 1/1/3 | 1 | 1 |

For the primary confidence-gated 60k candidate, PyMatching and candidate each had **1,129 errors**; candidate-only / PyMatching-only failures were **0 / 0**, paired delta **0.000000 percentage points**, root bootstrap interval **[0, 0]**, exact root sign-flip p = **1**, and Holm p = **1**. There was no change in prediction on the evaluated samples.

## Results by generating regime

Each row pools 75,000 paired shots (five roots × 15,000) for that regime. The complete per-root input rows are preserved in the derived audit CSV.

| Strategy | N / regime | Policy | Regime | Candidate errors / 75,000 | Candidate LER | PM errors / 75,000 | PM LER | Paired Δ | Root mean Δ (95% t CI) | Candidate-only / PM-only |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| balanced_minibatch | 10,000 | confidence_gate | x_biased | 617 / 75,000 | 0.822667% | 617 / 75,000 | 0.822667% | 0.000000 pp | 0.000000 pp [0.000000 pp, 0.000000 pp] | 0 / 0 |
| balanced_minibatch | 10,000 | confidence_gate | balanced | 393 / 75,000 | 0.524000% | 393 / 75,000 | 0.524000% | 0.000000 pp | 0.000000 pp [0.000000 pp, 0.000000 pp] | 0 / 0 |
| balanced_minibatch | 10,000 | confidence_gate | z_biased | 119 / 75,000 | 0.158667% | 119 / 75,000 | 0.158667% | 0.000000 pp | 0.000000 pp [0.000000 pp, 0.000000 pp] | 0 / 0 |
| balanced_minibatch | 10,000 | min_ler | x_biased | 624 / 75,000 | 0.832000% | 617 / 75,000 | 0.822667% | 0.009333 pp | 0.009333 pp [-0.016580 pp, 0.035247 pp] | 12 / 5 |
| balanced_minibatch | 10,000 | min_ler | balanced | 397 / 75,000 | 0.529333% | 393 / 75,000 | 0.524000% | 0.005333 pp | 0.005333 pp [-0.018371 pp, 0.029037 pp] | 14 / 10 |
| balanced_minibatch | 10,000 | min_ler | z_biased | 116 / 75,000 | 0.154667% | 119 / 75,000 | 0.158667% | -0.004000 pp | -0.004000 pp [-0.011404 pp, 0.003404 pp] | 2 / 5 |
| balanced_minibatch | 30,000 | confidence_gate | x_biased | 617 / 75,000 | 0.822667% | 617 / 75,000 | 0.822667% | 0.000000 pp | 0.000000 pp [0.000000 pp, 0.000000 pp] | 0 / 0 |
| balanced_minibatch | 30,000 | confidence_gate | balanced | 393 / 75,000 | 0.524000% | 393 / 75,000 | 0.524000% | 0.000000 pp | 0.000000 pp [0.000000 pp, 0.000000 pp] | 0 / 0 |
| balanced_minibatch | 30,000 | confidence_gate | z_biased | 119 / 75,000 | 0.158667% | 119 / 75,000 | 0.158667% | 0.000000 pp | 0.000000 pp [0.000000 pp, 0.000000 pp] | 0 / 0 |
| balanced_minibatch | 30,000 | min_ler | x_biased | 616 / 75,000 | 0.821333% | 617 / 75,000 | 0.822667% | -0.001333 pp | -0.001333 pp [-0.014935 pp, 0.012268 pp] | 6 / 7 |
| balanced_minibatch | 30,000 | min_ler | balanced | 397 / 75,000 | 0.529333% | 393 / 75,000 | 0.524000% | 0.005333 pp | 0.005333 pp [-0.024166 pp, 0.034833 pp] | 16 / 12 |
| balanced_minibatch | 30,000 | min_ler | z_biased | 116 / 75,000 | 0.154667% | 119 / 75,000 | 0.158667% | -0.004000 pp | -0.004000 pp [-0.011404 pp, 0.003404 pp] | 1 / 4 |
| balanced_minibatch | 60,000 | confidence_gate | x_biased | 617 / 75,000 | 0.822667% | 617 / 75,000 | 0.822667% | 0.000000 pp | 0.000000 pp [0.000000 pp, 0.000000 pp] | 0 / 0 |
| balanced_minibatch | 60,000 | confidence_gate | balanced | 393 / 75,000 | 0.524000% | 393 / 75,000 | 0.524000% | 0.000000 pp | 0.000000 pp [0.000000 pp, 0.000000 pp] | 0 / 0 |
| balanced_minibatch | 60,000 | confidence_gate | z_biased | 119 / 75,000 | 0.158667% | 119 / 75,000 | 0.158667% | 0.000000 pp | 0.000000 pp [0.000000 pp, 0.000000 pp] | 0 / 0 |
| balanced_minibatch | 60,000 | min_ler | x_biased | 628 / 75,000 | 0.837333% | 617 / 75,000 | 0.822667% | 0.014667 pp | 0.014667 pp [-0.015972 pp, 0.045306 pp] | 20 / 9 |
| balanced_minibatch | 60,000 | min_ler | balanced | 403 / 75,000 | 0.537333% | 393 / 75,000 | 0.524000% | 0.013333 pp | 0.013333 pp [0.000245 pp, 0.026422 pp] | 30 / 20 |
| balanced_minibatch | 60,000 | min_ler | z_biased | 106 / 75,000 | 0.141333% | 119 / 75,000 | 0.158667% | -0.017333 pp | -0.017333 pp [-0.043900 pp, 0.009233 pp] | 6 / 19 |
| natural_inverse_prevalence_weighted | 10,000 | min_ler | x_biased | 618 / 75,000 | 0.824000% | 617 / 75,000 | 0.822667% | 0.001333 pp | 0.001333 pp [-0.005592 pp, 0.008259 pp] | 2 / 1 |
| natural_inverse_prevalence_weighted | 10,000 | min_ler | balanced | 394 / 75,000 | 0.525333% | 393 / 75,000 | 0.524000% | 0.001333 pp | 0.001333 pp [-0.005592 pp, 0.008259 pp] | 2 / 1 |
| natural_inverse_prevalence_weighted | 10,000 | min_ler | z_biased | 119 / 75,000 | 0.158667% | 119 / 75,000 | 0.158667% | 0.000000 pp | 0.000000 pp [0.000000 pp, 0.000000 pp] | 0 / 0 |
| natural_inverse_prevalence_weighted | 30,000 | min_ler | x_biased | 624 / 75,000 | 0.832000% | 617 / 75,000 | 0.822667% | 0.009333 pp | 0.009333 pp [-0.000105 pp, 0.018771 pp] | 12 / 5 |
| natural_inverse_prevalence_weighted | 30,000 | min_ler | balanced | 390 / 75,000 | 0.520000% | 393 / 75,000 | 0.524000% | -0.004000 pp | -0.004000 pp [-0.015106 pp, 0.007106 pp] | 7 / 10 |
| natural_inverse_prevalence_weighted | 30,000 | min_ler | z_biased | 120 / 75,000 | 0.160000% | 119 / 75,000 | 0.158667% | 0.001333 pp | 0.001333 pp [-0.002369 pp, 0.005035 pp] | 2 / 1 |
| natural_inverse_prevalence_weighted | 60,000 | min_ler | x_biased | 617 / 75,000 | 0.822667% | 617 / 75,000 | 0.822667% | 0.000000 pp | 0.000000 pp [-0.010138 pp, 0.010138 pp] | 6 / 6 |
| natural_inverse_prevalence_weighted | 60,000 | min_ler | balanced | 391 / 75,000 | 0.521333% | 393 / 75,000 | 0.524000% | -0.002667 pp | -0.002667 pp [-0.007201 pp, 0.001867 pp] | 10 / 12 |
| natural_inverse_prevalence_weighted | 60,000 | min_ler | z_biased | 121 / 75,000 | 0.161333% | 119 / 75,000 | 0.158667% | 0.002667 pp | 0.002667 pp [-0.004737 pp, 0.010071 pp] | 4 / 2 |

Baseline regime counts were x-biased **617/75,000 (0.822667%)**, balanced **393/75,000 (0.524000%)**, and z-biased **119/75,000 (0.158667%)**. No candidate was better in the aggregate than fixed PyMatching. Some threshold-selected candidates traded small gains in one regime against losses in another. The largest apparent regime gains remain exploratory and are not reliable evidence of specialization with five roots and nine comparisons.

## Learning and paired correction diagnostics

The confidence-gated balanced candidates fell back exactly to PyMatching in **15/15** root × training-size selections. For the non-gated threshold-minimized candidates, useful and harmful residual corrections were mixed:

- Balanced 10k: 20 PyMatching-only errors corrected versus 28 candidate-only failures; aggregate LER was worse.
- Balanced 30k: 23 versus 23; aggregate LER tied, despite root-level variation.
- Balanced 60k: 48 versus 56; aggregate LER was worse.
- Weighted-natural 10k: 2 versus 4; worse.
- Weighted-natural 30k: 16 versus 21; worse.
- Weighted-natural 60k: 20 versus 20; aggregate tie.

The best monitor checkpoint was restored before calibration, per the frozen protocol. This study shows that the CNN can emit some nonzero residual corrections under threshold-minimized policies, but their utility did not beat the matching baseline. It does not establish that additional examples will fix the problem. The confidence gate's conservative all-fallback behavior avoided added errors but also delivered no gain.

## Resource use

Recorded active wall time was **1,211.8 s (20.2 min)**; CUDA training and selection **684.9 s**; CUDA inference **4.5 s**; maximum process RSS **1.405 GiB**; maximum CUDA allocation **0.066 GiB**; minimum free disk **252.49 GiB**. The frozen resource limits were not exceeded.

## Limitations and decision

This is a small feasibility study with five independent roots. Root t intervals and 100,000-resample root bootstraps are descriptive, and exact sign-flip tests have coarse resolution at n=5. The nine candidate/policy/budget comparisons were exploratory and Holm-adjusted. The endpoint is simulated development LER under one distance, basis, and noise family; there is no hardware evaluation, no independent test evaluation, and no claim of generalization. No direct MLP, non-residual CNN, or pooled CNN arm was part of this sprint; prior runs must not be conflated with these residual-CNN results.

**Decision: NO-GO for 10M/60M scaling under the current model and protocol.** Keep frozen PyMatching as the default. A non-training administrative recovery may preserve an external audit manifest and corrected report; do not relaunch or resume this experiment. Any future training effort should first present a distinct, evidence-based hypothesis and a separately frozen bounded development design. The runner's failed status should remain in the historical run record.

## Reproduction and evidence

The run was manually launched using the frozen controller. Read-only evidence recomputation was performed with `post_run_audit/verify_saved_results_after_runner_failure.py`; report tables are regenerated by `post_run_audit/generate_final_audit.py`. Neither script samples new shots or accesses test data. See `RUNNER_FAILURE_DIAGNOSIS.md`, `NEXT_EXPERIMENT_DECISION_AUDITED.md`, and `FINAL_EVIDENCE_MANIFEST.json`.
