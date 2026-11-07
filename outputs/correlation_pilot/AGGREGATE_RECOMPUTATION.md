# Independent raw-array recomputation

Status: **PASS**. This checker does not import `analyze_correlation_pilot.py` or the runner reporting functions.

- Coverage: 72 checkpoints; 720,000 paired shots.
- Decoder prediction bits independently checked: 2,880,000; mismatches: 0.
- Per-root reporting CSV rows independently checked against arrays: 72; mismatches: 0.
- Arm residual errors in order ['pooled_fixed_uncorrelated', 'pooled_fixed_correlated', 'regime_informed_uncorrelated', 'regime_informed_correlated']: [3532, 3349, 3372, 3720].
- Raw observable errors: 39,326.
- Primary delta (correlated minus uncorrelated): -0.0002541667 LER.
- Root-stratified 95% bootstrap CI: [-0.0003500000, -0.0001625000].
- Root-cluster sign-flip p: 0.0008399916001 (83/100,000 extreme assignments; add-one correction).
- Paired discordances: standard-only 763; correlation-only 580; total 1,343.
- Exact shot-level McNemar p (descriptive): 6.570520814e-07.

The numerical values agree with `RESULTS.json`. This is an independent reconstruction from saved test arrays and decoder predictions; the run remains a development pilot, and the DEM's disjoint-error approximation remains a modeling limitation.
