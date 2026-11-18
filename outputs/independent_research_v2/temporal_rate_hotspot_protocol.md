# Round-wise gate-rate heterogeneity screen

## Question and hypothesis

Does a matching graph calibrated to the exact round-wise gate-rate map lower logical failures versus a static graph calibrated to the same average gate rate, when two-qubit fault rates move through the circuit? This tests an oracle ceiling for temporal rate calibration. It does not test online estimation, change detection, or a device profile.

## Frozen design

- Use the d3, five-round Z-memory, X-biased ratio-10 Phase 2B circuit. Keep all one-qubit and measurement noise fixed at 0.003 and keep the full two-qubit Pauli-pair composition fixed.
- Modify only the total probability of each `PAULI_CHANNEL_2` event by round. Profile A uses factors `[0.25, 1.75, 1.0, 0.25, 1.75]`; profile B reverses the sequence. Each profile has mean factor 1.0 across five rounds, matching the pooled stationary model at gate p=0.003. The per-round map is known to the local decoder.
- Compare correlation-enabled PyMatching from the exact profile-specific approximate DEM against the pooled stationary p=0.003 graph. Both use Stim `decompose_errors=True`, `approximate_disjoint_errors=0.01`.
- Primary endpoint: paired LER difference (profile-specific minus pooled) for each reverse pair and their equal-weight macro. Report conditional paired confidence intervals, discordant counts and exact McNemar tests, absolute LERs, and decode time.
- Preflight: 100 samples/profile with seeds 2026113611 and 2026113612; verify five round groups, reversed factors, average factor 1, unchanged circuit shape and gate targets, DEM construction, deterministic noiseless circuit, and scalar/batch agreement. Runtime projection uses an additional 100 samples/profile with common seed 1. Main: 200,000 samples/profile with seeds 2026113621 and 2026113622.
- Advance this mechanism only if the local map improves the macro LER by at least 10%, neither profile is harmed by more than 5%, and its cost remains below 2x pooled decode time. This is an exploratory development gate.

## Resource and interpretation limits

Stop before main if any integrity check fails or the projected run exceeds 300 seconds. This tests an imposed rate pattern in a simulator with an oracle map, not an adaptive method or hardware noise. It does not change bias composition, gate schedule, qubit count, rounds, or average two-qubit error rate. No confirmatory or sealed data are in scope.
