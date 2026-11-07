# Q-SHIFT Stage 3 — Stage 2 Retrospective Diagnostic Review

## Scope and data boundary

This review reads only Stage 2's saved **final-development** prediction archives, its per-root/training diagnostics, frozen protocol, runner, and independent recovery audit. The Stage 2 final-development labels are used retrospectively to understand the prior method. They were not used to fit a Stage 3 model, choose a Stage 3 threshold, or alter the frozen Stage 3 allocation. No independent-test directory, file, seed, or result was opened. The read-only calculation is reproducible with `python outputs/cnn_stage3_residual_gate_v1/diagnose_stage2.py`; its summary is `STAGE2_RETROSPECTIVE_DIAGNOSTICS.json`.

## What Stage 2 actually found

The paired Stage 2 final-development set had 100,000 unique shots: 50,000 nominal and 50,000 synthetic-burst. Fixed nominal PyMatching made 255 nominal errors and 386 burst-condition errors (641 total). The V2 residual CNN made 650 total errors; its equal-condition LER difference was **+0.000090** versus fixed PyMatching, with a descriptive five-root 95% interval of **[-0.0000294, +0.0002094]**. The prespecified Stage 2 development gate failed.

| Decoder on Stage 2 final-development samples | Nominal errors / 50,000 | Burst errors / 50,000 | Total errors / 100,000 |
|---|---:|---:|---:|
| Nominal fixed PyMatching | 255 | 386 | 641 |
| Historical residual-position CNN | 254 | 389 | 643 |
| ResidualPositionCNNV2 | 255 | 395 | 650 |
| Factorized spatial-temporal residual CNN | 257 | 402 | 659 |
| Burst-informed PyMatching, burst only | n/a | 301 | n/a |

The burst-informed matching model reduced the observed burst error count by 85/50,000 (0.00170 absolute LER) relative to nominal matching. It is privileged: its DEM includes the exact synthetic burst probability and pair. This establishes that a model supplied with the right event mechanism can use it in this simulator; it does not establish that a detector-only neural model can infer the event or that the synthetic event is hardware-realistic.

## Why corrections hurt

For V2, the baseline had 641 failures. The CNN changed only **17/100,000** predictions: **4 useful** changes corrected baseline failures and **13 harmful** changes turned baseline successes into failures. Thus correction precision was **4/17 = 23.5%**, recall among baseline failures was **4/641 = 0.62%**, and net errors increased by nine. The burst cell accounted for 3 useful and 12 harmful changes; nominal had one of each. The historical CNN changed 12 decisions (5 useful, 7 harmful); the factorized model changed 42 (12 useful, 30 harmful). These are direct counts, not a claim that every harmful change has the same cause.

The V2 residual score ranked baseline failures above baseline successes in this retrospective set: ROC AUC was **0.942 nominal** and **0.932 burst** (root ranges 0.925–0.972 and 0.922–0.947). Yet the already-frozen thresholds produced few changes and low correction precision. AUC measures ranking across all thresholds; it does not guarantee that the rare high-score tail is precise enough to reduce LER. Stage 2 Brier scores were 0.00504 nominal and 0.00735 burst; ten-bin equal-width ECE was 0.00221 and 0.00153 respectively. These are retrospective calibration summaries and must not be used to tune Stage 3.

The Stage 2 threshold was chosen from only 2,000 threshold-selection shots per root-condition cell, while residual targets were rare. The five roots had 42–52 nominal and 60–76 burst training residual positives per 10,000-shot cell. Balanced sampling therefore repeated each positive example substantially: the reported positive-draw/unique-positive ratios ranged from roughly **329 to 1,064**. This confirms heavy reuse; it makes memorization plausible but does not prove that memorization caused the errors. Temperature calibration cannot by itself fix a weakly estimated rare-event tail or a poor conditional model.

## Syndrome-pattern evidence and limits

