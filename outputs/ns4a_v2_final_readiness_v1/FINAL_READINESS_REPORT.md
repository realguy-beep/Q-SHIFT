# NS-4A V2 final execution-readiness milestone

## Scope and boundary

Engineering and deterministic-fixture validation only. No Stim sampler calls, random detector events, training, production seed allocation, historical outcome inspection, Stage 5 access, freeze activation, or scientific pilot execution occurred. The 304,000-shot protocol and all six conditions are unchanged. Research remains ON HOLD.

## Integrated safety corrections

- The runner now passes reconstructed DEM identity checks through a schema-aware validator and fails closed on any mismatch.
- Checkpoint winner freeze now independently recomputes the global selection result from all 48 saved selection archives, checks exact score/tie/order fields, and verifies the archive hash map before committing a winner. Resume rechecks the winner before evaluation.
- The run-directory audit now requires explicit reconstructed model identities for each partition/condition, sampling-circuit identities, and seed/reference bindings for all 108 roots. It validates every archive and marker against those bindings, then recomputes the saved-array results independently.
- The full synthetic rehearsal now exercises this stricter audit with all 12 selection candidates and five evaluation arms.
- Regression tests inject a valid-but-wrong selected candidate, checkpoint mutation, archive/marker interruption, and DEM-manifest mismatch. Fully committed archive+marker recovery remains covered; an incomplete archive/marker transaction fails closed and is never resampled.

The accepted PR #10 source manifest remains byte-identical to the base commit (SHA-256 `897ba2e57622be52c93c2a73859ef087688aea3472f86c7feb42b91a4c1e7f49`). Its synthetic rehearsal summary matches the base Git object after normalizing Windows CRLF line endings (Git-blob SHA-256 `eb16df270a3da5b7c60f7c789258961a9771cf1b3adc22f13fd2636aa6fd20db`). The new full-suite rehearsal wrote the 108 fixture archives to test temporary storage, reopened and rehashed all of them, checked all commit markers, and reran the independent saved-array audit before temporary cleanup. No raw fixture arrays were committed.

Validation command:

```powershell
$env:PYTHONPATH = (Resolve-Path 'outputs/ns4a_v2_deterministic_implementation_v1').Path + ';' + (Resolve-Path 'outputs/ns4a_v2_integrated_runner_v1').Path
& 'C:\Users\LENOVO\Documents\Codex\2026-11-13\qshift-ns4a-v2-lockmatched-venv\Scripts\python.exe' -m pytest outputs/ns4a_v2_deterministic_implementation_v1/tests outputs/ns4a_v2_integrated_runner_v1/tests -q
```

Final result: **55 passed in 65.62 seconds** using the lock-matched Python 3.12.10 environment. Machine-readable details from the earlier complete rehearsal invocation are in `DETERMINISTIC_REHEARSAL_VALIDATION.json`.

## Bounded benchmark harness

A separate 6,000-shot maximum runtime benchmark is implemented but was not run. It would measure six detector-only Stim generations, all twelve PyMatching candidates, the five evaluation arms including BeliefMatching, DEM/decoder construction, atomic detector-only archive I/O, recovery-time hash/schema verification, Windows process peak working set, wall time, output size, and disk reserve. Caps: 600 seconds, 1 GiB peak working set, at least 1 GiB free disk, and 128 MiB total benchmark artifacts. It requires an exact benchmark protocol/source/inventory hash match, a separate short-lived owner authorization, and a completed seed-collision screen. The inventory remains unallocated. No resource throughput claim is made.

The candidate execution-manifest schema mirrors the current `load_authorized_execution` field contract. No manifest instance, production inventory, historical seed-screen file, DEM manifest freeze, or owner token was created. A schema is not authorization; the runner remains fail-closed until all exact bound files and a separate owner approval are provided.

## Source and dependency provenance

Lock-matched environment verified by the regression suite: Python 3.12.10, Stim 1.16.0, PyMatching 2.4.0, NumPy 2.2.6, 23 locked distributions, and BeliefMatching commit `4458c278bbec273c8c1a26411dadccc49222f8ef`.

An intermediate V3 source manifest was produced and verified during implementation (SHA-256 `277bcf663abff1d60aedda1ef5da04ecce5f5f77359598743dbaa642cb147d3b`). Subsequent benchmark-hardening edits made that snapshot non-current; it is retained as historical preparation evidence and must not authorize execution. Final V4 source manifest SHA-256: `96288e6d3b57f602699cc934fb4311f76b0d58c71e763c3b35aaade3be6108b9`. Both the V4 verifier and the production runner's `verify_source_manifest` accepted the V4 file inventory and environment. No stochastic throughput benchmark was run; full-pipeline runtime and peak memory therefore remain unknown.

## Remaining blockers to a first scientific run

1. No production numeric seed inventory has been allocated or collision-screened; an explicitly approved historical seed-metadata allowlist is still required.
2. The new benchmark harness has only deterministic fixture validation. Its real full-pipeline throughput and resource usage remain UNKNOWN and require separate benchmark authorization.
3. No final immutable execution manifest or matching owner execution authorization exists. Production execution remains blocked by the existing fail-closed validator.
4. The historical V2 freeze remains a historical record. This milestone creates a separately versioned implementation manifest; it does not activate or replace a scientific freeze.

These are authorization/data-boundary prerequisites, not reasons to alter the protocol. No sampling should occur until the benchmark, seed review, final source freeze, and separate owner approval are complete.

## Readiness decision

**NO-GO for scientific sampling at this checkpoint.** This is an execution-readiness hold, not a scientific rejection of NS-4A V2. The runner and independent audit now pass deterministic integration checks, but the unmeasured full pipeline/resource profile and absent seed/authorization artifacts are genuine prerequisites. No automatic sampling or progression is enabled.
