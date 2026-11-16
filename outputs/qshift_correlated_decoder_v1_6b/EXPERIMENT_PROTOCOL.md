# Correlated decoder V1.6b protocol

**Status:** prospective, single bounded development-only evaluation on **fresh seeds**. It is not independent confirmation. The run needs the owner's separate sign-off on the frozen commit.

This protocol implements `outputs/qshift_correlated_decoder_v1_6/DESIGN_PLAN_V1_6B_DRAFT.md`, which the owner approved. Its development gate **passed** (`d3d326df9`): device class 72/72, no-burst 23/24, flip 72/72.

## Question

When the burst's detector signature, rate and logical effect are **learned** from device calibration data instead of given (oracle support), does the exact DEM decoder (**Blearn**) still beat the strongest matching decoders? And does it stay within 0.05 pp of the same decoder given the true support?

## Fixed elements

- **Circuit:** rotated d=3 Z-memory, five rounds, p = 0.003, built with `model_v14.py` (pinned to V1.1 at d=3).
- **Burst conditions:** each condition applies `CORRELATED_ERROR(q) X<support>` after each MR, with q ∈ {0, 0.01, 0.02}.
  - **known:** support (8, 12, 15).
  - **hidden:** the support sealed before any learner code existed (commitment SHA-256 `caa9fd07…`, commit `23c0e219b`). Its plaintext is opened **only inside the frozen run**, after all gates pass, and is verified against the hash.
- **Learner:** `outputs/qshift_correlated_decoder_v1_6/learner.py`, unchanged since `304767972`. A test pins its bytes.
  - Stage 1 is a detector-only parity-moment class selection over the 15 signature classes, with Bonferroni χ² threshold 11.58.
  - Stage 2 learns the logical bit by exact joint likelihood on a labeled device partition.
- **Exact decoder:** V1.4B `mld.py`. Static settings come from V1.3: matching q = 0.00375, five-factor q = 0.01125.

## Per condition: partitions (fresh seeds)

1. **Device detector-only partition:** 4,000 rows per q (12,000 in total); observables are discarded unread. This trains Stage 1.
2. **Device labeled partition:** 500 rows per q (1,500 in total). Labels are read for the Stage 2 flip bit only.
3. **Per root** (3 × 24): 500 detector-only calibration rows give the per-root q̂ via the parity fit restricted to the class. That is the learned class for learned arms and the true class for oracle arms.
4. **Per root:** 4,000 paired evaluation rows. Observables are read only after all six predictions exist.

In total: 675,000 new shots in 300 sampler calls, with 304 seeds screened against 697 prior values (0 collisions).

## Arms

| Arm | Definition |
|---|---|
| A_nominal | PyMatching, base DEM, correlations OFF (no burst knowledge) |
| Astar_oracle | static correlated PyMatching, q = 0.00375, **true** support |
| Astar_learned | the same with the **learned** support (base DEM if none learned) |
| BoffStatic_oracle | V1.3 cost-consistent five-factor, q = 0.01125, **true** support |
| Bexact_oracle | exact DEM decoder, **true** support, per-root q̂ |
| **Blearn** | exact DEM decoder, **learned** support and flip, per-root q̂ (candidate) |

## Endpoints

Statistics are root-paired differences, equal-weight over q ∈ {0.01, 0.02}. The bootstrap uses 20,000 root-stratified replicates per condition, with condition-specific seeds and NumPy `linear` quantiles.

**Known-burst condition:**
- **Co-primary** (intersection-union): Blearn − Astar_oracle and Blearn − Astar_learned. Each 95% CI must lie entirely below 0.
- **Oracle gap:** Blearn − Bexact_oracle, with the 95% upper bound below +0.0005 (non-inferiority at 0.05 pp).
- **Safety:** q=0 Blearn − Astar_oracle, with a 95th percentile below +0.0005. Astar_oracle must have at least 100 nonzero errors.
- **Target:** 1 − LER(Blearn)/LER(Astar_oracle), with a 95% lower bound of at least 0.40 → **TARGET_MET**. If any bootstrap replicate has zero comparator errors, the interval is reported as unbounded and the target is not met.

**Hidden-burst condition** (robustness):
- Blearn − Bexact_oracle has a 95% upper bound below +0.0005;
- Blearn − Astar_learned has a 95% upper bound of at most 0;
- learned class and flip correctness are reported.

**Decision:**
- **GO (development only):** every known-burst endpoint and every hidden-burst endpoint above holds.
- **NO-GO:** the known Blearn − Astar_oracle CI lies entirely at or above 0, or the known q=0 5th percentile is above +0.0005.
- **INCONCLUSIVE:** everything else, including incomplete evidence.

**Secondary (descriptive):** Blearn − BoffStatic_oracle, Blearn − A_nominal, Bexact_oracle − Astar_oracle, and Astar_learned − Astar_oracle, for each condition.

## Interpretation boundary

The hypothesis space (X-bursts on at most 3 data qubits, one per round boundary) is given to the learner. Learning the logical bit needs labeled device data, which detectors alone can't provide; a sampler-free enumeration in V1.6 showed this. Blearn is exact only for the DEM. The study covers d=3 only and two synthetic bursts. It is not hardware, scaling or independent-test evidence.

## Execution controls

- The V1.5 structure is kept:
  - a non-circular LF hash freeze, covering the package, the learner, the hidden-burst commitment and seal script, the gate records, `model_v14`, `mld` and the V1.3 settings;
  - an exact `--expected-head` on a clean `codex/qshift-correlated-decoder-v1-6`;
  - the pinned environment and a PASS preflight;
  - the Windows watchdog, a single attempt, and no resume, retry or seed substitution.
- **Limits:** 18,000 s wall time; the preflight projected 4,990 s, within the required maximum of 10,800 s. Also 2 GiB RSS, at least 1 GiB free disk and 256 MiB of artifacts.
- **Rehearsal** uses a decoy hidden support (X1 X12), never the sealed one.
- **Post-run:** an identical re-analysis to a separate directory, plus the frozen NumPy-only `recount_from_scratch.py`.
