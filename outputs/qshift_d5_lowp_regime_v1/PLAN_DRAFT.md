# Plan draft: d=5 burst-dominated regime screen for the 95% target

**Status:** draft for owner review. No sampling until the owner approves.

## Why

The owner's target is a 90–95% logical-error reduction against the strongest static matcher (correlated PyMatching, "Astar").

At d=5, p = 0.003 the best result is about 60–65% (Phase 2: 64.8%; Phase C: 59.8%). Decoder work cannot close that gap, because of what the decoder fails on **without any burst**.

| Regime | L2 errors with no burst (q=0) | Astar errors with burst (mean of q = 0.01, 0.02) | Cap = 1 − ratio | Achieved |
|---|---|---|---|---|
| p = 0.003 (Phase C K) | 6.7e-4 | 2.0e-3 | ≈ 67% | 59.8% |
| p = 0.002 (frozen P2) | 1.5e-4 | 8.0e-4 | ≈ 81% | 78.1% |
| p = 0.001 | **≈ 2e-5** (p³ extrapolation, not measured) | ≈ 7e-4 (V1.4 gate, matching) | **≈ 97%** (projection) | — |

At both measured points, L2 with the burst is almost at its own burst-free floor:
- p = 0.002: 1.75e-4 vs 1.5e-4;
- p = 0.003: 8.1e-4 vs 6.7e-4.

Burst handling is therefore close to complete, and the background floor sets the cap. Because the floor falls roughly as p³ at d=5 while Astar's burst damage falls more slowly, **lower p is the regime in which 95% can be reached at all.** This is the "bursts dominate the error budget" route that the V1.4 gate and REPORT §7.3 already name.

**Honesty point (the owner should decide knowingly).** Moving to p = 0.001 is a scope choice made because that is where the target can be reached. Any result must be stated as *"d=5, p = 0.001, weight-3 burst, simulation"*, not as a general 95%. Choosing the regime before any frozen sample is legitimate. Choosing it after seeing frozen results would not be. The p = 0.003 results stay as they are.

## Design

This is a new package, `outputs/qshift_d5_lowp_regime_v1/`. It is a copy of the robustness package `qshift_d5_robustness_v1/` with new conditions, because that package already handles per-condition p, Astar re-selection, L2 prior selection, sizing, the freeze, the analysis and the recount. Frozen files are not edited.

**Conditions:** d=5, 5 rounds, `model_v14`, scaled_v1 burst (23, 31, 34), q ∈ {0, 0.01, 0.02}:
- **L10:** p = 0.001 (gates and measurement);
- **L15:** p = 0.0015, the curve point between L10 and P2.

**Arms:**
- **L2s** (candidate): serial BP+OSD, true support, prior selected on dev data;
- **L2o**: true-q oracle prior;
- **Astar** (comparator): correlated PyMatching re-selected per condition by the Phase 1 rule;
- **A_nominal** (reference).

**Support:** these are oracle-support results, as in the robustness study. Phase A of the mismatch study showed the learner breaks under a ±17% p mismatch, and τ would also need recalibrating for every new p. Learned support at low p is therefore out of scope and named as a caveat.

### Stage S: development screen (needs an OK)

- **Data:** fresh screened seeds, 200,000 shots per (condition, q), for 1.2 M shots in total.
- **Selections,** in-sample using the Step D rules:
  - Astar's mode and q_dec over the 9 × 2 grid;
  - the L2 prior over {0.0005, 0.001, 0.0025, 0.005, 0.01}. The grid is extended downward because p is lower.
- **Reported:**
  - the floor ratio, i.e. L2's q=0 LER divided by Astar's nonzero LER;
  - the in-sample R;
  - L2 timing;
  - frozen sizing.
- **Pre-declared stop rule:** if the in-sample R at L10 is below 0.90, stop and report that 95% is not reachable even at p = 0.001 for this burst. Otherwise freeze Stage E with **both** conditions. Neither is dropped after the screen.
- **Cost:** L2 ran at about 10 ms/shot at p = 0.002 and should be faster at lower p. The rough estimate is 1.2 M × ~6 ms over 8 workers, about 15–25 min plus sampling. The preflight confirms it.

### Stage E: frozen evaluation (separate sign-off after Stage S)

- **Shots:** sized from Stage S so that L2s has at least about 30 errors at nonzero q at L10. Expect about 1 M shots per (condition, q), roughly 6 M shots and about 1.5–2 h. The hard budget is 5 h, with the allocation fixed in the freeze.
- **Endpoints, per condition:**
  - co-primary L2s − Astar, equal-weight over nonzero q, with α = 0.05/2 Bonferroni across L10 and L15;
  - q=0 safety;
  - R with its 95% CI.
- **Pre-registered target statement:**
  - **TARGET_MET** if R's point estimate is at least 0.95 at L10;
  - **TARGET_MET_WITH_MARGIN** if the lower 95% bound is at least 0.95;
  - otherwise the achieved R and its CI are reported.
- **Execution:** the existing machinery, unchanged in kind:
  - clean tree and HEAD gate, per-job freeze hashes;
  - write-once jobs, single attempt;
  - byte-identical re-analysis, recount, and root-0 re-decode.

## Boundaries

- Simulation only: d=5, a single weight-3 burst family, q ≤ 0.02, true (oracle) burst support, and an exactly known base model.
- From the mismatch Phase A: on hardware both the support and the base model would have to be learned, and the current learner does not survive model error.
- The d=7 STOP stands.

## Owner decisions needed

1. Approve this plan. I then build the package and tests and commit the Stage S protocol and seeds, with no sampling.
2. Separately, approve the Stage S sampling (about 1.2 M shots).
3. After Stage S, approve the Stage E freeze and run.

Mismatch Phase B (`qshift_d5_model_mismatch_v1`) stays on hold. Its result is effectively known from Phase A.
