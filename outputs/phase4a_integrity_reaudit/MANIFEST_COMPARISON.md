# Manifest comparison

`MANIFEST.json` has 223 entries. `MANIFEST_FINAL.json` has 226. The final manifest adds `MANIFEST.json`, `POSTRUN_AUDIT.json`, and `audit_saved_results.py`; there are no entries only in the initial manifest. Both manifests agree on hashes for all other files except the three appended Markdown files.

The three changed entries are `IMPLEMENTATION_LOG.md`, `PHASE4A_RESULTS.md`, and `PHASE4A_INTERPRETATION.md`. The initial manifest's hashes match no longer-current bytes; the final manifest hashes match current bytes. File modification timestamps place the initial manifest after RESULTS/CSV and the final manifest shortly after the three Markdown edits. The implementation log states those edits followed the initial run. No Git repository/history is present in this workspace, so the sequence is supported by timestamps and the implementation log, not Git commits. `MANIFEST_FINAL.json` is not treated as independently trustworthy: its listed hashes were recomputed against current bytes in a separate audit and match.

Classification: three mismatches are documentation-only modifications. Added final-manifest entries are expected post-run audit artifacts. No scientific source, config, raw prediction, or result JSON/CSV hashes differ between manifests.
