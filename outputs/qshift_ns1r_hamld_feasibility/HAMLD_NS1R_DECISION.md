# NS-1R decision

## Gate result: FIX — parser-compatible route identified; build remains blocked

The exact pinned HAMLD DEM-to-hypergraph parser correctly preserves Q-SHIFT's undecomposed Stim DEM target ordering and decimal probabilities at p-burst 0 and .01. It preserves D0–D39/L0 node IDs, 28 D-only single-detector boundary mechanisms, 12 one-detector mechanisms that also touch L0, degree-2-to-4 multi-detector edges, and all five added burst pair mechanisms. No duplicate signatures or repeat/shift instructions were present in these flattened DEMs.

The compiled decoder was not built or invoked. The host lacks Bazel and any Linux build environment/compiler; the pinned package import requires an extension that is not shipped in upstream source. Therefore HAMLD logical predictions, inference determinism, CPU/RAM cost and runtime remain **unverified**. The deterministic parser result does not pass the decoder compatibility gate.

The narrow source-grounded next step is a separately authorized reproducible Linux/Python 3.10/Bazel 8.2.1 build, followed by the toy deterministic decoder fixtures in `HAMLD_DETERMINISTIC_DECODER_TESTS.md`. Before interpreting comparisons, disclose that HAMLD's undecomposed approximate DEM and PyMatching's decomposed approximate DEM differ in representation and may differ in modeling as well as inference.

No sampling, decoder-performance study, seed allocation, training, protected Stage 5 access, or merge occurred. The 240,000-shot pilot remains unauthorized. This review does not establish or suggest decoder superiority.