Across five roots, the 255 nominal baseline failures comprised 245 distinct detector bit patterns; the 386 burst failures comprised 355. Most failure examples were therefore not repeated exact syndromes. V2 made one useful nominal change and three useful burst changes, across one and three distinct patterns respectively. This is far too few observations to identify stable detector motifs. The median detector Hamming weight was four for baseline failures and zero for baseline successes, but that coarse retrospective association is not a useful learned correction rule by itself.

The failure labels are `observable XOR nominal_PyMatching_prediction`. A true residual-positive example is exactly a baseline logical failure; applying residual bit 1 flips the predicted logical observable. The Stage 2 independent recovery audit re-decoded saved detector rows, reproduced CNN outputs from saved weights, checked split hashes and XOR metrics, and passed. Thus the correction accounting is not explained by a prediction/label convention mismatch. The original audit's `KeyError: 'shots'` was an aggregate-reporting bug; its failure record remains preserved.

## Approach decision

| Option | Assessment from saved evidence | Decision |
|---|---|---|
| A. Residual hard-example learning | The residual class is rare and already oversampled heavily. More selective sampling needs inclusion-probability correction and could amplify memorization. The present data do not identify a stable hard-example family. | Defer. |
| B. Correlation-focused detector-only residual CNN | The burst-informed DEM has clear privileged headroom, while the Stage 2 CNN saw only a 1:1 mixed training pool. Detector geometry and rounds are available to the model. A focused burst-distribution training run can test whether this compact model learns useful syndrome patterns without a burst flag. | **Select as the single Stage 3 question.** |
| C. Conservative learned correction gate | This is scientifically sensible, but Stage 2 already used probability calibration and a separately selected residual threshold. The major unknown is whether correlation-focused learning supplies a useful signal, not whether a second threshold rule can hide an unchanged model's harmful tail. The Stage 3 residual threshold remains a strict fallback: no correction unless the selected score threshold is crossed. | Keep as an implementation property, not a second research direction. |

No larger CNN is justified. Stage 2's 13,429-parameter historical residual CNN, 13,041-parameter V2, and 12,653-parameter factorized CNN all stayed near the same capacity; V2 and factorized models did not beat PyMatching. Stage 3 therefore keeps the established 13,429-parameter position-preserving residual CNN and changes one scientific factor: training on the burst condition rather than mixing nominal and burst examples. This avoids attributing any difference to a larger architecture.

The direction is a bounded feasibility question, not a novelty claim. Neural decoders have previously used syndrome data to exploit correlated errors: [Baireuther et al. (2017 preprint)](https://arxiv.org/abs/1705.07855), [Varbanov et al., *Phys. Rev. Research* 7, 013029 (2025)](https://doi.org/10.1103/PhysRevResearch.7.013029), and [Bausch et al., *Nature* 635, 834–840 (2024)](https://doi.org/10.1038/s41586-024-08148-8). Those studies use different decoders, noise models, data, and scales. They show that learning from correlated syndromes is established research, not that Q-SHIFT's small synthetic-burst experiment is novel or comparable.

## Feasibility and interpretation

The 200,000-shot budget can support a five-root development screen with new training, monitor, calibration, threshold-selection, and final-development streams. It cannot support a confirmatory superiority claim. Stage 2's V2 disagreed with the strong fixed decoder only 15 times in 50,000 burst shots, so small LER differences may remain unresolved even at this budget. The Stage 3 success gate is consequently a **large-effect feasibility gate**; failure or an interval spanning zero means no demonstrated useful neural specialization, not proof that all CNN decoders are impossible.

The burst generator remains a synthetic proxy: a simultaneous X on data qubits 8 and 10 after each of five MR boundaries, independently with probability 0.01 per boundary, superposed on the Phase 2B balanced categorical Pauli circuit. No hardware-calibrated crosstalk model is available. Burst-informed PyMatching knows this generator and is an upper-reference comparator, not an information-matched deployable arm.
