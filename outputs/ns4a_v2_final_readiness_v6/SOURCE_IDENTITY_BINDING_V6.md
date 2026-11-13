# V6 source identity and authorization contract

The V6 source manifest deliberately does not embed its own final Git commit SHA. It binds the accepted V5 manifest and all V5 source rows, then adds the V6 repair sources, tests, recovery record, and documentation. After the V6 changes are committed, the owner authorization binds that exact final `git rev-parse HEAD` to the V6 manifest, the unchanged protocol, the unchanged six-seed inventory, and the recovery-record hash. This avoids self-referential commit hashing.

The V6 validator requires the current HEAD to exactly match the authorization, checks the full V6 source manifest and clean tracked worktree, and permits only the preserved untracked V5 token plus the new untracked V6 authorization file. It verifies the V5 token against its incident-recorded hash but never accepts or parses it as V6 authorization.

The V6 manifest inherits all file rows from the V5 source manifest, verifies the V5 manifest hash, and adds the V5 manifest itself plus all V6 execution, memory-guard, recovery, test, diagnostic, and manifest-tooling files. It excludes only the V6 manifest itself to avoid self-reference. Its external SHA-256 is reported after creation.

The V6 authorization schema is exact. Required fields are:

`schema`, `owner_id`, `scope`, `approval_statement`, `sampling_authorized`, `source_commit`, `source_manifest_sha256`, `protocol_sha256`, `seed_inventory_sha256`, `recovery_record_sha256`, `created_utc`, and `expires_utc`.

V5 authorization schema is rejected. V6 authorization must be issued separately after review; no authorization file is created by this repair.
