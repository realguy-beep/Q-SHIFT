# NS-3B decision

## Classification: A — WORKING AND FEASIBLE for bounded development comparison

The official BeliefMatching 0.2.0 implementation at commit `4458c278bbec273c8c1a26411dadccc49222f8ef` installed in an isolated Python 3.12.10 environment. Its pinned implementation source hash is verified at runtime. The Q-SHIFT adapter accepts the decomposed approximate DEM, preserves sampling/generating-noise and decoder-model identities separately, validates detector/observable order and outputs, and passed the NS-2C checked execution path with its experimental opt-in.

Fourteen deterministic tests passed. On the five saved Q-SHIFT fixtures, BM matched ordinary and correlation-enabled PyMatching predictions and converged on all rows at 20 BP iterations. A two-observable toy case preserved output order; a small toy exact-MAP case agreed on all four syndromes. These checks establish interface/fixture behavior only, not loopy-graph optimality or logical-error-rate performance.

The most important limitation is source-confirmed upstream DEM aliasing: different logical signatures on the same detector support can be overwritten. A deterministic counterexample shows direct upstream BM disagrees with both exact MAP and PyMatching; the adapter detects and rejects such DEMs. The tested Q-SHIFT decomposed DEM has no such conflicts and passes the guard.

Warm BM inference on five fixed Q-SHIFT rows was 0.472 ms versus 0.005 ms ordinary PyMatching and 0.008 ms correlation-enabled PyMatching in the final run. This is slower by approximately 94x/59x on the tiny fixture batch, but still sub-millisecond for this d3 test. Construction was about 21 ms for BM and 1.3–1.5 ms for PyMatching. This supports a plausible bounded scientific comparison, subject to explicit runtime budgets and identical DEM information.

## Recommendation

**PASS for integration handoff and a separately authorized bounded development study design. HOLD on all stochastic evaluation and performance claims.** No logical labels, circuit samples, protected outcomes, training, or seeds were used/generated. Do not merge this standalone research package into Main Codex; Main Codex should review and cherry-pick only after supervisor approval.
