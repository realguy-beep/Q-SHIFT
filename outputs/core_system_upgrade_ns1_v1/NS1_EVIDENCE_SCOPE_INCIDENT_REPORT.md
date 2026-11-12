# NS-1 Evidence-Scope Incident Review

**Disposition: HOLD — supervisor review required before publication.**  
This report is a local, uncommitted incident record. It does not change NS-1 code, historical freezes, expected hashes, or research results.

## 1. Preserved repository state

The pre-report Git snapshot was:

- Branch: `codex/ns1-circuit-identity`
- HEAD: `022588c7e9513d923da0b7f342a6199e34873b38`
- Tracked working-tree diff: empty (`git diff --stat` and `git diff --name-only` returned no entries).
- Before adding this incident report, the only changes were ten untracked NS-1 files: `qshift_core_v1/circuit_identity.py`, `dashboard/tests/test_circuit_identity_v1.py`, and eight files in `outputs/core_system_upgrade_ns1_v1/` (`NS1_CIRCUIT_IDENTITY_CONTRACT.md`, `NS1_COMPATIBILITY_TEST_REPORT.md`, `NS1_ENGINEERING_MANIFEST.json`, `NS1_EXTERNAL_DECODER_INTERFACE.md`, `NS1_UNRESOLVED_QUESTIONS.md`, `REPRODUCE.md`, `create_manifest.py`, `verify_manifest.py`).
- This report is the eleventh untracked path. No reset, clean, cherry-pick, merge, commit, or push occurred.

The new code and reports remain in the isolated NS-1 worktree. The accepted core branch and the separate research worktree were not edited by this task.

## 2. Incident chronology and command record

1. Created the isolated worktree/branch from the accepted core-v1.1 parent. Read the repository instructions, existing NS-0 engineering readiness report, core decoder integration contract, and current core/dashboard source.
2. Ran filename-only searches to locate committed NS-0/HAMLD material. In the core checkout, `rg --files | rg -i '(^|/|\\)(ns.?0|hamld|research.*decoder|decoder.*compat)'` returned the existing NS-0 readiness and integration-contract files. In the separate research checkout, a filename filter `rg --files 'C:\Users\LENOVO\Documents\QSHIFT-Research\Q-SHIFT' | rg -i 'ns.?0|hamld|decoder.*review|research.*decoder' | Select-Object -First 40` printed matching paths (up to 40), including research artifact names such as `outputs/neural_decoder_diagnostic/structured_seed_inventory.json` and `outputs/unified_headroom_audit/HEADROOM_PER_REGIME_DECODER_ERRORS.csv`. This stage listed paths; it did not read those files' contents.
3. Implemented the generic circuit/DEM identity module and deterministic tests; wrote NS-1 design and test documentation; ran deterministic tests and generated the NS-1 engineering manifest.
4. The historical v1.1 manifest check reported four pre-existing expected-hash mismatches. The current files were compared with the accepted base commit's blobs and found to match those blobs. No historical manifest was rewritten.
5. The final search command was:

   ```powershell
   rg -n -i --glob '*.md' --glob '*.json' 'HAMLD|NS-0|research decoder requirements' 'C:\Users\LENOVO\Documents\QSHIFT-Research\Q-SHIFT\outputs' | Select-Object -First 40
   ```

   It ran from `C:\Users\LENOVO\Documents\QSHIFT-NS1` and searched file **contents**, recursively under the separate research checkout's `outputs` directory, for Markdown and JSON paths matched by ripgrep's globs/traversal rules. The tool result contained no output. It did not display filenames, matching lines, or a match count. The recorded tool result did not expose a reliable `rg` exit code.

## 3. Exposure assessment

### Established from the existing command record

- The broad command was a content search, not a filename-only search.
- Its target was the separate local research checkout's `outputs` tree, not the NS-1 worktree's files.
- It returned no visible matches. No protected file contents, filenames, or match counts were printed by that command's result.
- The command had no redirection or explicit output-file destination. The command and empty result are present in the Codex tool transcript.
- The NS-1 engineering manifest was created and passed its 17-entry verifier before this final broad content search. Its `protected_outcomes_accessed: false` field therefore does not assess the complete session and must not be treated as a valid session-wide attestation.

### Reasonable inference

Ripgrep ordinarily opens candidate files to search their contents and does not create a persistent search index or cache. The command likely read content from non-ignored `.md`/`.json` files under the target tree until completion. The empty result means no matching text was emitted; it does not establish that no protected file was among the candidates read.

### Unknown without further authorized evidence

- The exact set of files opened by ripgrep, including which paths were skipped by ignore, hidden-file, or binary rules.
- Whether any protected Stage 5 or other sealed evaluation artifact was among the eligible JSON/Markdown files.
- Whether the operating system, endpoint-security software, or the desktop tool retained transient read caches. No such cache or persisted search output is evidenced in the available tool record, but absence is not verifiable here.
- The exact ripgrep process exit code.

