# NS-4A V2 V5 Source Identity Binding

Status: source-identity repair only; benchmark and scientific sampling are not authorized.

## Noncircular identity design

`SOURCE_HASH_MANIFEST_V5.json` contains the exact V4 source file rows plus the V5 benchmark executable, its identity validator and launcher, the dependency lock through the inherited V4 allowlist, the unchanged V4 manifest, and the approved benchmark seed/collision artifacts. The manifest does not include its own hash or the final Git commit SHA. Its `source_tree_sha256` covers the sorted path/hash rows; the final manifest SHA-256 is computed externally after the file is written.

After the V5 code and manifest are committed, the owner-created authorization payload binds four independent identities: exact current Git HEAD, V5 manifest SHA-256, existing benchmark protocol SHA-256, and the unchanged six-seed inventory SHA-256. The validator requires the payload's commit to equal `git rev-parse HEAD`, verifies all manifest rows and hashes, checks the exact protocol/inventory paths and hashes, and refuses a dirty tracked checkout. The benchmark ID hashes the four bound values. This avoids the impossible cycle of embedding a commit SHA in a file whose content determines that commit.

The `owner_id` and approval statement are procedural fields, not a digital signature. The software verifies exact content and bindings; it does not independently authenticate the human who wrote the local file.

## Worktree policy

- The approved seed inventory and all collision-screen records are tracked in the review branch and covered by V5 file hashes.
- The sole allowed pre-run untracked path is `outputs/ns4a_v2_final_readiness_v5/BENCHMARK_OWNER_APPROVAL_V5.json`. It must remain untracked, have the exact V5 schema, and match all bound hashes and the current commit.
- Any other staged, modified, or untracked path fails the pre-run cleanliness check.
- The V5 benchmark output directory must not exist before execution. It is created only after authorization checks pass; existing output is never resumed or overwritten.
- Ignored local files cannot replace manifest-listed source inputs; every executable and dependency file is checked directly against the V5 manifest before authorization.

## Preserved inputs

- V4 manifest SHA-256 remains `96288e6d3b57f602699cc934fb4311f76b0d58c71e763c3b35aaade3be6108b9`; its file is unchanged.
- Benchmark protocol SHA-256 remains `80f1581d6cd4d57e70ba2c51c38720b9c530e12cc6fac79914d121c49f8bb5dd`.
- The six-seed inventory is unchanged at SHA-256 `761e693d070fa58c249133f2cd6621a195baed62c92d007260e3949289eabc67`.
- The final seed screen is the preserved 2,667-distinct-seed report. Earlier traversal reports remain intact and are explicitly superseded by `BENCHMARK_SEED_COLLISION_SCREEN_V1_FINAL.json`.

## Execution guard

`benchmark_v5.py` is a separately versioned copy of the V4 bounded workload runner. V4 source and protocol files are not edited. V5 keeps the existing 6,000-shot/six-call/time/memory/disk/artifact limits, detector-only archive schema, and no-label policy. It additionally requires current-commit identity, exact manifest and input hashes, clean worktree, unchanged seed-screen extraction, and the lock-matched environment fingerprint before the first sampler call.

No owner authorization file is created by this change. No Stim sampler was called and no shots were generated.
