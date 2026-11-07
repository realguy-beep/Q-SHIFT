# Limitations

- This is a development feasibility pilot. It does not confirm performance on an untouched confirmatory experiment.
- The custom categorical `PAULI_CHANNEL_1/2` simulator is sampled directly by Stim, but DEM construction uses `approximate_disjoint_errors=True`. The four arms share the same approximate DEM within each model; this experiment isolates use of decomposition correlation metadata, not information loss from DEM conversion.
- PyMatching’s correlated option uses correlations represented by the decomposed DEM. It cannot reconstruct categorical event dependencies that the conversion omitted.
- Only distance 3 and five rounds are tested here; conclusions do not transfer automatically to other distances, rounds, or circuit schedules.
- The noise channels are controlled stochastic Pauli settings. No coherent noise, leakage, inter-gate crosstalk, long-range bursts, within-circuit drift, or device-calibrated parameters are included.
- Twelve independent roots per condition provide limited seed-level resolution. The confidence interval and root-level variability should be emphasized over shot-count-only significance.
- Regime-informed decoders receive the hidden simulated condition and are diagnostic references, not deployable policies.
- Runtime is local CPU software timing. No hard real-time or hardware compatibility claim is supported.
