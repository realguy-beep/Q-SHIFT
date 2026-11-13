# NS-4A V2 V5 Source-Identity Repair Report

## Status

The V5 source identity implementation and deterministic checks are ready for review. This work does not authorize or execute the bounded benchmark or scientific pilot.

## Change summary

- Added a separately versioned V5 benchmark runner and authorization validator. V4 runner, manifest, protocol, and historical records remain unchanged.
- V5 authorization requires exact current Git HEAD, clean tracked worktree, and exact V5 manifest, protocol, and inventory hashes. Only the exact local owner-authorization path may be untracked; seed inventory and collision evidence are tracked and manifest-covered.
- The manifest covers all 61 V4 source/dependency rows, the pinned dependency lock, unchanged V4 manifest, V5 executable/validator/launcher/tests, and approved seed evidence. It excludes its own hash and final commit SHA. The owner payload binds the final commit after publication.
- The benchmark identifier binds commit + V5 manifest + protocol + inventory. The authorization payload has an exact schema and 24-hour maximum lifetime. `owner_id` is procedural metadata, not a digital signature.
- Preserved the six allocated benchmark seeds and final 2,667-distinct-seed collision screen. Earlier traversal reports remain unchanged and are superseded by `BENCHMARK_SEED_COLLISION_SCREEN_V1_FINAL.json`.

## Validation

Commands run:

```powershell
python -m unittest discover -s outputs/ns4a_v2_final_readiness_v5 -p test_benchmark_source_identity_v5.py -v
python outputs/ns4a_v2_final_readiness_v5/verify_source_manifest_v5.py
python -m py_compile outputs/ns4a_v2_integrated_runner_v1/qshift_ns4a_v2_runner/benchmark_identity_v5.py outputs/ns4a_v2_integrated_runner_v1/qshift_ns4a_v2_runner/benchmark_v5.py outputs/ns4a_v2_final_readiness_v5/build_source_manifest_v5.py outputs/ns4a_v2_final_readiness_v5/verify_source_manifest_v5.py outputs/ns4a_v2_final_readiness_v5/run_benchmark_v5.py outputs/ns4a_v2_final_readiness_v5/test_benchmark_source_identity_v5.py
git diff --check
```

Results: 14/14 deterministic tests passed; V5 source verifier PASS for 73 files; Python compilation and whitespace checks passed. Tests cover wrong HEAD, dirty tracked files, extra untracked files, mismatched commit/hash fields, missing/mismatched owner authorization, modified executable, invalid V4/superseded manifest, seed extraction, and exact untracked-token handling. No Stim sampler was called.

V5 manifest SHA-256: `c3debd93346f6b04c3acc0d514f52e3b973f76c9f1b3dfb7867285d9df31403d`.

V5 source-tree SHA-256: `5383cb4f071b291ed19027de19c0a54b6366e4f4de452ac4b93df6af7dfaff0f`.

## Execution blocker retained

The existing V4 verifier was attempted and failed because the active global Python lacks locked distribution `iniconfig`; installed NumPy is 2.5.3 while the pinned lock requires 2.2.6. Python 3.12.10, Stim 1.16.0, and PyMatching 2.4.0 were observed. No package was installed or changed. V5 retains the existing V4 runtime-fingerprint gate and will fail closed until the approved isolated lock-matched environment is available.

No owner token was created. The only permitted future benchmark is the existing bounded 6,000-shot detector-only workload, with six sampler calls and existing resource caps. No scientific sampling or Stage 5 access occurred.
