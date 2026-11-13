# Limitations, negative results, and failed attempts

- The exact MAP oracle is exponential and intentionally capped at `2^20` assignments. It is not a full Q-SHIFT decoder.
- BP assumes independent Bernoulli mechanisms in the parsed DEM. Q-SHIFT's original circuit has categorical mutually exclusive gate outcomes, and Stim DEM conversion here uses `approximate_disjoint_errors=True`; BP results are DEM-level approximations.
- BP's tested tree case agrees with MAP. No exact loopy MAP oracle is feasible for the 448-mechanism Q-SHIFT DEM. No claim of loopy BP optimality is made.
- At a 50-iteration cap, all five deterministic Q-SHIFT rows and all synthetic scaling rows converged. The first low-iteration benchmark configuration did not converge. This shows cap sensitivity; a convergence flag is not an accuracy guarantee.
- On five selected Q-SHIFT fixtures, BP and standard/correlation-enabled PyMatching predictions matched, with zero observed disagreements. The rows are not random or representative, have no truth labels, and use different DEM representations.
- The local Python BP implementation is orders of magnitude slower than PyMatching on these fixtures. It should not be advanced to a large study without optimization or a hybrid design.
- BP output for its internal auxiliary logical variable is a loopy marginal hard decision, not necessarily a correction satisfying the syndrome. PyMatching's observable prediction convention is different in algorithmic construction; compare only after explicit output-contract fixtures.
- `benchmark_results.json` from NS-3 and `benchmark_results_ns3a.json.partial` from the canceled mission are both zero-byte interrupted files and remain preserved. Two low-iteration benchmark outputs (`benchmark_results_ns3a_attempt2.partial` and `benchmark_results_ns3a_attempt3.partial`) preserve BP nonconvergence. The invalid synthetic DEM syntax failure is preserved in the session transcript. The complete repaired run is `benchmark_results_ns3a.json`.
- No stochastic circuit samples, detector histories, logical labels, training, protected outcomes, or V2.4 material were accessed or generated for this NS-3A continuation.
