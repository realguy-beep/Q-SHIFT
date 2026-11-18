# d=5 low-p regime screen, Stage S: development selection, headroom and sizing (protocol)

**Committed before any Stage S sample.**
- **Plan:** `PLAN_DRAFT.md` (`40aaa4955`), approved by the owner on 2026-11-18 ("Approve, build it").
- **Not yet authorized:** Stage S sampling, which needs a separate owner go-ahead.
- **Status of the data:** Stage S shots are **development data** and are never reused for evaluation.

## Conditions (`contract.py`)

| ID | Burst | Base p (gates and measurements) |
|---|---|---:|
| L10 | scaled_v1 (23, 31, 34) | 0.001 |
| L15 | scaled_v1 (23, 31, 34) | 0.0015 |

All conditions use d=5, 5 rounds, `model_v14` `CodeSpec(distance=5, gate_p=p, measurement_p=p)`, and q ∈ {0, 0.01, 0.02}. Burst support is true (oracle) support.

## Sampling

- **Shots:** 200,000 labeled shots per (condition, q), one Stim sampler call each. That is 6 calls and **1.2 M shots**.
- **Seeds:** `DEV_SEEDS.json`, screened against 3,261 prior values. These cover every earlier inventory, including the robustness, learned-support (Phase B/B2/C) and model-mismatch seed files, plus stim seed 1.
- **Storage:** arrays go in the git-ignored `work/dev/`. `dev_jobs.py` is byte-identical in logic to the robustness `dev_jobs.py`, and a test pins this.

## Selections (in-sample; robustness Step D rules, unchanged)

- **Astar_C:** static PyMatching over correlations {ON, OFF} × q_dec ∈ {0, 0.0025, …, 0.02}.
  - The winner has the minimum total errors over the three q values.
  - Ties go to the smaller q_dec, then ON before OFF.
- **L2 prior:** L2 (product-sum, serial, max_iter 50, OSD-CS order 10, undecomposed DEM) at q_dec ∈ {0.001, 0.0025, 0.01}.
  - **The grid is a deviation from Step D's {0.0025, 0.005, 0.01, 0.02}.** It is extended down for low p and cut to 3 values for cost. Step D found that the prior moves errors very little.
  - **Eligible:** priors whose q=0 errors are ≤ 1.10 × Astar_C's q=0 errors.
  - **Selected:** the eligible prior with the fewest nonzero errors. Ties go to the smaller prior.
  - **Fallback:** if none is eligible, take the prior with the fewest q=0 errors and flag `guard_failed`.

## Headroom, stop rule, sizing (`dev_aggregate.py`)

**Reported per condition:**
- R_in_sample = 1 − (L2_selected nonzero errors)/(Astar_C nonzero errors);
- the floor ratio, i.e. L2_selected's q=0 LER divided by Astar_C's nonzero LER;
- cap = 1 − floor ratio;
- discordance;
- ms/shot.

**Stop rule (pre-declared).** If R_in_sample at L10 is < **0.90**, the decision is **STOP**: 95% is not reachable at p = 0.001 for this burst, and that is reported. Otherwise the decision is PROCEED_TO_STAGE_E_FREEZE, with **both** conditions included. No condition is dropped.

**Stage E sizing, shots per q:** the larger of
- ⌈30 / (2 · L2 nonzero rate)⌉, using a rule-of-three rate of 3 errors if L2 has none;
- the Phase 1 formula ⌈1.96² (v₁ + v₂)/4 / (0.25 L)²⌉;

rounded up to a multiple of 24 roots. The Stage E freeze fixes the final allocation within a hard 5 h budget.

## Execution

- **Rehearsal (done, not data):** 300 shots per cell on rehearsal seeds, run through `run_dev.py --rehearse` and the aggregator. Every job returned rc 0.
  - Timing under 8-way contention: L2 at about 6 ms/shot for L10 and 11.5 ms/shot for L15.
- **Run:** `python outputs/qshift_d5_lowp_regime_v1/run_dev.py`.
  - It needs a clean tree with `DEV_SEEDS.json` committed.
  - It runs 6 sample jobs, then 18 L2 jobs, at most 8 at once. Each writes once.
  - Projected time is about 1.1 h. This is above the plan's 20–30 min estimate, which left out the three-prior multiplier.
- **Output:** `DEV_SELECTION.json`, written once, plus `DEV_RESULTS.md`, committed before any Stage E seed is drawn.
