# Phase 2, d=5 only: plan (DRAFT, not frozen)

**Status:** planning draft for owner review. It authorizes nothing. Step 0 (re-decoding saved development arrays) and Step 1 (fresh-seed evaluation sampling) each need explicit sign-off.

## Why d=5 only

- **The d=7 screen returned STOP_d7** (`SCREEN_RESULTS.md`): the best BP+OSD configuration (L2, serial) tied the strongest matcher (57 vs 55 nonzero errors). Under the pre-registered rule, d=7 leaves the evaluation. That negative result stays reported as it is.
- **d=5 has shown a consistent BP+OSD advantage on two independent development sets:**
  - Phase 1 (V3.2 / L0): 37% lower nonzero LER than Astar_5;
  - the screen (L2): 63% lower (80 vs 217 nonzero errors; 18 vs 155 discordant shots).
- Both of those used the DEM at the **true** q, and the screen selected L2 in-sample. Phase 2 is the fresh-seed test of whether the gain holds without those advantages.

## Fixed elements (unchanged from the approved design)

- **Circuit:** `model_v14`, rotated Z-memory, d=5, rounds 5, p = 0.003.
- **Bursts:** scaled_v1 burst (X23 X31 X34), q ∈ {0, 0.01, 0.02}.
- **Comparator:** Astar_5, selected in Phase 1: correlated PyMatching, q_dec = 0.0025. It is not re-selected.

## Step 0: fix the candidate's prior on saved development data (no new sampling)

Phase 1 and the screen gave BP+OSD the true-q DEM, which a real decoder doesn't know. To make the comparison like-for-like with the static matcher, the primary candidate gets one **static** DEM, chosen on development data only.

- **Data:** the saved d=5 screen arrays in `work/screen/`, 150,000 shots (50,000 per q). These are development data, already used for the screen, and never evaluation data.
- **Grid:** L2 (ldpc product-sum, serial, max_iter 50, OSD-CS 10) with the DEM built at q_dec ∈ {0, 0.0025, 0.005, 0.01, 0.02}, the same for every condition.
- **Rule (the V1.3 rule):** minimise equal-weight nonzero errors (q=0.01 + 0.02), subject to q=0 errors ≤ 1.10 × Astar_5's q=0 errors on the same rows. Ties go to the smaller q_dec. If no q_dec passes the q=0 guard, take the one with the fewest q=0 errors and flag it.
- **Cost:** about 750,000 L2 decodes at about 20 ms each, so roughly 40 min on 8 workers.
- **Output:** `PHASE2_D5_PRIOR.json`, committed before any Phase 2 seed is drawn.

## Step 1: frozen evaluation (fresh seeds)

### Allocation

- **Size:** N = 200,016 shots per q (24 roots × 8,334), so 600,048 shots in total. Each root is one sampler call per q.
- **Expected power:** Astar_5 is about 0.17%, so roughly 340 Astar errors per nonzero q. The pre-registered Phase 1 formula needs only 19,896 per q for a CI half-width of 25% of Astar's LER. The larger N tightens the relative-reduction CI to a few percentage points and makes the q=0 safety check meaningful.
- **Budget:** well inside the approved caps (6 M shots, 10 h). The projection is about 26 ms of decode per shot across all arms, so about 1 h of wall time on 8 workers. The preflight replaces this estimate before the freeze.

### Arms (all on identical detector rows)

| Arm | Definition | Role |
|---|---|---|
| Astar_5 | correlated PyMatching, q_dec = 0.0025 | comparator |
| **L2s** | L2 at the Step 0 static q_dec | **candidate** |
| L2o | L2 at the true q (oracle prior) | secondary: cost of not knowing q |
| L0s | V3.2 settings (parallel) at the Step 0 q_dec | secondary: continuity with V3.2 |
| BoffStatic_5 | five-factor, true support, static prior 0.00125 (Phase 1) | secondary |
| A_nominal | PyMatching, burst-free DEM, correlations OFF | reference |

The NumPy V3 arm is dropped. It was worse than the ldpc candidates and slower in the screen.

### Endpoints

All endpoints use a root-paired bootstrap over 24 roots with 20,000 replicates and a fixed bootstrap seed.

- **Co-primary:** Δ = LER(L2s) − LER(Astar_5), equal-weight over q = 0.01 and 0.02. Its 95% CI must lie entirely below 0.
- **Safety:** at q=0, the 95th percentile of LER(L2s) − LER(Astar_5) must be below +0.05 × Astar_5's q=0 LER.
- **Key secondary:** the relative reduction R = 1 − LER(L2s)/LER(Astar_5), equal-weight nonzero, with a bootstrap 95% CI. It is reported, not used as a gate. The 90% target is not applied here: d=5 is not a burst-dominated regime.
- **Other secondaries:**
  - the q=0 contrast, which is the background-hyperedge gain;
  - L2s vs L2o (the cost of the static prior), L2s vs L0s, L2s vs BoffStatic_5, and L2s vs A_nominal;
  - discordance counts and the per-arm cost.

### Decision

- **GO_d5:** the co-primary and the safety check both pass.
- **NO-GO_d5:** L2s is significantly worse than Astar_5, meaning the CI lies entirely above 0, or the safety check fails.
- **INCONCLUSIVE:** any other outcome.

### Controls (the same machinery as V1.5, V1.6b and Phase 1)

- Fresh seeds are screened against every prior inventory, including Phase 1, the screen and the rehearsal seeds.
- Hash freeze with LF pinning, a clean-tree gate, a single attempt, and no retry or seed substitution.
- A fake-sampler rehearsal plus one small real rehearsal on separate seeds.
- A watchdog, the frozen aggregator, an independent recount, and identical re-analysis.

## Claim boundaries (stated in advance)

- A GO establishes a d=5, p=0.003 result for this single synthetic burst mechanism only. It is simulation, not hardware.
- The d=7 STOP stays in the record. A d=5 GO is not evidence that the method scales to d=7.
- The comparator is the strongest static matcher available here. No mode-switching matcher (A2sw) exists at d=5, and that absence is stated.
- **Deviation from the approved design:** the design specified a per-root fitted q̂ for the candidate. This draft uses a static prior selected on development data, with the true-q oracle as a secondary. That is simpler, needs no calibration rows, and matches how the comparator was chosen.

## Owner decisions

1. **Approve the plan** as drafted (static prior; N = 200,016 per q), or ask for changes.
2. Then a separate go-ahead for **Step 0** (re-decoding saved development arrays, about 40 min).
3. Then, after the freeze, a separate go-ahead for **Step 1** (600,048 fresh shots, about 1 h).
