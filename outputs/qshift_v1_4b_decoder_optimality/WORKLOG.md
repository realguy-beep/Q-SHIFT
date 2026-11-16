# V1.4B work log

Branch `codex/qshift-v1-4b-decoder-optimality`, from `e2ffab43f` (the V1.4 gate record). Frozen V1.3 and V1.4 artifacts are read, never written.

## 2026-11-16

1. Checked existing tooling. The `beliefmatching`, `ldpc`, `hamld`, `sinter`, `numba` and `quimb` packages are not installed. Prior NS-series work audited the HAMLD source (approximate MLD) and BeliefMatching, but neither is available here, and no exact maximum-likelihood decoder exists in the repo.
2. Measured the V1.1/V1.3 d=3 DEM (non-decomposed, approximate-disjoint): 448 mechanisms at q>0 (443 at q=0), 40 detectors, maximum detector span 11, and a maximum open elimination width of **11**.
3. Implemented `mld.py`, exact logical-class inference by variable elimination in detector order.
   - Tests check exact equality against brute-force enumeration over every syndrome of 6 random DEMs (1e-12), exact merging of duplicate signatures, width = 11 on the real DEM, and correct trivial-class decoding of pure burst syndromes.
   - A bit-axis-flip formulation gives identical results at 6.5 ms/shot (batch 256), compared with 15 ms/shot for index permutation.
4. Single-root timing look (disclosed in `PREREGISTRATION.md`). On V1.3 `eval_q2_r00`: R_true 25 errors, Boff 33, BoffStatic 33, Astar 69, out of 4,000.
5. Committed `PREREGISTRATION.md` before computing any screen statistic.
6. Ran `screen_decode.py S1` (8 processes; about 19 ms/shot per exact decode under contention). Ran `analyze_screen.py S1`, with these pre-registered results:
   - best-V1.3 = BoffStatic, at 0.725% nonzero.
   - R_true: 0.556%, a 23.3% reduction, so the headroom check **passes**.
   - **B** (exact at q̂): 0.553%, a 23.7% reduction, CI [−0.200, −0.144] pp. At q=0: 361 errors vs Boff's 481. That meets S1 criteria 1–4, with S2 pending.
   - **A** (mask marginalization): identical predictions to Boff on all 288,000 shots, so 0% improvement.
   - R_zero (burst-blind exact): 7.05%.
7. Residual taxonomy (S1, nonzero q, Boff vs R_true):
   - 551 recoverable and 859 inherent failures, plus 209 shots where Boff is right and R_true wrong.
   - Only 118 of the 551 recoverable failures change when bursts are removed from the exact model, so about 79% of the gap is background inference: degeneracy and hyperedge splitting. At q=0, all 186 recoverable failures are background-only.
   - Candidate A's null result confirms that how masks are combined is not the bottleneck.
8. Edited `screen_decode.py` (after S1 had finished loading) to recompute Boff and BoffStatic for S2, whose V1.2 archives predate those arms. The S1 code path is unchanged.
9. **Candidate C specified here, before any C screen statistic.** C is "five-factor with correlated-consistent residual cost":
   - Same 32-mask enumeration and burst log-odds as Boff, with per-root q̂.
   - Each mask's background cost and prediction come from one `Matching.decode(residual, return_weight=True, enable_correlations=True)`. The weight is PyMatching's correlation-reweighted solution weight, so edge selection and cost agree under the correlated model. A check on 300 S1 rows found it below the uncorrelated minimum in 11% of rows and never above it.
   - The q̂=0 path uses the same correlated decode.
   - Motivation: the residual is background-dominated and hyperedge-related, and correlation reweighting is PyMatching's scalable hyperedge approximation. C is evaluated against the same pre-registered thresholds.
