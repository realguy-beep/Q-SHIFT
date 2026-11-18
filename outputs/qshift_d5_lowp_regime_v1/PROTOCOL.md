# d=5 low-p regime, Stage E: frozen evaluation protocol

**Pre-registered.**
- **Frozen in:** `EVAL_FREEZE.json`, committed before any Stage E sample.
- **Authorized so far:** the owner said "Build Stage E freeze" on 2026-11-18.
- **Not yet authorized:** the single Stage E run, which needs a separate owner go-ahead on the freeze commit.

**Sources:**
- `PLAN_DRAFT.md` (`40aaa4955`);
- `STAGE_S_PROTOCOL.md` (`7fce3fa9f`);
- Stage S results `DEV_SELECTION.json` / `DEV_RESULTS.md` (`ef5cc2455`), with decision PROCEED.

## Question

In a burst-dominated regime (d=5, low p), is serial BP+OSD at least **95%** below the strongest static matcher? This is the owner's target.

## Conditions and arms

All conditions use d=5, 5 rounds, `model_v14`, the scaled_v1 burst (23, 31, 34) with **true support**, and q ∈ {0, 0.01, 0.02}.

| ID | p | Astar (comparator; Stage S selection) | L2s (candidate) prior |
|---|---|---|---|
| L10 | 0.001 | correlated PyMatching, q_dec 0.0025 | 0.001 |
| L15 | 0.0015 | correlated PyMatching, q_dec 0.0025 | 0.0025 |

Other arms:
- **L2o:** L2 with the true q as its prior (oracle).
- **A_nominal:** burst-free PyMatching with correlations off.

L2 means ldpc 2.4.1 product-sum, serial, max_iter 50, OSD-CS order 10, on the undecomposed DEM.

## Allocation (Stage S sizing rule: L2 expected to make ≥ 30 nonzero-q errors)

| | Roots per q | Shots per root | Shots per q | Shots |
|---|---|---|---|---|
| L10 | 24 | 31,250 | 750,000 | 2,250,000 |
| L15 | 24 | 8,929 | 214,296 | 642,888 |

**Total:** 2,892,888 shots in 144 jobs. Seeds are in `EVAL_SEEDS.json`: 148 keys screened against 3,273 prior values, including the Stage S seeds.

## Endpoints (`analyze.py`; robustness Step E analysis, unchanged except where noted)

The bootstrap is root-paired with 20,000 replicates and stats seeds from `EVAL_SEEDS.json`.

**Per condition:**
- **Co-primary:** L2s − Astar, equal-weight over q = 0.01 and 0.02. The 95% CI gives GO, NO-GO or INCONCLUSIVE. The Bonferroni CI (α = 0.05/2) is used for the overall verdict.
- **Safety at q=0:** take the 95th percentile of L2s − Astar. It passes if that value is ≤ 0, or below 0.05 × Astar's q=0 LER.
- **R:** R = 1 − LER(L2s)/LER(Astar), with a 95% CI.
- **Reported:** L2o − Astar, L2s − L2o and L2s − A_nominal.

**Overall:**
- NOT_CONFIRMED if any condition is NO-GO;
- CONFIRMED if both pass the Bonferroni CI and safety;
- PARTIAL if one does;
- INCONCLUSIVE otherwise.

**Target statement (new, pre-registered).** This is judged at **L10**. L15 is reported with the same labels.
- **TARGET_MET_WITH_MARGIN:** the lower 95% bound of R is ≥ 0.95.
- **TARGET_MET:** otherwise, if the R estimate is ≥ 0.95.
- **TARGET_NOT_MET:** otherwise. In that case the achieved R and its CI are reported.

## Execution

1. Run `python outputs/qshift_d5_lowp_regime_v1/run_all.py eval work/eval_v1 --expected-head <freeze commit> --workers 8`.
   - It needs a clean tree with HEAD equal to the freeze commit.
   - Each job re-verifies HEAD and every `EVAL_FREEZE.json` hash.
2. **Single attempt.**
   - Each job writes once, and `RUN_STATUS.json` refuses a second launch.
   - There is no retry or seed substitution.
   - A failure, or a job exceeding the 3,600 s timeout, makes the run `failed`.
3. **Budget:** `EVAL_PREFLIGHT.json` projects 12,256 s (3.4 h) wall time against an 18,000 s hard budget, with the longest job at 722 s. That projection is conservative: it uses the 1,000-shot rehearsal timings plus a 1.25 contention factor. Stage S's 200k-shot timings imply about 1.4 h.
4. **After the run:**
   - `analyze.py eval <run> results_v1` checks seeds, archive hashes and recorded counts;
   - a second analysis must be byte-identical;
   - `recount.py` recounts all totals and re-decodes root 0 of every (condition, q), requiring bit-identical predictions for all arms.
5. **Committed:** `results_v1/` (ANALYSIS.json, paired_roots.csv, RECOUNT.json, RUN_STATUS.json, RESULTS.md). Raw archives stay in git-ignored `work/`.

## Rehearsals before the freeze (not data)

- **Fake:** 144 × 30 shots from a NumPy DEM sampler, through `run_all`, the analysis (twice, byte-identical) and the recount. Every check passed.
- **Real:** 6 roots × 1,000 shots on rehearsal seeds. Every check passed, including the bit-identical re-decode. It also provided the preflight timings.

## Claim boundaries

- Simulation only: d=5, a single weight-3 burst family, q ≤ 0.02, p ∈ {0.001, 0.0015}.
- **Regime choice:** the low-p regime was chosen *because* the 95% target can be reached there. That choice was made before any frozen sample and is disclosed (`PLAN_DRAFT.md`). A result must be stated for this regime only, not as a general 95%.
- **Oracle assumptions:** true burst support and an exactly known base model. The mismatch diagnostic (`qshift_d5_model_mismatch_v1`) showed the current learner fails under a ±17% p mismatch.
- The d=7 STOP stands. The p = 0.003 results (about 60–65%) are unchanged.
