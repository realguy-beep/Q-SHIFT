# NS-1 Unresolved Questions

## Research decoder requirements

No committed NS-0/HAMLD-specific requirements document was present in the reviewed core checkout or found by filename in the separate local research checkout at preparation time. This is an availability finding, not evidence that the research workstream has no such requirements. The generic input/identity boundary is retained until Research Codex supplies the exact decoder requirements.

Questions for that handoff:

- Does the candidate require a full detector history, a selected time window, detector coordinates, or only a flat detector vector?
- Which circuit/DEM construction and approximation settings are supported?
- Which logical observable basis, polarity, and correction convention does its output represent?
- Does it consume matching weights, correlated mechanisms, soft information, or a non-graph representation?
- What initialization, training/calibration provenance, resource envelope, and deterministic inference guarantees apply?
- Can all required inputs be made available causally without labels or hidden simulation state?

## Contract limitations

- The caller supplies semantic labels and detector-column IDs. The API verifies internal consistency, but cannot prove the caller correctly associated an arbitrary array with those labels.
- Circuit and DEM hashes are serialization identities. Equivalent circuits serialized differently (including Stim-version formatting changes) can have different hashes; this is intentionally conservative.
- A noise-record hash identifies the supplied record, not the truth of its parameters or the way the circuit was produced.
- Coordinates may be absent, incomplete, or use circuit-specific semantics. They are retained as unknown where unavailable and are required only when a candidate declares that need.
- The flat v1 `DecoderProtocol` does not represent a general multi-round history object, soft detector values, or arbitrary graph topology.
- No cross-distance or external-research decoder has been performance-tested by NS-1.

## Protected research state

V2.4 remains on HOLD. The existing historical V2.4 record of 13-of-17 expected-hash discrepancies remains unchanged. NS-1 neither repairs nor re-baselines that evidence. No Stage 5 or other protected outcomes were opened.

**Factual correction after the evidence-scope incident:** the preceding sentence reflected the earlier NS-1 work record and is not a complete-session non-access guarantee. The later broad content search returned no visible content, but its exact accessed-file set is unknown. Complete non-access cannot be established; see `NS1_EVIDENCE_SCOPE_INCIDENT_REPORT.md`.

The historical engineering manifest in `outputs/core_system_upgrade_v1_1/MANIFEST.json` also has four entries whose expected hashes differ from the accepted base commit's current file bytes: `qshift_core_v1/controller.py`, `qshift_core_v1/evaluation.py`, `outputs/core_system_upgrade_v1_1/CORRECTIVE_REVIEW_REPORT.md`, and `outputs/core_system_upgrade_v1_1/V2_4_HOLD_AUDIT.json`. Read-only verification confirmed the current bytes equal the corresponding base commit blobs. The old manifest was not edited or regenerated. The precise expected/current digest pairs and verifier status are preserved in `NS1_COMPATIBILITY_TEST_REPORT.md`.
