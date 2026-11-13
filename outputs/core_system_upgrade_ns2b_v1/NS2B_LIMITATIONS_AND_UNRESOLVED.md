# NS-2B Limitations and Unresolved Questions

- No research decoder, including HAMLD, was integrated. Its inference API and exact input requirements remain unverified.
- The current decoder input is a flat, unpacked binary `[shots, detectors]` matrix. Temporal tensors, soft detector values, graph/hypergraph objects, and non-Stim input representations require a new explicit contract.
- Sampling identity hashes Stim's exact circuit text and records its version. This is intentionally strict; semantically equivalent circuits with different serialization/version can hash differently.
- Code-family, distance, rounds, memory basis, noise IDs, and observable meanings are explicit declarations bound into the identity, not inferred from Stim text or proven to be physically true by the contract.
- Generating-noise and decoder-assumption provenance are caller-supplied records. Hashes establish byte identity of those records, not truth or agreement with how a circuit/model was constructed.
- `StimDEMArtifact.build` records exact Stim conversion options and output text digest, but cannot prove a third-party decoder actually consumed that DEM or faithfully used it.
- The detector batch adapter verifies circuit, dimensions, ordering declaration, immutable bytes, and digest. It cannot prove arbitrary externally supplied arrays truly came from the named Stim sampler.
- The paired evaluator keeps labels out of decoder call signatures, but is not an OS-level sandbox. A decoder with access to ambient process/global state could access unrelated data.
- The API accepts static-resource digest declarations but does not enforce equal calibration data, runtime, compute, memory, or privileged-information budgets; future experiments must document them separately.
- PyMatching graph semantics and correlation configuration remain the existing adapter's responsibility. The v2 identity records declarations; external audit is still required to validate a candidate's construction and call behavior.
- No sampling, training, protected data access, benchmark, or performance evaluation was performed.
- V2.4 remains HOLD. NS-1 evidence-scope incident disclosure and historical manifest discrepancies remain unchanged.
