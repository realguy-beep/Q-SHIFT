# NS-0 Main Codex Engineering Readiness Handoff

## Current integration entry point

An external research implementation can be wrapped as `DecoderProtocol` in `qshift_core_v1/contracts.py` and registered through `DecoderRegistry.register` in `qshift_core_v1/controller.py`. It receives detector bits only and returns a `DecoderPrediction` with an explicit `[shots, observables]` binary matrix and immutable `DecoderMetadata`. Experimental candidates remain opt-in. A new candidate is added beside the fixed PyMatching instance; it does not replace or mutate the baseline.

`qshift_core_v1/evaluation.py:evaluate_paired` accepts caller-supplied detector and observable arrays, gives each decoder a copy of the same canonical detector matrix, and uses observable labels only after each decode call for scoring. Current review changes verify returned metadata against registered metadata and make the identity descriptor include the input representation and all candidate metadata. The content/evidence hashes do not prove who generated the arrays, whether inputs were authorized, or whether upstream selection leaked labels.

## Existing PyMatching baseline

The existing route is preserved. `outputs/phase2b_pauli_bias/decoder_bank.py:51-57` builds the approximate Stim DEM and calls `Matching.from_detector_error_model(..., enable_correlations=True)`; `decoder_bank.py:85` also decodes with correlations enabled. `dashboard/simulator.py:27-55,85-104` retains the basis-specific frozen fixed-bank selection and explicitly uses the same correlation-enabled legacy adapter. The new adapter also supports explicit `correlation_mode=False` and `True`; deterministic tests construct tiny DEMs and decode supplied arrays in each mode.

## Geometry and representation limits

- `dashboard/configuration.py:67-70` restricts the dashboard to distance 3 and five rounds. `dashboard/simulator.py:30-55` independently asserts exactly 40 detectors and one observable and builds the current distance-3/five-round model.
- `outputs/phase2b_pauli_bias/noise_model.py:57-77` generates rotated surface-code X/Z-memory circuits and asserts that same 40-detector/one-observable shape. It sets native one- and two-qubit categorical Pauli channels at the generator's post-Clifford locations and basis-appropriate measurement flips; its declared cross-location model is independent gate locations.
- `dashboard/structured_decoder.py:1-62` uses Stim detector coordinates to embed the current detector columns in a sparse space-time tensor with an occupancy channel. This is a neural feature mapping, not a general decoder interchange format.
- The core API supports arbitrary positive detector/observable counts as flat matrices, but metadata currently lacks code-family, distance, rounds, memory basis, circuit/DEM digest, detector-order fingerprint, coordinate/history schema, and explicit observable IDs/convention. Equal dimensions alone do not establish semantic compatibility.
- A candidate requiring full syndrome history, soft information, detector coordinates, streaming, or multiple time slices cannot receive those inputs through the current flat binary `decode(detectors)` contract. Do not flatten such data silently; define a separately versioned adapter/input schema with a content-addressed ordering contract first.

## Data ordering, observables, and noise provenance

Within the current dashboard path, detector columns are the order returned by the same Stim circuit's detector sampler, and the observable label is Stim's one reported logical observable. The decoder output is an observable-flip prediction, not a physical qubit correction map. The paired-evaluation record now says the detector columns are in caller-provided order and identifies dimensions/dtypes, but it does not independently bind that order to a circuit detector-coordinate table or hash. `DecoderMetadata.noise_model_id` can label an assumption but does not bind the model to a DEM or prove how a caller built it.

Before accepting an external candidate for a different geometry, require versioned circuit/DEM identity, code-family and logical-memory basis, distance/round count, detector ID ordering/coordinates, observable IDs and prediction convention, noise-model and DEM-decomposition provenance, correlation construction/decode mode where applicable, and explicit supported feature representation.

## Deterministic integration acceptance tests

Require these before registry admission or any comparison:

1. Validate metadata types and exact registered-versus-returned metadata equality, including identity, version, dimensions, noise model, correlation mode and provenance.
2. Validate binary input/output, exact detector/observable dimensions, shot count preservation, empty-batch policy, error handling, deterministic repeated decode and no mutation of caller arrays.
3. Verify detector and observable ordering against the candidate's declared circuit fixture; test trivial/noiseless syndromes and analytically known single-fault signatures where applicable.
4. For PyMatching adapters, construct and decode with the same explicit correlation mode; compare wrapper predictions with a reference PyMatching instance on fixed supplied syndromes.
5. For controller integration, test nonnegative increasing block IDs, strictly earlier evidence, confidence threshold, hysteresis/dwell, invalid estimates, unsupported decoder selection and fixed fallback.
6. Verify paired evaluation hands identical detector content to every arm and labels are not passed to decoder calls; recompute error and discordance counts from returned predictions.
7. Hash source, configuration, circuit/DEM identity and deterministic fixture, and preserve every failed compatibility test. These checks validate software contracts, not performance claims.

## Exhibition readiness

The present dashboard is a local neural-training console with a fixed PyMatching comparison, not a complete single-shot exhibition explorer. Its current visual change explains configured simulation noise and observable prediction semantics; it does not render a detector grid or a sourced known-fault trace. A reliable exhibition demonstration would need a separate, clearly labeled deterministic/Stim-derived single-fault view; explicit separation of known injected fault, observed detectors, decoder prediction and simulated reference observable; actual run state and sample counts; and no invented physical correction map or hardware claim. A future external decoder can appear as an experimental comparison arm only after tests and provenance fields above are satisfied. No exhibition code or hardware was changed here.

## NS-0 decision

**Engineering readiness: CONDITIONAL.** Same-distance/same-order binary detector candidates can be integrated without changing fixed PyMatching. A geometry-changing, history-based, or feature-rich decoder is not yet semantically plug-compatible. Extend the typed input and circuit-identity contract in a separately reviewed change when Research Codex returns a concrete candidate; do not prebuild speculative model architectures.
