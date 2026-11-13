# NS-2B Model-Information Parity Policy

## Identity and information accounting

The generating process is recorded in `SamplingIdentity.generating_noise_model_id` and its canonical provenance record. Each candidate's assumptions are separately recorded in `DecoderModelIdentity.decoder_assumed_noise_model_id` and `decoder_assumed_noise_provenance`. A nominal fixed decoder is therefore valid on a nonnominal sample stream when it explicitly declares that target sampling identity; its model mismatch remains visible and is not treated as an identity error.

Every deployable decoder receives the same immutable detector batch with exact Stim detector order. The checked registry passes a fresh copy of those same bytes to each model. No observable labels, hidden regime labels, true fault flags, future blocks, or protected result fields enter a decoder method. `evaluate_identity_aware_paired` refuses protected-test scope before decoding and scores labels only after all predictions return.

Decoder noise assumptions cannot be left ambiguous. A parameterized decoder names its assumed noise model and supplies a canonical provenance record. A method that has no explicit physical-noise parameter must still use a documented identity (for example, `not-applicable`) with a provenance rationale; an omitted/empty record is rejected.

## Fairness conditions for future evaluation

Before comparison, record for each arm:

1. Calibration/template samples and budgets, including whether they are shared or independent.
2. Model-selection information available in deployment and whether an arm has privileged true-noise information.
3. Assumed noise/DEM provenance and whether the DEM is decomposed, approximated, correlated, or undecomposed.
4. Detector history, coordinates, soft information, graph/hypergraph factors, and all other inference inputs.
5. Model/static-resource hashes, construction and inference time, memory, and update latency.
6. Evaluation sample identity and paired detector/label provenance.

The `DecoderModelIdentity` hash is an audit handle, not a proof that two decoders had equal resources or equal prior information. Information parity remains an experimental-design judgment requiring budgets and data-source records.

## DEM and representation differences

PyMatching's graphlike/decomposed DEM and a research decoder's undecomposed DEM are distinct model inputs with separate digests and settings. Compatibility means only that both declare support for the same detector and observable semantics. It does not assert equal probability distributions, graph compatibility, equivalent predictions, or equal informational privilege.

A graph decoder can register with a DEM record. A hypergraph or non-DEM decoder can set `dem_record=None`, but must still provide an explicit input representation supported by the interface, assumptions/provenance, correlation semantics when applicable, and static-resource hashes/notes. The current v2 implementation supports only unpacked binary detector matrices. A candidate requiring a richer graph object, hyperedge factors, soft data, syndrome history, or another temporal tensor needs a further versioned input contract and tests; no implicit conversions are allowed.

## Limits

Hashes and runtime metadata cannot prove sample origin, authorization, absence of hidden information, or calibration fairness. Those require controlled sampler boundaries, auditable data lineage, and independent review. A decoder implementation can also read unrelated global state; process isolation and code review are needed for stronger information-flow guarantees.
