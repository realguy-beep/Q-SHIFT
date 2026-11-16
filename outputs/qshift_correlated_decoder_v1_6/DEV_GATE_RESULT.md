# V1.6 development gate: result

**Outcome: FAIL (G1). Per the pre-registration, V1.6 stops here.** No frozen V1.6 evaluation will be built from this design. The learner and the thresholds are not changed after seeing these results. The hidden burst remains sealed and unused.

The gate was run once with `dev_gate.py`, pre-registered at `304767972`, on already-exposed data only (known burst X8 X12 X15), and took 300 s. The full record is in `DEV_GATE.json`.

| Criterion | Required | Result | |
|---|---|---|---|
| G1: learned class correct at q ∈ {0.01, 0.02}, per 500-row batch | ≥ 95% | **76.4%** (110/144) | ✗ |
| G2: "no burst" at q = 0 | ≥ 90% | 98.6% (71/72) | ✔ |
| G3: logical effect correct from 500 labeled shots (given a correct class) | ≥ 95% | **100%** (75/75) | ✔ |

## Where G1 failed

- **q = 0.02: 72/72 correct.**
- **q = 0.01: 38/72 correct.**
  - In 22 batches the evidence fell below the threshold (Δ < 11.58), so the learner said "no burst".
  - 12 batches picked a wrong class: class 3 seven times, class 0 twice, and class 14.

  Mean q̂ at q=0.01 was 0.0069, biased low largely because those below-threshold batches return 0.
- **q = 0: one false positive** (V1.3 root 15, Δ = 11.9, just over the threshold).

## What the reported-only diagnostics show

- **Pooled data is decisive.** The pooled learner, run on all 36,000 calibration rows of one study (mixed q), picked the **correct class in all three studies** with Δ ≈ 1,590–1,750, about 140× the threshold. It gave q̂ ≈ 0.0098–0.0104, close to the pooled mixture's mean burst rate of 0.01.
- **The labeled stage is not the bottleneck.** Its log-likelihood ratios ranged from −120 to −614 in favour of the correct, logically trivial effect on every evaluated root. As expected, the min-weight heuristic would have chosen the wrong effect (flip = 1).

## Interpretation

The two-stage design works in principle. The logical bit is learned reliably from 500 labeled shots, and the signature is unambiguous with enough detector data. It fails only because **500 detector-only rows per root is too little to identify the signature at q = 0.01**. That was a design choice (per-root support learning), not a defect in the method.

## What a redesign would look like (V1.6b; needs its own pre-registration and approval)

- **Learn the support once per device** from a pooled calibration set (the support is a device property), and estimate only q̂ per root.
- **Pre-register a pooled-learning gate** on detector data the learner hasn't seen: subsamples of the already-exposed V1.2/V1.3/V1.5 *evaluation* detector arrays, which this gate did not use for Stage 1. It would report class accuracy as a function of pooled N.
- **Keep the hidden-burst safeguard unchanged.**

This document doesn't authorize V1.6b. It records the negative result and its cause.
