# Methodology and Limitations

## Evidence hierarchy

1. Raw arrays plus verified script/configuration and an independently reproduced analysis.
2. Structured result JSON reconciled to per-seed records and validated manifests.
3. A report supported by source results but not replayed in this handoff.
4. Exploratory single-seed runs, smoke runs, or pilot checkpoints.
5. Conversation-only claims without a local raw artifact.

This handoff did not execute experiments or replay decoder predictions. It inspected source, reports, structured JSON, raw-file inventories, checksums/manifest notes, and selected aggregate consistency checks. Evidence classes are assigned in `EXPERIMENT_REGISTRY.csv` and `RESULTS_MASTER.json`.

## Decoder target and scoring

For detector vector `d` and sampled logical observable flip `L`, a decoder returns a correction estimate `c(d)`. The scored residual is `L XOR c(d)`. Neither L nor simulation noise labels may enter inference. A model predicting `L` is not itself proof of a valid decoder; it must be evaluated as a correction on independent shots. Matching returns a correction to the declared observable, not a guarantee of recovering the physical fault chain.

## Data splitting and pairing

The starter CSV's rows are highly duplicated and only span 61 detector vectors, making random row splits weak evidence of generalization. Later experiments use explicit seed-separated training, validation and test batches. Where decoders are compared, paired shots allow discordant-shot tests such as exact McNemar. Shot-level tests quantify within-simulation paired discordance; independent-seed intervals/tests quantify robustness across sampled seed families. These answer different questions and must remain separate. A large shot-level sample does not compensate for very few independent seeds.

## Noise conventions and circuit scope

The prototype uses repetition-code `memory`, d=3, r=3, 8 detectors, 1 observable and after-Clifford depolarization. Phase 1 uses explicit single-qubit Pauli probabilities at post-CX participant locations, with measurement flips inserted before Z-basis measurements; equal per-location probabilities do not imply equal total circuit fault opportunities. Phase 2 builds DEM/PyMatching models and uses Stim's approximate disjoint-error decomposition for specified multi-component channels. Phase 3 uses a rotated d=3 surface-code memory circuit, 3 rounds, 24 detectors, 1 logical Z observable; the studied inserted Pauli channel is not a full correlated two-qubit gate model, and the pilot disabled measurement noise. Results from different geometries/channels are not directly pooled.

## Statistical controls and caveats

Phase 1 reports paired shot-level tests and seed-bootstrap intervals; its per-regime count discrepancy between report and JSON remains unresolved. Phase 2 screened specialists with validation and did not build a selector after the gate failed. Phase 3A's p=.0386 is unadjusted across 12 comparisons and does not survive its stated multiplicity adjustment. Phase 3B was the independent replication and did not confirm the effect. Multiple comparisons, low logical-error counts in some conditions, model mismatch, and a limited distance/round grid constrain conclusions.

## Resource and runtime claims

Reported timings are local batched Python/software measurements, not hardware or per-shot latency guarantees. Reported Python wrapper sizes omit native PyMatching graph allocations. Memory and runtime comparisons across scripts may use different measurement boundaries; compare only within a documented run. No hardware integration or hardware compatibility has been demonstrated.

## Missing or incomplete validation

- The legacy pickle was not deserialized; provenance and safety were not established.
- The personal-notes DOCX text was extracted, but visual inspection was blocked by missing LibreOffice renderer.
- Phase 1 per-regime JSON aggregate disagrees with its report table; a raw replay is needed to settle it.
- Phase 2 prose conflates the condition-specific oracle count (2,401) with the validation-selected strategy count (2,402); JSON/table clarify the definitions.
- Phase 3A v2/v3/v4 reuse identical raw samples and cannot count as replication.
- Raw decoder outputs were not regenerated from all Phase 1/2/3 arrays during this handoff.
- No confirmed adaptive benefit, unseen-mixture novelty handling, production-scale scaling, or hardware evidence exists.
