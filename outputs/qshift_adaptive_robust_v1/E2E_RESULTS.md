# E2E results: end-to-end decoding under base-model mismatch

**Verdict:** **E2E_SUPPORTED**, under the rule frozen in `DEV2_PROTOCOL.md` at `fe035cde7`.
- The learner and decoders were re-based on detector-estimated (p, bias), using arm B2.
- With that re-basing, BP+OSD with the learned support **repairs the mismatch failure under Mlo and Mz** and **matches the true-model oracle within 1 error in every condition**. It shows no degradation under Mhi or the matched control.

These are fresh development samples. They are not a confirmatory evaluation.

## How the run was done

| Item | Detail |
|---|---|
| Authorization | Owner, 2026-11-18 ("Run E2E") |
| Command | `python dev2.py run e2e eval --expected-head fe035cde7… --workers 8` |
| Checkout | **Detached at the freeze commit** `fe035cde7`. The OG results commit `70dbdb9bf` had moved the branch HEAD, and the frozen rule requires HEAD to equal the freeze commit. The tree was clean, and each job re-verified all 28 freeze hashes |
| Timing | 14:46:08Z → 15:42:54Z (**3,407 s**, against a rehearsal-based estimate of about 33 min). 24/24 write-once records |
| Data | 288,000 fresh evaluation shots plus 24 calibration pools |
| Analysis | `python dev2.py analyze e2e eval`, run twice and byte-identical. It was run again after returning to the branch, with an identical result. The analysis recounts every recorded error from the saved per-shot error bits |
| Per-shot cost | L2 arms ≈ 28–34 ms/shot; matching ≈ 0.01 ms/shot |

## Calibration

- **B2:** learned the support exactly in **24/24** roots, with 0 flagged.
- **Nominal learner (N):** learned it in 12/24 (CTRL 6/6, Mhi 6/6, Mlo **0/6**, Mz **0/6**). This reproduces the Phase A failure on fresh seeds.

## Errors

Each cell gives the errors at q = 0 / 0.01 / 0.02, over 24,000 shots per q.

| Arm | Mlo (p 0.0025) | Mhi (p 0.0035) | Mz (Z-bias 10) | CTRL (matched) |
|---|---|---|---|---|
| **L2L_B2** (estimated model, learned support) | **10 / 10 / 8** | **21 / 20 / 18** | **1 / 1 / 1** | **20 / 16 / 14** |
| L2L_N (nominal; the "before" arm) | 11 / 58 / 95 | 21 / 19 / 19 | 3 / 28 / 54 | 20 / 16 / 14 |
| L2s_true (oracle) | 10 / 10 / 7 | 21 / 18 / 20 | 2 / 1 / 1 | 20 / 16 / 14 |
| Astar_B2 (estimated model, learned support) | 28 / 31 / 20 | 37 / 56 / 59 | 19 / 19 / 26 | 36 / 45 / 45 |
| Astar_N (nominal model, true support) | 28 / 31 / 19 | 40 / 59 / 60 | **5 / 10 / 12** | 36 / 45 / 45 |
| Astar_true (oracle model) | 29 / 31 / 20 | 38 / 55 / 59 | 19 / 19 / 26 | 36 / 45 / 45 |
| A_nominal | 17 / 93 / 137 | 45 / 143 / 248 | 2 / 40 / 64 | 36 / 112 / 199 |

## Endpoints

These cover the nonzero q values, pooled.

| | Mlo | Mhi | Mz | CTRL |
|---|---|---|---|---|
| **1. Repair:** L2L_B2 vs L2L_N, discordant counts (B2 only / N only) | **2 / 137**, p = 1.4e-38 | 1 / 1 | **0 / 80**, p = 8.3e-25 | 0 / 0 |
| **2. Gap to oracle:** L2L_B2 vs L2s_true discordance, net (margin) | 1 / 0, **+1** (4.25) | 2 / 2, **0** (9.5) | 0 / 0, **0** (3) | 0 / 0, **0** (7.5) |
| **3. R vs Astar_B2** (6-root bootstrap 95% CI; descriptive) | 64.7% [53.4, 81.4] | 67.0% [61.1, 73.3] | 95.6% [88.9, 100] | 66.7% [51.9, 79.6] |
| **4. Safety at q = 0:** L2L_B2 vs L2s_true / vs A_nominal (discordant) | 0/0 ; 3/10 | 0/0 ; 4/28 | 0/1 ; 1/2 | 0/0 ; 5/21 |
| Verdict | **REPAIRED** | NO_DEGRADATION | **REPAIRED** | NO_DEGRADATION |

## Interpretation

1. **The documented failure is repaired end to end.**
   - Under Mlo and Mz, the Phase C pipeline learned nothing and decoded with a burst-free model: 153 and 82 nonzero-q errors.
   - With re-basing it learns the support in every root and drops to 18 and 2 errors. That is within 1 error of a decoder given the **true** model and the **true** support.
   - Under Mhi and the control, it is unchanged.
2. **The relative advantage over matching is the familiar about 65% at these noise levels.**
   - R ≈ 65–67% at p = 0.0025–0.0035 is consistent with Phase 2 and Phase C.
   - Model mismatch, once handled, does not erode it.
3. **Mz needs a comparator caveat.** With the correct biased model, correlated matching gets *worse*: Astar_true and Astar_B2 make 45 errors, while Astar_N with the nominal balanced model makes 22.
   - The equal-information comparator therefore flatters L2L at Mz. Against the **best matcher present** (Astar_N), the reduction is 1 − 2/22 ≈ **91%**, descriptively, with very small counts.
   - The 95.6% figure must not be quoted without this caveat.
   - Why biased priors hurt matching here is not investigated. It is plausibly decomposition of Y-type hyperedges, but that is not tested.
4. **Small counts.** Mz has 2 nonzero-q L2L errors, and the oracle has 2, so the gap-to-oracle test there has almost no resolution. That was stated before the run.

## What this establishes (development) and what it does not

- **Established:** at d=5, with the known burst, from 12,000 unlabeled plus 1,500 labeled calibration rows per root, the full pipeline (estimate (p, b) → learn the support → decode) recovers oracle-level BP+OSD decoding under ±17% p error and Z-bias 10, on fresh samples.
- **Not established:**
  - a frozen, pre-registered **evaluation**; this was development;
  - other burst supports;
  - drift;
  - out-of-family noise (OG shows it is flagged, not decoded well);
  - d = 3 or d = 7;
  - the broad benchmark;
  - any improvement toward the 95% broad target. R stays at about 65% at p ≈ 0.003, as before.
