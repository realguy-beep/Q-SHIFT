# d=5 learned burst support, Phase B2: null-calibrated gate protocol

**Pre-registered.** This protocol, `b2.py`, `B2_SEEDS.json` and `tests/test_b2.py` are committed before any B2 sample is drawn.

**Authorization:** "Approve B2" from the owner on 2026-11-17, covering `GATE_B2_PLAN_DRAFT.md` (`4b8515b4c`).

**Scope:** development evidence only. The Phase B result (STOP, `22b8a4b80`) stands, and its data are not reused.

## The only change from Phase B

The stage-1 acceptance threshold. Phase B used χ²₁(1 − 0.01/C) = 19.52. B2 uses τ, set by null calibration.

Everything else is unchanged from Phase A and Phase B (`learner_d5.py`, `contract.py`, `DEV_PROTOCOL.md`): the hypothesis space, the parity fit, stage 2, the bursts SC, CR, M0 and M1, the pool sizes, and gates G1–G3.

## Step 1: null calibration (`b2.py null dev`)

- **Data:** 500 burst-free pools, 12,000 shots each, from the base circuit at d=5, p = 0.003. That is 6,000,000 shots, with labels unread.
- **Statistic:** for each pool, T = max over the 1,003 classes of Δ.
- **Threshold:** τ = max over the 500 pools of T. Under exchangeability, a fresh burst-free pool satisfies P(T > τ) ≤ 1/501.
- **Viability:** if τ = 0 or τ ≥ 3,000, B2 stops before the gate.
  - The 3,000 bound is disclosed as informed by Phase B's minimum true-burst Δ of 7,833.
  - τ = 0 would accept every pool, because Δ = 0 already meets a threshold of 0.
- **Record:** `NULL_THRESHOLD.json` is written once. It holds all 500 pool records, with seed, T, the argmax class and q̂. It is **committed before the gate**, and `b2.py gate dev` refuses to run unless the file is tracked and unchanged.

## Step 2: B2 gate (`b2.py gate dev`, then `b2.py aggregate dev DEV_GATE_B2.json`)

- **Design:** identical to Phase B.
  - 4 bursts × 24 pools. Each pool takes 3 q × (4,000 detector-only + 500 labeled) shots from one sampler call per q.
  - 24 burst-free pools of 12,000 shots.
  - 312 sampler calls, 720,000 shots in total.
- **Gates:**
  - G1: each burst ≥ 23 of 24 class-correct;
  - G2: ≥ 22 of 24 burst-free pools report "no burst";
  - G3: flip correct in ≥ 95% of class-correct pools.
- **Decision:** PASS if all three gates hold; otherwise STOP.
- **Reported, not gated:**
  - curves at 3k and 6k, which use τ calibrated for 12k and are descriptive only;
  - q̂ error;
  - the minimum true-burst Δ;
  - false selections.

## Seeds

The seeds are in `B2_SEEDS.json`, namespace `qshift-d5-learned-support-b2-2026-11-17`: 500 null pools plus 312 gate keys, and 15 rehearsal keys. They are screened against 1,692 earlier values: every prior inventory, Phase B's development and rehearsal seeds, and seed 1.

## Rehearsal (before this commit; not data)

The rehearsal ran 2 null pools and 1 pool per burst plus 1 burst-free pool, all on rehearsal seeds.
- The pipeline ran end to end.
- The 2-pool τ was 187 and is meaningless. The single burst-free pool exceeded it, so the rehearsal decision was STOP. That shows the gate logic works, not anything about the learner.

## After PASS

Phase C needs its own freeze and owner OK, as approved in the plan. Opening the hidden-support seal needs explicit authorization.
