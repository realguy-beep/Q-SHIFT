# d=5 low-p regime, Stage E: frozen evaluation results

**Overall verdict: CONFIRMED.** Both conditions are GO under the Bonferroni CI, and both pass q=0 safety.

**Target verdict at L10: TARGET_NOT_MET.** R = **94.0%** with 95% CI [92.3%, 95.5%]. The estimate is 1 point below the pre-registered 95% target. The target lies inside the CI, but by the frozen rule it is not met.

## Run

| Item | Value |
|---|---|
| Protocol | `PROTOCOL.md` / `EVAL_FREEZE.json` at freeze commit `610033ebbbc4ae84677a23f20e23cca4d6a27016` |
| Authorization | owner said "Run Stage E", 2026-11-18 |
| Launch | `run_all.py eval work/eval_v1 --expected-head 610033ebb… --workers 8`, clean tree, single attempt |
| Wall time | 10:30:51Z → 11:44:05Z (73 min), well under the 3.4 h conservative preflight |
| Jobs | 144/144 with rc 0; longest job 398 s (3,600 s limit) |
| Shots | 2,892,888 (L10: 24 × 31,250 per q; L15: 24 × 8,929 per q) |

**Integrity checks:**
- `analyze.py` checked every seed, archive hash and recorded count.
- A second analysis (`work/reanalysis`) produced a byte-identical `ANALYSIS.json` and `paired_roots.csv`.
- `RECOUNT.json` shows `recount_matches_analysis: true`.
- Root 0 of every (condition, q) re-decoded bit-identically for all four arms.

## Errors (q = 0 / 0.01 / 0.02)

| Arm | L10 (750,000 shots per q) | L15 (214,296 shots per q) |
|---|---|---|
| Astar (correlated PyMatching, q_dec 0.0025) | 368 / 411 / 517 | 183 / 212 / 250 |
| A_nominal (burst-free PyMatching) | 35 / 999 / 1,869 | 33 / 407 / 792 |
| **L2s** (BP+OSD, static prior, true support) | **25 / 26 / 30** | **12 / 16 / 16** |
| L2o (oracle prior) | 25 / 26 / 27 | 12 / 18 / 18 |

## Endpoints

| | L10 (p = 0.001) | L15 (p = 0.0015) |
|---|---|---|
| L2s − Astar, nonzero q (95% CI) | −5.81e-4 [−6.27e-4, −5.35e-4] | −1.00e-3 [−1.09e-3, −9.15e-4] |
| Bonferroni CI (α = 0.025) | [−6.34e-4, −5.29e-4], passes | [−1.11e-3, −9.01e-4], passes |
| Decision | **GO** | **GO** |
| q=0 safety: 95th percentile of L2s − Astar | −4.13e-4, passes | −6.95e-4, passes |
| **R = 1 − LER(L2s)/LER(Astar)** | **94.0% [92.3, 95.5]** | **93.1% [90.7, 95.2]** |
| Target label | TARGET_NOT_MET | TARGET_NOT_MET (reported only) |
| L2s − L2o, nonzero q | +2.0e-6 [−2.0e-6, 6.7e-6] | −9.3e-6 [−2.1e-5, 0] |
| L2s − A_nominal at q=0 | −1.3e-5 [−2.9e-5, 2.7e-6] | −9.8e-5 [−1.3e-4, −6.5e-5] |

## Interpretation

1. **The burst is effectively decoded.** L2s makes 26 and 30 errors with the burst present at L10, against 25 errors at its own burst-free q=0 floor. The same holds at L15: 16 and 16 against 12. What remains is background failure.
2. **The background floor is what blocks 95%.** L2's q=0 floor is 25 errors per 750k shots (3.3e-5). Astar's nonzero-q LER is 6.2e-4. Their ratio caps R at about **94.6%**, even with zero burst cost.
   - Stage S had estimated the floor at 4 errors per 200k shots (2.0e-5). That small count put the cap at 96.9%.
   - The frozen sample shows the floor is about 1.7× higher than Stage S suggested. Astar's rate matched Stage S (4.9e-4 at q=0 in both).
   - The Stage S in-sample figure was optimistic noise. The Stage S protocol flagged this risk: "L10 rests on 8 L2 errors."
3. **The prior does not matter.** L2s matches L2o within about 1e-5 at both p.
4. **Caveat on the comparator.** Astar, as selected in Stage S on nonzero q, has a q=0 LER of 4.9e-4. That is about 10× A_nominal's 4.7e-5, because the correlated q_dec = 0.0025 prior is a cost when no burst is present. At nonzero q, Astar is still the stronger static matcher by a wide margin (6.2e-4 against 1.9e-3). R is defined against the pre-registered selection and is not re-selected here.

## Claim boundaries

- **What can be claimed:** "In a simulated d=5 burst-dominated regime (p = 0.001, weight-3 burst, q ≤ 0.02, true support, exactly known base model), serial BP+OSD reduces the logical error rate **94.0% [92.3, 95.5]** relative to the strongest static correlated matcher. The pre-registered 95% target was not met."
- **The regime was chosen because a 95% reduction is reachable there.** This is disclosed in `PLAN_DRAFT.md`. The result holds for this regime only.
- **Assumptions:** oracle support and a known base model. The mismatch diagnostic shows the current learner fails under a ±17% p mismatch.
- **Unchanged by this run:** the p = 0.003 results (about 60%) and the d=7 STOP.
- **Not tuned on these results:** no selection, prior or allocation was changed after sampling.

## Artifacts

- `ANALYSIS.json`, `paired_roots.csv` (sha256 `fcf5f208…`), `RECOUNT.json`, `RUN_STATUS.json`.
- Raw archives stay in git-ignored `work/eval_v1/`.
