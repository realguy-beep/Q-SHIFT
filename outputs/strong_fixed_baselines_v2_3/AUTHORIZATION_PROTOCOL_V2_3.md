# Q-SHIFT V2.3 launch authorization protocol

**Status: implementation candidate for supervisor review only. Sampling is not authorized.** This separately versioned launch/provenance layer does not alter the scientific protocol, original V2 freeze/configuration, V1 evidence, or Stage 5 evidence.

## Why V2.3 exists

The original V2 configuration and freeze intentionally record `sampling_authorized=false`, while the frozen runner requires a true guard before sampling. V2.1 introduced a separate owner-approval layer, but its validator incorrectly required the 40-character Git commit ID to be 64 characters. The V2.1 valid-approval path was therefore unreachable. V2.2 corrected that distinction, and its synthetic valid-approval path reached the mocked sampler; the first complete V2.2 test run then exposed a test assertion that expected the wrong mocked function arguments. V2.2 is preserved unchanged as an intermediate candidate. V2.3 carries forward its code with the corrected assertion and an independently versioned freeze that verifies and hashes the V2.2 predecessor.

The V2.3 launcher validates a separate owner approval against the exact clean Git HEAD, V2.3 candidate freeze, original V2 freeze, frozen config, seed inventory, frozen runner, V2.3 launcher and verifier, and runtime environment. Only after all checks does the launcher pass the original V2 runner an in-memory copy of the config with only the authorization guard set true. The on-disk config remains false and the original freeze verifier is unchanged. Direct invocation of the original entrypoint remains fail-closed.

## Owner approval

No real approval file is present or generated. Separate explicit owner authorization would require a local record at `outputs/strong_fixed_baselines_v2_3/OWNER_APPROVAL_V2_3_TOKEN.json`. The existing `.gitignore` rule `*token*` excludes both this file and the run directory `outputs/strong_fixed_baselines_v2/run_v2_3_token/`, without changing the V2.1-bound `.gitignore`. The schema is strict: missing or extra fields, incorrect owner/scope, malformed timestamps, expired approvals, wrong hashes, and stale commit identity are rejected. Commit IDs must be exactly 40 lowercase hex characters; SHA-256 fields must be 64 lowercase hex characters.

The approval is a procedural JSON record, not a cryptographic signature. `approved_by` is not independently authenticated by the program; trust depends on owner account and filesystem controls. This remains a limitation.

## Fail-closed validation and resume

1. Read only the approval record first; absence or malformed/unauthorized content fails before inventory hashing/parsing or sampler invocation.
2. Require a clean tree and exact current commit, then compare freeze/config/runner/authorization/runtime bindings before inventory access.
3. Only after these match, verify inventory hash and content, uniqueness and collision fields; run the original V2 freeze verifier and V2.3 verifier (which transitively verifies V2.2 and V2.1).
4. Create-only persist an execution identity and exact approval receipt before dispatch. A changed approval or identity blocks resume. A completed run cannot be relaunched. No CLI or environment variable bypass exists; the only CLI flag is `--resume`, which still passes the identical approval gate.
5. Use the frozen V2 runner and fixed output path. No custom seed/config/output path is accepted.

## Freeze and tests

`PRETEST_FREEZE_V2_3.json` is a create-only review candidate. It hashes V2.3 launch/audit/test/docs code, `.gitignore`, the original V2 inputs, and the V2.2 predecessor freeze/verifier; V2.2 itself verifies the V2.1 predecessor. It records `sampling_authorized=false` and `sampling_performed=false`. Any source change invalidates it and requires a new version. All tests use temporary synthetic fixtures and a mocked sampler. No real approval, Stim sample, V2 run, or performance outcome is created.

