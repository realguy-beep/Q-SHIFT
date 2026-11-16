# V1.6b development gate: pre-registration

This file is committed **before** any V1.6b statistic is computed. The design is `DESIGN_PLAN_V1_6B_DRAFT.md` (approved by the owner). The learner is `learner.py`, unchanged since `304767972`.

**Prior exposure, disclosed:** V1.6's pooled learner (36,000 calibration rows per study) found the correct class in 3 of 3 studies. Those calibration archives are not used for signature learning here.

## Data (already exposed; known burst X8 X12 X15; no new sampling)

These are the evaluation archives of V1.2, V1.3 and V1.5 (`pilot_runs/attempt_001/evaluation/eval_q{qi}_r{rr}.npz`), with 96,000 rows per q per study. **They were never used for signature learning in V1.6.** Their labels were used in V1.6's flip stage, but only for V1.2/V1.3 and only the first 500 rows per root.

For each study and each q, all 96,000 rows are shuffled with a fixed seed (`20261116 + study_index * 10 + qi`) and split into contiguous blocks.

## Procedure

- **G1′:** 24 pooled subsamples per study (72 in total). Subsample k takes block k (4,000 rows) from each q, giving 12,000 rows. It runs `ParityLearner.select` with threshold χ²₁(1 − 0.01/15) = 11.58.
- **G3′:** for each G1′ subsample whose class is correct, run `learn_flip` at the subsample's device q̂. It uses 1,500 labeled rows: the first 500 rows of block (k + 12) mod 24 at each q, which are disjoint from the subsample's own detector rows.
- **G2′:** q=0-only pools of 12,000 rows, 8 disjoint per study (24 in total; that is all 96,000 q=0 rows). The plan said "24 per study", but a disjoint split only allows 8. This adjustment was made before computation.

## Gate criteria (all must hold → PASS)

| Criterion | Requirement |
|---|---|
| G1′ device class correct | ≥ 95% of 72 (at least 69) |
| G2′ "no burst" on q=0-only pools | ≥ 90% of 24 (at least 22) |
| G3′ flip correct, given a correct class | ≥ 95% |

**Reported only (no decision role):**
- class accuracy vs N_dev ∈ {1,500, 3,000, 6,000, 12,000, 24,000}, using as many disjoint equal-mixture subsamples as fit;
- device q̂;
- per-root q̂ bias and MAE using the true class on V1.2/V1.3/V1.5 per-root calibration batches (500 rows);
- cost.

**Outcome:**
- PASS: build the frozen V1.6b evaluation, which needs separate sign-off to run.
- FAIL: STOP and report, with no further redesign under this name.
