# d=5 learned burst support, Phase C: frozen evaluation protocol

**Pre-registered.** This protocol is frozen in `C_FREEZE.json` and committed before any Phase C sample.

- **Authorized so far:** the owner said "Build Phase C freeze" on 2026-11-17.
- **Not yet authorized:**
  - **sampling;**
  - **opening H's seal.**

  Both need a separate owner go-ahead on the freeze commit. The run command requires `--open-hidden-seal`.

Sources:
- the approved plan (`C:\Users\LENOVO\.claude\plans\what-next-my-target-encapsulated-sutton.md`, Phase C);
- the learner (Phase A, `45b0fe28d`);
- the null-calibrated threshold τ = 1,561.2 (B2, `fd42c44c0`);
- the B2 PASS (`1031fbbc9`).

## Question

At d=5, p = 0.003, does serial BP+OSD with a burst support **learned from calibration data** beat correlated PyMatching that is given the **true** support? This is tested for the known burst and for a sealed hidden burst.

## Conditions

All at d=5, 5 rounds, `model_v14`, p = 0.003, q ∈ {0, 0.01, 0.02}.

| ID | True support | Notes |
|---|---|---|
| K | (23, 31, 34), scaled_v1 | the Phase 2 burst |
| H | sealed | drawn uniformly (OS entropy) from 2,291 weight-3 supports, excluding the four development classes. Commitment `HIDDEN_COMMITMENT_C.json`, sealed at `9bb5c6f4e`. Nobody has read the plaintext. |

In fake and rehearsal modes, H is replaced by the surrogate M0 (12, 34, 45). Those modes never open the seal.

## Learning (one calibration job per condition, at device level)

**Calibration data:** 3 Stim sampler calls, one per q, each with 4,000 detector-only rows (labels discarded unread) plus 500 labeled rows. Seeds come from `C_SEEDS.json` (`d5ls:C:cal:*`).

**Learner:** `FastParityLearner` over 1,003 classes, accepting a class if Δ ≥ τ = 1,561.2 (`NULL_THRESHOLD.json`).

**Flip:** `learn_flip` decides the logical effect. A pure class gets its flip directly. A mixed class is decided by L2 errors on the 1,500 labeled rows, ties going to min-weight.

**Learned support:** the representative of the selected class and flip. If no class is accepted, there is none, and the learned-support arms use the base model (see below).

This is a single learning draw per condition. Learning reliability is measured by the B2 gate, not by this evaluation's CI, and that is disclosed.

## Allocation

- Per (condition, q): 24 roots, each one sampler call of 8,334 shots, for 200,016 shots.
- **In total: 1,200,096 shots in 144 calls,** plus 6 calibration calls (27,000 shots).

## Arms (identical rows)

| Arm | Definition | Role |
|---|---|---|
| **L2L** | ldpc 2.4.1, product-sum, serial, max_iter 50, OSD-CS order 10. Undecomposed DEM with the **learned** support at static prior 0.01; base DEM if nothing was learned | **candidate** |
| L2s | as L2L, with the **true** support (oracle) | reference |
| **Astar** | correlated PyMatching, q_dec 0.0025, with the **true** support (the d=5 Phase 2 comparator, selected at Phase 2 for scaled_v1) | **comparator** |
| Astar_L | as Astar, with the learned support; correlated matching on the base DEM if nothing was learned | secondary |
| A_nominal | PyMatching, burst-free DEM, correlations OFF | reference |

The comparator is conservative: it gets the true support, which the candidate does not. For H, Astar's q_dec is transferred from scaled_v1 rather than re-selected. This is disclosed.

## Endpoints, per condition (`c_analyze.py`)

The bootstrap is root-paired, with 20,000 replicates and seeds `d5ls:C:stats:<C>:{nonzero,zero}`. Quantiles are linear.

