# NS-1 Controlled Recovery Report

**Recovery verdict: PASS WITH DEVIATION.** Publication is still awaiting separate supervisor approval. This result documents the bounded engineering recovery; it does not erase or prove harmless the evidence-scope incident.

## Scope and preserved state

- Working branch: `codex/ns1-circuit-identity`.
- Accepted base and current HEAD: `022588c7e9513d923da0b7f342a6199e34873b38`.
- The tracked diff is empty. NS-1 implementation, tests, reports, and manifests are untracked additions in the isolated worktree; there is no commit or push.
- No V2.4, Stage 5, frozen research protocol, prior outcome, or protected evaluation file was changed.
- No sampling, training, decoder-performance experiment, protected evaluation, or hardware operation was run.

The earlier `NS1_EVIDENCE_SCOPE_INCIDENT_REPORT.md` is retained. A clearly labeled factual clarification was appended: the earlier statement about no targeted inspection does not establish that ripgrep did not read protected content. The broad search output was empty, the exact accessed-file inventory is unknown, no protected outcome content appeared in the recorded output, no implementation dependency on search results was identified, and complete non-access cannot be established.

## Paths inspected for this recovery

### NS-1 working additions

- `qshift_core_v1/circuit_identity.py`
- `dashboard/tests/test_circuit_identity_v1.py`
- `outputs/core_system_upgrade_ns1_v1/NS1_CIRCUIT_IDENTITY_CONTRACT.md`
- `outputs/core_system_upgrade_ns1_v1/NS1_COMPATIBILITY_TEST_REPORT.md`
- `outputs/core_system_upgrade_ns1_v1/NS1_EXTERNAL_DECODER_INTERFACE.md`
- `outputs/core_system_upgrade_ns1_v1/NS1_UNRESOLVED_QUESTIONS.md`
- `outputs/core_system_upgrade_ns1_v1/NS1_EVIDENCE_SCOPE_INCIDENT_REPORT.md`
- `outputs/core_system_upgrade_ns1_v1/create_manifest.py`
- `outputs/core_system_upgrade_ns1_v1/verify_manifest.py`
- `outputs/core_system_upgrade_ns1_v1/REPRODUCE.md`
- Existing pre-incident snapshot `outputs/core_system_upgrade_ns1_v1/NS1_ENGINEERING_MANIFEST.json` (retained unchanged; its `protected_outcomes_accessed=false` field predates the search and is not a session-wide claim).

### Explicit baseline/engineering dependencies

- `qshift_core_v1/contracts.py`, `controller.py`, `evaluation.py`
- `dashboard/simulator.py`, `dashboard/configuration.py`
- `outputs/phase2b_pauli_bias/noise_model.py`
- `outputs/phase2b_pauli_bias/decoder_bank.py`
- `outputs/phase2b_pauli_bias/CALIBRATION_SELECTION.json` — read by the existing dashboard `prepare` path during the deterministic dashboard compatibility test; this is a saved decoder-selection record, not a Stage 5 or sealed-test outcome.
- `outputs/core_system_upgrade_v1_1/NS0_ENGINEERING_READINESS.md`
- `outputs/core_system_upgrade_v1_1/V2_4_HOLD_CONFIRMATION.md`
- `outputs/core_system_upgrade_v1_1/MANIFEST.json`
- `outputs/core_system_upgrade_v1_1/V2_4_HOLD_AUDIT.json`

No search was run against the separate research checkout during this recovery. Review of the newly added source shows it implements only circuit/DEM identity, explicit detector and observable conventions, decoder declaration, and deterministic compatibility validation. The added test uses deterministic Stim circuit/DEM construction and fixed supplied detector arrays; it contains no generated data archive, checkpoint, experimental outcome, seed inventory, authorization token, or model weights. No unrelated dashboard or baseline source file was changed.

## Implementation audit

The additive `CircuitIdentity` binds canonical Stim circuit and DEM text digests, Stim version, explicit code geometry/basis declarations, ordered detector IDs, circuit and DEM coordinate maps, observable ID/convention order, supplied noise-record digest, and explicit DEM-conversion settings. Unknown required semantics fail compatibility. `ExternalDecoderSpec` carries decoder implementation metadata separately from circuit identity. `DetectorBatch` declares column detector IDs and fingerprints; equal dimensions alone do not pass. `decode_checked` validates declared compatibility, copies detector input to the decoder, and validates the returned prediction contract. No candidate is automatically activated, and the fixed PyMatching path was not altered.

