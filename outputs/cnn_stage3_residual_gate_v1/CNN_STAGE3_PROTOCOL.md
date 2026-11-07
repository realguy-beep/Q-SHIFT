# Q-SHIFT Stage 3 — Correlation-Focused Residual CNN Feasibility Protocol

**Status: prospective protocol; sampling is prohibited until `FREEZE.json` verifies and all deterministic tests pass.** This is a new independent Stage 3 allocation. It does not modify or extend Stage 2's freeze, data, checkpoints, or reports.

## Question and selected direction

Can fresh training focused on a synthetic spatial common-cause burst enable a small **detector-only residual-position CNN** to reduce logical errors relative to nominal fixed PyMatching, without receiving a burst flag, event history, generating-condition label, or true noise parameters at inference?

Stage 2 showed that its mixed-condition CNNs made very few changes and more harmful than helpful corrections. The burst-informed PyMatching reference made 301 errors versus 386 for nominal matching on the same 50,000 burst-condition final-development shots, a privileged 0.00170 observed LER decrease. This provides a model-mismatch question, not evidence for neural improvement. The Stage 3 intervention changes only the candidate's training distribution: one already-tested 13,429-parameter residual-position CNN is trained on the synthetic-burst regime. No larger architecture or second new architecture is introduced. Its inference input remains detector bits plus the nominal PyMatching logical prediction; its correction target is `observable XOR nominal_prediction`.

This is a five-root development feasibility screen. Based on Stage 2, the residual classifier's positive class is below 1% and the V2 model changed only 15 predictions in 50,000 burst shots. The 200,000-shot cap can reveal a large and repeated signal or preserve a negative result, but is **not powered to establish a modest improvement or confirm superiority**. The result must be reported as inconclusive if its paired effect is too small or its interval spans zero.

## Circuit and noise (held fixed)

- Stim rotated surface-code Z memory, distance 3, five rounds, 40 detectors, one logical observable.
- Base circuit: Phase 2B balanced categorical Pauli model, one- and two-qubit gate probability 0.003, measurement-flip probability 0.003, bias ratio 10.
- **Synthetic spatial-burst condition:** after each of five `MR` boundaries, an independent `CORRELATED_ERROR` applies simultaneous X to data qubits 8 and 10 with probability 0.01. This is a synthetic proxy for common-cause crosstalk, not a measured hardware process.
- **Nominal control:** identical base circuit, burst probability 0.
- Matching conversion is fixed to `decompose_errors=True`, `approximate_disjoint_errors=True`, `enable_correlations=True`, as in the prior project. This inherited decomposition can approximate categorical Pauli mechanisms; all DEM and circuit hashes are recorded. Both matching models must have identical detector/observable definitions and shot ordering.

## Decoder arms and information

1. **Nominal fixed PyMatching:** built once from the no-burst DEM; used on nominal and burst arrays; defines the residual target.
2. **Historical residual CNN:** the root-matched saved Stage 2 historical residual-position checkpoint, temperature, and threshold, frozen unchanged. It is scored on new Stage 3 samples and is not refit.
3. **Stage 3 burst-focused residual CNN:** a fresh model of the same historical residual-position architecture, trained only on Stage 3's burst training streams. It receives only the 40 detector bits in the real Stim geometry and the nominal PyMatching prediction. It does not receive burst-event flags, burst locations, condition identifiers, observables, or labels at inference. A single global residual threshold is selected from Stage 3 burst threshold-selection samples. It falls back exactly to nominal PyMatching on every shot where the residual probability is below that threshold.
4. **Burst-informed PyMatching:** built from the burst-inclusive DEM and scored only on burst-condition samples. It receives the true synthetic burst probability and pair at decoder construction; it is a privileged model-informed reference, not a deployable detector-only arm.

All final comparisons use identical detector and observable arrays within each root-condition cell. The historical CNN uses its saved Stage 2 calibration choices; the Stage 3 CNN receives fresh calibration on its own disjoint Stage 3 split. This difference in calibration history is reported.

## New sample allocation (exact cap: 200,000 unique shots)

Five new roots, each with independent Stage 3 streams. No Stage 2 final-development shot is reused in any Stage 3 partition.

| Partition per root | Condition | Shots/root | Across five roots |
|---|---|---:|---:|
| Training | synthetic burst | 17,000 | 85,000 |
| Monitor / best checkpoint | synthetic burst | 2,000 | 10,000 |
| Probability calibration | synthetic burst | 2,000 | 10,000 |
| Threshold selection | synthetic burst | 4,000 | 20,000 |
| Final development | synthetic burst | 10,000 | 50,000 |
| Final nominal control | nominal | 5,000 | 25,000 |
| **Total** |  | **40,000/root** | **200,000** |

The first 256 samples of `stage3-root-00 / training / synthetic_spatial_burst` are the throughput dry run and count within that 17,000-shot allocation. The identical rows are retained as the start of the training partition. No additional diagnostic samples are allowed.

