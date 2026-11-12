# Q-SHIFT V2.2 launch authorization protocol

**Status: implementation candidate for supervisor review only. Sampling is not authorized.** This is a separately versioned launch/provenance layer; the original `outputs/strong_fixed_baselines_v2/PRETEST_FREEZE_V2.json`, its scientific configuration, inventory, runner, and V1/Stage 5 evidence remain unchanged.

## The freeze conflict and its resolution

The frozen V2 configuration correctly records `execution.sampling_authorized=false`, and its verifier checks that value and the configuration hash. The V2 runner also requires true before sampling. Editing the configuration would invalidate its immutable freeze. V2.2 does not edit it: the new launcher checks a separate owner approval against the exact Git HEAD, V2.2 candidate freeze, original V2 freeze, frozen config, seed inventory, original runner, V2.2 launcher/verifiers, and runtime environment. Only after every check succeeds does the launcher give the original V2 runner a temporary in-memory configuration copy with that single authorization guard set true. The on-disk configuration remains false, and the original V2 freeze verifier still runs unchanged.

Running the original V2 entrypoint directly still fails before seed-inventory access or sampling. The V2.2 entrypoint accepts only `--resume`; it has no `--authorize`, `--skip-auth`, alternate config, seed, inventory, or approval-path switch. Environment variables are not consulted for authorization. `--resume` passes through the identical approval gate.

## Owner approval record

No real approval file is included or created by this implementation. After separate review and explicit owner authorization, the owner must create `outputs/strong_fixed_baselines_v2_2/OWNER_APPROVAL_V2_2_TOKEN.json` locally. The existing `.gitignore` rule `*token*` excludes this file and the local run directory without modifying the V2.1-bound ignore file. Required fields are strict and unknown/missing keys are rejected:

```json
{
  "schema_version": 1,
  "approval_status": "OWNER_AUTHORIZED",
  "approved_by": "realguy-beep",
  "approved_at_utc": "<UTC timestamp>",
  "expires_at_utc": "<UTC timestamp, within 24 hours of approval>",
  "approval_statement": "I explicitly authorize the frozen Q-SHIFT V2 development experiment identified by the exact commit, freeze, configuration, seed inventory, and runner hashes in this record.",
  "experiment_id": "qshift-strong-fixed-baselines-v2",
  "approved_commit_sha": "<40-character reviewed branch HEAD>",
  "candidate_freeze_sha256": "<PRETEST_FREEZE_V2_2.json SHA-256>",
  "original_freeze_sha256": "<PRETEST_FREEZE_V2.json SHA-256>",
  "configuration_sha256": "<frozen experiment_config_v2.json SHA-256>",
  "seed_inventory_sha256": "<frozen seed_inventory_v2_r2.json SHA-256>",
  "frozen_runner_sha256": "<run_development_v2.py SHA-256>",
  "authorized_launcher_sha256": "<run_development_v2_2.py SHA-256>",
  "authorization_validator_sha256": "<authorization_v2_2.py SHA-256>",
  "candidate_freeze_verifier_sha256": "<candidate_freeze_v2_2.py SHA-256>",
  "runtime_environment_sha256": "<canonical runtime dependency fingerprint SHA-256>"
}
```

The record is bounded to at most 24 hours. The reviewed commit is validated as exactly 40 lowercase hexadecimal characters; all SHA-256 bindings are separately validated as 64 lowercase hexadecimal characters. It is not a cryptographic signature: `approved_by` and the JSON are a procedural owner action, protected by local/GitHub access controls. This limitation must remain explicit. A future deployment that needs cryptographic proof would require a separately reviewed signed-approval design and trust-key policy.

## Validation order and fail-closed behavior

1. Parse only the approval file. Missing, malformed, expired, wrong-owner, wrong-scope, or non-authorizing records fail before seed-inventory reads or sampler calls.
2. Require a clean working tree and exact approved `git rev-parse HEAD`. Compare the candidate freeze, original freeze, config, frozen runner, authorization code, and runtime fingerprint before opening the inventory.
3. Hash the inventory only after those approval bindings match. Reject a mismatch before parsing it.
4. Run the original V2 freeze verifier and the additional V2.2 source-freeze verifier; validate unique seeds, no recorded collisions, and fixed allocation. The original V2 scientific methods are not altered.
5. Persist an immutable `EXECUTION_IDENTITY_V2_2.json` and the exact approval receipt in the run directory before dispatch. On resume, require the same record and identity; an incomplete or mismatched identity fails closed. Completed runs cannot be relaunched.
6. Dispatch the frozen V2 runner, and restore its Python functions/argv after return. The V2 runner retains its normal experiment lock, checkpoints, and scientific logic.

The approval path and output run path are constants in the launcher; callers cannot select another approval file or run directory through the CLI. A stale or ambiguous run directory requires manual review; no lock/checkpoint is automatically removed or rewritten to make resume pass.

## V2.2 candidate and sampling boundary

`PRETEST_FREEZE_V2_2.json` is create-only and binds the new authorization code, runner, auditor adapter, tests, protocol documents, `.gitignore`, exact original V2 freeze/config/inventory/runner, and the V2.1 predecessor freeze/verifier. Verification independently rechecks V2.1 and records its freeze hash as the superseded predecessor. V2.1's authorization validator had a schema defect: it required the 40-character commit SHA to be 64 characters, making the valid owner-approval path unreachable. That V2.1 package and freeze remain unchanged as historical evidence; V2.2 corrects the schema by validating commit and SHA-256 fields separately. V2.2 is marked `AUTHORIZATION_CANDIDATE_REVIEW_ONLY`, with both sampling fields false. It is not owner approval. Any change after creation requires a separately versioned candidate/freeze; neither freeze builder overwrites a different existing record.

All approval tests use temporary files under `SYNTHETIC_TEST_FIXTURE_ONLY` and a mocked sampler. No actual approval record, run identity, Stim sample, V2 run, or performance result is created.