The API verifies consistency among supplied declarations. It cannot prove that a caller truthfully attached those declarations to the physical origin or actual column order of an arbitrary array. The hash is not provenance, authorization, or leakage proof.

## Deterministic verification

Runtime recorded by the prior environment check: Python 3.12.10, Stim 1.16.0, PyMatching 2.4.0, NumPy 2.5.3.

| Command | Result |
|---|---:|
| `python -m unittest dashboard.tests.test_circuit_identity_v1 -v` | 11/11 passed |
| `python -m unittest dashboard.tests.test_core_system_v1 -v` | 35/35 passed |
| `python -m unittest dashboard.tests.test_dashboard.SeedAndConfigTests dashboard.tests.test_dashboard.MetricAndStorageTests -v` | 11/11 passed |
| `python -m unittest dashboard.tests.test_dashboard.StructuredDecoderTests.test_qshift_stim_coordinates_make_expected_round_geometry dashboard.tests.test_dashboard.StructuredDecoderTests.test_residual_target_and_xor_correction_convention -v` | 2/2 passed |
| `python -m compileall -q qshift_core_v1 dashboard\tests\test_circuit_identity_v1.py outputs\core_system_upgrade_ns1_v1` | passed |
| `node --check dashboard\static\app.js` | passed |
| Python `HTMLParser` check of `dashboard/static/index.html` | passed |

The safe dashboard suite emitted a Starlette/httpx deprecation warning; its tests passed. The dashboard baseline regression builds the distance-3/five-round model and decodes one supplied all-zero syndrome. It does not call the Stim sampler. No full test discovery was run because other project tests can sample or train.

## Post-incident engineering manifest

The pre-incident `NS1_ENGINEERING_MANIFEST.json` is preserved unchanged. The new `create_manifest.py` builds `NS1_ENGINEERING_MANIFEST_V2.json` from an explicit 24-path source/documentation/engineering-record allowlist. Text hashes and sizes are calculated after CRLF-to-LF normalization to match the repository's text-file checkout rules. V2 includes this recovery report and the incident account, records the exact search-output and access-inventory status, and does not assert complete non-access. The V2 manifest excludes itself from its own file list, as documented by the verifier's design; it is not a freeze.

Post-incident manifest V2 verification passed **24/24 listed hashes**, with no mismatches. It also reports `sampling_performed=false`, `training_performed=false`, no protected content in the recorded search output, complete non-access not established, accessed-file inventory unknown, and the deviation disclosed. The manifest is not self-hashed and is not a scientific freeze. Historical hashes are not rewritten.

### Separate historical discrepancies

1. **Core v1.1 manifest:** four expected digests differ from current bytes. Existing read-only records show current bytes equal the accepted base commit blobs. This is an old engineering-manifest mismatch, not a change from NS-1. The exact four path/hash pairs remain in `NS1_COMPATIBILITY_TEST_REPORT.md` and `NS1_EVIDENCE_SCOPE_INCIDENT_REPORT.md`.
2. **V2.4 freeze:** 13 of 17 expected hashes differ in the pre-existing audit; V2.4 remains **HOLD**. This is separate from the four v1.1 manifest mismatches. No expected hash was changed.

## Remaining limits and publication gate

- Exact files read by the broad search remain unknown. No protected content was printed in the recorded output, but complete non-access is not established.
- No implementation dependency on a search result was identified; the no-requirements finding is only an availability statement, not proof that the research workstream has no HAMLD requirements.
- No HAMLD-specific requirements were available in the reviewed committed engineering records, so the adapter remains generic.
- The flat v1 decoder input does not represent soft information or arbitrary history tensors. A future decoder needing those inputs requires a separately versioned representation contract.
- This is software compatibility work only; no performance claim, hardware claim, or empirical generalization claim is made.

**Decision:** PASS WITH DEVIATION for the bounded NS-1 engineering package. Keep the incident disclosure permanently attached. Do not publish, commit, push, merge, or open a PR until separate supervisor publication approval.
