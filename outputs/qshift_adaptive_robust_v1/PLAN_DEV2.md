# Plan: development studies OG (off-grid screen) and E2E (end-to-end decode under mismatch)

**Status: PLAN DRAFT.**
- Nothing has been built or sampled.
- Both studies draw **new development samples**, so each needs owner approval: first "build", then "run".
- Neither is confirmatory. Each one, if it passes, justifies the next step on the roadmap.

**Basis:**
- H-E1 (`HE1_RESULTS.md`): a scalar p̂ repairs p-scale mismatch.
- H-E1b (`HE1B_RESULTS.md`): a joint (p, b) fit repairs Z-bias.

**Open questions from H-E1b that these studies answer:**
1. Does recovery survive when the true values lie off the fitting grid?
2. Is a model outside the family flagged and handled safely?
3. Do the *decoders* recover too, when the learner and decoders all use the estimated model?

## Shared elements

**Burst:** d=5, 5 rounds, the known burst `scaled_v1` (23, 31, 34).

**Seeds:**
- New namespaces: `qshift-adaptive-robust-v1:dev:offgrid` and `qshift-adaptive-robust-v1:dev:e2e`.
- Screened for collisions against every prior seed inventory: the chain used in `prepare_eval_seeds.py`, plus the low-p `EVAL_SEEDS.json` and the mismatch `SEEDS.json`.
- The seed file is committed before sampling.

**Estimators (fixed before sampling):**

| Arm | Method |
|---|---|
| N | Phase C unchanged (nominal p = 0.003, balanced) |
| B | H-E1b unchanged (grid snap) |
| **B2 (primary)** | H-E1b grid search, then continuous refinement: (a) p by the H-E1 1-D root on the rate curve at b̂; (b) b by golden-section search on the trimmed objective within the neighbouring grid interval; 2 alternations |

**Misspecification flag:** a pool is flagged when its trimmed fit objective exceeds the largest objective among the 192 existing in-family H-E1b pools. That threshold is computed and committed before sampling. A flagged pool is not learned: it falls back to "no burst" and the base DEM.

**Execution, for both studies:**
- write-once records, a single attempt, a clean tree and an expected-head check;
- analysis run twice, required to be byte-identical;
- a disclosure of every deviation.

## Study OG: off-grid and out-of-family screen

**Design:** 24 burst pools (4,000 detector rows + 500 labelled rows per q, q ∈ {0, 0.01, 0.02}) and 24 burst-free pools (12,000 rows) per condition. This is the Phase A recipe.

| ID | True model | Role | Why |
|---|---|---|---|
| OG1 | p 0.0027, balanced | in family, off grid | p between grid points |
| OG2 | p 0.0033, balanced | in family, off grid | as OG1 |
| OG3 | p 0.003, Z-bias 6 | in family, off grid | b between grid points 5 and 7 |
| OG4 | p 0.003, Z-bias 12 | in family, off grid | b between grid points 10 and 15 |
| OG5 | p 0.0027, Z-bias 6 | in family, off grid, combined | both parameters off grid |
| OG6 | p 0.003, X-bias 10 | **out of family** | bias type not in the model family |
| OG7 | gate p 0.003, measurement p 0.009 | **out of family** | the family assumes gate p = measurement p |

Before the freeze, a script will check that every in-family true value is at least 30% of a grid step away from its nearest grid point.

**Decision rules (arm B2 is primary; N and B are reported):**
- **OG1–OG5:**
  - **PASS** requires both: class correct in ≥ 20/24 burst pools, and false accepts in ≤ 1/24 burst-free pools.
  - The "flagged" count must also be ≤ 1/48.
- **OG6–OG7:**
  - **SAFE** if false accepts are ≤ 1/24.
  - Flag rate and class accuracy are reported, but learning is not required.
- **Overall:**
  - **OG_SUPPORTED:** all five in-family conditions PASS and both out-of-family conditions are SAFE.
  - **OG_PARTIAL:** at least three in-family conditions PASS and both out-of-family conditions are SAFE.
  - **OG_NOT_SUPPORTED:** anything else.

