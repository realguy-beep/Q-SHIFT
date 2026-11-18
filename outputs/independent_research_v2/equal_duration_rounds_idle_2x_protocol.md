# Twofold idle-noise robustness challenge

## Hypothesis and fixed intervention

The equal-duration result may depend on the assumed data-idle channel. Stress it by doubling only the idle Pauli-channel probability from .003 to .006 per idle cycle, retaining the same X/Z axis bias ratio of 10. Keep the five-active-round comparator at its original source p_gate=p_measure=.003. This is a one-point robustness challenge, not a sweep or retuning exercise.

Use the same aligned d3 X/X-bias and Z/Z-bias conditions, same two idle cycles and 9 data qubits, same per-arm approximate-DEM correlation-enabled PyMatching decoder, and 500,000 fresh shots/arm/condition. Main seeds 2026113911–2026113914; preflight seeds 2026113901–2026113904. Report per-cell LER, independent-sample rate ratios and 95% intervals, and equal-weight mean cell ratio.

Robustness is retained only if both cell point estimates remain below 1 and macro RR <=.90 with no cell above 1.05. This tests simulator sensitivity to a declared idle-rate uncertainty. It does not make p=.006 hardware-calibrated or authorize further idle-factor search.

Stop on any circuit/readout/noiseless/decoder-integrity failure or a projected runtime above 300 seconds. No sealed or confirmatory data are in scope.
