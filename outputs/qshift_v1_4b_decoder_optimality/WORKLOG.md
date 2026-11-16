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
