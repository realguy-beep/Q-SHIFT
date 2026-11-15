# V2.2 runtime provenance and independent-audit handoff

## Run identity

Before the frozen V2 runner is called, the V2.2 launcher writes (create-only) `EXECUTION_IDENTITY_V2_2.json` and copies the exact `OWNER_APPROVAL_V2_2_TOKEN.json` bytes to `OWNER_APPROVAL_RECEIPT_V2_2.json` in `outputs/strong_fixed_baselines_v2/run_v2_2_token/`. The identity records:

- reviewed Git commit;
- V2.2 candidate-freeze hash and original V2 review-freeze hash;
- unchanged V2 configuration, seed-inventory, and frozen-runner hashes;
- launcher and authorization-verifier hashes;
- owner identity, approval timestamp/expiry, and approval-record hash;
- Python, OS/platform, Stim, PyMatching, and NumPy versions, plus a canonical runtime-environment hash;
- the fact that `sampling_authorized=true` is an in-memory guard value only, while the frozen on-disk scientific config remains false.

The package versions are recorded and must exist before launch; this candidate does not silently install packages or pin versions beyond the committed environment record. The owner approval must bind the runtime fingerprint. Environment drift therefore makes the approval stale and requires a new explicit review/approval.

The run identity and receipt are created before any call to the Stim sampler. A second identity with different bytes is rejected. Resume checks the same approval and identity; completed-run relaunch is rejected. The original runner still provides its own run lock and checkpoint checks. If the identity write is partial or inconsistent, execution stops before sampling; no automatic cleanup or rewrite is attempted.

## Independent audit

`audit_saved_arrays_v2_2.py` first validates the execution identity and receipt against the current clean reviewed commit, both freezes, frozen config/inventory, source hashes, and recorded runtime versions. It then invokes the existing read-only V2 saved-array auditor, which verifies the original freeze, checks archive and commit-marker hashes, re-decodes saved detector arrays with the frozen PyMatching bank, and recomputes paired results. The adapter adds the approved execution identity to its audit output; it does not relax or replace the original V2 source-hash verification.

Fixture tests patch the underlying array auditor after checking both freeze layers. No real V2 arrays currently exist, so a full saved-array audit and runtime benchmark have not been run. The auditor must not be pointed at V1 or Stage 5 runs.

## Remaining risks

- A local JSON owner approval is a procedural record, not a digital signature. Its provenance relies on account and filesystem access controls.
- Execution is permitted only from the exact approved clean commit. A subsequent commit or environment change requires new approval.
- V2’s original statistical plan remains a development design: the root-stratified percentile interval is descriptive, and no confirmatory p-value or superiority claim is specified.
- The original V2 calibration-budget asymmetry remains: pooled and adaptive arms have equal total detector calibration shots but pool/use them differently; safety-static additionally uses labeled selection/validation data.
- Historical RNG coverage is limited to screened metadata; undocumented seed reuse cannot be ruled out.

