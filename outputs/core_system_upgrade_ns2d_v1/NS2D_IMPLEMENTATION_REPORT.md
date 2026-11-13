# NS-2D BeliefMatching Integration Report

## Status

The deterministic engineering integration was committed and pushed as `ee096304fa72d6668101fbe0f54475b663e2c273` on `codex/ns2d-beliefmatching-integration`. Draft PR [#2](https://github.com/realguy-beep/Q-SHIFT/pull/2) targets `codex/ns2b-sampling-model-identity`, whose base commit is `d66346d8c7ad54b9567ecdd190e0d54ee7b93f0f`. It remains unmerged. The initial validation counts below record that checkpoint; supervisor-correction tests are recorded separately in `NS2D_REVIEW1_VALIDATION.json`. Neither record authorizes scientific sampling.

## Integration

The published NS-3B adapter was copied byte-for-byte to `qshift_core_v1/research_adapters/beliefmatching_adapter_ns3b.py` (SHA-256 `702dc36ef4dedd38347b0e78541d1d2d2ff063c2462dbab29aa2095f583c2106`). The NS-2D composition layer, `beliefmatching_integration_ns2d.py`, binds it to the existing NS-2C `SamplingIdentity`, `DEMConstructionRecord`, `DecoderModelIdentity`, `CheckedDecoderAdapter`, `CompatibilityAwareDecoderBank`, and `evaluate_paired_batch` contracts.

Registration requires `experimental_opt_in=True`. The helper checks circuit and sampling identity, Stim version, detector/observable dimensions, and the exact supported DEM conversion settings (`decompose_errors=True`, `approximate_disjoint_errors=True`; other unsupported conversion flags fail closed). It retains the NS-3B detector-support/logical-signature collision validation by calling the upstream constructor unchanged. Failed construction closes any partially created adapter. BeliefMatching remains marked experimental and does not become a default or fallback decoder.

PyMatching remains constructed through its existing NS-2C adapter. Both ordinary matching and correlation-enabled matching are exercised explicitly; the latter uses correlation mode at graph construction and batch decoding. The integration does not modify either behavior.

## Information parity and compatibility

All three arms in the deterministic comparison use the same Stim circuit, the exact same decomposed `StimDEMArtifact`, sampling identity, assumed-noise identifier/provenance, and five manually supplied detector rows. The paired harness gives decoder implementations detector-only batches and has no observable labels to score. Decoder-model identities are distinct and recorded separately from the shared sampling identity. The BeliefMatching arm is an algorithm/representation comparison on the shared decomposed DEM; it must not be described as equivalent to PyMatching’s graph matching semantics.

| Arm | Implementation / mode | DEM and inputs | Registration |
|---|---|---|---|
| PyMatching ordinary | PyMatching 2.4.0, correlations disabled in construction and decode | Shared decomposed DEM; 40 ordered detector bits | Enabled baseline |
| PyMatching correlated | PyMatching 2.4.0, correlations enabled in construction and decode | Same DEM and detector bits | Explicit correlation mode |
| BeliefMatching | Pinned BeliefMatching 0.2.0 at `4458c278bbec273c8c1a26411dadccc49222f8ef` | Same concrete decomposed DEM and detector-only batch; NS-3B ordering checks retained | Experimental opt-in required |

## Deterministic fixture result

The saved fixture has shape `[5, 40]`, one observable, circuit SHA-256 `bc679e70b5aa50ce23d9761f990e6270fc3f75ea43d7dab7bc84bdde14de11a7`, and DEM SHA-256 `8e0854b17f584dccec4baa6694d80abbd78b1341b3038281ac42a041ce66cb91`. All three arms returned the same five predictions `[0, 0, 1, 0, 1]`; each had zero prediction disagreements against ordinary PyMatching on these five rows. No logical labels were supplied, so no error count or LER is available.

One local timing observation (not a performance benchmark): construction was 1.852 ms for ordinary PyMatching, 2.188 ms for correlation-enabled PyMatching, and 141.908 ms for BeliefMatching. Paired-harness wall time for the five-row decode was 0.739 ms, 0.773 ms, and 0.844 ms respectively. These one-run timings include small-batch/runtime effects and do not establish scalable throughput or comparative performance.

## Validation

- NS-2D integration plus NS-2B/NS-2C regressions: **80 tests passed**.
- Published NS-3B adapter deterministic suite: **14 tests passed**.
- Fixed-fixture executable completed and saved `FIXED_FIXTURE_COMPARISON.json`.
- Publication source manifest: 36/36 listed entries, 5/5 unchanged engineering dependencies, 16/16 documented copy-transformation outputs, and 2/2 publication-authored Markdown documents verified by SHA-256/size.
- Pinned lock installed in an isolated `.venv`; package versions matched the lock.
- No Stim sampling, training, scientific experiment, Stage 5 access, or protected-outcome access occurred.

Exact commands and environment are in `REPRODUCE_NS2D.md`; hashes are in `NS2D_ENGINEERING_MANIFEST.json`.

## Limitations and recommendation

The fixture proves interface compatibility, ordering checks, opt-in behavior, deterministic output contracts, shared input identity, and timing capture only. Its five hand-built detector rows are not sampled data. Identical predictions here do not imply equivalent decoders, accuracy, or superiority. BeliefMatching requires the validated decomposed approximate DEM route and remains subject to its documented alias-collision guard and upstream modeling/runtime limitations. A separately authorized, frozen development-only paired scientific comparison is needed before any efficacy claim.

**Recommendation:** accept this as an engineering integration for supervisor review; do not infer a scientific benefit or authorize evaluation sampling from these tests.
