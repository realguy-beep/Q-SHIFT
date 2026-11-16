# Scalable decoder evaluation at d=5 and d=7: design plan (DRAFT, not frozen)

**Status:** planning draft for owner review. No code, seeds, freeze or sampling. Nothing here authorizes execution.

## Question

On fresh data at d=5 and d=7, does hypergraph BP+OSD (V3.2 `ldpc`, the feasible implementation; V3 NumPy where affordable) beat the **strongest static matcher**, re-selected at each distance, on the same correlated-burst noise family? And how much of any gain appears with **no bursts at all** (q=0, background hyperedges only)?

## What we already know

- **At d=3** (development data), BP+OSD recovers 93–99% of the exact decoder's gain over static matching. Most of that gain comes from faithful hyperedge modelling, and it appears at q=0 too.
- **At d≥5 there is no exact reference**: the elimination width is 28 at d=5 and 53 at d=7. Claims can only be relative to matching.
- **The V1.4 gate at p=0.003** (scaled_v1 burst family; best static matcher; errors per 20,000 shots, q = 0 / 0.01 / 0.02): d=5 gave 31 / 30 / 37 (about 0.15–0.19%), and d=7 gave 2 / 5 / 4 (about 0.01–0.025%).
- **Weight-3 bursts mostly stop mattering at d≥5**, so any d≥5 benefit would come mainly from background hyperedges, not burst handling.
- **Consequence:** d=7 at p=0.003 needs about **1.5 million shots per condition** to see roughly 300 comparator errors. That is the main cost driver.

## Fixed elements

- **Circuit:** `model_v14` (pinned to V1.1 at d=3): rotated Z-memory, d ∈ {5, 7}, rounds = 5, base p = 0.003 (decision 1 covers an optional extra p).
- **Bursts:** the rule-defined scaled_v1 burst at q ∈ {0, 0.01, 0.02}, with supports from `BURST_SUPPORT.json`: d=5 X23 X31 X34 and d=7 X46 X58 X61.
- **Decoders:**
  - V3.2 (`ldpc==2.4.1`, frozen V3.2 settings) and V3 (NumPy, d=5 only, if the preflight runtime allows);
  - the five-factor decoder from `model_v14`;
  - PyMatching.
- **Per-root q̂:** a detector-only parity fit restricted to the known burst events at that distance, on 500 calibration rows per root (the V1.6b method, generalized to one known class).

## Phase 1: development selection and sizing (fresh dev seeds; small)

- **Shots:** per distance, about 100,000 labeled development shots per q at d=5 (300,000 in total) and about 200,000 per q at d=7 (600,000).
- **Selected on these dev shots only:**
  - Astar_d: static PyMatching over {correlations ON, OFF} × q grid;
  - BoffStatic_d: the five-factor static prior;
  - both with the V1.3 rule and tie-breaks.
- **Measured for sizing:** comparator LERs, discordant-pair rates and **real-shot decode cost per arm**.
- **Sizing formula (pre-registered):** choose the evaluation N per (d, q) so that the projected 95% CI half-width of V3.2 − Astar is at most **25% of Astar's nonzero LER**, capped by the budget in decision 3.
- These shots are never reused for evaluation.

## Phase 2: frozen evaluation (fresh seeds; separate sign-off)

**Arms** (all on identical detector rows):

| Arm | Definition |
|---|---|
| A_nominal | PyMatching on the burst-free DEM, correlations OFF |
| Astar_d | static matcher selected in Phase 1 (the comparator) |
| BoffStatic_d | five-factor, true support, static prior from Phase 1 |
| **V3.2** | ldpc BP+OSD on the DEM at per-root q̂ (candidate) |
| V3 | NumPy BP+OSD at per-root q̂ (d=5 only; secondary) |

**Endpoints, separately per distance:**
- **Co-primary:** V3.2 − Astar_d, equal-weight nonzero, root-paired bootstrap 95% CI entirely below 0.
- **Safety:** at q=0, V3.2 − Astar_d with a 95th percentile below +0.05 × Astar_d's q=0 LER (relative, because LERs are small).
- **Key secondary:** the q=0 contrast V3.2 − Astar_d, which is the pure background-hyperedge gain.
- **Other secondaries:** V3.2 − BoffStatic_d, V3.2 − A_nominal, V3 − V3.2 (d=5), and relative reductions.

**Decision:**
- GO_d5 / GO_d7 is declared per distance.
- The overall result is GO if d=5 is GO and d=7 is GO or INCONCLUSIVE.
- NO-GO if V3.2 is significantly worse than Astar at either distance.
- An under-powered d=7 is reported as INCONCLUSIVE, never as a positive.

**Roots and controls:** 24 roots per (d, q), with 500 calibration plus N/24 evaluation shots each. The V1.5/V1.6b machinery carries over: hash freeze, LF pinning, watchdog, single attempt, fake-sampler rehearsal, frozen recount, and identical re-analysis.

## Cost estimates (to be replaced by Phase 1 measurements)

The V3.2 deterministic-syndrome medians were 25 ms at d=5 and 10 ms at d=7. Real d=3 shots were about 13× faster than the deterministic ones (0.22 vs 2.9 ms), so real d=5/7 shots are *estimated* at about 1–3 ms per shot per V3.2 decode. This estimate is unverified. Five-factor (32 matching calls per shot) is probably the slowest arm at d=7.

| Item | Shots | Rough decode time |
|---|---:|---:|
| Phase 1 (d=5 + d=7) | about 0.9 M | about 1–2 h |
| Phase 2 d=5 (≈400 Astar errors per q) | about 0.8 M | about 1–2 h |
| Phase 2 d=7 at p=0.003 (≈300 Astar errors per q) | about 4.5 M | about 4–8 h |

## Decisions for the owner

1. **Noise regime at d=7. DECIDED (owner, 2026-11-16): p=0.003 only, at both distances**, for continuity with V1.1–V1.6b and the V1.4 gate. No p=0.005 arm. As a result, d=7 needs about 4.5 M evaluation shots to be powered.
2. **The role of d=7. DECIDED (owner, 2026-11-16): powered.** d=7 is a full co-primary distance, sized by the pre-registered formula. It is reported INCONCLUSIVE only if the formula's target can't be met within the cap.
3. **Budget caps. DECIDED (owner, 2026-11-16):** Phase 1 about 0.9 M development shots. Phase 2 at most **6 M evaluation shots** and **10 h wall time**, with N per (d, q) set by the sizing formula within that cap.

**Status:** the design is approved. Building and running Phase 1 (new development sampling) still needs explicit sign-off, and so does the Phase 2 frozen run.
