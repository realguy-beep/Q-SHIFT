# NS-4A V2 Deterministic Preflight

**Status: BLOCKED for complete 12-candidate compatibility.** This report records deterministic source, circuit, DEM, identity, and decoder-compatibility checks only. It does not authorize sampling or model selection.

## Scope and isolation

- Branch: `codex/ns4a-v2-deterministic-preflight`
- Exact base: `612c5e1381d75ca069bc6952d057c798ab10e9ab`
- V2 protocol status remains prospective and unauthorized (`sampling_authorized=false`).
- The non-cone sparse-checkout allowlist is recorded by `git sparse-checkout list`. It comprises the five approved generator/protocol paths, the three V2 revision/configuration paths, the listed NS-2D contract/runtime/adapter paths, and this new preflight directory.
- Exact content inputs, SHA-256 digests, byte counts, upstream commit, and the adapter-copy check are in [SOURCE_INPUT_INVENTORY.json](SOURCE_INPUT_INVENTORY.json).
- The upstream NS-3B adapter blob at `e4ff201e3db18a2d18e7474bef4a83542eaa3da8` matches the integrated adapter byte-for-byte (SHA-256 `702dc36ef4dedd38347b0e78541d1d2d2ff063c2462dbab29aa2095f583c2106`). The upstream lockfile was read from that exact Git object only.
- No historical outcome files or Stage 5 material were read. No sampler was called; no random detector events, labels, training, model selection, or accuracy/performance comparison was used.

## Deterministic construction results

The V2 generator built all six proposed Z-memory circuits at distance 3 and five rounds. Each has 26 Stim qubit indices, 40 detectors, one logical observable, and five measurement-round (`MR`) boundaries. Stim DEM conversion succeeded for all six with the configured `decompose_errors=true` and `approximate_disjoint_errors=true`; the recorded effective settings also show the remaining Stim defaults. The normalized circuit-topology signatures, detector-order fingerprints, DEM detector-order fingerprints, and observable-semantics hashes agree across the six conditions. Circuit/DEM byte hashes vary with the configured Pauli/burst condition, as expected.

The unchanged NS-3B `validate_upstream_signature_semantics` guard passed on every candidate DEM. This establishes that the guard found no unsupported instruction, repeated component target, detector-support/logical-signature collision, or over-two-detector decomposed component in these six concrete DEMs. It does not establish that the DEM is a faithful physical model; it is the configured approximate-disjoint conversion.

| Candidate | PM mode | Circuit/DEM | Alias guard | PM construct + fixture decode | BM construct | DEM/provenance parity |
|---|---|---|---|---|---|---|
| `balanced_no_burst::correlations_false` | ordinary | PASS | PASS | PASS | BLOCKED: dependency absent | contract PASS; BM runtime blocked |
| `balanced_no_burst::correlations_true` | correlation-enabled | PASS | PASS | PASS | BLOCKED: dependency absent | contract PASS; BM runtime blocked |
| `x_biased_no_burst::correlations_false` | ordinary | PASS | PASS | PASS | BLOCKED: dependency absent | contract PASS; BM runtime blocked |
| `x_biased_no_burst::correlations_true` | correlation-enabled | PASS | PASS | PASS | BLOCKED: dependency absent | contract PASS; BM runtime blocked |
| `z_biased_no_burst::correlations_false` | ordinary | PASS | PASS | PASS | BLOCKED: dependency absent | contract PASS; BM runtime blocked |
| `z_biased_no_burst::correlations_true` | correlation-enabled | PASS | PASS | PASS | BLOCKED: dependency absent | contract PASS; BM runtime blocked |
| `balanced_burst_0.005::correlations_false` | ordinary | PASS | PASS | PASS | BLOCKED: dependency absent | contract PASS; BM runtime blocked |
| `balanced_burst_0.005::correlations_true` | correlation-enabled | PASS | PASS | PASS | BLOCKED: dependency absent | contract PASS; BM runtime blocked |
| `balanced_burst_0.010::correlations_false` | ordinary | PASS | PASS | PASS | BLOCKED: dependency absent | contract PASS; BM runtime blocked |
| `balanced_burst_0.010::correlations_true` | correlation-enabled | PASS | PASS | PASS | BLOCKED: dependency absent | contract PASS; BM runtime blocked |
| `balanced_burst_0.015::correlations_false` | ordinary | PASS | PASS | PASS | BLOCKED: dependency absent | contract PASS; BM runtime blocked |
| `balanced_burst_0.015::correlations_true` | correlation-enabled | PASS | PASS | PASS | BLOCKED: dependency absent | contract PASS; BM runtime blocked |

