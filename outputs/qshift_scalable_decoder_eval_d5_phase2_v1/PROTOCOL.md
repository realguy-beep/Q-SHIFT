# Phase 2, d=5: frozen evaluation protocol

**Pre-registered.** This protocol is frozen in `FREEZE.json` and committed before any evaluation sample. The owner approved the plan and Step 0 on 2026-11-17, and authorized "Build and freeze". **Sampling is not yet authorized.** The single run needs a separate owner go-ahead on the freeze commit.

Sources:
- the plan: `../qshift_scalable_decoder_eval_d57_v1/PHASE2_D5_PLAN_DRAFT.md` (`6356d5b9c`);
- the candidate's prior: `../qshift_scalable_decoder_eval_d57_v1/PHASE2_D5_PRIOR.json` (Step 0, `ee0d6ef88`).

## Question

On fresh seeds at d=5 and p=0.003, does hypergraph BP+OSD with one static prior beat the strongest static matcher on the same correlated-burst noise family?

## Circuit and data

- **Circuit:** `model_v14`, rotated Z-memory, d=5, rounds 5, p = 0.003, scaled_v1 burst (X23 X31 X34), q ∈ {0, 0.01, 0.02}.
- **Allocation:** 24 independent roots per q, with one stim sampler call per root and 8,334 shots per root. That gives 200,016 shots per q and **600,048 in total**, in 72 calls.
- **Seeds:** `SEEDS.json`, namespace `qshift-d5-phase2-eval-2026-11-17`. They are screened against every prior inventory, including d57 Phase 1 and the screen, with their rehearsal seeds (1,038 values). Rehearsal seeds come from a separate namespace.

## Arms (all on identical detector rows)

| Arm | Definition | Role |
|---|---|---|
| Astar | correlated PyMatching, DEM at q_dec = 0.0025 (Phase 1 selection) | **comparator** |
| **L2s** | ldpc 2.4.1 BP+OSD: product-sum, **serial**, max_iter 50, OSD-CS order 10; DEM at static q_dec = **0.01** (Step 0) | **candidate** |
| L2o | as L2s, DEM at the true q | secondary (oracle prior) |
| L0s | as L2s, but parallel schedule (V3.2 settings) | secondary |
| BoffStatic | five-factor, true support, static prior 0.00125 (Phase 1) | secondary |
| A_nominal | PyMatching, burst-free DEM, correlations OFF | reference |

## Endpoints (`analyze.py`)

All endpoints use a root-paired bootstrap with 20,000 replicates. The resampling seeds are `p2d5:stats:nonzero` and `p2d5:stats:zero`, and quantiles are linear.

- **Co-primary:** Δ = LER(L2s) − LER(Astar), equal-weight over q = 0.01 and 0.02. It passes if the upper bound of the 95% CI is below 0.
- **Safety at q=0:** take the 95th percentile of LER(L2s) − LER(Astar). It passes if that value is ≤ 0, or below 0.05 × Astar's q=0 LER.
  - The "≤ 0" clause was added before the freeze, after the 1-root rehearsal. That rehearsal had zero comparator errors, which made the margin 0, so an exact tie would have failed.
- **Key secondary:** R = 1 − LER(L2s)/LER(Astar), equal-weight nonzero, with a bootstrap 95% CI. It is reported, not gated. If any replicate has zero comparator errors, the interval is reported as unbounded.
- **Other secondaries** (each with nonzero and q=0 estimates and CIs): L2o − Astar, L2s − L2o, L2s − L0s, L2s − BoffStatic, L2s − A_nominal, plus per-arm error totals.

## Decision

- **NO-GO_d5:** the co-primary CI lies entirely above 0, or the safety check fails.
- **GO_d5:** otherwise, if the co-primary passes.
- **INCONCLUSIVE:** in every other case.

## Execution controls

1. Run `python run_all.py eval work/run_v1 --expected-head <freeze commit> --workers 8`.
   - It requires a clean tree and HEAD equal to the freeze commit.
   - Each job re-verifies HEAD and every `FREEZE.json` file hash before sampling.
2. **Single attempt.**
   - Each job writes once and refuses to overwrite, and `RUN_STATUS.json` refuses a second launch.
   - There is no retry or seed substitution.
   - A failed or timed-out job (limit 3,600 s) makes the run `failed`, and it is reported as such.
3. **Budget:** the preflight projects 5,192 s of wall time (`PREFLIGHT.json`). The hard wall budget is 10,800 s. The run is monitored in the background.
4. **After the run:**
   - `analyze.py eval work/run_v1 results_v1` checks seeds, archive hashes and recorded counts;
   - `recount.py` recounts the totals independently and re-decodes root 0 at every q, requiring bit-identical predictions;
   - re-analysis into a second folder must be byte-identical.
5. **Stored and committed:** lightweight results (`results_v1/`: ANALYSIS.json, paired_roots.csv, RESULTS.md). Raw archives stay in git-ignored `work/run_v1/`.

## Rehearsals done before the freeze (not data)

- **Fake-sampler pipeline test:** 72 roots × 40 shots from a NumPy sampler over the DEM columns, with no stim sampler calls. It ran through `run_all`, `analyze` and `recount`, and all checks passed.
- **Real rehearsal:** 3 roots × 1,000 shots on rehearsal seeds. All checks passed, including the bit-identical re-decode. It provided the cost numbers for the preflight.

## Claim boundaries

- A GO is a d=5, p=0.003 result for one synthetic burst mechanism, in simulation only.
- The d=7 STOP (`SCREEN_RESULTS.md`) stands. A d=5 GO is not evidence of scaling to d=7.
- No mode-switching matcher exists at d=5.
- **Deviation from the approved design:** the candidate uses a static prior selected on development data (Step 0) instead of a per-root fitted q̂.
