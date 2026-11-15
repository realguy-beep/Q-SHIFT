# Correlated decoder V1.2 protocol

**Status:** prospective, single bounded development-only evaluation. It is not independent confirmation. It does not authorize Stage 5 access, sealed-data access or follow-up sampling. The evaluation runs only after the owner gives separate sign-off on the frozen commit.

This protocol supersedes `DESIGN_PLAN_DRAFT.md`, which is kept as the approved planning record. It implements that plan unchanged, except for the items listed under "Changes from the draft".

## Question

Does the frozen V1.1 five-factor representation beat the **best static** matching decoder on fresh data? And is any gain due to the representation or to per-root adaptation?

## Lineage

V1.1 (`codex/qshift-correlated-decoder-feasibility-v1-1`) is INCONCLUSIVE because of a finalization defect: the analyzer read `global_A_qhat` while the runner wrote `A_global_qhat`. Its descriptive results were recovered by the post-run audit at `c097bc116f62412cdf094c6285b92dff09ba985e`, and the analyzer defect is fixed at `8227f96bd8f9e6cc4d750382409996efff8264c8`. V1.1's arm A (PyMatching at pooled q̂ ≈ 0.0102) was not chosen to minimize LER. At q=0 it lost to per-root matching by 0.35 pp. V1.2 therefore adds a selected static baseline and a static five-factor arm.

## Fixed elements (unchanged from V1.1)

- **Circuit:** rotated distance-3 Z-memory, five rounds, p_gate = p_meas = 0.003. A synthetic `CORRELATED_ERROR(q) X8 X12 X15` follows each of the five MR boundaries. q ∈ {0, 0.01, 0.02}. These are synthetic common-cause events, not calibrated hardware noise.
- **Decoder source:** V1.1 `model.py` is imported unchanged. Its hash is checked against the V1.1 pretest freeze.
- **Estimator:** the V1.1 affine triple-cofire estimator. It is refit deterministically from the same 3,000 V1 training detector rows (observables are never read), and execution stops unless slope = 0.88 and intercept = 0.000667 within 1e-12.
- **Multi-prior evaluation:** five-factor arms share their 32 residual matching calls per shot (`multi_prior.py`). Tests pin each arm bit-for-bit to `BurstEnumerationDecoder.decode_one`.

## Arms

All seven arms decode identical detector rows per root. No decoder receives logical labels, and observables are inspected only after all seven predictions exist.

| Arm | Definition |
|---|---|
| A0 | PyMatching at q=0 (nominal; informational) |
| A | PyMatching at the pooled V1.2 calibration q̂ (V1.1 definition) |
| **Astar** | PyMatching at static q = **0.005** (selected; strong static baseline) |
| A2 | PyMatching at the per-root calibration q̂ |
| Bstatic | Five-factor at static q = **0.0025** (selected) |
| **B** | Five-factor at the per-root calibration q̂ (candidate) |
| C | Five-factor at the true q (privileged; not deployable) |

## Static selection (completed before any V1.2 sampling)

The selection set is the 30 committed V1.1 evaluation archives (60,000 shots). These are already-exposed development data, hash-verified, and unchanged before and after selection. The grid is {0, 0.0025, …, 0.02} plus V1.1's pooled q̂ (0.0101667). The criterion is the minimum equal-weight mean LER over the three conditions, with ties going to the smaller q. The rule was committed (`528b43371b8310bc14b8e96444f2cd9858fc7a19`) before selection ran. The result is in `STATIC_SELECTION.json`:
- matching (Astar): q = 0.005, 760 errors / 60,000;
- five-factor (Bstatic): q = 0.0025, 599 errors / 60,000.

As a consistency check, matching at the pooled q̂ gives 821 errors, which equals V1.1 arm A.

Both static values were chosen in-sample on the selection set. This makes the static baselines optimistic on that set; it is not a property of fresh data.

## Allocation (new shots)

