# d=5 robustness, Step D: development selection and sizing (protocol)

**Committed before any Step D sample.** The owner authorized this step on 2026-11-17 ("Approve, run Step D") in response to `DESIGN_PLAN_DRAFT.md` (`2b5d11646`). Step D shots are **development data**. They are never reused for evaluation.

## Conditions (`contract.py`)

| ID | Burst family | Base p (gates and measurements) |
|---|---|---:|
| F2 | `centre_row` | 0.003 |
| P2 | `scaled_v1` | 0.002 |
| P4 | `scaled_v1` | 0.004 |

All conditions use d=5, 5 rounds and `model_v14` (`CodeSpec(distance=5, gate_p=p, measurement_p=p)`), with q ∈ {0, 0.01, 0.02}.

## Sampling

- **Shots:** 30,000 labeled shots per (condition, q), one sampler call each. That is 9 calls and **270,000 shots** in total.
- **Seeds:** `DEV_SEEDS.json`, screened against every earlier inventory, including d57 Phase 1, the screen and d=5 Phase 2.
- **Storage:** detectors and observables are saved bit-packed in git-ignored `work/dev/`.

## Selections (in-sample on Step D shots)

**Astar_C** is static PyMatching over correlations {ON, OFF} × q_dec ∈ {0, 0.0025, …, 0.02}.
- The winner has the **minimum total errors over the three q conditions**, which carry equal shots.
- Ties go to the smaller q_dec, then ON before OFF.
- This is the exact Phase 1 rule that selected Phase 2's comparator.
- **Correction:** the draft plan described this rule wrongly, as "nonzero errors subject to a q=0 guard". The protocol follows the actual Phase 1 rule.

**L2 prior:** L2 (product-sum, serial, max_iter 50, OSD-CS order 10) on the undecomposed DEM at static q_dec ∈ {0.0025, 0.005, 0.01, 0.02}. This is the Step 0 rule:
- **Eligible:** priors whose q=0 errors are ≤ 1.10 × Astar_C's q=0 errors.
- **Selected:** the eligible prior with the fewest nonzero errors (q = 0.01 + 0.02). Ties go to the smaller prior.
- **Fallback:** if no prior is eligible, take the one with the fewest q=0 errors and flag `guard_failed`.

## Sizing (Phase 1 formula)

Let v_q be the per-shot variance of (L2_selected error − Astar_C error) at q, and let L be Astar_C's equal-weight nonzero LER. Then:

**N_req = ⌈1.96² · (v_0.01 + v_0.02)/4 / (0.25·L)²⌉**

- If N_req > 200,016, that condition is labelled **projected under-powered** in `DEV_SELECTION.json`.
- The evaluation N is not changed.

## Execution

- **Rehearsal first:** 300 shots per (condition, q) on rehearsal seeds, written to `work/`. The full pipeline and the aggregator run in rehearsal mode. This is not data.
- **Run:** 9 sample jobs, then 36 L2 jobs (3 conditions × 3 q × 4 priors), at most 8 at once. Each writes once and refuses to overwrite.
- **Output:** `DEV_SELECTION.json`, written once and committed before any evaluation seed is drawn.
