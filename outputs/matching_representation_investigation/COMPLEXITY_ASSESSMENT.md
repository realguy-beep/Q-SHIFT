# Complexity and resource assessment

## Measurements in this bounded investigation

- Latest end-to-end deterministic job: 4.525 s.
- Peak process working set: 102,764,544 bytes (98.0 MiB); below the 2 GiB limit.
- Standard/correlated graph builds on 40-detector, five-round DEMs: about 1.7–2.4 ms per graph in the current run (timing is environment-specific).
- 8-detector exact independent-DEM posterior: 256 syndromes, 29 mechanisms, 0.00091–0.00095 exact risk; local posterior enumerates up to 4,096 configurations and takes 4.4–6.7 ms for the full syndrome sweep.
- 16-detector exact DEM inference enumerated up to 65,536 syndromes for the reduced fragments. It is not a full 5-round decode benchmark.

## Scaling limits

Global exact inference over `m` detector bits stores a distribution with up to `2^m` syndrome states (and more if joint logical states are stored). The previous verified scaling investigation reported roughly 256 MiB at 24 detectors and estimated 64 GiB at 32 detectors; the 40-detector five-round case was estimated at 16 TiB for that representation and skipped. These are historical measurements/estimates from `categorical_inference_investigation`, not runs in this phase. Direct categorical fault-configuration enumeration grows exponentially with fault locations (the existing full five-round model is far beyond a feasible exhaustive loop).

Candidate A adds linear preprocessing over DEM events and no asymptotic decoding change, but only applies if every complete event is graphlike and not logical-only. Candidate B has an explicit local enumeration cap of 12 events, at most 4,096 Bernoulli configurations. Its current syndrome selection covers only 10.5% of one-round surface-fragment syndromes without fallback. No evidence establishes acceptable full distance-3/five-round decoding performance, let alone larger distances.

No stochastic simulation, Phase 2B test decoding, large parameter search, or >2 GiB job was run.