Determining the exact accessed-file set by listing or opening protected outcomes would cross the stated evidence boundary. This report stops short of that action and requests supervisor direction.

## 4. Possible implementation contamination

The reviewed NS-1 additions implement explicit Stim circuit and DEM serialization hashes, declared geometry/noise/observable metadata, detector-column IDs/order fingerprints, and fail-closed compatibility checks. The tests use deterministic circuit construction and an explicitly supplied zero-syndrome input; the dashboard regression constructs the existing distance-3/five-round matching model. No source or test logic uses information returned by the broad search; its visible result was empty.

The only decision that could have been reinforced by the no-match result is the documentation statement that no NS-0/HAMLD-specific requirements were found in the available local research checkout. That statement was already based on the earlier filename search and must remain an availability observation, not proof that no report exists. No implementation behavior, circuit semantics, decoder selection, statistical decision, or scientific claim depends on contents from the broad search.

This supports **no evidence of implementation contamination**. It does not prove that no unobserved information was processed by the search. The conservative recovery is to hold publication pending supervisor review of the scope uncertainty; if the supervisor requires a clean-room rebuild, rebuild only the new NS-1 additions from the accepted base and the approved core-source contract, without using the research checkout or its outcomes.

## 5. Manifest findings

### Core v1.1 engineering manifest

The read-only verifier reported four mismatches between `outputs/core_system_upgrade_v1_1/MANIFEST.json` and current bytes. Existing command records show each current file hash matched the corresponding Git blob at the accepted base commit, while the manifest's historical expected digest differed:

| File | Manifest expected SHA-256 | Current/base-blob SHA-256 |
|---|---|---|
| `qshift_core_v1/controller.py` | `49e7987867324fe9b81c771ee78848c9be9863f3cedb4b98d2688faa31c94a08` | `b27bb76d59273fc1af06cb1c0db8bd545df21be6997c939ebfba9d540ef7bf90` |
| `qshift_core_v1/evaluation.py` | `a4de30fa858864fd7b66c693e921963b2d7011a633d186fc4ff76768bb7163e3` | `3012cd5822aa8b93f74b8b07f909aea60264278563fffc1a16b94d3df71c0c65` |
| `outputs/core_system_upgrade_v1_1/CORRECTIVE_REVIEW_REPORT.md` | `8e55b5c0339f8701528fcd6e3bef13d9f5d4c3027bd18287c48cfec4fcab373c` | `048f1decfac2ae50101ae10a4ca6bf4b2befbe52143d0acedfcf0fb85f46cf7b` |
| `outputs/core_system_upgrade_v1_1/V2_4_HOLD_AUDIT.json` | `22dccabcd80d98d0e1ba2d0c489803f4af194751fb4fc0f6ce226d3e19e16766` | `7b5ca864fd0f1c9921c3f1688d07ce67bb7a03aaabccb545b5f10110daaf87b1` |

This is an old engineering-manifest mismatch; it is not evidence that NS-1 changed those files. The current Git snapshot has no tracked modifications, and all NS-1 paths are new untracked additions.

### V2.4 historical discrepancy

Separately, the existing V2.4 audit records 13 expected-hash mismatches among 17 frozen entries and status `PREEXISTING_EXPECTED_HASH_MISMATCH_HOLD`. Its authorization flags remain recorded false. That is a historical scientific/authorization freeze discrepancy and is distinct from the four v1.1 engineering-manifest mismatches above. Neither manifest nor expected hash set was modified here. V2.4 remains **HOLD**.

The new NS-1 manifest's pre-search verification (17 entries, no mismatches) proves only that those listed bytes matched at that moment. It does not prove full-session evidence-scope compliance and is not a freeze.

## 6. Final assessment and requested supervisor decision

**Outcome: HOLD.** The empty search output and absence of content in the tool transcript limit exposure, and no contamination is evident in the new code. However, the exact accessed-file set is not available from existing records, and the broad content search may have read protected JSON/Markdown files. I will not enumerate or open those files to resolve that uncertainty.

Publication should remain paused until the supervisor decides whether the available transcript is sufficient for a documented deviation or whether a narrowly authorized, non-content filesystem audit or clean-room rebuild is required. No sampling, training, protected outcome inspection, commit, or push occurred.

## Factual clarification following supervisor review — 2026-11-12

The preceding phrase “No ... protected outcome inspection” means no targeted, intentional opening or review of protected outcome artifacts is recorded. It does **not** establish that the broad ripgrep process avoided reading any such file while searching eligible Markdown/JSON content. Search output was empty, the exact accessed-file inventory remains unknown, no protected outcome content appeared in the recorded output, and complete non-access cannot be established. The report is retained as the original incident account with this labeled clarification; the deviation is not erased or represented as harmless.
