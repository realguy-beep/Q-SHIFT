# Correlated decoder V1.5 protocol

**Status:** prospective, single bounded development-only evaluation on **fresh seeds**. It is not independent confirmation. It does not authorize Stage 5 access, sealed-data access or follow-up sampling. The run needs the owner's separate sign-off on the frozen commit.

## Question

On fresh data: does the exact DEM logical-class (maximum-likelihood) decoder at per-root, detector-only q̂ (**Bexact**, V1.4B candidate B) beat the best V1.3 decoder (BoffStatic) and the strongest static matcher (Astar)?

## Lineage

- **V1.3** (`bd43689e`): GO, with Boff and BoffStatic at 47% below Astar.
- **V1.4 gate:** no burst-dominated regime qualified (stop rule).
- **V1.4B** (`1eff83c35`): the development screen on already-exposed V1.3 and V1.2 arrays. Bexact was 23.7% and 24.3% below BoffStatic, with CIs excluding 0, and better at q=0. It sat essentially at the DEM-exact ceiling. Mask marginalization had no effect, and the correlated-consistent cost was worse.
- **This run:** V1.5 tests whether that holds on data neither screen saw.

## Fixed elements (nothing new is selected in V1.5)

- **Circuit and noise:** as V1.1–V1.3. Rotated d=3 Z-memory, five rounds, p = 0.003, `CORRELATED_ERROR(q) X8 X12 X15` after each MR, q ∈ {0, 0.01, 0.02}. V1.1 `model.py` is imported unchanged.
- **Estimator:** the frozen V1.1 estimator, refit from 3,000 V1 training detector rows (slope 0.88, intercept 0.000667 within 1e-12).
- **Baseline settings:** read from V1.3's hash-frozen `STATIC_SELECTION.json`. Astar is correlated, q=0.00375; A2sw has τ=0.0005; BoffStatic has q=0.01125. A test pins these values and the file hash.
- **Decoders:**
  - V1.3's `multi_prior.ModeAwareFiveFactor` (correlations OFF), imported unchanged, for Boff and BoffStatic;
  - V1.4B's `mld.ExactLogicalDecoder`, imported unchanged and hash-frozen, for Bexact. It runs on the non-decomposed DEM with `approximate_disjoint_errors=True` at each root's q̂, using the base DEM when q̂ = 0.

## Arms

All five arms decode identical rows. Observables are read only after every prediction exists.

| Arm | Definition |
|---|---|
| Astar | Static correlated PyMatching, q=0.00375 |
| A2sw | Mode-switching PyMatching, τ=0.0005 |
| Boff | V1.3 cost-consistent five-factor, per-root q̂ |
| **BoffStatic** | V1.3 cost-consistent five-factor, q=0.01125 (best V1.3; **reference**) |
| **Bexact** | Exact DEM logical-class decoder at per-root q̂ (**candidate**) |

## Allocation

The same as V1.3:
- 3 × 24 roots;
- 500 detector-only calibration shots per root, with observables discarded unread;
- 4,000 paired evaluation shots per root.

That is 324,000 new shots in 144 calls. There are 146 seeds in the V1.5 namespace, screened against V1, V1.1, V1.2, V1.3, the V1.4 gate and the performance sprint (551 values, 0 collisions). The calibration-order gate is as in V1.3.

## Endpoints and decision rule

Statistics are root-paired differences, equal-weight over q ∈ {0.01, 0.02}. The bootstrap uses 20,000 root-stratified replicates, with shared indices across contrasts and NumPy `linear` quantiles.

**Co-primary:** (1) Bexact − BoffStatic and (2) Bexact − Astar. This is intersection-union: GO needs both.

**Safety:** at q=0, Bexact − BoffStatic from an independent bootstrap stream, against a tolerance of +0.0005.

- **GO (development only):**
  - both co-primary 95% CIs lie entirely below 0;
  - BoffStatic has at least 100 nonzero errors;
  - Bexact's point LER is below BoffStatic's at both nonzero q;
  - the q=0 95th percentile is below +0.0005.
- **NO-GO:** the Bexact − BoffStatic CI is entirely at or above 0, or the q=0 5th percentile is above +0.0005.
- **INCONCLUSIVE:** everything else, including a gate, resource or finalization failure.

**Target endpoint** (pre-registered, reported alongside the decision and never replacing it): R = 1 − LER(Bexact)/LER(BoffStatic), equal-weight nonzero, using the same bootstrap indices.
- **TARGET_MET** if the 95% lower bound of R is at least **0.10**;
- otherwise **TARGET_NOT_MET**.

**Secondary (descriptive):** Bexact − Boff, Bexact − A2sw, BoffStatic − Astar, Boff − Astar. Relative reductions are reported vs BoffStatic, Astar and A2sw.

**Post-run descriptive (not an endpoint):** `posthoc_reference.py` computes the privileged true-q exact reference R_true on the saved arrays and reports Bexact − R_true, which shows the distance from the DEM-exact ceiling.

## Interpretation boundary

Even a GO and TARGET_MET is development evidence for:
- one synthetic mechanism;
- d=3 only (exact elimination width 11; it is intractable at d≥5 in this form);
- oracle burst support;
- exactness only at the DEM level (two-qubit channels approximated as independent).

It is not hardware, scaling, latency or independent-test evidence.

## Execution controls

- The V1.3 machinery is unchanged in structure:
  - a non-circular LF hash freeze, which also covers V1.3, V1.4 and V1.4B dependencies;
  - an exact `--expected-head` on a clean `codex/qshift-correlated-decoder-v1-5`;
  - the pinned environment, V1 reuse verification and estimator refit;
  - a PASS preflight;
  - the Windows watchdog and a single attempt with no resume, retry or seed substitution.
- **Limits:** 9,000 s wall time, 2 GiB sampled RSS, at least 1 GiB free disk, 256 MiB of artifacts. The preflight projection must be at or below 60% of the cap.
- **Rehearsal:** the fake-sampler rehearsal drives the same `run_pipeline`. A test re-decodes rehearsal roots with an independent `ExactLogicalDecoder` and matches the saved Bexact predictions.
- **Post-run:** `recount_from_scratch.py`, frozen and NumPy-only, plus an identical re-analysis to a separate directory.
