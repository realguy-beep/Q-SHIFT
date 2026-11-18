# Roadmap step 2 / H-E1: mismatch-robust burst-support learning (pre-registered)

**Authorization:** the owner said "Run H-E1 test" on 2026-11-18.

**Commit order:** this protocol and `he1.py` are committed before the full run.

**Disclosed peek.** A smoke test ran before this commit:
- p̂ was computed on 8 pools.
- The robust arm was run on **one** pool, Mlo burst 00. It selected the correct class, with the correct flip.

No parameter was changed after the smoke test. The trim of 0.2, the p grid and τ were fixed beforehand: the trim is the `adaptive/estimation.py` default, and τ is Phase C's.

## Question

The Phase C learner assumes the base noise model. Can it be made robust by first estimating a scalar background p from the pool's own **unlabeled** detector rows, then re-basing the learner on that estimate?

Three mismatches are tested, where Phase C failed completely in development:
- **Mlo:** true p = 0.0025. Phase C learned 0/24 burst pools.
- **Mhi:** true p = 0.0035. Phase C falsely accepted 24/24 burst-free pools.
- **Mz:** Z-bias 10. Phase C learned 0/24.

## Data (development only; no sampling)

| Set | Pools | Source |
|---|---|---|
| Mlo, Mhi, Mz | 24 burst pools (4,000 detector rows + 500 labeled rows per q) + 24 burst-free pools of 12,000 rows, per condition | `qshift_d5_model_mismatch_v1/work/diag_arrays` (Phase A) |
| CTRL, matched model | 24 SC burst pools (the known support (23, 31, 34)) + 24 Q0 burst-free pools at the nominal p = 0.003 | `qshift_d5_learned_support_v1/work/b2_dev/arrays` (Phase B2 development) |

**Not read:** Phase C evaluation archives and sealed material.

## Arms

- **N, nominal (Phase C unchanged):** `FastParityLearner` on the nominal base DEM (p = 0.003, balanced), τ = 1,561.218. The flip stage is `learn_flip` at the nominal spec.
- **R, robust:**
  1. Compute p̂: the root in log p of the trimmed mean (trim 0.2) of log(observed single-detector rate) − log(base-DEM rate at p). Use a 61-point geometric grid over 0.0012–0.0075 with linear interpolation.
  2. Use only the pool's **unlabeled** detector rows (for burst pools, the 12,000 detector rows; labeled rows are not used).
  3. Run the same learner and flip stage on the balanced base DEM at p̂. τ is unchanged.
  4. For Mz the balanced model is misspecified by design: one scalar cannot represent the bias.

**Identity check.** Arm N must reproduce every recorded Phase A selection (class and Δ) for Mlo, Mhi and Mz. If it doesn't, the run is INVALID.

## Decision rule (fixed)

**Per mismatch condition (arm R):**
- **PASS** requires both:
  - class correct in ≥ 20/24 burst pools;
  - false accepts in ≤ 1/24 burst-free pools.
- **FAIL** otherwise.

**Control (arm R on CTRL):**
- **CONTROL_OK** requires both:
  - class correct ≥ (arm N's control count − 2);
  - false accepts ≤ 1/24.
- **CONTROL_DEGRADED** otherwise.

**Overall:**
- **H-E1_SUPPORTED:** all three conditions PASS and the control is OK.
- **H-E1_PARTIAL:** at least one PASS and the control is OK.
- **H-E1_NOT_SUPPORTED:** otherwise.

**Also reported, not gated:**
- learned-correct counts (class plus flip);
- p̂ mean and SD against the true p;
- arm N's numbers;
- the largest burst-free Δ.

**Scope.** This is development evidence about the learner only. A PASS would justify a fresh-seed validation screen and an end-to-end decode check. It is not a confirmatory robustness claim.

## Execution

- `python he1.py run --workers 8` runs 192 write-once pool records into `results/he1/pools`.
- `python he1.py analyze` writes `results/he1/HE1.json`.
- Expected about 10–20 min.
