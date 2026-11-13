# NS-4A Baseline and Noise-Model Audit

**Scope:** source/protocol review only. No stochastic samples were generated and no Stage 5 outcomes were accessed.

## Reviewed evidence

- Approved engineering base: `codex/ns2d-beliefmatching-integration` at `924746ee3851f7662365e7834f998159d1b286a7`.
- NS-2D composition adapter: `qshift_core_v1/research_adapters/beliefmatching_integration_ns2d.py`.
- Imported NS-3B adapter: `qshift_core_v1/research_adapters/beliefmatching_adapter_ns3b.py`.
- NS-2D reports: `outputs/core_system_upgrade_ns2d_v1/NS2D_IMPLEMENTATION_REPORT.md`, `NS2D_DEPENDENCY_PROVENANCE.md`, and deterministic `FIXED_FIXTURE_COMPARISON.json`.
- Phase 2B implementation/protocol: `outputs/phase2b_pauli_bias/noise_model.py`, `PHASE2B_PROTOCOL.md`, `NOISE_MODEL_SPECIFICATION.md`.
- Phase 3A implementation/hypothesis: `outputs/phase3a_correlated_noise_preflight/simulator.py`, `CORRELATED_NOISE_HYPOTHESIS.md`.
- NS-3B research handoff, alias-collision finding, strong-baseline protocol, and feasibility decision in the separate research worktree (listed in the supervisor handoff).

No raw evaluation archives or protected Stage 5 result files were opened for this audit.

## What is implemented

NS-2C supplies sampling identity, separate decoder-model identity, checked adapters, compatibility-aware registration, and a paired evaluation harness. NS-2D registers the validated BeliefMatching adapter only under explicit `experimental_opt_in=True`. It preserves the upstream detector-support/logical-signature alias guard, validates sampling-circuit identity and detector/observable compatibility, uses `decompose_errors=True, approximate_disjoint_errors=True`, and closes partially constructed adapters on failure. Its constructor compares BM's concrete DEM and declared assumed-noise provenance with a registered reference decoder. The ordinary PyMatching path remains intact; correlation-enabled PyMatching enables that mode at both construction and decode.

The fixed fixture uses five manually supplied 40-bit detector rows and has no logical labels. All three validated NS-2D modes returned `[0, 0, 1, 0, 1]` on that fixture. This demonstrates deterministic contract compatibility only—not equal accuracy, a representative sample, or a performance result. Previously recorded one-run construction observations were approximately 1.852 ms (ordinary PM), 2.188 ms (correlated PM), and 141.908 ms (BM); five-row harness wall observations were approximately 0.739, 0.773, and 0.844 ms respectively. They are not throughput benchmarks.

Source locations reviewed: `noise_model.py:18-44` defines Pauli weights and probability tables; `noise_model.py:54-75` constructs the rotated-memory circuit and replaces generated depolarizing instructions; `noise_model.py:113` states that 2Q Pauli pairs are categorical but distinct locations are independent. `simulator.py:24-68` validates and injects the X8/X10 burst after each MR; `simulator.py:79-93` documents the DEM conversion and matching correlation option. The NS-2D wrapper requires opt-in at `beliefmatching_integration_ns2d.py:45-69`, enforces the decomposed/approximate DEM at `:87-95`, checks same-model/provenance parity at `:110-124`, and invokes upstream alias validation through the adapter at `:130-139`. The unchanged upstream guard is `beliefmatching_adapter_ns3b.py:61-124`.

## Baseline definitions and fairness

| Baseline / arm | Noise-model information | Algorithm or mode distinction | Intended role |
|---|---|---|---|
| Nominal ordinary PM | Balanced, no-burst assumed DEM | Correlations off at construction and decode | Familiar fixed reference |
| Nominal correlated PM | Same nominal DEM and weights | Correlations on at construction and decode | Isolate correlation-mode effect; not inherently “stronger” |
| Pooled-selected PM | One configuration selected from a fixed 4-model × 2-mode grid on separate, equally weighted selection roots | Single configuration frozen across evaluation strata | Primary strong static comparator |
| Matched-selected-DEM PM controls | Exact selected DEM used by pooled-selected arm | Ordinary and correlated modes | Separate model quality from mode |
| BeliefMatching | Exact same selected DEM/provenance as primary PM | Distinct algorithm/representation, experimental opt-in | Primary candidate |