| Partition | Roots | Shots/root | Shots | Sampler calls |
|---|---|---|---|---|
| Calibration (detector-only; observables discarded unread and never persisted) | 3 × 24 | 500 | 36,000 | 72 |
| Paired evaluation | 3 × 24 | 4,000 | 288,000 | 72 |
| **Total** | | | **324,000** | **144** |

Seeds come from the V1.2 namespace (146 identities: 72 calibration, 72 evaluation, 2 bootstrap streams). They are screened against the V1, V1.1 and performance-sprint inventories (205 values; 0 collisions). No Stage 5 or sealed metadata is accessed.

**Calibration gate:** if the mean per-root q̂ fails the strict order q=0 < q=0.01 < q=0.02, stop before the first evaluation sampler call. No model is built, no evaluation shot is drawn, and the result is INCONCLUSIVE.

## Endpoints and decision rule

Root-paired differences are computed per root as `LER(x) − LER(base)`, where negative favours x. The nonzero estimand is the equal-weight mean over q = 0.01 and 0.02. The bootstrap uses 20,000 root-stratified paired percentile replicates: within each q, roots are resampled with replacement, and the same resampling indices are used for every contrast. Quantiles use NumPy `linear`.

**Co-primary:** (1) B − Astar and (2) B − A2. This is an intersection-union test, so GO needs both and no multiplicity correction is applied.

**Zero-burst safety:** at q=0, the 5th and 95th percentiles of B − Astar from an independent bootstrap stream, compared against a tolerance of +0.0005.

- **GO (development only):** both co-primary 95% intervals lie entirely below 0; Astar has at least 100 errors pooled over nonzero q; B's point LER is below Astar's at both nonzero q; and the q=0 95th percentile is below +0.0005.
- **NO-GO:** the B − Astar interval is entirely at or above 0, or the q=0 5th percentile is above +0.0005.
- **INCONCLUSIVE:** everything else, including a calibration-gate failure, a runtime or resource stop, or incomplete evidence.

**Secondary (descriptive, no decision role):**
- Bstatic − Astar (representation alone);
- B − Bstatic (value of adaptation);
- B − A0, B − A, C − B;
- prediction disagreements;
- estimator bias and MAE.

**Interpretation boundary:** even a GO is development evidence for one synthetic three-qubit mechanism at d=3, with exact knowledge of the burst support. It is not hardware, scaling, real-time or independent-test evidence.

## Execution controls

- Every source, config, protocol, seed, selection and preflight file is hash-frozen in `PRETEST_FREEZE.json` (non-circular: the freeze excludes its own digest and the commit SHA).
- Launch is only `run_watchdog.py --execute --expected-head <SHA> --v1-repo <V1 worktree>`. It requires the exact commit, a clean tree on `codex/qshift-correlated-decoder-v1-2`, the pinned environment, matching V1 reuse verification, the estimator refit, and a PASS preflight.
- The runner refuses an existing run directory and never resumes, retries or substitutes seeds. Partial evidence is preserved on failure.
- Limits:
  - 1,800 s wall time, enforced by the watchdog's process-tree kill and by the in-process guard;
  - sampled RSS of 2 GiB;
  - at least 1 GiB free disk;
  - 256 MiB of run artifacts.

  The preflight projection was 632 s against a required maximum of 1,080 s.
- **Rehearsal:** `rehearsal.py` drives the identical `run_pipeline` code through runner, analyzer and manifest with a deterministic fake sampler, at 24 roots × 40 eval / 200 calibration shots. Tests confirm that every key the analyzer requires is written, that re-analysis is identical and non-mutating, that the V1.1 key defect class fails before any output, and that the calibration gate stops before evaluation.

## Changes and clarifications relative to the draft

1. **Change (engineering):** the analyzer accepts a `completed` run for non-mutating re-analysis to a separate output directory. The rehearsal tests showed this gap; it enables an independent post-run check with the same code. Decision rules are unaffected.
2. **Clarification:** V1's calibration arrays are not reused. Only V1 *training* detector rows are reused, to refit the frozen estimator. All V1.2 calibration batches are freshly sampled and detector-only, as in the draft's allocation.
