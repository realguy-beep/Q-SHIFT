# Q-SHIFT correlated-noise decoding: consolidated report (V1.1 → d=5 Phase 2 → belief-matching → d=5 robustness)

**Date:** 2026-11-17
**Branch:** `codex/qshift-correlated-decoder-v1-6`

**Scope:** simulation only. A rotated surface-code Z-memory (5 rounds, p = 0.003 unless noted) with one synthetic correlated X-burst (`CORRELATED_ERROR(q)` on three data qubits after every measurement round), at q ∈ {0, 0.01, 0.02}. There is no hardware data. Every frozen result is labelled *development evidence* by its own protocol.

This report summarizes and links. It does not change or re-derive any frozen result. Each number below is quoted from the study's own results file.

## 1. Bottom line

1. **At d=3, correlated-noise-aware decoding reaches the DEM's exact ceiling and roughly halves the strongest matcher's error rate.** The exact (maximum-likelihood) decoder is 61% below the best static matcher (V1.5), and that holds when the burst's location is *learned* from calibration data (V1.6b: 61.5% for the known burst, 52.4% for a sealed hidden burst).
2. **At d=5, a scalable decoder keeps most of that gain on fresh seeds.** Hypergraph BP+OSD, with a serial schedule and one static prior, is **64.8% below** correlated PyMatching (95% CI 61.2–68.4%; frozen Phase 2, GO_d5). **The gain is robust to three single-factor changes** (frozen robustness study, ROBUST): it was 20.9% for a 2-detector centre_row burst, 78.1% at p = 0.002 and 56.8% at p = 0.004. The comparator and prior were re-selected per condition.
3. **At d=7, nothing tried beats correlated matching.** That covers BP+OSD (parallel or serial) and belief-matching (parallel BP), all on development screens. Both pre-registered d=7 screens returned STOP.
4. **Most of the gain does not come from handling the burst.** At d=3, about 80% of the recoverable gap was background inference: degeneracy and hyperedges (V1.4B). At d=5, BP+OSD is 46% better than matching even with **no bursts** (q=0). The gain comes from decoding the full hypergraph DEM, which matching has to decompose.
5. **The owner's 90–95% target was not reached, and it is not reachable in this noise family.** At d=3 the burst-oracle ceiling is about 64% (V1.4 gate). No (d, p) cell qualified for 90% with margin. At d=5 the background errors that BP+OSD only halves cap the reduction well below 90%.

## 2. Study timeline

The outcome column gives each study's own pre-registered result. LER figures are equal-weight over q ∈ {0.01, 0.02} unless noted.

