# Q-SHIFT hybrid residual-decoder sprint v1

## Status and question

This is a new, development-only experiment. The previous 750,000-shot
experiment and every historical artifact remain read-only. The question is
whether a residual model trained under the established balanced objective can
be made safer by a validation-selected confidence gate, and whether an
imbalance-aware weighted-natural objective changes paired logical outcomes.
This is feasibility work, not a confirmatory test.

## Frozen candidates

All candidates use the existing position-preserving residual 3-D CNN with the
frozen Phase 2B Z-memory PyMatching decoder as the parity baseline. The target
is `observable XOR PyMatching_prediction`; final output is `PyMatching XOR
predicted_residual`.

1. **Balanced residual CNN:** existing architecture and balanced minibatches;
   restore the best checkpoint by monitor negative log likelihood (NLL), then
   select temperature on calibration data and a single correction threshold
   minimizing equal-regime LER on threshold-selection data.
2. **Confidence-gated policy:** same balanced residual CNN weights and
   calibrated probabilities. Among the fixed 0.01–0.99 threshold grid, allow
   a threshold only if a one-sided Wilson lower bound for correction precision
   exceeds 0.5, with Bonferroni familywise alpha 0.05 across all 99 thresholds.
   Select the qualifying threshold with lowest equal-regime threshold-split
   LER; ties prefer the threshold closest to 0.5, then the higher threshold.
   If none qualifies, make no residual corrections (exact PyMatching fallback).
3. **Weighted-natural residual CNN:** same architecture and optimizer, natural
   shuffled minibatches, BCE-with-logits with the training-only ratio
   `negative_count/positive_count` as `pos_weight`. Before calibration, remove
   the analytically expected `log(pos_weight)` logit offset. Temperature and
   LER-minimizing threshold are selected on their designated partitions.

The architecture is held fixed because the prior evidence suggests a
decision-calibration and rare-positive problem, not a demonstrated need for a
new architecture. Three nested per-regime training budgets (10k, 30k, 60k) are
evaluated only in order; no automatic expansion beyond the frozen cap occurs.

## Circuits and samples

Reuse the existing categorical Pauli-channel Stim generator, Z-memory rotated
surface code, distance 3, five rounds, 40 detectors and one observable. The
fixed comparator is the already selected Phase 2B nominal PyMatching model
(index 2). Generating regimes are `x_biased`, `balanced`, and `z_biased`, with
the existing generator's frozen 0.003 gate/measurement probabilities and
bias ratio 10. Each decoder prediction is paired to the same detector sample
and observable label.

Five independent root IDs use separate fresh simulator streams for training,
monitoring (6,000 shots/regime/root), probability calibration (15,000),
threshold selection (15,000), and final development evaluation (15,000).
Train streams are generated in nested prefixes up to 60,000 shots per
regime/root. Final-evaluation streams are not generated or loaded until all
weights, temperatures, thresholds, and gate/fallback choices are frozen for
every candidate. The final stream is scored once per frozen candidate family.
It is not an independent test set.

The seed allocator uses `block = 2,130,000,001 + 1,000 * (3*root + regime_index)`
with regime order `x_biased`, `balanced`, `z_biased`; offsets are train 0,
monitor 100, calibration 200, threshold selection 300, and final development
evaluation 400. Each partition consumes consecutive seeds from its offset,
one seed per 1,024-shot Stim batch (including a final partial batch). Model
RNG triplets begin at 2,140,000,001 and advance by ten per root/strategy/budget
job. Diagnostic Stim seeds are 2,145,000,001–2,145,000,003; the deterministic
checkpoint-resume model probe uses 2,145,000,010. The predeclared exact
sign-flip and root-bootstrap allocations are 2,146,000,001 and 2,146,000,002.
The inventory checks every derived value for internal duplicates and screens
against the recoverable explicitly test-free seed inventories named in
`prepare_freeze.py`. Independent-test seed records are deliberately not read.
The freeze therefore documents the limit of historical seed coverage rather
than claiming unavailable test-seed coverage.

Maximum planned data if every stage runs: 900,000 training + 90,000 monitor +
225,000 calibration + 225,000 threshold-selection + 225,000 final development
evaluation = **1,665,000 unique Stim shots**, plus the explicitly reserved
small diagnostic preflight. Repeated model scoring does not count as new
shots. The runner records exact generated and consumed counts by partition.

## Training and selection

AdamW learning rate 0.003, weight decay 0.0001, StepLR step size 5/gamma 0.5,
batch 256, at most 10 epochs, monitor-NLL patience 3, four-channel position
CNN and head width 16. Best monitor checkpoint is restored before calibration.
No old-run final-evaluation probabilities or thresholds enter any choice.

Balanced training uses the existing balanced-minibatch helper and the existing
natural-prior logit adjustment. Weighted-natural training uses shuffled natural
examples; the training positive weight and its logit correction are computed
from train labels only. Calibration temperature is chosen by macro NLL on the
separate calibration partition. Threshold and confidence-gate decisions use
only threshold-selection labels. The held-aside final development labels are
never used for training, checkpoint selection, temperature, threshold, or
gate choice.

## Analysis plan

Per-shot paired outcomes include raw residual prevalence, PyMatching errors,
candidate errors, candidate-only and PyMatching-only failures, correction
frequency, helpful corrections (true residual positives), harmful corrections
(false residual positives), precision, recall, Brier score, and regime results.
Per-root equal-regime paired LER difference is the independent-cluster summary.
Report mean and Student-t 95% interval across five roots, a 100,000-resample
root bootstrap interval, and exact two-sided root sign-flip result. Holm adjusts
the nine frozen model/policy/size comparisons versus PyMatching. These analyses
remain exploratory with five roots; no confirmatory superiority claim is
possible. Shot-level paired tests are descriptive only.

The predeclared decision candidate is the 60K-per-regime balanced residual CNN
with the confidence gate. A development signal sufficient to propose a separate
frozen confirmatory study requires at least 0.0002 absolute LER reduction vs
PyMatching, improvement in at least four of five roots, an upper 95% root
bootstrap bound below zero, and correction precision above 0.5. This is only a
feasibility gate; all nine comparisons remain multiplicity-adjusted, and no
independent test or superiority claim is authorized.

## Resource, restart, and safety limits

Hard caps: 10,800 active wall seconds, 9,000 CUDA seconds, RSS 3 GiB, CUDA
allocation 4 GiB, and minimum free disk 2 GiB. Simulation is chunked at 1,024
shots, partitions and job checkpoints are atomically saved and SHA-256
verified. A stop marker is honored at the next checkpoint boundary. Resume
continues with the same frozen streams and checkpoints; it does not create new
seeds. The process has no independent-test sampler. It makes no network calls
or dependency installs.

## Predeclared interpretation

The confidence gate is useful only if it reduces harmful updates without
discarding most helpful corrections and improves final paired LER. Weighted
training is useful only if its independent-root final development results are
better and stable against PyMatching. A positive development result is a
reason to design a separately frozen confirmatory study, not evidence of
generalization. A null or negative result is preserved and ends this sprint;
no further threshold or architecture search is allowed.
