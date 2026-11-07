# Safe Development Evidence Export Specification

## Exportable by default

- Source code, tests, dependency/environment metadata, protocols, configurations, seed inventories and collision-audit summaries.
- Lightweight aggregate results, per-root result tables when they contain no sample-level labels, and evidence manifests.
- Figures derived from development-only aggregates.
- A dataset card that states provenance and limitations without listing sealed-test paths or contents.

## Keep local / do not export by default

- Raw detector/observable shot arrays, per-shot prediction archives, model checkpoints, optimizer states, and large run logs.
- Any directory, file, or record designated independent-test, sealed, final-test, or held-out confirmation.
- Credentials, `.env` files, tokens, or machine-specific runtime state.
- Any data whose partition membership or provenance is uncertain until audited.

## Required checks before an authorized export

1. Confirm the experiment is complete and no process is writing its output.
2. Read that experiment's protocol and independent audit; verify its split and test-access status without opening sealed material.
3. Check `git status`, staged paths, file sizes, `.gitignore`, and staged diff.
4. Scan staged text for credentials and local paths; inspect archives only if they are explicitly approved development data.
5. Preserve manifests and original evidence hashes. Never repackage files to bypass ignore rules.
6. Record export scope, source hashes, and exclusions in the corresponding reproducibility report.

## Dataset sharing limitations

The inventory is a study-level catalog, not a deduplicated data release. No aggregate unique-row claim is permitted without an explicit cross-study deduplication protocol that does not touch sealed material. Historical arrays remain local under the repository's ignore rules. A future public development-data package would need explicit partition manifests, schema documentation, license review, and a separate leakage audit.
