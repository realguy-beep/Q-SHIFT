# d=5/d=7 evaluation, Phase 1: development selection and sizing (protocol)

**Committed before any Phase 1 sample.** The owner authorized Phase 1 on 2026-11-16 ("Build and run"). The design is in `DESIGN_PLAN_DRAFT.md` (approved; `237be2040`). Phase 1 shots are **development data**: they are used here for selection and sizing, and are never reused for evaluation.

## Sampling (fresh seeds, `PHASE1_SEEDS.json`)

- **Circuit:** `model_v14`, rotated Z-memory, rounds = 5, base p = 0.003, with the rule-defined scaled_v1 burst `CORRELATED_ERROR(q)`: d=5 support (23, 31, 34), d=7 support (46, 58, 61). Here q ∈ {0, 0.01, 0.02}.
- **Shots:** per (d, q), one labeled Stim sampler call: 100,000 shots at d=5 and 200,000 at d=7. That is **900,000 shots in 6 calls**.
- **Seeds:** the namespace is `qshift-d57-phase1-2026-11-16`, screened against every prior inventory (V1, V1.1, V1.2, V1.3, the V1.4 gate, V1.5, V1.6b, the performance sprint).

## Selection (in-sample on Phase 1 shots; V1.3 rules)

- **Astar_d:** static PyMatching over {correlations ON, OFF} × q_dec ∈ {0, 0.0025, …, 0.02} (9 values) on each distance's DEM. The winner has the minimum total errors over the three q conditions (equal shots, so equal-weight). Ties go to the smaller q_dec, then ON before OFF.
- **BoffStatic_d:** the five-factor decoder (`model_v14.FiveFactorDecoder`, correlations OFF, true support) with static prior over {0.00125·k : k = 1…16}, using the same criterion. To bound cost, it is evaluated on the **first 25,000 shots per q at d=5 and the first 50,000 at d=7**.

## Measurements for sizing

- **V3.2** (`ldpc==2.4.1`, frozen V3.2 settings) on all Phase 1 shots, with the DEM at the **true** q. That is a privileged model used here only as a sizing input; it may slightly overstate V3.2's per-root-q̂ performance.
- **A_nominal** (burst-free DEM, correlations OFF).
- **Per-shot decode time per arm.** All of V3.2 and the matchers are timed; the five-factor decoder on its subsample; and V3 (NumPy) at d=5 on the first 2,000 shots per q, to decide whether V3 is affordable in Phase 2.

## Sizing formula (determines the Phase 2 N; fixed now)

For each distance, with the Phase 1 estimates at q ∈ {0.01, 0.02}:
- v_q is the per-shot variance of the paired error difference (V3.2 − Astar_d), that is (n₁₀ + n₀₁)/N − (Δ_q)²;
- L is Astar_d's equal-weight nonzero LER.

The per-q evaluation shots needed for a 95% CI half-width of at most 0.25·L on the equal-weight difference are:

**N_d = ⌈ 1.96² · (v_0.01 + v_0.02)/4 / (0.25·L)² ⌉**, rounded up to a multiple of 24 roots.

q=0 uses the same N_d. Phase 2 totals are Σ_d [3·N_d + 72·500] evaluation plus calibration shots.

- **Cap:** at most 6,000,000 shots and 10 h projected wall time, using the measured per-arm costs and the Phase 2 arm list.
- **If the cap binds,** N_d is scaled down proportionally, and that distance is labelled *projected under-powered* (its Phase 2 result may come out INCONCLUSIVE).
- **The V3 arm** enters Phase 2 at d=5 only if its projected cost fits within the cap after V3.2 and the comparators.

## Execution controls

- **Rehearsal first:** 2,000 shots per job on a separate rehearsal seed namespace, written to a separate output folder. It checks correctness and measures costs; rehearsal shots are not Phase 1 data.
- **Run:** 6 independent jobs (one per (d, q)) in parallel processes. Each writes its own output once and refuses to overwrite. No retry or seed substitution.
- **Wall-time budget:** 3 h for Phase 1, enforced by a monitored background run. Failed jobs are preserved and reported.
- **Raw shot arrays are not saved.** Only per-arm error counts, discordance counts and timings are saved, as lightweight JSON.