- **Co-primary:** L2L − Astar, equal-weight over q = 0.01 and 0.02.
  - The 95% CI decides each condition.
  - The **97.5% CI** (Bonferroni, α = 0.05/2) decides the overall verdict.
- **Safety at q=0:** take the 95th percentile of L2L − Astar. It passes if that value is ≤ 0, or below 0.05 × Astar's q=0 LER.
- **Named secondary:** non-inferiority of L2L against the oracle L2s. It holds if the upper 95% CI of L2L − L2s at nonzero q is below 0.25 × LER(L2s).
- **Reported, not gated:**
  - R = 1 − LER(L2L)/LER(Astar), with a 95% CI;
  - L2L − Astar_L, L2s − Astar and L2L − A_nominal;
  - the learning outcome: selected class, Δ, q̂, flip, and whether it was correct, which is checked against the opened seal for H.

## Decisions

**Per condition:**
- **NO-GO:** the co-primary 95% CI lies entirely above 0, or the safety check fails.
- **GO:** otherwise, if the CI upper bound is below 0.
- **INCONCLUSIVE:** in every other case.

**Overall verdict:**
- **NOT_CONFIRMED:** any condition is NO-GO.
- **CONFIRMED:** otherwise, if both conditions pass the Bonferroni CI and the safety check.
- **PARTIAL:** otherwise, if one passes both.
- **INCONCLUSIVE:** otherwise.

## Execution controls

1. Run `python c_run_all.py eval work/c_eval_v1 --expected-head <freeze commit> --workers 8 --open-hidden-seal`.
   - It requires a clean tree, HEAD equal to the freeze commit, and the seal flag.
   - Each job re-verifies HEAD and every `C_FREEZE.json` hash.
   - The seal's plaintext is verified against the commitment before use.
2. **Order:** the 2 calibration jobs run first, then the 144 root jobs.
3. **Single attempt.**
   - Each job writes once, and `RUN_STATUS.json` refuses a second launch.
   - There is no retry or seed substitution.
   - A failure, or a job exceeding the 3,600 s timeout, makes the run `failed`.
4. **Budget:** the preflight (`C_PREFLIGHT.json`) projects 10,659 s, about 3.0 h, against a hard wall budget of 18,000 s. The rehearsal timed H with the surrogate.
5. **After the run:**
   - `c_analyze.py eval work/c_eval_v1 results_v1` checks seeds, archive hashes and recorded counts;
   - a second analysis must be byte-identical;
   - `c_recount.py eval work/c_eval_v1 results_v1/ANALYSIS.json --open-hidden-seal` recounts all totals and re-decodes root 0 of every (condition, q), requiring bit-identical predictions for all arms.
6. **Committed:** `results_v1/` (ANALYSIS.json, paired_roots.csv, RECOUNT.json, RUN_STATUS.json, learned/, RESULTS.md), plus H's revealed plaintext (`HIDDEN_REVEALED_C.json`), copied after the run so that anyone can check the commitment. Raw archives stay in git-ignored `work/`.

## Rehearsals before the freeze (not data)

- **Fake sampler:** 144 roots × 30 shots from a NumPy DEM sampler, with the surrogate used for H. It ran through `c_run_all`, the analysis (twice, byte-identical) and the recount, and every check passed.
- **Real rehearsal:** 6 roots × 1,000 shots plus 2 calibrations, on rehearsal seeds with the surrogate for H.
  - Every check passed, including the bit-identical re-decode.
  - The learner recovered (23, 31, 34) for K and (12, 34, 45) for the surrogate.
  - It also provided the preflight timings.

## Claim boundaries

- d=5 only, p = 0.003, weight-3 bursts, simulation only.
- One learning draw per condition. τ is calibrated with the true base noise model, which the learner assumes; base-model error on a real device is untested.
- A CONFIRMED verdict would remove the *burst-support oracle* caveat for these two bursts. It would not remove the base-model assumption.
- The d=7 STOP stands.
