# Q-SHIFT CNN Architecture Stage 2 — Frozen Development Protocol

**Status:** Prospective protocol frozen before sampling; **not executed**. The freeze is limited to a bounded development comparison. It does not authorize training or sampling in this preparation task. The independent test remains unallocated and sealed.

## Question and scope

Does either of the two Stage 1 residual CNN changes improve the historical residual position CNN's useful corrections, and does any candidate reduce logical error relative to the nominal fixed PyMatching decoder on paired development data? The primary candidate is `ResidualPositionCNNV2`; the factorized spatial-temporal CNN and historical CNN are predeclared secondary architecture comparisons. The study is a five-root feasibility assessment, not a confirmatory superiority test.

## Frozen circuit and noise conditions

Use the existing Stim rotated Z-memory surface code at distance 3 and five rounds, with 40 detector bits and one logical observable. Both conditions use the frozen Phase 2B balanced categorical Pauli-channel generator: gate probability 0.003, measurement-flip probability 0.003, bias ratio 10. The paired conditions are:

1. **Nominal:** no added cross-location burst.
2. **Synthetic spatial burst:** after every `MR` round boundary, `CORRELATED_ERROR` applies X jointly to data qubits 8 and 10 with probability 0.01. These five event draws are independent between rounds. This is a synthetic stress mechanism, not a hardware-calibrated noise claim.

Use the Stage 1 DEM conversion in both matching arms: `decompose_errors=True`, `approximate_disjoint_errors=True`, and PyMatching correlation handling enabled. This inherited DEM approximation is a limitation shared by the matching references and must be reported.

## Comparators and information access

- **Nominal fixed PyMatching:** constructed from the no-burst nominal circuit and used on both paired conditions. Its output is the residual-reference bit supplied to every CNN.
- **Burst-informed PyMatching:** constructed from the exact burst circuit and scored only on burst-condition shots. It receives the known burst probability and pair location, so it is a privileged model-informed reference, not a deployable detector-only policy.
- **Historical residual position CNN:** 13,429 parameters in the saved prior run.
- **ResidualPositionCNNV2:** Stage 1 primary candidate; 13,041 parameters in the preflight.
- **FactorizedSpatialTemporalResidualCNN:** Stage 1 secondary candidate; 12,653 parameters in the preflight.

All CNNs receive only the 40 real detector features, occupancy-aware geometry, and nominal fixed PyMatching prediction. Their target is `observable XOR nominal_fixed_prediction`; final output is `nominal_fixed_prediction XOR predicted_residual`. Observable labels and condition/burst metadata are prohibited at inference. Condition metadata may only stratify sampling and reports.

## Allocation and pairing

There are five independent development roots. For each root and each of the two conditions, reserve independent streams of 10,000 training, 2,000 monitor, 2,000 probability-calibration, 2,000 threshold-selection, and 10,000 final-development shots. This is 26,000 shots per condition/root, 52,000 per root, and **260,000 unique shots total**. The ceiling is not increased. The deterministic seed allocation is in `seed_inventory.json`; collision findings and coverage are in `seed_audit.json`.

For each root/condition, generate each partition once. The final-development detector and observable arrays are shared byte-for-byte across all three CNNs and both applicable matching decoders. Prediction arrays are checked against the same observable row order. The burst-informed decoder is not scored on nominal samples as though it were a general baseline.

Training pools exactly 10,000 nominal and 10,000 burst training samples per root (1:1 by construction), or 100,000 unique training shots per architecture across five roots. Each split's underlying sampled arrays are generated once and shared by all candidates; the full 260,000 unique-sample budget is 100,000 training, 20,000 monitor, 20,000 calibration, 20,000 threshold-selection, and 100,000 final-development shots. This equal-mixture choice prevents the larger condition from dominating the CNN objective and defines a balanced two-domain training distribution; it does not provide the CNN with the hidden condition label as a feature. It can still benefit from labeled examples drawn from both distributions, while nominal PyMatching is an analytical fixed decoder and receives no training samples. Thus this is a fair architecture comparison among CNNs, plus an intentionally conventional fixed-decoder comparison, not a claim of equal training-information budgets between neural and matching decoders. The burst-informed matcher receives exact burst metadata and is explicitly privileged. The same pool, class-balanced minibatch policy, optimizer-step cap, early-stopping rule, and partition arrays are used for all three CNNs.

## Rare residual positives and training budget

Train with the existing residual-target implementation and class-balanced minibatches **separately within each condition**, sampling minority examples with replacement when necessary. Use the existing natural-prevalence logit correction from the pooled training prevalence. Each condition has `ceil(10,000/256)=40` batches, so one epoch has 80 optimizer steps and each model/root has at most 800 steps. All models use identical training shot arrays and step limits; repeated positive-example draws are recorded. The process stops before fitting a root if either condition has fewer than 20 unique residual-positive training examples. No data top-up is allowed under this freeze.