| Study | Question | Outcome | Key numbers |
|---|---|---|---|
| **V1.1** | d=3 feasibility of a five-factor burst-mask decoder | Frozen classification **INCONCLUSIVE**: the analyzer key mismatch stopped finalization | Fixed analyzer in a new package (`qshift_correlated_decoder_v1_1_analyzer_fix_v1`). Its GO on a copy is *not* the frozen result |
| **V1.2** | Five-factor B with per-root q̂ vs strong matchers | **GO_DEVELOPMENT_ONLY** | B 1.149% vs Astar 1.421% (**−19.2%**); B − Astar −0.272 pp [−0.308, −0.238] |
| **V1.3** | Cost-consistent five-factor (Boff) vs Astar and the mode-switching matcher A2sw | **GO_DEVELOPMENT_ONLY** | Boff 0.734% vs Astar 1.392% (**−47%**) and vs A2sw 1.551%; Boff − Astar −0.658 pp [−0.703, −0.613] |
| **V1.4** (gate) | Is ≥90% reachable in any regime (d 3/5/7 × p 1–3e-3 × 2 burst families)? | **No cell qualifies**: stop | d=3 ceiling about 64%. Best point ceilings 0.90–0.93 at d=5, p ≤ 0.002, but with lower bounds 0.40–0.49 |
| **V1.4B** | How far is Boff from optimal? | **GO** (DEM-exact decoder) | DEM-exact at detector-only q̂: 0.553%, **−60.3% vs Astar** and −23.7% vs BoffStatic. Sits at the DEM ceiling. About 80% of the gap is background inference |
| **V1.5** | Frozen evaluation of the exact decoder Bexact | **GO_DEVELOPMENT_ONLY, TARGET_MET** | Bexact 0.542% vs BoffStatic 0.739%: **−26.6%** [23.7, 29.7]. vs Astar 1.400%: −61% |
| **V1.6** (dev gate) | Learn burst support from detector-only data | **FAIL (G1 = 76.4%)**: stop | The logical effect is not identifiable from detectors alone. Each of the 15 signature classes is ambiguous |
| **V1.6b** | Device-level learned support plus a labeled logical stage, with a sealed hidden burst | **GO_DEVELOPMENT_ONLY, TARGET_MET** | Both bursts learned exactly, so Blearn = Bexact_oracle on all 576,000 shots. **Known: −61.5%** [59.1, 63.8] vs Astar. **Hidden: −52.4%** [49.4, 55.4] |
| **V3** | Scalable NumPy BP+OSD | **REVISE** | d=3: 93–99% of the exact decoder's gain. d=7 runtime 60.7 ms > 50 ms gate |
| **V3.1** | Batched BP for speed | **REVISE** (negative) | Bit-equivalent to V3, but slower. BP is compute-bound (the earlier diagnosis was wrong) |
| **V3.2** | Compiled BP+OSD (`ldpc==2.4.1`, owner-approved) | **GO** (engineering milestone) | Correctness and speed gates pass. d ≥ 5 accuracy not measured |
| **d57 Phase 1** | Development selection and sizing at d=5/7 | Development | d=5: V3.2 **−37%** vs Astar_5. d=7: V3.2 about **2× worse** than Astar_7 |
| **d=7 configuration screen** | Can any BP+OSD configuration (L0–L3) beat Astar at d=7? | **STOP_d7** | Best (serial, L2): **57 vs 55** errors (a tie). d=5 check: L2 80 vs 217 |
| **Step 0** | A static prior for d=5 | Selected q_dec = 0.01 | Flat across 0.0025–0.02 (77–81 errors). True-q oracle: 80 |
| **d=5 Phase 2** (frozen) | Fresh-seed confirmation at d=5 | **GO_d5** | **L2s −64.8%** [61.2, 68.4] vs Astar. q=0: −46%. Static prior = oracle prior. 600,048 shots |
| **Belief-matching Phase A** | Build and verify BP-reweighted matching | Built. Gate fails for serial | d=3: 76% (parallel) and 87% (serial) of the exact decoder's gain. Serial BP about 200 ms/shot at d=7 |
| **Belief-matching screen** (BM0) | Does parallel belief-matching beat Astar at d=7? | **STOP** | d=7: **76 vs 55**. d=5: 109 vs 217 (−50%, behind BP+OSD's 80) |
| **d=5 robustness** (frozen) | Does the d=5 gain survive a different burst family (F2), p = 0.002 (P2) and p = 0.004 (P4)? | **ROBUST** (all GO; Bonferroni and q=0 safety pass) | L2s vs re-selected Astar: **F2 −20.9%** [13.3, 28.0], **P2 −78.1%** [71.8, 83.8], **P4 −56.8%** [53.0, 60.3]. Static prior ≈ oracle prior. 1,800,144 shots |

## 3. Baselines and fairness

- **The comparator is always the strongest available matcher, selected on development data.**
  - Astar: static correlated PyMatching over a correlation-mode × q grid.
  - A2sw: a mode-switching matcher, at d=3 only.
  - Weak nominal baselines (A_nominal) are reported only as references, never as the claim.
- **At d=3, Astar itself (about 1.4%) is about 5× better than uncorrelated nominal matching (about 7%).** All quoted reductions are against Astar, not the nominal baseline.
- **Learned vs oracle.** V1.2–V1.5 gave the five-factor and exact decoders the true burst support (oracle support). V1.6b removed that caveat for the two bursts tested. The d=5/7 BP+OSD and belief-matching decoders use the DEM at a static q_dec, with the true support of the *known* burst.

## 4. Why d=7 is different (interpretation, not a tested claim)

- **V1.4 showed** that weight-3 bursts become nearly harmless at d=7: few logical failures need them.
- **At d=7, BP rarely converges on real shots.** BP+OSD then depends on an OSD search that is too narrow at about 3,700 columns. Belief-matching hands BP's soft output to a matcher, but parallel BP's posteriors appear less informative than PyMatching's own two-pass correlation reweighting.
- **Serial BP was the strongest variant at d=3 and at d=5.** In `ldpc` 2.4.1 it costs about 20× more per iteration, so serial belief-matching could not be screened affordably.

The d=7 negative therefore covers: BP+OSD (L0–L3, development screen) and **parallel** belief-matching (development screen). Serial belief-matching at d=7 is untested.

## 5. What is and is not claimed

**Claimed (as development evidence, for this simulated noise family):**
- Exact decoding at d=3 reaches the DEM ceiling and is about 61% below the strongest matcher. This holds with learned support (V1.5, V1.6b).
- Serial hypergraph BP+OSD with a static prior is about 65% below the strongest matcher at d=5, p = 0.003 (frozen Phase 2).
- At d=5 that advantage holds under a second burst family and at p = 0.002 and 0.004 (frozen robustness study, ROBUST). Its size is regime-dependent: 21–78%.

**Not claimed:**
- any hardware result or real-device noise;
- any advantage at d=7;
- that the method scales;
- generality beyond the tested settings: the d=5 burst families scaled_v1 and centre_row, weight 3, at p ∈ {0.002, 0.003, 0.004}, plus V1.6b's hidden burst at d=3. Other burst weights, rates and shapes are untested;
- real-time feasibility. BP+OSD at d=5 takes about 13–31 ms/shot, three to four orders of magnitude slower than matching;
- novelty of the algorithms. BP+OSD and belief-matching are established methods. The contribution is careful, pre-registered measurement against strong baselines.

## 6. Deviations and disclosures (all recorded in their study folders)

- **V1.1:** the frozen analyzer failed on a key mismatch. The fix went into a new versioned package, an in-place edit was reverted, and the frozen classification stays INCONCLUSIVE.
- **V1.2:** a fabricated full SHA in a draft config was replaced with the real `git rev-parse` value before the freeze.
- **V1.2/V1.3:** CRLF line endings broke the freeze hashes. Files were normalized to LF with `.gitattributes`, re-frozen, and the change disclosed.
- **V3.2 environment:**
  - an unapproved 1.7 MB `pip download` probe was deleted and disclosed;
  - the approval request did not list four transitive packages (sinter, pytest, pluggy, iniconfig). They are recorded in `ENVIRONMENT_DELTA.txt`.
- **V1.6b:** the preflight under-projected the runtime by 1.75×. This is disclosed, and the run stayed within its cap.
- **d=5 Phase 2:**
  - the candidate uses a static prior selected on development data (Step 0) instead of the approved design's per-root q̂;
  - the q=0 safety rule gained a "≤ 0 passes" clause *before* the freeze, after a 1-root rehearsal exposed a zero-margin edge case.
- **Belief-matching:**
  - the edge-probability rule is the exact independent-merge rule rather than the plan's sum rule;
  - the screened variant set was cut to BM0 after the serial variants failed the cost gate (owner-approved).
- **d=5 robustness:**
  - the plan misstated Astar's selection rule. The protocol uses the actual Phase 1 rule, and the correction is recorded;
  - an overall INCONCLUSIVE verdict case, missing from the plan, was added before the freeze.
- **Reuse of development data:** the d57 screen arrays were reused for Step 0 and for the belief-matching screen. That is development selection only, and all frozen evaluations used fresh, collision-screened seeds.

## 7. Open directions (none authorized)

1. **Learned support at d=5.** Replace the known burst support in the BP+OSD DEM with support learned from calibration data, as in V1.6b. This removes the remaining oracle caveat at d=5.
2. **Burst weight at d=5.** Test weight 2 and weight 4 bursts. This is the remaining single-factor robustness axis, and the existing robustness package can be reused.
3. **Serial belief-matching at d=7.** This needs a faster serial BP: an in-house batched layered schedule, verified bit-equal to `ldpc`. Given the V3.1 result, the speed-up is uncertain.
4. **The 90% target.** This needs a different noise family in which bursts dominate the error budget, such as stronger or more frequent bursts, or lower p with more shots for power. That would be a new study design, not a continuation.

## 8. Where things are

| Study | Folder (`outputs/`) | Frozen commit |
|---|---|---|
| V1.2 | `qshift_correlated_decoder_v1_2/results_v1/RESULTS.md` | `b95687ccb` |
| V1.3 | `qshift_correlated_decoder_v1_3/results_v1/RESULTS.md` | `bd43689e1` |
| V1.4 gate | `qshift_correlated_decoder_v1_4/GATE_RESULTS.md` | — |
| V1.4B | `qshift_v1_4b_decoder_optimality/DECISION.md` | — |
| V1.5 | `qshift_correlated_decoder_v1_5/results_v1/RESULTS.md` | `f6f5a4b4e` |
| V1.6 gate | `qshift_correlated_decoder_v1_6/DEV_GATE_RESULT.md` | `304767972` (pre-registration) |
| V1.6b | `qshift_correlated_decoder_v1_6b/results_v1/RESULTS.md` | `02b7aa276` |
| V3 / V3.1 / V3.2 | `qshift_scalable_decoder_dev_v3{,_1,_2}/RESULTS.md` | — |
| d57 Phase 1, screen, Step 0 | `qshift_scalable_decoder_eval_d57_v1/` | protocols at `2c79f6ac2`, `5659e20f1`, `f81be21a7` |
| d=5 Phase 2 | `qshift_scalable_decoder_eval_d5_phase2_v1/results_v1/RESULTS.md` | `d22fccf70` |
| Belief-matching | `qshift_belief_matching_d7_v1/{PHASE_A_RESULTS,SCREEN_RESULTS}.md` | screen protocol `1fd226506` |
| d=5 robustness | `qshift_d5_robustness_v1/results_v1/RESULTS.md` (Step D: `DEV_RESULTS.md`) | `4d77c2d9e` |

Raw arrays live in each study's git-ignored `work/` or `pilot_runs/` folder on the local machine. Committed results carry the counts, hashes and analyses needed to audit them.
