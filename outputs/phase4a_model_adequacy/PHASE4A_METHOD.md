# Phase 4A: frozen model-adequacy protocol

## Hypothesis and scope

Primary hypothesis: under measurement-heavy noise, a detector-calibrated pair of gate/measurement probabilities reduces residual logical-observable error compared with fixed nominal PyMatching. This is a static calibrated-model experiment, not an adaptive switching experiment. The test condition's true rates are not passed to the calibrated fit. Each specialist receives a separate stationary calibration batch; there is no online change detection.

## Circuit and noise

Stim `surface_code:rotated_memory_z`, distance 3, five rounds. Use the generated circuit's native `after_clifford_depolarization=p_gate` and `before_measure_flip_probability=p_meas`. Single-qubit Clifford locations receive DEPOLARIZE1; two-qubit Clifford locations receive DEPOLARIZE2, a channel over the pair's 15 nonidentity Pauli products. No replacement with independent participant channels. Generated measurement noise is a basis-appropriate anticommuting Pauli before measurement. Reset and idle noise are disabled. The generator's gate schedule, detector annotations and logical Z observable are identical across conditions. Native depolarizing noise admits DEM generation without the disjoint-error approximation flag.

Data-heavy: (.006,.001); nominal: (.003,.003); measurement-heavy: (.001,.006), with coordinates (gate, measurement). Probabilities are per channel invocation, not per round or equal total circuit fault budgets. Faults after gates include ancillas. The noiseless control uses 256 diagnostic shots, separately reported from the experimental shot budget.

## Models and calibration

Fixed model: DEM at (.003,.003). Model-informed reference: DEM at the true pair, used only as an explicitly informed benchmark, not a guaranteed optimal decoder. Calibrated model: choose one of nine grid pairs from {.001,.003,.006} squared using only calibration detector counts. All models use ordinary PyMatching without correlation-aware decoding. Thus algorithm choice is held constant.

Generate 50,000 template shots per grid pair (450,000 total); fit each detector marginal with Jeffreys smoothing (k+.5)/(N+1). Score calibration counts with a composite Bernoulli log likelihood summed over detectors. This intentionally approximates correlated detectors; it is a fitting score, not an exact joint likelihood or calibrated posterior. Resolve exact score ties by the grid order. Templates are shared across replicates; uncertainty is conditional on this template bank. All true probabilities are on the grid; this study does not demonstrate continuous-rate or unseen-mixture generalization.

## Separation, budget, and gates

Twenty seed roots 42000001+10000*i. Per root and each of three conditions: 20,000 independent calibration shots, 10,000 validation shots, and 30,000 paired final test shots. Stage seeds are root+100/200/300+condition index. Template seeds start at 43000001. This totals at most 3.6m study shots plus 450k templates. Sampling/decoding proceeds in batches of at most 10,000. Store packed detector data and observable labels; labels are accessed only for validation/test scoring. Freeze config, method, and runner SHA-256 before any sampling.

Preflight checks: common ideal circuit text, expected 40 detectors and one observable, noiseless detector/observable zeros, native noise instructions and probabilities, successful exact DEM conversion, unique stage seeds, historical seed collision screening, and same-sized matching graphs. Save circuit/DEM text and hashes plus graph-weight differences.

Complete calibration and validation for all roots before any final test shots. Stop if exact rate-pair recovery is less than 16/20 for any condition. Stop if calibrated versus fixed primary validation predictions disagree on fewer than 100 shots, or calibrated primary validation residual count is not lower. The latter is a directional screening rule, not a declaration of statistical success. No retuning after this screen. These explicit gates operationalize the audit's calibration-failure and specialist-usefulness requirements.

## Inference and success

Residual = sampled logical observable XOR predicted correction. Compare each candidate with fixed on the identical test shots. Report raw/residual counts, Wilson intervals, candidate-only/fixed-only failures, disagreement rate, paired difference and approximate paired 95% interval, exact two-sided McNemar, per-seed differences, seed-bootstrap mean 95% interval, and seed sign test. Independent shots are paired across decoders; seed grouping does not itself create dependence.

Primary success requires calibrated minus fixed rate <= -.0001, exact McNemar p<.05, and seed-bootstrap mean upper 95% bound <0. Sign test is a robustness diagnostic. Secondary family: both candidates in each of three conditions except the primary calibrated comparison (five comparisons); Holm-adjust exact McNemar and seed sign tests separately. No optional significance stopping. Aggregate across all completed 20 roots only for the planned confirmatory analysis. Report primary absolute and relative improvement and any secondary harm. This gate justifies further replication research, not an adaptive-superiority claim.

## Resource limits and fallback

Conservatively cap the entire run after preflight start at 900 wall-clock seconds, including I/O and analysis. Check before every batch and phase. If time, validation, or calibration checks fail, save the stop reason and partial checkpoints and generate an incomplete/stopped report. Do not silently lower the seed count, change rates, or claim confirmation. No adaptive selector. Capture process peak working set (including native allocations where available), decoder time/shot, model construction, calibration fitting, simulation, and wall time separately. Expected working memory below 2 GB; terminate between batches if process RSS exceeds 2 GB. CPU execution only. All historical outputs remain read-only.
