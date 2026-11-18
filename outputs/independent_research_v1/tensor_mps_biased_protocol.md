# Fixed-bond tensor MPS under biased code-capacity noise

## Question

The fixed-chi=16 qecsim planar MPS screen improved over qecsim MWPM at d3/d5 under IID depolarizing code-capacity noise. Test whether that direction persists under a noise bias aligned with Q-SHIFT's Pauli-bias family, using the same model and syndrome for both decoders.

## Fixed model and comparison

Use `PlanarCode(d,d)` at d=3 and d=5, perfect syndrome extraction, code-capacity error probability p=.05, and `qecsim.models.generic.BiasedDepolarizingErrorModel(bias=5, axis='X')`. qecsim defines the bias as axis probability divided by each off-axis probability equal to 2*bias; bias=5 therefore gives the Q-SHIFT 10:1:1 nonidentity X:Y:Z ratio. This is a single-data-qubit code-capacity model, not the repeated-measurement circuit channel.

Compare `PlanarMPSDecoder(chi=16, mode='c')` with `PlanarMWPMDecoder()` using the same sampled Pauli error and perfect syndrome. Pass the identical error-model object and p to each decoder. Verify both recoveries return to the codespace and score the same logical observables. χ and mode are frozen from the prior screen; do not tune them.

Use 5,000 paired samples per distance, NumPy RNG seeds 2026113311 (d3) and 2026113312 (d5); preflight uses 100 samples/each at 2026113301/3302. Report per-arm LER/Wilson intervals, paired delta and normal interval, discordant errors/McNemar, valid-recovery count, runtime per decode, and peak RSS. Advancement requires MPS LER below bias-aware MWPM at both distances with the paired 95% interval below zero at both; this is only a code-capacity screening gate.

## Stop and interpretation

Stop before main if either decoder fails validity or if preflight projects more than 300 seconds. Do not use these results to claim Q-SHIFT circuit-level performance: measurement faults, repeated syndrome extraction, categorical two-qubit pair correlations, and spacetime decoding are absent. No confirmatory data or Q-SHIFT circuit shots are generated.
