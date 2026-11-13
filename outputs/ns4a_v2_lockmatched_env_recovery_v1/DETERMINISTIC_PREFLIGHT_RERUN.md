# Deterministic NS-4A V2 preflight rerun

## Scope and boundary

This version reruns only the deterministic circuit/DEM/decoder-compatibility preflight under the lock-matched environment. It preserves the earlier blocked preflight and its files unchanged. No Stim sampler was called; zero shots and zero evaluation labels were generated or read. No training, model selection, statistical analysis, protected outcome access, or Stage 5 access occurred.

The six condition-specific circuits and DEMs were constructed from the existing V2 configuration. This uses each condition's declared model parameters to create and label an **assumed decoder model** for compatibility testing. It does not pass a per-shot hidden regime label to a decoder. BeliefMatching receives the concrete DEM at construction and the deterministic detector fixture at decode; its generating-noise string and assumed-noise provenance are identity/provenance fields. No evaluation or observable-label arrays exist in this preflight. Consequently, this result does not validate a deployable estimator or establish that the correct model can be inferred online.

## Results

- 6/6 circuits constructed; each has 40 detectors, one observable, and five measurement-round boundaries.
- 6/6 DEMs constructed with frozen V2 settings `decompose_errors=True`, `approximate_disjoint_errors=True` and the remaining default/false flags recorded in the matrix.
- The unchanged NS-3B detector-support/logical-signature alias guard passed for all six DEMs.
- 12/12 PyMatching candidate rows passed: six DEMs × ordinary and correlation-enabled modes. PyMatching 2.4.0 correlation mode is passed at matcher construction and at `decode_batch` invocation, and the returned wrapper metadata preserves the same mode.
- 12/12 BeliefMatching candidate rows passed actual construction and deterministic fixture decoding using the pinned upstream implementation. Every output was `DecoderPrediction` with shape `(3, 1)`, `uint8` dtype, finite binary values, and unchanged detector input.
- The actual adapter rejected reversed detector order, an invalid observable ID, and a 39-column detector array. Shape rejection, experimental opt-in rejection, and input-only information isolation also passed.
- Registration failure-injection checks passed for construction failure, post-construction binding failure, and registration failure. They verified no partial bank registration; constructed adapters were closed on binding/registration failure.
- The runner and independent verifier each repeated the three registration failure-injection cases against all 12 baseline-only candidate banks; outcomes were aggregated conjunctively, so any row-level failure prevents an overall PASS.
- BeliefMatching adapters were explicitly closed after each candidate. The PyMatching wrapper exposes no close method; its candidate-scoped references were released and garbage-collected.
- Runtime BM/PM identities matched on the exact DEM digest and declared assumed-noise model ID/provenance for every row. The shared detector-order and observable-semantics fingerprints also matched.
- Independent reconstruction rebuilt all six circuits/DEMs, reconstructed and decoded all 12 rows, compared prediction values, rechecked the alias guard and model identity, independently repeated failure injection, and passed with zero failures.

The fixture is a deterministic 3×40 detector matrix constructed in source, not detector data emitted by Stim. Any fixture output agreement or bit pattern is only an interface check, not decoder accuracy evidence. Construction/inference timing values in the JSON are single-call diagnostics on this tiny fixture, not throughput or comparative performance benchmarks.

For resource context only, the 12 single candidate construction/fixture calls recorded PyMatching construction 1.221–1.736 ms (median 1.429 ms), PyMatching one-batch decode 0.103–0.627 ms (median 0.313 ms), BeliefMatching construction 19.280–116.804 ms (median 20.709 ms), and BeliefMatching one-batch decode 0.322–0.670 ms (median 0.353 ms). This is not a throughput benchmark: the fixture has only three rows, process warm-up is included, and the ranges should not be extrapolated to study workloads.

## Candidate-by-candidate result

| Candidate row | PyMatching mode | PM construction/decode | BeliefMatching construction/decode | Alias guard | DEM + assumed-noise provenance parity |
|---|---|---:|---:|---:|---:|
| `balanced_no_burst::correlations_false` | ordinary | PASS | PASS | PASS | PASS |
| `balanced_no_burst::correlations_true` | correlations enabled | PASS | PASS | PASS | PASS |
| `x_biased_no_burst::correlations_false` | ordinary | PASS | PASS | PASS | PASS |
| `x_biased_no_burst::correlations_true` | correlations enabled | PASS | PASS | PASS | PASS |
| `z_biased_no_burst::correlations_false` | ordinary | PASS | PASS | PASS | PASS |
| `z_biased_no_burst::correlations_true` | correlations enabled | PASS | PASS | PASS | PASS |
| `balanced_burst_0.005::correlations_false` | ordinary | PASS | PASS | PASS | PASS |
| `balanced_burst_0.005::correlations_true` | correlations enabled | PASS | PASS | PASS | PASS |
| `balanced_burst_0.010::correlations_false` | ordinary | PASS | PASS | PASS | PASS |
| `balanced_burst_0.010::correlations_true` | correlations enabled | PASS | PASS | PASS | PASS |
| `balanced_burst_0.015::correlations_false` | ordinary | PASS | PASS | PASS | PASS |
| `balanced_burst_0.015::correlations_true` | correlations enabled | PASS | PASS | PASS | PASS |

The complete row-by-row record is `BELIEFMATCHING_COMPATIBILITY_MATRIX.json`; aggregate results are in `LOCKMATCHED_PREFLIGHT_SUMMARY.json` and independent checks in `INDEPENDENT_PREFLIGHT_VERIFICATION.json`.

## Historical result preserved

The earlier `outputs/ns4a_v2_deterministic_preflight/VALIDATION_SUMMARY.json` remains the historical blocked run: its environment lacked BeliefMatching, and it recorded zero sampling. This rerun is in a separate versioned directory and does not rewrite or reinterpret that earlier result.
