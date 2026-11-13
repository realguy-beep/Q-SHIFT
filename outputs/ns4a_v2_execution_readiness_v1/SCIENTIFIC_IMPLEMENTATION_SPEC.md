# NS-4A V2 scientific implementation specification (prepare-only)

This is an engineering translation of the proposed V2 protocol, not a replacement protocol, freeze, or authorization. Any ambiguity listed in `STATISTICAL_VALIDATION_PLAN.md` must be resolved by review before freezing. Scientific choices below are read from `NS4A_PROTOCOL_REVISION_V2.md` and `proposed_config_v2.json`.

## Frozen-proposal scope

- Stim rotated Z-memory surface code; distance 3, 5 rounds, 40 detectors, 1 observable.
- Gate fault mass 0.003; measurement flip probability 0.003; Pauli axis bias ratio 10:1:1.
- Six finite, non-factorial cells: balanced, X-biased, Z-biased at zero burst; balanced at per-boundary burst probabilities 0.005, 0.010, 0.015.
- The burst is the synthetic simultaneous `X8 X10` common-cause event inserted after each of five `MR` boundaries, with independent Bernoulli events across boundaries. It is not temporal persistence or a hardware-calibrated model.
- Exactly 304,000 unique proposed shots: 64,000 selection and 240,000 evaluation. The proposed 1800-second, 2-GiB RSS, and 1-GiB free-disk reserve are stop limits, not validated capacity claims.

## Candidate DEM identity set

The six hashes below are the exact serialized DEM byte digests recorded by PR #7's deterministic preflight for V2's assumed-model families. Each used Stim conversion flags `decompose_errors=true`, `approximate_disjoint_errors=true`, with `flatten_loops=false`, `allow_gauge_detectors=false`, `ignore_decomposition_failures=false`, and `block_decomposition_from_introducing_remnant_edges=false`. Preflight reports 40 detectors, 1 observable, and a PASS from the unchanged BM support/logical-signature alias guard for every model. These are identity/compatibility records, not a new construction or accuracy claim.

| Assumed family | Circuit SHA-256 | DEM-byte SHA-256 |
|---|---|---|
| `balanced_no_burst` | `3d8b248bb8e23cb64649835ccb8cff9e8c880ed9e997f40914272b25c726eae0` | `7761142fdafe5be0eafdb3602159782a93d055740b19f7e622a4ab5699b0f1e6` |
| `x_biased_no_burst` | `cdd93dc13a80a838fdf2e86cd011425a17d6b56e10240070566422e5290206b0` | `d829fa17f21cc45fa800c91ecdbe5db7112a20e93aed49eb0ead1296735e96e8` |
| `z_biased_no_burst` | `97bb2a8a7d6e514c476988511f410d6f37ff20057a55509000a444a68e30ee1f` | `0c4adcd5af3bcd7f7b89432d37e1ae5074a82d1e20df4e93bec5b509c7c3eafc` |
| `balanced_burst_0.005` | `d97f48514d2b490e0d3bea80bbbff6a58d01dbd367804e7ab9b6338d19182ee3` | `5c1becc727a5000e19e5f338be192244282d303aaa3dda5c2c0c63eb928ab83c` |
| `balanced_burst_0.010` | `bc679e70b5aa50ce23d9761f990e6270fc3f75ea43d7dab7bc84bdde14de11a7` | `8e0854b17f584dccec4baa6694d80abbd78b1341b3038281ac42a041ce66cb91` |
| `balanced_burst_0.015` | `9bc89aea15b611fff6e9af858edbd9ac896264093abcf72085a5a4733053057a` | `8debaa2f252458247c52ed83733307c5254158e661a9f90cf38b3214ebdb88cc` |

All six rows in the evidence matrix share detector-order fingerprint `4df606e0198d8b3f4a393fbd452f5078f221935ed20a3eff936d9059bc3150e4` and observable-semantics fingerprint `9573b0b43c93ed90a6e50295fed09bc9fdc4172cb0f0ab062d528d4b119f6c7e`. V2 requires rechecking these identities in the final runner; do not treat a previous matrix as proof that future generated input bytes match.

## Selection implementation contract

1. Generate the six selection cells using 8 independent roots per cell, sharing each root's detector/observable arrays across all twelve candidates. The V2 allocation assigns 1,333 shots to each of 48 cell-roots, plus one shot to roots 0–2 in the first four ordered cells and roots 0–1 in the last two, for exactly 64,000 shots.
2. Construct the six assumed DEM families above; make both ordinary and correlation-enabled PyMatching decoders for each. Ordinary mode must be disabled at construction and decode; correlation mode enabled at both. Exactly 12 candidates must be scored, no omissions.
3. Keep a single, immutable selection sample identity per root-condition cell. Assert detector and observable bytes are identical across all candidates; detector content hash, shape, dtype/convention, detector order, circuit identity and root/sample ID are logged. A hash alone does not prove data provenance.
4. Decoder constructors and prediction methods receive detector-only inputs. The scoring layer may read selection labels only after all decoder calls. Enforce this via a spy/information-flow test; no selector callback or model metadata may receive evaluation labels or true condition labels.
5. For candidate `j`, compute each cell's mean over that cell's eight per-root LERs, then average the six cell means equally. Do not pool shot counts across cells. Choose one global candidate before any evaluation data are generated or scored.
6. Resolve score ties using the model-family order in `proposed_config_v2.json`, then ordinary before correlation-enabled. Persist all 12 scores, exact tie set, chosen index, candidate identities, and source/config hashes. Never replace the chosen candidate using evaluation labels.
7. Report root-stratified selection-rank stability by resampling the same root IDs within each of the six cells and rescoring all candidates on the same resampled paired arrays. The number of replicates and its seed are not specified by V2 and remain a freeze blocker.

Selection labels are permitted for this scorer and this scorer only. BeliefMatching and PyMatching are compared on the same selected concrete DEM and declared assumed-noise provenance. `register_beliefmatching` enforces `experimental_opt_in=True`, DEM identity/provenance parity with a named comparator, and the support/logical-signature guard. The upstream BM decode call accepts detector arrays; generation identity remains audit metadata and must not be used to choose a decoder at evaluation time.

## Evaluation arms and evidence

Preserve V2 arm labels: nominal ordinary PM; nominal correlation-enabled PM; one selected pooled-fixed PM; the opposite correlation mode on the selected DEM as a matched-model control; and BM on the exact selected DEM. If the selected arm is already identical to a control configuration, deduplicate computation but retain the semantic arm labels and document the shared prediction bytes. Each of the 60 evaluation root-condition cells has 4,000 paired shots and is scored only after the global candidate is frozen. No arm receives a condition-specific selection or generating-condition label.

Persist detectors, observables, predictions, sample/root IDs, sampling and decoder-model identities, seed derivation record, model hashes, and atomic commit markers. The independent auditor must reconstruct per-arm errors, paired discordances, cell means, primary endpoint, secondaries, and all reported intervals from saved evidence without importing runner aggregation code.

Implementation status at this checkpoint: selection runner, seed inventory, statistical code, scientific execution runner, persistence/recovery layer, and independent saved-array auditor are **not implemented or frozen**. This document specifies acceptance conditions only.
