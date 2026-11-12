# Historical V2.4 Freeze Hash Audit

## Finding

The V2.4 pretest freeze in the starting commit `0ff77c70e38a7e6c2ff547958aee00b0ae5c1fe5` records 17 file hashes. A read-only comparison of each recorded hash against the working file and the Git blob at that same base commit found 13 expected-hash mismatches and four expected-hash matches. The 13 mismatching source/configuration files have identical current and base-commit bytes. The remaining `.gitignore` entry matches its expected freeze hash; its working copy uses CRLF while the Git blob uses LF, and the normalized text is identical. The discrepancies therefore predate this core-upgrade branch; this work did not create them.

Line-ending conversion does not explain the 13 expected-hash mismatches: for those files, raw bytes, normalized-LF bytes, and the base Git blob all agree with one another and differ from the expected hash in the historical freeze. The `.gitignore` difference from its base-blob raw hash is only a CRLF/LF checkout conversion, while its raw worktree hash equals the freeze's expected value. No historical freeze or bound file was rewritten to make verification pass.

## Mismatches

| File | Expected in historical freeze | Current and base-commit SHA-256 |
|---|---|---|
| `outputs/strong_fixed_baselines_v2/PRETEST_FREEZE_V2.json` | `820c1f648f7516b82d7f4b3e6dd4c3617909bc9f3c9c5d5d59371f2bf2c06531` | `cce345f7459f693b989a24fafc3fe38e7f6351275358cca534c210c043f7d98d` |
| `outputs/strong_fixed_baselines_v2/experiment_config_v2.json` | `8a3a3e2d8fb062852465696aed4601ae19df89708316cdaa51430d1021323860` | `4460ecb4caffc3db4194d1b0000629358c246abade66d3d0bc7b9d8eebc54aaf` |
| `outputs/strong_fixed_baselines_v2/seed_inventory_v2_r2.json` | `9f38d03d3315bf74e33e2a994446bc1e103b9e08827d8b1cc8553516fbdc72c7` | `5530025b63cc571dc923e3f56f0fd2f7a93ab0832f38ca754872d47b59a7f64f` |
| `outputs/strong_fixed_baselines_v2_3/PRETEST_FREEZE_V2_3.json` | `dab92dadb57b4f1536ac0cbc2a14707ba5ac358c37594ea640f4a3e47d2206a2` | `038444567d23ba6ac57119358de66c71d5bdcbdd7e3cb5dd6028c2c5f9dd5cc4` |
| `outputs/strong_fixed_baselines_v2_3/candidate_freeze_v2_3.py` | `fcfdc3d2341df9015d4dab8db3830e91d771b8553a07f4fcba9ce4a1493d4a4f` | `861b5e5414e6dfba45f7712d4b87177f8f9cddfa3bb6a0ff95dd10620345e339` |
| `outputs/strong_fixed_baselines_v2_4/AUTHORIZATION_PROTOCOL_V2_4.md` | `e0c420ed5af1fbc93ec25373627d731a73f288b396384583094be0eab37e0186` | `5809b5d4580b39402982cd8878155339d67cef65fb5c375b774f6e8fd37f6472` |
| `outputs/strong_fixed_baselines_v2_4/RUNTIME_PROVENANCE_V2_4.md` | `2cfa9e3b88ff6a4b36c71ffeb5c6c3a3e1be3951b1b181fb1c8d9f4ef24f0cab` | `2c8603df32f607084325c86a6803e3ad995019a7b25e044683b07a1321fa2470` |
| `outputs/strong_fixed_baselines_v2_4/audit_saved_arrays_v2_4.py` | `784616c2bff7af7d1e3ef1aa43d768c2175a8152873a45fbba3fdefc62b12adc` | `fee089932fab7493807d53a60421f423c312071ebfb53091c92f8300fb1908d6` |
| `outputs/strong_fixed_baselines_v2_4/authorization_v2_4.py` | `ce86ebc4ca28d729727d7c994d56ca9b82af90137b9aa61aed13efca5d718b96` | `5c2e1d44463aa55f67daa01a1d7db0205bd072cb7672f009ea51df9762826600` |
| `outputs/strong_fixed_baselines_v2_4/candidate_freeze_v2_4.py` | `5dcb6c11cacf4add672a718bfa5ad8f70dc97a80c00948b2b827fc2948b974b4` | `426bb60c0f6f5b08cd884a85a3d42b14ea902038d3c98b4e32eecae235eb0d20` |
| `outputs/strong_fixed_baselines_v2_4/create_pretest_freeze_v2_4.py` | `1adb82a8bc918bd3f1e025ad947d6e962bae785eb3dbee615e393c45d71cdc20` | `a2c6aa9380d221a5734749c18a8988bd0cc029cf607024c30029d2423c881848` |
| `outputs/strong_fixed_baselines_v2_4/run_development_v2_4.py` | `3036ec33c880754768eae30023fdb9a8ad679a1bbc0251bee47d88836acd93df` | `8761df76bbd3e8762c3c1ee7c140613ab684a9e0355007fd159230f937911eca` |
| `outputs/strong_fixed_baselines_v2_4/test_authorization_v2_4.py` | `7bf21ab9f2c8f48705f390ea11ee9a9f116010f221b130049c296bf56f5a787b8` | `439bd4daee1bb3e4f4ca517c80dd885052a154fb4ebbbcb1ab8338ceaee149cb` |

The other four entries (including `.gitignore`) match their expected hashes. The machine-readable verifier records all 17 entries, including all four matches and the newline-normalized base comparison.

## Impact and safety interpretation

This is an unresolved historical evidence/provenance discrepancy. It prevents this branch from claiming that the original V2.4 hash-bound source set was independently verified against its recorded hashes. It does not establish that the scientific source was changed after freezing; current bytes are exactly those present in the declared base commit, but provenance before that commit is not established by this check.

The freeze authorization flags remain `sampling_authorized=false`, `sampling_performed=false`, and `sealed_test_access=false`. V2.4 remains on HOLD. This engineering branch does not activate approval, repair the manifest, or authorize sampling.

## Reproduction

From the repository root, run:

```powershell
python outputs\core_system_upgrade_v1\create_manifest.py
python outputs\core_system_upgrade_v1\verify_manifest.py
```

The verifier succeeds only when the core-upgrade file manifest matches, all 17 V2.4-bound text files are unchanged from the recorded base commit after newline normalization, and all three V2.4 authorization flags remain false. It reports `PRE-EXISTING_HASH_MISMATCH` separately and does not mislabel the historical expected-hash audit as a pass.
