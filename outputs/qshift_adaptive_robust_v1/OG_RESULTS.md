# OG results: off-grid and out-of-family screen of the bias-aware learner

**Verdict: OG_SUPPORTED**, under the rule frozen in `DEV2_PROTOCOL.md` at `fe035cde7`.
- All five in-family conditions with off-grid values PASS under arm B2. In every one of them, 24/24 burst pools were learned exactly and 0/24 burst-free pools were falsely accepted.
- Both out-of-family conditions are SAFE: every pool was flagged and fell back to the base model.

These are fresh development samples, so the result is not confirmatory.

## How the run was done

| Item | Detail |
|---|---|
| Authorization | Owner, 2026-11-18 ("Run OG") |
| Command | `python dev2.py run og eval --expected-head fe035cde7… --workers 8` |
| Commit and tree | HEAD equal to the freeze commit, clean tree. Each job re-verified all 28 freeze hashes |
| Timing | Started 14:35:34Z, finished 14:41:50Z: **376 s** for 336/336 write-once records. The 30 min estimate was too high, because rehearsal timings included per-worker start-up |
| Samples | 4.3 M fresh development shots from `DEV2_SEEDS.json` |
| Analysis | `python dev2.py analyze og eval`, run twice; `results/dev2/OG.json` byte-identical |

## Results

Counts are out of 24 burst pools (class correct) or 24 burst-free pools (false accepts). "Flagged" is out of all 48 pools.

| ID | True model | N: class / false accepts | B (grid): class / false accepts | **B2: class / learned / false accepts / flagged** | B2 p̂ (mean ± SD) | B2 b̂ (mean ± SD) | Largest B2 objective (flag threshold 118.4) | Verdict |
|---|---|---|---|---|---|---|---|---|
| OG1 | p 0.0027 | 0 / 0 | 24 / 0 | **24 / 24 / 0 / 0** | 0.00271 ± 0.00003 | 1.03 ± 0.04 | 91.2 | PASS |
| OG2 | p 0.00334 | 24 / **24** | 24 / 0 | **24 / 24 / 0 / 0** | 0.00336 ± 0.00002 | 1.03 ± 0.04 | 98.9 | PASS |
| OG3 | Z-bias 6 | 0 / 0 | 24 / **5** | **24 / 24 / 0 / 0** | 0.00300 ± 0.00003 | 5.98 ± 0.31 | 94.8 | PASS |
| OG4 | Z-bias 12 | 0 / 0 | 24 / **6** | **24 / 24 / 0 / 0** | 0.00300 ± 0.00004 | 11.94 ± 0.66 | 103.7 | PASS |
| OG5 | p 0.0027, Z-bias 6 | 0 / 0 | 24 / **4** | **24 / 24 / 0 / 0** | 0.00271 ± 0.00004 | 6.05 ± 0.32 | 108.6 | PASS |
| OG6 | X-bias 10 (out of family) | 24 / **24** | 24 / **24** | 0 / 0 / **0** / **48** | 0.00320 | 1.00 | 3,310 | SAFE |
| OG7 | measurement p 3× gate p (out of family) | 22 / **24** | 24 / **24** | 0 / 0 / **0** / **48** | 0.00402 | 1.00 | 433 | SAFE |

## Interpretation

1. **Continuous (p, b) refinement is required, and it works.**
   - Snapping to the grid (B) learned the burst everywhere in family, but produced **4–6 false accepts per condition** when the bias lay off the grid.
   - The residual model error looks like a burst, which is the Phase C failure mode in miniature.
   - With continuous refinement (B2), every in-family condition has 0 false accepts. The estimates recover p to about 1% and b to about 5% (e.g. 5.98 ± 0.31 for a true value of 6).
2. **Out-of-family noise is detected rather than mis-learned.**
   - For X-bias and measurement-heavy noise, the nominal and grid learners falsely accepted a burst in **every** burst-free pool.
   - B2 flagged all 96 out-of-family pools, with objectives 433–3,310 against a threshold of 118. They fell back to "no burst".
   - **The cost:** those conditions get no burst modelling at all; there are 0/24 learned bursts. Safe fallback is not adaptation. Extending the model family (X-bias, separate measurement p) is the way to recover the gain there.
3. **Flag margin.** The largest in-family B2 objective was 108.6, which is 92% of the threshold.
   - The margin is real but modest, and none of the 240 in-family pools was flagged.
   - The threshold scales with the number of rows (12,000 here). A deployed version must recalibrate it for other pool sizes.

## What this establishes (development) and what it does not

- **Established:** at d=5, with the known burst and fresh samples, the B2 learner works within its model family `{balanced, z_biased} × p`. It learns correctly and makes no false accepts at off-grid values, including both parameters off grid at once. Two out-of-family noise types were flagged.
- **Not established:**
  - decoding performance; that is study E2E, frozen with this B2 method;
  - other burst supports;
  - drift;
  - other out-of-family types (crosstalk, leakage, non-uniform bias);
  - pool sizes other than 12,000 rows;
  - a frozen evaluation.

## Next

**E2E (frozen at the same commit).** It decodes under Mlo, Mhi and Mz with B2-estimated models, against nominal and oracle arms. It needs the owner's "Run E2E". Rehearsal timings suggest about 33 min, though OG ran about 5× faster than its estimate.
