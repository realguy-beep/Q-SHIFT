# V1.6 development gate: pre-registration

This file is committed **before** any learner statistic is computed on real (already-exposed) data. The learner was developed and tested only on synthetic data drawn exactly from the DEM (`tests/test_learner.py`). The hidden second burst is sealed (commitment `caa9fd07…`) and is **not** used here.

## Data (already exposed; known burst X8 X12 X15 only; no new sampling)

- **Stage 1** (detector-only): calibration archives from V1.2, V1.3 and V1.5, `pilot_runs/attempt_001/calibration/cal_q{qi}_r{rr}.npz`. That is 3 studies × 72 per-root batches × 500 rows = 216 batches, each with a known generating q.
- **Stage 2** (labeled): the first 500 shots of each nonzero-q evaluation archive from V1.2 and V1.3 (96 roots). Each is paired with the same root's calibration batch from Stage 1.

## Learner (as implemented in `learner.py`, unchanged after this commit)

- **Stage 1:** `ParityLearner` over the 15 signature classes. The acceptance threshold is Δ ≥ the χ²₁ quantile at 1 − 0.01/15, a Bonferroni correction across the 15 classes (≈ 11.57, computed in `dev_gate.py`).
- **Stage 2:** `learn_flip` at that root's Stage 1 q̂, by exact joint likelihood.

## Gate criteria (all must hold → PASS)

- **G1:** at q ∈ {0.01, 0.02}, the learned class equals the true class in at least **95%** of the 144 batches.
- **G2:** at q = 0, "no burst" is selected in at least **90%** of the 72 batches.
- **G3:** among the 96 nonzero roots whose Stage 1 class is correct, the Stage 2 flip is correct (flip = 0) in at least **95%**.

These are reported but have no decision role:
- q̂ bias and MAE by q;
- the pooled-study learner (all 216 batches of one study, mixed q);
- the Stage 2 log-likelihood ratios;
- the min-weight heuristic's flip, which is expected to be wrong (1).

## Outcome rule

- **PASS:** build the frozen V1.6 evaluation (it still needs separate sign-off).
- **FAIL:** STOP. Report which criterion failed and why. Do not change the learner or the thresholds to obtain a pass. Any redesign would be a separately pre-registered V1.6b.
