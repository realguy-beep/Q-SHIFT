# RE2 results: frozen evaluation of the E1T pipeline with two new sealed bursts

**Verdict: NOT_CONFIRMED.** G1–G4 pass every gated endpoint. G5 (sealed burst H4) fails non-inferiority, with its point estimate beyond the margin, so the pre-registered logic gives FAIL_DIRECTION for G5 and NOT_CONFIRMED overall.

**Why G5 failed: one flagged root.**
- In G5 r04, E1T raised both checks (S1 and S2) and fell back to the nominal model, as designed. That root made 14 errors against the oracle's 1, and its 12 nonzero-q excess errors exceed the 10-error floor on their own.
- In the other 11 G5 roots, E1T learned H4 exactly, and L2L_E's decoded errors equal the oracle's (18 vs 18 nonzero-q). This split is descriptive and post hoc. It does not change the verdict.
- The records cannot say whether r04's flag rejected a correct class or caught a wrong one. The frozen scrub masks class correctness on a flagged root (`re2.py`, `estimate_e1t`), and the class itself is sealed.

**What passed, including on the sealed bursts:**
- **H3 (footprint ≥ 25):** in G3 (R6's base model) and G4, E1T learned H3 exactly in 24/24 roots, with no flags. L2L_E equalled the oracle bit for bit on the nonzero-q totals (14 vs 14; 100 vs 100). R against S\* was 0.91 in G3 and 0.76 in G4.
- **The R6 failure mode is repaired for this burst.** RE1's B2 estimator, run descriptively on the same roots, flagged 6/12 G3 roots and 4/12 G4 roots. Its G3 nonzero-q errors were 292, against E1T's 14.
- **K:** G1 and G2 learned 24/24, within 1 error of the oracle.
- **Safety at q = 0** and **SUP** passed in all five gated conditions, G5 included.

| | |
|---|---|
| Freeze | `67ed86c6a` (`RE2_FREEZE.json`, 68 files), run once from a detached checkout of that commit with `--open-hidden-seal` (RE2's seal only) |
| Run | 66/66 roots in a single attempt on 8 workers, 5,603 s (projected 10,446–13,058 s); every job returncode 0 |
| Samples | per root, 12,000 unlabelled + 1,500 labelled calibration rows and 12,000 evaluation shots (4,000 × q ∈ {0, 0.01, 0.02}). In total, 891,000 calibration and 792,000 evaluation shots, each evaluation shot decoded by every arm |
| Analysis | `results/re2/ANALYSIS.json`, run twice, byte-identical |
| Recount | `results/re2/RECOUNT.json`: the re-analysis is identical, and root 0 of all 6 conditions re-decodes identically (records and decoded error bits) |
| RE1's H2 seal | not read. The independence of H3 and H4 from H2 is untested (see below) |

## Errors per condition

The nonzero-q columns are summed over q = 0.01 and 0.02: 96,000 shots per arm (48,000 for X2). The q = 0 column has 48,000 shots per arm (24,000 for X2).

| Cond | Burst | L2L_E | Oracle L2s_true | S\* | Astar_true | A_nominal | L2L_B2 | L2L_E q=0 / A_nominal q=0 | Learned (E1T) | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| G1 | K | 31 | 30 | 90 | 89 | 458 | | 18 / 25 | 12/12 | **PASS** |
| G2 | K | 13 | 13 | 104 | 129 | 365 | | 3 / 9 | 12/12 | **PASS** |
| G3 | H3 (sealed) | 14 | 14 | 163 | 151 | 663 | 292 | 11 / 16 | 12/12 | **PASS** |
| G4 | H3 (sealed) | 100 | 100 | 409 | 395 | 1,172 | 391 | 46 / 79 | 12/12 | **PASS** |
| G5 | H4 (sealed) | 31 | 19 | 55 | 38 | 260 | | 5 / 9 | 11/12 (1 flagged) | **FAIL_DIRECTION** |
| X2 | K (descriptive) | 334 | 85 | 393 | 159 | 395 | | 55 / 65 | 0/6 (6 flagged) | descriptive |

## Endpoints (gated conditions)

All are root-bootstrap bounds, one-sided α = 0.0025, with 20,000 replicates. They are differences in LER.

| Cond | NI: L2L_E − oracle (est., upper) | NI margin (binding term) | NI_strict | SUP: L2L_E − S\*, upper | Safety q=0: p95 ≤ margin | R vs S\* (95% CI) |
|---|---|---|---|---|---|---|
| G1 | 1.0e-5, 4.2e-5 | 1.04e-4 (floor) | pass | −2.6e-4 | 2.1e-5 ≤ 6.3e-5 | 0.66 (0.46–0.79) |
| G2 | 0, 0 | 1.04e-4 (floor) | pass | −6.8e-4 | −4.2e-5 ≤ 6.3e-5 | 0.88 (0.81–0.93) |
| G3 | 0, 0 | 1.04e-4 (floor) | pass | −1.16e-3 | 2.1e-5 ≤ 6.3e-5 | 0.91 (0.87–0.95) |
| G4 | 0, 4.2e-5 | 2.60e-4 (25%) | pass | −2.60e-3 | −5.2e-4 ≤ 8.2e-5 | 0.76 (0.71–0.79) |
| G5 | **1.25e-4, 5.0e-4** | 1.04e-4 (floor) | **fail** | −4.2e-5 | 2.1e-5 ≤ 6.3e-5 | 0.44 (0.22–0.70) |

In G5, the point estimate (12 / 96,000) is above the margin (10 / 96,000). By the frozen rule (`re2.analyze`) that is FAIL_DIRECTION, not NOT_SHOWN.

## What the estimators did

- **p̂ and b̂ (E1T):**
  - **p̂:** mean p̂ was within 1.1% of the true p in every gated condition (0.002310, 0.003219, 0.002801, 0.003384, 0.002609).
  - **b̂:** 1.02 in G1 and 1.00 in G4 (both unbiased), against 6.16 for Z6, 4.01 for Z4 and 4.96 for Z5.
- **Learning:** E1T learned the burst exactly in 59/60 gated roots, with 1 flag (G5 r04, both S1 and S2).
- **S\* choice:** Astar_Em was chosen in 49/60 gated roots.
- **L2L_B2 (descriptive):** RE1's estimator learned 6/12 in G3 and 8/12 in G4; the rest were flagged. It disagreed with L2L_E on 280 and 294 shots, against 2 and 3 the other way.
- **X2 (X-bias 8, out of scope):** E1T flagged all 6 roots (S1 and S2) and decoded nominally, as designed. p̂ was 0.0018 and b̂ 1.00: E1T's Z-bias model cannot represent X-bias. L2L_E was still below S\*, but far from the oracle, and the safety criterion would have failed. This is descriptive only.

## Independence from RE1's H2 (untested)

- H3 and H4 were drawn without reading RE1's seal. The probability that either coincides with H2's class is 6.0% under the draw distribution, and at most 32.3% in the worst case (`results/re2/OVERLAP.json`).
- The hidden-burst results above (G3, G4 for H3; G5 for H4) are therefore conditional on independence from H2.
- `re2_contamination.py` is frozen and runs only after "Open the RE1 seal". If either burst is contaminated, its conditions are relabelled "not independent of RE1", its claim is withdrawn, and the verdict is restated without them.

## Interpretation

- **Achieved, in a frozen evaluation on sealed data:**
  - E1T → learn → BP+OSD learned a sealed, never-seen large-footprint burst (H3) in 24/24 roots.
  - It matched the oracle's decoded error counts there, under R6's own base model and at p 0.00335.
  - That repairs, for H3, the failure that sank RE1 R6. RE1's own estimator, run alongside, still failed half the time.
- **Not achieved:** the pre-registered claim across all five gated conditions.
  - A single flagged root in G5 cost more than the 10-error floor allows.
  - The fallback design (flag → nominal) is safe at q = 0 but expensive at q > 0.
  - With 12 roots and an LER near 2e-4, one flag is enough to fail NI.
- **Post-hoc observations (untested; no endpoint is redefined):**
  - E1T's flag rate on sealed weight-3 bursts here was 1/36 roots.
  - Whether that flag was a false alarm is unknowable without opening the RE2 seal, and even then the class correctness of a flagged root was not recorded.
  - Whether a cheaper fallback than the nominal model (for example S\*) would have rescued G5 is a design question for a later study. It is not something to apply to these results.
- **Unchanged:** the 95% target is out of reach. Nothing here bears on d ≥ 7, hardware, X-bias or other burst weights.

## Claim boundary

- d=5, in simulation, on fresh seeds.
- G1–G4 support the pre-registered claim for K and sealed burst H3, conditional on H3's independence from H2.
- G5 does not support it for H4.
- The overall pre-registered claim is NOT_CONFIRMED.
- H3 and H4 stay sealed until the owner says "Open the RE2 seal". RE1's H2 stays sealed.