**Cost:**
- 7 × (24 × 13,500 + 24 × 12,000) ≈ **4.3 M** unlabelled-learning shots.
- Phase A ran 2.84 M shots plus 54 k decoded shots in 290 s, so this should take about 8–12 min on 8 workers.

## Study E2E: end-to-end decoding under mismatch

**Conditions:**
- Mlo (p 0.0025);
- Mhi (p 0.0035);
- Mz (Z-bias 10);
- CTRL (matched, p 0.003).

**Per root:**
- **Calibration:** its own calibration pool, using the Phase C recipe (4,000 detector rows + 500 labelled rows per q). Arms B2 and N each learn from it.
- **Evaluation:** separate shots at q ∈ {0, 0.01, 0.02}, drawn from separate seeds.

**Decoders.** Every decoder decodes the same evaluation rows.

| Arm | Base model | Burst support | Deployable? |
|---|---|---|---|
| **L2L_B2** | estimated (p̂, b̂) | learned (B2) | yes (candidate) |
| **Astar_B2** | estimated (p̂, b̂), correlated matching, q_dec 0.0025 | learned (B2) | yes (comparator; equal information) |
| L2L_N | nominal | learned by N (base DEM if none) | yes (the Phase A failure, "before") |
| Astar_N | nominal, true support | true | reference (the Phase A comparator) |
| L2s_true | true model | true | **oracle** |
| Astar_true | true model | true | **oracle** |
| A_nominal | nominal, no burst model | — | reference |

**Allocation:** 6 roots × 4,000 evaluation shots per q, so 24,000 per (condition, q) and **288,000 decoded shots** in total.
- The earlier Phase A counts at 6,000 shots per q (Mlo nonzero q: L2L_N 44 vs L2s 5) mean this size detects the repair with large margins.
- It cannot resolve a small residual gap to the oracle at Mz, where L2s made 0 errors in 12,000 shots. That limit is stated in advance.

**Endpoints, per condition, summed over nonzero q:**
1. **Repair:** errors of L2L_B2 − L2L_N, with paired discordance and a one-sided exact McNemar test.
2. **Gap to oracle:** L2L_B2 − L2s_true, with discordance and a 95% interval.
3. **Advantage at equal information:** L2L_B2 vs Astar_B2, as relative reduction R with a root-cluster bootstrap CI (6 roots: wide, descriptive only).
4. **Safety at q=0:** L2L_B2 − L2s_true and L2L_B2 − A_nominal at q=0.

**Decision rules:**
- **REPAIRED:** Mlo and Mz each show both of these:
  - endpoint 1 at p < 0.01;
  - endpoint 2 has a net excess within 25% of L2s_true's errors, or ≤ 3 errors when L2s_true has ≤ 12.
- **Mhi and CTRL** must show no degradation: endpoint 2 within the same margin.
- **Overall:**
  - **E2E_SUPPORTED:** all four conditions meet their rule.
  - **E2E_PARTIAL:** some do.
  - **E2E_NOT_SUPPORTED:** none do.
- **R in endpoint 3** is reported but does not gate anything at this size.

**Cost:**
- Three L2 arms at about 15–19 ms/shot each: 288 k × 0.055 s ≈ 15,800 CPU s.
- With 8 workers and a 1.25 contention factor, about **40 min**, plus about 5 min of calibration learning.
- A preflight from a 1-root rehearsal will be committed before the run.

## Order and approvals

| Step | Needs | Gate |
|---|---|---|
| 1 | "Build OG + E2E" | code, seeds, flag threshold, tests and a rehearsal (rehearsal seeds only), then a freeze commit |
| 2 | "Run OG" | single run of OG, about 10 min |
| 3 | "Run E2E" | single run of E2E, about 45 min. This can run right after OG, but **E2E uses arm B2 as frozen before OG**. OG results cannot change E2E's method |

**If OG fails in family:** E2E still runs as frozen, because the question it answers (decoders on the estimated model) is separate. The result is reported with OG's caveat attached.

## Claim boundary

If both studies pass, the claim is limited to: "on fresh development samples at d=5, with the known burst, the learned-support pipeline, re-based on detector-estimated (p, bias), learns correctly and decodes close to the oracle under ±10–17% p error and Z-bias 6–12; unmodelled noise types are flagged."

That is still not a frozen evaluation and not the broad benchmark.
