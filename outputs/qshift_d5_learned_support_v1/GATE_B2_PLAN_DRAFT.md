# d=5 learned burst support, Phase B2: null-calibrated development gate (plan draft)

**Status: plan only.** Nothing here is authorized to sample until the owner approves it. Phase B (`DEV_RESULTS.md`, `22b8a4b80`) stays a STOP, and its data are not reused.

## Why

In Phase B the learner found every true burst, scoring Δ ≥ 7,833, but it accepted false bursts in 15 of 24 burst-free pools, with Δ up to 1,060. The χ²₁(1 − 0.01/C) threshold assumes independent parity statistics. At d=5 that assumption fails: the 2,920 statistics overlap. Phase B2 replaces the analytic threshold with one **calibrated by simulation from the known base model**. That model is the base circuit the learner already assumes, so no new knowledge is added. Nothing is taken from the Phase B gate data.

## Step 1: null calibration (sampling; needs OK)

- **Pools:** N₀ = 500 burst-free pools at d=5, p = 0.003, each 12,000 shots, sampled by Stim from the base circuit. These are fresh seeds in a dedicated namespace, labelled `null-calibration`.
- **Statistic:** for each pool, record T = max over the 1,003 classes of Δ, which is what `select` compares to the threshold.
- **Threshold τ:** the largest of the 500 null T values. For a fresh burst-free pool, P(T > τ) = 1/501 ≈ 0.2% (order-statistic exchangeability), which needs no distributional assumption.
- **Result:** τ is written to `NULL_THRESHOLD.json` and committed **before** the B2 gate samples. It is the only change to the learner. The class search, stage 2 and q̂ are unchanged from Phase A.
- **Pre-declared viability check:** if τ ≥ 3,000, the null tail is too close to Phase B's weakest true-burst Δ. B2 then stops before the gate, and the result is reported.
  - The 3,000 figure is set from Phase B's descriptive minimum of 7,833, with a margin of more than 2×. It is fixed here, before the null samples.
  - Disclosed: this one number is informed by Phase B burst pools.
- **Cost:** about 6 M shots at roughly 0.8 s per pool, around 1 minute on 8 workers.

## Step 2: B2 gate (sampling; same OK)

- **Design:** identical to Phase B (`DEV_PROTOCOL.md`). It uses the same four bursts (SC, CR, M0, M1), 24 pools each at 12,000 detector-only + 1,500 labeled shots, plus 24 burst-free pools. All seeds are **fresh**, in a new namespace screened against Phase B and null-calibration seeds.
- **Gates (unchanged):**
  - G1: each burst ≥ 23 of 24 class-correct;
  - G2: ≥ 22 of 24 burst-free pools report no burst;
  - G3: flip ≥ 95%.
- **Reported:** the learning curve at 3k, 6k and 12k. The τ calibration is only valid at 12k, so the 3k and 6k points use the same τ and are descriptive only.
- **Decision:** PASS allows Phase C planning, which needs a separate freeze and OK. STOP ends this line.
- **Cost:** 720,000 shots, about 10 minutes, as in Phase B.

## Execution controls (as in Phase B)

1. The rehearsal runs on rehearsal seeds and is not data.
2. The commit includes the protocol, seeds and code.
3. Null calibration runs and τ is committed.
4. The gate runs once, with write-once outputs.
5. `DEV_GATE_B2.json` and `DEV_RESULTS_B2.md` are committed.

## Phase C impact (if PASS)

Phase C follows the approved plan: conditions K and H, arms L2L, L2s, Astar and A_nominal. The only change is that the learner's acceptance threshold is τ. For the hidden support H, the base-model null calibration is the same, because τ depends only on the burst-free model.

## Honest boundaries

- τ is calibrated with the **true** base noise model. On a real device, base-model error would shift the null distribution. That is a limitation this simulation cannot test, and it is the same assumption V1.6b made with the base DEM.
- The calibration is specific to 12,000 calibration shots at p = 0.003. Other sizes or noise levels would need recalibration.
- A max-of-500 threshold controls false acceptance at about 0.2% per pool. It does not correct the overlap-induced miscalibration of Δ itself; a covariance-aware statistic would be a separate study.
