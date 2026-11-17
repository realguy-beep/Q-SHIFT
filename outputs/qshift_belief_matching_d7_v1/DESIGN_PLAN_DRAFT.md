# Belief-matching at d=7: design plan (DRAFT, not frozen)

**Status:** planning draft for owner review. It authorizes nothing. The build, the development screen and the frozen evaluation each need sign-off.

## Why

- **At d=7, BP+OSD tied the strongest matcher and could not beat it** (`SCREEN_RESULTS.md`: STOP_d7). On real d=7 shots BP rarely converges, so the result rests on OSD-CS order 10 over about 3,700 columns, and that search is too narrow.
- **At d=5, BP+OSD beat the matcher by 65%** on fresh seeds (`qshift_scalable_decoder_eval_d5_phase2_v1`, GO_d5). Most of that gain came from modelling hyperedges, the correlated mechanisms that matching has to split apart.
- **Belief-matching keeps that modelling gain but hands the final search to matching**, which stays strong at d=7. BP runs on the full hypergraph DEM. Its per-mechanism posterior probabilities then re-weight the edges of a matching graph built from the decomposed DEM, and PyMatching finds the correction.
- **It is faster than BP+OSD,** because there is no OSD elimination.
- **No new dependency is needed.** ldpc 2.4.1's `BpDecoder` exposes `log_prob_ratios`, and PyMatching 2.4.0 can rebuild its graph with new weights (`load_from_check_matrix`, or `add_edge` with `merge_strategy="replace"`).

## Decoder (to build)

`bm.py`, class `BeliefMatching(dem_hyper, dem_decomposed, bp_settings)`:

1. **Mapping, built once.** Each merged hyperedge mechanism *h* of the undecomposed DEM is matched to the graphlike components that stim's `decompose_errors=True` produces for the same instruction. Each matching edge *e* gets the set of hyperedges whose decomposition contains it.
   - If a mechanism can't be mapped unambiguously, that is an error at build time, not a silent fallback.
2. **Per shot:** run BP on the hyper DEM to get a posterior p̂_h for every mechanism *h*.
3. **Edge probability:** p_e = Σ_{h ∋ e} p̂_h (the Higgott et al. 2023 rule), clipped to [1e-12, 0.5). The weight is w_e = log((1 − p_e)/p_e).
4. **Matching:** run uncorrelated PyMatching on the re-weighted graph, giving the logical prediction.
5. **Variant "+conv":** if BP converged to a solution that reproduces the syndrome, use BP's own logical prediction instead.

## Candidate variants (fixed before the screen)

All variants use a static DEM prior. Static priors worked at d=5, where the prior made no measurable difference.

| ID | BP | Prior q_dec | BP-converged shortcut |
|---|---|---:|---|
| BM0 | product-sum, parallel, 50 iterations | 0.01 | no |
| BM1 | product-sum, **serial**, 50 iterations | 0.01 | no |
| BM2 | as BM1 | 0.01 | **yes** |
| BM3 | as BM1 | 0.0025 | no |

## Phase A: build and verify (no sampling)

Tests:
- **Identity:** when the posteriors equal the priors (BP with 0 iterations), BM's predictions must equal plain uncorrelated PyMatching on the same decomposed DEM, bit for bit, on deterministic syndromes at d=3, 5 and 7.
- **Mapping completeness:** every hyperedge maps, at d=3, 5 and 7, and the total prior mass is preserved.
- **d=3 quality vs exact:** use the V3 deterministic-syndrome generator and the exact decoder (`mld.py`), as in `QUALITY_D3.json`. This is reported, not gated.
- **Cost:** deterministic-syndrome timing at d=5 and d=7.

**Gate:** if the per-shot graph rebuild makes BM slower than about 50 ms/shot at d=7, stop and report before screening.

## Phase B: development screen (saved arrays; no new sampling)

**Data.** All of it is already saved in `qshift_scalable_decoder_eval_d57_v1/work/screen/`:
- d=7: 450,000 shots (150,000 per q, 18 chunks);
- d=5: 150,000 shots, used as a check.

These arrays were already used to screen the L configurations. Re-using them is development selection. The frozen evaluation (Phase C) uses fresh seeds.

**Comparators** use the saved per-shot error bits on the same rows: Astar (correlated PyMatching, q_dec 0.0025) and L2 (serial BP+OSD).

**Selection rule (to be committed before any BM decode):**
- **Selected variant:** among BM0–BM3, the one with the fewest d=7 nonzero-q errors. Ties go to the lower ID.
- **ADVANCE** to a Phase C plan only if both hold:
  1. at d=7, the selected variant's nonzero errors are **below Astar's** (55), and its q=0 errors are ≤ 1.10 × Astar's (28);
  2. at d=5, its nonzero errors are below Astar's (217).
- **STOP:** no variant beats Astar at d=7. We then report that belief-matching does not close the d=7 gap.
- **REVISE:** some variant beats Astar at d=7, but the selected one fails the d=5 or q=0 check.

**Noise warning.** The d=7 counts are small (about 55 comparator errors on nonzero shots), and the selection is in-sample over 4 variants. A pass here is a weak signal, which is why Phase C exists.

**Cost estimate.** About 600,000 shots × 4 variants. If BM is about 10–20 ms/shot at d=7, that is roughly 1–2 h on 8 workers. Phase A replaces this estimate.

## Phase C: frozen d=7 evaluation (only if Phase B returns ADVANCE; separate sign-off)

This reuses the d=5 Phase 2 machinery: freeze, fresh screened seeds, single attempt, recount, re-analysis.

- **Allocation:** N_7 = 406,128 per q, from the pre-registered Phase 1 sizing formula (CI half-width ≤ 25% of Astar's LER). That is 1,218,384 shots in 3 × 24 roots. The formula only detects reductions of about 25–30% or more, which is stated up front.
- **Arms:**
  - Astar (comparator);
  - the selected BM variant (candidate);
  - A_nominal (reference);
  - L2s at d=7 as a secondary, **only if** the preflight keeps the total within 10 h. Otherwise it is dropped and the drop is stated.
- **Endpoints and decision:** the same as d=5 Phase 2. Co-primary: BM − Astar, equal-weight nonzero, with the 95% CI below 0. Plus the q=0 safety check and R as a reported secondary. Decisions are GO_d7, NO-GO_d7 or INCONCLUSIVE.
- **Budget:** within the approved caps of 6 M shots and 10 h.

## Claim boundaries

- Simulation only, one synthetic burst mechanism, p = 0.003.
- Belief-matching is an established technique from the literature (Higgott et al. 2023). A positive result would mean it works in this regime, not that the method is new.
- If Phase B stops, the d=7 conclusion stands: in this regime, neither hypergraph decoder tried here beats correlated matching at d=7.

## Owner decisions

1. **Approve the plan**, or ask for changes, such as different variants or a different d=7 sample size.
2. Then a go-ahead for **Phase A** (build and tests, no sampling).
3. Phase B needs its own go-ahead after Phase A reports its cost. Phase C needs one after Phase B returns ADVANCE.