The primary candidate and comparator must share the same concrete DEM, DEM construction flags, detector/observable order, assumed-noise parameters and provenance. Their only primary difference is decoder implementation. This does not establish semantic equivalence: BeliefMatching's probabilistic/graph representation can differ from PyMatching's matching objective. Ordinary versus correlation-enabled PyMatching must use an identical DEM and weights; both construction-time and decode-time flags must match the arm label.

The selection set uses labels only to choose a single pooled static PyMatching configuration from the prespecified grid. The resulting chosen DEM is then supplied to both the primary PM and BM arms. It is not permissible to select a different model per evaluation condition. A selected static configuration is “strong” only relative to this stated candidate grid and selection partition, not globally optimal. The current NS-3B wrapper binds `SamplingIdentity` as adapter audit metadata (which includes a generating-noise ID), while `from_dem` passes only `decoder_dem` and `max_bp_iters` to the upstream factory (`beliefmatching_adapter_ns3b.py:203-221`), and `decode_batch` passes a copied detector matrix to the inner decoder (`:298-315`). The future runner must verify this boundary with an input spy; condition labels and observable labels must not enter the inner decoder call.

## Noise-condition suitability

| Proposed condition | Source support | Decision |
|---|---|---|
| Nominal | Phase 2B `balanced`, gate p 0.003, measurement p 0.003 | Include; specify “balanced Pauli composition,” not hardware nominal |
| Data-heavy | Not present as a separate rate parameter in the inspected Phase 2B/3A generator | Exclude. Do not relabel X/Z bias as data-heavy |
| Measurement-heavy | Measurement probability is fixed at 0.003 by Phase 2B generator; no independent sweep here | Exclude. Requires a new explicitly reviewed generator condition |
| Pauli composition bias | Phase 2B supports X-biased, balanced, Z-biased at fixed total gate fault mass and measurement p | Include X-/Z-biased no-burst sensitivity strata; these change Pauli composition, not total data/measurement rate |
| Spatial common-cause burst | Phase 3A supports simultaneous X8/X10 after each MR, independent over five boundaries | Include only as clearly labeled synthetic mechanism. p is per boundary, not a device-calibrated burst rate |

The Phase 2B `PAULI_CHANNEL_2` channel is categorical per gate and has dependent Pauli components within a gate; draws at distinct gate locations remain independent. Phase 3A adds a different cross-location event that simultaneously affects two data qubits. These mechanisms must not be conflated. Stim DEM conversion with `approximate_disjoint_errors=True` is an approximation shared across the matching and BM arms; results are conditional on that representation.

## Known limitations and blockers

1. **Alias collision safety:** upstream BeliefMatching keys some structures by detector support and can overwrite conflicting logical signatures. NS-3B rejects unsafe DEMs. The new model grid and each held-out burst model need deterministic checks against the unchanged guard before sampling. Any rejection blocks this proposed grid until a newly reviewed protocol says how to proceed; do not drop an inconvenient condition after seeing outcomes.
2. **DEM graph/decomposition semantics:** the integration accepts the declared decomposed approximate DEM. This is not an exact representation of every categorical/disjoint mechanism. Shared conversion provides information parity but not equal algorithmic semantics.
3. **Tiny fixture:** five hand-built rows provide no LER estimate and do not characterize inference scaling.
4. **No sample-derived variance:** existing fixture has no labels and cannot provide paired discordance, root heterogeneity or power estimates.
5. **Fixed-baseline selection uncertainty:** eight candidate configs and only eight roots per selection condition can create winner's-curse/model-rank instability. Report all eight selection scores and root-bootstrap rank frequencies; do not hide ties or instability.
6. **Restricted history:** historical seed screening may cover only recoverable metadata. Document unknown coverage; do not inspect protected Stage 5 outcomes.
7. **No adaptivity test:** comparing fixed BM to fixed PM does not evaluate a detector-only estimator, an online controller, or switching.

## Audit conclusion

The NS-2D deterministic integration is sufficient to propose a bounded development-only paired comparison, conditional on an all-condition DEM/alias preflight, seed screening, information-parity validation and a separate execution authorization. It is not sufficient to claim decoder accuracy, feasibility at the proposed sample size, or advantage over PyMatching.
