# d=5 robustness, Step E: frozen evaluation protocol

**Pre-registered.** This protocol is frozen in `EVAL_FREEZE.json` and committed before any Step E sample. The owner authorized "Build and freeze" on 2026-11-17. **Sampling is not yet authorized.** The single run needs a separate owner go-ahead on the freeze commit.

Sources: the plan (`DESIGN_PLAN_DRAFT.md`, `2b5d11646`) and the Step D selections (`DEV_SELECTION.json`, `f9bbb77c0`).

## Question

Does serial hypergraph BP+OSD with a static prior beat the re-selected strongest static matcher at d=5 under three single-factor changes from the d=5 Phase 2 setup?

## Conditions and selections (fixed; `eval_contract.py`, tested against `DEV_SELECTION.json`)

| ID | Burst family | Base p | Astar_C | L2s prior |
|---|---|---:|---|---:|
| F2 | centre_row | 0.003 | correlated PyMatching, q_dec 0.0175 | 0.01 |
| P2 | scaled_v1 | 0.002 | correlated PyMatching, q_dec 0.0025 | 0.0025 |
| P4 | scaled_v1 | 0.004 | correlated PyMatching, q_dec 0.0025 | 0.005 |

All conditions use d=5, 5 rounds, `model_v14` with gate_p = measurement_p = p, and q ∈ {0, 0.01, 0.02}.

## Allocation

- Per (condition, q): 24 independent roots, one stim sampler call each, 8,334 shots per root. That gives 200,016 shots per (condition, q).
- **In total: 1,800,144 shots in 216 calls.**
- Seeds come from `EVAL_SEEDS.json`, namespace `qshift-d5-robustness-eval-2026-11-17`. They are screened against 1,134 earlier values, including all of Step D's seeds and rehearsal seeds.

## Arms (identical rows within a condition)

| Arm | Definition | Role |
|---|---|---|
| Astar | Astar_C above | comparator |
| **L2s** | ldpc 2.4.1: product-sum, **serial**, max_iter 50, OSD-CS order 10; undecomposed DEM at the static prior above | **candidate** |
| L2o | as L2s, with the DEM at the true q | secondary |
| A_nominal | PyMatching, burst-free DEM, correlations OFF | reference |

## Endpoints, per condition (`analyze.py`)

The bootstrap is root-paired, with 20,000 replicates and per-condition seeds `d5rob:stats:<C>:{nonzero,zero}`. Quantiles are linear.

- **Co-primary:** L2s − Astar, equal-weight over q = 0.01 and 0.02.
  - The 95% CI is used for the per-condition decision.
  - The **98.33% CI** (Bonferroni, α = 0.05/3) is used for the overall verdict.
- **Safety at q=0:** take the 95th percentile of L2s − Astar. It passes if that value is ≤ 0, or below 0.05 × Astar's q=0 LER.
- **Reported, not gated:**
  - R = 1 − LER(L2s)/LER(Astar), with a 95% CI;
  - q=0 contrasts;
  - L2o − Astar, L2s − L2o and L2s − A_nominal;
  - per-arm totals.

## Decisions

**Per condition:**
- **NO-GO:** the 95% co-primary CI lies entirely above 0, or the safety check fails.
- **GO:** otherwise, if the 95% CI upper bound is below 0.
- **INCONCLUSIVE:** in every other case.

**Overall verdict:**
- **NOT_ROBUST:** any condition is NO-GO.
- **ROBUST:** otherwise, if every condition passes the Bonferroni CI and the safety check.
- **PARTIAL:** otherwise, if at least one condition passes both.
- **INCONCLUSIVE:** otherwise.

The plan did not name this final INCONCLUSIVE case. It was added before the freeze.

## Execution controls

1. Run `python run_all.py eval work/eval_run_v1 --expected-head <freeze commit> --workers 8`.
   - It requires a clean tree and HEAD equal to the freeze commit.
   - Each job re-verifies HEAD and every `EVAL_FREEZE.json` hash before sampling.
2. **Single attempt.**
   - Each job writes once, and `RUN_STATUS.json` refuses a second launch.
   - There is no retry or seed substitution.
   - A failed job, or one that hits the 3,600 s timeout, makes the run `failed`.
3. **Budget:** the preflight (`EVAL_PREFLIGHT.json`) projects 13,403 s. That is conservative, because the rehearsal timings were already taken under 8-way contention. The hard wall budget is 18,000 s.
4. **After the run:**
   - `analyze.py eval work/eval_run_v1 results_v1` checks seeds, archive hashes and recorded counts;
   - re-analysis into a second folder must be byte-identical;
   - `recount.py` recounts all totals independently and re-decodes root 0 of every (condition, q), requiring bit-identical predictions for all arms.
5. **Committed:** `results_v1/` (ANALYSIS.json, paired_roots.csv, RECOUNT.json, RUN_STATUS.json, RESULTS.md). Raw archives stay in git-ignored `work/`.

## Rehearsals done before the freeze (not data)

- **Fake-sampler pipeline:** 216 jobs × 30 shots from a NumPy DEM sampler, with no stim sampler call. It ran through `run_all`, `analyze` and `recount`, and every check passed.
- **Real rehearsal:** 9 roots × 1,000 shots on rehearsal seeds. Every check passed, including the bit-identical re-decode of all arms. It provided the costs for the preflight.

## Claim boundaries

- d=5 only, simulation only, and one burst weight (3). Each condition changes one factor from Phase 2.
- ROBUST would mean the gain holds across these three changes, not across all noise.
- The d=7 STOP stands.
- Each condition's prior and comparator were selected in-sample on Step D development shots. Evaluation uses fresh seeds.
