# Correlated decoder V1.6: learned burst support (DRAFT, not frozen)

**Status:** planning draft for owner review. No V1.6 code, seeds, freeze or sampling yet. Nothing here authorizes execution.

## Why V1.6

V1.5 (GO, TARGET_MET) showed that the exact DEM decoder **Bexact** cuts nonzero LER by 61.3% vs the strongest static matcher and by 26.6% vs the best V1.3 decoder. Every five-factor and exact arm so far, however, was **given** the burst's exact detector signatures and logical effect (oracle support). V1.6 asks:

**Does the advantage survive when the burst's signature, rate and logical effect are learned from calibration data?**

## Planning fact: the logical effect is not identifiable from detectors

A sampler-free check enumerated X-bursts on every 1–3 data-qubit subset at d=3 (129 subsets):
- 10 subsets are invisible to the detectors.
- The other **119 collapse to just 15 distinct per-round detector signatures**.
- **All 15 signatures are shared by supports with opposite logical effects,** because supports differing by a logical operator produce identical syndromes.

The true burst X8 X12 X15 (flip 0) shares its signature with X1 X12, X3 X12 and X5 X10 (flip 1), among others. X1 X8 X15 is a logical-X column.

**Consequences:**
- A detector-only learner can estimate *which signature* and *at what rate*, but never the logical effect.
- A "lowest-weight support" rule picks weight-2 X1 X12, which is the wrong logical effect for this burst.

V1.6 therefore needs **one bit of label information per learned signature**. Labeled calibration is realistic for memory experiments, because the logical state is prepared and known. It must be kept strictly separate from evaluation.

## Learner (two stages, both prospective)

1. **Signature and rate, from detector-only calibration data.**
   - The hypotheses are {no burst} ∪ the 15 signature classes (a physically grounded hypothesis space, enumerated from the circuit).
   - Each candidate is scored by the **exact marginal log-likelihood of the calibration syndromes**, using `ExactLogicalDecoder.joint` (V1.4B). For candidate c with rate q, the score is log P(s | base DEM + c at q).
   - q is fitted per candidate by a 1-D likelihood search over q ∈ [0, 0.02]. The best (c, q) wins, and "no burst" is retained unless the gain clears a likelihood-ratio threshold fixed in advance.
   - Cost: 16 candidates × q grid × N shots × about 7 ms. A cheap parity-deficit pre-screen narrows this to the top 3 before the exact likelihood is run.
2. **Logical effect, from labeled calibration shots.** For the chosen signature, pick flip ∈ {0, 1} by the exact **joint** likelihood P(s, ℓ) of a separate labeled partition. That is a one-bit likelihood-ratio decision, made before any evaluation.

The decoder is **Blearn**: the exact DEM decoder with the learned mechanism added, at per-root q̂ (from the learned signature's cofire rate, as in V1.1, refit to the learned signature).

## Development stage (no new sampling)

Use only already-exposed arrays:
- **Signature learning:** detector-only calibration archives from V1.2, V1.3 and V1.5 (3 × 72 × 500 = 108,000 rows).
- **Flip learning:** labeled shots from the V1.2/V1.3 evaluation arrays.

Report signature-recovery accuracy, q̂ bias, and flip-decision correctness as functions of calibration size, plus learner cost.

**Pre-registered development gate** (to be written before the development statistics are computed):
- the learned signature is correct in at least 95% of per-root calibration batches at q ≥ 0.01;
- the flip decision is correct with at most N_label labeled shots, where N_label is fixed in advance;
- "no burst" is chosen at q=0 in at least 90% of batches.

If the gate fails: STOP and report. Do not tune toward a pass.

**Blindness safeguard:** the developer knows the true burst. To keep the learner honest, V1.6 adds a **second, hidden burst condition**. Its support is drawn by a seeded random choice among the 119 detectable supports and committed as a hash before learner development. The plaintext is revealed only inside the frozen run. Development uses only the known burst.

## Frozen V1.6 evaluation (separate sign-off)

**Arms:**

| Arm | Definition |
|---|---|
| Astar | V1.3 static correlated matching, q=0.00375 |
| BoffStatic | V1.3 cost-consistent five-factor, oracle support, q=0.01125 |
| Bexact | V1.5 exact decoder, **oracle** support, per-root q̂ |
| **Blearn** | Exact decoder with a **learned** signature, rate and logical effect (candidate) |
| Blearn_minweight | Learned signature, with the logical effect from the lowest-weight support (detector-only; shows the ambiguity's cost) |

**Conditions:**
- the known burst at q ∈ {0, 0.01, 0.02}, which is V1.5-comparable;
- the hidden burst at q ∈ {0, 0.01, 0.02}.

**Partitions per root:**
- 500 detector-only calibration shots, used for signature, rate and q̂;
- L labeled calibration shots, used for the flip bit only;
- 4,000 paired evaluation shots.

**Co-primary** (intersection-union; per burst condition, equal-weight nonzero):
1. Blearn − Astar (the advantage survives without oracle knowledge);
2. Blearn − BoffStatic (it beats the best V1.3 decoder, which itself has oracle support).

**Key secondary:** Blearn − Bexact, the oracle gap. A non-inferiority margin is to be fixed before freezing, for example 0.05 pp.

**Target endpoint:** the relative reduction of Blearn vs Astar, with a 95% lower bound of at least 0.40 (stated in advance, not optimized). Safety at q=0 is as in V1.5.

**Allocation:** 2 burst conditions × 3 q × 24 roots × (500 + L + 4,000) shots. About 650,000 new shots if L = 500. Runtime is about 2 × the V1.5 exact-arm time plus the learner. The preflight sets the cap.

## Engineering

The V1.5 machinery carries over: contract, run_pipeline, rehearsal, frozen recount, watchdog, an LF freeze and a single attempt. New pieces:
- a tested signature-class enumerator, checking that the 119 → 15 collapse is reproducible;
- learner unit tests on synthetic DEMs with known answers;
- a hidden-burst commitment, where only the SHA-256 of (support, seed) is committed before development.

## Decisions for the owner

1. **Labeled calibration:** may V1.6 use a separate labeled calibration partition (known logical preparation) to learn the one logical bit per signature? Without it, learned support can't be correct in general, and that is itself a result Blearn_minweight would show.
2. **Hidden second burst:** add the blind second burst condition? It roughly doubles the sampling, but it guards against a learner that implicitly knows the answer.
3. **Thresholds and size:** the development-gate thresholds, the target lower bound of 0.40 vs Astar, and roughly 650,000 new shots.
