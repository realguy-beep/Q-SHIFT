# d=5 learned burst support, Phase A: the learner (no sampling)

**Status:** Phase A is done. **Phase B (the development gate) needs a separate owner go-ahead.** No Stim sampler was called: every test uses NumPy draws from DEMs.

Plan: `C:\Users\LENOVO\.claude\plans\what-next-my-target-encapsulated-sutton.md`, approved by the owner on 2026-11-17. Its content is carried into this package's protocol files.

## What was built

- **`learner_d5.py`** is a thin wrapper over the V1.6 learner (`outputs/qshift_correlated_decoder_v1_6/learner.py`, which is not edited).
  - `FastParityLearner` computes the same base-DEM log-moments, class counts n_A(c), weighted least-squares fit and selection as `ParityLearner`, using matrix products in place of Python loops.
  - The threshold is χ²₁ at 1 − 0.01/C, the same rule as V1.6b applied to d=5's class count.
  - Stage 2, `learn_flip`, is a **declared deviation**, because the exact decoder is infeasible at d=5:
    - a class whose supports all share one logical effect gets that flip directly, with no labels used;
    - a mixed class is decoded with L2 BP+OSD at the static prior 0.01, once per flip's representative. Fewer errors on the labeled shots wins, and a tie goes to the min-weight flip.
- **`CLASSES_D5.json`** holds the full d=5 hypothesis space and its SHA-256.

## d=5 hypothesis space (CLASSES_D5.json)

| Quantity | d=3 (V1.6) | d=5 |
|---|---:|---:|
| Detectable supports of weight 1–3 | 119 | 2,621 (of 2,625; 4 are detector-invisible) |
| Signature classes C | 15 | **1,003** |
| Classes that mix both logical flips | 15 (all) | **86** |
| Parity test subsets | — | 2,920 |
| Stage-1 threshold | 11.58 | **19.52** |

**Known bursts:**

- **scaled_v1** (23, 31, 34) is in class 790, a singleton class with flip 0.
- **centre_row** (25, 27, 29) is in class 901: 3 supports, all flip 0, with representative (16, 18, 25).

Both classes are pure, so at d=5 the labeled stage is **not needed for either known burst**. This differs from d=3, where every class was ambiguous. A centre_row-learned DEM uses the representative (16, 18, 25). Its burst mechanisms have the same detectors and logical effect as the true support, which is the same identity V1.6 tested at d=3.

The plan expected 2,625 supports and left the class structure open. The numbers above are what the enumeration gives.

## Tests (`tests/test_learner_d5.py`; 9 pass in 116 s)

- **d=3 equivalence with V1.6:**
  - 119 supports and 15 classes;
  - threshold 11.58;
  - `FastParityLearner` matches `ParityLearner` on subsets, base_log (to 1e-12) and n (exactly);
  - identical selections on three synthetic datasets (known burst, no burst, another class).
- **d=5:**
  - the class record is deterministic (hash and counts);
  - base_log and n match the direct formula on 25 random subsets;
  - 12,000 synthetic shots at q=0.02 recover scaled_v1's class with q̂ within 0.006;
  - a pure class takes the label-free path;
  - the L2 stage-2 picks the correct flip for both effects of a mixed class (600 synthetic labeled shots each).

Synthetic DEM draws are not Stim samples. Phase B measures accuracy on real Stim development samples.

## Next: Phase B (needs an OK)

Phase B is the development gate from the plan:

- d=5, p=0.003, families scaled_v1 and centre_row, plus q=0 pools, on a new development seed namespace;
- G1 (class accuracy) ≥ 95%, G2 (q=0 "no burst" rate) ≥ 90%, G3 (flip accuracy) ≥ 95%;
- a learning curve at 3k/6k/12k/24k shots, and a check of L2 decoding with the learned vs the true support.

Phase B would be pre-registered (protocol and seeds committed) before any sample is drawn. A failed gate stops the study.
