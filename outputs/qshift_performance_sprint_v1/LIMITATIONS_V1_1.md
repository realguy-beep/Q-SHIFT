# V1.1 limitations and next-step recommendation

1. **No observed improvement.** Profile-estimated PyMatching tied pooled-fixed PyMatching in all 100,000 evaluation rows. The frozen gate is NO-GO for this estimator and configuration.
2. **Estimator collapse.** The 40-detector ridge estimator predicts approximately the five-condition mean burst probability across all tested settings. It failed to identify the condition-specific probability; overall bias near zero is an artifact of the balanced probability grid.
3. **Small development study.** Ten roots per condition and 20,000 shots per condition are insufficient for broad claims; the exact zero paired difference makes the bootstrap interval degenerate but does not establish population equivalence.
4. **Synthetic model only.** Results depend on the distance-3, five-round Stim circuit and DEM decomposition/approximate-disjoint settings. They do not demonstrate hardware performance.
5. **Oracle is privileged.** True-p PyMatching receives the generating parameter. It is an upper-reference arm only and cannot support a fair deployable comparison.
6. **Replay provenance limit.** The first failed V1 evaluation call returned 2,000 rows but did not persist them. V1.1 regenerated that same sample identity from its original seed/circuit/Stim version. Exact equality to the lost transient array is not directly verifiable.
7. **Cumulative execution count.** There were 106 sampler calls and 132,000 returned rows across the failed attempt and recovery, including the replay. The archived dataset has one row set per each of 105 unique partition identities and 130,000 persisted rows.
8. **Local raw evidence.** Raw `.npz` files are ignored and remain local. Git contains the seed/source manifests, per-root CSV, aggregate analysis, and audit hashes, but not the arrays needed to rerun the saved-array auditor elsewhere.
9. **Resource measurement.** The run measured process peak working set, not a hard process-tree memory cap. No resource limit was approached.

## Recommendation

Do not launch a larger experiment using this same estimator. The code did not produce a distinct decoder output from the strong pooled-fixed baseline, and the 50-batch diagnostics show the probability estimator collapsing toward the grid mean. A later development proposal should first demonstrate, on disjoint synthetic development data and before evaluation, that a detector-only estimator can distinguish the burst probabilities or estimate a decoder-relevant parameter. Any new method needs a new frozen protocol and success criteria; this NO-GO does not authorize it.
