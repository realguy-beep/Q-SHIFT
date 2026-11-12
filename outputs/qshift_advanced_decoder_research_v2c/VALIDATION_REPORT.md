# Phase 2C deterministic validation report

## Execution record

Reproduction command: `python outputs/qshift_advanced_decoder_research_v2c/joint_estimator_comparison.py` from repository root. Inputs are the current circuit builder, Phase 2B deterministic signature/expectation routines, and the existing `DetectorProfileEstimator` specification. Software versions and reviewed checkpoint are recorded in `SOURCE_MANIFEST.json` and `comparison_results.json`. The routine calls no sampler, RNG, decoder, trainer, logical label, seed source, or protected data.

## Independent deterministic checks

1. **Expectation algebra:** parity-character means were checked against direct categorical XOR-state convolution at nominal `(.008,.003)`, mismatch `(.008,.006)`, and two boundaries. Maximum absolute differences ranged from **1.98×10⁻¹⁴ to 2.02×10⁻¹⁴**.
2. **Interpolation:** all 231 lattice nodes reproduce their stored template means exactly. At 200 deterministic half-cell points, maximum absolute feature error was **4.870×10⁻⁶**, maximum vector RMS **1.284×10⁻⁶**, for the exact circuit; the DEM values were essentially the same.
3. **GLS arithmetic:** the final analysis independently recomputes a nonzero exact-circuit-truth / DEM-template mismatch residual quadratic using `rᵀWr` and a direct linear solve of the regularized DEM reference covariance. The weight-product score was **2.9665532386521275×10⁻⁷** and the direct-solve score **2.9665532386521285×10⁻⁷**, absolute difference **1.06×10⁻²²**; the script asserts difference below `1e-10`.
4. **Finite-difference and grids:** the bilinear exact-circuit and DEM template surfaces have rank two at every one of 231 nodes; maximum raw conditions were about **4.2182**. This describes the interpolants and is a finite-grid screen, not an exact continuum derivative or proof over the continuum.
5. **Source/hash integrity:** historical inputs and source files are hashed in the manifest. Output JSON is parsed and all recorded hashes are independently rechecked before commit.

The algebraic reference shares deterministic fault masks with the primary character calculation and therefore does not independently validate Stim compilation or the circuit specification. Direct linear solve verifies the GLS weighting arithmetic but does not validate an empirical covariance estimate. No stochastic validation was requested or performed.

## Arithmetic checks

- Phase 2B nominal exact-circuit vs DEM difference: max **3.27196×10⁻⁵**, RMS **2.13601×10⁻⁵**; current 231-node audit maximum max-gap **3.31158×10⁻⁵**, pooled node-feature RMS **2.11686×10⁻⁵**.
- Fixed-`p_m` burst projection at mismatch: `.008 → .0109` on the `.0001` fit grid; bias `+.0029`. The finer Phase 2B scalar minimizer `.01091` is consistent with the coarser Phase 2C search.
- Fixed-reference covariance condition number **26.744**; 45/45 positive eigenvalues; ridge `7.83×10⁻⁸` is lower than minimum eigenvalue `.00293` and has no effect at this reference.
- Delta-method standard errors and guard statistics are analytical approximations only. They are not intervals, formal power, or observed finite-sample performance.

## Privacy and preservation checks

Before publication, scan only new Phase 2C deliverables for absolute machine paths, email addresses, credential patterns and unexpected large files; verify manifest SHA-256 values; ensure staged paths are exclusively under `outputs/qshift_advanced_decoder_research_v2c/`; and confirm the parent commit remains `7597510a41be09b6b9c727e7ae6091627011424f`. Phase 1, Phase 2, Phase 2A, Phase 2B, V2.4 and historical source files remain unchanged. No Stage 5 material or protected seed inventory was accessed. PR #1 is not modified.
