# Autonomous Development Protocol

## Status and scope

This is a prospective, development-only experiment. The prepared legacy 100K run is not used. The independent test allocation is not represented in the seed inventory and the controller has no test-sampling path. Do not launch the full run unless the user explicitly approves the `--full-run --confirm-full-autonomous` command after reviewing the dry-run readiness report.

## Question and comparisons

The study asks whether additional training data improves a position-preserving detector CNN, and whether a PyMatching-assisted residual CNN changes logical decisions on the same samples. It is not a confirmatory test of neural superiority.

On each root's shared detector/observable streams, compare:

1. Flattened position-preserving 3-D CNN at 3,000, 10,000, and 30,000 training shots per generating regime.
2. Balanced MLP at the same nested training budgets.
3. A larger pooled CNN16 capacity control at the same budgets.
4. A separate residual position CNN at 10,000 training shots per regime. Its target is `observable XOR frozen PyMatching prediction`; inference applies `PyMatching prediction XOR predicted residual`.

The conventional decoder is frozen Phase 2B PyMatching model index 2 for the Z-memory experiment, using the frozen nominal DEM. Neural outputs never replace or modify the classical baseline records.

## Circuit and generation

- Stim Z-memory rotated surface code, distance 3, five rounds, 40 detector bits, one logical observable.
- Frozen Phase 2B categorical Pauli-channel generator, nominal gate and measurement probabilities 0.003/0.003, bias ratio 10, regimes in frozen order `x_biased`, `balanced`, `z_biased`.
- Five independent development roots. Each root has separate simulator streams for training, monitoring, probability calibration, threshold selection, and final development evaluation. The final-evaluation stream is not sampled or loaded until the model, temperature, and threshold are saved for that job; it is then saved once per root and shared across jobs for paired scoring.
- Training data are generated once per root/regime at 30,000 shots and smaller learning-curve fits use nested prefixes. All models are evaluated on identical saved final-development shots within a root/regime.
- Four validation partitions per root/regime: monitor 4,000; calibration 3,000; threshold-selection 3,000; final development evaluation 10,000.
- Total full-run generation: 450,000 training + 300,000 validation = 750,000 shots. The extra dry-run streams are separate and small.

## Model selection and scoring

- Balanced minibatches give each class equal representation within each batch; the final partial batch is retained. BCE-with-logits is used. Natural-prevalence logit correction uses training labels only. AdamW uses the frozen 0.003 learning rate, and StepLR halves it after each five completed epochs; optimizer and scheduler states are checkpointed.
- Best checkpoint is selected by equal-regime monitor NLL with patience 3 and a fixed maximum of 10 epochs. The saved best weights are restored before calibration or evaluation.
- Temperature is chosen on the calibration partition by equal-regime NLL over the frozen grid. A single threshold is selected on the separate threshold-selection partition by equal-regime residual logical error; ties prefer threshold nearest 0.5, then the lower threshold.
- Only after temperature and threshold are atomically recorded does the controller load the final-development evaluation partition. The final partition is scored once and never used for model, epoch, temperature, or threshold selection.
- Primary descriptive endpoint: equal-regime LER and paired LER difference versus PyMatching within each root. The residual pilot is separately reported versus PyMatching and paired with it shot-for-shot.
- Root-level mean and paired-difference intervals use two-sided Student-t 95% intervals across independent roots. They are descriptive feasibility intervals, not confirmatory tests. No significance claim is predeclared.

## Resource and restart policy

- Hard caps: 6 hours active wall time, 4 hours measured CUDA training plus validation/final inference, at least 2 GiB free disk, process RSS at most 3 GiB, CUDA allocated memory at most 4 GiB.
- Data are atomically written per root. Checkpoints alternate between two slots, each SHA-256 verified; a corrupted latest slot falls back to the last valid prior slot. If both are invalid, the controller stops.
- Training progress, model/optimizer/RNG states, next batch, selected best weights, and validation history are checkpointed. A safe stop is honored at a batch boundary; a partially sampled root is deterministically regenerated from its frozen seeds.
- Resuming requires `--resume --confirm-full-autonomous`. This clears a previously acknowledged stop marker and continues from verified artifacts.
- NaNs, non-binary labels, unexpected dimensions, hash mismatches, seed collisions, prohibited split names, or resource-cap violations stop execution and write traceback/progress evidence.

## Frozen budget

Five roots × (three direct models × three training sizes + one residual model) = 50 model jobs. Maximum 10 epochs/job, batch size 256, early-stop patience 3. No automatic scale-up beyond these budgets, no overnight background launch, and no access to independent test data.
