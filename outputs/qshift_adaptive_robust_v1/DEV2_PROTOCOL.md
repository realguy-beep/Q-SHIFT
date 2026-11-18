# OG + E2E development studies: frozen protocol

**Pre-registered.**
- **Frozen in:** `DEV2_FREEZE.json`, committed before any study sample was drawn.
- **Authorized so far:** the owner approved the build on 2026-11-18 ("Approve, build it").
- **Not yet authorized:** the two runs need separate go-aheads ("Run OG", "Run E2E") on the freeze commit.

**Source:** `PLAN_DEV2.md` (`b6b732eaf`). Everything there applies except the deviations listed below.

**Status of the evidence:** development only, so not confirmatory.

## Pre-freeze deviations from the plan

All of these were found by build checks or rehearsals, on rehearsal seeds only, before any study sample.

1. **OG2's p changed from 0.0033 to 0.00334.** The build check found 0.0033 only 0.12 grid steps from a grid point, against the ≥ 0.3 required. 0.00334 is about 0.5 steps off.
2. **The off-grid check is per condition.**
   - OG3 and OG4 keep p = 0.003, which is a grid point, by design: they test an off-grid **bias**.
   - The check is applied to the parameter(s) each condition is designed to put off grid. That is p for OG1 and OG2, b for OG3 and OG4, and both for OG5 (`dev2_config.OFF_GRID`).
3. **B2's p step changed.** It now uses **golden-section minimisation of the same trimmed objective** over log p within ±3 grid steps of the grid fit, instead of the H-E1 1-D root.
   - **Why:** in rehearsal the root optimised a different criterion. It raised the fit objective (72 → 81 on the Mz rehearsal pool) and biased p̂ 3–5% high in burst pools.
   - **Why ±3 steps, not ±1:** p and b trade off along a ridge. With ±1 step, the synthetic case (0.0027, 6) could not reach the true p.
   - **Result after the change:** in rehearsal the objective falls below the grid fit (Mz 72 → 66; OG3 113 → 84), and p̂ is within about 1%.
4. **Test tolerance changed from 2% to 3% for p̂ on synthetic data.** It was justified by a direct check, which the test now also asserts. In 4 seeds the estimate's objective was below the truth's, so the residual p error is sampling noise along the ridge.
5. **Runtime estimates corrected from rehearsal timings:**
   - OG: about 33 s per pool, so 336 pools take about **30 min** on 8 workers, against the plan's 10 min.
   - E2E: about 520 s per full root, so 24 roots take about **33 min**, against the plan's 45 min.

## Fixed method

- **Arms:**
  - **N:** Phase C unchanged.
  - **B:** H-E1b grid fit.
  - **B2 (primary):** grid fit, then 2 alternations of p-golden (±3 p steps) and b-golden (neighbouring b interval), then a final p-golden. τ is 1,561.218 throughout.
- **Misspecification flag:**
  - A pool is flagged when its B2 objective exceeds **118.432**. That is the largest H-E1b grid objective over the 192 in-family development pools (`FLAG_THRESHOLD.json`).
  - A flagged pool falls back to "no burst". In E2E it also falls back to the nominal base model.
  - The threshold comes from grid-fit objectives, while B2 objectives are typically lower, so the flag is relatively permissive. This is disclosed.
- **Decoders:** the static settings are Phase C's (L2 prior 0.01; Astar q_dec 0.0025 with correlations on).
- **Seeds:** `DEV2_SEEDS.json` holds 816 study keys and 10 rehearsal keys. They are screened against 3,428 prior values, covering every inventory used by the low-p screening chain plus the low-p `EVAL_SEEDS.json`.

## Conditions, allocations, endpoints and decision rules

As in `PLAN_DEV2.md`, with deviation 1 applied.
- **OG:** 7 conditions, each with 24 burst pools and 24 burst-free pools.
- **E2E:** 4 conditions × 6 roots × 4,000 evaluation shots per q. That is 288,000 decoded evaluation shots plus 24 calibration pools.

Implementation:
- `dev2.analyze_og` and `dev2.analyze_e2e`;
- exact one-sided McNemar test;
- root-cluster bootstrap with 20,000 replicates, seed 20261120.

## Execution

From the package directory:

```
python dev2.py run og eval --expected-head <freeze commit> --workers 8
python dev2.py analyze og eval results/dev2      # twice; byte-identical
python dev2.py run e2e eval --expected-head <freeze commit> --workers 8
python dev2.py analyze e2e eval results/dev2     # twice; byte-identical
```

**Safeguards:**
- A run requires a clean tree with HEAD equal to the freeze commit. Each job re-verifies HEAD and every `DEV2_FREEZE.json` hash.
- Records are write-once, and there is a single attempt: `RUN_STATUS.json` refuses a relaunch.
- E2E's analysis recounts every recorded error from the saved error bits.
- E2E uses the B2 method as frozen here. OG results cannot change it.

## Rehearsals (rehearsal seeds; not data)

Rehearsal used OG3 burst 00, OG6 burst-free 00, and E2E Mz root 0 with 200 evaluation shots per q.
- The pipeline ran end to end.
- Both analyses were byte-identical across two runs.
- The OG6 (X-bias) pool was flagged (objective 2,046).
- The Mz calibration pool was learned correctly under B2.

The rehearsal "verdicts" are meaningless at that size and are not reported as results.