Use AdamW (learning rate 0.003, weight decay 0.0001), StepLR (halve after each five completed epochs), at most 10 epochs, batch size 256, patience 3, and best-checkpoint selection by equal-condition monitor NLL. Restore the selected weights before any probability or threshold selection. Monitor, calibration, threshold-selection, and final-development partitions remain disjoint.

This budget is comparable across architectures in unique examples, number of optimizer steps, batches, stopping rule, and optimization schedule. The maximum is 800 optimizer steps per model/root, 12,000 total across all 15 model/root jobs; early stopping may produce different realized step counts, which must be reported rather than padded. Parameter counts differ by less than 6% in the saved Stage 1 preflight. Class-balanced sampling does not make the number of distinct rare positive patterns comparable to the number of training presentations; positive counts and reuse are mandatory results.

## Selection and held-out development evaluation

1. Select checkpoint by minimum equal-condition monitor NLL; ties retain the earlier checkpoint.
2. Select temperature from `[0.5, 0.7, 0.85, 1.0, 1.2, 1.5, 2.0, 3.0, 4.0]` by minimum equal-condition calibration NLL; ties prefer the value nearest 1, then the lower value.
3. Select one threshold from 0.01 through 0.99 in 0.01 increments using equal-condition LER on the separate threshold-selection data; ties prefer nearest 0.5, then lower threshold.
4. Persist model hash, temperature, and threshold before loading the final-development partition. Score that partition exactly once; never revise selections after looking at it.

Report per root and condition: shots, observable positives, natural residual prevalence/count, LER and errors for each arm, prediction distribution, precision/recall, Brier score/NLL, paired disagreements, CNN-only failures, and PyMatching-only failures. Report burst-informed errors separately for the burst condition.

## Frozen analysis and development gate

The primary estimand is, for each root, the equal-weight mean across the two conditions of `(ResidualPositionCNNV2 LER − nominal fixed PyMatching LER)`, using identical shots. Report the mean across five roots and a two-sided 95% Student-t interval `mean(d) ± t(0.975, df=4) * sd(d)/sqrt(5)` over root-level paired effects. Report condition-specific root effects and intervals the same way. These small-sample intervals are descriptive feasibility summaries; no shot-level interval may replace root-level uncertainty and no statistical-superiority claim is authorized. No p-value is used as a success criterion. The two other CNNs are secondary descriptive comparisons; they cannot be promoted to primary after results are viewed. Their multiplicity and the development gate's selection role are reported as limitations.

The predeclared V2 development gate is all of: equal-condition mean LER improvement at least 0.0002 absolute; a favorable paired effect in at least four of five roots; and no condition with mean harm greater than 0.0002 absolute. Compare V2 against burst-informed PyMatching on burst shots as a separate privileged reference. Passing this gate does not demonstrate confirmatory improvement or authorize independent-test access. Failure or ambiguity is reported as failure/inconclusive; no alternative threshold, condition weighting, or architecture winner is selected from final-development outcomes.

## Seed, source, and resource freeze

`FREEZE.json` records SHA-256 hashes of this protocol, readiness report, configuration, seed inventory/audit, this stage's freeze builder, and all referenced architecture, training, circuit, decoder, and Stage 1 evidence sources. Seeds are unique within the allocation and screened against the recoverable historical seed scan plus explicit Phase 3A and Stage 1 diagnostic seed records. Historical coverage is finite; unrecoverable RNG uses cannot be ruled out. No independent-test seed is opened or allocated.

Resource limits: 21,600 seconds wall time; 14,400 seconds measured CUDA training/validation; minimum 2 GiB free disk; process RSS at most 3 GiB; CUDA allocation at most 4 GiB on the RTX 4050 Laptop GPU (6 GB). These are hard stops, not a request to reduce or change the protocol. The 260,000-shot ceiling includes every generated sample. Any future sample-based dry run must use the first 256 shots of the already allocated `dev-root-00/nominal/training` stream, count those shots within its 10,000-shot training partition, and reuse those same rows during training; no extra diagnostic samples or seed stream is permitted. Non-sampling deterministic tensor/circuit checks are preferred. Automatic scale-up is prohibited.

## Not authorized by this freeze

This document does not start training or sample any data. A separate implementation readiness review must confirm a Stage 2 runner exists, validate deterministic sample generation and paired rescoring, verify best-checkpoint restore and split isolation, and benchmark a bounded dry run against these limits. No independent test, production training, scale-up, adaptive switching, or hardware claim is authorized here.
