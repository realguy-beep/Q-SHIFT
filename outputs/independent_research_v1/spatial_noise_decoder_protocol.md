# Spatially heterogeneous noise and local matching

## Question and hypothesis

Prior model-mismatch screens changed global rate/bias, but not spatial distribution. Test whether a PyMatching model with the correct spatially local two-qubit rates improves logical decoding over a pooled static model when the underlying noise has a stable hotspot. If it does not, a detector-only selector between such spatial models is unlikely to be useful for this mechanism.

## Fixed simulator intervention

Use the existing distance-3, five-round Z-memory/X-biased-ratio10 Phase 2B circuit at p=.003. Split each `PAULI_CHANNEL_2` target pair into its own channel instruction at the same circuit position. Rank the 120 independent pair locations by interaction midpoint x-coordinate, then y-coordinate, instruction index, and pair index; divide into equal 60-location west/east halves. Preserve the exact source Pauli-pair probability proportions. For the east-hot profile multiply total p by 1.5 in the east half and .5 in the west half; for west-hot, reverse these factors. Thus both profiles have exactly the same average pair fault rate and composition as the homogeneous source circuit. One-qubit and measurement noise remain homogeneous.

For each profile, build two correlation-enabled PyMatching decoders from approximate DEMs using the same `decompose_errors=True, approximate_disjoint_errors=.003` settings: (1) pooled static source-model graph at the exact spatial mean p=.003, and (2) profile-calibrated local graph from the actual heterogeneous circuit. Decode the same sampled detector/observable rows with both models. The local decoder is an oracle-map upper reference: the spatial profile is known exactly; this does not test estimating or selecting it.

## Fixed experiment and metrics

Run two profiles (east-hot, west-hot), 200,000 direct Stim samples/profile on fresh streams. Seeds: 2026112901–2902 for 100-shot/profile preflight; 2026112911–2912 for main. Primary per-profile endpoint is paired difference in logical failures local minus pooled; report both LERs, exact two-sided McNemar test on discordant predictions, paired difference interval, decoder runtime, and the equal-weight macro relative change. Report the exact site count, per-zone p, mean p, and check that east/west maps are reversals. Advancement to any selector study requires at least 10% macro LER reduction and no profile harmed by more than 5%; otherwise stop this spatial-hotspot direction.

## Preflight and limits

Before main sampling require 120 unique pair sites, 60 per zone, equal mean pair rate .003, exact source probability proportions, east/west reversal, unchanged qubits/detectors/observables/rounds/interaction count, deterministic noiseless circuits, successful pooled/local DEM construction, and scalar/batch decoder agreement. Stop if any check fails or the measured 200k/profile projection exceeds 300 seconds. This is a synthetic robustness stress test at d3, not hardware-calibrated noise, an adaptive result, a threshold, or confirmatory evidence. Do not tune hotspot factors, split locations, or decoder threshold after observing samples.


## Preflight amendment before sampling

The initial no-shot preflight stopped during DEM conversion: the largest 1.5x local Pauli component is .0026786, above the existing .0018 decomposition threshold. No stochastic Q-SHIFT samples were generated. Before resuming, set the same fixed conversion threshold to .003 for both the pooled and local graphs, which exceeds every tested branch probability while preserving model symmetry. The sample counts, noise maps, seeds, endpoints, and advancement gate are unchanged.
