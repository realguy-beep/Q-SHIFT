# d=5 robustness of the BP+OSD gain: design plan (DRAFT, not frozen)

**Status:** planning draft for owner review. It authorizes nothing. The development step and the frozen evaluation each need sign-off.

## Question

The frozen d=5 Phase 2 (`qshift_scalable_decoder_eval_d5_phase2_v1`, GO_d5) found serial hypergraph BP+OSD **64.8% below** correlated PyMatching, in **one** setup: the scaled_v1 burst at base noise p = 0.003.

**Does a significant gain over the strongest static matcher hold when the burst shape or the base noise level changes?**

## Conditions (three, each changing one factor from Phase 2)

| ID | Burst family (`model_v14.burst_qubits`) | Base noise p (gate = measurement) | What it tests |
|---|---|---:|---|
| **F2** | `centre_row`: three adjacent data qubits in the centre row (declared in V1.4's `BURST_SUPPORT.json`) | 0.003 | burst shape |
| **P2** | `scaled_v1` | 0.002 | lower noise |
| **P4** | `scaled_v1` | 0.004 | higher noise |

All three use d=5, 5 rounds, q ∈ {0, 0.01, 0.02}, and the same circuit builder as Phase 2. The conditions are fixed now, before any data.

**What to expect, from V1.4:**
- In `centre_row`, each burst event has a 2-detector signature that looks like an ordinary matching edge, so the static matcher already handles it well. Any gain there should come mainly from **background hyperedges**, which is what this condition probes.
- At p = 0.002, Astar's LER at d=5 is about 0.1%, which still gives about 200 comparator errors per q at the planned size.

## Step D: development selection (fresh development seeds, per condition)

**Data:** 30,000 labeled development shots per q, so 90,000 per condition and **270,000 in total**. These seeds are never reused for evaluation.

**Selections**, each following the earlier rule:
- **Astar_C:** static PyMatching over correlations {ON, OFF} × q_dec ∈ {0, 0.0025, …, 0.02} (9 values). Use the V1.3/Phase 1 rule: minimise equal-weight nonzero errors, subject to q=0 errors ≤ 1.10 × the best q=0 errors. Ties go to ON, then to the smaller q_dec.
- **L2s_C prior:** L2 (product-sum, serial, max_iter 50, OSD-CS 10) with a static DEM at q_dec ∈ {0.0025, 0.005, 0.01, 0.02} (the Step 0 rule, with Astar_C as the q=0 guard).

**Sizing check:** apply the Phase 1 formula, CI half-width ≤ 25% of Astar_C's nonzero LER. If 200,016 per q is below the formula's N for some condition, that condition is labelled *projected under-powered* before the freeze. N is not changed.

**Cost:** 4 L2 priors × 90,000 shots × about 25 ms, so roughly 20 min per condition on 8 workers. All three conditions together take about 1 h.

The output is a committed `DEV_SELECTION.json` before any evaluation seed is drawn.

## Step E: frozen evaluation (fresh seeds, one freeze for all three conditions)

**Allocation:** per condition, 24 roots × 8,334 shots per q, the same as Phase 2. That is 600,048 per condition and **1,800,144 in total** in 216 sampler calls.

**Arms (identical rows within a condition):**

| Arm | Definition | Role |
|---|---|---|
| Astar_C | selected in Step D | comparator |
| **L2s_C** | L2 at the Step D static prior | candidate |
| L2o_C | L2 at the true q | secondary (oracle prior) |
| A_nominal | PyMatching, burst-free DEM, correlations OFF | reference |

L0s and BoffStatic are dropped. Phase 2 has already answered their questions, and the five-factor prior would need its own per-condition selection.

**Endpoints (per condition):** the same as Phase 2.
- **Co-primary:** L2s_C − Astar_C, equal-weight nonzero, root-paired bootstrap with 20,000 replicates.
- **Safety at q=0:** the 95th percentile must be ≤ 0, or below 0.05 × Astar_C's q=0 LER.
- **Reported:** the relative reduction R with its CI, the q=0 contrast, L2s − L2o, and discordance.

**Decision:**
- **Per condition:** GO_C, NO-GO_C or INCONCLUSIVE, by the Phase 2 rules, each at 95%.
- **Overall robustness verdict** (three conditions, so a Bonferroni correction): the co-primary must be judged on a **98.33%** CI (α = 0.05/3), and safety must pass.
  - **ROBUST:** all three conditions pass.
  - **PARTIAL:** at least one passes and none is NO-GO.
  - **NOT_ROBUST:** any condition is NO-GO.

**Execution:** the Phase 2 machinery (contract, `run_all`, `eval_job`, analyze, recount, freeze), generalized to take the condition as a parameter:
- one freeze and one single-attempt run of 216 jobs, 8 at a time;
- a per-job timeout, then independent recount, bit-identical re-decode, and identical re-analysis;
- a fake-sampler rehearsal and a 1,000-shot real rehearsal per condition, before the freeze.

**Cost:** about 31 ms/shot across the four arms under contention, giving about 1.8 M × 31 ms / 8 ≈ 2 h, plus overhead. The preflight replaces this estimate. The hard budget is 5 h, inside the approved 6 M-shot / 10 h caps.

## Total

| Item | Shots | Projected wall time |
|---|---:|---:|
| Step D (development) | 270,000 | about 1 h |
| Step E (frozen evaluation) | 1,800,144 | about 2–2.5 h |

## Claim boundaries

- Simulation only, d=5 only, and one burst size (weight 3).
- A ROBUST verdict means the gain holds across these three single-factor changes. It is not a claim about all noise.
- d=7 stays negative (STOP), and this study does not revisit it.

## Owner decisions

1. **Approve the plan:** conditions F2, P2 and P4, N = 200,016 per q, Bonferroni-corrected overall verdict. Or ask for changes, for example a different condition set, or dropping L2o to save about 40% of the decode time.
2. Then a go-ahead for **Step D** (270,000 development shots, about 1 h).
3. Then, after the freeze, a go-ahead for **Step E**.