The machine-readable [COMPATIBILITY_MATRIX.json](COMPATIBILITY_MATRIX.json) contains all 12 candidate rows (six conditions × ordinary/correlation-enabled mode), including full circuit and DEM SHA-256 digests, detector ordering, observable semantics, graph dimensions, mode, errors, and candidate-specific status. It has no candidate exclusions.

### Correlation mode and paired-model identity

The installed PyMatching 2.4.0 accepted both modes for every DEM. The project adapter constructs with `enable_correlations=correlation_mode` and calls `decode_batch(..., enable_correlations=metadata.correlation_mode)`; see `qshift_core_v1/pymatching_adapter.py` lines 35–50 and 99–104. A deterministic synthetic `(3, 40)` detector fixture was decoded in each mode; predictions had the expected shape and binary values. The fixture was not produced by Stim sampling.

For each condition, both PyMatching modes and the intended BeliefMatching model identity refer to the same concrete DEM digest and declared assumed-noise provenance. The NS-2D registration path compares the reference decoder's DEM hash/noise provenance and passes `dem_artifact.dem` into `BeliefMatchingAdapter.from_dem` (`qshift_core_v1/research_adapters/beliefmatching_integration_ns2d.py` lines 120–135). Contract and identity parity checks pass. **This is not runtime parity evidence for BeliefMatching:** its constructor could not complete, so the preflight could not verify the installed library binding against those bytes or perform an end-to-end BM decode.

The opt-in guard rejects BeliefMatching registration with `experimental_opt_in=false`; the failure leaves the bank unchanged. On the authorized synthetic fixtures, detector-only inputs reached the adapter, while wrong detector shape and wrong detector order were rejected. An injected missing-dependency construction failure also left no partial registration. The unchanged alias guard is defined at `qshift_core_v1/research_adapters/beliefmatching_adapter_ns3b.py` lines 61–124 and is invoked before construction in that adapter at lines 217–219.

## Exact blocker and environment

The current environment reports Python 3.12.10, Stim 1.16.0, PyMatching 2.4.0, and NumPy 2.5.3. `beliefmatching` is not installed. The exact NS-3B lock pins BeliefMatching to upstream commit `4458c278bbec273c8c1a26411dadccc49222f8ef` and pins NumPy 2.2.6. Therefore the environment is also not lock-equivalent. The deterministic runner reports the exact construction error for every attempted BM candidate:

```text
BeliefMatchingConstructionError: failed to import pinned beliefmatching dependency: ModuleNotFoundError: No module named 'beliefmatching'
```

No package was installed or substituted. This blocks certification of the 12-candidate decoder compatibility matrix, even though circuit/DEM construction, alias screening, and the two PyMatching modes passed.

## Construction and resource accounting

The observed PyMatching graph has 40 detector nodes in every condition: 142 edges for the three no-burst DEMs and 147 edges for the three burst DEMs; each graph has one observable/fault ID. The deterministic workload constructed six circuits and six DEMs, constructed 12 PyMatching instances (two modes per DEM), and decoded only the small fixed synthetic fixture. BeliefMatching construction was attempted for each candidate and failed at dependency import.

No timing, peak memory, throughput, or inference benchmark was run. This preflight establishes graph sizes and number of constructions only; it does not support a runtime or memory projection for the 304,000-shot proposal. Decoder construction and inference must be measured separately in a later authorized preflight after a lock-matched environment is supplied.

## Validation and disposition

See [VALIDATION_SUMMARY.json](VALIDATION_SUMMARY.json) and [VALIDATION_SUMMARY.md](VALIDATION_SUMMARY.md). The final deterministic runner completed with 6/6 circuits, 6/6 DEMs, 12/12 PyMatching mode checks, 6/6 alias-guard passes, and all deterministic identity/order/shape/opt-in/failure-injection checks passing. Counts are 0 sampler calls, 0 sampled shots, 0 labels, and 0 model selections.

**Decision: BLOCKED — stop for supervisor review.** The next permissible step is to provide/authorize a lock-matched isolated environment containing the exact pinned BeliefMatching dependency, then repeat this deterministic preflight. This report does not authorize sampling, model selection, execution, or a scientific freeze. PRs #2–#5 are not modified by this preflight branch.
