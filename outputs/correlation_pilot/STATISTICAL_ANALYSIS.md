# Statistical analysis

## Primary pooled-fixed paired comparison

- Difference, correlated minus uncorrelated: -0.0002541667 LER (-0.025417 percentage points).
- Regime-stratified root-cluster bootstrap 95% interval: [-0.0003500000, -0.0001625000].
- Two-sided paired root-cluster sign-flip p=0.0008399916001 using 100,000 assignments and add-one correction; 83 assignments were at least as extreme.
- Descriptive exact paired-shot McNemar p=6.570520814e-07.
- Root wins/losses/ties by stratum are in `PER_STRATUM_RESULTS.csv`; primary shot-level discordances are 763 standard-only vs 580 correlation-aware-only failures.
- Root clusters, not individual shots, are the independent units for the primary uncertainty and test.

## Resampling and secondary family

The primary bootstrap resamples roots within each of six strata and applies the same root indices to the paired arms. The primary estimand is the equal-weight mean of the six stratum means. Secondary comparisons are the 12 exact root-level sign-flip tests of regime-informed minus the corresponding pooled fixed arm, separately for correlation off/on, with Holm adjustment across all 12. These are privileged regime-information diagnostics, not deployable policies.

## Runtime and memory

- Decoder construction: 0.0387 s.
- Stim sampling: 0.1143 s.
- Decode time by arm: `{"pooled_fixed_uncorrelated": 0.22752090000358294, "pooled_fixed_correlated": 0.6424155999848153, "regime_informed_uncorrelated": 0.21209520001502824, "regime_informed_correlated": 0.6042506999910984}`.
- Sampling/decode loop wall time: 3.0455 s.
- Process RSS at start / after model build / sampled peak: None / None / None bytes.
- Process memory includes Python and native allocations; the peak is observed between root batches and is not an isolated PyMatching measurement.
