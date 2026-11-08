# Stage 5 Execution Safety Repair v3.3

## Decision

**GO for the safety repair only; Stage 5 sampling remains unauthorized.** The v3.3 wrapper preserves the frozen research protocol and adds process locks, deadline supervision, durable checkpoints, fail-closed recovery, and independent saved-array verification. All required v3.3 tests passed. No Stage 5 evaluation samples were generated.

## Historical freeze and scope

The Stage 5 v2 freeze remains `PRETEST_FROZEN_NOT_AUTHORIZED`. Its **53/53 SHA-256 entries match**. The configuration remains 6,050 roots and 27,225,000 unique shots. Endpoint B, its −0.0002 null boundary, planning alternative, no-harm check, and secondary inference rules are unchanged. No v2 source or frozen evidence was edited.

v3 and v3.1 are retained as superseded local drafts. v3.2 added worker-owned locking and a separately supervised finalizer. v3.3 adds mandatory self-verification of its own pre-sampling source/configuration freeze in both the CLI preflight and before execution; the worker repeats the verification before importing the frozen v2 runner.

## Safety implementation

- **Locking:** A launcher lock excludes simultaneous controller processes. A distinct worker lock remains held for the entire sampling/aggregation process, so a surviving child remains protected if its launcher exits. A second worker fails before writing status. Locks are nonblocking kernel file locks. Live-lock contention fails closed; crash releases the OS lock and leaves owner metadata. Stale metadata is never used to override a held kernel lock, and a possibly live PID blocks takeover.
- **Deadline:** One monotonic deadline begins before freeze verification and is shared across the worker, independent auditor, and finalizer. A parent supervises each child and terminates it at expiry. The v2 `completed` state is intercepted as `finalizing`. A separate finalizer verifies counts and hashes, writes the final manifest, reserves time for the terminal status replacement, and is itself subject to the parent deadline. Deadline expiry produces a non-completed status.
- **Checkpoint commitment:** Checkpoints use unique temporary files, flush and file `fsync`, atomic replacement, and SHA-256 commit markers. Resume verifies every marker. A missing or mismatched marker blocks recovery. Counts are reconstructed from committed archives rather than attempted sampler calls.
- **Active sampler recovery:** The benchmark fault killed a live worker at a marker adjacent to a real 1,000,000-shot Stim calibration call. Status retained the in-flight calibration and zero generated/committed shots; no archive existed. Explicit recovery recorded the uncommitted attempt, replayed the same frozen benchmark seed, and the independent audit counted that saved stream once. The interrupted call was not reported as completed.
- **Atomic outputs:** Status, summary, archive manifest, recovery journal, independent audit, and finalization manifest use atomic replacement. POSIX directory `fsync` is attempted where supported.

## Regression tests

Command:

```powershell
python -m unittest outputs.stage5_execution_safety_v3_3.test_safety_v3
```

**PASS: 15 tests, 0 failures, 52.501 seconds.** Tests cover both source freezes; two-process lock contention; worker-lock survival after launcher release; stale-lock recovery after crash; checkpoint interruption before replacement, between archive replacement and commit marker, and after commit; JSON write interruption; expiry during aggregation, artifact writing, and finalizer writes; active sampler interruption; explicit uncommitted replay; committed checkpoint resume without resampling; marker corruption rejection; and independent benchmark array/prediction recomputation.

The non-sampling preflight command also passed:

```powershell
python outputs/stage5_execution_safety_v3_3/safety_runner_v3.py --preflight
```

It verified 53 historical hashes and 13 safety source/config hashes, reported `PASS_NO_SAMPLING`, and confirmed the Stage 5 run directory was absent.

## Independent benchmark recovery audit

The benchmark allocations are independent from the frozen Stage 5 reservation and were frozen before benchmark sampling. Eight benchmark seeds were unique; no collisions were found among 11,495 recoverable historical seed integers, and the Stage 5 reservation was checked by namespace bounds without opening its stream rows.

- `benchmark_runs/paired_audit/`: 2 roots, 256 calibration plus 512 paired evaluation shots per root, **1,536 shots total**. Independent re-decoding and both checkpoint hash checks passed.
- `benchmark_runs/active_sampler/`: after the live-call interruption, committed shot count was zero and no checkpoint existed. Explicit replay completed **1,000,000 calibration plus 64 evaluation shots**; its recovery journal says `uncommitted_stream_will_replay_same_frozen_seed`. Independent re-decoding and the checkpoint hash passed.
- Atomic-write injection after archive replacement but before the commit marker was rejected. Injection after the marker but before status update resumed from the checkpoint without another calibration sample.
- Timeout injections during final aggregation, artifact output, and the finalizer's artifact-write phase terminated without a successful completion status.

These are bounded safety fixtures, not decoder-performance experiments. Their logical error counts are not used to make a research claim.

## Reproduction

From repository root in PowerShell:

```powershell
python outputs/stage5_execution_safety_v3_3/safety_runner_v3.py --preflight
python -m unittest outputs.stage5_execution_safety_v3_3.test_safety_v3
python outputs/stage5_execution_safety_v3_3/benchmark_harness.py --run-dir outputs/stage5_execution_safety_v3_3/benchmark_runs/paired_audit
python outputs/stage5_execution_safety_v3_3/benchmark_harness.py --config outputs/stage5_execution_safety_v3_3/active_sampler_config.json --run-dir outputs/stage5_execution_safety_v3_3/benchmark_runs/active_sampler --kill-active-sampler
python outputs/stage5_execution_safety_v3_3/benchmark_harness.py --config outputs/stage5_execution_safety_v3_3/active_sampler_config.json --run-dir outputs/stage5_execution_safety_v3_3/benchmark_runs/active_sampler --recover-uncommitted
```

The interruption command intentionally exits nonzero with `interrupted_active_sampler`. The recovery command is explicitly benchmark-only. Neither harness command can target the frozen Stage 5 run path.

## Limitations

- Windows file flush plus `os.replace` is tested, but portable directory `fsync` is unavailable in this Python implementation; sudden power-loss durability remains unverified.
- The interruption marker is adjacent to the native Stim sampler call. The exact internal C-level point cannot be observed; evidence establishes that the process was terminated before the call returned to Python or any checkpoint was committed.
- Deadline tests use short injected limits, not an actual two-hour run. They exercise termination and status behavior for each expensive phase, but long-run scheduling and OS shutdown latency remain unmeasured.
- Independent saved-array re-decoding covered three benchmark roots, not all 6,050 Stage 5 roots. Full-scale memory, filesystem behavior, and runtime remain unverified at the target allocation.
- An owner record naming a live PID when no kernel lock is held is treated conservatively and requires operator investigation (including possible PID reuse).
- Disk exhaustion and system-wide memory pressure were not induced. The frozen 512 MiB free-disk and 2 GiB RSS limits are unchanged.

## Final status

The v3.3 safety freeze hashes the launcher, worker, auditor, finalizer, tests, configurations, protocol, and seed audit before benchmark sampling. Final verification confirms those 13 source/config hashes and all 53 historical Stage 5 hashes still match. `outputs/stage5_secondary_inference_repair_v1/run` remains absent, the frozen v2 status remains unauthorized, and Stage 5 evaluation shots remain **zero**. No sealed outcomes or website worktree were accessed.
