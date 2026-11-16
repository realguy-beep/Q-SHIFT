# Correlated decoder V1.6b: device-level learned burst support (DRAFT, not frozen)

**Status:** planning draft for owner review. No V1.6b code, seeds, freeze or sampling yet. Nothing here authorizes execution.

## Why V1.6b

The V1.6 development gate **failed G1**: 76.4% class accuracy against the 95% required. With only 500 detector-only rows per root, the signature isn't identifiable at q = 0.01; at q = 0.02 the learner was perfect. The other two stages held:
- the labeled logical-effect stage was 100% correct (75/75);
- "no burst" at q=0 was 98.6% correct.

A reported-only diagnostic found the pooled learner (36,000 rows) correct in 3/3 studies. **That pooled look is disclosed here as prior exposure.** V1.6b does not re-test on the data that produced it.

**Design change (the only one):** the burst support is a property of the device, so it is learned **once per device** from a pooled calibration partition. Per root, only the rate q̂ is estimated. The learner algorithm, the 15-class hypothesis space, the χ² threshold and the labeled-flip stage are unchanged from V1.6 (`learner.py` at `304767972`).

## Device-level learner

1. **Device signature**, detector-only: `ParityLearner.select` on a pooled device-calibration partition of N_dev = 12,000 rows, drawn as an equal mixture of the operating conditions (q ∈ {0, 0.01, 0.02}). Same Bonferroni χ² threshold (11.58).
2. **Device logical effect**, labeled: `learn_flip` on a separate pooled labeled partition of N_lab = 1,500 rows (same mixture), at the device-level q̂.
3. **Per-root rate:** the parity fit restricted to the learned class, on that root's 500 detector-only calibration rows (no threshold; clipped to [0, 0.02]).

**Blearn** is the exact DEM decoder (V1.4B `mld.py`) with the learned mechanism added at per-root q̂. If no burst is learned, Blearn is the exact base-DEM decoder.

## V1.6b development gate (pre-registered before any statistic)

**Data:** the detector arrays of the already-exposed V1.2, V1.3 and V1.5 *evaluation* archives (3 × 288,000 rows), with the known burst only. These rows were **never used for signature learning** in V1.6 (which used calibration archives). The flip stage uses their labels, as before.

**Procedure:** for each study, draw 24 disjoint pooled subsamples of N_dev = 12,000 (equal q mixture) and 24 disjoint labeled subsamples of N_lab = 1,500. Seeds are fixed in advance.

| Criterion | Requirement |
|---|---|
| **G1′** device class correct | ≥ 95% of the 72 pooled subsamples |
| **G2′** "no burst" on q=0-only pooled subsamples (N = 12,000, 24 per study) | ≥ 90% of 72 |
| **G3′** device flip correct (given a correct class) | ≥ 95% |

Reported only:
- a learning curve of class accuracy vs N_dev ∈ {1,500, 3,000, 6,000, 12,000, 24,000};
- per-root q̂ bias and MAE using the device class;
- learner cost.

**Outcome rule:** PASS lets the frozen V1.6b evaluation be built, with separate sign-off. FAIL means STOP, report, and no further redesign under this name.

## Frozen V1.6b evaluation (separate sign-off)

**Burst conditions:**
- **known** (X8 X12 X15), which is V1.5-comparable;
- **hidden**: the sealed V1.6 support (commitment `caa9fd07…`). It is opened only inside the run, after the freeze, and the run verifies the hash.

Each condition uses q ∈ {0, 0.01, 0.02}.

**Per condition, the device partitions are** 12,000 detector-only + 1,500 labeled rows (fresh seeds). **Per root:** 500 detector-only calibration rows + 4,000 paired evaluation rows, with 3 × 24 roots.

**Arms.** "Oracle" means the arm is given the true support; it is not deployable without that knowledge.

| Arm | Information used | Role |
|---|---|---|
| A_nominal | base DEM only (best mode, fixed in advance: correlations OFF, q=0) | no-knowledge matching |
| Astar_oracle | V1.3 static correlated matching, q = 0.00375, true support | strongest matcher (oracle) |
| Astar_learned | same, with the *learned* support | strongest matcher, same information as Blearn |
| BoffStatic_oracle | V1.3 five-factor, q = 0.01125, true support | best V1.3 decoder (oracle) |
| Bexact_oracle | V1.5 exact decoder, true support, per-root q̂ | oracle-support ceiling |
| **Blearn** | exact decoder, **learned** support, flip and per-root q̂ | **candidate** |

For the hidden condition, the static q values are reused unchanged from the known-burst selection, because no selection on hidden data is possible without peeking.

**Endpoints, known-burst condition** (equal-weight nonzero; root-paired bootstrap; intersection-union):
- **Co-primary:** (1) Blearn − Astar_oracle and (2) Blearn − Astar_learned. Each 95% CI must be entirely below 0.
- **Oracle gap:** Blearn − Bexact_oracle is non-inferior at a margin of +0.05 pp (upper 95% bound below +0.0005).
- **Target:** the relative reduction of Blearn vs Astar_oracle, with a 95% lower bound of at least 0.40.
- **Safety:** at q = 0, Blearn − Astar_oracle has a 95th percentile below +0.0005.

**Endpoints, hidden-burst condition** (robustness; may be benign for matching):
- Blearn is non-inferior to Bexact_oracle (margin +0.05 pp);
- Blearn − Astar_learned has an upper bound ≤ 0, so it is not worse;
- device class and flip correct (reported).

**Decision:** GO requires the known-burst co-primary endpoints and the oracle-gap test, plus the hidden-burst non-inferiority endpoints. The target is reported separately as TARGET_MET or TARGET_NOT_MET.

**Allocation:** 2 conditions × (13,500 device rows + 72 × 4,500 root rows) = **675,000 new shots**.

**Runtime:** two exact arms × about 1,650 s × 2 conditions, plus five-factor and matching, comes to about 2 h. The proposal is a cap of 5 h, with a preflight projection at or below 60% of it.

## Engineering

Reuse the V1.5 machinery (contract, run_pipeline, rehearsal, frozen recount, watchdog, LF freeze, single attempt). New pieces:
- a device-calibration phase in the pipeline;
- hidden-burst opening with hash verification;
- learned-arm construction;
- tests:
  - the rehearsal through the device phase with a fake sampler;
  - the commitment check (a fake sealed file must fail on a hash mismatch);
  - Blearn equal to Bexact_oracle whenever the learned class and flip are the true ones.

## Decisions for the owner

1. **Device-level design:** a pooled device calibration of 12,000 detector-only + 1,500 labeled rows per burst condition, with per-root q̂ only.
2. **Development gate:** run it on the unused-for-learning evaluation detectors of V1.2, V1.3 and V1.5, with G1′/G2′/G3′ as above.
3. **Comparators and endpoints:** oracle and learned matchers, the hidden-burst robustness endpoints, the 0.05 pp oracle-gap margin and the 40% target. About 675,000 new shots and a 5 h cap.
