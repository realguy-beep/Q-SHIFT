# Bounded feasibility pilot protocol — correlation-aware PyMatching

**Status: planned only. No new simulation was run for this direction-selection task.** This is development/feasibility work, not a confirmatory benchmark. Historical Phase 2B–5 files remain untouched.

## Objective and frozen comparison

Measure whether correlation-aware decoding changes logical-observable predictions and improves paired logical error rate compared with ordinary matching when the circuit, approximate DEM, DEM edge weights and test shots are held constant.

### Circuit/noise conditions

Reuse Phase 2B’s rotated surface-code X-memory and Z-memory circuits at distance 3, five rounds. Use three gate-composition regimes from its existing noise specification: X-biased 10:1:1, balanced 1:1:1, and Z-biased 1:1:10. Keep total single- and two-qubit categorical gate-fault probability at 0.003 and generated basis-appropriate measurement flips at 0.003. Preserve the existing post-Clifford injection locations and two-qubit Pauli-pair channel ordering. Do not add new fault locations or alter the circuit between decoder arms.

### Decoder arms on each shared sample bundle

1. **Pooled fixed, uncorrelated:** use the Phase 2B calibration-selected fixed model for that memory basis (X-memory grid index 0; Z-memory grid index 2) and decode with correlated matching disabled.
2. **Pooled fixed, correlated:** the identical frozen DEM and weights with correlated matching enabled.
3. **Regime-informed, uncorrelated:** use the DEM corresponding to the known generating composition as an explicitly non-deployable information reference, with correlation use disabled.
4. **Regime-informed, correlated:** the same regime-informed DEM with correlation use enabled.

The main ablation is arms 1 vs 2: fixed weights, one deployable pooled model per basis, only the correlation-aware decoding mode differs. Arms 3 vs 4 test whether correlation use matters when the DEM composition is informed. Noise-regime knowledge is not an input to arms 1 or 2.

## Sampling and seeds

- Six strata: 2 memory bases × 3 gate-composition conditions.
- 12 independent development roots per stratum.
- 10,000 shots per root; **720,000 paired shots total**.
- Candidate prospective seed allocation: circuit root seed `93000001 + 100 × stratum_index + root_index`, where strata are ordered X-memory/X-biased, X-memory/balanced, X-memory/Z-biased, Z-memory/X-biased, Z-memory/balanced, Z-memory/Z-biased and root indices are 0–11. Diagnostic seed `93000000`; root-cluster bootstrap RNG `93010001`; sign-flip RNG `93010002`. Before any sampling, scan all recoverable historical source/config/result seed records and the reserved Q-SHIFT namespaces. If any collision is found, select a disjoint contiguous seed block prospectively, write the inventory and hash it before sampling. Use one unique Stim root seed per stratum/root; all four arms consume the identical detectors and observable labels from that generated bundle.
- Store detector arrays, observables, all four prediction arrays, per-root counts, seeds, configuration/source hashes and environment versions. Do not reuse Phase 2B held-out labels for selection or scoring.
- These are fresh development samples. They must not be called confirmatory, and no later policy may be tuned and evaluated on the same data as an independent test.

## Circuit and decoder preflight

Before full sampling: (a) recreate noiseless circuits and confirm zero detectors/observable flips; (b) verify each noisy circuit has 40 detectors and one observable; (c) verify generating probabilities, target placement and retained detector/observable definitions against Phase 2B; (d) create off/on matchers from the exact same frozen DEM and assert matching graph/weight fingerprints are identical; (e) confirm the on matcher is constructed with correlation support and decoding calls use the matching option consistently; (f) confirm all four outputs have one binary logical prediction per sample; (g) scan DEM decompositions to ensure the target correlation metadata exists; and (h) run a small diagnostic with a fresh diagnostic-only seed. If the API fails to expose a valid on/off comparison for the saved DEMs, stop and document that technical blocker rather than substitute a different decoder.

The expected DEM conversion remains the Phase 2B choice `decompose_errors=True, approximate_disjoint_errors=True`. Both arms see the same approximation. The pilot therefore isolates use of the available decomposition/correlation metadata; it does not test the fidelity of the DEM representation itself.

## Endpoints and analysis rules

For every root and stratum, save raw observable errors and residual failures (`observable XOR predicted logical flip`) for each arm, plus paired shot-level discordances. Report LER, absolute paired LER difference, relative reduction when the baseline error rate is nonzero, correction disagreement, decoder runtime per shot and total runtime. Record memory as process RSS before/after model construction and peak during sampling/decoding, noting that native allocations may be included only in process-level values.

**Primary feasibility estimand:** equal-weight mean across the six strata of (pooled-fixed correlated LER − pooled-fixed uncorrelated LER). Negative favors correlation-aware decoding. Calculate the root-level paired difference within each stratum, then aggregate strata equally. Use a two-sided root-cluster sign-flip test with 100,000 Monte Carlo assignments (RNG seed 93010002) and a regime-stratified root bootstrap with 20,000 resamples (RNG seed 93010001) for a 95% interval. Shot-level exact McNemar counts are reported as paired descriptive evidence, not as a substitute for independent-root uncertainty. The two regime-informed arms are secondary diagnostics; correct their six stratum comparisons with Holm adjustment if inferential p-values are reported. Do not choose a decoder from pilot evaluation labels.

## Decision gate

The pilot is worth a separate frozen benchmark only if: (1) preflight confirms usable correlation metadata and correct API behavior; (2) the primary point estimate is at least **0.02 percentage points lower LER** for correlated mode and the upper endpoint of its 95% interval is at or below **−0.02 percentage points** (the provisional minimum practically interesting effect); and (3) at least four of six strata have a favorable point estimate, with no one stratum driving the aggregate. Fix this margin before sampling, report all cells, and do not redefine it after results. This is a development investment gate, not confirmatory evidence. A 12-root feasibility pilot may be inconclusive. If so, report “uncertain” and either add a prespecified development sample or stop; do not label it a positive result. If model predictions are nearly identical and paired utility shows no stable gain, move to fallback C rather than invent an adaptive layer.

## Reporting and stopping

Stop if circuit or graph preflight fails, the correlation-on setting is not verifiably active, or seed screening finds a recoverable collision. Preserve every completed root. No adaptive switching, no hardware interface, no threshold claim, and no confirmatory test are authorized by this protocol. A later confirmatory study would need a new protocol and a fresh untouched test stream after feasibility outcomes are reviewed.