The burst-focused candidate is deliberately trained on one generating distribution, but no condition label is available at inference and the candidate is evaluated on a separately seeded nominal control. Results therefore test a fixed noise-specialist's transfer; they do not demonstrate online adaptation or a regime selector.

## Training and frozen selection

Use the existing historical residual-position CNN architecture from the saved project (13,429 parameters; position-preserving 3-D detector grid plus occupancy channel and nominal PyMatching bit). Keep the Stage 2 optimizer and fitting method: AdamW, learning rate 0.003, weight decay 0.0001, StepLR every five epochs at gamma 0.5, batch size 256, at most ten epochs, patience three, class-balanced minibatches with replacement, and training-prevalence logit correction. Each root has `ceil(17,000/256)=67` steps/epoch and at most 670 optimizer steps. Before fitting, stop if fewer than 20 unique residual-positive burst training examples occur; do not top up or inspect final labels.

For each root:

1. Select the earliest epoch with minimum monitor NLL and restore those weights.
2. Choose a temperature from `[0.5, 0.7, 0.85, 1.0, 1.2, 1.5, 2.0, 3.0, 4.0]` by minimum root-specific probability-calibration NLL; ties prefer nearest 1 then lower.
3. Apply that temperature to each root's separate threshold-selection scores. Choose **one global threshold** from 0.01 through 0.99 in 0.01 increments to minimize the burst LER pooled equally over the five roots; ties prefer nearest 0.5 then lower. This reduces five independent threshold fits to one fixed rule. No final-development label is available during these steps.
4. Atomically persist all five checkpoints, calibration values, and the global threshold in `STAGE3_POLICY_FREEZE.json`. Hash this policy record.
5. Only after that file is verified, generate final-development burst and nominal-control samples. Score those labels once for the frozen comparison; independent rescoring may reread them only to verify stored counts and predictions, never to revise the model or threshold.

## Metrics, uncertainty, and decision gate

Primary paired estimand: across the five roots, the mean of `Stage 3 burst-focused CNN burst LER − nominal fixed PyMatching burst LER`. A negative difference favors the CNN. Report the mean, a two-sided 95% Student-t interval over root-level paired differences (df=4), all five root effects, exact paired disagreement counts, and candidate-only/fixed-only failures. Root intervals are descriptive development uncertainty, not confirmatory inference. No shot-level CI is substituted for root-level variability. Secondary comparisons are descriptive; do not promote a secondary decoder after seeing results.

The predeclared **development success gate** requires every condition below:

1. Primary mean improvement is at least 0.0002 absolute LER (mean difference ≤ −0.0002).
2. At least four of five independent roots favor the Stage 3 CNN.
3. The primary root-level 95% interval's upper endpoint is below zero.
4. On the nominal control, Stage 3 CNN harm relative to nominal fixed PyMatching is no greater than 0.0002 absolute LER.

The gate only decides whether a later, independently frozen confirmatory study is justified. Passing does not establish a neural advantage or hardware relevance. Failing or an interval spanning zero means no demonstrated useful specialization at this budget.

Report per condition and root: raw logical errors/LER, residual target prevalence, useful/harmful corrections, correction precision/recall, candidate-only and fixed-only failures, disagreements, probability Brier/NLL, threshold/temperature, positive-example reuse, checkpoint epoch, model parameter count, inference time, training time, and memory. Burst-informed results remain clearly labeled privileged.

## Seed, freeze, resource, and stop controls

`seed_inventory.json` explicitly reserves 46 distinct sample/training/analysis RNG values beginning at 3,100,000,001. The inventory generator checks them against the archived recoverable seed scan, Stage 1 and Stage 2 inventories/audits, and Phase 3A preflight records. `seed_audit.json` records the exact scanned files, hashes, collisions, and coverage gap. No independent-test seed is allocated. `FREEZE.json` hashes this protocol, code, configuration, inventory, audit, historical model selections/checkpoints, and relevant circuit/decoder sources before sampling.

Hard limits: 14,400 seconds wall time, 9,000 measured CUDA training seconds, RSS 3.5 GiB, CUDA allocation 4.5 GiB, and at least 10 GiB free disk. CUDA is required; CPU fallback is forbidden. Stop on a freeze/hash or seed error, any data overlap, fewer than 20 unique residual positives, invalid shape/value, non-finite loss/gradient, failed independent prediction recomputation, or resource breach. Preserve partial files and status; never silently change counts or seeds.

## Preservation and claims boundary

All Phase 1–5, Stage 1/2, Phase 3A and prior reports remain unchanged. Stage 2 final-development samples are diagnostic context only and are never Stage 3 train/calibration/threshold/evaluation samples. No independent test, quantum hardware, live device telemetry, or actual hardware correction is used. The spatial burst is synthetic and DEM matching inherits `approximate_disjoint_errors=True`; conclusions are restricted to this one distance-3 circuit, basis, event pair, and probability.
