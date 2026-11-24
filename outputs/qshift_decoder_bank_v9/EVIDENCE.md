# DB8-dev local evidence (for independent verification)

This branch is `claude/qshift-decoder-bank-v9-db8` at commit 2e4ef30e0, plus the git-ignored `work/` run folders of all three DB8 attempts and the fidelity gate.

- **Paths and content:** the folders are added at their original paths and are byte-identical to the local copies. Nothing was regenerated, re-run or analysed again.
- **Manifest:** `EVIDENCE_MANIFEST.json` lists every added file with its byte size and SHA-256.

| Folder | What it holds | Cross-check |
|---|---|---|
| `work/dev/` | attempt 1: `RUN.lock`, journal, status and 7 partial archives in `partial/` | `RUN_ATTEMPT1/PARTIALS.json` |
| `work/dev_a2/` | attempt 2: `RUN.lock`, journal, status, 28 records and 28 archives | `RUN_ATTEMPT2/OUTPUTS.json` |
| `work/dev_a3/` | attempt 3, the analysed run: 64 records and 64 archives | each record's `archive_sha256`; `results/dev/records` is byte-identical |
| `work/fidelity/` | the fidelity re-run of DB6 dev BB_e0 and U_e0 | `FIDELITY.json`, and DB6's `results/dev` |

The DB8 verdict (no ADVANCE) and every committed file from the base commit are unchanged.

The attempt 1 and attempt 2 outputs were never analysed. They are included only so their provenance can be checked.
