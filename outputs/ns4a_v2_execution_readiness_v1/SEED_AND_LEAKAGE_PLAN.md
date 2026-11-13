# Seed, sample-identity, and leakage plan (no seed allocation)

**No numeric seeds were generated, reserved, tested through a PRNG, or committed in this preparation task.** This file defines a design for a later separately reviewed freeze.

## Disjoint stream domains

Use separate, explicit purpose domains for:

| Domain | Purpose | Must be independent of |
|---|---|---|
| `ns4a-v2/selection` | Six cells × 8 selection roots; exact 64,000-shot allocation | evaluation and every resampling stream |
| `ns4a-v2/evaluation` | Six cells × 10 evaluation roots × 4,000 shots | selection and every resampling stream |
| `ns4a-v2/selection-rank-bootstrap` | Selection-root bootstrap ranks for 12 candidates | all sampling and analysis domains |
| `ns4a-v2/primary-bootstrap` | Primary evaluation root bootstrap | all other domains |
| `ns4a-v2/sign-flip` | Root-cluster sign-flip sensitivity | all other domains |

The later freeze must specify a deterministic, domain-separated derivation (for example, a named master entropy plus explicit purpose/condition/root labels and a documented generator), record the resulting numeric values and generator version, and reject duplicate derived seeds before any sampler call. Do not assign or derive the master entropy here. Do not reuse an upstream generator's mutable RNG state across roots, conditions, decoders, or analysis procedures.

## Root/sample identity and allocation assertions

Use a canonical logical sample key `(protocol_revision, partition, condition_id, root_id, shot_offset)`. Selection roots and evaluation roots have disjoint partition IDs; each root-condition owns one contiguous offset interval. Before sampling, assert exactly 48 selection root-condition cells and 60 evaluation cells, unique root IDs within and across partitions, expected shots per cell, no offset overlap, and total unique shot ceiling 304,000. On resume, each committed sample key and archive digest must be unique; rerunning an uncommitted call with the same seed may only proceed after proving the call's output was never committed. Never substitute a seed or count ambiguous samples.

The deterministic 16 selection remainder shots are assigned exactly as V2 says: +1 to roots 0–2 in the first four ordered selection conditions and roots 0–1 in the final two. This produces cell totals 10,667 for the first four conditions and 10,666 for the final two, while the selection objective remains equal-weighted by condition and by root, not shot-pooled.

## Collision-screening coverage

Before a future seed freeze, screen proposed numeric root and resampling seeds against every explicitly approved, recoverable historical development/diagnostic/template/selection/bootstrap seed inventory accessible under that review's allowlist. Record every checked metadata path, hash, exact coverage, and unresolved gap. Do not open protected Stage 5 or sealed outcome material. The current sparse review did not include any historical seed inventory, so historical collision coverage is **NOT PERFORMED / UNKNOWN**. The V2 configuration itself says seeds are unallocated; it is not a complete collision audit.

## Leakage barriers

- Sampling code alone constructs detector/observable arrays and sample IDs. Selection scoring code alone may access selection labels.
- Candidate decoders receive copied, binary detector arrays only. Constructor inputs are six fixed assumed DEMs; no true evaluation noise parameter, regime identifier, burst flag, or observable label may enter candidate selection or inference.
- Freeze the one global selection winner, its DEM bytes, model identity, tie-break result and code/config hashes before evaluation arrays are created.
- Evaluation labels remain outside decoder processes/objects and are attached only by the scorer after all arm predictions for a paired batch are complete.
- An independent audit must compare sample IDs, input digests and exact prediction row order across arms. It must not rely on the runner's own counts.
- The adapter wrapper carries `SamplingIdentity` and generating-noise identity for audit compatibility, but the upstream decoder receives only the selected DEM at construction and detector rows at inference. Tests must demonstrate that condition metadata cannot change which fixed model is selected and is not passed into the upstream inference call.

Content hashes establish byte identity only; they do not prove data provenance, authorization, non-access, or absence of leakage.
